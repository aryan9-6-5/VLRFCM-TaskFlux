# Source audit

Notes on the five PDFs in `papers/`, plus a warning about one of them.

## What each paper actually contains

### papers/five.pdf, OpenVLA (Kim et al., CoRL 2024)
The backbone we build on. 7B parameters, Prismatic-7B VLM (Llama 2 7B plus a fused
SigLIP + DINOv2 visual encoder), trained on 970k episodes from Open X-Embodiment.
Actions are discretised into 256 bins per dimension and written over the 256 least
used tokens in the Llama vocabulary, so action prediction is just next token
prediction.

Numbers worth quoting, all verified from the PDF:
- 70.6% +/- 3.2% mean success across 29 tasks
- 16.5 absolute points over RT-2-X, which has 55B parameters
- LoRA at rank 32 reaches 68.2% +/- 7.5% against 69.7% +/- 7.2% for full fine-tuning,
  while training 1.4% of the weights (97.6M parameters, 59.7 GB VRAM at batch 16
  versus 163.3 GB sharded across two GPUs for full fine-tuning)
- One new task in 10 to 15 hours on a single A100, roughly 8x cheaper than full
  fine-tuning
- Rank had almost no effect, so r = 32 is the authors' own default

Stated limitations: single image observation only, no proprioception, no observation
history, and throughput too low for high frequency control such as ALOHA at 50 Hz.
The authors also note Diffusion Policy still produces smoother trajectories on narrow
dexterous tasks and suggest action chunking as future work.

### papers/four.pdf, Fan, Yin, Wang, Dong, Zheng, Wang (Frontiers of Engineering Management, 2024)
The systematic survey. 109 papers, searched across Web of Science, Scopus and IEEE
Xplore for "human-robot" plus "vision language", 2020 to 2024.

This paper is the single strongest citation for our gap. Section 6.6 is titled
"Dynamic task adaptation and unsupervised evaluation" and says current methods
"always rely on an assumption of an ideal training environment", that real deployment
"necessitates human operators for continuous monitoring and intervention", and that
robots "must evolve to autonomously adapt to dynamic environments and tasks". It then
calls for "a continuous learning mechanism" that lets robots "adapt and improve their
performance autonomously over time".

Section 6.2 adds that VLM task planning is stuck on static scenes and that real-time
planning in dynamic scenes "remains an unresolved issue".

In other words, the most cited survey in this space asks for exactly the thing we are
proposing to build. Quote it in the introduction and again in the gap section.

### papers/first.pdf, QUAR-VLA / QUART (Ding et al., ECCV 2024)
VLA for quadrupeds. QUARD dataset, 259K simulated plus 3K real episodes. QUART beats
CLIP, R3M and VC-1 across every difficulty tier; the baselines score exactly 0.0 on
the crawl and unload tasks while QUART gets 0.32 and 0.12. Useful to us as evidence
that a VLA backbone transfers across embodiments, and as a contrast case: the task set
is fixed and enumerated in advance.

### papers/two.pdf, OWG (Tziafas and Kasaei, CoRL 2024)
Open world grasping. GPT-4V plus Mask-RCNN plus GR-ConvNet, three stages: referring
segmentation, grounded grasp planning, grasp ranking by contact reasoning. Two UR5e
arms with Robotiq 2F-140 grippers, 50 Gazebo trials per scenario over 30 object models.

Simulation success, seen / unseen: isolated 78.0 / 82.0, cluttered 62.0 / 66.0.
Real robot: isolated 83.3 / 66.6, cluttered 50.0 / 50.0. Beats CROG and SayCan-IM in
every cell.

Their limitations section is directly relevant to our design. Being modular, OWG
"suffers from error cascading effects introduced by the segmentor and grasp synthesis
models". That is the argument for keeping a monolithic VLA in the execution path and
putting the language reasoning above it rather than in series with it.

### papers/three.pdf, Byrne (Journal of Computer Science and Software Applications, 2025)
Read the warning below before citing this one.

## Warning about papers/three.pdf

The title is "Vision-Language Models for Human-Robot Collaboration: Real-Time Task
Understanding and Execution". The abstract underneath it is about predicting stock
prices on the CSI 300 index with a CNN-LSTM hybrid. The keywords list is also the
stock prediction one. The body then talks about robots.

That is an unedited copy-paste from a different manuscript, sitting in the published
version of record. A journal that ships that has no meaningful peer review, and the
reported results (91% success rate, 95% grounding accuracy, 1.4 s latency, all round
numbers, no variance, no confidence intervals, 20 trials per condition) should not be
treated as evidence.

Recommendation: drop it from the reference list. If a reviewer asks why the count went
from six to five, that is an easy answer and a good one. Replace it with Fan and Zheng
(2024) in the Journal of Manufacturing Systems, which is the paper the project actually
positions itself against anyway.
