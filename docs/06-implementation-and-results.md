# Implementation and results

Status: the planning layer of TaskFlux is implemented and tested against a step-level simulator. **No robot and no OpenVLA weights were used.** The development machine has a 4 GB RTX 3050 laptop GPU, which cannot hold the 7B model. Every number below comes from `taskflux/sim.py` with the assumed parameters stated there, and characterises the planning layer under those assumptions.

Phase 0 of the roadmap (hardening on this machine) is done and is included here: pinned environment, second process, ablations, failure analysis, perception noise, and a geometry stub. Phases 1 and 2 (a real policy in the loop, real hardware) are not started.

## How to run it

```bash
python -m experiments.reproduce            # tests, then every experiment, then an environment record (about 1 to 2 minutes)
python -m pytest tests -q                  # 243 tests
python -m experiments.retention_toy        # adapter merge gate on a toy policy
python -m taskflux.demo                    # scripted operator dialogue on the gearbox example
```

Environment: `requirements.lock.txt` pins the exact versions behind the reported numbers (Python 3.12.7, numpy 1.26.4, scipy 1.13.1, pandas 2.2.3, matplotlib 3.9.0, scikit-learn 1.5.2, pytest 8.4.2). Every results file records the environment and git state. Two consecutive runs, one with a randomised `PYTHONHASHSEED`, produce identical results except for the wall-clock timing table (E4).

**The Dockerfile has not been built.** Docker is installed on the development machine but its daemon was not running, so the image is untested. Treat it as a draft until someone runs `docker build`.

## Architecture

```
operator utterance ─► IntentClassifier (+ lexical stop override)      taskflux/utterances.py
                          │  P(clarification, edit, changeover, abort)
                          ▼
                     Triage: act / continue / ask / halt                taskflux/triage.py
                          │  Ra, Rc, Ca from the reconciler's cost-to-go
                          ▼
   ┌── act ──►  Reconciler: keep / undo / discard, refusal certificate  taskflux/reconcile.py
   │                salvage-versus-scrap; tool, reach and zone checks
   └── ask ──►  Hedged execution: zero-regret steps while waiting       taskflux/hedge.py
                          │  one instruction per step
                          ▼
                     StepPolicy (SimPolicy here, OpenVLAPolicy stub)    taskflux/vla.py
                          ▲
   perception noise: consistency check and inspection policies          taskflux/perception.py
```

| Module | Role |
|---|---|
| `process.py` | Step, variant and process model: `requires`, `covered_by`, irreversibility, undo damage risk, tools, positions. A state is valid only if prerequisites are present **and** a build order could have produced it. |
| `reconcile.py` | Minimum undo closure, reverse-dependency undo order, forward plan, refusal certificate, plain-language explanation, scrap comparison, tool, reach and safety-zone checks. |
| `hedge.py` | Zero-regret step selection for the confirmation window. |
| `triage.py` | Cost-coupled decision rule, plus the fixed-threshold baseline. |
| `utterances.py` | Synthetic utterances with disjoint train, dev and test templates; calibrated classifier; lexical stop override. |
| `perception.py` | Observation noise, the free consistency check, five inspection policies. |
| `geometry.py` | **Stub**: spherical reach, box safety zones, covers derived from part placement. Not robot kinematics. |
| `spec.py` | Load and dump processes as JSON; blinded annotation sheet and agreement scoring for independent review. |
| `ablation.py` | Reconciler with one rule removed, for measuring what each rule is worth. |
| `controller.py` | Runtime glue: workpiece state, queue, dialogue. |
| `adapters.py` | Known-versus-novel routing and the two-gate adapter merge. |
| `vla.py` | The seam to a VLA. `OpenVLAPolicy` follows the OpenVLA README usage and is **untested**. |
| `sim.py` | Step-level episode simulator, four baselines, TaskFlux, ask variants. |
| `synth.py`, `examples.py`, `examples/*.json` | Random processes, the gearbox, and a second process (sensor module) as a JSON spec. |

## How success is counted (changed this phase)

Earlier drafts ended an episode as a failure whenever an undo damaged the part, while the reconciler's own cost model treated damage as recoverable at the price of a scrap and rebuild. That inconsistency **inflated the success gap** in the earlier headline (for example 99.9% against 84.7% on the gearbox). It is fixed: a damaged part is now scrapped and the target rebuilt, exactly as the cost model assumes. Success rates therefore converge near 99% for every system that recovers. **The differences that remain, and that matter, are time, parts lost, and rework.** Columns:

* `CSR`: the final assembly matches the new variant (after any recovery).
* `scrapped`: the workpiece was scrapped, by decision or by damage.
* `destroyed`: an undo damaged the part, an unplanned loss.
* `rework`: completed steps that had to be redone (individual undos plus everything lost to a scrap) divided by steps done.
* `unneeded undos`: deliberate undos of steps that did not conflict with the new goal. Work lost to a scrap is not counted here.

## Results

Full tables: `experiments/results/results.md`. Success intervals are 95% Wilson.

### E1. Changeover with the intent already known (gearbox; second process in E1b)

| Stage | Result |
|---|---|
| **Truncation only** | **The reconciler adds nothing.** Naive replanning (B3a) ties TaskFlux: 99.7% against 99.4% success, 152 s against 153 s. Restart is 232 s, order-diff replanning 218 s, and both lose parts to needless undos (6 to 7%). |
| **Undo required** | **TaskFlux 162 s, 0% parts lost, rework 0.32.** Restart 326 s, 15% lost, 4.36 unneeded undos. Order-diff 314 s, 16% lost, 3.48 unneeded. Naive replanning collides every time. Sensor module: 270 s against 327 s and 311 s, but TaskFlux still loses 27% of parts (see E7). Synthetic (7,509 episodes each): 271 s against 369 s and 364 s. |
| **Scrap cheaper than a risky salvage** | TaskFlux scraps up front (377 s, 0% lost, synthetic) where restart takes 470 s losing 22% and order-diff 486 s losing 36%. |
| **Irreversible conflict** | **TaskFlux matches restart** (331 s against 330 s on the gearbox; 308 s against 309 s on the sensor module). Nothing beats scrapping here. Order-diff replanning takes longer (357 s) and destroys the part every time. The value is that TaskFlux asks first and says what blocks the change. |

### E1b. Second process (sensor module, `examples/sensor_module.json`)

Different structure: soldered headers, a shield can that blocks the B header, potting resin as the irreversible trap. The gearbox pattern holds: no gain on truncation (175 s against 176 s for naive replanning), a clear time gain when undo is needed, a tie with restart on irreversible conflicts. The second process is authored by the same person as the code, so its reversibility and damage values are **not independent evidence**. A blinded annotation sheet (`taskflux.spec.annotation_sheet`) exists so an independent person can annotate it, and `compare_annotation` scores agreement. That has not been done.

### E6. Ablations: what each reconciler rule is worth

| Rule removed | Effect |
|---|---|
| **cover rule** | Success falls to **0% on the gearbox** (100% collisions), even for truncation-only changes, because the forward plan puts the cover on before the B housing. Sensor module: 50% (undo), 17% (risky). This rule is the most important. |
| **cascade** (undo dependents) | Vacuous on the gearbox, where every dependent of a forced root is itself forced. On the sensor module: 60% success (40% collisions), and 3% where scrapping is cheaper. Matters exactly when a forced root has shared dependents. |
| **refusal** | Every irreversible case destroys the part; +25 s (gearbox) to +36 s (sensor module) of wasted attempt. |
| **scrap-versus-salvage choice** | Sensor module, risky stage: 38% of parts destroyed instead of 0%, +7 s. Small. |
| **tolerated extras** | About +0.8 to 1.0 needless undos and +2 to 5 s on the gearbox. Small. |

### E7. Failure analysis

TaskFlux never ended in a collision or a wrong product in any episode. Its unrecovered failures (0.2 to 1%) are policy steps that failed after their retries at the assumed 92% per-attempt success, spread evenly across steps with no dominant cause. **Where the parts go:** on the sensor module a single undo, desoldering `header_a`, accounts for essentially all parts destroyed (27% of undo-stage episodes). The reconciler chooses salvage there because it is cheaper in expectation than scrapping, which is right on average and costly in material. TaskFlux is never meaningfully slower than the fastest alternative (at most 1.6 s behind, on ties).

### E8. Perception noise

Each step of the true state is independently misread with the stated rate. At 5% per step, more than half of all observations contain an error.

| Policy | Success at 5% error (synthetic) | Inspections |
|---|---|---|
| trust the verifier | 74.4% | 0 |
| **free consistency check** | 85.0% | 0.9 |
| inspect steps about to be undone | 85.0% (no gain over the free check) | 2.5 |
| **inspect decision-critical steps** | **98.8%** | 9.6 |
| inspect everything | 99.5% | 17 |

* The free check (a step seen done without its prerequisites, or a set of steps with contradictory ordering) notices 47 to 89% of erroneous observations, with **no false alarms**. It is never worse than trusting the verifier and costs nothing.
* **Inspecting before an undo does not help.** The harmful errors are steps believed done that are not, and steps missed that are done. Neither is in the undo list. A wrongly believed step inside the undo set only causes a harmless phantom undo.
* Inspecting only steps whose status would change the plan (value of information) reaches near-full success with roughly half of the inspections (5 against 13 on the sensor module, 10 against 17 on the synthetic set).
* With an assumed 450 s penalty for a failed changeover: the free check at 0 to 2% error, decision-critical inspection from about 3 to 5% up. Full inspection was never best. The penalty is an assumption and the ranking depends on it (the table in the results file shows it).

### E2. Triage under classifier uncertainty (scored by the simulator, not by the decision formulas)

| Policy | Mean regret, s | Note |
|---|---|---|
| Oracle | 0.0 | ceiling |
| **TaskFlux** | **2.9 ± 0.1** | asks in 22% of cases |
| TaskFlux without hedging | 3.3 ± 0.1 | hedging worth about 0.4 s |
| TaskFlux without the stop override | 3.0 ± 0.1 | **505 missed stop requests** |
| Fixed threshold 0.5 / 0.3 | 4.2 ± 0.2 / 4.3 ± 0.2 | |
| Always ask, with hedging / idle | 7.1 / 8.4 | asks 92% of the time |
| Never act | 23.9 ± 0.5 | |

The classifier alone catches 88.5% of stop requests on held-out phrasings; with the lexical override 100% (0% false halts on this synthetic set, which is not evidence about real speech). Regret is scored with damage switched off in the simulator, so it does not reflect damage risk.

### E3. Hedged execution

Worst-case change in completion time over 2,106 synthetic states plus the gearbox: **0.00 s**, never worse in either world. **Tightened this phase:** a hedged step is zero-regret only if the hypothesised undo cannot damage the part; otherwise a scrap would waste it. That cut the share of states with a safe step from 73% to 44% on the synthetic set (44% on the gearbox). Average saving is 2.7 s per confirmation, bounded by the 6 s window; time to the first useful action falls from 7.4 s to 4.5 s. A modest gain. Its value is that it is free of regret by construction.

### E4 and E5

Reconcile takes 0.025 ms at 9 steps and roughly 14 to 17 ms at 800 steps (varies by run). Across irreversible-step rates from 0 to 0.4, TaskFlux is at or above both baselines on success and faster than restart at every rate (for example 293 s against 398 s at rate 0, 332 s against 366 s at 0.4). The order-diff replanner destroys parts in 12% (rate 0) to 79% (rate 0.4) of cases.

### Geometry stub

Reach (spherical shell), human safety zones (boxes) and covers derived from part placement (a part above another and overlapping it in plan view covers it) are checked, and a failure produces a refusal that names the step and the zone. **This is a stub**, not robot kinematics: no inverse kinematics, joint limits, swept volumes or self-collision, top-down approach only. A real cell needs a motion-planning check (MoveIt or similar) behind the same interface. Tested on small hand-built cases only.

### Retention gate (toy, not OpenVLA)

A small MLP with a LoRA adapter merges when the variants do not conflict (retention 96% to 94%). With conflicting variants the gate refuses (95% to 74% and 96% to 40% if merged blindly) and the adapter stays routed. A conservative Wilson-bound gate needs about 36 to 57 evaluation episodes before it can pass even a perfectly retained variant; the protocol budgets 10 to 15. On a student-scale cell the gate will refuse to merge.

## What the tests, the demo and the experiments caught

Each is a real modelling error that plausible aggregate numbers would have hidden.

1. **First hedging definition was not zero-regret** (a step can be ready yet cover something the running plan needs first). Property test.
2. **"Continue" looked free when the running product was finished**, so a certain changeover was ignored. Caught by the demo, not by any metric.
3. **"Act" looked free early in the build.** The two error costs are now symmetric.
4. **Regret was scored with the same formulas that made the decision** (circular). Now scored by the simulator.
5. **A failed episode with time near zero counted as the best response.** Failed responses now count as infinite time.
6. **Wrongly acting long enough can execute an irreversible step of the wrong product.** That is a scrap, not an infinite cost.
7. **Per-episode seeds used Python's randomised string hash.** Now deterministic; verified.
8. **The gearbox ended on its irreversible step**, so no mid-build irreversible conflict occurred. Added leak-test steps.
9. **The classifier misses about 11.5% of stops.** The lexical override exists because of this.
10. **The simulator ended episodes at a damaged part while the cost model treated damage as recoverable.** This inflated the success gap in earlier drafts. Found by running a second process whose undos are riskier. Fixed; success rates and the headline claims above are restated accordingly.
11. **Lemma 2 (zero-regret hedging) was only true under that inconsistent cost model.** With a consistent one it needs the hedged undo to be damage-free. The condition is added and tested.
12. **A forced removal of an irreversible step took 0 s in the simulator.** It now takes about as long as the step did.
13. **The state-validity check missed physically impossible states.** Found because the noise experiment crashed on a belief whose ordering constraints formed a six-step cycle. A state now also needs a valid build order, which doubles as a second free error detector.
14. **The perception figure plotted mean time over all episodes**, which made failing policies look faster. Now successes only.
15. **"Unneeded undos" counted work lost to a scrap.** Now separate from deliberate undos.

## Threats to validity

* All timing and success figures rest on assumed parameters (`SimParams`, per-step costs, damage probabilities, the 450 s failure penalty). Sensitivity was explored only for the irreversible-step rate and the perception error rate.
* Reversibility, damage risk and costs are hand-set, for both example processes by the code's author. **Not yet independently annotated.**
* Perception errors are independent per step. Real verifier errors are correlated (occlusion, lighting), which would make the consistency check less effective.
* Utterances are authored by us; the classifier is trained and tested on the same generator with disjoint templates.
* Two hand-built processes plus generated ones; two variants only; a single change per episode.
* The comparison baselines are our own implementations of what an LLM replanner would do. No published system was reproduced.
* Undo and forward success are assumed. On a real cell undo may be the binding constraint.
* The geometry layer is a stub, and the Dockerfile is unbuilt.

## Integrating with OpenVLA

`taskflux/vla.py` defines the seam. TaskFlux issues one language instruction per step and needs two things a stock OpenVLA does not provide: a **step-completion verifier** (OpenVLA has no termination signal; E8 shows how much its errors matter) and **state kept outside the policy** (it sees one image and no history). `OpenVLAPolicy` wraps `predict_action` as documented in the OpenVLA repository. Neither loading nor the prompt format was verified here.
