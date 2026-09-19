"""Triage decisions, the controller dialogue, the adapter gates, and the stop override."""
import numpy as np
import pytest

from taskflux.adapters import GateConfig, Registry, Adapter, episodes_needed, quality_gate, retention_gate
from taskflux.controller import Controller
from taskflux.examples import GEARBOX_CELL, gearbox
from taskflux.triage import ABORT, Action, TriageParams, build_context, decide, fixed_threshold
from taskflux.utterances import IntentClassifier, lexical_stop, make_split

fs = frozenset


@pytest.fixture(scope="module")
def clf():
    return IntentClassifier.train()


def ctx_at(k, hedge=True):
    p = gearbox()
    C = fs(p.topo_order(p.goal("A"))[:k])
    return p, C, build_context(p, C, "A", "B", TriageParams(hedge=hedge), GEARBOX_CELL)


def probs(change, abort=0.0):
    rest = 1.0 - change - abort
    return [rest / 2, rest / 2, change, abort]


# ---------------------------------------------------------------- triage
def test_stop_always_halts_regardless_of_cost():
    for k in (1, 6, 9):
        _, _, ctx = ctx_at(k)
        assert decide(probs(0.9, abort=0.1), ctx) == Action.HALT
        assert decide([0, 0, 0, 1.0], ctx) == Action.HALT


def test_certain_no_change_continues_and_certain_change_acts_when_allowed():
    _, _, ctx = ctx_at(3)
    assert decide(probs(0.0), ctx) == Action.CONTINUE
    assert decide(probs(0.999), ctx) == Action.ACT


def largest_p_that_still_continues(ctx):
    """The most likely a changeover can be, in this state, before the rule stops carrying on."""
    best = 0.0
    for i in range(0, 101):
        pc = i / 100
        if decide(probs(pc), ctx) == Action.CONTINUE:
            best = pc
    return best


def test_threshold_moves_with_state_of_the_workpiece():
    """Same classifier confidence, different workpiece: the point at which we stop ignoring a
    possible changeover is not a constant. That is what a fixed threshold cannot do."""
    limits = [largest_p_that_still_continues(ctx_at(k)[2]) for k in range(1, 10)]
    assert len(set(limits)) > 1
    assert limits[0] > limits[-1]                      # nearly untouched bench tolerates more doubt


def test_irreversible_state_never_acts_blindly():
    _, _, ctx = ctx_at(10)
    assert not ctx.act_allowed
    assert decide(probs(1.0), ctx) == Action.ASK


def test_missed_changeover_with_no_work_left_still_costs_the_discovery_delay():
    """Regression: 'continue' looked free when A was finished, so a certain changeover was ignored."""
    _, _, ctx = ctx_at(11)                              # all of A done, nothing left to work on
    assert ctx.continue_regret >= TriageParams().discovery_delay - 1e-9


def test_fixed_threshold_is_state_blind():
    assert fixed_threshold(probs(0.55), 0.5) == Action.ACT
    assert fixed_threshold(probs(0.45), 0.5) == Action.CONTINUE


# ---------------------------------------------------------------- utterances
def test_lexical_stop_catches_stop_words_and_ignores_normal_speech():
    assert all(lexical_stop(s) for s in ["stop", "not safe, stop", "hold everything", "shut it down", "freeze"])
    assert not any(lexical_stop(s) for s in ["switch to the B housing", "use 12 Nm", "the left screw"])


def test_classifier_beats_chance_on_held_out_templates(clf):
    xs, ys = make_split("test", 100, 5)
    assert (clf.predict(xs) == np.array(ys)).mean() > 0.8
    P = clf.proba(xs)
    assert np.allclose(P.sum(1), 1.0)


# ---------------------------------------------------------------- controller
def make_controller(clf, k):
    p = gearbox()
    return Controller(p, "A", "B", clf, GEARBOX_CELL, done=set(p.topo_order(p.goal("A"))[:k]))


def test_controller_acts_on_clear_changeover_and_queues_undo_then_build(clf):
    c = make_controller(clf, 6)
    r = c.hear("switch to variant B")
    assert r.action == Action.ACT and c.current == "B"
    assert c.queue[0] == ("undo", "cover")


def test_controller_stops_on_stop(clf):
    c = make_controller(clf, 6)
    assert c.hear("stop").action == Action.HALT and c.halted and c.next_action() is None


def test_controller_asks_then_hedges_then_switches(clf):
    c = make_controller(clf, 2)
    c.done = set(c.process.topo_order(c.process.goal("A"))[:2])
    c.pending_change = True
    step = c.next_action()
    assert step is not None and step[0] == "do"         # keeps building while waiting
    assert step[1] in c.process.goal("B")
    c.complete(*step)
    r = c.answer(True)
    assert r.action == Action.ACT and c.current == "B"


def test_controller_refusal_then_scrap(clf):
    c = make_controller(clf, 10)
    r = c.hear("the order changed, it's the B housing now")
    assert r.action == Action.ASK and "cured" in r.say
    r2 = c.answer(True)
    assert not c.done and c.current == "B" and "Scrapping" in r2.say


# ---------------------------------------------------------------- adapters
def test_gates_reject_small_lucky_samples():
    assert not quality_gate(9, 10).passed                # 90% of 10 has a weak lower bound
    assert quality_gate(90, 100).passed


def test_retention_gate_catches_a_drop():
    assert retention_gate((95, 100), (94, 100)).passed
    assert not retention_gate((95, 100), (70, 100)).passed


def test_gate_needs_more_episodes_than_a_student_cell_can_run():
    n = episodes_needed(0.90)
    assert n is not None and n > 15


def test_registry_routes_and_only_merges_when_both_gates_pass():
    reg = Registry(base_variants={"A"}, adapters={"B": Adapter("B")})
    assert reg.route("A") == "base" and reg.route("B") == "adapter" and reg.route("C") == "train"
    assert not reg.consider_merge("B", (90, 100), {"A": (95, 100)}, lambda v: (60, 100))
    assert reg.route("B") == "adapter"                    # failed merge leaves the adapter routable
    assert reg.consider_merge("B", (90, 100), {"A": (95, 100)}, lambda v: (94, 100))
    assert reg.route("B") == "base"
