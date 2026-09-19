"""Metric helpers. Everything reports counts and an interval, never a bare percentage."""
from __future__ import annotations

import math
from typing import Iterable, Sequence, Tuple


def wilson(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def mean_ci(xs: Sequence[float], z: float = 1.96) -> Tuple[float, float]:
    """Mean and normal-approximation half-width."""
    n = len(xs)
    if n == 0:
        return (float("nan"), float("nan"))
    m = sum(xs) / n
    if n == 1:
        return (m, float("nan"))
    var = sum((x - m) ** 2 for x in xs) / (n - 1)
    return (m, z * math.sqrt(var / n))


def fmt_rate(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{k}/{n} ({100 * k / n:.0f}%, CI {100 * lo:.0f}-{100 * hi:.0f})" if n else "n/a"
