"""Build demo/index.html: a self-contained page that visualises the prototype.

    python -m demo.build_demo

Everything on the page is computed by the real code in taskflux/ and embedded as JSON: the reconciler's
plan at every stage of the build, the classifier's probabilities and the triage decision for a handful of
operator utterances, and averaged simulator runs for the comparison bars. Nothing is computed in the
browser, and no network or server is needed.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from taskflux.controller import Controller
from taskflux.examples import GEARBOX_CELL, gearbox
from taskflux.hedge import safe_steps
from taskflux.metrics import wilson
from taskflux.reconcile import Status, reconcile
from taskflux.sim import SimParams, change_stage, run_episode
from taskflux.triage import TriageParams, build_context
from taskflux.utterances import IntentClassifier

HERE = Path(__file__).resolve().parent
UTTERANCES = [
    ("switch to the B housing, skip the foam gasket", "a direct changeover"),
    ("we're building variant B instead", "a direct changeover"),
    ("turns out the paperwork says the B housing", "an indirect changeover"),
    ("no, the other screw", "a clarification, not a change"),
    ("use 12 Nm instead of the default torque", "a parameter edit"),
    ("not safe, stop", "a stop request"),
]
SYSTEMS = {"TF": "TaskFlux", "B2": "Restart from scratch", "B3b": "Replan by comparing build orders",
           "B3a": "Replan and build on top"}
RUNS = 150


def layout(p):
    """Columns by dependency depth across both variants; rows grouped A-only, shared, B-only."""
    A, B = p.goal("A"), p.goal("B")
    level = {}

    def lv(s):
        if s not in level:
            level[s] = 1 + max((lv(r) for r in p.steps[s].requires), default=-1)
        return level[s]

    for s in p.order:
        lv(s)
    group = {s: ("shared" if s in A and s in B else "A" if s in A else "B") for s in p.order}
    NW, NH, DX, DY = 132, 48, 168, 60
    y0, out = 34, {}
    for g in ("A", "shared", "B"):
        members = [s for s in p.order if group[s] == g]
        stack = {}
        for s in members:
            stack.setdefault(level[s], []).append(s)
        for lvl, ss in stack.items():
            for i, s in enumerate(ss):
                out[s] = (16 + lvl * DX, y0 + i * DY)
        y0 += max((len(v) for v in stack.values()), default=1) * DY + 40
    width = 16 + (max(level.values()) + 1) * DX
    return out, group, level, width, y0, (NW, NH)


def plan_dict(p, C, cell):
    plan = reconcile(p, C, "B", cell)
    scrap = plan.status != Status.PROCEED
    order_G = p.topo_order(p.goal("B"))
    return {
        "status": plan.status.value,
        "keep": sorted(plan.keep), "discard": sorted(plan.discard),
        "undo": [] if scrap else list(plan.undo),
        "forward": order_G if scrap else list(plan.forward),
        "scrap": scrap,
        "blockers": [{"step": b.step, "kind": b.kind, "chain": list(b.chain)} for b in plan.blockers],
        "explanation": plan.explanation,
        "undo_time": None if scrap else round(plan.undo_time),
        "forward_time": round(sum(p.steps[s].forward_cost for s in order_G)) if scrap else round(plan.forward_time),
        "scrap_total": round(plan.scrap_total),
        "damage_prob": round(plan.damage_prob, 3),
    }


def main(runs: int = RUNS, out: Path | None = None) -> Path:
    p, cell = gearbox(), GEARBOX_CELL
    clf = IntentClassifier.train()
    order = p.topo_order(p.goal("A"))
    pos, group, level, width, height, (nw, nh) = layout(p)

    steps = []
    for s in p.order:
        st = p.steps[s]
        steps.append({"id": s, "label": st.label, "x": pos[s][0], "y": pos[s][1], "group": group[s],
                      "irreversible": st.irreversible, "why": st.irreversible_reason,
                      "forward": st.forward_cost, "undo": None if st.irreversible else st.undo_cost,
                      "damage": st.undo_damage})
    edges = {"requires": [[r, s] for s in p.order for r in sorted(p.steps[s].requires)],
             "covers": [[u, s] for s in p.order for u in sorted(p.steps[s].covered_by)]}

    states, responses, compare = [], [], []
    params = TriageParams()
    for k in range(len(order) + 1):
        C = frozenset(order[:k])
        ctx = build_context(p, C, "A", "B", params, cell)
        states.append({"k": k, "done": order[:k], "stage": change_stage(p, C, "B"),
                       "plan": plan_dict(p, C, cell), "safe": safe_steps(p, C, "A", "B"),
                       "ra": round(ctx.act_regret), "rc": round(ctx.continue_regret), "ca": round(ctx.ask_regret),
                       "act_allowed": ctx.act_allowed})
        row = []
        for text, _ in UTTERANCES:
            c = Controller(p, "A", "B", clf, cell, done=set(C))
            r = c.hear(text)
            row.append({"action": r.action.value, "say": r.say, "probs": [round(float(x), 3) for x in r.probs],
                        "hedged": list(r.hedged)})
        responses.append(row)
        cmp = {}
        for key in SYSTEMS:
            eps = [run_episode(p, key, order[:k], "A", "B", random.Random(f"demo-{k}-{key}-{i}"), SimParams(), cell=cell)
                   for i in range(runs)]
            ok = [e for e in eps if e.success]
            cmp[key] = {"time": round(sum(e.total_time for e in ok) / len(ok)) if ok else None,
                        "success": round(len(ok) / len(eps), 3),
                        "lost": round(sum(e.destroyed for e in eps) / len(eps), 3),
                        "scrapped": round(sum(e.scrapped for e in eps) / len(eps), 3)}
        compare.append(cmp)

    data = {"steps": steps, "edges": edges, "states": states, "utterances": [{"text": t, "kind": k} for t, k in UTTERANCES],
            "responses": responses, "compare": compare, "systems": SYSTEMS, "runs": runs,
            "box": {"w": nw, "h": nh, "width": width, "height": height},
            "params": {"confirm_window": params.confirm_window, "discovery_delay": params.discovery_delay}}
    html = (HERE / "template.html").read_text(encoding="utf-8").replace("__DATA__", json.dumps(data, separators=(",", ":")))
    out = out or HERE / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
    return out


if __name__ == "__main__":
    main()
