"""Perception noise: observation, the free consistency check, and the policies."""
import random

import pytest

from taskflux.examples import GEARBOX_CELL, gearbox
from taskflux.perception import (NoiseParams, close_downward, inconsistent_steps, observe, run_noisy_episode)
from taskflux.sim import SimParams

fs = frozenset
PERFECT = SimParams(p_forward=1.0, p_undo_retry=0.0, damage_scale=0.0)


def state(p, k):
    return fs(p.topo_order(p.goal("A"))[:k])


def test_no_noise_observation_is_the_truth():
    p = gearbox()
    C = state(p, 6)
    assert observe(p, C, NoiseParams(0.0, 0.0), random.Random(1)) == C


def test_observation_is_deterministic_per_seed():
    p = gearbox()
    C = state(p, 6)
    a = observe(p, C, NoiseParams(0.2, 0.2), random.Random(5))
    b = observe(p, C, NoiseParams(0.2, 0.2), random.Random(5))
    assert a == b


def test_valid_states_are_never_flagged():
    p = gearbox()
    order = p.topo_order(p.goal("A"))
    assert all(not inconsistent_steps(p, fs(order[:k])) for k in range(len(order) + 1))


def test_a_missed_middle_step_is_flagged_but_a_missed_last_step_is_not():
    p = gearbox()
    C = state(p, 6)                       # base, sticker_a, bearing, shaft, connector, cover
    missed_middle = C - {"connector"}     # cover is seen done but its prerequisite is not
    flagged = inconsistent_steps(p, missed_middle)
    assert "cover" in flagged and "connector" in flagged
    missed_last = C - {"cover"}           # nothing depends on it, so the state still looks fine
    assert not inconsistent_steps(p, missed_last)


def test_close_downward_repairs_an_impossible_state():
    p = gearbox()
    bad = fs({"shaft"})
    assert not p.is_valid_state(bad)
    assert p.is_valid_state(close_downward(p, bad))


def test_oracle_matches_truth_and_costs_no_inspections():
    p = gearbox()
    r = run_noisy_episode(p, "oracle", state(p, 6), "A", "B", random.Random(0), PERFECT, cell=GEARBOX_CELL)
    assert r.episode.success and r.inspections == 0 and not r.had_error


@pytest.mark.parametrize("policy", ["trust", "consistency", "inspect_undo", "inspect_all"])
def test_every_policy_matches_the_oracle_when_there_is_no_noise(policy):
    p = gearbox()
    for k in range(1, 11):
        C = state(p, k)
        base = run_noisy_episode(p, "oracle", C, "A", "B", random.Random(0), PERFECT, NoiseParams(0, 0), GEARBOX_CELL)
        r = run_noisy_episode(p, policy, C, "A", "B", random.Random(0), PERFECT, NoiseParams(0, 0), GEARBOX_CELL)
        assert r.episode.success == base.episode.success
        assert r.episode.undone == base.episode.undone


def test_inspect_all_is_exact_under_heavy_noise():
    p = gearbox()
    heavy = NoiseParams(0.3, 0.3)
    for seed in range(30):
        C = state(p, 6)
        r = run_noisy_episode(p, "inspect_all", C, "A", "B", random.Random(seed), PERFECT, heavy, GEARBOX_CELL)
        assert r.episode.success


def test_trusting_a_wrong_observation_can_fail_and_inspection_repairs_it():
    p = gearbox()
    C = state(p, 6)
    noise = NoiseParams(0.25, 0.25)
    trust_fail = insp_fail = 0
    for seed in range(60):
        trust_fail += not run_noisy_episode(p, "trust", C, "A", "B", random.Random(seed), PERFECT, noise, GEARBOX_CELL).episode.success
        insp_fail += not run_noisy_episode(p, "inspect_all", C, "A", "B", random.Random(seed), PERFECT, noise, GEARBOX_CELL).episode.success
    assert trust_fail > 0 and insp_fail == 0


def test_inspection_costs_time():
    p = gearbox()
    C = state(p, 6)
    a = run_noisy_episode(p, "oracle", C, "A", "B", random.Random(0), PERFECT, NoiseParams(0, 0), GEARBOX_CELL)
    b = run_noisy_episode(p, "inspect_all", C, "A", "B", random.Random(0), PERFECT, NoiseParams(0, 0), GEARBOX_CELL)
    assert b.episode.total_time > a.episode.total_time and b.inspections > 0


def test_a_state_with_contradictory_ordering_is_impossible_even_if_prerequisites_are_present():
    """Regression: found by the noise experiment. Two steps that each must be removed before the other."""
    from taskflux.process import Process, Step, Variant
    steps = [Step("x", "x", covered_by=fs({"y"})), Step("y", "y", covered_by=fs({"x"})), Step("z", "z")]
    p = Process(steps, [Variant("A", fs({"x", "z"})), Variant("B", fs({"y", "z"}))])
    both = fs({"x", "y"})
    assert p.requires_closed(both) and not p.realizable(both) and not p.is_valid_state(both)
    assert p.cycle_core(both) == {"x", "y"}
    assert inconsistent_steps(p, both) == {"x", "y"}
    from taskflux.reconcile import reconcile
    with pytest.raises(ValueError):
        reconcile(p, both, "B")
    from taskflux.perception import _repair
    assert p.is_valid_state(_repair(p, both))


def test_real_build_states_are_always_realizable():
    from taskflux.synth import random_process
    for seed in range(60):
        p = random_process(random.Random(seed))
        order = p.topo_order(p.goal("A"))
        for k in range(len(order) + 1):
            assert p.is_valid_state(order[:k])


def test_inspect_critical_is_exact_under_noise_but_cheaper_than_inspecting_everything():
    p = gearbox()
    noise = NoiseParams(0.05, 0.05)
    crit_fail = crit_n = all_n = 0
    for k in range(1, 11):
        for seed in range(30):
            C = state(p, k)
            a = run_noisy_episode(p, "inspect_critical", C, "A", "B", random.Random(seed), PERFECT, noise, GEARBOX_CELL)
            b = run_noisy_episode(p, "inspect_all", C, "A", "B", random.Random(seed), PERFECT, noise, GEARBOX_CELL)
            crit_fail += not a.episode.success
            crit_n += a.inspections
            all_n += b.inspections
    assert crit_n < all_n
    assert crit_fail <= 5      # critical steps are inspected exactly; what is left is only policy step failures
