# ATLAS v2.4R2 — Validation Dataset & Reference Implementation

This package contains:
- Synthetic validation datasets: `data/calibration.jsonl`, `data/control_small_curvature.jsonl`, `data/synthetic_real_mixture.jsonl`
- Reference implementation (minimal): `atlas_reference_impl/`
- Scripts: `scripts/run_pipeline.py`, `scripts/compute_roc.py`
- Schemas: `schema/`
- Thresholds: `ATLAS_thresholds_v2.4R2.json`
- ROC report & figure: `roc_report.json`, `figures/roc_curves.png`

## Reproduce
```bash
python scripts/run_pipeline.py ATLAS_thresholds_v2.4R2.json data/synthetic_real_mixture.jsonl results_synthetic_real_mixture.jsonl
python scripts/compute_roc.py results_synthetic_real_mixture.jsonl roc_synthetic_real.json
```

## License
- Data: CC BY 4.0
- Code: Apache-2.0
