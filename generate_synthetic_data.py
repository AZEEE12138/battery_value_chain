# -*- coding: utf-8 -*-
"""
Synthetic example-data generator
================================================================

Generates a fully synthetic battery value-chain example dataset for the public release. The schema
(column layout, node/edge organisation, BED scenario-table format) matches what the analysis code
expects, while:

- all node identities are neutral codes (S001, S002, ...), with no real firm names or classification
  codes;
- sectors are labelled only with generic English category names, not tied to any classification
  system;
- all numerical values (weights, degrees, BED scenario shares) are freshly generated from a fixed
  random seed and neither derive from nor can be reverse-engineered to any real records;
- the generation procedure is fully open (this script), so the dataset carries no confidential
  information.

Design principles (see the repository README)
---------------------------------------------
1. Fully synthetic: no real values are reused; everything is regenerated.
2. The dataset is meant to demonstrate code functionality and the data schema; it is NOT intended to
   reproduce exact published figures.
3. Contains no identifiable firm/classification elements.

Run
---
    python scripts/generate_synthetic_data.py
"""
from pathlib import Path
import numpy as np
import pandas as pd

# Fixed seed: makes the bundled example reproducible for anyone; because the data are synthetic,
# publishing the seed reveals no confidential information.
SEED = 20260806

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------
# Tiered structure of the synthetic value chain (generic supply-chain layout)
# ------------------------------------------------------------------
# Each tier: (tier code, generic English label prefix, node count)
TIERS = [
    ("RM", "Raw material", 20),        # upstream raw materials
    ("PM", "Processed material", 24),  # processed materials
    ("CP", "Component", 20),           # components
    ("CE", "Cell", 14),                # cells
    ("AP", "Application", 12),         # end applications (EV / storage / other)
    ("RC", "Recycling", 16),           # recycling
]
# The battery-manufacturing hub and the EV-application node (the two roles the BED definition needs)
BATTERY_HUB_LABEL = "Battery manufacturing"
EV_APP_LABEL = "Electric-vehicle assembly"


def build_nodes(rng: np.random.Generator) -> pd.DataFrame:
    """Build the node table: neutral codes + generic English sector labels."""
    rows = []
    idx = 1
    for tier_code, label_prefix, count in TIERS:
        for j in range(count):
            code = f"S{idx:03d}"
            # generic, purely descriptive sector label
            if tier_code == "CE" and j == 0:
                sector = BATTERY_HUB_LABEL
            elif tier_code == "AP" and j == 0:
                sector = EV_APP_LABEL
            elif tier_code == "AP" and j == 1:
                sector = "Stationary-storage integration"
            elif tier_code == "AP" and j == 2:
                sector = "Export / other application"
            else:
                sector = f"{label_prefix} sector {j + 1:02d}"
            rows.append({
                "Node_Code": code,
                "Tier": tier_code,
                "Sector_Label_EN": sector,
            })
            idx += 1
    nodes = pd.DataFrame(rows)
    return nodes


def _lognormal_weight(rng: np.random.Generator, n: int, scale: float) -> np.ndarray:
    """Synthetic edge weights: lognormal, plausible magnitude but fully randomly generated."""
    return np.round(rng.lognormal(mean=np.log(scale), sigma=1.0, size=n), 2)


def build_edges(rng: np.random.Generator, nodes: pd.DataFrame) -> pd.DataFrame:
    """
    Build directed weighted edges: mostly forward (upstream -> downstream) flows, plus recycling
    return edges and a few indirect edges, up to the target edge count. All edges and weights are
    synthetic.
    """
    by_tier = {t: nodes[nodes["Tier"] == t]["Node_Code"].tolist() for t, _, _ in TIERS}
    battery_hub = nodes[nodes["Sector_Label_EN"] == BATTERY_HUB_LABEL]["Node_Code"].iloc[0]
    ev_node = nodes[nodes["Sector_Label_EN"] == EV_APP_LABEL]["Node_Code"].iloc[0]

    forward_order = ["RM", "PM", "CP", "CE", "AP"]
    edges = []
    seen = set()

    def add_edge(s, t, wscale, category):
        if s == t or (s, t) in seen:
            return
        seen.add((s, t))
        edges.append({
            "Source_Code": s,
            "Target_Code": t,
            "Category": category,
            "Weight": float(_lognormal_weight(rng, 1, wscale)[0]),
        })

    # Forward supply flows: each tier's nodes connect to several nodes in the next tier
    for a, b in zip(forward_order[:-1], forward_order[1:]):
        for s in by_tier[a]:
            k = rng.integers(3, 7)
            targets = rng.choice(by_tier[b], size=min(k, len(by_tier[b])), replace=False)
            for t in targets:
                add_edge(s, t, 5.0e4, "forward_supply")

    # Battery-hub out-edges: an explicit dominant battery -> EV edge plus battery -> other
    # application/component edges (needed by the BED definition). The battery -> EV weight is much
    # larger, placing the synthetic baseline BED near a plausible magnitude (~0.5).
    add_edge(battery_hub, ev_node, 6.0e5, "battery_to_ev")
    for t in by_tier["AP"]:
        if t != ev_node:
            add_edge(battery_hub, t, 6.0e4, "battery_to_application")
    for t in rng.choice(by_tier["CP"], size=6, replace=False):
        add_edge(battery_hub, t, 3.0e4, "battery_to_component")

    # Recycling returns: recycling tier draws from application/cell tiers and feeds processed
    # materials (closed loop)
    for s in by_tier["RC"]:
        for t in rng.choice(by_tier["PM"], size=rng.integers(2, 5), replace=False):
            add_edge(s, t, 2.0e4, "recycling_loop")
    for s in rng.choice(by_tier["AP"], size=len(by_tier["AP"]), replace=False):
        for t in rng.choice(by_tier["RC"], size=rng.integers(2, 4), replace=False):
            add_edge(s, t, 2.5e4, "end_of_life_return")

    # A few cross-tier indirect edges for realism (still synthetic)
    all_codes = nodes["Node_Code"].tolist()
    while len(edges) < 739:
        s, t = rng.choice(all_codes, size=2, replace=False)
        add_edge(s, t, 1.0e4, "indirect")

    edges_df = pd.DataFrame(edges)
    return edges_df, battery_hub, ev_node


def build_bed_scenarios(rng: np.random.Generator) -> pd.DataFrame:
    """
    Build the annual BED scenario table (2015-2035): two trajectories (optimistic/conservative).
    Values are synthetic trend lines plus noise; the source column carries generic descriptors only.
    """
    years = list(range(2015, 2036))
    rows = []
    for y in years:
        if y <= 2025:
            # historical segment: a single rising trend + noise (synthetic)
            base = 25 + (y - 2015) * 4.2 + rng.normal(0, 1.5)
            base = float(np.clip(base, 20, 72))
            opt = cons = round(base, 1)
            note = "Historical (synthetic); single trajectory"
            source = "Synthetic historical series"
        else:
            # projection segment: optimistic (declining) vs conservative (high)
            t = y - 2025
            opt = round(float(np.clip(63 - t * 2.0 + rng.normal(0, 0.6), 40, 65)), 1)
            cons = round(float(np.clip(64 - t * 0.6 + rng.normal(0, 0.4), 55, 65)), 1)
            note = "Projection (synthetic); optimistic vs conservative"
            source = "Synthetic scenario model"
        rows.append({
            "Year": y,
            "BED_optimistic_pct": opt,
            "BED_conservative_pct": cons,
            "Scenario_Note": note,
            "Source": source,
        })
    return pd.DataFrame(rows)


def main():
    print("[generate] synthetic example data (fixed seed)...", flush=True)
    rng = np.random.default_rng(SEED)

    nodes = build_nodes(rng)
    edges, battery_hub, ev_node = build_edges(rng, nodes)
    bed = build_bed_scenarios(rng)

    # Fill in node degree/weight columns (computed from the synthetic edges)
    out_w = edges.groupby("Source_Code")["Weight"].sum()
    in_w = edges.groupby("Target_Code")["Weight"].sum()
    out_d = edges.groupby("Source_Code").size()
    in_d = edges.groupby("Target_Code").size()
    nodes["Out_Degree"] = nodes["Node_Code"].map(out_d).fillna(0).astype(int)
    nodes["In_Degree"] = nodes["Node_Code"].map(in_d).fillna(0).astype(int)
    nodes["Out_Weight"] = nodes["Node_Code"].map(out_w).fillna(0.0).round(2)
    nodes["In_Weight"] = nodes["Node_Code"].map(in_w).fillna(0.0).round(2)
    nodes["Is_Battery_Hub"] = (nodes["Node_Code"] == battery_hub)
    nodes["Is_EV_Node"] = (nodes["Node_Code"] == ev_node)

    nodes.to_csv(DATA_DIR / "nodes_synthetic.csv", index=False, encoding="utf-8")
    edges.to_csv(DATA_DIR / "edges_synthetic.csv", index=False, encoding="utf-8")
    bed.to_csv(DATA_DIR / "bed_scenarios_synthetic.csv", index=False, encoding="utf-8")

    # Compute and print the synthetic baseline BED
    b2e = edges[(edges["Source_Code"] == battery_hub) & (edges["Target_Code"] == ev_node)]["Weight"]
    total_out = edges[edges["Source_Code"] == battery_hub]["Weight"].sum()
    baseline_bed = float(b2e.iloc[0] / total_out) if len(b2e) and total_out > 0 else float("nan")

    print(f"[done] nodes={len(nodes)}  edges={len(edges)}  battery_hub={battery_hub}  ev_node={ev_node}", flush=True)
    print(f"[done] synthetic baseline BED={baseline_bed:.3f}", flush=True)
    print(f"[out] {DATA_DIR / 'nodes_synthetic.csv'}", flush=True)
    print(f"[out] {DATA_DIR / 'edges_synthetic.csv'}", flush=True)
    print(f"[out] {DATA_DIR / 'bed_scenarios_synthetic.csv'}", flush=True)


if __name__ == "__main__":
    main()
