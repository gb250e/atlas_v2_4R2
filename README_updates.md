# Bump to ATLAS v2.4R2 — Repository Updates

## File layout
- Add: `docs/ATLAS_Framework_v2.4R2.md`, `docs/ATLAS_Framework_v2.4R2.pdf`, `docs/LATEST.md`
- Add: `configs/ATLAS_thresholds_v2.4R2.json`
- Add: `tools/migrate_thresholds.py`, `validators/validate_tg_ind.py`
- Add: `VERSION`, `codex.meta.json`, `MIGRATION.md`

## Suggested Git steps
```bash
git checkout -b chore/atlas-v2.4R2
unzip atlas_v2.4R2_patch.zip -d .
git add VERSION docs/ configs/ tools/ validators/ codex.meta.json MIGRATION.md
git commit -m "ATLAS: bump to v2.4R2 (spec, thresholds, migration tools)"
```

## Indexer ('codex') hints
- Machine-readable files:
  - `VERSION` contains `2.4R2`
  - `docs/LATEST.md` first bullet: **Current latest: v2.4R2**
  - `codex.meta.json.atlas.latest` = `2.4R2`
- Update any internal indexers to prioritize these markers.
