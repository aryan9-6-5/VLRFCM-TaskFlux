# Adaptive vision-language-action systems for task changeover in collaborative manufacturing: a review and a proposed architecture

Draft for the Phase-1 review. Target length once expanded: 8 to 10 pages, IEEE two-column.

Authors: Batch 03, Department of CSE (AI and ML), Vardhaman College of Engineering, Hyderabad
Supervisor: Dr. Ramachandro Majji

---

## Abstract

Vision-language-action models let a robot map a camera image and a natural language instruction directly to motor commands, and recent open models such as OpenVLA reach 70.6 percent mean success across 29 manipulation tasks while remaining fine-tunable on a single GPU. All of this work shares one assumption: the instruction holds constant for the length of the episode. On a high-mix, low-volume assembly line that assumption breaks several times a shift, because the operator changes the product variant while the robot is partway through building the previous one.

This paper reviews vision-language robotics for collaborative manufacturing through the specific lens of task change. We group twenty representative works into generalist VLA policies, language grounding and ambiguity resolution, LLM-based planning and replanning, and parameter-efficient continual adaptation, and we show that each group leaves the same thing untouched. Ambiguity work resolves which object an instruction refers to while holding the goal fixed. Replanning work reacts to execution failure while holding the goal fixed. Recent task-switching and undo-on-correction work handles the case where the goal itself is withdrawn and replaced mid-episode at the policy or plan level, without reasoning about which completed steps can stay, which must come off, and when a change must be refused because a step cannot be undone.

We then propose TaskFlux, an adaptation layer that sits above an existing VLA rather than replacing it. Its four components are a changeover intent classifier, a partial-assembly state reconciler that decides which completed steps to keep, undo or discard, a feasibility and safety gate that can refuse a request and explain why, and a LoRA-based specialised policy head whose adapters are merged into the base model only after passing a retention check. Because no benchmark exists for mid-episode task change, we also define an evaluation protocol with five metrics: changeover success rate, adaptation latency, rework cost, false changeover rate, and retention score.

Keywords: vision-language-action models, human-robot collaboration, task replanning, high-mix low-volume manufacturing, parameter-efficient adaptation

---

## 1. Introduction

High-mix, low-volume manufacturing is the awkward middle of production. Volumes are too low to justify a dedicated line and too high to do by hand. Medical device assembly, custom electronics and aerospace subassembly all live there, and in all three the product variant changes often, sometimes several times in one shift.

Industrial robots handle this badly. A variant switch means a stop, a reprogram, a revalidation and a restart, and the cost of that downtime is what keeps a lot of this work manual. Collaborative robots were supposed to help, and they do help with safety and with physical proximity to the operator, but the reprogramming problem is untouched. A cobot that needs a technician with a teach pendant every time the part changes is not flexible in any way that matters to a plant manager.

Vision-language-action models looked like the answer. Train one policy on enough demonstrations, condition it on a natural language instruction, and it should generalise to new objects and new phrasings without retraining. RT-2 showed the idea worked. OpenVLA showed it could be open, reproducible, and cheap enough to adapt on a single A100 in ten to fifteen hours using LoRA at rank 32, which trains 1.4 percent of the model's weights and still matches full fine-tuning.

But look at how these systems are actually evaluated. An episode begins, an instruction is provided, the policy runs to completion or failure, the episode ends. The instruction is an input, supplied once. There is no path in the architecture for it to change while the robot is working.

That is exactly what happens in a real changeover. And the moment it happens, a second problem appears that the VLA work we reviewed does not treat: the workspace is no longer empty. Parts have already been placed. Screws are already torqued. A plan generated fresh from the current camera frame will not account for any of that, and executing it will produce either a collision or a hybrid assembly that matches neither specification.

This paper does two things. First it reviews the field with that specific failure in mind, to establish that the gap is real rather than assumed. Second it proposes an architecture, TaskFlux, for closing it, along with the evaluation protocol that would be needed to test any such system.

Contributions:

1. A structured review of twenty works across four themes, each assessed against a single question: what happens if the task changes mid-episode
2. A three-way distinction between referential ambiguity, execution failure and task changeover, which have been conflated in the literature and which require different mechanisms
3. TaskFlux, an adaptation layer over an existing VLA, whose central component is a partial-assembly state reconciler
4. A five-metric evaluation protocol for mid-episode task change, since we found no benchmark that measures rework or refusal for it

Section 2 covers background. Section 3 states the review method. Section 4 is the thematic review. Section 5 is the comparative table. Section 6 is the gap analysis. Section 7 presents TaskFlux. Section 8 gives the evaluation protocol. Section 9 lists open problems. Section 10 concludes.

---

## 2. Background

### 2.1 From vision-language models to vision-language-action models

CLIP established that contrastive pretraining on image-text pairs produces representations that transfer to tasks the model was never trained on. Robotics picked this up quickly. CLIPort fused CLIP semantics with a spatial stream for language-conditioned pick and place, and PerAct extended the idea into voxel space.

The step to a VLA came when RT-2 treated actions as text. Discretise each dimension of the robot action into bins, assign each bin a token, and the whole control problem becomes next-token prediction over a vocabulary that happens to include motor commands. That means every trick developed for training large language models applies directly to training robot policies.

OpenVLA is the open realisation of that idea and the backbone this project uses. It is a 7B model built on Prismatic-7B, which pairs Llama 2 with a two-part visual encoder that concatenates SigLIP and DINOv2 features. The authors chose that pairing deliberately: SigLIP carries high-level semantics, DINOv2 carries low-level spatial detail, and spatial detail is what a manipulation policy needs. Each of the seven action dimensions is discretised into 256 bins set by the 1st and 99th quantiles of the training distribution, and those 256 tokens overwrite the 256 least-used entries in the Llama tokenizer.

Trained on 970k episodes from Open X-Embodiment, it reaches 70.6 percent mean success across 29 tasks, which is 16.5 absolute points above RT-2-X despite having seven times fewer parameters.

### 2.2 What the OpenVLA authors say is missing

Their own limitations section is worth taking seriously, because it constrains what any system built on top can do.

The model sees one image. No proprioception, no wrist camera, no observation history. Inference throughput is too low for high-frequency control; the authors note it cannot support something like ALOHA at 50 Hz. And on narrow dexterous tasks, Diffusion Policy still produces smoother trajectories, which the authors attribute to action chunking and temporal smoothing that OpenVLA does not do.

For our purposes the throughput limit is the binding one. A changeover that takes a few seconds to reason about is acceptable when changeovers happen a handful of times per shift. It would not be acceptable for anything reactive.

### 2.3 Parameter-efficient adaptation

LoRA freezes the base weights and learns a low-rank update on each linear layer. On OpenVLA the numbers are unusually favourable. Rank 32 gives 68.2 percent against 69.7 percent for full fine-tuning, trains 97.6M parameters instead of 7.19B, and fits in 59.7 GB at batch size 16 where full fine-tuning needs 163.3 GB sharded across two GPUs. Rank had almost no effect on the result, so 32 is a reasonable default rather than a tuned choice.

That is what makes a per-variant adapter practical. It is also what makes the merge-back question interesting, because if adapters are cheap you will accumulate a lot of them and you need a policy for what to do with the pile.

---

## 3. Review method

We started from the six sources compiled during the project's initial survey and expanded outward along citation edges from two anchors: OpenVLA as the technical backbone and the Fan et al. survey in Frontiers of Engineering Management as the domain reference. That survey itself screened Web of Science, Scopus and IEEE Xplore for combinations of "human-robot" and "vision language" over 2020 to 2024 and retained 109 papers, so it provides reasonable coverage of the manufacturing side without us repeating the search.

Inclusion required a paper to do at least one of: propose or evaluate a policy that consumes both visual and language input, propose a planning or replanning mechanism driven by language, or propose an adaptation method we intend to use. Twenty works met that bar and appear in Table 1.

One source was excluded after screening. Byrne (2025) in the Journal of Computer Science and Software Applications carries a robotics title over an abstract and keyword list describing CNN-LSTM stock price prediction on the CSI 300 index. The mismatch is present in the published version, which indicates the manuscript was never reviewed. Its reported results are round numbers with no variance, from twenty trials per condition, and we do not treat them as evidence. We mention the exclusion rather than quietly dropping it, because journals of this kind are increasingly common in search results for this topic and other groups will hit the same paper.

---

## 4. Thematic review

### 4.1 Generalist VLA policies

RT-1 showed one transformer could absorb hundreds of manipulation tasks. RT-2 added web-scale semantic knowledge by co-fine-tuning a pretrained VLM on robot trajectories. Open X-Embodiment aggregated over sixty datasets across twenty-two embodiments and demonstrated positive transfer between them. OpenVLA made the recipe open. Octo showed the same territory can be reached with a diffusion action head and modular input tokenisers.

QUAR-VLA is useful as a control on the embodiment question. Ding et al. built QUART for quadrupeds over an 11-dimensional command space and trained on QUARD, 259k simulated plus 3k real episodes. The gap between QUART and the CLIP, R3M and VC-1 baselines widens as tasks get harder, and on the crawl and unload tasks the baselines score exactly zero while QUART reaches 0.32 and 0.12. The formulation clearly transfers off arms.

What all six share: the instruction is bound once, at the start of the episode, and the architecture provides no way to rebind it.

### 4.2 Language grounding and ambiguity in HRC

Fan and Zheng (2024) is the closest published work to this project and should be the primary baseline. They target under-specified operator instructions in collaborative assembly, the "hand me that one" case, and use vision-language guidance to pick the intended referent.

It is worth being precise about what that solves and what it does not. The operator and the robot already agree on what is being built. The uncertainty is over which physical object satisfies a step of an agreed plan. Resolve it and execution continues along the same plan. This is genuinely useful and genuinely different from what happens when the operator says "we are building the B variant now", where the plan itself is no longer valid.

OWG approaches grounding from the grasp side. Tziafas and Kasaei prompt GPT-4V with visual markers over segmented objects and candidate grasps, in three zero-shot stages: referring segmentation, grounded grasp planning, then grasp ranking by contact reasoning. On real hardware with two UR5e arms they reach 83.3 percent on isolated unseen objects and 50.0 percent in clutter, beating both a supervised baseline (CROG) and an LLM planner baseline (SayCan-IM) in every cell.

Their limitations section carries a lesson we adopted. Being modular, OWG "suffers from error cascading effects introduced by the segmentor and grasp synthesis models". A segmentation error becomes a grasp error becomes a task failure, and there is no path to recover. That is a direct argument for keeping the low-level policy monolithic and putting the language reasoning above it rather than in series with perception.

### 4.3 LLM planning and replanning

SayCan pairs an LLM's estimate of what a skill contributes toward a goal with an affordance model's estimate of whether that skill will succeed here and now, and multiplies them. The feasibility gate is the part we generalise: our safety module does the same job but checks process constraints, not just affordances.

Code as Policies has the LLM emit executable code that calls perception and control APIs, which makes the plan inspectable and verifiable instead of free text. That is a property we want for a plan that a human operator may need to approve.

Inner Monologue is the canonical replanning system. Success detectors, scene descriptors and human feedback are all injected back into the LLM's context as text, and the plan is revised when reality diverges from prediction.

Read those three together and the pattern is clear. The goal is a constant. Planning generates a route to it, replanning generates a new route when the old one fails, and no mechanism exists for the goal to be replaced. That is the structural gap.

### 4.4 Parameter-efficient adaptation and continual learning

LoRA and QLoRA make per-variant adaptation cheap enough to do on-premise. Model soups and task arithmetic show that merging in weight space works and can even be reversed, which matters if an adapter turns out to have hurt something. Elastic weight consolidation gives the theoretical account of why unconstrained sequential fine-tuning destroys earlier competence.

None of this has been assembled into a loop that runs on a factory floor with a validation gate in the middle. That assembly is part of what we are proposing.

### 4.5 The manufacturing view

The Fan et al. survey is where the domain requirements are stated most clearly, and two of its future-work sections read like a specification for this project.

Section 6.2 says VLM-based task planning is focused on static scenes and that "real-time task planning in dynamic scenes remains an unresolved issue".

Section 6.6, titled "Dynamic task adaptation and unsupervised evaluation", says current methods "always rely on an assumption of an ideal training environment", that real deployment "necessitates human operators for continuous monitoring and intervention", and that this "significantly hinders real applications". It then argues robots "must evolve to autonomously adapt to dynamic environments and tasks" and calls for "a continuous learning mechanism" allowing them "to adapt and improve their performance autonomously over time based on new experiences and feedback".

That is our problem statement, written by someone else, in a survey of 109 papers, with no solution attached.

---

## 5. Comparative table

Table 1 in `03-literature-review-table.md` gives the full twenty-row comparison across method, data, reported results, contribution, and the gap relative to task changeover. Table 2 there is the condensed six-row version for presentation.

---

## 6. Gap analysis

### 6.1 Three problems that get conflated

The literature contains two named problems and one unnamed one.

Referential ambiguity: the goal is agreed, but which object does the instruction denote. Trigger is uncertainty in language. The goal is fixed. Fan and Zheng address this.

Execution failure: the goal is agreed and the referent is clear, but the world did not do what the plan predicted. Trigger is a divergence between expected and observed state. The goal is fixed. Inner Monologue and its descendants address this.

Task changeover: the operator has withdrawn the goal and supplied a different one, while execution is in progress. Trigger is an external decision, not an error. The goal is replaced. Recent policy-level task-switching work touches it; we found none that reasons about partial-assembly state.

The three need different machinery. Ambiguity needs better grounding. Failure needs monitoring and recovery. Changeover needs goal-state comparison and a way to deal with work already done.

### 6.2 The partial-state problem

This is the part that has no precedent at all.

Suppose a plan has n steps and the goal is replaced at step k. The naive response is to regenerate a plan from the new goal and the current image. That fails, because the current image shows a partially assembled product and the planner will either treat the placed parts as obstacles to avoid or ignore them entirely. Either way the output is wrong.

What is actually needed is a comparison between the effects of steps 1 through k and the requirements of the new goal, producing a partition into steps to keep, steps to undo, and steps to discard, plus a valid ordering for the undos. Undo has to respect dependencies, an outer cover comes off before the inner bracket, and it has to respect irreversibility, because cured adhesive and set rivets do not come back out.

We found nothing in the reviewed literature that does this with a completeness guarantee, although plan repair, selective disassembly planning and undo-on-correction work are adjacent. Rearrangement planning in classical robotics is adjacent but assumes a symbolic world model with clean pre- and post-conditions, which is exactly what a VLA does not give you.

### 6.3 Adaptation without forgetting

A system that learns variant B by fine-tuning on B and then cannot build A any more has not adapted. It has moved. Every project in this space needs a retention answer and most do not state one.

### 6.4 There is no benchmark for rework or refusal

Every dataset in Table 1 supplies one instruction per episode. There is no public benchmark with a mid-episode instruction change, no metric for how fast a system adapts, and no metric for how much finished work an adaptation destroyed. Defining these is a prerequisite for the field, not an afterthought.

---

## 7. Proposed architecture: TaskFlux

An adaptation layer over an existing VLA. Six stages.

### Stage 1. Instruction intake

Operator speech is transcribed and passed to the orchestrator along with the current camera frame and the execution state, meaning which steps of the active plan have completed.

### Stage 2. Agentic orchestrator

An LLM performs four jobs in sequence.

Intent understanding produces a structured reading of the utterance: what the operator wants, which product variant is implied, and which constraints they stated.

Changeover classification assigns the utterance to one of four types: clarification, parameter edit, changeover, or abort. Only a changeover triggers reconciliation. This classification is where a large share of the system's errors will live, and the two error directions have very different costs, so the classifier should be biased toward asking rather than guessing.

Feasibility and safety analysis checks reachability, collision against the current workspace occupancy, tool and fixture availability, and process constraints such as torque sequence and cure time.

The critique step reports what it cannot do and why, in a sentence the operator can act on, rather than failing silently or attempting a partial adaptation.

### Stage 3. State reconciliation

The novel component. Inputs are the completed prefix of the old plan, the goal state implied by the new variant, and a process description that marks each step's reversibility and its dependencies.

Output is a keep set, an undo set ordered in reverse dependency order, and a discard set, followed by the residual steps of the new plan. If any required undo touches an irreversible step, the reconciler stops and escalates to the operator with the specific blocking step named.

### Stage 4. Policy selection

Known variant, meaning present in the skill library, routes to the base OpenVLA policy. Unknown variant instantiates a LoRA adapter at rank 32, following the OpenVLA authors' own default, and routes to that.

### Stage 5. Execution and validation

The selected policy executes. A validation module checks each completed step against the expected post-condition using the perception module, and checks the finished assembly against the new specification. Novel-variant executions run under stricter validation and with a lower intervention threshold.

### Stage 6. Knowledge update

Successful adaptations are logged to a dynamic knowledge base holding the skill library, a vector store of past instructions and their resolved plans, and execution traces.

The merge engine folds an adapter into the base weights only when two gates pass. The quality gate requires success above threshold across a minimum number of executions. The retention gate re-evaluates a held-out set of previously mastered variants after a candidate merge and rejects the merge if any regresses beyond tolerance. Because merging is done in weight space, a rejected merge can be backed out.

### 7.1 Why the layer sits above the VLA rather than inside it

Two reasons, both taken from the reviewed papers.

OWG's error cascading result argues against putting more modules in series with perception and control. Keeping OpenVLA monolithic in the execution path limits the depth of the cascade.

Practically, the base model stays a stock checkpoint. That means it can be swapped for a newer VLA without redesigning the adaptation layer, which matters in a field where the state of the art moves every few months.

---

## 8. Evaluation protocol

Full definitions in `04-evaluation-protocol.md`. Summary here.

The core experimental unit is a changeover episode. Start executing variant A. At a controlled step k, issue an instruction. Record everything that follows.

Five metrics:

Changeover success rate. Fraction of episodes where the final assembly matches the new specification. The headline number.

Adaptation latency. Seconds from the end of the operator's utterance to the first action that is correct under the new plan. Report the language reasoning time and the reconciliation time separately, because they have different optimisation paths.

Rework cost. Undo actions divided by steps already completed at the moment of the change. A perfect reconciler undoes only what conflicts. This measures how much finished work the adaptation destroyed.

False changeover rate. Fraction of clarification or parameter-edit utterances that were misclassified as changeovers. Report the opposite direction, missed changeovers, separately, since the consequences differ.

Retention score. Success rate on variant A measured after the system has learned variant B and merged the adapter. Without this number, any claim about continual learning is unsupported.

Conditions to vary: the step index k at which the change arrives, early against late; whether the change requires undo or only truncation; whether the new variant is known or novel; and whether the required undo crosses an irreversible step, which should produce a refusal rather than an attempt.

Baselines: OpenVLA with the original instruction, which should fail every changeover episode and establishes the floor; OpenVLA restarted from scratch with the new instruction, which establishes the cost of the current industrial practice; an LLM replanner with no reconciler, which isolates the contribution of the reconciliation step; and the full system.

That third baseline is the important ablation. It is the one that shows whether state reconciliation actually earns its place or whether naive replanning would have been enough.

---

## 9. Open problems

Reversibility is hand-authored. In this project the process description that tells the reconciler which steps can be undone is written by a human. Learning it from demonstration or from physical interaction is open and hard.

Undo is a harder manipulation problem than assembly. Extracting a seated connector is contact-rich and OpenVLA is admittedly weaker on that class of task than a diffusion policy. Undo success may end up being the binding constraint on the whole system.

Latency compounds. A speech transcription, an LLM call, a reconciliation pass and a policy switch stack up in front of a policy that already runs at single-digit hertz. Acceptable for a shift-level changeover. Not acceptable for anything faster.

Trust and authority are unresolved. If the robot refuses an operator instruction, who overrides whom, and what gets logged. This is a human factors question that a technical paper can raise but not settle.

Merging in weight space is not well understood for control policies. Model soups and task arithmetic were validated on classification, not on a policy where a small behavioural regression can mean a collision.

---

## 10. Conclusion

The vision-language-action literature has converged on a formulation that works: condition a pretrained vision-language model on robot demonstrations, emit actions as tokens, and get generalisation across objects and phrasings that hand-programmed systems never had. OpenVLA made that formulation open and cheap to adapt.

The formulation carries one assumption that most of it leaves implicit, which is that the task is fixed for the duration of the episode. In high-mix manufacturing it is not, and the failure that follows is not a perception failure or a grounding failure. It is a system that keeps confidently building the wrong product.

We reviewed twenty works against that specific question and found the gap consistent across all four themes. We separated task changeover from the two problems it is usually confused with, referential ambiguity and execution failure, and argued that it needs different machinery, specifically a way to reconcile a half-built workspace against a replaced goal.

TaskFlux is our proposal for that machinery, and the evaluation protocol in Section 8 is our proposal for how anyone would know whether it works. Neither is validated yet. The next phase of this project builds the reconciler and runs the changeover episodes described above on a single-arm assembly cell.

---

## References

Numbered to match the existing deck where possible. Entries marked with a dagger were read in full during this review; the rest need bibliographic details confirmed against the originals before submission.

[1] A. Brohan et al., "RT-2: Vision-Language-Action Models Transfer Web Knowledge to Robotic Control," in Proc. 7th Conf. on Robot Learning (CoRL), 2023, pp. 2165-2183.

[2] M. J. Kim, K. Pertsch, S. Karamcheti et al., "OpenVLA: An Open-Source Vision-Language-Action Model," in Proc. 8th Conf. on Robot Learning (CoRL), 2024. (dagger)

[3] A. O'Neill et al., "Open X-Embodiment: Robotic Learning Datasets and RT-X Models," in Proc. IEEE ICRA, Yokohama, Japan, 2024, pp. 6892-6903.

[4] P. Ding, H. Zhao, W. Song et al., "QUAR-VLA: Vision-Language-Action Model for Quadruped Robots," in Proc. European Conf. on Computer Vision (ECCV), 2024. (dagger)

[5] G. Tziafas and H. Kasaei, "Towards Open-World Grasping with Large Vision-Language Models," in Proc. Conf. on Robot Learning (CoRL), 2024. (dagger)

[6] J. Fan, Y. Yin, T. Wang, W. Dong, P. Zheng and L. Wang, "Vision-language model-based human-robot collaboration for smart manufacturing: A state-of-the-art survey," Frontiers of Engineering Management, 2024. (dagger)

[7] J. Fan and P. Zheng, "A vision-language-guided robotic action planning approach for ambiguity mitigation in human-robot collaborative manufacturing," Journal of Manufacturing Systems, vol. 74, pp. 1009-1018, 2024.

[8] A. Radford et al., "Learning Transferable Visual Models From Natural Language Supervision," in Proc. ICML, 2021.

[9] E. J. Hu et al., "LoRA: Low-Rank Adaptation of Large Language Models," in Proc. ICLR, 2022.

[10] T. Dettmers, A. Pagnoni, A. Holtzman and L. Zettlemoyer, "QLoRA: Efficient Finetuning of Quantized LLMs," in Proc. NeurIPS, 2023.

[11] M. Ahn et al., "Do As I Can, Not As I Say: Grounding Language in Robotic Affordances," in Proc. CoRL, 2022.

[12] J. Liang et al., "Code as Policies: Language Model Programs for Embodied Control," in Proc. IEEE ICRA, 2023.

[13] W. Huang et al., "Inner Monologue: Embodied Reasoning through Planning with Language Models," in Proc. CoRL, 2022.

[14] M. Shridhar, L. Manuelli and D. Fox, "CLIPort: What and Where Pathways for Robotic Manipulation," in Proc. CoRL, 2021.

[15] M. Shridhar, L. Manuelli and D. Fox, "Perceiver-Actor: A Multi-Task Transformer for Robotic Manipulation," in Proc. CoRL, 2022.

[16] Octo Model Team, "Octo: An Open-Source Generalist Robot Policy," in Proc. Robotics: Science and Systems (RSS), 2024.

[17] A. Brohan et al., "RT-1: Robotics Transformer for Real-World Control at Scale," 2022.

[18] M. Wortsman et al., "Model Soups: Averaging Weights of Multiple Fine-tuned Models Improves Accuracy Without Increasing Inference Time," in Proc. ICML, 2022.

[19] G. Ilharco et al., "Editing Models with Task Arithmetic," in Proc. ICLR, 2023.

[20] J. Kirkpatrick et al., "Overcoming Catastrophic Forgetting in Neural Networks," PNAS, vol. 114, no. 13, pp. 3521-3526, 2017.
