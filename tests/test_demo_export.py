"""The demo page is built from the real code; check the embedded data is sane."""
import json
import re

from demo.build_demo import main


def test_demo_builds_and_embeds_consistent_data(tmp_path):
    out = main(runs=3, out=tmp_path / "index.html")
    html = out.read_text(encoding="utf-8")
    assert "__DATA__" not in html and "TaskFlux" in html
    data = json.loads(re.search(r"const D = (\{.*?\});\nconst NS", html, re.S).group(1))
    assert len(data["states"]) == 12 and len(data["responses"]) == 12 and len(data["compare"]) == 12
    assert len(data["steps"]) == 16 and len(data["responses"][0]) == len(data["utterances"])
    assert data["states"][6]["plan"]["undo"] == ["cover"]                 # cover has to come off, then go back
    assert data["states"][10]["plan"]["scrap"] and data["states"][10]["stage"] == "irreversible"
    for r in data["responses"][6]:
        assert abs(sum(r["probs"]) - 1.0) < 0.01 and r["say"]
    assert data["responses"][6][5]["action"] == "halt"                    # "not safe, stop" always halts
