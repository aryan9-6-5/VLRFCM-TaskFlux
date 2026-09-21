"""Phase 0 experiments: second process (E1b), reconciler ablations (E6), failure analysis (E7).

Called from run_experiments.main(). Kept separate so the original experiments stay readable.
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from taskflux.ablation import ABLATIONS
from taskflux.examples import GEARBOX_CELL, gearbox
from taskflux.metrics import wilson
from taskflux.sim import SYSTEMS, run_episode
from taskflux.spec import load_process
from taskflux.synth import random_process

from experiments.run_experiments import LABEL, PRM, _row, md_table, states, summarise_e1

EX = Path(__file__).resolve().parent.parent / "examples"
ABL_SYSTEMS = ["TF"] + [f"TF:{a}" for a in ABLATIONS[1:]]
LABEL.update({"TF": "TaskFlux (full)", **{f"TF:{a}": f"- {a}" for a in ABLATIONS[1:]}})


def named_processes() -> Dict[str, Tuple[object, object]]:
    return {"gearbox": (gearbox(), GEARBOX_CELL), "sensor_module": load_process(EX / "sensor_module.json")}


def run_systems(systems: List[str], n_named: int, n_procs: int, eps_per: int, names=None) -> pd.DataFrame:
    rows = []
    for name, (p, cell) in named_processes().items():
        if names and name not in names:
            continue
        for k, C in enumerate(states(p), start=1):
            for sysname in systems:
                for i in range(n_named):
                    ep = run_episode(p, sysname, C, "A", "B", random.Random(f"{name}-{k}-{sysname}-{i}"), PRM, cell=cell)
                    rows.append(dict(source=name, k=k, system=sysname, failed_at=ep.failed_at, **_row(ep)))
    if n_procs:
        rng0 = random.Random(2026)
        for pi in range(n_procs):
            q = random_process(rng0)
            for k, C in enumerate(states(q), start=1):
                for sysname in systems:
                    for i in range(eps_per):
                        ep = run_episode(q, sysname, C, "A", "B", random.Random(f"s-{pi}-{k}-{sysname}-{i}"), PRM)
                        rows.append(dict(source="synthetic", k=k, system=sysname, failed_at=f"{pi}:{ep.failed_at}" if ep.failed_at else "",
                                         **_row(ep)))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- E6
def summarise_ablation(df: pd.DataFrame, source: str) -> str:
    d = df[df.source == source]
    out = []
    for stage in ["truncation", "undo", "risky", "irreversible"]:
        s = d[d.stage == stage]
        if s.empty:
            continue
        rows = []
        for sysname in ABL_SYSTEMS:
            g = s[s.system == sysname]
            n = len(g)
            ok = int(g.success.sum())
            lo, hi = wilson(ok, n)
            succ = g[g.success]
            rows.append({"variant": LABEL[sysname], "n": n,
                         "CSR": f"{100 * ok / n:.1f}% [{100 * lo:.0f}-{100 * hi:.0f}]",
                         "collision": f"{100 * (g.outcome == 'collision').mean():.0f}%",
                         "destroyed (unplanned)": f"{100 * g.destroyed.mean():.0f}%",
                         "wrong product": f"{100 * (g.outcome == 'wrong_product').mean():.0f}%",
                         "unneeded undos": f"{g.unnecessary.mean():.2f}",
                         "time s (successes)": "-" if succ.empty else f"{succ.total_time.mean():.0f}"})
        out.append(f"**{source}, stage = {stage}** ({len(s) // len(ABL_SYSTEMS)} episodes per variant)\n\n" + md_table(pd.DataFrame(rows)))
    return "\n\n".join(out)


# --------------------------------------------------------------------------- E7
def failure_analysis(df: pd.DataFrame) -> str:
    """Why does TaskFlux fail, and where is it not the best choice? Uses the full-system rows of E1b/E6."""
    out = []
    tf = df[df.system == "TF"]
    # 1. how TaskFlux episodes end, by source and stage
    rows = []
    for (src, stage), g in tf.groupby(["source", "stage"]):
        n = len(g)
        c = g.outcome.value_counts()
        rows.append({"source": src, "stage": stage, "n": n,
                     "ok": int(c.get("ok", 0)), "scrapped_ok": int(c.get("scrapped_ok", 0)),
                     "destroyed then rebuilt": int(g.destroyed.sum()), "exec_failure (policy)": int(c.get("exec_failure", 0)),
                     "collision": int(c.get("collision", 0)), "wrong_product": int(c.get("wrong_product", 0))})
    out.append("**How TaskFlux episodes end**\n\n" + md_table(pd.DataFrame(rows)))
    # 2. which steps cause the failures
    bad = tf[~tf.success & (tf.failed_at != "")]
    if len(bad):
        top = (bad.groupby(["source", "outcome", "failed_at"]).size().reset_index(name="count")
               .sort_values("count", ascending=False).head(8))
        out.append("**Steps most often responsible for an unrecovered TaskFlux failure** (a policy step that failed after its retries)\n\n"
                   + md_table(top))
    # 2b. which undos destroy parts (these are recovered by scrap and rebuild, so they cost time and material, not success)
    lost = tf[tf.destroyed & (tf.damaged_at != "")]
    if len(lost):
        top = (lost.groupby(["source", "damaged_at"]).size().reset_index(name="parts destroyed")
               .sort_values("parts destroyed", ascending=False).head(6))
        out.append("**Undos that destroyed a part under TaskFlux (then scrapped and rebuilt)**\n\n" + md_table(top))
    # 3. where TaskFlux is not the fastest system that still gets the right product
    sysd = df[df.system.isin(["B2", "B3a", "B3b", "TF"])]
    rows = []
    for (src, stage), g in sysd.groupby(["source", "stage"]):
        t = g[g.success].groupby("system").total_time.mean()
        if "TF" in t and len(t) > 1:
            best = t.drop("TF").idxmin()
            rows.append({"source": src, "stage": stage, "TaskFlux s": f"{t['TF']:.0f}",
                         "fastest other": f"{LABEL.get(best, best)} {t[best]:.0f} s",
                         "TaskFlux slower by": f"{t['TF'] - t[best]:.1f} s" if t["TF"] > t[best] else "no (TaskFlux is fastest)"})
    out.append("**Time of successful episodes against the fastest baseline**\n\n" + md_table(pd.DataFrame(rows)))
    # 4. worst single states against restart
    piv = (df[df.system.isin(["B2", "TF"]) & df.success].groupby(["source", "k", "system"]).total_time.mean().unstack())
    if {"B2", "TF"} <= set(piv.columns):
        piv["TF minus restart"] = piv["TF"] - piv["B2"]
        worst = piv.sort_values("TF minus restart", ascending=False).head(5).reset_index()
        out.append("**States where TaskFlux is furthest behind restart** (positive = slower)\n\n"
                   + md_table(worst.round(1)))
    return "\n\n".join(out)


# --------------------------------------------------------------------------- E8
def e8_perception(n_named: int, n_procs: int) -> pd.DataFrame:
    from taskflux.perception import NoiseParams, POLICIES, run_noisy_episode
    rows = []
    sources = [(name, p, cell) for name, (p, cell) in named_processes().items()]
    rng0 = random.Random(77)
    sources += [(f"synthetic", random_process(rng0), None) for _ in range(n_procs)]
    for si, (name, p, cell) in enumerate(sources):
        reps = n_named if name != "synthetic" else 1
        for eps in [0.0, 0.02, 0.05, 0.10]:
            noise = NoiseParams(p_miss=eps, p_false=eps)
            for k, C in enumerate(states(p), start=1):
                truth = frozenset(C)
                for pol in POLICIES:
                    for i in range(reps):
                        r = run_noisy_episode(p, pol, truth, "A", "B", random.Random(f"e8-{si}-{eps}-{k}-{i}"), PRM, noise, cell)
                        e = r.episode
                        rows.append(dict(source=name, eps=eps, k=k, policy=pol, success=e.success, outcome=e.outcome,
                                         total_time=e.total_time, inspections=r.inspections, had_error=r.had_error,
                                         flagged=r.flagged, destroyed=e.destroyed, scrapped=e.scrapped))
    return pd.DataFrame(rows)


def summarise_e8(df: pd.DataFrame) -> str:
    out = []
    for src in ["gearbox", "sensor_module", "synthetic"]:
        d = df[df.source == src]
        rows = []
        for eps in sorted(d.eps.unique()):
            for pol in ["oracle", "trust", "consistency", "inspect_undo", "inspect_critical", "inspect_all"]:
                if pol == "oracle" and eps > 0:
                    continue
                g = d[(d.eps == eps) & (d.policy == pol)]
                n, ok = len(g), int(g.success.sum())
                lo, hi = wilson(ok, n)
                rows.append({"error rate": eps, "policy": pol, "n": n,
                             "CSR": f"{100 * ok / n:.1f}% [{100 * lo:.0f}-{100 * hi:.0f}]",
                             "collision": f"{100 * (g.outcome == 'collision').mean():.1f}%",
                             "wrong product": f"{100 * (g.outcome == 'wrong_product').mean():.1f}%",
                             "inspections": f"{g.inspections.mean():.1f}",
                             "time s (successes)": "-" if not g.success.any() else f"{g[g.success].total_time.mean():.0f}"})
        out.append(f"**{src}**\n\n" + md_table(pd.DataFrame(rows)))
    # how well the free consistency check detects errors
    det = []
    for src in ["gearbox", "sensor_module", "synthetic"]:
        for eps in [0.02, 0.05, 0.10]:
            g = df[(df.source == src) & (df.eps == eps) & (df.policy == "consistency")]
            err = g[g.had_error]
            harmful = err[~err.success] if False else err
            det.append({"process": src, "error rate": eps, "observations with an error": f"{100 * g.had_error.mean():.0f}%",
                        "error noticed by precedence": f"{100 * err.flagged.mean():.0f}%",
                        "false alarms": int((g[~g.had_error].flagged).sum())})
    out.append("**How often the free consistency check notices an observation error**\n\n" + md_table(pd.DataFrame(det)))
    return "\n\n".join(out)


def fig_e8(df: pd.DataFrame, out_path) -> None:
    import matplotlib.pyplot as plt
    d = df[df.source == "synthetic"]
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    for pol in ["trust", "consistency", "inspect_undo", "inspect_critical", "inspect_all"]:
        g = d[d.policy == pol].groupby("eps")
        ax[0].plot(g.success.mean().index * 100, g.success.mean().values * 100, marker="o", label=pol)
        gs = d[(d.policy == pol) & d.success].groupby("eps")      # successes only: failed episodes stop early
        ax[1].plot(gs.total_time.mean().index * 100, gs.total_time.mean().values, marker="o", label=pol)
    ax[0].set_xlabel("observation error rate (%)"); ax[0].set_ylabel("changeover success (%)")
    ax[1].set_xlabel("observation error rate (%)"); ax[1].set_ylabel("mean time of successful episodes (s)")
    ax[0].set_title("Success under perception noise (synthetic)"); ax[1].set_title("Cost of the policy")
    ax[0].legend(fontsize=8); fig.tight_layout(); fig.savefig(out_path, dpi=150); plt.close(fig)


def summarise_e8_expected(df: pd.DataFrame, penalty: float = 450.0) -> str:
    """Expected time to a correct product when a failed changeover costs ``penalty`` extra seconds.

    A collision or a wrong product means the operator steps in, the workpiece is scrapped and rebuilt:
    about the scrap cost plus a full build. 450 s is an assumption; the table shows how the ranking depends on it.
    """
    rows = []
    for src in ["gearbox", "sensor_module", "synthetic"]:
        d = df[df.source == src]
        for eps in [0.0, 0.02, 0.05, 0.10]:
            row = {"process": src, "error rate": eps}
            best, best_v = None, float("inf")
            for pol in ["trust", "consistency", "inspect_critical", "inspect_all"]:
                g = d[(d.eps == eps) & (d.policy == pol)]
                v = g[g.success].total_time.mean() + (1 - g.success.mean()) * penalty
                row[pol] = f"{v:.0f}"
                if v < best_v:
                    best, best_v = pol, v
            row["best"] = best
            rows.append(row)
    return md_table(pd.DataFrame(rows))
