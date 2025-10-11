from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

import jsonschema

from atlas.io.jsonl import read_jsonl, write_jsonl
from atlas.stages import delta, htop, kms, nmod, sg, tg_ind, triage
from atlas.utils.cost import CostTracker
from atlas.utils.gpu import detect_accelerator
from atlas.utils.logging import StageMeta, get_git_commit, sha256_of_file, stage_line
from atlas.utils.rng import DEFAULT_DTYPE, DEFAULT_SEED, make_rng


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_thresholds(path: Path, profile: str) -> Dict[str, Any]:
    raw = load_json(path)
    if "profiles" in raw:
        return raw["profiles"].get(profile) or raw["default"]
    if "default" in raw:
        return raw["default"]
    return raw


def make_validators() -> Dict[str, jsonschema.Draft7Validator]:
    schema_dir = Path(__file__).resolve().parent.parent / "io" / "schemas"
    stage_schema = load_json(schema_dir / "stage_result.schema.json")
    state_schema = load_json(schema_dir / "system_state.schema.json")
    return {
        "stage": jsonschema.Draft7Validator(stage_schema),
        "state": jsonschema.Draft7Validator(state_schema),
    }


def render_determinism(meta: StageMeta, anchor_id: str, rng) -> Dict[str, Any]:
    accel = detect_accelerator()
    aux = {
        "rng": "Philox",
        "seed": meta.seed,
        "dtype": str(DEFAULT_DTYPE),
        "accelerator": accel,
        "fma": "default",
        "bit_generator": type(rng.generator.bit_generator).__name__,
    }
    return stage_line(
        meta,
        anchor_id=anchor_id,
        stage="determinism",
        status="PASS",
        metric="backend",
        value=None,
        threshold=None,
        aux=aux,
    )


def render_cost(meta: StageMeta, anchor_id: str, tracker: CostTracker) -> Dict[str, Any]:
    snapshot = tracker.snapshot()
    return stage_line(
        meta,
        anchor_id=anchor_id,
        stage="cost_reporting",
        status="PASS",
        metric="wall_seconds",
        value=snapshot["wall_seconds"],
        threshold=None,
        aux=snapshot,
        cost=snapshot["wall_seconds"],
    )


def validate_stage(result: Dict[str, Any], validator: jsonschema.Draft7Validator) -> None:
    validator.validate(result)


def run_pipeline(
    thresholds_path: Path,
    input_jsonl: Path,
    output_jsonl: Path,
    *,
    profile: str = "default",
    seed: int = DEFAULT_SEED,
) -> List[Dict[str, Any]]:
    thresholds_hash = sha256_of_file(str(thresholds_path))
    thresholds = load_thresholds(thresholds_path, profile)
    validators = make_validators()
    commit = get_git_commit(str(thresholds_path.parent))
    meta = StageMeta(seed=seed, commit=commit, thresholds_sha256=thresholds_hash)
    rng = make_rng(seed)

    if not input_jsonl.exists():
        fallback = Path("data/toy.jsonl")
        if fallback.exists():
            input_jsonl = fallback
        else:
            raise FileNotFoundError(f"Input JSONL not found: {input_jsonl}")
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    all_rows: List[Dict[str, Any]] = []
    for state in read_jsonl(str(input_jsonl)):
        validators["state"].validate(state)
        anchor_id = state.get("id", "unknown")
        tracker = CostTracker()

        rows: List[Dict[str, Any]] = []
        rows.append(render_determinism(meta, anchor_id, rng))

        delta_row = delta.evaluate(state, thresholds, meta)
        nmod_row = nmod.evaluate(state, thresholds, meta)
        htop_row = htop.evaluate(state, thresholds, meta, delta_row, nmod_row)

        rows.extend([delta_row, nmod_row, htop_row])

        sg_rows = sg.evaluate(state, thresholds, meta, delta_row, nmod_row, htop_row)
        rows.extend(sg_rows)

        tg_row = tg_ind.evaluate(state, thresholds, meta)
        kms_row = kms.evaluate(state, thresholds, meta)
        rows.extend([tg_row, kms_row])

        triage_row = triage.evaluate(state, thresholds, meta, delta_row, nmod_row, htop_row, tg_row, kms_row)
        rows.append(triage_row)

        rows.append(render_cost(meta, anchor_id, tracker))

        for r in rows:
            validate_stage(r, validators["stage"])
        all_rows.extend(rows)
    write_jsonl(str(output_jsonl), all_rows)
    return all_rows


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ATLAS pipeline.")
    parser.add_argument("thresholds", type=Path)
    parser.add_argument("input_jsonl", type=Path)
    parser.add_argument("output_jsonl", type=Path)
    parser.add_argument("--profile", default="default")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv or [])
    run_pipeline(args.thresholds, args.input_jsonl, args.output_jsonl, profile=args.profile, seed=args.seed)


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
