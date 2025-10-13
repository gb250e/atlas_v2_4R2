#!/usr/bin/env python3
import argparse, csv, json, math, random, time
from collections import defaultdict

def read_csv_pairs(path, key_name, val_name, cast=float):
    d = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            k = row[key_name]
            v = cast(row[val_name])
            d[k] = v
    return d

def roc_points(scores, labels):
    # scores: list of floats; labels: list of 0/1 ints
    # Sort by descending score
    pairs = sorted(zip(scores, labels), key=lambda x: -x[0])
    P = sum(labels)
    N = len(labels) - P
    tp = fp = 0
    fn = P
    tn = N
    last_score = None
    points = []
    for s, y in pairs:
        if last_score is None or s != last_score:
            # record point at current threshold
            fpr = fp / N if N else 0.0
            tpr = tp / P if P else 0.0
            points.append((fpr, tpr))
            last_score = s
        # move threshold below this score → count this as positive
        if y == 1:
            tp += 1; fn -= 1
        else:
            fp += 1; tn -= 1
    # final point
    fpr = fp / N if N else 0.0
    tpr = tp / P if P else 0.0
    points.append((fpr, tpr))
    # ensure start at (0,0), end at (1,1)
    points = [(0.0,0.0)] + points + [(1.0,1.0)]
    # deduplicate monotone
    uniq = []
    for p in points:
        if not uniq or p != uniq[-1]:
            uniq.append(p)
    return uniq

def auc_trapezoid(points):
    # points: [(fpr, tpr), ...] sorted by fpr asc
    points = sorted(points, key=lambda p: p[0])
    area = 0.0
    for (x0,y0),(x1,y1) in zip(points[:-1], points[1:]):
        dx = x1 - x0
        area += dx * (y0 + y1) / 2.0
    return max(0.0, min(1.0, area))

def best_youden_J(points):
    # Return max(tpr - fpr)
    return max((tpr - fpr) for (fpr,tpr) in points)

def bootstrap_auc(scores, labels, B=500, seed=1337):
    rnd = random.Random(seed)
    n = len(scores)
    aucs = []
    for _ in range(B):
        idx = [rnd.randrange(n) for _ in range(n)]
        ss = [scores[i] for i in idx]
        ll = [labels[i] for i in idx]
        pts = roc_points(ss, ll)
        aucs.append(auc_trapezoid(pts))
    aucs.sort()
    lo = aucs[int(0.025*B)]
    hi = aucs[int(0.975*B)]
    return lo, hi

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True, help="CSV file with columns: id,label")
    ap.add_argument("--scores", required=True, help="CSV file with columns: id,score")
    ap.add_argument("--out", default="roc_external.jsonl")
    ap.add_argument("--min-auc", type=float, default=0.75)
    ap.add_argument("--profile", default="reviewer")
    ap.add_argument("--commit", default="UNKNOWN")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--thresholds-sha256", default="UNKNOWN")
    ap.add_argument("--anchor-id", default="UNKNOWN")
    args = ap.parse_args()

    labels = read_csv_pairs(args.labels, "id", "label", cast=lambda x:int(float(x)))
    scores = read_csv_pairs(args.scores, "id", "score", cast=float)

    # inner join on ids
    ids = sorted(set(labels.keys()) & set(scores.keys()))
    y = [labels[i] for i in ids]
    s = [scores[i] for i in ids]

    pts = roc_points(s, y)
    auc = auc_trapezoid(pts)
    J = best_youden_J(pts)
    lo, hi = bootstrap_auc(s, y, B=500, seed=args.seed)

    status = "PASS" if auc >= args.min_auc else "FAIL"
    rec = {
        "stage": "roc",
        "status": status,
        "metric": "external",
        "value": auc,
        "threshold": args.min_auc,
        "aux": {
            "best_J": J,
            "ci95": [lo, hi],
            "roc_points": pts,
            "n": len(ids)
        },
        "notes": f"profile={args.profile}",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "commit": args.commit,
        "seed": args.seed,
        "thresholds_sha256": args.thresholds_sha256,
        "anchor_id": args.anchor_id
    }
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(json.dumps({"auc": auc, "best_J": J, "ci95": [lo,hi], "status": status}, ensure_ascii=False))

if __name__ == "__main__":
    main()
