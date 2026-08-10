# -*- coding: utf-8 -*-
"""
Cascade-path identification + circular (recycling) edge-contribution demo
================================================================

Demonstrates two analyses (besides the BED scan) on the synthetic example data:
(1) cascade-path identification: run one cascade and print the failure rounds/order (the propagation
    sequence starting from the battery hub);
(2) circular-edge contribution: the Robustness difference between keeping vs removing recycling-tier
    (Tier == 'RC') edges.

Note: runs on synthetic data; illustrates the method and schema, not published numbers (see README).

Run
---
    python scripts/run_cascade_and_circular_demo.py
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.model import SimParams, load_network, simulate_once, circular_edge_contribution  # noqa: E402

DATA_DIR = BASE_DIR / "data"


def main():
    nodes, edges, battery_hub, ev_node = load_network(
        str(DATA_DIR / "nodes_synthetic.csv"), str(DATA_DIR / "edges_synthetic.csv"))

    # Cascade-path identification uses a stronger illustrative setting so that a multi-node cascade is
    # actually triggered on this (robust) synthetic network, exercising the path-identification method.
    print("===== 1) Cascade-path identification (illustrative setting: tau=0.35, beta=10, shock=0.9, BED=0.80) =====", flush=True)
    demo_params = SimParams(tau=0.35, beta=10.0, shock_intensity=0.9, seed=42)
    # scan several seeds; take the run with the largest cascade to display the path
    best = max((simulate_once(nodes, edges, battery_hub, ev_node, 0.80, demo_params, sid)
                for sid in range(20)), key=lambda r: r["n_failed"])
    print(f"battery_hub={battery_hub}  failed_nodes={best['n_failed']}/{best['n_total']}  "
          f"Robustness={best['Robustness']*100:.1f}%", flush=True)
    for k, rnd in enumerate(best["failure_rounds"][:6], 1):
        print(f"  round {k} newly failed ({len(rnd)}): {rnd[:12]}{' ...' if len(rnd) > 12 else ''}", flush=True)
    print(f"  failure order (first 15): {best['failure_order'][:15]}", flush=True)
    if best["n_failed"] == 0:
        print("  (note: this synthetic network is highly robust; no cascade triggered under this "
              "setting. The path-identification method itself is in model.simulate_once.)", flush=True)

    print("\n===== 2) Circular (recycling) edge-contribution (baseline: tau=0.50, beta=10, shock=0.8) =====", flush=True)
    params = SimParams(tau=0.50, beta=10.0, shock_intensity=0.8, seed=42)
    for bed in [0.50, 0.60]:
        c = circular_edge_contribution(nodes, edges, battery_hub, ev_node, bed, params, n_repeats=30)
        print(f"  BED={bed:.2f}: with recycling Robustness={c['robustness_with_recycling_pct']:.1f}%  "
              f"without={c['robustness_without_recycling_pct']:.1f}%  "
              f"contribution={c['recycling_contribution_pp']:+.2f}pp  "
              f"({c['n_recycling_edges_removed']} recycling edges removed)", flush=True)
    print("\n[note] Based on synthetic data; illustrates the method only, not published numbers.", flush=True)


if __name__ == "__main__":
    main()
