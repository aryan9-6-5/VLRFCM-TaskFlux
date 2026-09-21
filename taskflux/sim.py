"""Changeover episode simulator with the four evaluation baselines.

The simulator plays out a changeover *at the level of assembly steps*. It does
not simulate contact physics or run a VLA; per-step outcomes are drawn from
explicit, configurable probabilities, so results characterise the planning
layer under stated assumptions, not a robot. See docs/06.

Systems
  B1  stock policy, original instruction: ignores the utterance and finishes A.
  B2  stock policy, restart: clear the workpiece (scrap if anything cannot be
      undone) and build B from scratch. Current industrial practice.
  B3a LLM replanner, no reconciler: plans "B minus what is on the bench" and
      runs it on top of the existing state.
  B3b LLM replanner with an order-based diff: keeps the longest common prefix of
      the two build sequences, undoes the rest in reverse, ignores reversibility.
  TF  TaskFlux, confident changeover: reconcile, refuse or escalate, then act.
  TF-ask / TF-ask-hedge  TaskFlux when triage decides to ask first; the second
      spends the confirmation window on zero-regret steps.

Time is seconds from the end of the operator's utterance. AL is the start of the
first executed action (undo or build) of the adaptation; TTP is the start of the
first build step. Both are reported because a restart starts acting at once (by
clearing) yet does no productive work for a long time.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import FrozenSet, List, Optional, Sequence, Tuple

from .ablation import ablated_plan
from .hedge import hedge_window
from .process import Process
from .reconcile import Cell, Status, reconcile, undo_closure

SYSTEMS = ["B1", "B2", "B3a", "B3b", "TF"]


@dataclass(frozen=True)
class SimParams:
    p_forward: float = 0.92        # per-attempt success of a forward step (assumption)
    max_retries: int = 2
    p_undo_retry: float = 0.10     # chance an undo needs a second attempt (time x2)
    t_transcribe: float = 0.8      # ASR, seconds (assumption)
    t_classify: float = 0.05
    t_policy_known: float = 0.5    # switching instruction on the base policy
    t_policy_novel: float = 6.0    # adapter instantiation (assumption)
    p_forward_novel: float = 0.80  # per-attempt success under a fresh adapter
    confirm_window: float = 6.0    # ask-and-answer time
    damage_scale: float = 1.0      # multiplies each step's undo_damage; 0 makes paired comparisons deterministic


@dataclass
class Episode:
    system: str
    success: bool = False
    outcome: str = ""              # ok | wrong_product | collision | damaged | exec_failure | scrapped_ok | refused
    total_time: float = 0.0        # utterance end -> finished (or failure point)
    t_transcribe: float = 0.0
    t_reconcile: float = 0.0
    t_policy: float = 0.0
    al: Optional[float] = None     # start of first adaptation action
    ttp: Optional[float] = None    # start of first build step
    undone: List[str] = field(default_factory=list)     # steps removed one by one by a deliberate undo
    lost: List[str] = field(default_factory=list)       # steps lost when the workpiece was scrapped (planned or not)
    completed_before: int = 0
    unnecessary_undos: int = 0
    scrapped: bool = False
    hedged_steps: int = 0
    escalated: bool = False
    stage: str = ""                # truncation | undo | risky | irreversible (post-hoc label)
    failed_at: str = ""            # step id where the episode failed, if it did
    destroyed: bool = False        # a part was damaged by an undo and had to be scrapped (unplanned loss)
    damaged_at: str = ""           # step whose undo damaged the part

    @property
    def undo_actions(self) -> int:
        """Completed work that had to be redone: individual undos plus everything lost to a scrap."""
        return len(self.undone) + len(self.lost)

    @property
    def rework_cost(self) -> float:
        return self.undo_actions / self.completed_before if self.completed_before else 0.0


def change_stage(process: Process, done: FrozenSet[str], target: str) -> str:
    p = reconcile(process, done, target)
    if p.status == Status.REFUSE:
        return "refused"
    if p.status == Status.ESCALATE:
        # an irreversible step is in the way, or salvage is riskier than a restart
        return "irreversible" if any(b.kind == "irreversible" for b in p.blockers) else "risky"
    return "truncation" if not p.undo else "undo"


# ------------------------------------------------------------------ primitives
def _do_forward(process: Process, s: str, rng: random.Random, prm: SimParams, novel: bool) -> Tuple[bool, float]:
    p = prm.p_forward_novel if novel else prm.p_forward
    t = 0.0
    for _ in range(1 + prm.max_retries):
        t += process.steps[s].forward_cost
        if rng.random() < p:
            return True, t
    return False, t


def _do_undo(process: Process, s: str, rng: random.Random, prm: SimParams) -> Tuple[str, float]:
    st = process.steps[s]
    if st.irreversible:
        return "damaged", st.forward_cost   # forcing an irreversible removal takes about as long as the step did, and destroys the part
    t = st.undo_cost * (2.0 if rng.random() < prm.p_undo_retry else 1.0)
    return ("damaged" if rng.random() < st.undo_damage * prm.damage_scale else "ok"), t


def _recover(process, state, target, rng, prm, novel, t, ep) -> Tuple[str, float]:
    """A part damaged during an undo is scrapped and the target is built again from nothing."""
    ep.destroyed = ep.scrapped = True
    ep.lost.extend(sorted(x for x in state if x not in ep.lost))          # all completed work is lost
    state.clear()
    return _run(process, state, [], process.topo_order(process.goal(target)), rng, prm, novel,
                t + process.scrap_cost, ep)


def _run(process, state, undo, forward, rng, prm, novel, t, ep, physics=False,
         recover_to: Optional[str] = None) -> Tuple[str, float]:
    """Execute undos then forwards from time ``t``. Returns (status, time).

    With ``recover_to`` set, a damaged part is scrapped and that variant rebuilt instead of the episode ending.
    """
    for s in undo:
        if physics and (process.dependents[s] & state):
            ep.failed_at = s
            return "collision", t
        if ep.al is None:
            ep.al = t
        res, dt = _do_undo(process, s, rng, prm)
        t += dt
        if res != "ok":
            ep.damaged_at = s
            if recover_to is not None:
                return _recover(process, state, recover_to, rng, prm, novel, t, ep)
            ep.failed_at = s
            return "damaged", t
        state.discard(s)
        ep.undone.append(s)
    for s in forward:
        if physics and not process.ready(state, s):
            ep.failed_at = s
            return "collision", t
        if ep.al is None:
            ep.al = t
        if ep.ttp is None:
            ep.ttp = t
        ok, dt = _do_forward(process, s, rng, prm, novel)
        t += dt
        if not ok:
            ep.failed_at = s
            return "exec_failure", t
        state.add(s)
    return "ok", t


def _matches(process: Process, state: set, target: str) -> bool:
    return process.goal(target) <= state <= process.keepable(target)


def _score_unnecessary(process: Process, C: FrozenSet[str], target: str, ep: Episode) -> None:
    U, _, _ = undo_closure(process, C, target)
    ep.unnecessary_undos = len([s for s in ep.undone if s not in U])


# ------------------------------------------------------------------ the systems
def run_episode(process: Process, system: str, done: Sequence[str], current: str, target: str,
                rng: random.Random, prm: SimParams = SimParams(), novel: bool = False,
                cell: Optional[Cell] = None, ask: str = "none") -> Episode:
    """``ask`` is 'none', 'idle' or 'hedge' and only applies to TF."""
    C = frozenset(done)
    ep = Episode(system, completed_before=len(C), stage=change_stage(process, C, target))
    ep.t_transcribe = prm.t_transcribe + prm.t_classify
    ep.t_policy = prm.t_policy_novel if novel else prm.t_policy_known
    state = set(C)
    G = process.goal(target)
    t0 = ep.t_transcribe

    if system == "B1":
        st, t = _run(process, state, [], process.topo_order(process.goal(current) - C), rng, prm, False, t0, ep)
        ep.al = ep.ttp = None                       # never adapts
        ep.outcome = "ok" if (st == "ok" and _matches(process, state, target)) else ("wrong_product" if st == "ok" else st)
        ep.success, ep.total_time = ep.outcome == "ok", t
        return ep

    if system == "B2":
        t = t0
        if any(process.steps[s].irreversible for s in C):
            ep.scrapped = True
            ep.al = t
            t += process.scrap_cost
            ep.lost = list(C)                       # every completed step is lost
            state = set()
        else:
            for s in process.undo_order(C):
                if ep.al is None:
                    ep.al = t
                res, dt = _do_undo(process, s, rng, prm)
                t += dt
                if res != "ok":
                    ep.damaged_at = s
                    st, t = _recover(process, state, target, rng, prm, novel, t, ep)
                    ep.outcome = "ok" if (st == "ok" and _matches(process, state, target)) else st
                    ep.success, ep.total_time = ep.outcome == "ok", t
                    _score_unnecessary(process, C, target, ep)
                    return ep
                state.discard(s)
                ep.undone.append(s)
        t += ep.t_policy
        st, t = _run(process, state, [], process.topo_order(G), rng, prm, novel, t, ep)
        if ep.al is None:
            ep.al = ep.ttp
        _score_unnecessary(process, C, target, ep)
        ep.outcome = "ok" if (st == "ok" and _matches(process, state, target)) else st
        ep.success, ep.total_time = ep.outcome == "ok", t
        return ep

    if system == "B3a":
        t = t0 + ep.t_policy
        st, t = _run(process, state, [], process.topo_order(G - C), rng, prm, novel, t, ep, physics=True)
        ep.outcome = st if st != "ok" else ("ok" if _matches(process, state, target) else "wrong_product")
        ep.success, ep.total_time = ep.outcome == "ok", t
        return ep

    if system == "B3b":
        seqA = [s for s in process.topo_order(process.goal(current)) if s in C]
        seqB = process.topo_order(G)
        k = 0
        while k < len(seqA) and k < len(seqB) and seqA[k] == seqB[k]:
            k += 1
        keep = set(seqA[:k])
        t = t0 + ep.t_policy
        st, t = _run(process, state, list(reversed(seqA[k:])), [s for s in seqB if s not in keep],
                     rng, prm, novel, t, ep, recover_to=target)
        _score_unnecessary(process, C, target, ep)
        ep.outcome = st if st != "ok" else ("ok" if _matches(process, state, target) else "wrong_product")
        ep.success, ep.total_time = ep.outcome == "ok", t
        return ep

    # ---- TaskFlux ----
    ablation = system.split(":", 1)[1] if system.startswith("TF:") else "full"
    tic = time.perf_counter()
    plan = ablated_plan(process, C, target, ablation, cell)
    ep.t_reconcile = time.perf_counter() - tic
    t = t0 + ep.t_reconcile

    if plan.status == Status.REFUSE:
        ep.outcome, ep.total_time = "refused", t
        return ep

    if plan.status == Status.ESCALATE:
        ep.escalated = True
        ep.scrapped = True
        ep.al = t                                   # operator approves; assumed yes for measurement
        t += process.scrap_cost + ep.t_policy
        ep.lost = list(C)
        st, t = _run(process, set(), [], process.topo_order(G), rng, prm, novel, t, ep)
        ep.outcome = "scrapped_ok" if st == "ok" else st
        ep.success = ep.outcome == "scrapped_ok"
        ep.total_time = t
        return ep

    if ask != "none":
        hedged = hedge_window(process, C, current, target, prm.confirm_window) if ask == "hedge" else []
        ep.hedged_steps = len(hedged)
        window_end = t + prm.confirm_window
        for s in hedged:
            if ep.al is None:
                ep.al = t
            if ep.ttp is None:
                ep.ttp = t
            ok, dt = _do_forward(process, s, rng, prm, False)   # still the running policy
            t += dt
            if not ok:
                ep.outcome, ep.total_time = "exec_failure", t
                return ep
            state.add(s)
        t = max(t, window_end)
        plan = ablated_plan(process, state, target, ablation, cell)   # re-plan from the hedged state
    t += ep.t_policy
    # physics=True: a plan is only worth what it does to the real workpiece, so an unsound plan collides
    st, t = _run(process, state, plan.undo, plan.forward, rng, prm, novel, t, ep, physics=True, recover_to=target)
    ep.outcome = st if st != "ok" else ("ok" if _matches(process, state, target) else "wrong_product")
    ep.success, ep.total_time = ep.outcome == "ok", t
    _score_unnecessary(process, C, target, ep)
    return ep


def no_change_episode(process: Process, done: Sequence[str], current: str, rng: random.Random,
                      prm: SimParams = SimParams(), ask: str = "none", target: str = "B") -> Episode:
    """The operator did not change anything: time to finish ``current`` under each triage response.

    ask='none': keep going. ask='idle': pause for the confirmation window.
    ask='hedge': work on zero-regret steps during the window, then continue.
    """
    C = frozenset(done)
    ep = Episode("no-change/" + ask, completed_before=len(C))
    state = set(C)
    t = prm.t_transcribe + prm.t_classify
    if ask != "none":
        window_end = t + prm.confirm_window
        if ask == "hedge":
            for s in hedge_window(process, C, current, target, prm.confirm_window):
                ok, dt = _do_forward(process, s, rng, prm, False)
                t += dt
                if not ok:
                    ep.outcome, ep.total_time = "exec_failure", t
                    return ep
                state.add(s)
                ep.hedged_steps += 1
        t = max(t, window_end)
    st, t = _run(process, state, [], process.topo_order(process.goal(current) - state), rng, prm, False, t, ep)
    ep.outcome = "ok" if st == "ok" else st
    ep.success, ep.total_time = st == "ok", t
    return ep


def false_change_episode(process: Process, done: Sequence[str], current: str, target: str,
                         rng: random.Random, prm: SimParams = SimParams(), delay: float = 60.0,
                         cell: Optional[Cell] = None) -> Episode:
    """The system acted on a changeover that was not one. It runs the changeover plan until the
    operator objects ``delay`` seconds later, then gets back to finishing the running product."""
    C = frozenset(done)
    ep = Episode("false-change", completed_before=len(C))
    plan = reconcile(process, C, target, cell)
    state = set(C)
    t = prm.t_transcribe + prm.t_classify
    started, budget_used = t, 0.0
    for kind, seq in (("undo", plan.undo), ("do", plan.forward)):
        for s in seq:
            if budget_used >= delay:
                break
            if kind == "undo":
                res, dt = _do_undo(process, s, rng, prm)
                if res != "ok":
                    ep.damaged_at = s
                    ep.destroyed = ep.scrapped = True
                    state = set()
                    t += budget_used + dt + process.scrap_cost
                    back = reconcile(process, state, current, cell)
                    st, t = _run(process, state, back.undo, back.forward, rng, prm, False, t, ep)
                    ep.outcome, ep.success, ep.total_time = st, st == "ok", t
                    return ep
                state.discard(s)
            else:
                ok, dt = _do_forward(process, s, rng, prm, False)
                if not ok:
                    ep.outcome, ep.total_time = "exec_failure", t + budget_used + dt
                    return ep
                state.add(s)
            budget_used += dt
    t += max(budget_used, delay)
    back = reconcile(process, state, current, cell)
    if back.status == Status.ESCALATE:
        # an irreversible step of the wrong product went on before anyone objected: scrap and rebuild
        ep.scrapped = True
        t += process.scrap_cost
        state = set()
        back = reconcile(process, state, current, cell)
    st, t = _run(process, state, back.undo, back.forward, rng, prm, False, t, ep)
    ep.outcome, ep.success, ep.total_time = st, st == "ok", t
    return ep


def delayed_change_episode(process: Process, done: Sequence[str], current: str, target: str,
                           rng: random.Random, prm: SimParams = SimParams(), delay: float = 60.0,
                           cell: Optional[Cell] = None) -> Episode:
    """The system ignored a real changeover and kept building ``current`` for ``delay`` seconds
    before anyone noticed; then TaskFlux reconciles from wherever the build had got to."""
    C = frozenset(done)
    state = set(C)
    t = prm.t_transcribe + prm.t_classify
    ignore = Episode("ignored", completed_before=len(C))
    spent = 0.0
    for s in process.topo_order(process.goal(current) - C):
        if spent >= delay:
            break
        ok, dt = _do_forward(process, s, rng, prm, False)
        spent += dt
        if not ok:
            ignore.outcome, ignore.total_time = "exec_failure", t + spent
            return ignore
        state.add(s)
    ep = run_episode(process, "TF", sorted(state), current, target, rng, prm, cell=cell)
    ep.total_time += t + max(spent, delay)      # nobody notices before ``delay`` even if the robot ran out of work
    return ep
