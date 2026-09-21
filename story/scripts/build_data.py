"""Build the evidence file the story page reads: story/src/data/evidence.json.

    python story/scripts/build_data.py

Nothing on the page is typed in by hand except prose. The workpiece plans come from the reconciler, the
strategy comparison and the results bars from the simulator (same seeds and sample sizes as experiment E1),
the perception bars from experiment E8, and the triage examples from the real controller.
"""
from __future__ import annotations

import json
import random
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from demo.build_demo import layout, plan_dict  # noqa: E402
from experiments import phase0  # noqa: E402
from experiments.run_experiments import PRM, e1_changeover  # noqa: E402
from taskflux.controller import Controller  # noqa: E402
from taskflux.examples import GEARBOX_CELL, gearbox  # noqa: E402
from taskflux.hedge import safe_steps  # noqa: E402
from taskflux.sim import run_episode  # noqa: E402
from taskflux.triage import TriageParams, build_context  # noqa: E402
from taskflux.utterances import IntentClassifier  # noqa: E402

OUT = ROOT / "story" / "src" / "data" / "evidence.json"

# Figures that come from the written record rather than from a run. Each has a pointer to where it is stated;
# tests/test_story_data.py checks that the pointer still says it.
FACTS = {
    "errors_fixed": {"value": 15, "source": "docs/07-weekly-progress-report.md", "quote": "Fifteen modelling errors in total"},
    "stop_missed_pct": {"value": 11.5, "source": "docs/06-implementation-and-results.md", "quote": "misses about 11.5% of stops"},
    "random_processes": {"value": 40, "source": "docs/05-novelty-and-formal-results.md", "quote": "on 40 random small processes"},
    "withdrawn_gap": {"value": [99.9, 84.7], "source": "docs/06-implementation-and-results.md", "quote": "99.9% against 84.7%"},
    "novelty": {"value": "moderate", "source": "docs/05-novelty-and-formal-results.md", "quote": "Honest strength assessment: moderate"},
}

SOURCES = {
    "problem": "taskflux reconciler and simulator, gearbox process, six steps done (story/scripts/build_data.py)",
    "plans": "taskflux reconciler on examples/gearbox, plans at 9 and 10 steps done (story/scripts/build_data.py)",
    "triage": "taskflux controller on four scripted sentences (story/scripts/build_data.py)",
    "results": "experiments/results/results.md, E1 gearbox (undo 1,200 runs each, truncation 1,500, irreversible 300)",
    "perception": "experiments/results/results.md, E8 synthetic processes, 5% misread rate",
}


def count_tests() -> int:
    out = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
                         cwd=ROOT, capture_output=True, text=True).stdout
    m = re.search(r"(\d+) tests? collected", out) or re.search(r"(\d+) tests?", out)
    return int(m.group(1)) if m else 0



def main() -> None:
    p, cell = gearbox(), GEARBOX_CELL
    order = p.topo_order(p.goal("A"))
    pos, group, level, width, height, (nw, nh) = layout(p)

    steps = [{"id": s, "label": p.steps[s].label, "x": pos[s][0], "y": pos[s][1], "group": group[s],
              "irreversible": p.steps[s].irreversible, "why": p.steps[s].irreversible_reason} for s in p.order]
    edges = {"requires": [[r, s] for s in p.order for r in sorted(p.steps[s].requires)],
             "covers": [[u, s] for s in p.order for u in sorted(p.steps[s].covered_by)]}

    # ---- chapter 1: what each strategy does at the moment of the change (deterministic, no random damage)
    det = PRM.__class__(p_forward=1.0, p_forward_novel=1.0, p_undo_retry=0.0, damage_scale=0.0)
    k = 6
    done = order[:k]
    problem = {"k": k, "done": done, "utterance": "switch to the B housing, skip the foam gasket", "strategies": {}}
    for key in ("B2", "B3b", "B3a", "TF"):
        ep = run_episode(p, key, done, "A", "B", random.Random(0), det, cell=cell)
        problem["strategies"][key] = {"undone": list(ep.undone) + list(ep.lost), "outcome": ep.outcome, "failed_at": ep.failed_at,
                                      "time": round(ep.total_time)}

    # ---- chapters 3 and 4: the reconciler's plans
    plans = {str(kk): plan_dict(p, frozenset(order[:kk]), cell) for kk in (6, 9, 10)}
    plans["9"]["done"] = order[:9]
    plans["10"]["done"] = order[:10]

    # ---- chapter 5: triage on four real utterances
    clf = IntentClassifier.train()
    scenes = [("switch to the B housing, skip the foam gasket", 6, "a direct changeover"),
              ("turns out the paperwork says the B housing", 8, "an indirect changeover"),
              ("no, the other screw", 8, "a clarification"),
              ("not safe, stop", 8, "a stop request")]
    triage = []
    for text, kk, kind in scenes:
        c = Controller(p, "A", "B", clf, cell, done=set(order[:kk]))
        r = c.hear(text)
        ctx = build_context(p, frozenset(order[:kk]), "A", "B", TriageParams(), cell)
        triage.append({"text": text, "k": kk, "kind": kind, "action": r.action.value, "say": r.say,
                       "probs": [round(float(x), 3) for x in r.probs], "hedged": list(r.hedged),
                       "ra": round(ctx.act_regret), "rc": round(ctx.continue_regret), "ca": round(ctx.ask_regret)})

    # ---- chapter 5, last step: what is safe to build while waiting for an answer
    hk = 2
    hedge = {"k": hk, "done": order[:hk], "safe": safe_steps(p, frozenset(order[:hk]), "A", "B")}

    # ---- chapter 8: results bars, from the same runs as experiment E1 (gearbox, 300 episodes per state)
    df = e1_changeover(300, 0, 1)
    g = df[df.source == "gearbox"]
    results = {}
    for stage in ("truncation", "undo", "irreversible"):
        s = g[g.stage == stage]
        row = {}
        for key in ("B2", "B3a", "B3b", "TF"):
            x = s[s.system == key]
            ok = x[x.success]
            row[key] = {"time": None if ok.empty else round(float(ok.total_time.mean())),
                        "success": round(float(x.success.mean()), 3), "lost": round(float(x.destroyed.mean()), 3),
                        "unneeded": round(float(x.unnecessary.mean()), 2), "rework": round(float(x.rc.mean()), 2), "n": int(len(x))}
        results[stage] = row

    # ---- chapter 7: perception noise, from experiment E8 (same sizes as the full run)
    pe = phase0.e8_perception(60, 100)
    d = pe[(pe.source == "synthetic") & (pe.eps == 0.05)]
    perception = {}
    for pol in ("trust", "consistency", "inspect_undo", "inspect_critical", "inspect_all"):
        x = d[d.policy == pol]
        perception[pol] = {"success": round(float(x.success.mean()), 3), "inspections": round(float(x.inspections.mean()), 1)}
    cons = pe[(pe.source == "synthetic") & (pe.eps == 0.05) & (pe.policy == "consistency") & pe.had_error]
    perception["noticed"] = round(float(cons.flagged.mean()), 2)
    perception["n"] = int(len(d[d.policy == "trust"]))

    data = {"steps": steps, "edges": edges, "box": {"w": nw, "h": nh, "width": width, "height": height}, "order": order,
            "problem": problem, "plans": plans, "triage": triage, "hedge": hedge, "results": results, "perception": perception,
            "facts": {**FACTS, "tests": {"value": count_tests(), "source": "pytest --collect-only"}}, "sources": SOURCES,
            "counts": {"gearbox_runs_per_system": sum(r["TF"]["n"] for r in results.values()), "situations": [[k2, r["TF"]["n"]] for k2, r in results.items()],
                       "answers_compared": 4, "processes": len(list((ROOT / "examples").glob("*.json")))}}
    OUT.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    print("wrote", OUT, OUT.stat().st_size // 1024, "KB")
    for stage, row in results.items():
        print(stage, {k2: (v["time"], v["lost"]) for k2, v in row.items()})
    print("hedge", hedge)
    print("triage", [(t["k"], t["action"], t["hedged"]) for t in triage])
    print("perception", perception)
    print("problem", {k2: (v["undone"], v["outcome"], v["failed_at"]) for k2, v in problem["strategies"].items()})


if __name__ == "__main__":
    main()
