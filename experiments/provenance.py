"""Environment and code provenance, so a results file says exactly what produced it."""
from __future__ import annotations

import importlib.metadata as md
import platform
import subprocess
import sys

PACKAGES = ["numpy", "scipy", "pandas", "matplotlib", "scikit-learn", "pytest"]


def git_state() -> str:
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=5).stdout.strip()
        return f"{commit or 'unknown'}{' (uncommitted changes)' if dirty else ''}"
    except Exception:
        return "unknown (not a git checkout)"


def report() -> str:
    pk = []
    for p in PACKAGES:
        try:
            pk.append(f"{p}=={md.version(p)}")
        except md.PackageNotFoundError:
            pk.append(f"{p}==missing")
    return (f"python {platform.python_version()} on {platform.system()} {platform.release()}; "
            f"{', '.join(pk)}; git {git_state()}")
