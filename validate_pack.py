#!/usr/bin/env python3
import os, json, sys

BASE = os.path.dirname(__file__)

def fail(msg):
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    sys.exit(1)

def must_exist(path):
    if not os.path.exists(path):
        fail(f"Missing required file: {path}")

def main():
    must_exist(os.path.join(BASE, "metadata", "zenodo.json"))
    must_exist(os.path.join(BASE, "docs", "dataset_card.md"))
    must_exist(os.path.join(BASE, "splits", "splits.json"))
    if not os.path.isdir(os.path.join(BASE, "data")):
        fail("Missing data/ directory")
    with open(os.path.join(BASE, "metadata", "zenodo.json"), "r", encoding="utf-8") as f:
        meta = json.load(f)
    for k in ("title","upload_type","description","creators","license","access_right","version"):
        if not meta.get(k):
            fail(f"metadata/zenodo.json missing field: {k}")
    if meta.get("upload_type") != "dataset":
        fail("upload_type must be 'dataset'")
    # Splits sanity
    with open(os.path.join(BASE, "splits", "splits.json"), "r", encoding="utf-8") as f:
        splits = json.load(f)
    if "external" not in splits:
        fail("splits.json must contain an 'external' section")
    print(json.dumps({"ok": True, "message": "Pack looks structurally sound."}, ensure_ascii=False))

if __name__ == "__main__":
    main()
