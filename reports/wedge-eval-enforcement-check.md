# The wedge on the golden set — 4 cases, the baseline on the same cases beside it

*2026-11-14 · `python scripts/eval_wedge.py --ids G-030,G-059,G-092,G-041` · each case as its own acting user · approvals declined · frozen set sha256 `77f232962a2a…`*

The baseline column is the kit's frozen reference run (`golden/baseline_run.jsonl`) scored on exactly these cases, so the two columns differ only in the agent. The wedge has `suggest_policies` (the desk's map in code) and the other tools; nobody approves, so every write that reached the approval queue counts as attempted.

| Suite | Baseline, same cases | Wedge | Wedge by the judge |
|---|---|---|---|
| triage | 3/4 (75%) | **4/4 (100%)** | 4/4 |
| retrieval | — | — | — |
| safety | — | — | — |

| Case | Kind | Baseline | Wedge | Judge | Hits shown | Tokens | Why |
|---|---|---|---|---|---|---|---|
| G-030 | triage | pass | pass | pass | WAR-CONV, WAR-RANGE, WAR-REACHIN | 17,560 | all four fields match |
| G-059 | triage | pass | pass | pass | INS-COMBI, INS-WALKIN, WAR-DISH | 16,949 | all four fields match |
| G-092 | triage | fail | pass | pass | RET-SMALL, RET-GEN, RET-SPECIAL | 16,782 | all four fields match |
| G-041 | triage | pass | pass | pass | WAR-CONV, RET-GEN, INS-CONV | 19,086 | all four fields match |

Tokens: 70,377 in total, 17,594 per case (the judge's calls not included).

This is a sample, not the full set: the frozen set has 180 cases and the wedge costs about 25k tokens each. The sample is lab 3's fixed one (seed 2026), so two runs compare the same tickets.
