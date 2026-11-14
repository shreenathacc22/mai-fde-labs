# What each disputed labelling rule does to the triage score

*`python scripts/readout_impact.py --write` · nothing in the frozen set is changed*

Each B column applies labeller B's reading of one rule (from `golden/DISAGREEMENTS.md`, made general so it applies to any output) on top of the frozen scorer. The ops lead picks one reading per rule at the readout; see `reports/readout-decisions.md` for the recommendation on each.

| Outputs | Triage cases | A (frozen scorer) | B: category-never-set | B: same-policy-family | B: priority-normal-high | B: honest-null | B on all four |
|---|---|---|---|---|---|---|---|
| Rules alone (`labs/_triage.py`), all 120 | 120 | 111 (92%) | 118 (+7) | 111 | 111 | 111 | 118 (98%) |
| Baseline model, frozen run, all 120 | 120 | 38 (32%) | 42 (+4) | 45 (+7) | 39 (+1) | 81 (+43) | 93 (78%) |
| Wedge before the triage rules (30-case sample) | 20 | 6 (30%) | 6 | 6 | 6 | 6 | 6 (30%) |
| Wedge with the triage rules (30-case sample) | 20 | 16 (80%) | 18 (+2) | 16 | 16 | 16 | 18 (90%) |
| Wedge with the triage rules (30 more triage cases) | 30 | 24 (80%) | 27 (+3) | 24 | 24 | 24 | 27 (90%) |
