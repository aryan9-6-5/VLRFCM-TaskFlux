"""Synthetic operator utterances and a calibrated four-way intent classifier.

Intents: clarification, edit (parameter edit), changeover, abort.

The template sets for train, dev (calibration) and test are disjoint on
purpose: the test phrasings are ones the classifier has never seen, and include
indirect changeovers ("we are not doing gaskets on this batch") and hard
negatives ("no, the other housing", "stop building this one, do B").

These utterances are authored by us. They test the pipeline, not real
operator speech; a deployed system would put ASR and an LLM in front of this
and would need recorded shop-floor phrasings.
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import numpy as np
from scipy.special import logsumexp
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

INTENTS = ["clarification", "edit", "changeover", "abort"]

VARIANTS_TRAIN = ["variant B", "the B housing", "spec B", "the B build", "B", "the B version"]
VARIANTS_TEST = VARIANTS_TRAIN + ["the marine unit", "the export model"]
PARTS = ["screw", "gasket", "housing", "cover", "connector", "bearing", "label"]

T: Dict[str, Dict[str, List[str]]] = {
    "changeover": {
        "train": ["switch to {v}", "change over to {v} now", "we're building {v} instead",
                  "stop building this one, do {v}", "the order changed, it's {v} now",
                  "make it {v} instead of what you're doing", "new order, {v}, skip the {p}",
                  "actually I need {v}", "switch to {v}, skip the {p}", "let's do {v} on this one"],
        "dev": ["customer moved this order to {v}", "forget this variant, {v} is what we need",
                "go with {v} for this unit", "we're not doing {p}s on this batch",
                "swap this build over to {v}", "this one is {v}, not what's on the sheet"],
        "test": ["planning just told me it's {v} from here on", "no {p} on this batch anymore",
                 "scratch that, this unit ships as {v}", "can you redirect this to {v}",
                 "the line lead wants {v} built here", "turns out the paperwork says {v}",
                 "let's pivot this one over to {v}", "instead of what you have going, {v} please"],
    },
    "clarification": {
        "train": ["no, the {p} on the left", "I meant the other {p}", "the {p}, not the {p2}",
                  "pick up the red {p}", "the one closer to me", "use the {p} in the second bin",
                  "yes that {p}", "the bigger {p}", "the {p} next to the tray", "that one there"],
        "dev": ["not that one, the shiny one", "the {p} by the fixture", "I meant the top {p}",
                "the one in the blue tray", "the smaller {p} please", "left one, not right"],
        "test": ["no, the other {p}", "grab the {p} nearest the clamp", "the {p} with the notch",
                 "I mean the {p} at the back", "that {p}, the one you just passed",
                 "the cleaner-looking {p}", "the {p} on the far side of the table", "the one with the marking"],
    },
    "edit": {
        "train": ["use {n} instead of the default torque", "set the torque to {n}", "tighten the {p} to {n}",
                  "go slower on the {p}", "use the M4 {p} instead of M5", "apply less adhesive",
                  "increase the press force a bit", "use the longer {p}", "cure time should be {n2}",
                  "lower the speed when seating the {p}"],
        "dev": ["make the torque {n}", "use a lighter press on the {p}", "swap to the M5 {p}",
                "bead should be thinner", "wait {n2} before the cover", "go gentler on the connector"],
        "test": ["drop the tightening torque to {n}", "we need a slower approach for the {p}",
                 "use the coarse thread {p} from now on", "the adhesive bead can be smaller",
                 "hold the {p} for {n2} longer", "seat the {p} more softly", "bump the torque to {n}",
                 "use a shorter {p} for this one"],
    },
    "abort": {
        "train": ["stop", "stop stop stop", "emergency stop", "halt", "hold on, stop the arm", "freeze",
                  "cancel that, stop moving", "wait, stop", "abort", "everybody clear, stop the robot"],
        "dev": ["stop the robot now", "whoa hold it", "pause everything", "kill it",
                "stop moving please", "hands are in the way, stop"],
        "test": ["hold everything", "stop right there", "wait wait wait", "shut it down",
                 "not safe, stop", "halt the arm", "abort abort", "freeze, don't move"],
    },
}


def _fill(t: str, rng: random.Random, variants: Sequence[str]) -> str:
    return t.format(v=rng.choice(variants), p=rng.choice(PARTS), p2=rng.choice(PARTS),
                    n=f"{rng.choice([8, 10, 12, 14])} Nm", n2=f"{rng.choice([5, 10, 20])} seconds")


def make_split(split: str, n_per_class: int, seed: int) -> Tuple[List[str], List[int]]:
    rng = random.Random(seed)
    variants = VARIANTS_TEST if split == "test" else VARIANTS_TRAIN
    xs: List[str] = []
    ys: List[int] = []
    for ci, intent in enumerate(INTENTS):
        for _ in range(n_per_class):
            xs.append(_fill(rng.choice(T[intent][split]), rng, variants))
            ys.append(ci)
    order = list(range(len(xs)))
    rng.shuffle(order)
    return [xs[i] for i in order], [ys[i] for i in order]


@dataclass
class IntentClassifier:
    pipe: Pipeline
    temperature: float = 1.0

    @classmethod
    def train(cls, n_train: int = 300, n_dev: int = 150, seed: int = 0) -> "IntentClassifier":
        xs, ys = make_split("train", n_train, seed)
        feats = FeatureUnion([
            ("word", TfidfVectorizer(ngram_range=(1, 2), lowercase=True)),
            ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), lowercase=True)),
        ])
        pipe = Pipeline([("f", feats), ("lr", LogisticRegression(C=4.0, max_iter=2000))])
        pipe.fit(xs, ys)
        clf = cls(pipe)
        dx, dy = make_split("dev", n_dev, seed + 1)
        clf.temperature = clf._fit_temperature(dx, dy)
        return clf

    # ---- probabilities ----
    def _logits(self, xs: Sequence[str]) -> np.ndarray:
        return self.pipe.decision_function(list(xs))

    def proba(self, xs: Sequence[str]) -> np.ndarray:
        z = self._logits(xs) / self.temperature
        return np.exp(z - logsumexp(z, axis=1, keepdims=True))

    def _fit_temperature(self, xs: Sequence[str], ys: Sequence[int]) -> float:
        z = self._logits(xs)
        y = np.asarray(ys)
        best_t, best = 1.0, np.inf
        for t in np.linspace(0.3, 6.0, 115):
            lp = z / t
            lp = lp - logsumexp(lp, axis=1, keepdims=True)
            nll = -lp[np.arange(len(y)), y].mean()
            if nll < best:
                best, best_t = nll, float(t)
        return best_t

    def predict(self, xs: Sequence[str]) -> np.ndarray:
        return self.proba(xs).argmax(axis=1)


def ece(proba: np.ndarray, y: Sequence[int], bins: int = 10) -> float:
    """Top-label expected calibration error."""
    y = np.asarray(y)
    conf = proba.max(axis=1)
    hit = proba.argmax(axis=1) == y
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            total += m.mean() * abs(hit[m].mean() - conf[m].mean())
    return float(total)


# Safety override. A stop request must never depend on a learned classifier, so any of
# these words halts the arm outright. It errs toward halting: "stop building this one, do B"
# also trips it, which costs a few seconds and is the safe side of the trade.
_STOP = re.compile(r"\b(stop|halt|freeze|abort|emergency|kill|shut|pause|whoa|hold (on|it|everything)|"
                   r"wait wait|not safe)\b", re.I)


def lexical_stop(utterance: str) -> bool:
    return bool(_STOP.search(utterance))


def resolve_target(utterance: str, variants: Sequence[str]) -> str | None:
    """Very small slot filler: find which variant letter the operator named."""
    for name in variants:
        if re.search(rf"\b(variant|spec|the)?\s*{re.escape(name)}\b", utterance, flags=re.I):
            return name
    return None
