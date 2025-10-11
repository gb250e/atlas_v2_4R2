from __future__ import annotations

from pathlib import Path

import pytest

import codex
from atlas.cli.run_pipeline import run_pipeline


@pytest.fixture()
def stage_log(tmp_path):
    thresholds = Path("thresholds/thresholds.json")
    data = Path("data/toy.jsonl")
    output = tmp_path / "results.jsonl"
    run_pipeline(thresholds, data, output)
    return output


@pytest.fixture(autouse=True)
def _reset_codex_state():
    codex.reset_dynamic_profiles()
    codex.clear_store()
    codex.reload()
    yield


def test_figures_figure_set():
    figure_set = codex.get("atlas.figures.figure_set")
    assert len(figure_set) == 10
    assert figure_set[0] == "F1_dashboard"


def test_validate_reports_missing_requirements(stage_log):
    result = codex.validate(
        "atlas.figures.inputs",
        {"log_jsonl": str(stage_log), "profile": "default"},
    )
    assert result["ok"] is False
    errors = "\n".join(result["errors"])
    assert "F2_tg_ind" in errors
    assert "F6_roc" in errors
    assert "F3_delta_map" in errors


def test_plan_raises_when_requirements_missing(stage_log):
    with pytest.raises(codex.AtlasFiguresError):
        codex.plan(
            "atlas.figures.build",
            {"log_jsonl": str(stage_log), "profile": "default"},
        )
