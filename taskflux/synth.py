"""Random two-variant processes for experiments.

Creation order is a valid build order for both variants because ``requires``
only ever points at earlier steps. Shared steps only require shared steps, so
each variant's required set is closed.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from .process import Process, ProcessError, Step, Variant

fs = frozenset


@dataclass(frozen=True)
class SynthConfig:
    n_shared: int = 7
    n_a: int = 5
    n_b: int = 5
    p_irreversible: float = 0.12
    p_cover: float = 0.35      # chance a variant-only step is covered by a shared step
    p_tolerated: float = 0.20  # chance a leaf variant-only step is harmless to leave
    p_damage: float = 0.30     # chance a reversible step carries undo damage risk
    scrap_cost: float = 150.0


def _ancestors(steps: Dict[str, Step], sid: str) -> Set[str]:
    out: Set[str] = set()
    stack = list(steps[sid].requires)
    while stack:
        r = stack.pop()
        if r not in out:
            out.add(r)
            stack.extend(steps[r].requires)
    return out


def random_process(rng: random.Random, cfg: SynthConfig = SynthConfig(), max_tries: int = 50) -> Process:
    for _ in range(max_tries):
        try:
            return _build(rng, cfg)
        except ProcessError:
            continue
    raise RuntimeError("could not generate a consistent process")


def _build(rng: random.Random, cfg: SynthConfig) -> Process:
    groups = ["S"] * cfg.n_shared + ["A"] * cfg.n_a + ["B"] * cfg.n_b
    rng.shuffle(groups)
    n = len(groups)
    made: Dict[str, Step] = {}
    grp: Dict[str, str] = {}
    counters = {"S": 0, "A": 0, "B": 0}
    pending_cover: List[str] = []
    for pos, g in enumerate(groups):
        sid = f"{g.lower()}{counters[g]}"
        counters[g] += 1
        if g == "S":
            pool = [x for x in made if grp[x] == "S"]
        else:
            pool = [x for x in made if grp[x] in ("S", g)]
        req: Set[str] = set()
        if pool:
            k = rng.choice([1, 1, 2]) if len(pool) > 1 else 1
            if g != "S" or rng.random() < 0.7:
                req = set(rng.sample(pool, min(k, len(pool))))
        fwd = round(rng.uniform(5, 30), 1)
        irr = rng.random() < cfg.p_irreversible * (0.5 + pos / n)
        dmg = 0.0 if irr or rng.random() > cfg.p_damage else round(rng.uniform(0.02, 0.15), 3)
        st = Step(sid, sid, fwd, round(fwd * rng.uniform(0.8, 2.0), 1), irreversible=irr,
                  undo_damage=dmg, requires=fs(req),
                  irreversible_reason="it cannot be undone" if irr else "")
        made[sid] = st
        grp[sid] = g
        if g != "S":
            pending_cover.append(sid)
    # cover relations: a variant-only step is covered by a shared step that is not its ancestor
    shared = [x for x in made if grp[x] == "S"]
    for sid in pending_cover:
        if shared and rng.random() < cfg.p_cover:
            anc = _ancestors(made, sid)
            cands = [c for c in shared if c not in anc]
            if cands:
                c = rng.choice(cands)
                made[sid] = _replace(made[sid], covered_by=fs({c}))
    # tolerated extras: variant-only leaves are harmless to leave in the other variant
    def leaves(g: str) -> List[str]:
        used = {r for s in made.values() for r in s.requires}
        cover_targets = {c for s in made.values() for c in s.covered_by}
        return [x for x in made if grp[x] == g and x not in used and x not in cover_targets]
    tol_for_b = fs(x for x in leaves("A") if rng.random() < cfg.p_tolerated)
    tol_for_a = fs(x for x in leaves("B") if rng.random() < cfg.p_tolerated)
    A = Variant("A", fs(x for x in made if grp[x] in ("S", "A")), tol_for_a)
    B = Variant("B", fs(x for x in made if grp[x] in ("S", "B")), tol_for_b)
    return Process(list(made.values()), [A, B], scrap_cost=cfg.scrap_cost)


def _replace(st: Step, **kw) -> Step:
    from dataclasses import replace
    return replace(st, **kw)
