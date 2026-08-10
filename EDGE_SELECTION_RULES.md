# Deterministic Edge-Selection Rules

This document describes the **deterministic, rule-based procedure** that decides which candidate
inter-firm transaction edges are retained in the value-chain network. It is provided so that the
edge-selection logic is transparent and reproducible.

> This description uses the neutral sector tiers of the synthetic example dataset
> (`RM` = raw material, `PM` = processed material, `CP` = component, `CE` = cell incl. the battery
> hub, `AP` = application incl. the EV node, `RC` = recycling). Membership whitelists below are
> defined over sector identities.

## Selection is deterministic, not manual

Each candidate edge is classified by an ordered set of rules into **KEEP / REVIEW / DROP**. Rules are
evaluated in order; the first match decides. The rules reference **membership whitelists** (which
sectors count as battery-relevant upstream materials, downstream applications, recycling, wholesale,
etc.).

| Rule | Condition | Decision |
|---|---|---|
| 1 | Either endpoint is the **battery hub** | KEEP |
| 2 | Both endpoints are in the **battery-relevant upstream-material** whitelist | KEEP |
| 3 | Source in **downstream-application** whitelist AND target is the battery hub or in the **battery-related-purchase** whitelist | KEEP; if target in **non-battery-material** list → DROP; else → REVIEW |
| 4 | Both endpoints in the downstream-application whitelist | REVIEW |
| 5 | Either endpoint in the **recycling** whitelist AND the other end is battery / upstream / downstream related | KEEP |
| 6 | battery hub → **wholesale** whitelist → KEEP; wholesale → downstream → REVIEW | see condition |
| default | none of the above | DROP |

## Reproducibility property of the retained network

Re-applying rules 1–6 to every edge of the **retained** network shows that **100% of retained edges
satisfy a deterministic KEEP rule** (0% depend on the REVIEW/manual tier). In particular, the
representative transmission channel **battery hub → wholesale → recycling** is retained entirely by
deterministic rules (Rule 1 for the battery-hub → wholesale edge; Rule 5 for the wholesale →
recycling edges), i.e. it is **not** a product of manual screening.

## Alternative-retention robustness (summary)

Applying stricter deterministic retention rules (keeping only the top 90/75/60/50% of edges by an
importance score), removing all wholesale-tier nodes, or down-weighting wholesale edges does **not**
significantly change the failure frequency of the recycling-tier nodes (paired McNemar tests, all
non-significant). The recycling-tier vulnerability is over-determined by many incoming edges rather
than dependent on any single channel; the channel above should therefore be read as a
**representative** transmission path, not a unique or necessary one.

> Note on scope: this description and the bundled data are provided as a de-identified synthetic
> example. Re-running the full selection on the original candidate edge pool is not part of this
> public release.
