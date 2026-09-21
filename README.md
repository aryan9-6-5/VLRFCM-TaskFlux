# VLRFCM-TaskFlux

Vision Language Robotics for Collaborative Manufacturing.

Major project, Batch 03, Department of CSE (AI and ML), Vardhaman College of Engineering, Hyderabad. Supervisor: Dr. Ramachandro Majji.

This repository holds the literature review, the refined problem framing, the review paper draft, the evaluation protocol, and a tested implementation of the planning layer for TaskFlux, an adaptation layer that lets a collaborative robot revise its assembly plan when the operator changes the product variant mid-task.

**Status.** The planning layer is implemented and tested (243 tests) against a step-level simulator, with a hardening phase done (second process, ablations, failure analysis, perception noise, geometry stub, pinned environment). Nothing has been run on a robot or on OpenVLA weights. See [docs/06](docs/06-implementation-and-results.md) for results and limits, and [docs/05](docs/05-novelty-and-formal-results.md) for the novelty search, which narrowed some of the claims below.

---

## What this project actually claims

Vision-language-action models map a camera image and a language instruction to motor commands. OpenVLA reaches 70.6 percent mean success across 29 manipulation tasks and can be adapted with LoRA on a single GPU. RT-2 and QUART show the formulation transfers across tasks and across embodiments.

All of them share one assumption: the instruction holds constant for the length of the episode.

On a high-mix, low-volume line that assumption breaks several times a shift. The operator changes the product variant while the robot is partway through building the previous one. When that happens, the workspace is not empty. Three screws are torqued, a connector is seated, a gasket is in place. Regenerating a plan from the current camera frame produces a plan for a fresh workbench, and executing it gives you either a collision or a hybrid assembly matching neither specification.

That is the gap. It is not a perception problem and not a grounding problem. It is a gap in how the system models its own objective over time.

## Three problems that the literature conflates

| Problem | Trigger | Goal state | Addressed by |
|---|---|---|---|
| Referential ambiguity | referent is unclear | fixed | Fan and Zheng (2024) |
| Execution failure | execution diverged from prediction | fixed | Inner Monologue, DoReMi, REFLECT |
| Task changeover | operator changed the requirement | replaced mid-episode | SwitchVLA (policy level, implicit), plan-repair and undo-on-correction work; none found that reasons about covering and irreversibility with a completeness guarantee (docs/05) |

Ambiguity work resolves which object an instruction refers to while everyone still agrees on what is being built. Replanning work reacts when the world does not match the prediction, with the goal still intact. Neither covers the case where the goal is withdrawn and replaced while execution is in progress. Recent work that does touch it (SwitchVLA, a vision-language-policy replanner, an undo-on-correction cognitive architecture) handles it at the policy or plan level. None of them, as far as the search found, decides which completed steps can stay, which must come off in what order, and when the change has to be refused because a step cannot be undone.

## The five contributions

1. **Changeover intent classification.** Sort each operator utterance into clarification, parameter edit, changeover, or abort. Existing systems collapse all four into "an instruction". The two error directions have opposite costs: a false changeover destroys completed work, a missed changeover finishes the wrong product.

2. **Partial-assembly state reconciliation.** The novel component. Partition completed steps into keep, undo and discard against the new goal, order the undos by reverse dependency, and escalate to the operator when a required undo crosses an irreversible step such as cured adhesive or a set rivet. The concept has neighbours (plan repair, selective disassembly planning, undo generation), so the claim is the formal treatment, not the idea: a unique minimum undo set, an exact refusal certificate, and its coupling to triage. See docs/05.

3. **A refusal path.** Check reachability, collision against current workspace occupancy, tool availability and process constraints before committing. When a check fails, say which constraint blocked it in a sentence the operator can act on, rather than returning an error code.

4. **Known versus novel routing with a gated merge-back.** Known variants route to the base policy. Novel ones get a LoRA adapter at rank 32, following the OpenVLA authors' own default. An adapter merges into the base weights only after passing a quality gate and a retention gate.

5. **An evaluation protocol.** We found no benchmark that measures rework or refusal for mid-episode task change, so defining the measurement is part of the contribution.

## What is implemented

| Contribution | Status |
|---|---|
| 1. Intent classification | Implemented as a calibrated four-way classifier on synthetic phrasings, with a lexical stop override. Classifier alone missed 11.5% of stop requests, which is why the override exists. |
| 2. State reconciliation | Implemented with proofs and exhaustive tests. Optimal for every non-negative cost model. Adds nothing over naive replanning when nothing needs undoing. Matches restart when an irreversible step is in the way. Clearly better in time and parts lost when undo is needed (gearbox: 162 s and 0% parts lost against 314 to 326 s and 15 to 16%). Success rates are about 99% for every system that recovers by scrapping, so success is not the differentiator. |
| 3. Refusal path | Implemented, with a complete certificate and a plain-language reason. Tools and irreversibility are checked. Reachability and collision are not modelled. |
| 4. Routing and gated merge | Gate logic implemented and checked on a toy only. The gate needs about 36 to 57 evaluation episodes to pass, more than the protocol budgets. |
| 5. Evaluation protocol | Implemented as a simulator harness with all five metrics and four baselines, plus two additions: time to productive work, and a split of changes into truncation, undo, risky and irreversible. |
| New: cost-coupled triage | Act, continue or ask, with regrets derived from the reconciler. 2.9 s mean regret against 4.2 s for a fixed threshold. |
| New: zero-regret hedged execution | Proven and tested, under the condition that the hypothesised undo cannot damage the part. Never worse in either world; modest gain (2.7 s per confirmation, in 44% of states). |
| New: perception noise | A free consistency check notices 47 to 89% of verifier errors; inspecting only decision-critical steps recovers near-full success at half the inspections. Simulated, independent per-step errors. |
| New: geometry | Reach, human safety zones and derived covers, as a stub. Not robot kinematics. |

## Evaluation metrics

- **Changeover Success Rate.** Does the final assembly match the new specification.
- **Adaptation Latency.** Seconds from end of utterance to first correct action under the new plan, broken into transcription, reconciliation, and policy load.
- **Rework Cost.** Undo actions divided by steps already completed. A full restart scores 1.0 by definition.
- **False Changeover Rate.** Clarifications misread as changeovers. Missed changeovers reported separately, since the costs are not symmetric.
- **Retention Score.** Success on variant A after the system has learned variant B. Without this number, any continual-learning claim is unsupported.

Four baselines: stock OpenVLA with the original instruction (the floor), stock OpenVLA restarted from scratch (current industrial practice), an LLM replanner with no reconciler, and the full system. The third against the fourth is the ablation that decides whether reconciliation earns its place.

---

## Repository contents

| File | Contents |
|---|---|
| [docs/00-source-audit.md](docs/00-source-audit.md) | Per-paper notes with verified figures, and a warning about one source |
| [docs/01-idea-and-novelty.md](docs/01-idea-and-novelty.md) | The refined idea, the five novelty claims, and stated limitations |
| [docs/02-review-paper-draft.md](docs/02-review-paper-draft.md) | Review paper draft. Ten sections, twenty references |
| [docs/03-literature-review-table.md](docs/03-literature-review-table.md) | Twenty-row comparative table in four themed groups, plus a six-row slide version and a verification checklist |
| [docs/04-evaluation-protocol.md](docs/04-evaluation-protocol.md) | Metrics, conditions, baselines, and sample size guidance |
| [docs/05-novelty-and-formal-results.md](docs/05-novelty-and-formal-results.md) | Prior-art search, revised novelty claims, lemmas with proofs, more ideas |
| [docs/06-implementation-and-results.md](docs/06-implementation-and-results.md) | Architecture, results, bugs the tests caught, threats to validity |
| [docs/07-weekly-progress-report.md](docs/07-weekly-progress-report.md) | Short report for the weekly meeting |
| [taskflux/](taskflux) | The implementation: process model, reconciler, hedging, triage, classifier, controller, simulator |
| [tests/](tests) | 251 tests, including exhaustive optimality checks |
| [examples/](examples) | Process specs as JSON (gearbox, sensor module) |
| `Dockerfile`, `requirements.lock.txt` | Pinned environment. The Dockerfile has not been built yet. |
| [experiments/](experiments) | Experiment runner and results (`experiments/results/results.md`) |
| [paper/main.tex](paper/main.tex) | The same draft in IEEE conference LaTeX, with both tables typeset and an embedded bibliography |
| [docs/figures/architecture-a3.png](docs/figures/architecture-a3.png) | Six-stage proposed architecture |
| [docs/figures/system-flow-diagram.png](docs/figures/system-flow-diagram.png) | Simplified data flow |
| [presentation/](presentation) | Slides (PPTX and PDF). The abstract video is excluded from version control |
| [site/](site) | Deployable static site: the story, the earlier story and the demo |
| [story/](story) | Source of the scroll story and its data pipeline (`story/SPINE.md`) |

The five source PDFs and the abstract video are excluded from version control. The papers are copyrighted and this repository is public. See `.gitignore`.

## Visual demo

`demo/index.html` is a single self-contained page (no server, no internet) that shows the prototype working: drag a slider for how far the build has got, pick what the operator says, and see which steps are kept, taken off in order, and rebuilt, what the robot replies, and how long a restart or a naive replanner would take instead. Press *Play the changeover* to watch the steps come off and go back on. Every value is computed by the real code and embedded as JSON. Rebuild it with `python -m demo.build_demo`, then open the file in a browser. It shows the simulated planning layer only, and says so on the page.

## Story site

`site/` is a static site for a non-technical visitor: an icon-led scroll story at `/`, the earlier detailed story at `/classic/`, and the interactive demo at `/demo/`. Every number on the story comes from `story/src/data/evidence.json`, generated by `python story/scripts/build_data.py` from the code and `experiments/results/results.md`; `tests/test_story_data.py` pins those numbers to the results file and to the docs they are quoted from. Rebuild with `cd story && npm install && npm run site`. `vercel.json` at the repository root serves only `site/`, so a Git-connected Vercel project deploys the prebuilt files with no build step. The design notes and fact ledger are in `story/SPINE.md`.

## Quick start

```bash
python -m experiments.reproduce            # tests, then every experiment (1 to 2 minutes)
python -m pytest tests -q                  # 243 tests
python -m taskflux.demo                    # scripted operator dialogue
```

## A note on one of the sources

`papers/three.pdf` is Byrne, "Vision-Language Models for Human-Robot Collaboration: Real-Time Task Understanding and Execution", Journal of Computer Science and Software Applications, 2025.

The robotics title sits above an abstract describing CNN-LSTM stock price prediction on the CSI 300 index. The keyword list is the stock prediction one too. The body then discusses robots. That mismatch is present in the published version, which means the manuscript was never reviewed.

Its reported figures are round numbers with no variance, from twenty trials per condition. They are not usable as evidence and the paper has been dropped from the reference list, replaced by Fan and Zheng (2024) in the Journal of Manufacturing Systems. Full reasoning in `docs/00-source-audit.md`.

## Verified figures

Everything below was read directly from the source PDFs and can be cited without rechecking.

**OpenVLA (Kim et al., CoRL 2024).** 7B parameters on Prismatic-7B, Llama 2 with a fused SigLIP and DINOv2 encoder. 970k episodes from Open X-Embodiment. Actions discretised into 256 bins per dimension, written over the 256 least-used Llama tokens. 70.6 +/- 3.2 percent across 29 tasks, 16.5 absolute points above RT-2-X at seven times fewer parameters. LoRA rank 32 gives 68.2 +/- 7.5 percent against 69.7 +/- 7.2 percent for full fine-tuning, training 97.6M of 7.19B parameters, 59.7 GB VRAM at batch 16 against 163.3 GB sharded across two GPUs, one task in 10 to 15 hours on a single A100. Stated limitations: single image only, no proprioception, no observation history, throughput too low for 50 Hz control.

**QUAR-VLA / QUART (Ding et al., ECCV 2024).** QUARD dataset, 259k simulated plus 3k real episodes. QUART scores 0.66 on seen tasks against 0.44 for CLIP and 0.46 for VC-1. Baselines score exactly 0.0 on crawl and unload where QUART reaches 0.32 and 0.12.

**OWG (Tziafas and Kasaei, CoRL 2024).** GPT-4V with Mask-RCNN and GR-ConvNet. Two UR5e arms, Robotiq 2F-140 grippers, 50 Gazebo trials per scenario over 30 object models. Simulation seen/unseen: isolated 78.0/82.0, cluttered 62.0/66.0. Real: isolated 83.3/66.6, cluttered 50.0/50.0. Beats CROG and SayCan-IM in every cell. The authors note the modular pipeline "suffers from error cascading effects introduced by the segmentor and grasp synthesis models", which is the argument for keeping the low-level policy monolithic.

**Fan, Yin, Wang, Dong, Zheng and Wang (Frontiers of Engineering Management, 2024).** 109 papers, Web of Science plus Scopus plus IEEE Xplore, keywords "human-robot" and "vision language", 2020 to 2024. Section 6.2 states real-time task planning in dynamic scenes "remains an unresolved issue". Section 6.6, "Dynamic task adaptation and unsupervised evaluation", says current methods "always rely on an assumption of an ideal training environment" and calls for "a continuous learning mechanism". That is this project's problem statement, written by someone else, with no solution attached.

## Still to verify before submission

- The exact success figure for Fan and Zheng (2024). The current deck cites 93.3 percent. Confirm it in the JMS paper.
- Author lists, venues and years for the planning and continual-learning rows of the literature table, which are described qualitatively rather than numerically on purpose.
- Page ranges for RT-1, RT-2 and Open X-Embodiment. Cross-check against the existing reference slide rather than retyping.

## Known limitations

Reversibility is hand-authored. The process description telling the reconciler which steps can be undone is written by a human, not learned. That caps generality.

Undo is a harder manipulation problem than assembly. Extracting a seated connector is contact-rich, and the OpenVLA authors concede Diffusion Policy is smoother on that class of task. Undo success may end up being the binding constraint.

Latency compounds. Transcription, an LLM call, a reconciliation pass and a policy switch stack in front of a policy already running at single-digit hertz. Workable for a changeover a few times per shift. Not workable for anything reactive.

Evaluation will be small-n. A single-arm student cell cannot reach the 50 trials per scenario that OWG reports or the 500 per suite that OpenVLA reports. Plan for 10 to 15 episodes per condition, report raw counts alongside percentages, and do not pool conditions to inflate n. The conditions are the finding.
