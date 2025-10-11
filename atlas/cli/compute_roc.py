from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Sequence

from atlas.io.jsonl import read_jsonl
from atlas.utils.stats import roc_curve


def compute_roc(results_path: Path, positives: Sequence[str]) -> dict:
    rows = [row for row in read_jsonl(str(results_path)) if row.get("stage") == "triage"]
    return roc_curve(rows, positives)


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute ROC metrics from StageResult logs.")
    parser.add_argument("results_jsonl", type=Path)
    parser.add_argument("out_json", type=Path)
    parser.add_argument("--positives", nargs="*", default=["true_tear"])
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv or [])
    if not args.results_jsonl.exists():
        raise FileNotFoundError(f"results_jsonl not found: {args.results_jsonl}")
    metrics = compute_roc(args.results_jsonl, args.positives)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    with args.out_json.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
