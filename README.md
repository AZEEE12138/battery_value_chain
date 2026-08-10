# Battery Value-Chain Resilience — Public Code & De-identified Data Release

This repository accompanies the manuscript on how terminal-market (electric-vehicle)
lock-in affects the resilience of a battery value chain. It provides a **clean,
self-contained reference implementation** of the analysis pipeline together with a
**synthetic, de-identified example dataset**, so that readers can inspect the data
schema, run the code, and understand the methodology.

---

## ⚠️ Important: what this release is (and is not)

**Confidentiality first.** The analyses in the paper are built on inter-firm
transaction records that are commercially sensitive and access-restricted. To protect
that confidential source while still supporting transparency, this public release does
**not** contain any raw, real, or reverse-derivable data.

| Aspect | Status in this release |
|---|---|
| Raw inter-firm transaction records | **Not included** — restricted, available from the corresponding author subject to the data provider's conditions |
| Node / edge tables | **Synthetic**: all node identities are neutral codes (`S001`, `S002`, …); sector labels are generic English descriptors that do **not** correspond to any real-world classification system; all numerical weights are **freshly generated from a fixed random seed** |
| Annual BED scenario table | **Synthetic** trend lines; source column is a generic descriptor, not real institutional reports |
| Simulation / analysis code | Faithful **reference implementation** of the methods in the manuscript, rewritten for public release |
| Random-seed scheme | Documented: `seed = base_seed + simulation_id` |

**This example dataset is not intended to reproduce the exact numbers in the published
figures.** It is provided to demonstrate (a) the data structure and (b) that the code
runs end-to-end and produces the qualitative behaviour described in the paper (e.g.
resilience declining as BED increases). Because the data are synthetic, running the
code here yields illustrative — not published — values.

Anyone re-running `scripts/generate_synthetic_data.py` will regenerate exactly the same
synthetic example (fixed seed); the synthetic data therefore carry **no** confidential
information and expose **no** real commercial relationship.

---

## Repository layout

```
battery_value_chain_release/
├── README.md                     # this file
├── LICENSE                       # license for code and synthetic data
├── EDGE_SELECTION_RULES.md       # de-identified deterministic edge-selection rules
├── requirements.txt              # Python dependencies
├── config/
│   └── parameters.yaml           # default model parameters (tau, beta, shock, seed)
├── data/
│   ├── nodes_synthetic.csv       # synthetic node table (neutral codes)
│   ├── edges_synthetic.csv       # synthetic directed weighted edges
│   ├── bed_scenarios_synthetic.csv  # synthetic annual BED scenario table
│   └── DATA_DICTIONARY.md        # column-by-column description
├── src/
│   └── model.py                  # reference implementation of the methods
├── scripts/
│   ├── generate_synthetic_data.py       # regenerates the synthetic dataset (fixed seed)
│   ├── run_bed_scan.py                  # BED-scan demonstration
│   └── run_cascade_and_circular_demo.py # cascade-path identification + circular-edge contribution
└── outputs/                      # generated results (created on run)
```

## Quick start

```bash
pip install -r requirements.txt

# (optional) regenerate the synthetic example dataset
python scripts/generate_synthetic_data.py

# 1) BED scan → Robustness-vs-BED curve
python scripts/run_bed_scan.py

# 2) cascade-path identification + circular (recycling) edge contribution
python scripts/run_cascade_and_circular_demo.py
```

Outputs (`outputs/bed_scan_results.csv`, `outputs/bed_scan_demo.png`) illustrate the
Robustness-vs-BED relationship on the synthetic network. The demo script prints the cascade failure
order and the recycling-edge contribution.

## What this release covers (mapping to the analyses in the paper)

| Analysis in the paper | Where in this release |
|---|---|
| Deterministic edge-selection rules | `EDGE_SELECTION_RULES.md` |
| BED scan (Robustness vs BED) | `scripts/run_bed_scan.py` + `src/model.bed_scan` |
| Cascade-path identification | `src/model.simulate_once` (`failure_rounds`/`failure_order`) + demo script |
| Circular-edge (recycling) contribution | `src/model.circular_edge_contribution` + demo script |
| Fixed random-seed scheme | `seed = base_seed + simulation_id` (see `config/parameters.yaml`) |

## Method summary (see `src/model.py` for details)

- **BED (Battery–EV Dependency)** = weight of the battery hub → EV edge divided by the
  battery hub's total outgoing weight.
- **Controlled rewiring** adjusts the battery→EV share to a target BED while conserving
  the battery hub's total outgoing weight; remaining out-edges are rescaled
  proportionally.
- **Shock & cascade**: an EV-demand shock imposes a first-round loss on the battery hub
  equal to `BED × shock_intensity`; node failure follows a sigmoid function
  `P_fail = 1/(1+exp(-beta·(loss − tau)))`, so failure probability reaches 0.5 exactly
  when the profit loss equals `tau`.
- **Recovery** proceeds probabilistically and does not re-invoke the failure sigmoid.
- **Robustness** is the relative surviving output at the post-shock low point.

## Data & code availability statement (as intended for the manuscript)

> The raw inter-firm transaction records used to construct the battery value-chain
> network contain commercially sensitive information and remain restricted; requests
> should be directed to the corresponding author, subject to the data provider's
> conditions. To support transparency and code reuse, a de-identified synthetic example
> dataset (with neutral node identifiers and freshly generated numerical values) and a
> self-contained reference implementation of the network construction, controlled BED
> rewiring, cascading-failure and recovery simulation, and BED-scan analysis — together
> with the fixed random-seed scheme (`seed = base_seed + simulation_id`) — are provided
> in this repository. The synthetic dataset is intended to demonstrate the data schema
> and code functionality and is not a reproduction of the confidential source data.

## License

See `LICENSE`. Code and synthetic data are released for academic transparency and reuse.
The synthetic data contain no real or confidential information.
