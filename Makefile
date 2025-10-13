SHELL := bash
.ONESHELL:
.SHELLFLAGS := -Eeuo pipefail -c
.RECIPEPREFIX := >

.PHONY: roc-ci freeze-summary check-v2.4R2

# 上書き可能： make roc-ci ROC_LABELS=data/lab.csv
ROC_LABELS ?= eval/labels.csv
ROC_SCORES ?= eval/scores.csv
ANCHOR_ID  ?= zenodo:10.5281/zenodo.17328804   # 版 DOI を設定

# 直近の母ログ（無ければ既知のフォールバック）
RUN_OUT := $(shell ls -1t outputs/*/pipeline_output.jsonl 2>/dev/null | head -1)
ifeq ($(RUN_OUT),)
RUN_OUT := outputs/run-20251012T024516Z/pipeline_output.jsonl
endif

roc-ci:
> SHA=$$(jq -r '.atlas.thresholds_sha256' codex.meta.json)
> COMMIT=$$(git rev-parse --short HEAD)
> echo "SHA=$$SHA COMMIT=$$COMMIT RUN_OUT=$(RUN_OUT)"
> python3 eval/roc_external_bootstrap.py \
>   --labels "$(ROC_LABELS)" \
>   --scores "$(ROC_SCORES)" \
>   --out eval/roc_external.jsonl \
>   --min-auc 0.75 --bootstraps 5000 \
>   --thresholds-sha256 "$$SHA" --commit "$$COMMIT" \
>   --anchor-id "$(ANCHOR_ID)" --jitter 0.0
> tmp=$$(mktemp); grep -v '"stage":"roc"' "$(RUN_OUT)" > "$$tmp" || true; mv "$$tmp" "$(RUN_OUT)"
> cat eval/roc_external.jsonl >> "$(RUN_OUT)"
> echo "OK → $(RUN_OUT)"

freeze-summary:
> # 最新の母ログを取得（無ければ既知の固定値へ）
> RUN=$$(ls -1t outputs/*/pipeline_output.jsonl 2>/dev/null | head -1 || true)
> [ -n "$$RUN" ] || RUN="outputs/run-20251012T024516Z/pipeline_output.jsonl"
> # Python: timestamp（または ts）で tg_ind/roc/cost の「最新」1件ずつ抽出
> python3 - "$$RUN" <<'PY'
> import json,sys,datetime,os
src=sys.argv[1]
def ts(rec):
	t = rec.get("timestamp") or rec.get("ts") or ""
	try: return datetime.datetime.fromisoformat(t.replace("Z","+00:00"))
	except Exception: return datetime.datetime.min
	latest={}
	with open(src,encoding="utf-8") as f:
	for ln in f:
		try: o=json.loads(ln)
		except Exception: continue
		s=o.get("stage")
		if s in ("tg_ind","roc","cost"):
			prev=latest.get(s)
			if (prev is None) or (ts(o) >= ts(prev)): latest[s]=o
	out=[latest[s] for s in ("tg_ind","roc","cost") if s in latest]
	os.makedirs("artifacts", exist_ok=True)
	path="artifacts/pipeline_output.v2.4R2.summary.jsonl"
	with open(path,"w",encoding="utf-8") as g:
	for r in out: g.write(json.dumps(r)+"\n")
	print(path)
> PY
> sha256sum artifacts/pipeline_output.v2.4R2.summary.jsonl > artifacts/SHA256SUMS.txt
> echo "frozen → artifacts/pipeline_output.v2.4R2.summary.jsonl"

check-v2.4R2:
> # Python: サマリの妥当性チェック（閾値や必須 stage を確認）
> python3 - "artifacts/pipeline_output.v2.4R2.summary.jsonl" <<'PY'
> import json,sys,collections
> src=sys.argv[1]
> c=collections.Counter()
> frob=orth=None; auc=ci=None; roc=False; cost=False
> with open(src,encoding='utf-8') as f:
>	for ln in f:
>		try: o=json.loads(ln)
>		except Exception: continue
>		c[o.get('stage','?')]+=1
>		if o.get('stage')=='tg_ind':
>			a=o.get('aux',{}); frob=a.get('frobenius_resid'); orth=a.get('orthogonality')
>		if o.get('stage')=='roc' and o.get('metric')=='external':
>			roc=True; auc=o.get('value'); ci=o.get('aux',{}).get('ci95')
>		if o.get('stage')=='cost': cost=True
> print({
>   "stages": dict(c),
>   "tg_ind_pass": (frob is not None and frob<=1e-3 and orth is not None and orth<=1e-6),
>   "roc_found": roc, "auc": auc, "ci95": ci, "cost_found": cost
> })
> PY
> # しきい値JSONの DOI（triage 必須 & guard 推奨）も目視
> jq -r '.default.triage.roc.external_set_doi,
>		.default.N_mod.extrapolation_guard.roc.external_set_doi' \
>	 configs/ATLAS_thresholds_v2.4R2.json