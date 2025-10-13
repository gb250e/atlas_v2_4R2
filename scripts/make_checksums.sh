#!/usr/bin/env bash
set -euo pipefail
if [ ! -d "data" ]; then
  echo "No data/ directory found. Create and add files first." >&2
  exit 1
fi
mkdir -p checksums
# sha256sum every file under data/
( cd data && find . -type f -print0 | xargs -0 sha256sum ) > checksums/SHA256SUMS.txt
echo "Wrote checksums/SHA256SUMS.txt"
