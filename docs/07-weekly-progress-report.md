# Weekly progress report: TaskFlux

Batch 03, Vision Language Robotics for Collaborative Manufacturing. Supervisor: Dr. Ramachandro Majji.

## Summary

This week the project moved from a literature review and a proposed architecture to a **tested implementation of the planning layer and a novelty check against recent work**. The novelty check changed the framing: two of our headline claims were too strong and have been narrowed. What remains is a smaller but better-supported set of contributions, with proofs and measurements behind them.

Not done: anything on a robot or on OpenVLA weights. The development machine has a 4 GB GPU, and the 7B model does not fit. All results come from a step-level simulator with assumed parameters.

## 1. Novelty check

A prior-art search found work that our earlier documents said did not exist:

* **SwitchVLA** (2025) does task switching inside a VLA policy, using execution state. It does not reason about dependencies or irreversibility.
* A **vision-language-policy replanner** passes execution history into a forward replan. No undo reasoning.
* **"Do This Instead"** (ACM THRI) generates undo steps when an instruction is corrected, in a rule-based cognitive architecture. This is the closest prior work on undo and must be cited.
* Classical **plan repair**, **selective disassembly planning** and **KnowNo** (asking when unsure) are adjacent.

So "no paper addresses mid-episode task change" is false and has been removed from the drafts. The remaining claims, ranked by strength, are in `docs/05`:

1. A formal treatment of the half-built workspace with an exact refusal certificate.
2. Cost-coupled triage (act, continue or ask), with error costs taken from the reconciler.
3. Zero-regret hedged execution while the operator's intent is unconfirmed.
4. A measurement protocol and harness.
5. A reported negative result: a min-cut formulation looked necessary and was not.

Honest assessment: **moderate novelty**. Each algorithm is elementary. A workshop or short paper is realistic now. A full paper needs a real policy in the loop (see next steps).

## 2. What was built

* Process model with precedence, covering, irreversibility and undo damage risk.
* **Reconciler**: minimum undo set, reverse-dependency ordering, refusal certificate with a plain-language reason, salvage-versus-scrap decision.
* **Hedged execution**, **triage**, a calibrated intent classifier with a lexical stop override, a controller, an adapter merge gate, and an OpenVLA interface (untested).
* Simulator with four baselines and five experiments; 207 tests; a scripted operator dialogue (`python -m taskflux.demo`).

## 3. Results (simulated, assumed parameters)

| Question | Result |
|---|---|
| Is the reconciler optimal? | Yes, and proven: the minimum undo set is unique and optimal for every non-negative cost. Checked against exhaustive enumeration on 40 random processes. |
| When does it help? | **When undo is needed.** Gearbox: 99.9% success in 162 s, 0 unneeded undos, against restart at 84.7% in 310 s with 4.25 unneeded undos per episode. |
| When does it *not* help? | **Truncation-only changes:** naive replanning ties it (99.7% against 99.4%). **Irreversible conflicts:** it ties restart, since scrapping is the only option. Its value there is that it asks and explains, while a naive replanner destroys the part every time. |
| Does triage beat a fixed threshold? | 2.7 s mean regret against 4.2 s, scored by the simulator. Hedging is worth about 0.6 s of that. |
| Is hedging safe? | Worst case 0.00 s over 2,125 states: never worse in either world. Modest gain (about 3 to 4 s per confirmation). |
| Is a learned classifier safe for stop requests? | **No.** It missed 11.5% on held-out phrasings. A lexical override is required. |
| Does the retention gate work? | On a toy, yes: it merges without conflict and refuses when a merge would drop retention from 95% to 74%. But it needs 36 to 57 evaluation episodes to pass, more than the protocol's 10 to 15. |

## 4. Errors found and fixed during the work

Nine, listed in `docs/06`. Three matter most for the report:

* An early hedging definition was not actually zero-regret (caught by a property test).
* The triage rule ignored a real changeover when the running product was already finished (caught by running the demo, not by any aggregate metric).
* Regret was first scored with the same formulas that made the decision. It is now scored by the simulator.

## 5. Limitations to state up front

* No robot, no OpenVLA. Everything is planning-layer only.
* Costs, damage probabilities and success rates are assumed. Only the irreversible-step rate was varied.
* Reversibility is hand-authored.
* Utterances are authored by us. Classifier accuracy (88.8% on held-out templates) is not a claim about real speech.
* One hand-built example plus generated processes; two variants only.

## 6. Next steps

In order of value:

1. **Put a real policy in the loop** on a simulated manipulation benchmark so undo and forward success are measured, not assumed. Needs a GPU that can run a fine-tuned VLA. Check which simulator setups OpenVLA supports before committing.
2. **Perception uncertainty.** The step-completion verifier will be wrong sometimes. Precedence gives free error detection (a step seen done while its prerequisite is seen missing). Add an inspect-before-undo action.
3. **A second, independently annotated process**, with reversibility marked by someone other than the code's author.
4. **Recorded operator phrasings**, even 100, for the classifier.
5. Read the full text of SwitchVLA and "Do This Instead" and write the related-work paragraph and a differentiation.
6. Optionally: learn reversibility from process documents; compose with SwitchVLA-style execution; repeated changes.

## 7. Decisions needed

* **Target venue and scope:** a short paper on the planning layer now, or hold for the real-policy experiment?
* **Compute:** access to a GPU with enough memory for a 7B VLA, or agreement to use a smaller model.
* **Sign-off** on the narrowed novelty claims in `docs/05`, since they change the paper draft's framing.

## Files

`docs/05` (novelty and proofs), `docs/06` (implementation and results), `experiments/results/results.md` (all tables). Paper drafts were edited only to soften overclaims. They still need a related-work paragraph on the newly found papers. `paper/main.tex` was edited but not compiled, since no LaTeX compiler is installed here.
