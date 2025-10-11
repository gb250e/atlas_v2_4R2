from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from atlas.io.jsonl import read_jsonl


def extract_triplets(rows: Iterable[Dict[str, object]]) -> List[Tuple[float, float, float, float]]:
    by_anchor: Dict[str, Dict[str, Dict[str, object]]] = {}
    for row in rows:
        anchor = row.get("anchor_id")
        by_anchor.setdefault(anchor, {})
        by_anchor[anchor][row.get("stage")] = row
    triplets: List[Tuple[float, float, float, float]] = []
    for anchor, stages in by_anchor.items():
        d = stages.get("delta")
        n = stages.get("nmod")
        h = stages.get("htop")
        if not (d and n and h):
            continue
        delta_val = d.get("aux", {}).get("delta_chart")
        abs_delta_n = n.get("aux", {}).get("abs_delta_N")
        h_obs = h.get("aux", {}).get("H_obs")
        h_lb = h.get("aux", {}).get("H_lb")
        if delta_val is None or abs_delta_n is None or h_obs is None or h_lb is None:
            continue
        gap = max(0.0, float(h_obs) - float(h_lb))
        triplets.append((float(delta_val), float(abs_delta_n), float(h_obs), gap))
    return triplets


def calibrate(rows: Iterable[Dict[str, object]]) -> Dict[str, float]:
    triplets = extract_triplets(rows)
    if not triplets:
        return {"c_delta": 0.0, "c_n": 0.0, "samples": 0}
    ratios_delta = [gap / (delta if delta else 1e-9) for delta, _, _, gap in triplets if delta > 0]
    ratios_n = [gap / (abs_n if abs_n else 1e-9) for _, abs_n, _, gap in triplets if abs_n > 0]
    c_delta = max(ratios_delta) if ratios_delta else 0.0
    c_n = max(ratios_n) if ratios_n else 0.0
    return {"c_delta": c_delta, "c_n": c_n, "samples": len(triplets)}


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calibrate error budget coefficients from StageResults.")
    parser.add_argument("results_jsonl", type=Path)
    parser.add_argument("out_json", type=Path)
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv or [])
    if not args.results_jsonl.exists():
        raise FileNotFoundError(f"results_jsonl not found: {args.results_jsonl}")
    rows = list(read_jsonl(str(args.results_jsonl)))
    metrics = calibrate(rows)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    with args.out_json.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    import sys

    main(sys.argv[1:])
