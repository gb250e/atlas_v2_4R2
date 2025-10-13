# Evaluator — External ROC exporter (pure Python)

## Inputs
- `labels.csv`: CSV with header `id,label` where label ∈ {0,1}
- `scores.csv`: CSV with header `id,score` where score ∈ ℝ (higher → more positive)

## Output
- `roc_external.jsonl`: one JSON object with fields:
  - `stage="roc"`, `metric="external"`, `value=<AUC>`, `threshold=<min_auc> | null`,
  - `status = "PASS" if AUC ≥ min_auc else "FAIL"`,
  - `aux = { "best_J": <float>, "ci95": [lo, hi], "roc_points": [[fpr,tpr], ...] }`

## Example
```bash
python3 compute_roc.py --labels labels.csv --scores scores.csv --out roc_external.jsonl --profile reviewer --min-auc 0.75
```
