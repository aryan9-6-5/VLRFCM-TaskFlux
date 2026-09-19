"""Assembly process model.

A *process* is a universe of steps shared by every product variant the cell
can build. Each step records what it physically needs and what it costs to do
and to undo. A *variant* names the steps that make up one product.

Two physical relations, both variant independent:

* ``requires``: steps that must be present before this step can be done.
  Removing a step therefore forces removal of everything that requires it.
* ``covered_by``: steps that, once present, block access to this step. A step
  can only be done or undone while everything in ``covered_by`` is absent.
  A cover is therefore an undo-dependent of what it covers, and when both are
  needed the covered step has to come first.

Reversibility is hand authored (``irreversible``), which is the assumption the
docs call out as a limitation. Times are seconds.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cached_property
from typing import Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence

INF = math.inf


@dataclass(frozen=True)
class Step:
    id: str
    label: str
    forward_cost: float = 10.0
    undo_cost: float = 10.0
    irreversible: bool = False
    undo_damage: float = 0.0  # probability the workpiece is damaged while undoing
    requires: FrozenSet[str] = frozenset()
    covered_by: FrozenSet[str] = frozenset()
    tool: Optional[str] = None
    irreversible_reason: str = ""

    def __post_init__(self) -> None:
        if self.irreversible and not math.isinf(self.undo_cost):
            object.__setattr__(self, "undo_cost", INF)


@dataclass(frozen=True)
class Variant:
    name: str
    required: FrozenSet[str]
    tolerated: FrozenSet[str] = frozenset()  # extras that are harmless to leave in place


class ProcessError(ValueError):
    pass


class Process:
    def __init__(self, steps: Sequence[Step], variants: Sequence[Variant], scrap_cost: float = 120.0):
        self.order: List[str] = [s.id for s in steps]
        self.index: Dict[str, int] = {sid: i for i, sid in enumerate(self.order)}
        self.steps: Dict[str, Step] = {s.id: s for s in steps}
        if len(self.steps) != len(steps):
            raise ProcessError("duplicate step ids")
        self.variants: Dict[str, Variant] = {v.name: v for v in variants}
        self.scrap_cost = scrap_cost
        self._validate()

    # ---------- derived relations ----------
    @cached_property
    def dependents(self) -> Dict[str, FrozenSet[str]]:
        """D(s): steps that must be gone before s can be undone."""
        d: Dict[str, set] = {sid: set(self.steps[sid].covered_by) for sid in self.steps}
        for u, st in self.steps.items():
            for s in st.requires:
                d[s].add(u)
        return {k: frozenset(v) for k, v in d.items()}

    def goal(self, variant: str) -> FrozenSet[str]:
        return self.variants[variant].required

    def keepable(self, variant: str) -> FrozenSet[str]:
        v = self.variants[variant]
        return v.required | v.tolerated

    # ---------- state checks ----------
    def is_valid_state(self, done: Iterable[str]) -> bool:
        s = set(done)
        return all(self.steps[x].requires <= s for x in s)

    def ready(self, done: Iterable[str], step: str) -> bool:
        d = set(done)
        st = self.steps[step]
        return step not in d and st.requires <= d and not (st.covered_by & d)

    # ---------- ordering ----------
    def topo_order(self, subset: Iterable[str]) -> List[str]:
        """Order ``subset`` so requires-edges and cover-edges are respected."""
        nodes = set(subset)
        succ: Dict[str, set] = {n: set() for n in nodes}
        indeg: Dict[str, int] = {n: 0 for n in nodes}

        def edge(a: str, b: str) -> None:
            if a in nodes and b in nodes and b not in succ[a]:
                succ[a].add(b)
                indeg[b] += 1

        for n in nodes:
            st = self.steps[n]
            for r in st.requires:
                edge(r, n)  # required step first
            for c in st.covered_by:
                edge(n, c)  # covered step before its cover
        ready = sorted((n for n in nodes if indeg[n] == 0), key=self.index.__getitem__)
        out: List[str] = []
        while ready:
            n = ready.pop(0)
            out.append(n)
            for m in sorted(succ[n], key=self.index.__getitem__):
                indeg[m] -= 1
                if indeg[m] == 0:
                    ready.append(m)
            ready.sort(key=self.index.__getitem__)
        if len(out) != len(nodes):
            raise ProcessError("ordering constraints are cyclic")
        return out

    def undo_order(self, subset: Iterable[str]) -> List[str]:
        """Reverse of a valid build order: dependents come off first."""
        nodes = set(subset)
        # Build order for the union of what is present is not needed; we only
        # need dependents before dependees, using the D relation restricted to subset.
        remaining = set(nodes)
        out: List[str] = []
        while remaining:
            free = sorted(
                (s for s in remaining if not (self.dependents[s] & remaining)),
                key=lambda s: -self.index[s],
            )
            if not free:
                raise ProcessError("undo dependencies are cyclic")
            s = free[0]
            out.append(s)
            remaining.discard(s)
        return out

    # ---------- validation ----------
    def _validate(self) -> None:
        for st in self.steps.values():
            for ref in st.requires | st.covered_by:
                if ref not in self.steps:
                    raise ProcessError(f"{st.id} references unknown step {ref}")
            if not 0.0 <= st.undo_damage <= 1.0:
                raise ProcessError(f"{st.id}: undo_damage must be a probability")
        self._check_requires_acyclic()
        for v in self.variants.values():
            if not (v.required | v.tolerated) <= set(self.steps):
                raise ProcessError(f"variant {v.name} references unknown steps")
            if v.required & v.tolerated:
                raise ProcessError(f"variant {v.name}: tolerated overlaps required")
            for s in v.required:
                if not self.steps[s].requires <= v.required:
                    raise ProcessError(f"variant {v.name}: {s} requires steps outside the variant")
            self.topo_order(v.required)

    def _check_requires_acyclic(self) -> None:
        state: Dict[str, int] = {}

        def visit(n: str) -> None:
            if state.get(n) == 2:
                return
            if state.get(n) == 1:
                raise ProcessError(f"requires cycle through {n}")
            state[n] = 1
            for r in self.steps[n].requires:
                visit(r)
            state[n] = 2

        for n in self.steps:
            visit(n)

    def label(self, sid: str) -> str:
        return self.steps[sid].label
