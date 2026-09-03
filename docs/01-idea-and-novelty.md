# TaskFlux: the idea, and what is actually new about it

## The problem in one paragraph

A cobot on a high-mix line is halfway through assembling variant A. The operator walks up and says "switch to the B housing, skip the foam gasket". Every VLA model published so far will treat that sentence as an instruction to execute right now. None of them will ask the question that matters: has the goal changed, and if so, what do I do about the three parts I have already placed?

That is the gap. It is not a perception gap and it is not a grounding gap. It is a gap in how the system models its own objective over time.

## What the field currently assumes

Read across the five papers in `papers/` and the assumption is consistent.

OpenVLA maps (image, instruction) to an action. The instruction is a constant for the length of the episode. RT-2 is the same. QUART enumerates its task set in advance and evaluates on seen and unseen instances of those tasks, never on a task that mutates mid-episode. OWG plans a grasp for a target named in a single utterance.

Fan and Zheng (2024) get closest. They handle the case where the operator says "hand me that one" and the system cannot tell which object "that one" refers to. But the ambiguity they resolve is referential: which object satisfies a goal that everyone already agrees on. The goal itself never moves.

The replanning literature has a similar blind spot from the other direction. Inner Monologue, DoReMi and REFLECT all replan, but they replan on failure. The trigger is "the world did not turn out how I predicted". The goal is still the goal. Nobody replans because the goal was withdrawn and replaced.

So there are two established problems, and a third one sitting between them that has no name:

| Problem | Trigger | Goal state |
|---|---|---|
| Ambiguity mitigation (Fan and Zheng) | referent is unclear | fixed |
| Failure recovery (Inner Monologue, DoReMi) | execution diverged from prediction | fixed |
| Task changeover (this project) | operator changed the requirement | replaced mid-episode |

## The five things that make this project defensible

Most of these are not "we added an LLM to a VLA". That framing is weak and a reviewer will say so. Here is the stronger version.

### 1. Changeover intent classification as a first-class step

Before anything else happens, the system has to decide what kind of utterance it just heard. Four categories, and they demand completely different responses:

- a clarification, which resolves a referent inside the current plan and changes nothing structurally
- a parameter edit, which keeps the plan skeleton but swaps a value, for example a torque spec or a part number
- a changeover, which replaces the goal state and invalidates part of the plan
- an abort or safety stop

Existing systems collapse all four into "an instruction". Separating them is cheap, and getting it wrong is expensive in opposite directions. Misclassifying a clarification as a changeover means the robot throws away good work. Misclassifying a changeover as a clarification means it finishes building the wrong product. That asymmetry is worth a section in the paper on its own.

### 2. Partial-assembly state reconciliation

This is the hardest part and the part nobody has published on.

When the goal changes at step k of an n-step plan, the workspace is not in a clean initial state. Three screws are torqued, a connector is seated, a gasket is in place. Naive replanning from the current camera frame produces a plan for a fresh workbench, which is wrong, and executing it will either collide with existing parts or produce a mongrel assembly.

The reconciliation step compares the completed prefix against the new goal and partitions it three ways:

- keep: steps whose result is still required by the new goal
- undo: steps whose result actively conflicts and must be reversed
- discard: steps that are now irrelevant but harmless to leave in place

Then it emits a plan of the form: undo sequence in reverse dependency order, followed by the remaining steps of the new plan with the kept prefix removed.

Undo is not free and not always possible. Adhesive cures. Rivets do not come out. So the reconciler also needs a notion of irreversible steps, and when an undo crosses one it has to escalate to the operator rather than attempt it.

This single component is the clearest novel contribution in the project. It is concrete, it is implementable, it has an obvious failure mode to measure, and no paper in the folder or in the wider VLA literature addresses it.

### 3. A refusal path

An adaptation layer that always says yes is a liability on a factory floor. Before the new plan is committed, it gets checked for reachability, for collisions against the current occupancy of the workspace, for tool availability, and for whether the requested change violates a process constraint such as a cure time or a torque sequence.

The output when a check fails is not an error code. It is a sentence explaining what specifically blocked it, so the operator can amend the request. "I can switch to the B housing, but the gasket is already seated with adhesive and I cannot remove it without damaging the part" is a useful thing for a robot to say, and no VLA can say it today.

### 4. Known versus novel routing, with gated merge-back

If the requested variant is already in the skill library, route to the base OpenVLA policy and execute. If it is not, spin up a LoRA adapter, run the task under closer validation, and log the outcome.

The interesting part is not the adapter. LoRA on OpenVLA is established: the paper itself reports rank 32 matching full fine-tuning at 1.4% of the parameters. The interesting part is the merge-back gate. An adapter only gets folded into the base weights after it clears a threshold on the validation module and after a retention check confirms performance on previously mastered variants has not regressed.

That retention check is what keeps this from being a slow-motion catastrophic forgetting machine, and it is the piece that answers Fan et al.'s call for a "continuous learning mechanism" with something more specific than "we fine-tune sometimes".

### 5. An evaluation protocol that does not exist yet

There is no benchmark for mid-episode task change, so a large part of the contribution is defining how you would even measure it. See `04-evaluation-protocol.md` for the full set. The short version is five metrics:

- Changeover Success Rate: did the finished assembly match the new specification
- Adaptation Latency: seconds from end of utterance to first correct action under the new plan
- Rework Cost: undo actions divided by steps already completed
- False Changeover Rate: how often a clarification was misread as a changeover
- Retention Score: success on variant A after the system has learned variant B

Retention is the one people forget, and it is the one that separates a system that adapts from a system that just overfits to whatever it was told most recently.

## The pitch, compressed

Every VLA published so far answers "what should I do next given this instruction". TaskFlux answers a different question: the instruction just changed, and I am halfway through the old one, so what now.

It handles that by classifying the type of change, reconciling the half-built workspace against the new goal, refusing the request when physics or process constraints say no, routing novel variants to a lightweight adapter, and merging that adapter back only when it passes both a quality gate and a retention gate.

## Honest limitations to state up front

Say these in the paper before a reviewer says them for you.

The reconciler depends on knowing which assembly steps are reversible. In this project that comes from a hand-authored process description, not from learning. That is a real restriction and it caps generality.

Undo actions are harder than the forward actions. Removing a seated connector is a contact-rich manipulation that OpenVLA is not especially good at, and the OpenVLA paper concedes Diffusion Policy is smoother on exactly that class of task.

Latency is a problem. OpenVLA runs in the single-digit hertz range, and an LLM replanning call on top of that adds seconds. The system is plausible for a changeover that happens a few times per shift. It is not plausible for anything reactive.

Evaluation will be small-n. A student project with one arm cannot produce the trial counts that OWG (50 per scenario) or OpenVLA (500 per suite) report. State the sample size honestly and report per-condition results rather than one aggregate number.
