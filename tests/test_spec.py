"""Spec loading, round trip, annotation comparison, and the second example process."""
import csv
import io
import json
from pathlib import Path

import pytest

from taskflux.examples import GEARBOX_CELL, gearbox
from taskflux.process import ProcessError
from taskflux.reconcile import Cell, Status, reconcile
from taskflux.spec import annotation_sheet, compare_annotation, dump_process, load_process

fs = frozenset
EX = Path(__file__).resolve().parent.parent / "examples"


def test_gearbox_round_trips_through_json():
    p = gearbox()
    q, cell = load_process(json.loads(json.dumps(dump_process(p, GEARBOX_CELL, "gearbox"))))
    assert q.order == p.order and cell == GEARBOX_CELL
    for sid in p.order:
        a, b = p.steps[sid], q.steps[sid]
        assert (a.forward_cost, a.undo_cost, a.irreversible, a.undo_damage, a.requires, a.covered_by, a.tool) == \
               (b.forward_cost, b.undo_cost, b.irreversible, b.undo_damage, b.requires, b.covered_by, b.tool)
    assert {n: (v.required, v.tolerated) for n, v in p.variants.items()} == {n: (v.required, v.tolerated) for n, v in q.variants.items()}


def test_shipped_gearbox_json_matches_code():
    q, _ = load_process(EX / "gearbox.json")
    p = gearbox()
    order = p.topo_order(p.goal("A"))
    for k in range(len(order) + 1):
        a = reconcile(p, fs(order[:k]), "B")
        b = reconcile(q, fs(order[:k]), "B")
        assert (a.status, a.undo, a.forward) == (b.status, b.undo, b.forward)


def test_unknown_keys_are_rejected():
    d = dump_process(gearbox(), GEARBOX_CELL)
    d["steps"][0]["reversable"] = True
    with pytest.raises(ProcessError):
        load_process(d)
    d2 = dump_process(gearbox(), GEARBOX_CELL)
    d2["extra"] = 1
    with pytest.raises(ProcessError):
        load_process(d2)


def test_invalid_spec_is_caught_by_process_validation():
    d = dump_process(gearbox(), GEARBOX_CELL)
    d["steps"][3]["requires"] = ["nonexistent"]
    with pytest.raises(ProcessError):
        load_process(d)


# ---------------------------------------------------------------- second process
@pytest.fixture(scope="module")
def sensor():
    return load_process(EX / "sensor_module.json")


def state(p, k):
    return fs(p.topo_order(p.goal("A"))[:k])


def test_sensor_shield_can_must_lift_to_solder_the_b_header(sensor):
    p, cell = sensor
    plan = reconcile(p, state(p, 4), "B", cell)      # pcb, header_a, sensor, shield_can
    assert plan.status == Status.PROCEED
    assert set(plan.undo) == {"header_a", "shield_can"}
    assert plan.forward.index("header_b") < plan.forward.index("shield_can")


def test_sensor_potting_is_the_irreversible_trap(sensor):
    p, cell = sensor
    plan = reconcile(p, state(p, 8), "B", cell)      # potting_a is on
    assert plan.status == Status.ESCALATE
    assert plan.blockers[0].step == "potting_a" and "cured" in plan.explanation


def test_sensor_missing_sprayer_refuses_the_b_variant(sensor):
    p, cell = sensor
    weaker = Cell(tools=cell.tools - {"sprayer"})
    plan = reconcile(p, state(p, 2), "B", weaker)
    assert plan.status == Status.REFUSE and "sprayer" in plan.explanation


def test_sensor_tolerated_label_is_left_in_place(sensor):
    p, cell = sensor
    C = state(p, 1) | {"lot_label"}
    plan = reconcile(p, C, "B", cell)
    assert "lot_label" in plan.discard


# ---------------------------------------------------------------- annotation workflow
def test_blinded_sheet_hides_the_answers():
    p, _ = load_process(EX / "sensor_module.json")
    sheet = annotation_sheet(p)
    assert "cured" not in sheet and "0.15" not in sheet
    rows = list(csv.DictReader(io.StringIO(sheet)))
    assert [r["step_id"] for r in rows] == p.order
    assert all(r["can_be_undone (yes/no)"] == "" for r in rows)


def fill(p, mutate=None):
    rows = list(csv.DictReader(io.StringIO(annotation_sheet(p))))
    for r in rows:
        s = p.steps[r["step_id"]]
        r["can_be_undone (yes/no)"] = "no" if s.irreversible else "yes"
        r["chance_undo_damages_part (0-1)"] = str(s.undo_damage) if not s.irreversible else ""
        r["steps_that_must_be_removed_first (ids, ; separated)"] = ";".join(sorted(p.dependents[s.id]))
        if mutate:
            mutate(r)
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
    return out.getvalue()


def test_perfect_annotation_scores_perfectly():
    p, _ = load_process(EX / "sensor_module.json")
    r = compare_annotation(p, fill(p))
    assert r["reversibility_agreement"] == 1.0 and r["cohens_kappa"] == 1.0
    assert r["damage_mae"] == 0.0 and r["dependency_precision"] == 1.0 and r["dependency_recall"] == 1.0


def test_disagreement_is_visible():
    p, _ = load_process(EX / "sensor_module.json")

    def flip(r):
        if r["step_id"] == "shield_can":
            r["can_be_undone (yes/no)"] = "no"          # the annotator thinks a soldered can cannot come off
        if r["step_id"] == "sensor":
            r["steps_that_must_be_removed_first (ids, ; separated)"] = ""

    r = compare_annotation(p, fill(p, flip))
    assert r["reversibility_agreement"] < 1.0 and r["cohens_kappa"] < 1.0
    assert r["dependency_recall"] < 1.0
