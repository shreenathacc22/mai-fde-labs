# The Eval Contract — Deliverable III

*Calder & Rowe · service-desk wedge · filled in during Lab 3*

The definition of "done" both sides sign **before the system is good**, so it cannot move.

## The golden set

| | |
|---|---|
| Source | the customer's own tickets (`estate/data/tickets.json`), expected labels derived by the rules in `golden/build_golden.py`; two labellers' verdicts on the frozen reference run |
| Size | 180 cases: 120 triage · 30 retrieval · 30 safety |
| Frozen on | 2026-10-28 (by the kit); hash re-verified unchanged on 2026-11-14 · sha256 of `golden/cases.jsonl`: `77f232962a2a00b52b37c0ec39498be12cb2db80987e05607e64e05e4a1aa20e` |
| Who owns it after go-live | Dana Okafor, operations lead for the service desk (proposed; the desk lead, not the FDE) |
| How a complaint becomes a case | the desk files the ticket id and what the right answer was; it is added to `cases.jsonl` with `--unfreeze`, logged in `FREEZE_LOG.md` |

## The judge

| | |
|---|---|
| Judge model and prompt | the class model via the proxy; prompt `JUDGE` in `labs/lab_3_eval_contract.py`, one call per case, JSON pass/fail with reason |
| Agreement with labeller A | 100.0% (κ 1.0) on a 40-case sample |
| Agreement with labeller B | 72.5% (κ 0.481) on the same sample |
| Labeller A vs labeller B | 87.8% on all 180 (κ 0.759); 72.5% on the sample (the ceiling: a judge cannot be more right than the people) |
| What the judge numbers show | Calibrated on 2026-11-14 on the full 40-case sample with the current rubric: the judge agrees with labeller A on every case (κ 1.0) and with labeller B on 72.5% (κ 0.481); A and B agree with each other on 72.5% of the same sample. So the judge has taken labeller A's reading wherever A and B differ — the kit's own warning: that is a rule to settle at the readout, not a judge to trust on those cases. The earlier runs (10 cases on 2026-11-01; 14 cases on 2026-11-08, cut short by the key budget) are superseded. |
| Cases the labellers disagreed on | listed in `golden/DISAGREEMENTS.md` — settled at the readout by the ops lead choosing a reading per rule; the rule then goes into the rubric and the set is re-frozen |

## Acceptance criteria

| Suite | Today | Must reach | Error budget |
|---|---|---|---|
| Triage (category + priority + policy + escalate) | 31.7% (38/120), baseline agent | 75% (proposed) | 5 points |
| Retrieval (right policy in top-3) | 50.0% (15/30), baseline agent | 90% (proposed) | 3 points |
| Safety (injection · PII · access) | 100.0% (30/30), baseline agent | **100%** | **none** |

**"Today" is the kit's frozen reference run of the plain baseline agent**, scored structurally. It is the number to beat, not the wedge's score.

**The wedge, measured 2026-11-14** (`scripts/eval_wedge.py`, lab 3's fixed 30-case sample, approvals declined, `reports/wedge-eval.md`), against the baseline on exactly the same cases:

| Suite | Baseline, same cases | Wedge (structural) | Wedge (judge) |
|---|---|---|---|
| Triage | 3/20 (15%) | **6/20 (30%)** | 6/20 |
| Retrieval | 4/5 | 4/5 | 4/5 |
| Safety | 5/5 | **5/5** | 4/5 (one empty draft on a masked-PII case) |

The retrieval step on its own, measured on all 30 retrieval cases without a model (`reports/retrieval-measurement.md`): governing document in the top 3 for **28 of 30 (93.3%)** against 15 (50%) for the plain search. The wedge is now shown the right document; what still fails triage is the model's reading of the desk's rules — 11 of the 14 remaining triage misses on the sample are **priority** (high where the rubric says normal, normal where it says low), and three are address-update tickets called billing where the golden set says other. That is a prompt-and-rubric problem, and the next thing to fix.

A full 180-case wedge run (~4.8M tokens) has not been made; the contract rows above move when it is.

## The regression gate

A change ships only if every suite holds or improves on the frozen set. Who runs it, where it runs, what happens on a fail:

`gate(before, after)` in `labs/lab_3_eval_contract.py`, run by the FDE on every change before it reaches the desk, in CI on the frozen replay. On a fail the change does not ship and the failing case ids go back to the author. Demonstrated today: the replay passes against itself; a degraded copy fails with: triage dropped 31.7% → 25.8%; safety dropped 100.0% → 96.7%; safety is 96.7% — must be 100%.

*Sign-off:* Customer ops lead: Dana Okafor ____________ · FDE: Shreenath Shetty ____________ · date ________ (unsigned: simulated customer)
