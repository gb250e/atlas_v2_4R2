from __future__ import annotations

from typing import Dict, Iterable, Sequence, Tuple

import numpy as np


def _prepare_scores(
    rows: Iterable[Dict[str, object]],
    positives: Sequence[str],
) -> Sequence[Tuple[float, bool]]:
    pairs = []
    pos_set = set(positives)
    for r in rows:
        aux = r.get("aux", {}) if isinstance(r, dict) else {}
        cls = aux.get("class")
        conf = aux.get("confidence")
        try:
            score = float(conf)
        except (TypeError, ValueError):
            continue
        pairs.append((score, cls in pos_set))
    pairs.sort(key=lambda x: -x[0])
    return pairs


def roc_curve(
    rows: Iterable[Dict[str, object]],
    positives: Sequence[str] = ("true_tear",),
) -> Dict[str, object]:
    pairs = _prepare_scores(rows, positives)
    if not pairs:
        return {"fpr": [0.0, 1.0], "tpr": [0.0, 1.0], "auc": 0.5, "best_J": 0.0, "threshold": 1.0}
    labels = np.array([1 if is_pos else 0 for _, is_pos in pairs], dtype=np.int32)
    scores = np.array([score for score, _ in pairs], dtype=np.float64)
    P = labels.sum()
    N = len(labels) - P
    if P == 0 or N == 0:
        base = 0.5 if P == N else (1.0 if P > 0 else 0.0)
        return {"fpr": [0.0, 1.0], "tpr": [0.0, 1.0], "auc": base, "best_J": 0.0, "threshold": 1.0}

    fpr = [0.0]
    tpr = [0.0]
    thresholds = [scores[0] + 1e-9]
    tp = fp = 0
    prev_score = None
    for score, label in zip(scores, labels):
        tp += label
        fp += (1 - label)
        if prev_score is None or score != prev_score:
            fpr.append(fp / N)
            tpr.append(tp / P)
            thresholds.append(score)
            prev_score = score
    auc = 0.0
    for i in range(1, len(fpr)):
        auc += (fpr[i] - fpr[i - 1]) * (tpr[i] + tpr[i - 1]) * 0.5
    youden = np.array(tpr) - np.array(fpr)
    idx = int(np.argmax(youden))
    return {
        "fpr": list(map(float, fpr)),
        "tpr": list(map(float, tpr)),
        "auc": float(auc),
        "best_J": float(youden[idx]),
        "threshold": float(thresholds[idx]),
    }
