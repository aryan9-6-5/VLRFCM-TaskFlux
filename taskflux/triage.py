"""Cost-coupled intent triage: act, continue, ask, or halt.

A fixed probability threshold on "is this a changeover?" ignores that the two
mistakes cost different amounts in different states of the build:

* acting on a false changeover wastes ``Ra``: the robot runs the changeover plan until someone
  notices, then has to get back to the running product;
* continuing through a real changeover wastes ``Rc``: it keeps building the wrong product until
  someone notices, and everything past the shared work has to come off (or is scrapped if an
  irreversible step comes up meanwhile);
* asking wastes ``Ca``: the operator's attention plus whatever part of the confirmation window the
  robot cannot fill with zero-regret hedged work.

Both error terms include the discovery delay itself: a mistake nobody has noticed yet is regret
even when the robot has nothing left to do. ``Ra`` and ``Rc`` come from the reconciler's
cost-to-go, so the confidence needed before acting or carrying on moves with the state of the
workpiece. Choosing the action with the least expected regret is Bayes-optimal for that cost matrix,
given calibrated probabilities. Because hedging makes asking cheap, the rule asks whenever the
classifier is unsure and acts or continues only when it is confident.

Safety is lexicographic, not weighed: a non-trivial chance the operator said
"stop" halts the arm before any cost comparison, and no hedged step runs while
a stop is plausible.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, Optional, Sequence

from .hedge import hedge_window
from .process import INF, Process
from .reconcile import Cell, Status, cost_to_go, reconcile

CLAR, EDIT, CHANGE, ABORT = 0, 1, 2, 3


class Action(str, Enum):
    CONTINUE = "continue"
    ACT = "act"
    ASK = "ask"
    HALT = "halt"


@dataclass(frozen=True)
class TriageParams:
    discovery_delay: float = 60.0   # seconds a missed changeover runs before someone notices
    confirm_window: float = 6.0     # seconds the operator takes to answer a question
    operator_cost: float = 4.0      # cost of interrupting the operator, in seconds-equivalent
    halt_cost: float = 3.0          # cost of a needless stop and resume
    p_halt: float = 0.10            # stop if P(abort) reaches this
    hedge: bool = True              # fill the confirmation window with zero-regret steps


@dataclass(frozen=True)
class Context:
    act_regret: float        # Ra
    continue_regret: float   # Rc
    ask_regret: float        # Ca
    act_allowed: bool        # False when the reconciler would have to escalate or refuse
    hedged: Sequence[str] = ()


def _next_steps(process: Process, done: frozenset, current: str, budget: float) -> frozenset:
    """State after the running plan works for ``budget`` more seconds."""
    C = set(done)
    t = 0.0
    for s in process.topo_order(process.goal(current) - C):
        if t >= budget:
            break
        C.add(s)
        t += process.steps[s].forward_cost
    return frozenset(C)


def _after_plan(process: Process, done: frozenset, plan, budget: float):
    """State after the robot executes ``plan`` (undo, then build) for ``budget`` seconds, and the time used."""
    C = set(done)
    t = 0.0
    for s in plan.undo:
        if t >= budget:
            break
        C.discard(s)
        t += process.steps[s].undo_cost
    for s in plan.forward:
        if t >= budget:
            break
        C.add(s)
        t += process.steps[s].forward_cost
    return frozenset(C), t


def build_context(process: Process, done: Iterable[str], current: str, target: str,
                  params: TriageParams = TriageParams(), cell: Optional[Cell] = None) -> Context:
    C = frozenset(done)
    plan = reconcile(process, C, target, cell)
    v_cur = cost_to_go(process, C, current)
    v_tgt = cost_to_go(process, C, target, cell)

    if plan.status == Status.PROCEED:
        # Acting on a changeover that was not one: the robot runs the changeover plan until someone
        # notices, then has to get back to the running product. Same shape as the missed-changeover term.
        C_b, used = _after_plan(process, C, plan, params.discovery_delay)
        ra = max(0.0, max(params.discovery_delay, used) + cost_to_go(process, C_b, current) - v_cur
                 + plan.damage_prob * process.scrap_cost)
        act_allowed = True
    else:
        ra = plan.scrap_total - v_cur
        act_allowed = False

    # A missed changeover is only noticed after discovery_delay seconds whether or not the robot has
    # useful work left, so idling through that delay is itself regret (work that is zero-regret cancels).
    C_d = _next_steps(process, C, current, params.discovery_delay)
    elapsed = max(params.discovery_delay, sum(process.steps[s].forward_cost for s in C_d - C))
    rc = max(0.0, elapsed + cost_to_go(process, C_d, target, cell) - v_tgt) if not math.isinf(v_tgt) else 0.0

    hedged = hedge_window(process, C, current, target, params.confirm_window) if params.hedge else []
    filled = sum(process.steps[s].forward_cost for s in hedged)
    ca = max(0.0, params.confirm_window - filled) + params.operator_cost
    return Context(ra, rc, ca, act_allowed, tuple(hedged))


def decide(p: Sequence[float], ctx: Context, params: TriageParams = TriageParams()) -> Action:
    """Least-expected-regret action given class probabilities ``p`` (clar, edit, change, abort)."""
    if p[ABORT] >= params.p_halt:
        return Action.HALT
    live = 1.0 - p[ABORT]
    p_change = p[CHANGE] / live if live > 0 else 0.0
    cost = {
        Action.ACT: (1.0 - p_change) * ctx.act_regret if ctx.act_allowed else INF,
        Action.CONTINUE: p_change * ctx.continue_regret,
        Action.ASK: ctx.ask_regret,
    }
    return min(cost, key=lambda a: (cost[a], a.value))


def realized_regret(action: Action, truth: int, ctx: Context, params: TriageParams = TriageParams()) -> float:
    """Regret of ``action`` when the operator's true intent was ``truth``."""
    if truth == ABORT:
        return 0.0 if action == Action.HALT else INF     # anything but a stop is a safety violation
    changeover = truth == CHANGE
    if action == Action.HALT:
        return params.halt_cost
    if action == Action.ACT:
        return 0.0 if changeover else (ctx.act_regret if ctx.act_allowed else INF)
    if action == Action.CONTINUE:
        return ctx.continue_regret if changeover else 0.0
    return ctx.ask_regret


def fixed_threshold(p: Sequence[float], threshold: float, params: TriageParams = TriageParams()) -> Action:
    """The obvious baseline: act if P(changeover) clears a constant, otherwise carry on. Stops still halt."""
    if p[ABORT] >= params.p_halt:
        return Action.HALT
    live = 1.0 - p[ABORT]
    return Action.ACT if p[CHANGE] / max(live, 1e-9) >= threshold else Action.CONTINUE
