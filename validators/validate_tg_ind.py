#!/usr/bin/env python3
import argparse, json, sys

def iter_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                print(f"[WARN] skip invalid JSON line: {line[:80]}...", file=sys.stderr)

def main():
    ap = argparse.ArgumentParser(description="Validate TG-Ind log presence and fields.")
    ap.add_argument("log_jsonl", help="Pipeline JSON Lines output")
    ap.add_argument("--frobenius_tol", type=float, default=1e-3)
    ap.add_argument("--orth_tol", type=float, default=1e-6)
    args = ap.parse_args()

    found = False
    ok = False
    for rec in iter_jsonl(args.log_jsonl):
        if rec.get("stage") == "tg_ind":
            found = True
            aux = rec.get("aux", {})
            frob = aux.get("frobenius_resid")
            orth = aux.get("orthogonality")
            if frob is None or orth is None:
                print("TG-Ind record missing frobenius_resid/orthogonality", file=sys.stderr)
                continue
            ok = (frob <= args.frobenius_tol) and (orth <= args.orth_tol)
            print(json.dumps({"found": True, "frobenius_resid": frob, "orthogonality": orth, "pass": ok}))
            break

    if not found:
        print(json.dumps({"found": False, "pass": False}))
        sys.exit(2)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
