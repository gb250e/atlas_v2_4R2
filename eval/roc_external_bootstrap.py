#!/usr/bin/env python3
"""
ATLAS v2.4R2 — External ROC with bootstrap CI (JSON Lines logger)

- Reads labels(id,label) and scores(id,score) CSV (headers optional).
- Computes AUC (mid-rank / Mann–Whitney), Youden's J (best_J, threshold),
  and 95% bootstrap CI (percentile).
- Appends a single JSONL record:
  {
    "stage":"roc", "metric":"external", "value": <auc>, "threshold": <min_auc>,
    "status":"PASS"|"FAIL", "aux":{"best_J":..., "threshold_at_best_J":..., "ci95":[lo,hi], "B":...},
    "notes":"bootstrap-ci(robust)", "timestamp": "...", "ts":"...",
    "commit":"...", "seed":..., "thresholds_sha256":"...", "anchor_id":"..."
  }
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


Label = Tuple[str, int]
Pairs = List[Tuple[float, int]]


def read_labels(path: Path) -> List[Label]:
    """Read labels as (id, int(label)), skipping headers like 'label'."""
    out: List[Label] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 2:
                continue
            id0 = row[0].strip()
            y_raw = row[1].strip()
            # skip potential header tokens
            if y_raw.lower() in {"label", "y", "target"}:
                continue
            try:
                y = int(y_raw)
            except ValueError:
                # skip invalid rows
                continue
            out.append((id0, y))
    return out


def read_scores(path: Path) -> Dict[str, float]:
    """Read scores as dict[id] = float(score), skipping headers like 'score'."""
    out: Dict[str, float] = {}
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 2:
                continue
            id0 = row[0].strip()
            s_raw = row[1].strip()
            if s_raw.lower() in {"score", "pred", "p"}:
                continue
            try:
                s = float(s_raw)
            except ValueError:
                continue
            out[id0] = s
    return out


def make_pairs(labs: Sequence[Label], scrs: Dict[str, float]) -> Pairs:
    """Join labels and scores on id keeping label order."""
    return [(scrs[_id], y) for _id, y in labs if _id in scrs]


def auc_midrank(pairs: Pairs) -> float:
    """AUC via mid-rank (Mann–Whitney U equivalence), stable for ties."""
    if not pairs:
        return 0.5
    p_count = sum(1 for _, y in pairs if y == 1)
    n_count = len(pairs) - p_count
    if p_count == 0 or n_count == 0:
        return 0.5
    # ranks by ascending score, ties -> midrank
    idx = sorted(range(len(pairs)), key=lambda i: pairs[i][0])
    ranks = [0.0] * len(pairs)
    i = 0
    while i < len(pairs):
        j = i + 1
        while j < len(pairs) and pairs[idx[j]][0] == pairs[idx[i]][0]:
            j += 1
        avg = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[idx[k]] = avg
        i = j
    sum_pos = sum(r for r, (_s, y) in zip(ranks, pairs) if y == 1)
    auc = (sum_pos - p_count * (p_count + 1) / 2.0) / (p_count * n_count)
    return float(auc)


def youden_best_j(pairs: Pairs) -> Tuple[float, float | None]:
    """Return (best_J, best_threshold) scanning unique scores."""
    if not pairs:
        return -1.0, None
    scores = sorted({s for s, _ in pairs}, reverse=True)
    p_count = sum(1 for _, y in pairs if y == 1)
    n_count = len(pairs) - p_count
    best_j = -1.0
    best_th: float | None = None
    for t in scores:
        tp = sum(1 for s, y in pairs if s >= t and y == 1)
        tn = sum(1 for s, y in pairs if s < t and y == 0)
        sens = tp / max(p_count, 1)
        spec = tn / max(n_count, 1)
        j = sens + spec - 1.0
        if j > best_j:
            best_j = j
            best_th = t
    return best_j, best_th


def bootstrap_auc_ci(
    pairs: Pairs, bootstraps: int, seed: int, max_tries_factor: int = 20
) -> Tuple[float, float, int]:
    """Percentile 95% CI for AUC via bootstrap; skips degenerate resamples.

    Returns (lo, hi, effective_B).
    """
    rng = random.Random(seed)
    n = len(pairs)
    if n == 0 or bootstraps <= 0:
        return 0.0, 1.0, 0
    aucs: List[float] = []
    tries = 0
    need = bootstraps
    while len(aucs) < need and tries < max_tries_factor * need:
        tries += 1
        samp = [pairs[rng.randrange(n)] for _ in range(n)]
        p = sum(1 for _, y in samp if y == 1)
        q = n - p
        if p == 0 or q == 0:
            continue
        aucs.append(auc_midrank(samp))
    aucs.sort()
    if not aucs:
        return 0.0, 1.0, 0
    lo = aucs[int(0.025 * len(aucs))]
    hi = aucs[int(0.975 * len(aucs)) - 1]
    return float(lo), float(hi), len(aucs)


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def build_record(
    auc: float,
    min_auc: float,
    best_j: float,
    best_th: float | None,
    ci_lo: float,
    ci_hi: float,
    eff_b: int,
    commit: str,
    seed: int,
    thr_sha256: str,
    anchor_id: str,
    notes: str = "bootstrap-ci(robust)",
) -> dict:
    status = "PASS" if auc >= min_auc else "FAIL"
    rec = {
        "stage": "roc",
        "metric": "external",
        "value": auc,
        "threshold": min_auc,
        "status": status,
        "aux": {
            "best_J": best_j,
            "threshold_at_best_J": best_th,
            "ci95": [ci_lo, ci_hi],
            "B": eff_b,
        },
        "notes": notes,
        # Keep both keys for compatibility with existing logs & schema.
        "timestamp": now_iso(),
        "ts": now_iso(),
        "commit": commit,
        "seed": seed,
        "thresholds_sha256": thr_sha256,
        "anchor_id": anchor_id,
    }
    return rec


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Compute external ROC (AUC, best-J, 95% CI) and append JSONL."
    )
    p.add_argument("--labels", required=True, help="CSV: id,label")
    p.add_argument("--scores", required=True, help="CSV: id,score")
    p.add_argument("--out", required=True, help="Output JSONL to append")
    p.add_argument(
        "--min-auc",
        type=float,
        default=0.75,
        help="PASS threshold for AUC (default 0.75)",
    )
    p.add_argument(
        "--bootstraps",
        type=int,
        default=5000,
        help="Number of bootstrap resamples (default 5000)",
    )
    p.add_argument(
        "--thresholds-sha256",
        default="UNKNOWN",
        help="Thresholds file SHA-256 (for traceability)",
    )
    p.add_argument("--commit", default="UNKNOWN", help="Git commit id")
    p.add_argument("--anchor-id", default="UNKNOWN", help="External set id/DOI alias")
    p.add_argument("--seed", type=int, default=42, help="Random seed")
    return p.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    labels = read_labels(Path(args.labels))
    scores = read_scores(Path(args.scores))
    pairs = make_pairs(labels, scores)
    if not pairs:
        # Degenerate input: still log a FAIL with wide CI to remain auditable.
        rec = build_record(
            auc=0.5,
            min_auc=float(args.min_auc),
            best_j=-1.0,
            best_th=None,
            ci_lo=0.0,
            ci_hi=1.0,
            eff_b=0,
            commit=str(args.commit),
            seed=int(args.seed),
            thr_sha256=str(args.thresholds_sha256),
            anchor_id=str(args.anchor_id),
            notes="no_pairs: check labels/scores join",
        )
        with Path(args.out).open("a", encoding="utf-8") as g:
            g.write(json.dumps(rec) + "\n")
        print(json.dumps({"auc": 0.5, "ci95": [0.0, 1.0], "B": 0}))
        return 0

    auc = auc_midrank(pairs)
    best_j, best_th = youden_best_j(pairs)
    ci_lo, ci_hi, eff_b = bootstrap_auc_ci(
        pairs, int(args.bootstraps), int(args.seed)
    )

    rec = build_record(
        auc=auc,
        min_auc=float(args.min_auc),
        best_j=best_j,
        best_th=best_th,
        ci_lo=ci_lo,
        ci_hi=ci_hi,
        eff_b=eff_b,
        commit=str(args.commit),
        seed=int(args.seed),
        thr_sha256=str(args.thresholds_sha256),
        anchor_id=str(args.anchor_id),
    )
    with Path(args.out).open("a", encoding="utf-8") as g:
        g.write(json.dumps(rec) + "\n")
    print(json.dumps({"auc": auc, "ci95": [ci_lo, ci_hi], "B": eff_b}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
