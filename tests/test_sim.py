"""Simulator sanity: baselines behave as documented, deterministic per seed."""
import random

import pytest

from taskflux.examples import GEARBOX_CELL, gearbox
from taskflux.sim import SimParams, no_change_episode, run_episode

fs = frozenset
PERFECT = SimParams(p_forward=1.0, p_forward_novel=1.0, p_undo_retry=0.0)


def state(p, k):
    return p.topo_order(p.goal("A"))[:k]


def run(system, k, prm=PERFECT, **kw):
    p = gearbox()
    return p, run_episode(p, system, state(p, k), "A", "B", random.Random(0), prm, cell=GEARBOX_CELL, **kw)


def test_b1_finishes_wrong_product():
    _, ep = run("B1", 3)
    assert ep.outcome == "wrong_product" and not ep.success


def test_b2_restart_has_rework_cost_one_and_succeeds_when_reversible():
    _, ep = run("B2", 6)                  # cover fitted, nothing irreversible yet
    assert ep.success and ep.rework_cost == pytest.approx(1.0)


def test_b2_scraps_when_adhesive_is_on():
    _, ep = run("B2", 10)
    assert ep.scrapped and ep.success and ep.rework_cost == pytest.approx(1.0)


def test_b3a_collides_when_cover_is_in_the_way():
    _, ep = run("B3a", 6)
    assert ep.outcome == "collision"


def test_b3a_wrong_product_when_extra_steps_remain():
    _, ep = run("B3a", 7)                 # A housing seated
    assert not ep.success


def test_b3b_undoes_unnecessarily_and_fails_on_irreversible():
    _, ep = run("B3b", 6)
    assert ep.success and ep.unnecessary_undos >= 1
    _, ep2 = run("B3b", 10)
    assert ep2.outcome == "damaged"


def test_taskflux_succeeds_with_minimal_undo():
    p, ep = run("TF", 6)
    assert ep.success and ep.undone == ["cover"] and ep.unnecessary_undos == 0
    assert ep.rework_cost < 1.0


def test_taskflux_escalates_on_irreversible():
    _, ep = run("TF", 10)
    assert ep.escalated and ep.outcome == "scrapped_ok"


def test_taskflux_beats_restart_on_time_when_undo_is_small():
    _, tf = run("TF", 6)
    _, b2 = run("B2", 6)
    assert tf.total_time < b2.total_time


def test_hedge_reduces_time_in_both_worlds():
    p = gearbox()
    C = state(p, 2)
    rng = lambda: random.Random(3)
    idle = run_episode(p, "TF", C, "A", "B", rng(), PERFECT, ask="idle")
    hedge = run_episode(p, "TF", C, "A", "B", rng(), PERFECT, ask="hedge")
    assert hedge.success and idle.success
    assert hedge.total_time < idle.total_time
    n_idle = no_change_episode(p, C, "A", rng(), PERFECT, ask="idle")
    n_hedge = no_change_episode(p, C, "A", rng(), PERFECT, ask="hedge")
    assert n_hedge.total_time <= n_idle.total_time


def test_deterministic_given_seed():
    p = gearbox()
    a = run_episode(p, "TF", state(p, 6), "A", "B", random.Random(7), cell=GEARBOX_CELL)
    b = run_episode(p, "TF", state(p, 6), "A", "B", random.Random(7), cell=GEARBOX_CELL)
    assert (a.total_time - a.t_reconcile) == pytest.approx(b.total_time - b.t_reconcile)
