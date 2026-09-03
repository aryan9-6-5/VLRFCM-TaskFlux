# VLRFCM-TaskFlux

Vision Language Robotics for Collaborative Manufacturing.

Major project, Batch 03, Department of CSE (AI and ML), Vardhaman College of Engineering, Hyderabad. Supervisor: Dr. Ramachandro Majji.

This repository holds the literature review, the refined problem framing, the review paper draft, and the evaluation protocol for TaskFlux, an adaptation layer that lets a collaborative robot revise its assembly plan when the operator changes the product variant mid-task.

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
| Task changeover | operator changed the requirement | replaced mid-episode | nothing |

Ambiguity work resolves which object an instruction refers to while everyone still agrees on what is being built. Replanning work reacts when the world does not match the prediction, with the goal still intact. Neither covers the case where the goal is withdrawn and replaced while execution is in progress.

## The five contributions

1. **Changeover intent classification.** Sort each operator utterance into clarification, parameter edit, changeover, or abort. Existing systems collapse all four into "an instruction". The two error directions have opposite costs: a false changeover destroys completed work, a missed changeover finishes the wrong product.

2. **Partial-assembly state reconciliation.** The novel component. Partition completed steps into keep, undo and discard against the new goal, order the undos by reverse dependency, and escalate to the operator when a required undo crosses an irreversible step such as cured adhesive or a set rivet. No paper in the reviewed set does this.

3. **A refusal path.** Check reachability, collision against current workspace occupancy, tool availability and process constraints before committing. When a check fails, say which constraint blocked it in a sentence the operator can act on, rather than returning an error code.

4. **Known versus novel routing with a gated merge-back.** Known variants route to the base policy. Novel ones get a LoRA adapter at rank 32, following the OpenVLA authors' own default. An adapter merges into the base weights only after passing a quality gate and a retention gate.

5. **An evaluation protocol.** No benchmark measures mid-episode task change, so defining the measurement is part of the contribution.

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
| `Architecture A3.png` | Six-stage proposed architecture |
| `proposed_system_flow_diagram.png` | Simplified data flow |

The five source PDFs and the abstract video are excluded from version control. The papers are copyrighted and this repository is public. See `.gitignore`.

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
