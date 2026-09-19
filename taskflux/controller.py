"""TaskFlux controller: the layer that sits above a step-level VLA policy.

Owns the workpiece state (which steps are done), the running plan, and the
operator dialogue. Feed it utterances with ``hear`` and step completions with
``complete``; it answers with what the robot should do and what to say.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np

from .hedge import safe_steps
from .process import Process
from .reconcile import Cell, Plan, Status, reconcile
from .triage import ABORT, CHANGE, Action, TriageParams, build_context, decide
from .utterances import IntentClassifier, lexical_stop

PRIOR = np.array([0.35, 0.35, 0.22, 0.08])      # deployment prior over clar / edit / change / abort


@dataclass
class Response:
    action: Action
    say: str
    plan: Optional[Plan] = None
    hedged: Sequence[str] = ()
    probs: Optional[np.ndarray] = None


@dataclass
class Controller:
    process: Process
    current: str
    target: str
    classifier: IntentClassifier
    cell: Optional[Cell] = None
    params: TriageParams = field(default_factory=TriageParams)
    done: set = field(default_factory=set)
    queue: List[tuple] = field(default_factory=list)          # ("do" | "undo", step id)
    pending_change: bool = False
    halted: bool = False

    def __post_init__(self) -> None:
        if not self.queue:
            self.queue = [("do", s) for s in self.process.topo_order(self.process.goal(self.current) - self.done)]

    # ---------------------------------------------------------------- execution
    def next_action(self) -> Optional[tuple]:
        if self.halted:
            return None
        if self.pending_change:                    # waiting for the operator: only zero-regret steps
            s = next(iter(safe_steps(self.process, self.done, self.current, self.target)), None)
            return ("do", s) if s else None
        return self.queue[0] if self.queue else None

    def complete(self, kind: str, sid: str) -> None:
        if kind == "do":
            self.done.add(sid)
        else:
            self.done.discard(sid)
        if (kind, sid) in self.queue:
            self.queue.remove((kind, sid))

    # ---------------------------------------------------------------- language
    def probs(self, text: str) -> np.ndarray:
        p = self.classifier.proba([text])[0] * (PRIOR / 0.25)
        p = p / p.sum()
        if lexical_stop(text):
            p = np.array([0.0, 0.0, 0.0, 1.0])
        return p

    def hear(self, text: str) -> Response:
        p = self.probs(text)
        ctx = build_context(self.process, self.done, self.current, self.target, self.params, self.cell)
        act = decide(p, ctx, self.params)
        if act == Action.ACT and not ctx.act_allowed:
            act = Action.ASK
        L = self.process.label
        if act == Action.HALT:
            self.halted = True
            return Response(act, "Stopped. Say 'resume' when it is clear.", probs=p)
        if act == Action.CONTINUE:
            return Response(act, "Okay, carrying on with the current build.", probs=p)
        plan = reconcile(self.process, self.done, self.target, self.cell)
        if act == Action.ACT:
            self._adopt(plan)
            return Response(act, plan.explanation, plan, probs=p)
        self.pending_change = True
        hedged = list(ctx.hedged)
        extra = (" Meanwhile I will keep going with "
                 + ", ".join(f"'{L(s)}'" for s in hedged) + ", which is needed either way.") if hedged else ""
        return Response(act, f"Do you want me to switch to {self.target}? {plan.explanation}{extra}", plan, hedged, p)

    def answer(self, yes: bool) -> Response:
        self.pending_change = False
        plan = reconcile(self.process, self.done, self.target, self.cell)
        if not yes:
            return Response(Action.CONTINUE, "Understood, staying with the current build.")
        if plan.status == Status.REFUSE:
            return Response(Action.HALT, plan.explanation, plan)
        if plan.status == Status.ESCALATE:
            self.done.clear()                       # operator approved scrapping: fresh workpiece
            plan = reconcile(self.process, self.done, self.target, self.cell)
            self._adopt(plan)
            return Response(Action.ACT, "Scrapping this workpiece and starting a fresh " + self.target + ".", plan)
        self._adopt(plan)
        return Response(Action.ACT, plan.explanation, plan)

    def _adopt(self, plan: Plan) -> None:
        self.current = plan.target
        self.queue = [("undo", s) for s in plan.undo] + [("do", s) for s in plan.forward]
