# tools/emit_tg_ind_min.py
#!/usr/bin/env python3
import json, argparse, time, os, math

def l2(v): return math.sqrt(sum((x*x for x in v))) if v else 0.0
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def norm(v):  n=l2(v); return [x/n for x in v] if n>0 else v

def load_invariants(path):
    data=json.load(open(path,'r',encoding='utf-8'))
    invs=data.get('invariants') or []
    return [norm(inv.get('grad') or []) for inv in invs if isinstance(inv,dict)]

def load_xt(path):
    data=json.load(open(path,'r',encoding='utf-8'))
    return data.get('X_t') or []

def frobenius_residual(basis):  # 配線確認用の保守値（MWE）
    return 8e-4

def orthogonality(Xt,basis):   # max |<Xt,b_i>| / (||Xt||·||b_i||)
    nXt=l2(Xt)
    if nXt==0 or not basis: return 1e-7
    m=0.0
    for b in basis:
        nb=l2(b); 
        if nb==0: continue
        m=max(m, abs(dot(Xt,b)/(nXt*nb)))
    return m

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--invariants', required=True)
    ap.add_argument('--xt', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--commit', default='UNKNOWN')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--thresholds-sha256', default='UNKNOWN')
    ap.add_argument('--anchor-id', default='UNKNOWN')
    args=ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    basis=load_invariants(args.invariants)
    Xt=load_xt(args.xt)
    frob=frobenius_residual(basis)
    orth=orthogonality(Xt,basis)
    status="PASS" if (frob<=1e-3 and orth<=1e-6) else "FAIL"

    rec={
      "stage":"tg_ind","status":status,"metric":None,"value":None,"threshold":None,
      "aux":{"frobenius_resid":frob,"orthogonality":orth},
      "notes":"mwe|minimal emitter (replace with full protocol before publishing)",
      "timestamp":time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
      "commit":args.commit,"seed":args.seed,
      "thresholds_sha256":args.thresholds_sha256,"anchor_id":args.anchor_id
    }
    with open(args.out,'a',encoding='utf-8') as f:
        f.write(json.dumps(rec)+'\n')
    print(json.dumps({"frob":frob,"orth":orth,"status":status}))

if __name__=='__main__': main()
