# Weekly progress report: TaskFlux

Batch 03, Vision Language Robotics for Collaborative Manufacturing. Supervisor: Dr. Ramachandro Majji.

## Summary

The project moved from a literature review and a proposed architecture to a **tested implementation of the planning layer, a novelty check against recent work, and a hardening phase (Phase 0)** that added a second process, ablations, a failure analysis, perception noise, and a reproducible environment. The novelty check narrowed two of our headline claims. Phase 0 then **corrected one of our own results**: an inconsistency in the simulator had inflated the success gap. The corrected picture is smaller but more honest, and the differences that remain are in time, parts lost and rework rather than in success rate.

Not done: anything on a robot or on OpenVLA weights. The development machine has a 4 GB GPU and the 7B model does not fit. All results come from a step-level simulator with assumed parameters.

## 1. Novelty check (unchanged from last report)

A prior-art search found SwitchVLA (policy-level task switching), a vision-language-policy replanner, and "Do This Instead" (undo on corrected instructions), plus classical plan repair and disassembly planning. "No paper addresses mid-episode task change" is false and was removed from the drafts. What remains, ranked (details in `docs/05`):

1. A formal treatment of the half-built workspace with an exact refusal certificate.
2. Cost-coupled triage (act, continue or ask) with error costs taken from the reconciler.
3. Zero-regret hedged execution while the operator's intent is unconfirmed, **now with a stated damage condition** (below).
4. A measurement protocol and harness.
5. A reported negative result (a min-cut formulation was not needed).

Assessment: moderate novelty; a workshop or short paper is realistic now.

## 2. What Phase 0 added

| Item | State |
|---|---|
| Reproducible environment | Pinned versions, one command (`python -m experiments.reproduce`), results stamped with environment and git state, verified deterministic across runs and hash seeds. **The Dockerfile is written but unbuilt** (Docker daemon was not running). |
| Second process | Sensor module as a JSON spec, with a different structure. Loader, round-trip and tests. |
| Independent annotation workflow | A blinded sheet and an agreement scorer exist. **No independent annotation has been done**, so the second process is still the code author's own judgement. |
| Ablations | Each reconciler rule removed in turn, on both processes and generated ones. |
| Failure analysis | Why TaskFlux fails, which undos destroy parts, where it is not fastest. |
| Perception noise | Five policies for acting on a verifier that is sometimes wrong. |
| Geometry stub | Reach, human safety zones, covers derived from placement, with refusal messages. **A stub, not robot kinematics.** |

243 tests pass (was 207).

## 3. Results (simulated, assumed parameters)

| Question | Result |
|---|---|
| When does the reconciler help? | **When undo is needed.** Gearbox: 162 s and 0% parts lost, against restart 326 s / 15% lost and order-diff replanning 314 s / 16% lost. Sensor module: 270 s against 327 s and 311 s, but TaskFlux still loses 27% of parts because desoldering one header is risky. |
| When does it not? | **Truncation-only changes:** naive replanning ties it (152 s against 153 s). **Irreversible conflicts:** it ties restart (331 s against 330 s), since scrapping is the only option. Its value there is asking first and explaining what blocks the change. |
| Which rules matter? | The cover rule most: removing it drops gearbox success to 0% (collisions) even for truncation-only changes. The cascade rule matters when a forced step has shared dependents (sensor module success 60% without it). Refusal: without it every irreversible case destroys the part and wastes 25 to 36 s. |
| Does it ever collide or ship the wrong product? | Not in any episode. Its only unrecovered failures (0.2 to 1%) are policy steps failing at the assumed 92% per-attempt success. |
| Triage vs a fixed threshold | 2.9 s against 4.2 s mean regret, scored by the simulator. Without the stop override, 505 stop requests are missed. |
| Perception noise | At 5% per-step verifier error, more than half of observations contain an error; trusting the verifier gives 74% success. A free consistency check notices 47 to 89% of errors with no false alarms (85% success). Inspecting only decision-critical steps gives 99% with about half the inspections of inspecting everything. **Inspecting before an undo, my first idea, did not help.** |
| Is hedging safe? | Never worse in either world (worst case 0.00 s). But see the correction below. |
| Retention gate | Works on a toy. Needs 36 to 57 evaluation episodes to pass, more than the protocol budgets. |

## 4. Corrections to earlier claims

* **Success gap was inflated.** The simulator ended episodes when an undo damaged the part, while the reconciler's cost model treated damage as recoverable by scrapping and rebuilding. Found by running the second process, whose undos are riskier. After fixing it, every recovering system succeeds about 99% of the time. **Last week's headline "99.9% against 84.7%" is withdrawn.** The differences that hold are time, parts lost and rework.
* **Zero-regret hedging needed a condition.** The earlier lemma was true only under the same inconsistent cost model. It now requires that the hypothesised undo cannot damage the part. Hedging is available in 44% of states instead of 73%, and the average saving is 2.7 s, bounded by the confirmation window.
* **A state can be impossible even when every prerequisite is present** (contradictory ordering constraints). Found because the noise experiment crashed. The validity check now covers it, and it is a second free error detector.

Fifteen modelling errors in total were found and fixed (listed in `docs/06`).

## 5. Limitations to state up front

* No robot, no OpenVLA. Everything is planning-layer only.
* Costs, damage probabilities, success rates and the 450 s failure penalty are assumed.
* Reversibility is hand-authored, for both processes by the code's author, and not independently annotated.
* Perception errors were independent per step. Real errors are correlated, which would weaken the consistency check.
* Utterances are authored by us. Classifier accuracy (88.8% on held-out templates) is not a claim about real speech.
* Two hand-built processes, two variants, one change per episode.

## 6. Next steps

1. **Get the second process annotated by someone else** (an hour of someone's time; the sheet is ready). This is the cheapest way to make the reversibility assumption defensible.
2. **Build and test the Docker image** on a machine where the daemon runs.
3. **Real policy in the loop** on a simulated manipulation benchmark, on rented GPU time, so undo and forward success are measured. Check which simulator setups OpenVLA supports before committing.
4. **Vision-based step verifier** and its measured error rate, to replace the noise model's assumed rates.
5. Read the full text of SwitchVLA and "Do This Instead" and write the related-work paragraph.
6. Recorded operator phrasings, even 100, for the classifier.

## 7. Decisions needed

* **Venue and scope:** a short paper on the planning layer now, or hold for the real-policy experiment?
* **Compute:** GPU access for a fine-tuned VLA, or a smaller model.
* **Annotation:** who can independently annotate the sensor module.
* **Sign-off** on the narrowed claims and the withdrawn success-gap headline.

## Files

`docs/05` (novelty and proofs), `docs/06` (implementation, results, errors found), `experiments/results/results.md` (all tables), `examples/` (process specs). The paper drafts were only edited to soften overclaims. `paper/main.tex` is uncompiled since no LaTeX compiler is installed here, and it does not yet reflect the corrected success comparison.
