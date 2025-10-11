# ATLAS v2_4R2 — Hotfix Kit

このキットは、以下の 3 つのエラーを**即時解消**します：
1) `scripts/codex_loop.py` が見つからない → 本キットで追加  
2) `data/toy.jsonl` が見つからない → 本キットで追加  
3) `streamlit: command not found` → `requirements.txt` に `streamlit` を追加（`pip install -r requirements.txt` を実行）

## 使い方（/home/eb24516/work/atlas_v2_4R2 に展開する想定）

```bash
cd /home/eb24516/work/atlas_v2_4R2
# hotfix を展開（zip をこのディレクトリに置いて unzip）
unzip ATLAS_v2_4R2_Hotfix_Kit.zip

# 依存をインストール（WSL）
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# パイプライン実行（生成された toy データで）
python -m atlas.cli.run_pipeline thresholds/thresholds.json data/toy.jsonl out/results.jsonl

# ROC 計算
python -m atlas.cli.compute_roc out/results.jsonl out/roc.json
```

Streamlit GUI を使う場合は、`pip install -r requirements.txt` で `streamlit` を入れた後に、
`streamlit run ui/app.py` を実行してください（GUI 本体はプロジェクト側に依存）。

## 参考
- `thresholds/thresholds.json` は v2.4R2 の要点（τ_Δ=0.15, τ_N=0.05, confidence 定義）に整合。
- 詳細仕様は **ATLAS Framework v2.4R2 Codex フルスペック**を参照してください。
