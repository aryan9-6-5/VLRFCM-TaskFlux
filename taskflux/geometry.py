"""A deliberately small geometry layer: reach, human safety zones, and covers derived from geometry.

This is a STUB. It exists so the refusal path can say "I cannot reach that" or "that is inside the
human zone", and so `covered_by` can be derived from part placement instead of being typed by hand.
It is not robot kinematics:

* reach is a spherical shell around the arm base, not inverse kinematics or joint limits;
* parts and zones are axis-aligned boxes; there is no swept-volume or self-collision check;
* approach is assumed to be top-down, so a part blocks another only if it sits above it;
* units are metres.

A real cell needs a proper motion-planning check (MoveIt or similar) behind the same interface.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, FrozenSet, Optional, Tuple

Vec = Tuple[float, float, float]


@dataclass(frozen=True)
class Box:
    lo: Vec
    hi: Vec

    def __post_init__(self) -> None:
        if any(l > h for l, h in zip(self.lo, self.hi)):
            raise ValueError("box lower corner must not exceed upper corner")

    def overlaps_xy(self, other: "Box") -> bool:
        return (self.lo[0] < other.hi[0] and other.lo[0] < self.hi[0]
                and self.lo[1] < other.hi[1] and other.lo[1] < self.hi[1])

    def contains(self, p: Vec) -> bool:
        return all(l <= v <= h for l, v, h in zip(self.lo, p, self.hi))


@dataclass(frozen=True)
class Zone:
    name: str
    box: Box


@dataclass(frozen=True)
class Workcell:
    base: Vec = (0.0, 0.0, 0.0)
    reach: float = 0.85
    min_reach: float = 0.10
    zones: Tuple[Zone, ...] = ()

    def reachable(self, p: Vec) -> bool:
        d = math.dist(self.base, p)
        return self.min_reach <= d <= self.reach

    def zone_of(self, p: Vec) -> Optional[Zone]:
        for z in self.zones:
            if z.box.contains(p):
                return z
        return None


def derive_covered_by(boxes: Dict[str, Box], eps: float = 1e-9) -> Dict[str, FrozenSet[str]]:
    """``u`` covers ``s`` when ``u`` sits above ``s`` and overlaps it in plan view.

    With a top-down approach, a part that is above another and overlaps it in x and y blocks access to it.
    """
    out: Dict[str, set] = {s: set() for s in boxes}
    for s, bs in boxes.items():
        for u, bu in boxes.items():
            if u != s and bu.overlaps_xy(bs) and bu.lo[2] >= bs.hi[2] - eps:
                out[s].add(u)
    return {s: frozenset(v) for s, v in out.items()}
