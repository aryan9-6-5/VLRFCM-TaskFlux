# Novelty search, revised claims, and formal results

Written after a prior-art search and an implementation pass. It supersedes the "nothing addresses this" framing in `01-idea-and-novelty.md`, which turned out to be too strong.

## 1. What the search found

Searches run in September 2026 (web search, abstracts and pages read where reachable). Entries marked *verify* were seen in search results or abstracts only. Read the full paper and confirm authors, venue, year and claims before citing.

| Work | What it does | Relation to TaskFlux | Status |
|---|---|---|---|
| **SwitchVLA**, arXiv 2506.03574 (2025) | Task switching inside a VLA policy. Treats a new instruction mid-execution as behaviour modulation conditioned on execution state, using contact phases from demonstrations. | Closest competitor at the policy level. Its abstract and page describe no reasoning about step dependencies, reversibility, or which completed steps to undo. Complementary: it could be the low-level executor under TaskFlux's structural decision. | abstract read; *verify* full text |
| **Vision-Language-Policy model for dynamic robot task planning**, arXiv 2512.19178 | Pauses on a new instruction, passes task state, robot state and execution history with the instruction to a fine-tuned VLM, regenerates the plan. 50 trials, two platforms, over 70% execution success. | Forward replanning with history. No undo, dependency or irreversibility reasoning in the description. Behaves like our B3 baseline family. | page read; *verify* |
| **"Do This Instead": robots that adequately respond to corrected instructions**, ACM Trans. Human-Robot Interaction, DOI 10.1145/3623385 | Handles verbal corrections before, during and after taught task sequences in a cognitive architecture; replaces the goal or action and generates undo steps when needed (navigation, retrieval, meal assembly). | Closest prior work on *undoing on correction*. Rule-based, not tied to a VLA, no formal optimality or irreversibility analysis found in the summary. **Must be cited and differentiated.** Full text was not retrievable (HTTP 403). | search summary only; *verify* |
| Fox, Gerevini, Long, Serina, "Plan stability: replanning versus plan repair", ICAPS 2006 | Classical AI planning: repairing a partly executed plan versus replanning. | Establishes plan repair as a field. Goal change is a recognised trigger there. Our setting adds physical covering, irreversibility and a VLA executor. | *verify* authors |
| Nebel and Koehler, plan reuse / plan modification complexity (IJCAI 1993; AIJ 1995) | Conservative plan modification is in general as hard as planning from scratch. | Bounds what we may claim: our polynomial result depends on the precedence-and-cover structure of assembly, not on planning in general. | *verify* |
| Selective disassembly sequence planning (e.g. Yin et al., Proc. IMechE B, 2024, DOI 10.1177/09544054231201873) | Computes disassembly sequences to reach a target part, with precedence graphs and joint reversibility. | Our undo set is a selective disassembly where the target is a required goal. Prior art for the *undo ordering* idea. Not about goal replacement mid-build or language. | search summary; *verify* |
| KnowNo (Ren et al., CoRL 2023, arXiv 2307.01928) | Conformal prediction so an LLM planner asks for help when uncertain. | Prior art for "ask when unsure". Ours differs in that the ask threshold is derived from state-dependent regret and the wait is filled with provably safe work. | *verify* |
| Yell At Your Robot (arXiv 2403.12910), Hi Robot (arXiv 2502.19417) | Language corrections and interjections handled by a high-level policy over a low-level VLA. | Hierarchical correction handling. No physical-state reconciliation. | search summary; *verify* |
| Reversibility-aware learning ("Don't do things you can't undo", NeurIPS 2021 self-supervised reversibility work) | Learn which actions are reversible. | Related to our limitation that reversibility is hand-authored. A route to removing it. | title only; *verify* |

### Verdict on the original claims

| Original claim | Verdict |
|---|---|
| "No paper addresses mid-episode task change." | **False as stated.** SwitchVLA, the VLP model and "Do This Instead" all address some form of it. Remove the sentence from the paper draft. |
| "Nobody has written about the workspace not being empty after a change." | **Too strong.** Plan repair and undo-on-correction cover pieces of it. What we could not find is treatment of covering relations and irreversibility with a completeness guarantee. |
| Partial-assembly reconciliation is "the clearest novel contribution." | **Partly.** The concept has neighbours (plan repair, selective disassembly, undo generation). What is new is the formal treatment below and its coupling to triage and hedging. |
| "No benchmark exists for mid-episode task change." | **Narrowed.** One search found no benchmark that measures rework or refusal. InternVLA-M1 (arXiv 2510.13778) reports a test where new instructions arrive mid-execution (seen in search results only), so a mid-execution instruction test does exist. Say "we found none that measures rework or refusal" and search benchmarks properly before submission. |
| Retention-gated adapter merge. | **Engineering, not a research claim.** Kept as a component, validated only on a toy. |

## 2. Revised novelty claims, ranked by strength

1. **A formal treatment of goal replacement over a partly built assembly, with an exact refusal certificate** (Lemma 1). Not found in the reviewed literature. Individually simple, so the value is the characterisation and its use.
2. **Cost-coupled triage** (Proposition 3): the act, continue or ask decision uses error costs that come from the reconciler's own cost-to-go, so the required confidence moves with the state of the workpiece. Prior work asks when uncertain (KnowNo) but not with costs derived from partial-assembly state.
3. **Zero-regret hedged execution** (Lemma 2): while the operator's intent is unconfirmed, the robot works only on steps that are provably no worse in either world. Not found elsewhere.
4. **A measurement protocol and harness** for mid-episode changeover, five metrics, four baselines. No benchmark for this was found. Contribution as infrastructure.
5. **A reported negative result.** A min-cut formulation looked necessary and was not (section 3.2). Reporting that saves later readers the detour.

Honest strength assessment: moderate. Each algorithm is elementary. A workshop or short conference paper is realistic on the current evidence. A full paper needs the validation listed in section 6.

## 3. Formal results

### 3.1 Model

A process has a step universe `S`. Each step `s` has `requires(s) ⊆ S` (must be present first; acyclic) and `covered_by(s) ⊆ S` (once present, blocks access to `s`: `s` can be done or undone only while these are absent). Removing `s` first requires removing its **undo-dependents** `D(s) = {u : s ∈ requires(u)} ∪ covered_by(s)`. Each step has a forward cost, an undo cost, an undo damage probability, and an irreversibility flag (undo cost infinite).

A variant `T` has required steps `G` (closed under `requires`) and tolerated extras `H` (harmless to leave). A state `C` is the set of completed steps, closed under `requires`.

A changeover plan removes `U ⊆ C`, leaving `K = C \ U`, then builds `G \ K`. It is **valid** when:

* V1: `U` is closed under `D` within `C`;
* V2: `K ⊆ G ∪ H`;
* V3: for every `g ∈ G \ K`, `covered_by(g) ∩ K = ∅`.

### 3.2 Lemma 1 (unique minimum undo set, exact refusal)

Let `F0 = {s ∈ C : s ∉ G ∪ H} ∪ {u ∈ C : u ∈ covered_by(g) for some g ∈ G \ C}` and let `U*` be the closure of `F0` under `D` within `C`. Then:

* (a) every valid plan has `U ⊇ U*`;
* (b) `U*` is itself valid;
* (c) so for any cost that is non-decreasing in the undo set, `U*` is optimal, with no tuning of the cost model;
* (d) if `U*` contains an irreversible step, **no** valid plan avoids an irreversible undo. Escalation is then exactly right, not a heuristic giving up. The chain of steps from a forced root to the irreversible one is a human-readable certificate.

*Proof.* (a) A completed step outside `G ∪ H` cannot stay by V2. A completed `u` that covers a not-yet-built `g ∈ G` cannot stay by V3, since `g ∉ C ⊇ K` puts `g` in `G \ K`. V1 then forces the closure. (b) V1 holds by construction. V2 holds because roots outside `G ∪ H` are removed. V3: take `g ∈ G \ K*`. If `g ∉ C`, then `covered_by(g) ∩ C ⊆ F0 ⊆ U*`. If `g ∈ C ∩ U*`, any `u ∈ covered_by(g)` is in `D(g)`, so closure puts `u` in `U*`. (c) Total cost is `Σ_U undo + Σ_{G\C} fwd + Σ_{G∩U} fwd`, non-decreasing in `U`. Damage risk is also non-decreasing in `U`. (d) follows from (a). ∎

Computation is linear in steps plus edges. Measured 14 to 17 ms at 800 steps (`experiments/results/results.md`, E4).

Checked by exhaustive enumeration of every valid keep-set on 40 random small processes (`tests/test_reconcile.py`): the closure is the maximum valid keep-set in every case, and the plan's cost equals the enumerated optimum on 25 more.

**Negative result.** The problem first looked like a minimum-weight closure needing a min-cut solver. It does not: with non-negative costs every step is worth keeping if it is allowed to stay, so the optimum is the largest valid keep-set, which the closure gives directly. Do not present min-cut in the paper.

**Scope.** This is polynomial because assembly steps come with precedence and cover structure. It does not contradict Nebel and Koehler's hardness of conservative plan modification in general planning. Say so explicitly.

**What remains a real decision.** Once `U*` is fixed, only salvage-versus-scrap is left: expected salvage cost (undo time plus damage risk times scrap cost plus forward work) against scrap cost plus full rebuild. Implemented in `taskflux/reconcile.py`.

### 3.3 Lemma 2 (zero-regret hedging)

A ready step `s` of the running plan is **safe** for hypothesis `T` when: the hypothesis plan is a salvage plan; `s` is required by `T`; `s` does not cover a step the running plan still needs first; and `U*(C ∪ {s}, T) = U*(C, T)` with `s ∉ U*`. Then the remaining cost falls by exactly `forward(s)` whether or not the operator wanted the change.

*Proof sketch.* Under `T`, `K*` gains `s` and the forward set loses `s`, so salvage cost drops by `forward(s)` while the scrap alternative is unchanged and the plan stays a salvage plan. Under the running variant, `s` is simply its next step. ∎

Verified: 60 random processes plus every prefix of the gearbox process (`tests/test_hedge.py`), and 2,125 states in experiment E3 with a worst case of exactly 0.00 s.

Bug the test suite caught while writing this: the first definition ignored that a step can be physically ready yet cover something the running plan still needs first. That version was not zero-regret.

### 3.4 Proposition 3 (cost-coupled triage)

Given calibrated probabilities `p` over clarification, edit, changeover, abort, and regrets `Ra` (acting on a false changeover), `Rc` (continuing through a real one), `Ca` (asking), choosing the least expected regret among act, continue and ask is Bayes-optimal for that cost matrix. `Ra` and `Rc` are computed from the reconciler's cost-to-go, so they depend on the state of the workpiece. A stop request halts before any cost comparison.

This is a standard decision rule. The contribution is where the costs come from, plus the fact that hedging makes `Ca` small enough for asking to be the usual response to real uncertainty. It is optimal only for the modelled costs and only if the probabilities are calibrated (ECE 0.054 on held-out synthetic templates after temperature scaling).

## 4. What is not claimed

* Nothing here was run on a robot or on OpenVLA. The 7B model does not fit the development machine's 4 GB GPU.
* The utterances are authored by us. Classifier accuracy (88.8% on held-out templates) says nothing about shop-floor speech.
* Reversibility, undo damage and costs are hand-set. Results depend on them.
* Undo success is assumed, not measured. On a real cell undo may be the binding constraint.

## 5. More ideas, ranked

Not implemented. Ordered by expected value for a paper.

1. **Validate on a simulated manipulation benchmark with a fine-tuned VLA** so undo and forward success come from a policy instead of assumed probabilities. Turns a planning-layer paper into a system paper. Check which simulator setups the OpenVLA repository supports before committing.
2. **Perception uncertainty.** The verifier that says a step is done will be wrong sometimes. Precedence gives free error detection: a step seen done while its prerequisite is seen missing is inconsistent and should trigger re-inspection. Add an "inspect before destructive undo" action to the triage rule.
3. **Learn reversibility instead of hand-authoring it** from work instructions or process documents with an LLM, and report agreement with an expert annotation. Removes the largest stated limitation.
4. **Compose with SwitchVLA-style execution**: use its policy-level switching for smooth motion and TaskFlux for the structural decision. A natural "we complement, not replace" section.
5. **Conformal calibration of the intent probabilities** (KnowNo-style) so the act/ask decision carries a coverage guarantee.
6. **Repeated changes**: what if the operator changes again mid-changeover? Test that reconciliation composes (`reconcile` from a state that is itself a partial changeover) and bound the extra rework.
7. **Undo as a learned skill**: fine-tune reverse instructions and measure undo success directly, since the OpenVLA authors concede Diffusion Policy is smoother on contact-rich tasks.

## 6. What would raise this from workshop to full paper

* Idea 1 above, with a real policy in the loop.
* Idea 2, because state estimation is where a deployed system would actually fail.
* A second real process (not the gearbox and not random) with reversibility annotated by someone who did not write the code.
* Recorded operator phrasings for the classifier, even 100 of them.
