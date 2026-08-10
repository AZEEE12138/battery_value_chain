# -*- coding: utf-8 -*-
"""
Battery value-chain resilience model — reference implementation
================================================================

A self-contained reference implementation of the analysis pipeline: network construction ->
controlled BED rewiring -> demand shock + sigmoid cascading failure -> priority-free probabilistic
recovery -> resilience metric (Robustness).

Notes
-----
- This is a clean, standalone implementation. It contains no internal paths, real data, or
  identifiable information.
- The bundled dataset is synthetic (see the repository README and DATA_DICTIONARY). Running this code
  therefore illustrates the data schema and method behaviour; it is NOT intended to reproduce exact
  published numbers.

Core definitions
----------------
- BED (Battery-EV Dependency) = weight of the battery-hub -> EV edge divided by the battery hub's
  total outgoing weight.
- Controlled rewiring: with the battery hub's total outgoing weight conserved, set the battery -> EV
  edge to the target BED share and rescale the remaining out-edges proportionally.
- Failure probability: sigmoid P_fail = 1 / (1 + exp(-beta * (profit_loss - tau)));
  P_fail = 0.5 exactly when profit_loss = tau.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


# ------------------------------------------------------------------
# Parameter container
# ------------------------------------------------------------------
@dataclass
class SimParams:
    """Simulation parameters (defaults)."""
    tau: float = 0.50          # bankruptcy threshold (failure prob crosses 0.5 when loss = tau)
    beta: float = 10.0         # sigmoid steepness
    shock_intensity: float = 0.8   # demand-shock intensity (fractional EV-demand drop)
    max_cascade_rounds: int = 15   # cascade propagation round cap (loose safety cap)
    recovery_steps: int = 45       # number of recovery steps
    p_recover: float = 0.05        # per-step baseline recovery probability
    seed: int = 42                 # random seed (effective seed = seed + simulation_id)


# ------------------------------------------------------------------
# Data loading and network construction
# ------------------------------------------------------------------
def load_network(nodes_csv: str, edges_csv: str) -> Tuple[pd.DataFrame, pd.DataFrame, str, str]:
    """Load node/edge tables; return (nodes, edges, battery_hub_code, ev_node_code)."""
    nodes = pd.read_csv(nodes_csv, encoding="utf-8")
    edges = pd.read_csv(edges_csv, encoding="utf-8")
    battery_hub = nodes.loc[nodes["Is_Battery_Hub"], "Node_Code"].iloc[0]
    ev_node = nodes.loc[nodes["Is_EV_Node"], "Node_Code"].iloc[0]
    return nodes, edges, str(battery_hub), str(ev_node)


def current_bed(edges: pd.DataFrame, battery_hub: str, ev_node: str) -> float:
    """Compute BED = (battery -> EV edge weight) / (battery total outgoing weight)."""
    src = edges["Source_Code"].astype(str)
    b_out = edges[src == battery_hub]
    total = b_out["Weight"].sum()
    if total <= 0:
        return 0.0
    b2e = b_out[b_out["Target_Code"].astype(str) == ev_node]["Weight"]
    return float(b2e.iloc[0] / total) if len(b2e) else 0.0


# ------------------------------------------------------------------
# Controlled BED rewiring
# ------------------------------------------------------------------
def rewire_to_target_bed(edges: pd.DataFrame, battery_hub: str, ev_node: str,
                         target_bed: float) -> pd.DataFrame:
    """
    Conserving the battery hub's total outgoing weight, set the battery -> EV edge to the target BED
    share and redistribute the remaining battery out-edges proportionally.

    Let W be the (conserved) battery total outgoing weight. After rewiring:
        w(battery -> EV)      = target_bed * W
        w(battery -> other i) = (1 - target_bed) * W * (orig w_i / sum of other orig out-weights)
    """
    if not (0.0 <= target_bed <= 1.0):
        raise ValueError(f"target_bed={target_bed} out of [0,1]")

    edges = edges.copy()
    src = edges["Source_Code"].astype(str)
    tgt = edges["Target_Code"].astype(str)

    b_mask = src == battery_hub
    W = edges.loc[b_mask, "Weight"].sum()
    if W <= 0:
        return edges

    ev_mask = b_mask & (tgt == ev_node)
    other_mask = b_mask & (tgt != ev_node)
    other_sum = edges.loc[other_mask, "Weight"].sum()

    # battery -> EV set to target share
    edges.loc[ev_mask, "Weight"] = target_bed * W
    # remaining out-edges share (1 - target) * W proportionally
    if other_sum > 0:
        factor = (1.0 - target_bed) * W / other_sum
        edges.loc[other_mask, "Weight"] = edges.loc[other_mask, "Weight"] * factor
    return edges


# ------------------------------------------------------------------
# Shock + sigmoid cascading failure
# ------------------------------------------------------------------
def _sigmoid_fail_prob(profit_loss: np.ndarray, tau: float, beta: float) -> np.ndarray:
    """Node failure probability P = 1/(1+exp(-beta*(loss-tau))); equals 0.5 when loss = tau."""
    return 1.0 / (1.0 + np.exp(-beta * (profit_loss - tau)))


def _build_adjacency(nodes: pd.DataFrame, edges: pd.DataFrame
                     ) -> Tuple[List[str], Dict[str, int], np.ndarray, np.ndarray]:
    """Build node index and weighted adjacency (used to propagate loss along edges)."""
    codes = nodes["Node_Code"].astype(str).tolist()
    idx = {c: i for i, c in enumerate(codes)}
    n = len(codes)
    # in_weight[j] = total incoming weight of node j; W[i,j] = weight of edge i->j
    W = np.zeros((n, n), dtype=float)
    for _, e in edges.iterrows():
        s, t = str(e["Source_Code"]), str(e["Target_Code"])
        if s in idx and t in idx:
            W[idx[s], idx[t]] += float(e["Weight"])
    in_weight = W.sum(axis=0)
    return codes, idx, W, in_weight


def simulate_once(nodes: pd.DataFrame, edges: pd.DataFrame, battery_hub: str, ev_node: str,
                  target_bed: float, params: SimParams, simulation_id: int = 0) -> Dict:
    """
    One simulation: rewire to target BED -> apply EV-demand shock -> sigmoid cascade -> probabilistic
    recovery -> compute Robustness. Returns a dict of metrics.

    Reproducibility: random seed = params.seed + simulation_id (deterministic seeding scheme).
    """
    rng = np.random.default_rng(params.seed + simulation_id)

    rewired = rewire_to_target_bed(edges, battery_hub, ev_node, target_bed)
    codes, idx, W, in_weight0 = _build_adjacency(nodes, rewired)
    n = len(codes)

    # Initial output capacity (incoming weight as a proxy for a node's throughput; the battery hub
    # uses its total outgoing weight as its capacity).
    capacity0 = in_weight0.copy()
    b_i = idx[battery_hub]
    capacity0[b_i] = W[b_i, :].sum()
    capacity0 = np.maximum(capacity0, 1e-9)

    # Round 1: the EV-demand shock hits the battery hub directly. Under weight-conserving rewiring the
    # battery hub's first-round loss equals profit_loss = BED * shock_intensity.
    profit_loss = np.zeros(n)
    profit_loss[b_i] = target_bed * params.shock_intensity

    failed = np.zeros(n, dtype=bool)
    failure_rounds: List[List[str]] = []  # nodes newly failing each round (for cascade-path ID)

    # Cascade: failed nodes propagate loss downstream proportionally, triggering further failures.
    for _ in range(params.max_cascade_rounds):
        p_fail = _sigmoid_fail_prob(profit_loss, params.tau, params.beta)
        draw = rng.random(n)
        newly = (draw < p_fail) & (~failed)
        if not newly.any():
            break
        failed |= newly
        failure_rounds.append([codes[i] for i in np.where(newly)[0]])
        # Propagate: for a newly failed node i, downstream j gains loss = (W[i,j]/in_weight0[j]) * loss_i
        for i in np.where(newly)[0]:
            downstream = np.where(W[i, :] > 0)[0]
            for j in downstream:
                if in_weight0[j] > 0:
                    profit_loss[j] = min(1.0, profit_loss[j] + W[i, j] / in_weight0[j] * profit_loss[i])

    # Lowest post-shock output (the emergency-robustness low point)
    surviving = ~failed
    perf_after_shock = capacity0[surviving].sum() / capacity0.sum()

    # Recovery phase: failed nodes recover probabilistically (does not re-invoke the failure sigmoid).
    recovered = failed.copy() & False
    for _ in range(params.recovery_steps):
        still_failed = failed & (~recovered)
        if not still_failed.any():
            break
        draw = rng.random(n)
        newly_rec = still_failed & (draw < params.p_recover)
        recovered |= newly_rec

    final_surviving = surviving | recovered
    perf_final = capacity0[final_surviving].sum() / capacity0.sum()

    # Robustness: relative output at the post-shock low point (primary metric; higher = more robust)
    robustness = float(perf_after_shock)
    # Cascade-path identification: the propagation sequence stitched across failure rounds
    failure_order = [c for rnd in failure_rounds for c in rnd]
    return {
        "target_bed": target_bed,
        "achieved_bed": current_bed(rewired, battery_hub, ev_node),
        "Robustness": robustness,
        "perf_final": float(perf_final),
        "n_failed": int(failed.sum()),
        "n_total": n,
        "failure_rounds": failure_rounds,   # newly failed nodes per round (cascade-path ID)
        "failure_order": failure_order,     # failure order
    }


# ------------------------------------------------------------------
# Circular (recycling) edge contribution analysis
# ------------------------------------------------------------------
def circular_edge_contribution(nodes: pd.DataFrame, edges: pd.DataFrame, battery_hub: str,
                               ev_node: str, target_bed: float, params: SimParams,
                               n_repeats: int = 30) -> Dict:
    """
    Contribution of circular (recycling-tier, Tier == 'RC') edges to resilience: the Robustness
    difference between the full network and a network with all recycling edges removed, under matched
    seeds. A positive difference means recycling connectivity is net-stabilising; negative means it
    transmits fragility. (Illustrated on synthetic data; not a reproduction of published numbers.)
    """
    rc_nodes = set(nodes.loc[nodes["Tier"] == "RC", "Node_Code"].astype(str))
    s = edges["Source_Code"].astype(str)
    t = edges["Target_Code"].astype(str)
    edges_no_rc = edges[~(s.isin(rc_nodes) | t.isin(rc_nodes))].copy()

    with_rc, without_rc = [], []
    for r in range(n_repeats):
        with_rc.append(simulate_once(nodes, edges, battery_hub, ev_node, target_bed, params, r)["Robustness"])
        without_rc.append(simulate_once(nodes, edges_no_rc, battery_hub, ev_node, target_bed, params, r)["Robustness"])
    with_rc = np.array(with_rc) * 100.0
    without_rc = np.array(without_rc) * 100.0
    return {
        "target_bed": target_bed,
        "robustness_with_recycling_pct": float(with_rc.mean()),
        "robustness_without_recycling_pct": float(without_rc.mean()),
        "recycling_contribution_pp": float(with_rc.mean() - without_rc.mean()),
        "n_recycling_edges_removed": int(len(edges) - len(edges_no_rc)),
        "n_repeats": n_repeats,
    }


# ------------------------------------------------------------------
# BED scan (Robustness-vs-BED curve)
# ------------------------------------------------------------------
def bed_scan(nodes: pd.DataFrame, edges: pd.DataFrame, battery_hub: str, ev_node: str,
             bed_grid: List[float], params: SimParams, n_repeats: int = 30) -> pd.DataFrame:
    """Repeat simulations over a BED grid; return the mean/std Robustness at each BED point."""
    rows = []
    for bed in bed_grid:
        robs = []
        for r in range(n_repeats):
            res = simulate_once(nodes, edges, battery_hub, ev_node, bed, params, simulation_id=r)
            robs.append(res["Robustness"] * 100.0)
        robs = np.array(robs)
        rows.append({
            "BED": bed,
            "Robustness_pct_mean": float(robs.mean()),
            "Robustness_pct_std": float(robs.std(ddof=1)) if len(robs) > 1 else 0.0,
            "n_repeats": n_repeats,
        })
    return pd.DataFrame(rows)
