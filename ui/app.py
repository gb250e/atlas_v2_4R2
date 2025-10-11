from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import streamlit as st

# streamlit 実行時にもリポジトリルートを import パスに登録する
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from atlas.cli.run_pipeline import run_pipeline
from atlas.io.jsonl import read_jsonl
from atlas.utils.stats import roc_curve


def stage_lookup(rows: List[Dict[str, object]], stage_name: str) -> Dict[str, Dict[str, object]]:
    return {row["anchor_id"]: row for row in rows if row.get("stage") == stage_name}


def ensure_fig_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    st.title("ATLAS v2.4R2 Pipeline Dashboard")

    default_thresholds = Path("thresholds/thresholds.json").resolve()
    default_input = Path("data/toy.jsonl").resolve()
    default_output = Path("out/results.jsonl").resolve()

    thresholds_path = Path(st.text_input("Thresholds path", str(default_thresholds)))
    input_path = Path(st.text_input("Input JSONL path", str(default_input)))
    output_path = Path(st.text_input("Results JSONL path", str(default_output)))

    run_triggered = st.button("Run pipeline")

    out_rows: List[Dict[str, object]] = []
    if run_triggered:
        with st.spinner("Running pipeline..."):
            out_rows = run_pipeline(thresholds_path, input_path, output_path)
        st.success(f"Pipeline completed with {len(out_rows)} StageResult rows.")
    elif output_path.exists():
        out_rows = list(read_jsonl(str(output_path)))

    if not out_rows:
        st.info("Run the pipeline or point to an existing results JSONL to view panels.")
        return

    anchors = sorted({row["anchor_id"] for row in out_rows if "anchor_id" in row})
    st.write(f"Loaded results for {len(anchors)} anchors.")

    fig_dir = Path("out/fig")
    ensure_fig_dir(fig_dir)

    delta_rows = stage_lookup(out_rows, "delta")
    nmod_rows = stage_lookup(out_rows, "nmod")
    htop_rows = stage_lookup(out_rows, "htop")
    triage_rows = [row for row in out_rows if row.get("stage") == "triage"]

    # Δ panel
    fig_delta, ax_delta = plt.subplots(figsize=(6, 3))
    delta_vals = [delta_rows[a]["aux"].get("delta_chart", 0.0) for a in anchors if a in delta_rows]
    tau_delta = next(iter(delta_rows.values()))["aux"].get("tau_delta", 0.0) if delta_rows else 0.0
    ax_delta.bar(range(len(delta_vals)), delta_vals, color="tab:blue")
    ax_delta.axhline(tau_delta, color="tab:red", linestyle="--", label=r"$\tau_{\Delta}$")
    ax_delta.set_title("Δ stage")
    ax_delta.set_ylabel("Δ value")
    ax_delta.legend()
    st.pyplot(fig_delta)
    fig_delta.savefig(fig_dir / "delta_panel.png", dpi=150, bbox_inches="tight")

    # N panel
    fig_n, ax_n = plt.subplots(figsize=(6, 3))
    n_vals = [nmod_rows[a]["aux"].get("abs_delta_N", 0.0) for a in anchors if a in nmod_rows]
    tau_n = next(iter(nmod_rows.values()))["aux"].get("tau_n", 0.0) if nmod_rows else 0.0
    ax_n.bar(range(len(n_vals)), n_vals, color="tab:green")
    ax_n.axhline(tau_n, color="tab:red", linestyle="--", label=r"$\tau_{N}$")
    ax_n.set_title("N_mod stage")
    ax_n.set_ylabel("|δN|")
    ax_n.legend()
    st.pyplot(fig_n)
    fig_n.savefig(fig_dir / "nmod_panel.png", dpi=150, bbox_inches="tight")

    # H panel
    fig_h, ax_h = plt.subplots(figsize=(6, 3))
    h_obs_vals = [htop_rows[a]["aux"].get("H_obs", 0.0) for a in anchors if a in htop_rows]
    h_lb_vals = [htop_rows[a]["aux"].get("H_lb", 0.0) for a in anchors if a in htop_rows]
    ax_h.plot(range(len(h_obs_vals)), h_obs_vals, marker="o", label="H_obs")
    ax_h.plot(range(len(h_lb_vals)), h_lb_vals, marker="x", label="H_lb")
    ax_h.set_title("H_top stage")
    ax_h.set_ylabel("H value")
    ax_h.legend()
    st.pyplot(fig_h)
    fig_h.savefig(fig_dir / "htop_panel.png", dpi=150, bbox_inches="tight")

    # ROC
    roc = roc_curve(triage_rows)
    fig_roc, ax_roc = plt.subplots(figsize=(4, 4))
    ax_roc.plot(roc["fpr"], roc["tpr"], marker="o", label="ROC")
    ax_roc.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Chance")
    ax_roc.set_xlabel("False Positive Rate")
    ax_roc.set_ylabel("True Positive Rate")
    ax_roc.set_title(f"ROC (AUC={roc['auc']:.3f})")
    ax_roc.legend()
    st.pyplot(fig_roc)
    fig_roc.savefig(fig_dir / "roc_curve.png", dpi=150, bbox_inches="tight")

    st.json(roc)


if __name__ == "__main__":
    main()
