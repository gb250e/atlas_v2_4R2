#!/usr/bin/env bash
set -euo pipefail
if [ $# -lt 2 ]; then
  echo "Usage: $0 <DOI> <thresholds_json_path>"
  exit 1
fi
DOI="$1"
THR="$2"
tmp="$(mktemp)"
jq --arg doi "$DOI" '
  .default.triage.roc.external_set_doi = $doi
| .profiles.default.triage.roc.external_set_doi = $doi
| .profiles.reviewer.triage.roc.external_set_doi = $doi
| .profiles.student.triage.roc.external_set_doi = $doi
| .profiles.benchmark.triage.roc.external_set_doi = $doi
| .profiles.hpc.triage.roc.external_set_doi = $doi
' "$THR" > "$tmp" && mv "$tmp" "$THR"
echo "Updated external_set_doi in $THR → $DOI"
