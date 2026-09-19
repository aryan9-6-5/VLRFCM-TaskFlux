"""The seam between TaskFlux and a VLA policy.

TaskFlux never touches motor commands. It hands the policy one language
instruction per assembly step and asks a verifier whether the step is done.
Two things a stock OpenVLA does not give you, and which this layer has to
supply, are visible here:

* OpenVLA has no termination signal, so step completion needs a separate verifier;
* it sees one image and no history, so which step it is on has to live outside it.

``OpenVLAPolicy`` follows the usage in the OpenVLA repository README. It is NOT
exercised in this repo: the 7B model needs more memory than the development
machine's 4 GB GPU offers, so everything measured here runs against ``SimPolicy``.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Optional, Protocol

from .process import Step


def instruction_for(step: Step, undo: bool = False) -> str:
    """Language instruction handed to the policy for one step."""
    verb = "remove: " if undo else ""
    return f"{verb}{step.label}"


class StepPolicy(Protocol):
    def execute(self, instruction: str, observation: Any = None) -> bool: ...


class StepVerifier(Protocol):
    def confirmed(self, step_label: str, observation: Any = None) -> bool: ...


@dataclass
class SimPolicy:
    """Stand-in policy: succeeds with a fixed probability. Used by every experiment here."""
    p_success: float = 0.92
    seed: int = 0

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def execute(self, instruction: str, observation: Any = None) -> bool:
        return self._rng.random() < self.p_success


class OpenVLAPolicy:
    """Wrapper around the public OpenVLA checkpoint. Untested here, see module docstring.

    Prompt format and ``predict_action`` follow the OpenVLA README. ``unnorm_key`` selects the
    action de-normalisation statistics and must match the robot the model was tuned for.
    """

    def __init__(self, model_id: str = "openvla/openvla-7b", device: str = "cuda:0",
                 unnorm_key: str = "bridge_orig", load_in_4bit: bool = True) -> None:
        import torch
        from transformers import AutoModelForVision2Seq, AutoProcessor
        self._torch, self.device, self.unnorm_key = torch, device, unnorm_key
        self.processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
        kw = dict(torch_dtype=torch.bfloat16, low_cpu_mem_usage=True, trust_remote_code=True)
        if load_in_4bit:
            from transformers import BitsAndBytesConfig
            kw["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True)
        self.model = AutoModelForVision2Seq.from_pretrained(model_id, **kw)
        if not load_in_4bit:
            self.model.to(device)

    def act(self, image, instruction: str):
        prompt = f"In: What action should the robot take to {instruction}?\nOut:"
        inputs = self.processor(prompt, image).to(self.device, dtype=self._torch.bfloat16)
        return self.model.predict_action(**inputs, unnorm_key=self.unnorm_key, do_sample=False)

    def execute(self, instruction: str, observation: Any = None) -> bool:
        raise NotImplementedError("wire act() to the robot's control loop and a StepVerifier for your cell")
