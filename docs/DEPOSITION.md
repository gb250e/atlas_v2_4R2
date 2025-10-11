# Deposition Guide (Zenodo or OSF)

1. Create a GitHub release for this package or upload zip directly.
2. Connect the repository to Zenodo (or upload to OSF) and publish a new record.
3. Use `docs/zenodo.json` and `docs/datacite.json` metadata.
4. After DOI is minted, replace DOI placeholders in:
   - docs/CITATION.cff
   - docs/README.md (if referenced)
5. Record the DOI in your paper and in ATLAS thresholds `provenance.external_set_doi` fields where needed.
