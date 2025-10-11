from __future__ import annotations

from pathlib import Path

from atlas.cli.run_pipeline import run_pipeline


def test_pipeline_smoke(tmp_path):
    thresholds = Path("thresholds/thresholds.json")
    data = Path("data/toy.jsonl")
    output = tmp_path / "results.jsonl"

    rows = run_pipeline(thresholds, data, output)
    assert output.exists()
    assert len(rows) > 0

    anchors = {row["anchor_id"] for row in rows if "anchor_id" in row}
    triage_rows = [row for row in rows if row.get("stage") == "triage"]

    assert triage_rows, "Triage stage results should be present"
    assert len(rows) >= 6 * max(1, len(anchors))

    for row in triage_rows:
        confidence = row["aux"].get("confidence")
        assert 0.0 <= confidence <= 1.0
