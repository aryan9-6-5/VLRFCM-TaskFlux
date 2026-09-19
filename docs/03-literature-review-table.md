# Literature review table

Two versions below. Table 1 is the full comparative survey, grouped by theme, for the review paper. Table 2 is the compressed six-row version formatted for a slide.

A note on numbers before you use these. Everything in the "Reported results" column for rows 1, 2, 3 and 15 was read directly out of the PDFs in `papers/`. Everything else is described qualitatively on purpose, because I have not verified those figures against the source documents. Do not put a number in your submitted paper that you have not personally seen in the original PDF. Verification checklist is at the bottom.

---

## Table 1. Comparative review of vision-language robotics for collaborative manufacturing

### Group A. Generalist vision-language-action policies

| # | Work | Year | Method | Data | Reported results | Contribution | Gap relative to task changeover |
|---|---|---|---|---|---|---|---|
| 1 | OpenVLA (Kim et al., CoRL) | 2024 | 7B VLA. Llama 2 backbone, fused SigLIP and DINOv2 vision encoder. Actions discretised into 256 bins written over unused Llama tokens | Open X-Embodiment, 970k episodes | 70.6 +/- 3.2 percent over 29 tasks; 16.5 points above RT-2-X at 7x fewer parameters; LoRA r=32 gives 68.2 +/- 7.5 percent training 1.4 percent of weights | Open weights, code and data. Establishes LoRA as a viable adaptation route on consumer hardware | Instruction is fixed for the episode. Single image, no proprioception, no history. Low control rate |
| 2 | QUAR-VLA / QUART (Ding et al., ECCV) | 2024 | VLA for quadruped locomotion and manipulation with a unified 11-dimensional command space | QUARD, 259k simulated plus 3k real episodes | QUART 0.66 on seen tasks against 0.44 for CLIP and 0.46 for VC-1; baselines score 0.0 on crawl and unload where QUART reaches 0.32 and 0.12 | Shows VLA training transfers to a non-arm embodiment | Task set enumerated in advance. No mechanism for a task that changes during execution |
| 3 | RT-2 (Brohan et al., CoRL) | 2023 | Web-pretrained VLM co-fine-tuned on robot trajectories, actions emitted as text tokens | Internet VQA plus robot demonstrations | Strong emergent semantic generalisation reported by the authors | Established the VLA formulation this project builds on | Closed weights. Fixed-task assumption. No replanning layer |
| 4 | RT-1 (Brohan et al.) | 2022 | Transformer policy over image and instruction tokens | 130k demonstrations, 700 tasks | Reported high multi-task success on a mobile manipulator | First large-scale demonstration that one transformer can absorb many manipulation tasks | Task identity supplied at episode start and never revised |
| 5 | Open X-Embodiment / RT-X (O'Neill et al., ICRA) | 2024 | Cross-embodiment dataset aggregation and joint policy training | 60-plus datasets, 22 embodiments | Positive transfer across embodiments reported | The dataset OpenVLA trains on | Dataset contribution, no task adaptation mechanism |
| 6 | Octo (Octo Model Team) | 2024 | Transformer policy with a diffusion action head and modular input tokenisers | Open X-Embodiment subset | Competitive with generalist baselines, flexible fine-tuning | Shows modular conditioning is compatible with generalist policies | Same fixed-goal assumption |

### Group B. Language grounding and ambiguity in human-robot collaboration

| # | Work | Year | Method | Data | Reported results | Contribution | Gap relative to task changeover |
|---|---|---|---|---|---|---|---|
| 7 | Fan and Zheng, J. Manufacturing Systems 74:1009-1018 | 2024 | Vision-language guided action planning for ambiguity mitigation in collaborative assembly | Assembly scenes with under-specified operator instructions | Authors report high task success on ambiguous referring instructions | The closest prior work to this project, and the correct baseline to compare against | Resolves which object an instruction refers to. The goal state itself is fixed throughout |
| 8 | OWG (Tziafas and Kasaei, CoRL) | 2024 | GPT-4V with Mask-RCNN and GR-ConvNet. Referring segmentation, grounded grasp planning, contact-reasoning grasp ranking, all zero-shot via visual prompting | OCID-VLG, Gazebo with 30 object models, dual UR5e hardware | Simulation seen/unseen: isolated 78.0/82.0, cluttered 62.0/66.0. Real: isolated 83.3/66.6, cluttered 50.0/50.0. Beats CROG and SayCan-IM in every cell | Demonstrates zero-shot open-vocabulary grasping without task-specific training | Single-object grasping, not multi-step assembly. Authors themselves flag error cascading between modules, which argues for keeping the VLA monolithic in the execution path |
| 9 | CLIPort (Shridhar et al., CoRL) | 2021 | Two-stream policy fusing CLIP semantics with a spatial Transporter stream | Ravens-style tabletop tasks | Strong sample efficiency on language-conditioned pick and place | Early demonstration that CLIP features carry usable manipulation semantics | Table-top rearrangement only, one instruction per episode |
| 10 | PerAct (Shridhar et al., CoRL) | 2022 | Perceiver-based voxel policy for language-conditioned manipulation | RLBench plus real demonstrations | Multi-task success from few demonstrations | Brings 3D structure into language-conditioned control | No plan-level reasoning, no adaptation to a changed goal |
| 11 | CLIP (Radford et al., ICML) | 2021 | Contrastive image-text pretraining | 400M image-text pairs | Strong zero-shot classification transfer | The perception grounding primitive used across this whole field, including our variant-grounding module | Not a robotics model. Provides similarity, not action |

### Group C. LLM task planning and replanning

| # | Work | Year | Method | Data | Reported results | Contribution | Gap relative to task changeover |
|---|---|---|---|---|---|---|---|
| 12 | SayCan (Ahn et al., CoRL) | 2022 | LLM scores candidate skills, an affordance model scores feasibility, product selects the next skill | Kitchen skill library | Long-horizon instruction following on a real mobile manipulator | Introduced the feasibility gate that our safety module generalises | Skill library fixed. Plan is generated once from a goal that never changes |
| 13 | Code as Policies (Liang et al., ICRA) | 2023 | LLM writes executable policy code that calls perception and control APIs | Prompted, no training | Generalises to novel instructions through code composition | Shows LLM output can be structured and verifiable rather than free text | Generates a program for a stated goal. No notion of revising it mid-execution |
| 14 | Inner Monologue (Huang et al., CoRL) | 2022 | Closed-loop replanning driven by textual feedback from success detectors, scene descriptors and human input | Simulated and real manipulation | Improved long-horizon success from feedback grounding | The canonical replanning-on-failure system | Replans when execution diverges from prediction. The goal is never withdrawn and replaced |
| 15 | Fan, Yin, Wang, Dong, Zheng and Wang, Frontiers of Engineering Management | 2024 | Systematic survey. Web of Science, Scopus and IEEE Xplore, keywords "human-robot" and "vision language", 2020 to 2024 | 109 selected papers | Taxonomy across planning, navigation, manipulation and skill transfer | Section 6.6 explicitly calls for "dynamic task adaptation" and "a continuous learning mechanism". Section 6.2 states real-time planning in dynamic scenes "remains an unresolved issue" | Survey only. Names the gap this project fills but does not build anything |

### Group D. Parameter-efficient adaptation and continual learning

| # | Work | Year | Method | Data | Reported results | Contribution | Gap relative to task changeover |
|---|---|---|---|---|---|---|---|
| 16 | LoRA (Hu et al., ICLR) | 2022 | Low-rank update matrices injected into frozen linear layers | NLP benchmarks | Matches full fine-tuning at a fraction of trainable parameters | The mechanism behind our specialised policy head | Designed for offline adaptation to a static target task |
| 17 | QLoRA (Dettmers et al., NeurIPS) | 2023 | LoRA over a 4-bit quantised base model | Instruction tuning benchmarks | Large memory reduction at near-parity quality | Makes on-premise adaptation feasible on a single workstation GPU | Same offline assumption |
| 18 | Model soups (Wortsman et al., ICML) | 2022 | Averaging weights of independently fine-tuned models | Vision benchmarks | Averaging can beat the best single member | Evidence that weight-space merging is viable, which is what our merge-back engine does | No gating on retention or safety. Merging is unconditional |
| 19 | Task arithmetic (Ilharco et al., ICLR) | 2023 | Add and subtract task vectors in weight space to edit model behaviour | Vision and language benchmarks | Behaviour can be composed and removed arithmetically | Suggests a principled way to fold an adapter in and pull it back out if retention drops | Not validated in a control or safety-critical setting |
| 20 | Elastic weight consolidation (Kirkpatrick et al., PNAS) | 2017 | Penalise change to parameters important for earlier tasks | Sequential supervised tasks | Reduces catastrophic forgetting | The theoretical basis for the retention gate | Predates VLAs entirely, never tested on a manipulation policy |

### Excluded source

Byrne, "Vision-Language Models for Human-Robot Collaboration: Real-Time Task Understanding and Execution", J. Computer Science and Software Applications, 2025. Excluded. The published abstract and keywords describe CNN-LSTM stock price prediction on the CSI 300 index, not robotics, indicating no editorial review took place. Reported figures (91 percent success, 95 percent grounding accuracy, 1.4 s latency, 20 trials per condition, no variance reported) are not usable as evidence. See `00-source-audit.md`.

---

## Table 2. Compressed version for a slide

| # | Work | Year | Approach | Key result | Gap |
|---|---|---|---|---|---|
| 1 | OpenVLA | 2024 | 7B VLA on Open X-Embodiment, LoRA fine-tuning | 70.6% over 29 tasks, +16.5 pts over RT-2-X | Instruction fixed per episode |
| 2 | RT-2 | 2023 | Web-pretrained VLM co-fine-tuned on robot data | Strong semantic generalisation | Closed, fixed-task, no replanning |
| 3 | QUAR-VLA | 2024 | VLA for quadrupeds, 262k demonstrations | Baselines score 0.0 on crawl and unload, QUART 0.32 and 0.12 | Task set enumerated in advance |
| 4 | OWG | 2024 | GPT-4V plus segmentation plus grasp synthesis, zero-shot | Real robot 83.3% isolated, 50.0% cluttered | Grasping only, module error cascading |
| 5 | Fan and Zheng | 2024 | Vision-language ambiguity mitigation in HRC assembly | Resolves under-specified referring instructions | Resolves which object, not whether the task changed |
| 6 | Fan et al. survey (FEM) | 2024 | Systematic review of 109 papers | Calls for dynamic task adaptation and continuous learning | Survey, no implementation |

---

## Verification checklist before submission

Verified by me from the PDFs in `papers/`:

- OpenVLA 70.6 +/- 3.2 percent, 29 tasks, 16.5 points over RT-2-X, 970k episodes, LoRA r=32 at 68.2 +/- 7.5 percent, 1.4 percent of parameters, 97.6M trainable, 59.7 GB at batch 16, 10 to 15 hours on one A100
- QUART table 2 values and the 0.0 baseline scores on crawl and unload
- QUARD 259k simulated plus 3k real
- OWG table 2 values, the 30 Gazebo object models, the dual UR5e setup, and the error-cascading limitation
- Fan et al. FEM: 109 papers, the 2020 to 2024 window, the three databases, and the section 6.2 and 6.6 wording

You still need to confirm from the original sources:

- The exact success figure for Fan and Zheng (2024). Your current deck cites 93.3 percent. Find it in the JMS paper before it goes in the draft
- Author list, venue and year for every row in groups C and D, since I described those qualitatively rather than pulling numbers
- Full bibliographic details for RT-1, RT-2 and Open X-Embodiment page ranges. Your existing reference slide has these, so cross-check rather than retyping

---

## Additional related work found in the novelty search

Added after the search recorded in [05](05-novelty-and-formal-results.md). None of these were in the original twenty rows, and none has been read in full. **Confirm authors, venue, year and claims before adding a row.**

| Work | Theme | One-line relevance | Verification status |
|---|---|---|---|
| SwitchVLA, arXiv 2506.03574 | Policy-level task switching | Closest competitor. Implicit switching from execution state. | abstract read |
| Vision-Language-Policy model for dynamic robot task planning, arXiv 2512.19178 | Replanning with history | Forward replan on a new instruction. | page read |
| "Do This Instead", ACM THRI, DOI 10.1145/3623385 | Correction handling | Generates undo steps on corrected instructions (rule-based cognitive architecture). | search summary only |
| Fox, Gerevini, Long, Serina, "Plan stability", ICAPS 2006 | Plan repair | Repair versus replanning in classical planning. | search summary only |
| Nebel and Koehler (IJCAI 1993; AIJ 1995) | Plan modification complexity | Conservative plan modification is as hard as planning in general. | search summary only |
| Yin et al., selective disassembly sequence planning, DOI 10.1177/09544054231201873 | Disassembly planning | Undo ordering to reach a target part. | search summary only |
| KnowNo, arXiv 2307.01928 | Asking when uncertain | Conformal prediction for LLM planners. | search summary only |
| Yell At Your Robot, arXiv 2403.12910; Hi Robot, arXiv 2502.19417 | Language corrections | Hierarchical correction handling. | search summary only |
| InternVLA-M1, arXiv 2510.13778 | VLA with mid-execution instruction test | Reports new instructions issued mid-execution. | search snippet only |
