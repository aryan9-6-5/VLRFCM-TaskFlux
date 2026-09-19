"""Known-versus-novel routing and the gated adapter merge.

A variant already in the library runs on the base policy. A novel variant gets
a LoRA adapter (rank 32 is OpenVLA's own default). The adapter is only folded
into the base weights when both gates pass:

* quality gate:   the adapter succeeds on the new variant, judged by the lower
                  end of a Wilson interval so that a lucky small sample cannot pass;
* retention gate: success on previously mastered variants does not fall by more
                  than a margin, judged the same conservative way.

A failed gate never discards the adapter. It stays as a separate, switchable
adapter, so retention on the old variants is exactly preserved by routing.

With the 10 to 15 evaluation episodes a student cell can afford, a Wilson bound
is wide, so the gates will often refuse. ``episodes_needed`` says how many
episodes the retention gate needs before it can pass at all.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .metrics import wilson


@dataclass(frozen=True)
class GateConfig:
    quality_floor: float = 0.70       # lower confidence bound the adapter must clear on the new variant
    retention_margin: float = 0.10    # tolerated drop on an old variant, in absolute success rate
    z: float = 1.645                  # one-sided 95%


@dataclass
class GateResult:
    passed: bool
    detail: str


def quality_gate(k: int, n: int, cfg: GateConfig = GateConfig()) -> GateResult:
    lo, _ = wilson(k, n, cfg.z)
    return GateResult(lo >= cfg.quality_floor, f"new variant {k}/{n}, lower bound {lo:.2f} vs floor {cfg.quality_floor:.2f}")


def retention_gate(before: tuple, after: tuple, cfg: GateConfig = GateConfig()) -> GateResult:
    """``before`` and ``after`` are (successes, episodes) on an old variant, pre and post merge."""
    (kb, nb), (ka, na) = before, after
    p_before = kb / nb
    lo_after, _ = wilson(ka, na, cfg.z)
    ok = lo_after >= p_before - cfg.retention_margin
    return GateResult(ok, f"old variant {kb}/{nb} -> {ka}/{na}, lower bound {lo_after:.2f} vs {p_before - cfg.retention_margin:.2f}")


def episodes_needed(p_success: float, cfg: GateConfig = GateConfig(), max_n: int = 2000) -> Optional[int]:
    """Smallest n at which a perfectly retained variant with success rate ``p_success`` can pass the gate."""
    for n in range(5, max_n):
        k = round(p_success * n)
        if retention_gate((k, n), (k, n), cfg).passed:
            return n
    return None


@dataclass
class Adapter:
    variant: str
    rank: int = 32
    merged: bool = False


@dataclass
class Registry:
    """Which variants run on the base policy and which need a routed adapter."""
    base_variants: set = field(default_factory=set)
    adapters: Dict[str, Adapter] = field(default_factory=dict)
    log: List[str] = field(default_factory=list)

    def route(self, variant: str) -> str:
        if variant in self.base_variants:
            return "base"
        if variant in self.adapters and not self.adapters[variant].merged:
            return "adapter"
        if variant in self.adapters:
            return "base"       # merged into the base weights
        return "train"          # novel: an adapter has to be created and validated first

    def consider_merge(self, variant: str, new_score: tuple, old_scores: Dict[str, tuple],
                       post_merge_score: Callable[[str], tuple], cfg: GateConfig = GateConfig()) -> bool:
        """Try to merge ``variant``'s adapter. ``post_merge_score(v)`` evaluates old variant v with the merge applied."""
        q = quality_gate(*new_score, cfg=cfg)
        self.log.append(f"{variant}: quality {'PASS' if q.passed else 'FAIL'} ({q.detail})")
        if not q.passed:
            return False
        for v, before in old_scores.items():
            r = retention_gate(before, post_merge_score(v), cfg)
            self.log.append(f"{variant}: retention on {v} {'PASS' if r.passed else 'FAIL'} ({r.detail})")
            if not r.passed:
                return False
        self.adapters[variant].merged = True
        self.base_variants.add(variant)
        self.log.append(f"{variant}: merged into base")
        return True
