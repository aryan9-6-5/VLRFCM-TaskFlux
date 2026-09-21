"""Reach, human safety zones, covers derived from geometry, and their use in refusal."""
import pytest

from taskflux.geometry import Box, Workcell, Zone, derive_covered_by
from taskflux.process import Process, Step, Variant
from taskflux.reconcile import Cell, Status, reconcile
from taskflux.spec import dump_process, load_process

fs = frozenset


def test_box_basics():
    a = Box((0, 0, 0), (1, 1, 1))
    assert a.contains((0.5, 0.5, 0.5)) and not a.contains((2, 0, 0))
    assert a.overlaps_xy(Box((0.5, 0.5, 5), (2, 2, 6))) and not a.overlaps_xy(Box((1, 0, 0), (2, 1, 1)))
    with pytest.raises(ValueError):
        Box((1, 0, 0), (0, 1, 1))


def test_reach_is_a_shell_around_the_base():
    wc = Workcell(base=(0, 0, 0), reach=0.8, min_reach=0.1)
    assert wc.reachable((0.5, 0.0, 0.2))
    assert not wc.reachable((1.0, 0.0, 0.0))          # too far
    assert not wc.reachable((0.02, 0.0, 0.0))         # too close to the base


def test_stack_covers_are_derived_from_placement():
    boxes = {
        "plate": Box((0, 0, 0), (0.4, 0.3, 0.01)),
        "gasket": Box((0.05, 0.05, 0.01), (0.35, 0.25, 0.02)),
        "housing": Box((0.05, 0.05, 0.02), (0.35, 0.25, 0.10)),
        "lid": Box((0.05, 0.05, 0.10), (0.35, 0.25, 0.11)),
        "label": Box((0.38, 0.28, 0.01), (0.40, 0.30, 0.011)),      # off to the side: covers nothing, covered by nothing
    }
    cov = derive_covered_by(boxes)
    assert cov["gasket"] >= {"housing", "lid"}
    assert cov["housing"] == {"lid"}
    assert cov["lid"] == frozenset()
    assert cov["label"] == frozenset()


def make_process(pos_far=(2.0, 0.0, 0.0), pos_zone=(0.3, 0.3, 0.1)):
    steps = [
        Step("base", "place base", 5, 5, pos=(0.4, 0.0, 0.0)),
        Step("a1", "fit part a1", 5, 5, requires=fs({"base"}), pos=(0.4, 0.1, 0.05)),
        Step("b1", "fit part b1", 5, 5, requires=fs({"base"}), pos=pos_far),
        Step("b2", "fit part b2", 5, 5, requires=fs({"base"}), pos=pos_zone),
    ]
    return Process(steps, [Variant("A", fs({"base", "a1"})), Variant("B", fs({"base", "b1"})),
                           Variant("C", fs({"base", "b2"}))])


WC = Workcell(base=(0, 0, 0), reach=0.85, zones=(Zone("operator bench", Box((0.2, 0.2, 0.0), (0.5, 0.5, 0.5))),))


def test_unreachable_step_is_refused_with_a_reason():
    p = make_process()
    plan = reconcile(p, fs({"base", "a1"}), "B", Cell(workcell=WC))
    assert plan.status == Status.REFUSE
    assert plan.blockers[0].kind == "reach" and "reach" in plan.explanation


def test_step_in_the_human_zone_is_refused_and_names_the_zone():
    p = make_process()
    plan = reconcile(p, fs({"base", "a1"}), "C", Cell(workcell=WC))
    assert plan.status == Status.REFUSE
    assert plan.blockers[0].kind == "zone" and "operator bench" in plan.explanation


def test_undoing_a_step_also_needs_the_arm_to_reach_it():
    p = make_process(pos_far=(0.3, 0.0, 0.0))
    far_a1 = Step("a1", "fit part a1", 5, 5, requires=fs({"base"}), pos=(3.0, 0.0, 0.0))
    steps = [p.steps[s] if s != "a1" else far_a1 for s in p.order]
    q = Process(steps, list(p.variants.values()))
    plan = reconcile(q, fs({"base", "a1"}), "B", Cell(workcell=WC))     # a1 must come off but cannot be reached
    assert plan.status == Status.REFUSE and plan.blockers[0].step == "a1"


def test_no_workcell_means_no_geometry_checks():
    p = make_process()
    assert reconcile(p, fs({"base", "a1"}), "B", Cell()).status == Status.PROCEED
    assert reconcile(p, fs({"base", "a1"}), "B", None).status == Status.PROCEED


def test_steps_without_positions_are_skipped():
    p = make_process()
    steps = [Step(s.id, s.label, s.forward_cost, s.undo_cost, requires=s.requires) for s in (p.steps[i] for i in p.order)]
    q = Process(steps, list(p.variants.values()))
    assert reconcile(q, fs({"base", "a1"}), "B", Cell(workcell=WC)).status == Status.PROCEED


def test_spec_round_trip_keeps_positions_and_workcell():
    p = make_process()
    cell = Cell(tools=fs({"gripper"}), workcell=WC)
    q, cell2 = load_process(dump_process(p, cell))
    assert cell2 == cell and q.steps["b1"].pos == (2.0, 0.0, 0.0)
    assert reconcile(q, fs({"base", "a1"}), "C", cell2).status == Status.REFUSE
