"""Hedged steps must be zero-regret in both worlds, checked against the cost-to-go function."""
import math
import random

import pytest

from taskflux.examples import gearbox
from taskflux.hedge import hedge_window, safe_steps
from taskflux.reconcile import cost_to_go
from taskflux.synth import random_process

fs = frozenset


def check_zero_regret(p, C, hyp="B", cur="A"):
    for s in safe_steps(p, C, cur, hyp):
        f = p.steps[s].forward_cost
        # world "changeover": remaining cost falls by exactly f(s)
        assert math.isclose(cost_to_go(p, C | {s}, hyp) + f, cost_to_go(p, C, hyp))
        # world "no change": s is simply the next step of the running plan
        assert math.isclose(cost_to_go(p, C | {s}, cur) + f, cost_to_go(p, C, cur))


def test_gearbox_shared_prefix_is_safe():
    p = gearbox()
    C = fs()
    safe = safe_steps(p, C, "A", "B")
    assert "base" in safe and "sticker_a" not in safe     # label is tolerated in B, not required


def test_gearbox_cover_is_not_safe_before_housing_b():
    """Fitting the cover early would have to be undone under B, so hedging must not do it."""
    p = gearbox()
    C = fs(p.topo_order(p.goal("A"))[:5])                  # base, sticker, bearing, shaft, connector
    assert "cover" not in safe_steps(p, C, "A", "B")


def test_nothing_is_safe_when_the_hypothesis_ends_in_scrap():
    p = gearbox()
    C = fs(p.topo_order(p.goal("A"))[:9])                  # housing_a fitted, screws on; B needs undo
    p2 = fs(p.topo_order(p.goal("A"))[:10])                # adhesive on -> irreversible block
    assert safe_steps(p, p2, "A", "B") == []


def test_gearbox_zero_regret_every_prefix():
    p = gearbox()
    order = p.topo_order(p.goal("A"))
    for k in range(len(order) + 1):
        check_zero_regret(p, fs(order[:k]))


@pytest.mark.parametrize("seed", range(60))
def test_random_zero_regret(seed):
    rng = random.Random(seed)
    p = random_process(rng)
    order = p.topo_order(p.goal("A"))
    C = fs(order[: rng.randint(0, len(order))])
    check_zero_regret(p, C)


def test_hedge_window_respects_budget_and_stays_safe():
    p = gearbox()
    started = hedge_window(p, fs(), "A", "B", window=20.0)
    assert started and sum(p.steps[s].forward_cost for s in started[:-1]) < 20.0
    C = fs()
    for s in started:
        assert s in safe_steps(p, C, "A", "B")
        C = C | {s}
