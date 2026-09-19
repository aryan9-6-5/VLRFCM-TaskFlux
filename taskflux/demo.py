"""Scripted end-to-end demo on the gearbox example.

    python -m taskflux.demo
"""
from __future__ import annotations

from .controller import Controller
from .examples import GEARBOX_CELL, gearbox
from .utterances import IntentClassifier


def scene(title: str, k: int, say: str, answer: bool | None, clf: IntentClassifier) -> None:
    p = gearbox()
    done = set(p.topo_order(p.goal("A"))[:k])
    c = Controller(p, "A", "B", clf, GEARBOX_CELL, done=done)
    print(f"\n=== {title}")
    print(f"    workpiece: {k} step(s) done: {', '.join(p.label(s) for s in p.topo_order(done)) or 'nothing'}")
    print(f"    operator : \"{say}\"")
    r = c.hear(say)
    print(f"    triage   : {r.action.value}   P(clar, edit, change, abort) = {r.probs.round(2).tolist()}")
    print(f"    robot    : {r.say}")
    if r.action.value == "ask" and answer is not None:
        print(f"    operator : {'yes' if answer else 'no'}")
        r = c.answer(answer)
        print(f"    robot    : {r.say}")
    if c.queue:
        print("    next     : " + " -> ".join(f"{kind} {p.label(s)}" for kind, s in c.queue[:6]) + (" ..." if len(c.queue) > 6 else ""))


if __name__ == "__main__":
    clf = IntentClassifier.train()
    scene("Early changeover, nothing conflicts", 3, "switch to the B housing", None, clf)
    scene("Cover already on: it has to come off and go back", 6, "switch to the B housing, skip the foam gasket", None, clf)
    scene("Housing and screws fitted: undo cascade", 9, "we're building variant B instead", None, clf)
    scene("Adhesive has cured: refusal with a reason", 10, "the order changed, it's the B housing now", True, clf)
    scene("Indirect phrasing near the end of the build", 8, "turns out the paperwork says the B housing", True, clf)
    scene("A clarification is not a changeover", 8, "no, the other screw", None, clf)
    scene("A stop is never weighed against cost", 8, "not safe, stop", None, clf)
