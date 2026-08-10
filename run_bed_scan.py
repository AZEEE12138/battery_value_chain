# -*- coding: utf-8 -*-
"""
BED-scan demonstration
================================================================

Runs the full analysis pipeline on the synthetic example data, producing a Robustness-vs-BED curve
and saving the results table and figure. Demonstrates code functionality and the method workflow.

Note
----
This script runs on synthetic data; its values are NOT intended to reproduce exact published figures
(see the repository README). It illustrates the method and the data schema, not empirical results.

Run
---
    python scripts/run_bed_scan.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.model import SimParams, load_network, bed_scan  # noqa: E402

DATA_DIR = BASE_DIR / "data"
OUT_DIR = BASE_DIR / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("[load] synthetic network...", flush=True)
    nodes, edges, battery_hub, ev_node = load_network(
        str(DATA_DIR / "nodes_synthetic.csv"),
        str(DATA_DIR / "edges_synthetic.csv"),
    )
    print(f"[load] nodes={len(nodes)}  edges={len(edges)}  battery_hub={battery_hub}  ev_node={ev_node}", flush=True)

    params = SimParams(tau=0.50, beta=10.0, shock_intensity=0.8, seed=42)
    bed_grid = [round(x, 2) for x in np.arange(0.30, 0.701, 0.05)]

    print(f"[run] BED scan grid={bed_grid} repeats=30 ...", flush=True)
    df = bed_scan(nodes, edges, battery_hub, ev_node, bed_grid, params, n_repeats=30)
    out_csv = OUT_DIR / "bed_scan_results.csv"
    df.to_csv(out_csv, index=False, encoding="utf-8")
    print(f"[out] {out_csv}", flush=True)
    print(df.to_string(index=False), flush=True)

    # plot
    fig, ax = plt.subplots(figsize=(5.4, 4.0))
    ax.errorbar(df["BED"], df["Robustness_pct_mean"], yerr=df["Robustness_pct_std"],
                marker="o", markersize=6, markeredgecolor="black", markeredgewidth=0.5,
                color="#0072B2", linewidth=1.6, capsize=3)
    ax.axhline(50, color="#D55E00", linestyle="--", linewidth=1, label="Illustrative warning line (50%)")
    ax.set_xlabel("Battery-EV Dependency (BED)", fontweight="bold")
    ax.set_ylabel("Robustness (%)", fontweight="bold")
    ax.set_title("Robustness vs BED (synthetic demonstration data)", fontsize=10, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.legend(fontsize=8, frameon=True, edgecolor="#222")
    fig.tight_layout()
    out_png = OUT_DIR / "bed_scan_demo.png"
    fig.savefig(out_png, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"[out] {out_png}", flush=True)
    print("\n[note] Based on synthetic data; illustrates the method only, not published numbers.", flush=True)


if __name__ == "__main__":
    main()
