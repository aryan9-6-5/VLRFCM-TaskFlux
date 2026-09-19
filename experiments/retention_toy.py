"""Toy check that the retention gate catches forgetting a merge would cause.

A small MLP policy stands in for OpenVLA: it maps a 24-d observation to one of 8 discrete
actions. Variant A and variant B use overlapping observations with partly conflicting
action rules, so teaching B can overwrite A. LoRA (rank 4 here) is trained on B and then
merged into the base weights. This says nothing about OpenVLA; it only exercises the gate.

    python -m experiments.retention_toy
"""
from __future__ import annotations

import copy

import numpy as np
import torch
import torch.nn as nn

from taskflux.adapters import GateConfig, Registry, Adapter, episodes_needed, quality_gate, retention_gate

torch.manual_seed(0)
np.random.seed(0)
D, H, K = 24, 64, 8


def make_task(seed: int, conflict: float, base_W=None):
    g = np.random.RandomState(seed)
    W = g.randn(K, D) if base_W is None else base_W + conflict * g.randn(K, D)
    return W


def sample(W, n, seed):
    g = np.random.RandomState(seed)
    x = g.randn(n, D).astype(np.float32)
    y = (x @ W.T).argmax(1)
    return torch.tensor(x), torch.tensor(y)


class LoRALinear(nn.Module):
    def __init__(self, lin: nn.Linear, r: int):
        super().__init__()
        self.lin, self.r = lin, r
        self.A = nn.Parameter(torch.randn(r, lin.in_features) * 0.01)
        self.B = nn.Parameter(torch.zeros(lin.out_features, r))
        self.on = True

    def forward(self, x):
        y = self.lin(x)
        return y + (x @ self.A.T @ self.B.T if self.on else 0)

    def merge(self):
        with torch.no_grad():
            self.lin.weight += self.B @ self.A
        self.on = False


def acc(model, x, y):
    with torch.no_grad():
        return int((model(x).argmax(1) == y).sum()), len(y)


def run(conflict: float, n_eval: int = 300):
    WA = make_task(1, 0.0)
    WB = make_task(2, conflict, WA)
    xa, ya = sample(WA, 4000, 10)
    base = nn.Sequential(nn.Linear(D, H), nn.ReLU(), nn.Linear(H, K))
    opt = torch.optim.Adam(base.parameters(), 3e-3)
    for _ in range(600):
        opt.zero_grad(); nn.functional.cross_entropy(base(xa), ya).backward(); opt.step()
    for p in base.parameters():
        p.requires_grad_(False)
    model = copy.deepcopy(base)
    model[0] = LoRALinear(model[0], 4)
    model[2] = LoRALinear(model[2], 4)
    xb, yb = sample(WB, 4000, 11)
    opt = torch.optim.Adam([p for m in (model[0], model[2]) for p in (m.A, m.B)], 3e-3)
    for _ in range(600):
        opt.zero_grad(); nn.functional.cross_entropy(model(xb), yb).backward(); opt.step()
    ea, eb = sample(WA, n_eval, 20), sample(WB, n_eval, 21)
    before_A = acc(base, *ea)
    adapter_on_B = acc(model, *eb)
    adapter_on_A = acc(model, *ea)                # adapter left switched on, applied to A: what a careless merge does
    merged = copy.deepcopy(model)
    merged[0].merge(); merged[2].merge()
    reg = Registry(base_variants={"A"}, adapters={"B": Adapter("B", rank=4)})
    ok = reg.consider_merge("B", adapter_on_B, {"A": before_A}, lambda v: acc(merged, *ea))
    return dict(conflict=conflict, A_before=before_A, B_with_adapter=adapter_on_B, A_after_merge=acc(merged, *ea),
                merged=ok, route_B=reg.route("B"), log=reg.log)


if __name__ == "__main__":
    for c in [0.0, 0.3, 1.0]:
        r = run(c)
        f = lambda t: f"{t[0]}/{t[1]} ({100 * t[0] / t[1]:.0f}%)"
        print(f"\nconflict {c}: A before {f(r['A_before'])}, B with adapter {f(r['B_with_adapter'])}, "
              f"A after merge {f(r['A_after_merge'])} -> merged={r['merged']}, B now routed via '{r['route_B']}'")
        for line in r["log"]:
            print("   ", line)
    print("\nepisodes needed for a retained variant at 90% success to pass the gate:", episodes_needed(0.90))
    print("at 80%:", episodes_needed(0.80), " at 95%:", episodes_needed(0.95))
