"""Load and dump processes as JSON, and support independent annotation.

A process spec is plain JSON so that someone who did not write the code can author or review it.

    {
      "name": "sensor_module",
      "scrap_cost": 120,
      "cell": {"tools": ["gripper", "soldering_iron"],
               "workcell": {"base": [0, 0, 0], "reach": 0.85, "min_reach": 0.1,
                            "zones": [{"name": "operator bench", "box": [0.2, 0.2, 0, 0.5, 0.5, 0.5]}]}},
      "steps": [
        {"id": "pcb", "label": "seat PCB", "forward": 12, "undo": 10,
         "requires": [], "covered_by": [], "irreversible": false, "irreversible_reason": "",
         "undo_damage": 0.0, "tool": null, "pos": [0.4, 0.0, 0.05]}
      ],
      "variants": [{"name": "A", "required": ["pcb"], "tolerated": []}]
    }

Unknown keys are rejected, so a typo in an annotation does not silently become a default.
"""
from __future__ import annotations

import csv
import io
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .process import INF, Process, ProcessError, Step, Variant
from .geometry import Box, Workcell, Zone
from .reconcile import Cell

fs = frozenset

_STEP_KEYS = {"id", "label", "forward", "undo", "requires", "covered_by", "irreversible",
              "irreversible_reason", "undo_damage", "tool", "pos"}
_TOP_KEYS = {"name", "scrap_cost", "cell", "steps", "variants", "notes"}


def load_process(src: Union[str, Path, Dict[str, Any]]) -> Tuple[Process, Cell]:
    d = src if isinstance(src, dict) else json.loads(Path(src).read_text(encoding="utf-8"))
    extra = set(d) - _TOP_KEYS
    if extra:
        raise ProcessError(f"unknown top-level keys: {sorted(extra)}")
    steps: List[Step] = []
    for s in d["steps"]:
        bad = set(s) - _STEP_KEYS
        if bad:
            raise ProcessError(f"step {s.get('id')}: unknown keys {sorted(bad)}")
        irr = bool(s.get("irreversible", False))
        steps.append(Step(
            id=s["id"], label=s.get("label", s["id"]),
            forward_cost=float(s["forward"]), undo_cost=INF if irr else float(s.get("undo", s["forward"])),
            irreversible=irr, undo_damage=float(s.get("undo_damage", 0.0)),
            requires=fs(s.get("requires", [])), covered_by=fs(s.get("covered_by", [])),
            tool=s.get("tool"), irreversible_reason=s.get("irreversible_reason", ""),
            pos=tuple(float(x) for x in s["pos"]) if s.get("pos") else None))
    variants = [Variant(v["name"], fs(v["required"]), fs(v.get("tolerated", []))) for v in d["variants"]]
    proc = Process(steps, variants, scrap_cost=float(d.get("scrap_cost", 120.0)))
    c = d.get("cell", {})
    wc = None
    if "workcell" in c:
        w = c["workcell"]
        wc = Workcell(base=tuple(float(x) for x in w.get("base", (0, 0, 0))), reach=float(w.get("reach", 0.85)),
                      min_reach=float(w.get("min_reach", 0.1)),
                      zones=tuple(Zone(z["name"], Box(tuple(z["box"][:3]), tuple(z["box"][3:]))) for z in w.get("zones", [])))
    return proc, Cell(tools=fs(c.get("tools", [])), workcell=wc)


def dump_process(proc: Process, cell: Optional[Cell] = None, name: str = "process") -> Dict[str, Any]:
    steps = []
    for sid in proc.order:
        s = proc.steps[sid]
        steps.append({
            "id": s.id, "label": s.label, "forward": s.forward_cost,
            "undo": None if s.irreversible else s.undo_cost,
            "requires": sorted(s.requires), "covered_by": sorted(s.covered_by),
            "irreversible": s.irreversible, "irreversible_reason": s.irreversible_reason,
            "undo_damage": s.undo_damage, "tool": s.tool, "pos": list(s.pos) if s.pos else None})
    cd: Dict[str, Any] = {"tools": sorted(cell.tools) if cell else []}
    if cell and cell.workcell:
        w = cell.workcell
        cd["workcell"] = {"base": list(w.base), "reach": w.reach, "min_reach": w.min_reach,
                          "zones": [{"name": z.name, "box": list(z.box.lo) + list(z.box.hi)} for z in w.zones]}
    return {"name": name, "scrap_cost": proc.scrap_cost,
            "cell": cd,
            "steps": steps,
            "variants": [{"name": v.name, "required": sorted(v.required), "tolerated": sorted(v.tolerated)}
                         for v in proc.variants.values()]}


# --------------------------------------------------------------------------- independent annotation
SHEET_COLUMNS = ["step_id", "label", "can_be_undone (yes/no)", "chance_undo_damages_part (0-1)",
                 "steps_that_must_be_removed_first (ids, ; separated)", "notes"]


def annotation_sheet(proc: Process) -> str:
    """A blinded CSV for a domain expert. It shows labels and step order but none of the
    reversibility, damage or blocking values, so the answers are independent of the code's author."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(SHEET_COLUMNS)
    for sid in proc.order:
        w.writerow([sid, proc.steps[sid].label, "", "", "", ""])
    return out.getvalue()


def compare_annotation(proc: Process, filled_csv: str) -> Dict[str, Any]:
    """Agreement between an independent annotation and the process's own values.

    Reports raw agreement and Cohen's kappa on reversibility, mean absolute error on undo damage,
    and precision and recall on the undo-dependency relation (what must come off first).
    """
    rows = list(csv.DictReader(io.StringIO(filled_csv)))
    both, agree = [], 0
    a_yes = b_yes = 0
    mae, n_mae = 0.0, 0
    tp = fp = fn = 0
    for r in rows:
        sid = r["step_id"]
        if sid not in proc.steps:
            raise ProcessError(f"annotation references unknown step {sid}")
        ans = r["can_be_undone (yes/no)"].strip().lower()
        if ans not in ("yes", "no"):
            continue
        ours = not proc.steps[sid].irreversible
        theirs = ans == "yes"
        both.append((ours, theirs))
        agree += ours == theirs
        a_yes += ours
        b_yes += theirs
        dmg = r["chance_undo_damages_part (0-1)"].strip()
        if dmg and theirs and ours:
            mae += abs(float(dmg) - proc.steps[sid].undo_damage)
            n_mae += 1
        theirs_dep = {x.strip() for x in r["steps_that_must_be_removed_first (ids, ; separated)"].split(";") if x.strip()}
        ours_dep = set(proc.dependents[sid])
        tp += len(theirs_dep & ours_dep)
        fp += len(theirs_dep - ours_dep)
        fn += len(ours_dep - theirs_dep)
    n = len(both)
    po = agree / n if n else float("nan")
    pe = ((a_yes / n) * (b_yes / n) + (1 - a_yes / n) * (1 - b_yes / n)) if n else float("nan")
    kappa = (po - pe) / (1 - pe) if n and pe != 1 else float("nan")
    return {"steps_annotated": n, "reversibility_agreement": po, "cohens_kappa": kappa,
            "damage_mae": mae / n_mae if n_mae else float("nan"),
            "dependency_precision": tp / (tp + fp) if tp + fp else float("nan"),
            "dependency_recall": tp / (tp + fn) if tp + fn else float("nan")}
