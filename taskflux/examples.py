"""Hand-authored example process: a small gearbox with two housing variants.

Variant A: foam gasket, A housing, screws, cured seam adhesive, leak test, A label.
Variant B: B housing (no gasket), screws, cured seam adhesive, leak test, B label.

Physical facts that make changeover non-trivial:
* the cover plate blocks access to the connector (connector before cover) and
  also blocks seating the B housing, so a cover fitted early in A has to come
  off when B is requested and go back on afterwards;
* the seam adhesive cures and cannot be removed: once it is on, nothing under
  it can be undone.
"""
from __future__ import annotations

from typing import FrozenSet

from .process import Process, Step, Variant
from .reconcile import Cell

fs = frozenset

GEARBOX_CELL = Cell(tools=fs({"gripper", "torque_driver", "dispenser"}))


def gearbox() -> Process:
    steps = [
        Step("base", "place base plate", 8, 6),
        Step("sticker_a", "apply variant-A label", 5, 4, requires=fs({"base"})),
        Step("bearing", "press bearing", 18, 30, undo_damage=0.08, requires=fs({"base"})),
        Step("shaft", "insert shaft", 12, 14, requires=fs({"bearing"})),
        Step("connector", "seat connector", 15, 28, undo_damage=0.10,
             requires=fs({"base"}), covered_by=fs({"cover"})),
        Step("cover", "fit cover plate", 12, 10, requires=fs({"connector"})),
        Step("gasket", "fit foam gasket", 9, 8, requires=fs({"base"}), covered_by=fs({"housing_a"})),
        Step("housing_a", "seat A housing", 20, 22, requires=fs({"base", "gasket", "shaft"})),
        Step("screws_a", "torque A housing screws", 30, 28, requires=fs({"housing_a"}), tool="torque_driver"),
        Step("adhesive_a", "cure A seam adhesive", 25, requires=fs({"screws_a"}), tool="dispenser",
             irreversible=True, irreversible_reason="the adhesive bond has cured"),
        Step("test_a", "leak-test A housing", 15, 3, requires=fs({"adhesive_a"})),
        Step("housing_b", "seat B housing", 22, 24, requires=fs({"base", "shaft"}), covered_by=fs({"cover"})),
        Step("screws_b", "torque B housing screws", 34, 30, requires=fs({"housing_b"}), tool="torque_driver"),
        Step("adhesive_b", "cure B seam adhesive", 25, requires=fs({"screws_b"}), tool="dispenser",
             irreversible=True, irreversible_reason="the adhesive bond has cured"),
        Step("test_b", "leak-test B housing", 15, 3, requires=fs({"adhesive_b"})),
        Step("label_b", "apply variant-B label", 5, 4, requires=fs({"base"})),
    ]
    A = Variant("A", fs({"base", "sticker_a", "bearing", "shaft", "connector", "cover", "gasket",
                        "housing_a", "screws_a", "adhesive_a", "test_a"}))
    B = Variant("B", fs({"base", "bearing", "shaft", "connector", "cover", "housing_b", "screws_b",
                        "adhesive_b", "test_b", "label_b"}), tolerated=fs({"sticker_a"}))
    return Process(steps, [A, B], scrap_cost=150.0)
