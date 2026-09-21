"""Ablated reconcilers, for measuring what each rule in the reconciler is worth.

Each name removes one rule and leaves the rest intact:

  full             the reconciler as shipped
  no_refusal       never escalates on an irreversible undo; it attempts the removal anyway
  no_scrap_choice  never compares salvage against scrap on damage risk; salvages whenever possible
  no_cascade       undoes only the forced roots, not the steps stacked on them
  no_cover_rule    ignores that a present cover blocks a step that still has to be built
  no_tolerated     treats every extra step of the old variant as something to remove
"""
from __future__ import annotations

from dataclasses import replace
from typing import Dict, Iterable, Optional, Tuple

from .process import Process, Variant
from .reconcile import Cell, Plan, Status, reconcile, undo_closure

ABLATIONS = ["full", "no_refusal", "no_scrap_choice", "no_cascade", "no_cover_rule", "no_tolerated"]

_cache: Dict[Tuple[int, str], Process] = {}


def _variant_copy(process: Process, name: str) -> Process:
    key = (id(process), name)
    if key in _cache:
        return _cache[key]
    steps = [process.steps[s] for s in process.order]
    variants = list(process.variants.values())
    if name == "no_cover_rule":
        steps = [replace(s, covered_by=frozenset()) for s in steps]
    elif name == "no_tolerated":
        variants = [Variant(v.name, v.required, frozenset()) for v in variants]
    q = Process(steps, variants, scrap_cost=process.scrap_cost)
    _cache[key] = q
    return q


def ablated_plan(process: Process, done: Iterable[str], target: str, name: str,
                 cell: Optional[Cell] = None) -> Plan:
    C = frozenset(done)
    if name == "full":
        return reconcile(process, C, target, cell)
    if name == "no_refusal":
        p = reconcile(process, C, target, cell)
        if p.status == Status.ESCALATE:
            p.status = Status.PROCEED
        return p
    if name == "no_scrap_choice":
        p = reconcile(process, C, target, cell)
        if p.status == Status.ESCALATE and not any(b.kind == "irreversible" for b in p.blockers):
            p.status = Status.PROCEED
        return p
    if name == "no_cascade":
        _, roots, _ = undo_closure(process, C, target)
        U = frozenset(roots)
        K = C - U
        G = process.goal(target)
        p = reconcile(process, C, target, cell)
        return replace(p, status=Status.PROCEED, keep=K & G, undo=tuple(process.undo_order(U)),
                       forward=tuple(process.topo_order(G - K)), discard=frozenset(K - G), blockers=[])
    if name in ("no_cover_rule", "no_tolerated"):
        return reconcile(_variant_copy(process, name), C, target, cell)
    raise ValueError(f"unknown ablation {name}")
