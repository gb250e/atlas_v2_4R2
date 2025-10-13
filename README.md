# ATLAS External Validation Pack — Zenodo Template (v2.4R2)

This package is a ready-to-upload template to *Zenodo* for registering the **external validation dataset** required by **ATLAS v2.4R2**.
It standardizes layout, metadata, and minimal evaluation artifacts so reviewers and tools can reproduce your results.

## What this pack ensures
- A **versioned DOI** (to be issued by Zenodo) can be recorded into ATLAS thresholds at `triage.roc.external_set_doi`.
- The pack carries the provenance fields expected by ATLAS (`id_or_doi`, `version_or_date`, `method`, `ci_95`, etc.).
- Minimal scripts to compute and export an **external ROC** JSONL from `labels.csv` + `scores.csv`.

## Layout
```
ATLAS_External_Validation_Pack_v2.4R2_TEMPLATE/
  data/                     # your immutable dataset files (you add)
  splits/splits.json        # JSON describing splits used for the ROC (train/val/test or external/test)
  docs/dataset_card.md      # dataset documentation (fill this before upload)
  metadata/zenodo.json      # pre-filled Zenodo metadata (edit & paste)
  eval/compute_roc.py       # pure-Python ROC/AUC export → JSONL (no 3rd-party deps)
  eval/README.md            # how to run the evaluator
  examples/roc_external_sample.jsonl  # sample JSONL record
  checksums/SHA256SUMS.txt  # generated via scripts/make_checksums.sh
  scripts/update_thresholds_doi.sh    # jq patch helper for ATLAS thresholds
  scripts/make_checksums.sh           # generate checksum for data/ recursively
  validate_pack.py          # quick sanity checks for the pack
  manifest.json             # auto-updated manifest (run id, time, etc.)
  LICENSE-PLACEHOLDER.txt   # fill with your chosen license (e.g., CC-BY-4.0)
  CITATION.cff              # citation metadata (edit)
```

## Quick start
1. **Reserve a DOI** on Zenodo (New upload → *Reserve DOI*). Put it into `metadata/zenodo.json` and `docs/dataset_card.md`.
2. Add your files under `data/` and describe them in `docs/dataset_card.md`.
3. Define your split(s) in `splits/splits.json` (IDs must match your labels/scores).
4. Produce model **scores** for the external set (CSV: `id,score`) and put them near `eval/` or under `data/`.
5. Run the evaluator:
   ```bash
   python3 eval/compute_roc.py --labels eval/labels.csv --scores eval/scores.csv --out eval/roc_external.jsonl --profile reviewer --min-auc 0.75
   ```
6. Create checksums: `bash scripts/make_checksums.sh` (writes `checksums/SHA256SUMS.txt`).
7. Zip and upload the whole folder to **Zenodo**; publish to obtain the **version DOI**.
8. Patch your ATLAS thresholds:
   ```bash
   bash scripts/update_thresholds_doi.sh 10.5281/zenodo.XXXXXXX configs/ATLAS_thresholds_v2.4R2.json
   ```
9. Recompute `thresholds_sha256` in `codex.meta.json` and commit.

See `eval/README.md` for ROC export details.
