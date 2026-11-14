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

**The wedge, measured 2026-11-14** (`scripts/eval_wedge.py`, approvals declined), against the baseline on exactly the same cases. Full account: `reports/wedge-triage-summary.md`.

| Run | Triage, baseline same cases | Triage, wedge (structural) | Wedge (judge) | Retrieval | Safety |
|---|---|---|---|---|---|
| Lab 3's 30-case sample, retrieval step only | 3/20 | 6/20 (30%) | 6/20 | 4/5 (= baseline) | 5/5 |
| Same sample, with the desk's triage rules (`labs/_triage.py`) | 3/20 | **16/20 (80%)** | 16/20 | 4/5 | **5/5** |
| 30 more triage cases (`Random(2026)`), with the rules | 12/30 | **24/30 (80%)** | 24/30 | — | — |
| **Both, 50 of the 120 triage cases** | **15/50 (30%)** | **40/50 (80%)** | 40/50 | — | 5/5 (sample) |

The two earlier gaps are closed in code and measured without a model: the retrieval step puts the governing document in the top 3 for **28 of 30** retrieval cases (93.3%, was 50%; `reports/retrieval-measurement.md`), and the desk's triage rules alone get **111 of 120** triage cases right (92.5%; `reports/triage-measurement.md`). On 50 triage cases the wedge is at 80% against the proposed 75%. After those runs the rubric's priority, escalation and document were also enforced in code; the four cases that failed for those reasons then passed one by one (projected 44/50, not yet measured as a run). The six misses left are all the disputed "category never set" rule (D1 in `reports/readout-decisions.md`).

**Not yet the contract's number:** the triage row in the table at the top moves only on a run of all 120 triage cases (~2.2M tokens; the key holds ~0.15M). Until then the wedge's 80% is a 50-case measurement with a 95% interval of about 67–89%.

## The regression gate

A change ships only if every suite holds or improves on the frozen set. Who runs it, where it runs, what happens on a fail:

`gate(before, after)` in `labs/lab_3_eval_contract.py`, run by the FDE on every change before it reaches the desk, in CI on the frozen replay. On a fail the change does not ship and the failing case ids go back to the author. Demonstrated today: the replay passes against itself; a degraded copy fails with: triage dropped 31.7% → 25.8%; safety dropped 100.0% → 96.7%; safety is 96.7% — must be 100%.

*Sign-off:* Customer ops lead: Dana Okafor ____________ · FDE: Shreenath Shetty ____________ · date ________ (unsigned: simulated customer)
