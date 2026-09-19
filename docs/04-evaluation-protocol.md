# Evaluation protocol for mid-episode task changeover

No existing benchmark measures what this system does, so the protocol is part of the contribution. This document defines the experimental unit, the metrics, the conditions, and the baselines.

## The experimental unit: a changeover episode

1. The cell is set up for product variant A with a known initial part layout.
2. The robot begins executing the plan for A.
3. At a controlled step index k, an operator utterance is issued.
4. Everything after that point is recorded: the classification decision, the reconciliation output, any refusal, the actions executed, and the final state of the assembly.

Holding k fixed per condition is what makes episodes comparable. Letting the operator speak whenever they feel like it produces data you cannot analyse.

## Metrics

### 1. Changeover Success Rate (CSR)

Fraction of changeover episodes where the final assembly matches the specification of the new variant, judged against the same acceptance criteria a human inspector would use.

The headline number. Report it per condition, not just pooled, because pooling hides the interesting variation.

### 2. Adaptation Latency (AL)

Seconds from the end of the operator utterance to the first executed action that is correct under the new plan.

Break it into three components and report them separately, since they optimise differently:

- transcription and intent classification
- reconciliation
- policy load or adapter instantiation

Do not report only the total. A total of six seconds means something very different if five of them are adapter loading than if five of them are LLM reasoning.

### 3. Rework Cost (RC)

Number of undo actions executed, divided by the number of plan steps completed before the change arrived.

RC of 0 means nothing completed had to be reversed. RC of 1 means the entire completed prefix was thrown away, which is what a full restart does by definition. A good reconciler should sit well below the restart baseline on episodes where the two variants share a prefix.

Report alongside it the number of unnecessary undos, meaning steps that were reversed but did not actually conflict with the new goal. That is the reconciler's precision.

### 4. False Changeover Rate (FCR)

Fraction of clarification and parameter-edit utterances that were classified as changeovers.

Report the opposite error separately as Missed Changeover Rate. The two are not symmetric. A false changeover destroys completed work and wastes time. A missed changeover produces a finished product that does not match the order. On a real line the second is worse, so the classifier should be tuned toward over-triggering, and the paper should say so explicitly rather than reporting a single accuracy number that hides the tradeoff.

### 5. Retention Score (RS)

Success rate on variant A, measured after the system has learned variant B and merged the adapter into the base weights.

Compare against the pre-merge success rate on A. The difference is the forgetting. Any claim about continuous learning without this number is unsupported.

### Supporting measurements

- Refusal precision: of the requests the system refused, how many were genuinely infeasible. A system that refuses everything scores perfectly on safety and is useless.
- Explanation quality: whether the stated reason for a refusal identified the actual blocking constraint. Rate this by hand against the ground truth; small n makes that practical.
- Operator interventions per episode.

## Conditions to vary

Cross these deliberately rather than sampling at random.

**When the change arrives.** Early (k small, little completed work) against late (k large, most of the plan done). Late changes stress the reconciler; early ones do not.

**What the change requires.** Three levels:
- truncation only, where the new goal is a prefix or subset of the old one and nothing needs undoing
- undo required, where completed steps conflict
- irreversible conflict, where a required undo crosses a step marked irreversible

The third condition is a refusal test. Success there means the system refused and explained correctly, not that it completed the task.

**Whether the variant is known.** Known routes to the base policy. Novel routes to a LoRA adapter. Compare CSR and AL across both.

**Instruction phrasing.** Collect several phrasings per intent, including indirect ones ("we are not doing gaskets on this batch") rather than only imperatives. Grounding on clean commands and evaluating on clean commands overstates how well this will work.

## Baselines

Four systems, run on identical episodes.

**B1. Stock OpenVLA, original instruction.** No adaptation. Should fail every changeover episode. This is the floor and it establishes that the problem exists.

**B2. Stock OpenVLA, restarted with the new instruction.** Clear the workspace, reset, run the new variant from scratch. This is what a factory does today. It should achieve high CSR and terrible AL and RC, which is exactly the point. It quantifies the cost of current practice.

**B3. LLM replanner, no reconciler.** Regenerate a plan from the new goal and the current camera frame, execute directly. This isolates the contribution of state reconciliation.

**B4. Full TaskFlux.**

B3 against B4 is the ablation that matters most. If B3 performs as well as B4, the reconciler is not earning its place and the paper's central claim is weak. Run it, report it honestly either way, and if the gap is small say so and explain what that means. A negative result that is properly measured is publishable; an unmeasured claim is not.

## Sample size, stated honestly

A single-arm student cell will not reach the trial counts in the papers we cite. OWG ran 50 Gazebo trials per scenario and 6 real trials. OpenVLA ran 500 trials per simulation suite.

Plan for roughly 10 to 15 episodes per condition on hardware, more in simulation if a simulated cell is available. Report per-condition counts in the table, report the actual numbers rather than only percentages, and give confidence intervals or at minimum standard error. With n of 10, one extra failure moves the percentage by ten points, and a reader needs to be able to see that.

Do not pool conditions to get a bigger-looking n. The conditions are the finding.

---

## Implementation notes (added after building the harness)

`experiments/run_experiments.py` implements this protocol in simulation. Where the implementation departs from, or sharpens, the text above:

**Two latency measures instead of one.** Adaptation Latency is the start of the first executed action of the adaptation, whether an undo or a build step. Time to Productive Work (TTP) is the start of the first *build* step. Both are reported because a restart begins acting almost at once, by clearing the bench, and then does no productive work for a long time. On the gearbox, restart scores AL 0.8 s and TTP 41 s (truncation), 129 s (undo) and 151 s (irreversible). TaskFlux scores AL 1.4 s and TTP 1.4 s (truncation) and 38.6 s (undo); where it has to scrap it matches restart at 151 s. The statement above that restart has "terrible AL" holds for TTP, not for AL.

**Four stages of change, not three.** Episodes are labelled after the fact by what the reconciler says: *truncation* (nothing to undo), *undo* (completed steps conflict), *risky* (salvage is possible but scrapping is cheaper in expectation because of undo damage risk), and *irreversible* (a required undo crosses an irreversible step). Report each separately. Pooling them hides the finding that the reconciler adds nothing on truncation and matches restart on irreversible conflicts.

**B3 is split.** B3a replans "target minus what is on the bench" with no undo. B3b replans and undoes by an order-based diff (longest common prefix of the two build sequences) and ignores reversibility. B3b is the more honest stand-in for a careful LLM replanner. B3a against B4 alone would overstate the reconciler.

**How success is counted when scrapping is the right answer.** A scrap-and-restart that ends in the right product counts as success in CSR, and `scrapped` and `destroyed` are reported next to it. For the irreversible stage the protocol says success means refusing and explaining correctly. The simulator measures the outcome, not the explanation quality. Explanation quality still needs the manual rating described above.

**Stop requests are a safety metric, not a classification metric.** Report the fraction of stop utterances that halt the arm, separately from intent accuracy. A learned classifier alone missed 11.5% on held-out phrasings.

**Triage is scored by regret.** For the false-changeover and missed-changeover rates above, the simulator also reports seconds lost against the best response in the true world, which puts the two asymmetric errors on one scale.

**The retention gate needs more episodes than this protocol budgets.** With a one-sided 95% Wilson bound and a 10-point margin, a variant with a true 90% success rate needs about 43 evaluation episodes before a perfectly retained adapter can pass (36 at 95%, 57 at 80%). At 10 to 15 episodes the gate will refuse to merge. Plan for that, or use a simulator cell with more trials for the retention check, or state that merge-back was validated only on a toy.

**Sample sizes used in simulation.** 1,200 to 1,500 episodes per system per stage on the gearbox and 900 to 7,584 on the synthetic processes. These are simulated draws under assumed parameters, not hardware trials, and should not be compared to the 10 to 15 hardware episodes planned above.
