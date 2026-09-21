"""Partial-assembly state reconciliation.

Given the set ``C`` of completed steps and a new target variant with required
steps ``G`` and tolerated extras ``H``, decide what to keep, undo, or leave.

Forced roots (steps that cannot stay):
  1. completed steps outside ``G | H`` (they belong to the withdrawn product),
  2. completed steps that cover a step of ``G`` that is not done yet
     (the cover has to come off before the covered step can be done).

The undo set is the closure of the roots under ``dependents``: to remove a
step, everything requiring it or covering it has to come off first.

Optimality (see docs/05-novelty-and-formal-results.md, Lemma 1). Every
feasible plan has an undo set that contains this closure, and the closure
itself is a feasible undo set. It is therefore the unique minimum, and it is
optimal for *every* cost model in which undoing a step costs a non-negative
amount, with no tuning. What is left to decide is only the salvage-versus-
scrap question when irreversible steps are in the way or damage risk is high.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, Iterable, List, Optional, Tuple

from .geometry import Workcell
from .process import INF, Process


class Status(str, Enum):
    PROCEED = "proceed"      # salvage plan is feasible and cheapest
    ESCALATE = "escalate"    # operator must approve scrap-and-restart
    REFUSE = "refuse"        # target cannot be built in this cell


@dataclass(frozen=True)
class Cell:
    """What the workcell can currently do."""
    tools: FrozenSet[str] = frozenset()
    workcell: Optional[Workcell] = None      # reach and human safety zones, if the cell has them


@dataclass(frozen=True)
class Blocker:
    kind: str                      # "irreversible" | "tool" | "reach" | "zone"
    step: str                      # the step that blocks
    chain: Tuple[str, ...] = ()    # forced root ... blocking step, in removal-dependency order
    root_reason: str = ""


@dataclass
class Plan:
    status: Status
    target: str
    keep: FrozenSet[str]
    undo: Tuple[str, ...]              # ordered, dependents first
    discard: FrozenSet[str]            # tolerated extras left in place
    forward: Tuple[str, ...]           # ordered
    undo_time: float
    forward_time: float
    damage_prob: float
    salvage_cost: float                # expected, includes damage risk; inf if infeasible
    scrap_total: float                 # scrap the workpiece and build target from scratch
    blockers: List[Blocker] = field(default_factory=list)
    explanation: str = ""

    @property
    def cost(self) -> float:
        """Expected cost-to-go under the recommended course of action."""
        if self.status == Status.PROCEED:
            return self.salvage_cost
        if self.status == Status.ESCALATE:
            return self.scrap_total
        return INF


def undo_closure(process: Process, done: Iterable[str], target: str
                 ) -> Tuple[FrozenSet[str], Dict[str, Tuple[str, Optional[str]]], Dict[str, Optional[str]]]:
    """Minimum undo set, its forced roots with reasons, and cascade parents."""
    C = frozenset(done)
    allowed = process.keepable(target)
    pending = process.goal(target) - C
    roots: Dict[str, Tuple[str, Optional[str]]] = {}
    for s in C:
        if s not in allowed:
            roots[s] = ("not_in_goal", None)
    for g in pending:
        for u in process.steps[g].covered_by & C:
            roots.setdefault(u, ("covers", g))
    parent: Dict[str, Optional[str]] = {s: None for s in roots}
    stack = list(roots)
    while stack:
        r = stack.pop()
        for d in process.dependents[r] & C:
            if d not in parent:
                parent[d] = r
                stack.append(d)
    return frozenset(parent), roots, parent


def _chain(parent: Dict[str, Optional[str]], node: str) -> Tuple[str, ...]:
    out = [node]
    while parent[out[-1]] is not None:
        out.append(parent[out[-1]])  # type: ignore[arg-type]
    return tuple(reversed(out))  # root first, blocker last


def reconcile(process: Process, done: Iterable[str], target: str,
              cell: Optional[Cell] = None, allow_scrap: bool = True) -> Plan:
    C = frozenset(done)
    if not process.is_valid_state(C):
        raise ValueError("completed set is impossible: a step lacks a prerequisite, or no build order can produce it")
    G = process.goal(target)
    U, roots, parent = undo_closure(process, C, target)
    K = C - U
    N = G - K
    forward = tuple(process.topo_order(N))
    undo = tuple(process.undo_order(U))
    discard = frozenset(K - G)

    undo_time = sum(process.steps[s].undo_cost for s in U)
    forward_time = sum(process.steps[s].forward_cost for s in N)
    survive = 1.0
    for s in U:
        survive *= 1.0 - process.steps[s].undo_damage
    damage = 1.0 - survive
    scrap_pen = process.scrap_cost if C else 0.0
    forward_all = sum(process.steps[s].forward_cost for s in G)
    scrap_total = scrap_pen + forward_all

    blockers: List[Blocker] = []
    for s in sorted(U, key=process.index.__getitem__):
        if process.steps[s].irreversible:
            ch = _chain(parent, s)
            blockers.append(Blocker("irreversible", s, ch, roots[ch[0]][0]))
    if cell is not None:
        for s in N:
            tool = process.steps[s].tool
            if tool is not None and tool not in cell.tools:
                blockers.append(Blocker("tool", s, (s,), tool))
        wc = cell.workcell
        if wc is not None:
            for s in sorted(set(N) | set(U), key=process.index.__getitem__):   # building and undoing both need the arm there
                pos = process.steps[s].pos
                if pos is None:
                    continue
                zone = wc.zone_of(pos)
                if zone is not None:
                    blockers.append(Blocker("zone", s, (s,), zone.name))
                elif not wc.reachable(pos):
                    blockers.append(Blocker("reach", s, (s,), ""))

    # If an undo damages the part it is scrapped and the target rebuilt from nothing, which replaces
    # the planned forward work with the full build: a damage event costs the scrap fee plus the difference.
    salvage_cost = INF if any(b.kind == "irreversible" for b in blockers) else (
        undo_time + forward_time + damage * (process.scrap_cost + forward_all - forward_time))

    if any(b.kind in ("tool", "zone", "reach") for b in blockers):
        status = Status.REFUSE
    elif any(b.kind == "irreversible" for b in blockers):
        status = Status.ESCALATE if allow_scrap else Status.REFUSE
    elif salvage_cost <= scrap_total:
        status = Status.PROCEED
    else:
        status = Status.ESCALATE if allow_scrap else Status.PROCEED

    plan = Plan(status, target, K & G, undo, discard, forward, undo_time, forward_time,
                damage, salvage_cost, scrap_total, blockers)
    plan.explanation = explain(process, plan, roots, done_count=len(C))
    return plan


def _steps(n: int) -> str:
    return f"{n} step" if n == 1 else f"{n} steps"


def explain(process: Process, plan: Plan, roots: Dict[str, Tuple[str, Optional[str]]], done_count: int) -> str:
    L = process.label
    tgt = plan.target
    tool_b = [b for b in plan.blockers if b.kind == "tool"]
    irr_b = [b for b in plan.blockers if b.kind == "irreversible"]
    zone_b = [b for b in plan.blockers if b.kind == "zone"]
    reach_b = [b for b in plan.blockers if b.kind == "reach"]
    if zone_b:
        b = zone_b[0]
        return (f"I cannot switch to {tgt}: '{L(b.step)}' is inside the human safety zone '{b.root_reason}'. "
                f"Please clear the zone or move the part.")
    if reach_b:
        b = reach_b[0]
        return f"I cannot switch to {tgt}: '{L(b.step)}' is outside the arm's reach from where it is mounted."
    if tool_b:
        b = tool_b[0]
        return (f"I cannot build {tgt}: the step '{L(b.step)}' needs {b.root_reason}, "
                f"which is not available in this cell.")
    if irr_b:
        b = irr_b[0]
        root, why = b.chain[0], roots[b.chain[0]]
        if why[0] == "not_in_goal":
            need = f"'{L(root)}' does not belong to {tgt}"
        else:
            need = f"'{L(root)}' blocks '{L(why[1])}', which {tgt} needs"
        reason = process.steps[b.step].irreversible_reason or "it cannot be undone"
        path = "" if len(b.chain) == 1 else (
            " To get there I would first have to remove " + ", then ".join(f"'{L(s)}'" for s in reversed(b.chain[1:])) + ".")
        blocked = "it" if len(b.chain) == 1 else f"'{L(b.step)}'"
        return (f"I can only switch to {tgt} by scrapping this workpiece: {need}, so it has to come off, "
                f"but {blocked} cannot be removed ({reason}).{path} "
                f"Options: scrap and restart (about {plan.scrap_total:.0f} s), or finish the current product.")
    if plan.status == Status.ESCALATE:
        return (f"Switching to {tgt} is possible but removing {len(plan.undo)} steps risks damaging the part "
                f"(about {plan.damage_prob:.0%}). Restarting from a fresh workpiece is cheaper in expectation "
                f"({plan.scrap_total:.0f} s versus {plan.salvage_cost:.0f} s). Please confirm.")
    if not plan.undo:
        extra = f" and leaving {_steps(len(plan.discard))} in place because they are harmless" if plan.discard else ""
        return (f"Switching to {tgt}: keeping {_steps(len(plan.keep))}{extra}. Nothing has to come off, "
                f"and {_steps(len(plan.forward))} remain.")
    return (f"Switching to {tgt}: keeping {_steps(len(plan.keep))}, taking off {_steps(len(plan.undo))} "
            f"({', '.join(L(s) for s in plan.undo)}), then building {_steps(len(plan.forward))}.")


def cost_to_go(process: Process, done: Iterable[str], target: str, cell: Optional[Cell] = None) -> float:
    """Expected remaining cost of reaching ``target`` from ``done``.

    Includes the scrap path, so it is finite whenever the target is buildable.
    """
    p = reconcile(process, done, target, cell)
    if p.status == Status.REFUSE:
        return INF
    return min(p.salvage_cost, p.scrap_total)
