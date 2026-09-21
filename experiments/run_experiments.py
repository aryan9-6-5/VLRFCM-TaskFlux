"""Run every experiment and write tables, CSVs and figures to experiments/results.

    python -m experiments.run_experiments            # full run
    python -m experiments.run_experiments --quick    # smaller sample, for a smoke test

All numbers come from the step-level simulator with the assumed parameters in
taskflux.sim.SimParams. They characterise the planning layer, not a robot.
"""
from __future__ import annotations

import argparse
import math
import random
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from taskflux.examples import GEARBOX_CELL, gearbox
from taskflux.metrics import mean_ci, wilson
from taskflux.reconcile import reconcile
from taskflux.sim import (SYSTEMS, SimParams, delayed_change_episode, false_change_episode, no_change_episode,
                          run_episode)
from taskflux.synth import SynthConfig, random_process
from taskflux.triage import ABORT, CHANGE, Action, TriageParams, build_context, decide, fixed_threshold
from experiments import provenance
from taskflux.utterances import INTENTS, IntentClassifier, ece, lexical_stop, make_split

OUT = Path(__file__).parent / "results"
OUT.mkdir(exist_ok=True)
PRM = SimParams()
DET = SimParams(p_forward=1.0, p_undo_retry=0.0, damage_scale=0.0)   # deterministic, for paired comparisons
LABEL = {"B1": "B1 stock, ignore change", "B2": "B2 restart", "B3a": "B3a replan, no reconciler",
         "B3b": "B3b replan, order diff", "TF": "TaskFlux"}


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def states(p, current="A"):
    order = p.topo_order(p.goal(current))
    return [order[:k] for k in range(1, len(order))]      # k = 0 is a fresh bench, k = n is a finished product


# --------------------------------------------------------------------------- E1
def e1_changeover(n_gearbox: int, n_procs: int, eps_per: int):
    rows = []
    p = gearbox()
    for k, C in enumerate(states(p), start=1):
        for sysname in SYSTEMS:
            for i in range(n_gearbox):
                rng = random.Random(f"g-{k}-{sysname}-{i}")
                ep = run_episode(p, sysname, C, "A", "B", rng, PRM, cell=GEARBOX_CELL)
                rows.append(dict(source="gearbox", k=k, system=sysname, **_row(ep)))
    rng0 = random.Random(2026)
    for pi in range(n_procs):
        q = random_process(rng0)
        for k, C in enumerate(states(q), start=1):
            for sysname in SYSTEMS:
                for i in range(eps_per):
                    rng = random.Random(f"s-{pi}-{k}-{sysname}-{i}")
                    ep = run_episode(q, sysname, C, "A", "B", rng, PRM)
                    rows.append(dict(source="synthetic", k=k, system=sysname, **_row(ep)))
    return pd.DataFrame(rows)


def _row(ep):
    return dict(stage=ep.stage, success=ep.success, outcome=ep.outcome, total_time=ep.total_time,
                al=ep.al, ttp=ep.ttp, undo=ep.undo_actions, done=ep.completed_before, rc=ep.rework_cost,
                unnecessary=ep.unnecessary_undos, scrapped=ep.scrapped, escalated=ep.escalated, destroyed=ep.destroyed, damaged_at=ep.damaged_at,
                t_reconcile=ep.t_reconcile)


def summarise_e1(df: pd.DataFrame, source: str, systems=None) -> str:
    systems = systems or SYSTEMS
    d = df[df.source == source]
    out = []
    for stage in ["truncation", "undo", "risky", "irreversible"]:
        s = d[d.stage == stage]
        if s.empty:
            continue
        rows = []
        for sysname in systems:
            g = s[s.system == sysname]
            n = len(g)
            ok = int(g.success.sum())
            lo, hi = wilson(ok, n)
            succ = g[g.success]
            destroyed = int(g.destroyed.sum())
            rows.append({
                "system": LABEL[sysname],
                "n": n,
                "CSR": f"{100 * ok / n:.1f}% [{100 * lo:.0f}-{100 * hi:.0f}]",
                "rework (undo/done)": f"{g.rc.mean():.2f}",
                "unneeded undos": f"{g.unnecessary.mean():.2f}",
                "scrapped": f"{100 * g.scrapped.mean():.0f}%",
                "destroyed": f"{100 * destroyed / n:.0f}%",
                "AL s": "-" if g.al.isna().all() else f"{g.al.mean():.1f}",
                "TTP s": "-" if g.ttp.isna().all() else f"{g.ttp.mean():.1f}",
                "time s (successes)": "-" if succ.empty else f"{succ.total_time.mean():.0f}",
            })
        out.append(f"**{source}, stage = {stage}** ({len(s) // len(systems)} episodes per system)\n\n" + md_table(pd.DataFrame(rows)))
    return "\n\n".join(out)


def fig_rc(df: pd.DataFrame):
    g = df[df.source == "gearbox"]
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    for sysname in ["B2", "B3b", "TF"]:
        s = g[g.system == sysname].groupby("k")
        ax[0].plot(s.rc.mean().index, s.rc.mean().values, marker="o", label=LABEL[sysname])
        ax[1].plot(s.success.mean().index, s.success.mean().values, marker="o", label=LABEL[sysname])
    ax[0].set_xlabel("steps completed before change (k)"); ax[0].set_ylabel("rework cost (undo / done)")
    ax[1].set_xlabel("steps completed before change (k)"); ax[1].set_ylabel("changeover success rate")
    ax[0].set_title("Rework cost, gearbox"); ax[1].set_title("Success (scrap-and-restart counts as success)")
    ax[0].legend(fontsize=8); fig.tight_layout(); fig.savefig(OUT / "e1_gearbox_rework.png", dpi=150); plt.close(fig)


# --------------------------------------------------------------------------- E2
def sim_times(p, C, cell, delay=60.0):
    """Time to a finished correct product for each response in each world, from the step simulator.

    Deliberately independent of the closed-form costs in taskflux.triage that drive the decision.
    A response that does not end in the right product (or that the reconciler would not allow) is infinite.
    """
    r = lambda: random.Random(0)
    fin = lambda ep: ep.total_time if ep.success else math.inf
    act_ok = reconcile(p, C, "B", cell).status.value == "proceed"
    T = {}
    T[("ACT", "change")] = fin(run_episode(p, "TF", C, "A", "B", r(), DET, cell=cell))
    T[("CONT", "change")] = fin(delayed_change_episode(p, C, "A", "B", r(), DET, delay, cell))
    T[("IDLE", "change")] = fin(run_episode(p, "TF", C, "A", "B", r(), DET, cell=cell, ask="idle"))
    T[("HEDGE", "change")] = fin(run_episode(p, "TF", C, "A", "B", r(), DET, cell=cell, ask="hedge"))
    T[("ACT", "nochange")] = fin(false_change_episode(p, C, "A", "B", r(), DET, delay, cell)) if act_ok else math.inf
    T[("CONT", "nochange")] = fin(no_change_episode(p, C, "A", r(), DET, "none"))
    T[("IDLE", "nochange")] = fin(no_change_episode(p, C, "A", r(), DET, "idle"))
    T[("HEDGE", "nochange")] = fin(no_change_episode(p, C, "A", r(), DET, "hedge"))
    if not act_ok:
        T[("ACT", "change")] = math.inf      # never executed blindly; the ask path is the real response
    return T


def sim_regret(T, key, world):
    """Seconds lost against the best response. Asking also costs the operator's attention (a stated
    parameter, not something the step simulator can time), charged the same way the decision rule charges it."""
    extra = TriageParams().operator_cost if key in ("IDLE", "HEDGE") else 0.0
    best = min(T[(k, world)] + (TriageParams().operator_cost if k in ("IDLE", "HEDGE") else 0.0)
               for k in ("ACT", "CONT", "IDLE", "HEDGE"))
    return T[(key, world)] + extra - best


def e2_triage(n_utt: int, n_procs: int, seed: int = 7):
    clf = IntentClassifier.train()
    xs, ys = make_split("test", 400, seed)
    P = clf.proba(xs)
    acc = float((P.argmax(1) == np.array(ys)).mean())
    calib = ece(P, ys)
    # deployment prior: changeovers are rare, aborts rarer. Correct the balanced-training posterior.
    prior = np.array([0.35, 0.35, 0.22, 0.08])
    Pc = P * (prior / 0.25)
    Pc = Pc / Pc.sum(1, keepdims=True)
    y = np.array(ys)
    halt_thr = TriageParams().p_halt
    stop_lex = np.array([lexical_stop(x) for x in xs])
    Pl = Pc.copy()                       # with the lexical safety override
    Pl[stop_lex] = np.array([0.0, 0.0, 0.0, 1.0])
    meta_safety = dict(
        clf_only=float((Pc[y == ABORT, ABORT] >= halt_thr).mean()),
        with_lex=float((Pl[y == ABORT, ABORT] >= halt_thr).mean()),
        false_halt_clf=float((Pc[y != ABORT, ABORT] >= halt_thr).mean()),
        false_halt_lex=float((Pl[y != ABORT, ABORT] >= halt_thr).mean()))

    rng = random.Random(seed)
    procs = [("gearbox", gearbox(), GEARBOX_CELL)] + [("synthetic", random_process(rng), None) for _ in range(n_procs)]
    by_class = {c: np.where(y == c)[0] for c in range(4)}
    policies = ["oracle", "TaskFlux", "TaskFlux (no hedge)", "TaskFlux (no stop override)", "fixed 0.5", "fixed 0.3", "always ask (idle)",
                "always ask (hedge)", "never act"]
    rows = []
    for src, p, cell in procs:
        n_k = len(states(p)) + 1
        for k, C in enumerate(states(p), start=1):
            ctx_h = build_context(p, C, "A", "B", TriageParams(hedge=True), cell)
            ctx_n = build_context(p, C, "A", "B", TriageParams(hedge=False), cell)
            T = sim_times(p, C, cell)
            stage = "early" if k / n_k < 1 / 3 else ("mid" if k / n_k < 2 / 3 else "late")
            for _ in range(n_utt):
                truth = rng.choices(range(4), weights=prior)[0]
                i = int(rng.choice(by_class[truth]))
                pr = Pl[i]
                acts = {
                    "oracle": {CHANGE: (Action.ACT if ctx_h.act_allowed else Action.ASK), 0: Action.CONTINUE,
                               1: Action.CONTINUE, ABORT: Action.HALT}[truth],
                    "TaskFlux": decide(pr, ctx_h, TriageParams(hedge=True)),
                    "TaskFlux (no hedge)": decide(pr, ctx_n, TriageParams(hedge=False)),
                    "TaskFlux (no stop override)": decide(Pc[i], ctx_h, TriageParams(hedge=True)),
                    "fixed 0.5": fixed_threshold(pr, 0.5),
                    "fixed 0.3": fixed_threshold(pr, 0.3),
                    "always ask (idle)": Action.HALT if pr[ABORT] >= halt_thr else Action.ASK,
                    "always ask (hedge)": Action.HALT if pr[ABORT] >= halt_thr else Action.ASK,
                    "never act": Action.HALT if pr[ABORT] >= halt_thr else Action.CONTINUE,
                }
                for pol in policies:
                    a = acts[pol]
                    hedges = pol in ("TaskFlux", "TaskFlux (no stop override)", "always ask (hedge)", "oracle")
                    c = ctx_h if hedges else ctx_n
                    if a == Action.ACT and not c.act_allowed:
                        a = Action.ASK              # an irreversible plan is never executed blindly
                    world = "change" if truth == CHANGE else "nochange"
                    if truth == ABORT:
                        reg = 0.0 if a == Action.HALT else math.inf
                    elif a == Action.HALT:
                        reg = TriageParams().halt_cost
                    else:
                        key = {Action.ACT: "ACT", Action.CONTINUE: "CONT",
                               Action.ASK: "HEDGE" if hedges else "IDLE"}[a]
                        reg = sim_regret(T, key, world)
                    rows.append(dict(src=src, stage=stage, policy=pol, truth=INTENTS[truth], action=a.value,
                                     regret=reg, unsafe=math.isinf(reg)))
    return pd.DataFrame(rows), dict(acc=acc, ece=calib, T=clf.temperature, **meta_safety)


def summarise_e2(df: pd.DataFrame, meta) -> str:
    rows = []
    for pol in df.policy.unique():
        g = df[df.policy == pol]
        gs = g[~g.unsafe]
        m, hw = mean_ci(gs.regret.tolist())
        rows.append({"policy": pol, "mean regret (s)": f"{m:.1f} +/- {hw:.1f}",
                     "early": f"{gs[gs.stage == 'early'].regret.mean():.1f}",
                     "mid": f"{gs[gs.stage == 'mid'].regret.mean():.1f}",
                     "late": f"{gs[gs.stage == 'late'].regret.mean():.1f}",
                     "ask %": f"{100 * (g.action == 'ask').mean():.0f}",
                     "unsafe (missed stop)": int(g.unsafe.sum())})
    head = (f"Intent classifier on held-out templates: accuracy {100 * meta['acc']:.1f}%, ECE {meta['ece']:.3f} after "
            f"temperature scaling (T = {meta['T']:.2f}).\n\n"
            f"Stop requests that reach the halt threshold: classifier alone {100 * meta['clf_only']:.1f}%, with the lexical "
            f"override {100 * meta['with_lex']:.1f}%. Non-stop utterances that halt anyway: classifier alone "
            f"{100 * meta['false_halt_clf']:.1f}%, with the override {100 * meta['false_halt_lex']:.1f}%.\n\n"
            "Regret is scored by the step simulator (seconds lost against the best response in the true world), not by the "
            "formulas that drive the decision. All rows use the lexical override.\n\n")
    return head + md_table(pd.DataFrame(rows))


def fig_triage(df: pd.DataFrame):
    order = ["oracle", "TaskFlux", "TaskFlux (no hedge)", "fixed 0.5", "fixed 0.3", "always ask (hedge)", "never act"]
    g = df[~df.unsafe & df.policy.isin(order)]
    piv = g.groupby(["policy", "stage"]).regret.mean().unstack()[["early", "mid", "late"]].loc[order]
    ax = piv.plot(kind="bar", figsize=(9, 3.8))
    ax.set_ylabel("mean regret (s)"); ax.set_xlabel(""); ax.set_title("Triage regret by build stage (simulator-scored)")
    plt.xticks(rotation=25, ha="right"); plt.tight_layout(); plt.savefig(OUT / "e2_triage_regret.png", dpi=150); plt.close()


# --------------------------------------------------------------------------- E3
def e3_hedge(n_procs: int):
    rows = []
    rng0 = random.Random(11)
    procs = [gearbox()] + [random_process(rng0) for _ in range(n_procs)]
    for pi, p in enumerate(procs):
        cell = GEARBOX_CELL if pi == 0 else None
        for k, C in enumerate(states(p), start=1):
            bi = run_episode(p, "TF", C, "A", "B", random.Random(0), DET, cell=cell, ask="idle")
            bh = run_episode(p, "TF", C, "A", "B", random.Random(0), DET, cell=cell, ask="hedge")
            ai = no_change_episode(p, C, "A", random.Random(0), DET, ask="idle")
            ah = no_change_episode(p, C, "A", random.Random(0), DET, ask="hedge")
            if bi.escalated:
                continue                                       # nothing is hedged when B would be scrapped
            rows.append(dict(src="gearbox" if pi == 0 else "synthetic", k=k, hedged=bh.hedged_steps,
                             gain_changeover=round(bi.total_time - bh.total_time, 3),
                             gain_nochange=round(ai.total_time - ah.total_time, 3),
                             al_idle=bi.al, al_hedge=bh.al))
    return pd.DataFrame(rows)


def summarise_e3(df: pd.DataFrame) -> str:
    rows = []
    for src in ["gearbox", "synthetic"]:
        d = df[df.src == src]
        has = d[d.hedged > 0]
        rows.append({"process set": src, "states": len(d), "states with a safe step": f"{100 * len(has) / len(d):.0f}%",
                     "time saved if change (s, all states)": f"{d.gain_changeover.mean():.1f}",
                     "time saved if no change (s, all states)": f"{d.gain_nochange.mean():.1f}",
                     "worst case (s)": f"{min(d.gain_changeover.min(), d.gain_nochange.min()) + 0.0:.2f}",
                     "AL idle -> hedge (s)": f"{d.al_idle.mean():.1f} -> {d.al_hedge.mean():.1f}"})
    return md_table(pd.DataFrame(rows))


# --------------------------------------------------------------------------- E4
def e4_scaling():
    rows = []
    for n in [10, 25, 50, 100, 200, 400, 800]:
        rng = random.Random(n)
        cfg = SynthConfig(n_shared=n // 2, n_a=n // 4, n_b=n // 4)
        p = random_process(rng, cfg)
        order = p.topo_order(p.goal("A"))
        C = frozenset(order[: int(len(order) * 0.7)])
        t0 = time.perf_counter()
        for _ in range(20):
            reconcile(p, C, "B")
        rows.append(dict(steps=len(p.steps), ms=(time.perf_counter() - t0) / 20 * 1000))
    return pd.DataFrame(rows)


def fig_scaling(df):
    fig, ax = plt.subplots(figsize=(4.8, 3.4))
    ax.loglog(df.steps, df.ms, marker="o"); ax.set_xlabel("steps in process"); ax.set_ylabel("reconcile time (ms)")
    ax.set_title("Reconciler runtime"); fig.tight_layout(); fig.savefig(OUT / "e4_scaling.png", dpi=150); plt.close(fig)


# --------------------------------------------------------------------------- E5
def e5_sensitivity(n_procs: int):
    rows = []
    for p_irr in [0.0, 0.1, 0.25, 0.4]:
        rng0 = random.Random(int(p_irr * 100) + 5)
        for pi in range(n_procs):
            q = random_process(rng0, SynthConfig(p_irreversible=p_irr))
            for k, C in enumerate(states(q), start=1):
                for sysname in ["B2", "B3b", "TF"]:
                    ep = run_episode(q, sysname, C, "A", "B", random.Random(f"e5-{p_irr}-{pi}-{k}-{sysname}"), PRM)
                    rows.append(dict(p_irr=p_irr, system=sysname, success=ep.success, time=ep.total_time,
                                     scrapped=ep.scrapped, destroyed=ep.destroyed))
    d = pd.DataFrame(rows)
    out = []
    for p_irr in sorted(d.p_irr.unique()):
        for sysname in ["B2", "B3b", "TF"]:
            g = d[(d.p_irr == p_irr) & (d.system == sysname)]
            out.append({"irreversible rate": p_irr, "system": LABEL[sysname], "n": len(g),
                        "success": f"{100 * g.success.mean():.0f}%", "scrapped": f"{100 * g.scrapped.mean():.0f}%",
                        "destroyed": f"{100 * g.destroyed.mean():.0f}%", "mean time s": f"{g.time.mean():.0f}"})
    return d, md_table(pd.DataFrame(out))


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    q = ap.parse_args().quick
    t0 = time.time()
    report = ["# Experiment results (generated by experiments/run_experiments.py)\n",
              "Step-level simulation. Every number depends on the assumed parameters in `taskflux/sim.py` and is not a "
              "measurement of a physical robot or of OpenVLA. Success intervals are 95% Wilson. "
              "`CSR` counts a scrap-and-restart that ends in the right product as a success; `scrapped` and `destroyed` "
              "are reported next to it so that cost stays visible.\n",
              f"Produced by: {provenance.report()}\n"]

    print("E1 changeover systems ..."); df1 = e1_changeover(20 if q else 300, 15 if q else 400, 1 if q else 3)
    df1.to_csv(OUT / "e1_changeover.csv", index=False)
    fig_rc(df1)
    report += ["## E1. Changeover with the intent already known, four baselines\n", summarise_e1(df1, "gearbox"), "",
               summarise_e1(df1, "synthetic"), "", "![rework](e1_gearbox_rework.png)\n"]

    print("E2 triage ..."); df2, meta = e2_triage(3 if q else 40, 8 if q else 120)
    df2.to_csv(OUT / "e2_triage.csv", index=False)
    fig_triage(df2)
    report += ["## E2. Triage under classifier uncertainty\n", summarise_e2(df2, meta), "", "![triage](e2_triage_regret.png)\n"]

    print("E3 hedge ..."); df3 = e3_hedge(10 if q else 300)
    df3.to_csv(OUT / "e3_hedge.csv", index=False)
    report += ["## E3. Hedged execution while confirmation is pending\n", summarise_e3(df3), ""]

    print("E4 scaling ..."); df4 = e4_scaling(); df4.to_csv(OUT / "e4_scaling.csv", index=False); fig_scaling(df4)
    report += ["## E4. Reconciler runtime\n", md_table(df4.round(3)), "", "![scaling](e4_scaling.png)\n"]

    print("E5 sensitivity ..."); d5, t5 = e5_sensitivity(8 if q else 150)
    d5.to_csv(OUT / "e5_sensitivity.csv", index=False)
    report += ["## E5. Sensitivity to the irreversible-step rate\n", t5, ""]

    from experiments import phase0
    print("E1b second process ..."); dfb = phase0.run_systems(SYSTEMS, 20 if q else 300, 0, 0, names=["sensor_module"])
    report += ["## E1b. The same comparison on a second process (sensor module, examples/sensor_module.json)\n",
               summarise_e1(dfb, "sensor_module"), ""]

    print("E6 ablations ..."); dfa = phase0.run_systems(phase0.ABL_SYSTEMS, 20 if q else 200, 15 if q else 150, 1)
    report += ["## E6. What each rule of the reconciler is worth (ablations)\n",
               "Each row removes one rule. `no_refusal` attempts irreversible removals, `no_scrap_choice` never trades "
               "salvage against scrap on damage risk, `no_cascade` undoes only the forced roots, `no_cover_rule` ignores "
               "that a present cover blocks a step still to be built, `no_tolerated` removes harmless extras.\n",
               phase0.summarise_ablation(dfa, "gearbox"), "", phase0.summarise_ablation(dfa, "sensor_module"), "",
               phase0.summarise_ablation(dfa, "synthetic"), ""]

    print("E7 failure analysis ...")
    dfall = pd.concat([df1.assign(failed_at=""), dfb, dfa[dfa.system == "TF"]], ignore_index=True)
    report += ["## E7. Failure analysis\n", phase0.failure_analysis(dfall), ""]

    print("E8 perception noise ..."); dfp = phase0.e8_perception(15 if q else 60, 20 if q else 100)
    dfp.to_csv(OUT / "e8_perception.csv", index=False)
    phase0.fig_e8(dfp, OUT / "e8_perception.png")
    report += ["## E8. Perception noise: acting on a state the verifier may have got wrong\n",
               "Each step of the true state is independently misread with the stated error rate (a finished step seen as "
               "missing, and an unfinished one seen as done, both at that rate). Inspections are exact and cost 6 s each. "
               "Times are for successful episodes only, because failed episodes stop early and would look fast.\n",
               phase0.summarise_e8(dfp), "",
               "**Expected time to a correct product when a failed changeover costs 450 s extra** (an assumption: the "
               "operator steps in, the workpiece is scrapped and rebuilt). Seconds, lower is better.\n",
               phase0.summarise_e8_expected(dfp), "", "![perception](e8_perception.png)\n"]

    (OUT / "results.md").write_text("\n".join(report), encoding="utf-8")
    print(f"done in {time.time() - t0:.0f}s -> {OUT / 'results.md'}")


if __name__ == "__main__":
    main()
