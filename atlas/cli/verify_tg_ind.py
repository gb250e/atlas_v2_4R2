from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List

from atlas.cli.run_pipeline import load_thresholds, make_validators
from atlas.io.jsonl import read_jsonl, write_jsonl
from atlas.stages import tg_ind
from atlas.utils.logging import StageMeta, get_git_commit, sha256_of_file


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Quick TG-Independence verification.")
    parser.add_argument("thresholds", type=Path)
    parser.add_argument("input_jsonl", type=Path)
    parser.add_argument("output_jsonl", type=Path)
    parser.add_argument("--profile", default="default")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv or [])
    thresholds_hash = sha256_of_file(str(args.thresholds))
    thresholds = load_thresholds(args.thresholds, args.profile)
    validators = make_validators()
    commit = get_git_commit(args.thresholds.parent)
    meta = StageMeta(seed=args.seed, commit=commit, thresholds_sha256=thresholds_hash)

    if not args.input_jsonl.exists():
        raise FileNotFoundError(f"Input JSONL not found: {args.input_jsonl}")
    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    rows: List[dict] = []
    for state in read_jsonl(str(args.input_jsonl)):
        validators["state"].validate(state)
        result = tg_ind.evaluate(state, thresholds, meta)
        validators["stage"].validate(result)
        rows.append(result)
    write_jsonl(str(args.output_jsonl), rows)


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
