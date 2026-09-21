"""One command: tests, then every experiment, then an environment record.

    python -m experiments.reproduce
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from . import provenance

OUT = Path(__file__).parent / "results"


def main() -> int:
    OUT.mkdir(exist_ok=True)
    (OUT / "environment.txt").write_text(provenance.report() + "\n", encoding="utf-8")
    print("environment:", provenance.report())
    for cmd in ([sys.executable, "-m", "pytest", "tests", "-q"], [sys.executable, "-m", "experiments.run_experiments"]):
        print("\n$", " ".join(cmd))
        rc = subprocess.call(cmd)
        if rc != 0:
            print("failed:", " ".join(cmd))
            return rc
    print(f"\nall done; see {OUT / 'results.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
