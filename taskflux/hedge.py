"""Hedged execution: keep working while the operator's intent is unconfirmed.

A ready step ``s`` of the *current* plan is **safe** with respect to a
hypothesised target ``T`` when all of these hold:

    reconcile(done, T) is a salvage plan (not a scrap or a refusal)
    undoing U*(done, T) cannot damage the part (otherwise a scrap would waste s)
    s is required by T (not merely tolerated)
    U*(done + s, T) == U*(done, T)     the undo set under T does not grow
    s not in U*(done + s, T)           s is not itself thrown away under T

Under "no change" the step is just the next step of the running plan, so it is
not wasted. Under "changeover" the step stays in the assembly and is now
finished, so the remaining cost falls by exactly ``forward_cost(s)``.
Either way there is zero regret (checked exhaustively in tests/test_hedge.py),
so the robot can spend the confirmation window building instead of idling. The abort hypothesis is excluded on
purpose: a possible stop request always halts motion (safety first).
"""
from __future__ import annotations

from typing import FrozenSet, Iterable, List

from .process import Process
from .reconcile import Status, reconcile, undo_closure


def safe_steps(process: Process, done: Iterable[str], current: str, hypothesis: str) -> List[str]:
    """Ready steps of ``current`` that are zero-regret under ``hypothesis``, in build order."""
    C = frozenset(done)
    # If the hypothesis would end in a scrap or refusal, work done now is wasted
    # under that hypothesis, so nothing is zero-regret.
    plan = reconcile(process, C, hypothesis)
    if plan.status != Status.PROCEED:
        return []
    if plan.damage_prob > 0:
        # If an undo can damage the part, the part is scrapped and rebuilt from nothing, and a step
        # built in the meantime is lost with it: expected regret d * forward_cost(s), not zero.
        return []
    G_hyp = process.goal(hypothesis)
    pending = process.goal(current) - C
    covered_pending = {u for g in pending for u in process.steps[g].covered_by}
    base_U, _, _ = undo_closure(process, C, hypothesis)
    out: List[str] = []
    for s in process.topo_order(pending):
        if s not in G_hyp or not process.ready(C, s):
            continue  # a merely tolerated step would still be wasted time if the hypothesis holds
        if s in covered_pending:
            continue  # the running plan itself needs a step done before this one covers it
        U, _, _ = undo_closure(process, C | {s}, hypothesis)
        if U == base_U and s not in U:
            out.append(s)
    return out


def hedge_window(process: Process, done: Iterable[str], current: str, hypothesis: str,
                 window: float) -> List[str]:
    """Greedily execute safe steps for up to ``window`` seconds; return those started.

    Safety is re-evaluated after every step because finishing one step can make
    another safe (or stop it being safe).
    """
    C = set(done)
    started: List[str] = []
    t = 0.0
    while t < window:
        cands = safe_steps(process, C, current, hypothesis)
        if not cands:
            break
        s = cands[0]
        started.append(s)
        C.add(s)
        t += process.steps[s].forward_cost
    return started
