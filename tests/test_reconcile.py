"""Reconciler correctness, including exhaustive optimality checks on small random processes."""
import itertools
import math
import random

import pytest

from taskflux.examples import GEARBOX_CELL, gearbox
from taskflux.process import Process, ProcessError, Step, Variant
from taskflux.reconcile import Cell, Status, reconcile, undo_closure
from taskflux.synth import SynthConfig, random_process

fs = frozenset


def prefix(p: Process, variant: str, k: int):
    return fs(p.topo_order(p.goal(variant))[:k])


# ---------------------------------------------------------------- gearbox scenarios
def test_truncation_only_when_nothing_conflicts():
    p = gearbox()
    plan = reconcile(p, prefix(p, "A", 3), "B")  # base, sticker_a, bearing
    assert plan.status == Status.PROCEED
    assert plan.undo == ()
    assert "sticker_a" in plan.discard          # tolerated extra is left in place
    assert "sticker_a" not in plan.keep


def test_cover_must_come_off_for_b_housing_and_goes_back_later():
    p = gearbox()
    done = prefix(p, "A", 6)                    # ... connector, cover
    assert "cover" in done
    plan = reconcile(p, done, "B")
    assert plan.status == Status.PROCEED
    assert plan.undo == ("cover",)
    assert plan.forward.index("housing_b") < plan.forward.index("cover")   # cover redone last
    assert "cover" in plan.forward


def test_undo_cascades_in_reverse_dependency_order():
    p = gearbox()
    done = prefix(p, "A", 9)                    # ... gasket, housing_a, screws_a
    plan = reconcile(p, done, "B")
    assert plan.status == Status.PROCEED
    u = plan.undo
    assert set(u) == {"cover", "gasket", "housing_a", "screws_a"}
    assert u.index("screws_a") < u.index("housing_a") < u.index("gasket")


def test_irreversible_step_forces_escalation_with_certificate():
    p = gearbox()
    done = prefix(p, "A", 10)                   # adhesive_a is on
    plan = reconcile(p, done, "B")
    assert plan.status == Status.ESCALATE
    assert plan.blockers and plan.blockers[0].step == "adhesive_a"
    ch = plan.blockers[0].chain
    assert ch[-1] == "adhesive_a"
    assert "adhesive" in plan.explanation and "cured" in plan.explanation
    assert math.isinf(plan.salvage_cost)
    assert plan.cost == plan.scrap_total


def test_missing_tool_is_refused():
    p = gearbox()
    cell = Cell(tools=fs({"gripper", "dispenser"}))       # no torque driver
    plan = reconcile(p, prefix(p, "A", 3), "B", cell)
    assert plan.status == Status.REFUSE
    assert "torque_driver" in plan.explanation


def test_empty_workspace_is_a_plain_build():
    p = gearbox()
    plan = reconcile(p, fs(), "B")
    assert plan.status == Status.PROCEED and plan.undo == () and set(plan.forward) == set(p.goal("B"))
    assert plan.scrap_total == plan.salvage_cost


def test_rejects_invalid_state():
    p = gearbox()
    with pytest.raises(ValueError):
        reconcile(p, fs({"shaft"}), "B")    # shaft without bearing


def test_same_variant_is_a_no_op_plus_remaining():
    p = gearbox()
    done = prefix(p, "A", 6)
    plan = reconcile(p, done, "A")
    assert plan.undo == () and set(plan.forward) == set(p.goal("A")) - done


# ---------------------------------------------------------------- exhaustive optimality
def brute_force_valid_keeps(p: Process, C, target):
    """Every K subset of C that a physically valid changeover could leave in place."""
    G = p.goal(target)
    allowed = p.keepable(target)
    C = sorted(C)
    out = []
    for r in range(len(C) + 1):
        for K in itertools.combinations(C, r):
            K = set(K)
            if not K <= allowed:
                continue
            # closure: keeping a step forces keeping what it needs and what it covers
            if any(not (p.steps[u].requires <= K) for u in K):
                continue
            if any(s in set(C) and s not in K and u in p.steps[s].covered_by for u in K for s in p.steps):
                continue
            # a kept cover blocks a still-needed step
            if any(p.steps[g].covered_by & K for g in G - K):
                continue
            out.append(frozenset(K))
    return out


@pytest.mark.parametrize("seed", range(40))
def test_undo_set_is_the_unique_minimum(seed):
    rng = random.Random(seed)
    p = random_process(rng, SynthConfig(n_shared=3, n_a=3, n_b=3))
    order = p.topo_order(p.goal("A"))
    for k in range(len(order) + 1):
        C = fs(order[:k])
        valid = brute_force_valid_keeps(p, C, "B")
        assert valid, "keeping nothing is always feasible"
        U, _, _ = undo_closure(p, C, "B")
        K_star = C - U
        assert K_star in valid
        assert all(K <= K_star for K in valid)      # maximum element => minimum undo set


@pytest.mark.parametrize("seed", range(40))
def test_plan_is_executable(seed):
    """Replaying the plan step by step never violates prerequisites or blocks."""
    rng = random.Random(1000 + seed)
    p = random_process(rng)
    order = p.topo_order(p.goal("A"))
    k = rng.randint(0, len(order))
    state = set(order[:k])
    plan = reconcile(p, state, "B")
    for s in plan.undo:
        assert s in state
        assert not (p.dependents[s] & state), "undo attempted while dependents still present"
        state.discard(s)
    for s in plan.forward:
        assert p.ready(state, s), f"{s} not executable"
        state.add(s)
    assert fs(state) == p.goal("B") | plan.discard


@pytest.mark.parametrize("seed", range(25))
def test_cost_is_minimal_over_all_valid_keeps(seed):
    rng = random.Random(500 + seed)
    p = random_process(rng, SynthConfig(n_shared=3, n_a=3, n_b=3, p_irreversible=0.0))
    order = p.topo_order(p.goal("A"))
    C = fs(order[: rng.randint(0, len(order))])
    G = p.goal("B")

    def cost(K):
        return (sum(p.steps[s].undo_cost for s in C - K) + sum(p.steps[s].forward_cost for s in G - K))

    best = min(cost(K) for K in brute_force_valid_keeps(p, C, "B"))
    plan = reconcile(p, C, "B")
    assert math.isclose(plan.undo_time + plan.forward_time, best)


def test_validation_catches_bad_variant():
    with pytest.raises(ProcessError):
        Process([Step("a", "a", requires=fs({"b"})), Step("b", "b")], [Variant("V", fs({"a"}))])


def test_certificate_chain_names_root_then_trapping_step():
    """A glued lid (shared, irreversible dependent) sits over a step only variant B needs."""
    steps = [
        Step("base", "place base", 5, 5),
        Step("c", "fit inner cover", 5, 5, requires=fs({"base"})),
        Step("t", "glue lid onto cover", 5, requires=fs({"c"}), irreversible=True, irreversible_reason="the glue has set"),
        Step("g", "seat gasket", 5, 5, requires=fs({"base"}), covered_by=fs({"c"})),
    ]
    p = Process(steps, [Variant("A", fs({"base", "c", "t"})), Variant("B", fs({"base", "c", "t", "g"}))])
    plan = reconcile(p, fs({"base", "c", "t"}), "B")
    assert plan.status == Status.ESCALATE
    b = plan.blockers[0]
    assert b.step == "t" and b.chain == ("c", "t") and b.root_reason == "covers"
    assert "'fit inner cover' blocks 'seat gasket'" in plan.explanation
    assert "glue lid onto cover" in plan.explanation and "the glue has set" in plan.explanation
