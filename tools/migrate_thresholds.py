#!/usr/bin/env python3
import json, argparse, copy

def get_path(d, path):
    cur = d
    for k in path.split('.'):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur

def set_path(d, path, value):
    cur = d
    parts = path.split('.')
    for k in parts[:-1]:
        if k not in cur or not isinstance(cur[k], dict):
            cur[k] = {}
        cur = cur[k]
    cur[parts[-1]] = value

def del_path(d, path):
    cur = d
    parts = path.split('.')
    for k in parts[:-1]:
        if k not in cur or not isinstance(cur[k], dict):
            return
        cur = cur[k]
    cur.pop(parts[-1], None)

def apply_renames(obj, renames):
    for src, dst in renames:
        val = get_path(obj, src)
        if val is not None and get_path(obj, dst) is None:
            set_path(obj, dst, val)
            del_path(obj, src)

def apply_defaults(obj, defaults):
    for k, v in defaults.items():
        if get_path(obj, k) is None:
            set_path(obj, k, v)

def migrate(thr, renames, defaults):
    out = copy.deepcopy(thr)
    # migrate default
    if 'default' in out:
        apply_renames(out['default'], renames)
        apply_defaults(out['default'], defaults)
    # migrate profiles
    if 'profiles' in out and isinstance(out['profiles'], dict):
        for name, prof in out['profiles'].items():
            apply_renames(prof, renames)
            apply_defaults(prof, defaults)
    return out

def main():
    ap = argparse.ArgumentParser(description="Migrate ATLAS thresholds JSON to v2.4R2 schema.")
    ap.add_argument("infile")
    ap.add_argument("-o","--outfile", required=True)
    ap.add_argument("--renames", help="JSON string of [[from,to],...] for extra renames", default=None)
    ap.add_argument("--defaults", help="JSON string of {path:value,...} for extra defaults", default=None)
    args = ap.parse_args()

    with open("configs/ATLAS_thresholds_v2.4R2.json","r",encoding="utf-8") as f:
        canonical = json.load(f)
    rules = canonical.get("default",{}).get("schema_migration",{}).get("rules",[])
    renames = [(r["from"], r["to"]) for r in rules if "from" in r and "to" in r]
    defs = {}
    for r in rules:
        if "defaults" in r:
            defs.update(r["defaults"])

    if args.renames:
        renames += json.loads(args.renames)
    if args.defaults:
        defs.update(json.loads(args.defaults))

    with open(args.infile,"r",encoding="utf-8") as f:
        src = json.load(f)

    migrated = migrate(src, renames, defs)
    with open(args.outfile,"w",encoding="utf-8") as f:
        json.dump(migrated, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
