# ATLAS v1.9R5 → v2.4R2 Migration Guide

This document summarizes the schema migration rules embedded in `configs/ATLAS_thresholds_v2.4R2.json`.

## Supported source versions
1.95R5, 2.0, 2.0R1, 2.2, 2.3, 2.3R1, 2.4, 2.4R1

## Key renames
- `epsilon` → `N_mod.regularization_epsilon`
- `epsilon_range` → `N_mod.regularization_epsilon_range`
- `lr_speed` → `v_LR`
- `causality.epsilon` → `epsilon_caus`
- `delta_local` → `delta_chart`
- `delta_lat` → `delta_chart`
- `holonomy` → `holonomy_lb`
- `H_lb` → `holonomy_lb`

## Default insertions (if missing)
- `determinism.rng_name` = `Philox`
- `determinism.dtype` = `float64`
- `determinism.rtol` = `1e-10`
- `determinism.atol` = `1e-14`
- `determinism.ulp_max` = `8`
- `H_top.plateau_method` = `theil_sen`
- `H_top.plateau_pmax` = `0.1`
- `triage.report.required` = `True`

## How to migrate an old thresholds file
1. Run the script:
   ```bash
   python tools/migrate_thresholds.py old_thresholds.json -o configs/ATLAS_thresholds_v2.4R2.migrated.json
   ```
2. Inspect differences and copy the calibrated fields (e.g., `anchor_metric.scales`, `provenance.*`) from your environment.
3. Update any `TBD` fields (e.g., `triage.roc.external_set_doi`) and add anchor-specific values for `epsilon_caus` / `v_LR`.
