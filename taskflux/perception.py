"""Perception uncertainty: what the reconciler does when the state it is given may be wrong.

The reconciler needs the set of completed steps. On a real cell that comes from a step-completion
verifier (a vision model, since OpenVLA has no termination signal), and it will sometimes be wrong:
a finished step seen as missing, or an unfinished one seen as done.

Precedence and physics give a cheap error detector for free. A step seen done whose prerequisites are
not seen done is impossible, and so is a set of steps whose ordering constraints contradict each other
(no build order could have produced it). Either way the observation is inconsistent and something in it
is wrong. This does not
catch every error (a wrongly missed *last* step, or a wrongly added step whose prerequisites are
done, look perfectly plausible), so it is measured, not assumed.

Policies for acting on a noisy observation:

  trust           use the observation; if it is impossible, assume prerequisites are done
  consistency     re-inspect exactly the steps a violated precedence points at
  inspect_undo    consistency, plus re-inspect every step about to be undone before undoing it
                  (an undo is the costly, sometimes destructive action)
  inspect_critical  consistency, plus re-inspect every step whose status, if it were the other way,
                  would change the plan (value of information); repeat until none is left
  inspect_all     re-inspect every step of either variant (upper bound on cost, lower bound on error)
  oracle          the true state, free (reference)
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import FrozenSet, List, Optional, Set, Tuple

from .process import Process
from .reconcile import Cell, Status, reconcile
from .sim import Episode, SimParams, _do_forward, _do_undo, _matches, _recover, change_stage

POLICIES = ["oracle", "trust", "consistency", "inspect_undo", "inspect_critical", "inspect_all"]


@dataclass(frozen=True)
class NoiseParams:
    p_miss: float = 0.05     # a completed step is observed as not done
    p_false: float = 0.05    # a step that is not done is observed as done
    t_inspect: float = 6.0   # seconds to inspect one step closely; the inspection is exact


@dataclass
class NoisyResult:
    episode: Episode
    inspections: int
    had_error: bool          # the first observation differed from the truth
    flagged: bool            # the consistency check noticed


def observe(process: Process, truth: FrozenSet[str], noise: NoiseParams, rng: random.Random) -> FrozenSet[str]:
    obs: Set[str] = set()
    for s in process.order:
        if s in truth:
            if rng.random() >= noise.p_miss:
                obs.add(s)
        elif rng.random() < noise.p_false:
            obs.add(s)
    return frozenset(obs)


def inconsistent_steps(process: Process, obs: FrozenSet[str]) -> Set[str]:
    """Steps an impossible observation points at.

    Two kinds of impossibility: a step seen done whose prerequisites are not (implicates the step and what is
    missing), and a set of steps whose ordering constraints contradict each other, so no build order could have
    produced them (implicates the steps caught in the cycle).
    """
    out: Set[str] = set()
    for s in obs:
        missing = process.steps[s].requires - obs
        if missing:
            out.add(s)
            out |= missing
    out |= process.cycle_core(obs)
    return out


def close_downward(process: Process, obs: FrozenSet[str]) -> FrozenSet[str]:
    """Naive repair of a missing prerequisite: a step seen done implies its prerequisites are done."""
    out = set(obs)
    stack = list(obs)
    while stack:
        s = stack.pop()
        for r in process.steps[s].requires:
            if r not in out:
                out.add(r)
                stack.append(r)
    return frozenset(out)


def _repair(process: Process, belief: FrozenSet[str]) -> FrozenSet[str]:
    """Naive fallback when a belief is impossible: fill in missing prerequisites, and if the ordering
    constraints still contradict, drop the latest step in the cycle and everything built on it."""
    b = set(belief)
    for _ in range(len(process.steps) + 1):
        if not process.requires_closed(b):
            b = set(close_downward(process, frozenset(b)))
            continue
        core = process.cycle_core(b)
        if not core:
            return frozenset(b)
        drop = max(core, key=process.index.__getitem__)
        gone = {drop}
        grew = True
        while grew:
            grew = False
            for x in list(b):
                if x not in gone and process.steps[x].requires & gone:
                    gone.add(x)
                    grew = True
        b -= gone
    return frozenset(b)


def _signature(plan) -> tuple:
    return (plan.status, plan.undo, plan.forward)


def critical_steps(process: Process, belief: Set[str], target: str, cell: Optional[Cell],
                   universe: List[str], skip: Set[str]) -> List[str]:
    """Steps whose belief, if wrong, would change what the reconciler does. Impossible flips are ignored."""
    base = _signature(reconcile(process, frozenset(belief), target, cell))
    out = []
    for s in universe:
        if s in skip:
            continue
        flipped = set(belief) ^ {s}
        if not process.is_valid_state(flipped):
            continue
        if _signature(reconcile(process, frozenset(flipped), target, cell)) != base:
            out.append(s)
    return out


def run_noisy_episode(process: Process, policy: str, truth: FrozenSet[str], current: str, target: str,
                      rng: random.Random, prm: SimParams = SimParams(), noise: NoiseParams = NoiseParams(),
                      cell: Optional[Cell] = None) -> NoisyResult:
    ep = Episode("noisy/" + policy, completed_before=len(truth), stage=change_stage(process, truth, target))
    ep.t_transcribe = prm.t_transcribe + prm.t_classify
    ep.t_policy = prm.t_policy_known
    t = ep.t_transcribe
    inspections = 0
    inspected: Set[str] = set()
    universe = sorted(process.goal(current) | process.goal(target), key=process.index.__getitem__)

    def inspect(belief: Set[str], steps) -> Set[str]:
        nonlocal t, inspections
        for s in steps:
            if s in inspected:
                continue
            inspected.add(s)
            inspections += 1
            t += noise.t_inspect
            (belief.add if s in truth else belief.discard)(s)
        return belief

    obs = truth if policy == "oracle" else observe(process, truth, noise, rng)
    had_error = obs != truth
    flagged_set = inconsistent_steps(process, obs)
    belief: Set[str] = set(obs)

    if policy == "inspect_all":
        belief = inspect(belief, universe)
    elif policy in ("consistency", "inspect_undo"):
        belief = inspect(belief, sorted(flagged_set, key=process.index.__getitem__))
    belief = set(_repair(process, frozenset(belief)))

    plan = reconcile(process, belief, target, cell)
    if policy == "inspect_undo":
        for _ in range(len(process.steps)):
            if plan.status != Status.PROCEED:
                break
            fresh = [s for s in plan.undo if s not in inspected]
            if not fresh:
                break
            belief = inspect(belief, fresh)
            belief = set(_repair(process, frozenset(belief)))
            plan = reconcile(process, belief, target, cell)

    if policy == "inspect_critical":
        for _ in range(len(process.steps)):
            if plan.status == Status.REFUSE:
                break
            fresh = critical_steps(process, belief, target, cell, universe, inspected)
            if not fresh:
                break
            belief = inspect(belief, fresh)
            belief = set(_repair(process, frozenset(belief)))
            plan = reconcile(process, belief, target, cell)

    def finish(st: str, tt: float, state: Set[str]) -> NoisyResult:
        ep.outcome = st if st != "ok" else ("ok" if _matches(process, state, target) else "wrong_product")
        ep.success, ep.total_time = ep.outcome == "ok", tt
        return NoisyResult(ep, inspections, had_error, bool(flagged_set))

    state = set(truth)
    if plan.status == Status.REFUSE:
        ep.outcome, ep.total_time = "refused", t
        return NoisyResult(ep, inspections, had_error, bool(flagged_set))
    if plan.status == Status.ESCALATE:
        ep.escalated = ep.scrapped = True                      # scrapping is safe whatever is really on the bench
        t += process.scrap_cost + ep.t_policy
        state = set()
        for s in process.topo_order(process.goal(target)):
            ok, dt = _do_forward(process, s, rng, prm, False)
            t += dt
            if not ok:
                ep.failed_at = s
                return finish("exec_failure", t, state)
            state.add(s)
        return finish("ok", t, state)

    t += ep.t_policy
    # Execute against the TRUE workpiece. A plan built on a wrong belief meets physics.
    for s in plan.undo:
        if s not in state:
            t += 0.3 * process.steps[s].undo_cost              # tried to remove something that is not there
            continue
        if process.dependents[s] & state:
            ep.failed_at = s
            return finish("collision", t, state)
        res, dt = _do_undo(process, s, rng, prm)
        t += dt
        if res != "ok":
            ep.damaged_at = s
            st, t = _recover(process, state, target, rng, prm, False, t, ep)
            return finish(st, t, state)
        state.discard(s)
        ep.undone.append(s)
    for s in plan.forward:
        if s in state or not process.ready(state, s):          # duplicate, missing prerequisite, or blocked
            ep.failed_at = s
            return finish("collision", t, state)
        ok, dt = _do_forward(process, s, rng, prm, False)
        t += dt
        if not ok:
            ep.failed_at = s
            return finish("exec_failure", t, state)
        state.add(s)
    return finish("ok", t, state)
