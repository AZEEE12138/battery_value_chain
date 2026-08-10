# Data Dictionary — Synthetic De-identified Dataset

All three files below are **synthetic**. Node identities are neutral codes, sector
labels are generic English descriptors unrelated to any real-world classification system,
and all numerical values are freshly generated from a fixed random seed
(`scripts/generate_synthetic_data.py`, `SEED = 20260806`). They contain no real or
confidential information and are not a reproduction of the paper's source data.

---

## `nodes_synthetic.csv`

| Column | Type | Description |
|---|---|---|
| `Node_Code` | string | Neutral node identifier (`S001`…). No real entity mapping. |
| `Tier` | string | Generic supply-chain tier: `RM` (raw material), `PM` (processed material), `CP` (component), `CE` (cell), `AP` (application), `RC` (recycling). |
| `Sector_Label_EN` | string | Generic English sector descriptor. Not tied to any real-world classification code. |
| `Out_Degree` | int | Number of outgoing edges (computed from synthetic edges). |
| `In_Degree` | int | Number of incoming edges. |
| `Out_Weight` | float | Sum of outgoing edge weights (synthetic units). |
| `In_Weight` | float | Sum of incoming edge weights (synthetic units). |
| `Is_Battery_Hub` | bool | `True` for the single battery-manufacturing hub node (BED numerator/denominator role). |
| `Is_EV_Node` | bool | `True` for the single electric-vehicle application node (BED numerator role). |

## `edges_synthetic.csv`

| Column | Type | Description |
|---|---|---|
| `Source_Code` | string | Source node (`S…`). |
| `Target_Code` | string | Target node (`S…`). |
| `Category` | string | Generic edge type: `forward_supply`, `battery_to_ev`, `battery_to_application`, `battery_to_component`, `recycling_loop`, `end_of_life_return`, `indirect`. |
| `Weight` | float | Directed edge weight (synthetic units). |

## `bed_scenarios_synthetic.csv`

| Column | Type | Description |
|---|---|---|
| `Year` | int | Calendar year label (2015–2035). Used only as an axis label mapping each year's projected BED onto the stress-test surface; it is **not** a simulation time step. |
| `BED_optimistic_pct` | float | Synthetic optimistic-scenario BED (%). |
| `BED_conservative_pct` | float | Synthetic conservative-scenario BED (%). |
| `Scenario_Note` | string | Generic note (historical vs projection; synthetic). |
| `Source` | string | Generic descriptor. No real institutional report names. |
