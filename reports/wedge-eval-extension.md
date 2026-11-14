# The wedge on the golden set — 30 cases, the baseline on the same cases beside it

*2026-11-14 · `python scripts/eval_wedge.py --ids G-001,G-002,G-011,G-013,G-015,G-017,G-018,G-030,G-032,G-034,G-036,G-040,G-045,G-056,G-059,G-062,G-063,G-070,G-075,G-076,G-084,G-085,G-087,G-089,G-090,G-092,G-093,G-097,G-103,G-119` · each case as its own acting user · approvals declined · frozen set sha256 `77f232962a2a…`*

The baseline column is the kit's frozen reference run (`golden/baseline_run.jsonl`) scored on exactly these cases, so the two columns differ only in the agent. The wedge has `suggest_policies` (the desk's map in code) and the other tools; nobody approves, so every write that reached the approval queue counts as attempted.

| Suite | Baseline, same cases | Wedge | Wedge by the judge |
|---|---|---|---|
| triage | 12/30 (40%) | **24/30 (80%)** | 24/30 |
| retrieval | — | — | — |
| safety | — | — | — |

| Case | Kind | Baseline | Wedge | Judge | Hits shown | Tokens | Why |
|---|---|---|---|---|---|---|---|
| G-001 | triage | fail | pass | pass | PRT-ORDER, PRT-CONSUM, PRT-AVAIL | 19,594 | all four fields match |
| G-002 | triage | fail | pass | pass | PRC-FREIGHT, REG-CENTRAL-WINTER, INS-RANGE | 17,355 | all four fields match |
| G-011 | triage | fail | fail | fail | PRT-ORDER, PRT-CONSUM, PRT-AVAIL | 18,839 | category: got 'parts', expected 'other'; priority: got 'normal', expected 'low'; policy_doc_id: got 'PRT-ORDER', expected 'SLA-STD' |
| G-013 | triage | fail | fail | fail | CRD-ISSUE, CRD-GOODWILL, CRD-REFUND | 16,196 | category: got 'billing', expected 'other'; priority: got 'normal', expected 'low'; escalate: got True, expected False; policy_doc_id: got 'CRD-ISSUE', expected 'SLA-KEY' |
| G-015 | triage | fail | fail | fail | CRD-ISSUE, CRD-GOODWILL, CRD-REFUND | 16,274 | category: got 'billing', expected 'other'; priority: got 'normal', expected 'low'; escalate: got True, expected False; policy_doc_id: got 'CRD-ISSUE', expected 'SLA-STD' |
| G-017 | triage | pass | pass | pass | INS-RANGE, INS-FRYER, INS-ICE | 25,002 | all four fields match |
| G-018 | triage | fail | pass | pass | RET-GEN, RET-SMALL, RET-SPECIAL | 16,992 | all four fields match |
| G-030 | triage | pass | fail | fail | WAR-CONV, WAR-RANGE, WAR-REACHIN | 25,448 | escalate: got True, expected False |
| G-032 | triage | pass | pass | pass | WAR-CONV, WAR-RANGE, WAR-WALKIN | 17,392 | all four fields match |
| G-034 | triage | fail | pass | pass | WAR-RANGE, WAR-DISH, WAR-CONV | 16,874 | all four fields match |
| G-036 | triage | fail | pass | pass | WAR-ICE, WAR-SMALLWARES, WAR-COMBI | 16,457 | all four fields match |
| G-040 | triage | fail | pass | pass | WAR-MIXER, WAR-REACHIN, WAR-DISH | 17,256 | all four fields match |
| G-045 | triage | pass | pass | pass | WAR-REACHIN, WAR-WALKIN, INS-REACHIN | 17,011 | all four fields match |
| G-056 | triage | fail | pass | pass | PRC-FREIGHT, REG-EAST-HOURS, WAR-RANGE | 16,517 | all four fields match |
| G-059 | triage | pass | fail | fail | INS-COMBI, INS-WALKIN, WAR-DISH | 20,298 | policy_doc_id: got 'INS-WALKIN', expected 'INS-COMBI' |
| G-062 | triage | pass | pass | pass | INS-COMBI, INS-ICE, INS-WALKIN | 26,249 | all four fields match |
| G-063 | triage | pass | pass | pass | INS-COMBI, PRT-CONSUM, WAR-COMBI | 16,612 | all four fields match |
| G-070 | triage | fail | pass | pass | PRT-ORDER, PRT-CONSUM, PRT-AVAIL | 16,393 | all four fields match |
| G-075 | triage | pass | pass | pass | PRT-ORDER, PRT-CONSUM, PRT-AVAIL | 16,301 | all four fields match |
| G-076 | triage | fail | pass | pass | PRT-ORDER, PRT-CONSUM, PRT-AVAIL | 16,160 | all four fields match |
| G-084 | triage | fail | pass | pass | CRD-ISSUE, CRD-REFUND, CRD-GOODWILL | 15,887 | all four fields match |
| G-085 | triage | fail | pass | pass | CRD-ISSUE, CRD-REFUND, CRD-GOODWILL | 15,960 | all four fields match |
| G-087 | triage | pass | pass | pass | CRD-ISSUE, CRD-GOODWILL, CRD-REFUND | 16,461 | all four fields match |
| G-089 | triage | pass | pass | pass | CRD-ISSUE, CRD-GOODWILL, CRD-REFUND | 19,684 | all four fields match |
| G-090 | triage | fail | pass | pass | CRD-ISSUE, CRD-GOODWILL, CRD-REFUND | 17,634 | all four fields match |
| G-092 | triage | fail | fail | fail | RET-SMALL, RET-GEN, RET-SPECIAL | 16,082 | policy_doc_id: got 'RET-SPECIAL', expected 'RET-SMALL' |
| G-093 | triage | pass | pass | pass | RET-SMALL, RET-GEN, RET-SPECIAL | 17,858 | all four fields match |
| G-097 | triage | pass | pass | pass | RET-SMALL, RET-GEN, RET-SPECIAL | 19,803 | all four fields match |
| G-103 | triage | fail | pass | pass | SLA-PREF, SLA-STD, SLA-KEY | 18,977 | all four fields match |
| G-119 | triage | fail | pass | pass | PRC-FREIGHT, PRT-ORDER, PRT-CONSUM | 18,796 | all four fields match |

Tokens: 546,362 in total, 18,212 per case (the judge's calls not included).

This is a sample, not the full set: the frozen set has 180 cases and the wedge costs about 25k tokens each. The sample is lab 3's fixed one (seed 2026), so two runs compare the same tickets.
