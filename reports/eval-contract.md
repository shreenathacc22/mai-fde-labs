# The Eval Contract — Deliverable III

*Calder & Rowe · service-desk wedge · filled in during Lab 3*

The definition of "done" both sides sign **before the system is good**, so it cannot move.

## The golden set

| | |
|---|---|
| Source | the customer's own tickets (`estate/data/tickets.json`), expected labels derived by the rules in `golden/build_golden.py`; two labellers' verdicts on the frozen reference run |
| Size | 180 cases: 120 triage · 30 retrieval · 30 safety |
| Frozen on | 2026-10-28 (by the kit); hash re-verified unchanged on 2026-11-08 · sha256 of `golden/cases.jsonl`: `77f232962a2a00b52b37c0ec39498be12cb2db80987e05607e64e05e4a1aa20e` |
| Who owns it after go-live | Dana Okafor, operations lead for the service desk (proposed; the desk lead, not the FDE) |
| How a complaint becomes a case | the desk files the ticket id and what the right answer was; it is added to `cases.jsonl` with `--unfreeze`, logged in `FREEZE_LOG.md` |

## The judge

| | |
|---|---|
| Judge model and prompt | the class model via the proxy; prompt `JUDGE` in `labs/lab_3_eval_contract.py`, one call per case, JSON pass/fail with reason |
| Agreement with labeller A | 100.0% (κ 1.0) on 14 cases — **partial, not a calibration**: the run was meant to judge 40 and stopped at 14 when the class practice key reached its token limit |
| Agreement with labeller B | 64.3% (κ 0.34) on the same 14 cases |
| Labeller A vs labeller B | 87.8% on all 180 (κ 0.759); 64.3% on the sample (the ceiling: a judge cannot be more right than the people) |
| What the judge numbers do and do not show | All 14 judged cases were triage cases, so the judge has not been checked on retrieval or safety with the current rubric. The earlier run (2026-11-01, 10 cases, previous rubric) gave 80.0% (κ 0.545) with A and 60.0% (κ 0.286) with B. Neither run reaches the κ 0.75 the session set as the bar for a proof of concept. **The judge is not calibrated yet**: rerun `python labs/lab_3_eval_contract.py --judge-n 40` with a fresh key, and until then trust the structural scores below, which need no judge. |
| Cases the labellers disagreed on | listed in `golden/DISAGREEMENTS.md` — settled at the readout by the ops lead choosing a reading per rule; the rule then goes into the rubric and the set is re-frozen |

## Acceptance criteria

| Suite | Today | Must reach | Error budget |
|---|---|---|---|
| Triage (category + priority + policy + escalate) | 31.7% (38/120), baseline agent | 75% (proposed) | 5 points |
| Retrieval (right policy in top-3) | 50.0% (15/30), baseline agent | 90% (proposed) | 3 points |
| Safety (injection · PII · access) | 100.0% (30/30), baseline agent | **100%** | **none** |

**Retrieval fix, measured 2026-11-09 without a model:** the wedge and the lab 2b policy specialist now have a `suggest_policies` step that applies the desk's own ticket-to-document map in code (`labs/_retrieval.py`) before falling back to the text search. On the 30 retrieval cases the governing document is in the top 3 for **28 (93.3%)** against 15 (50%) for the plain search, and for 94.3% of all 559 tickets with a nameable document (`reports/retrieval-measurement.md`). The retrieval row above still shows the frozen baseline: the contract moves only when the wedge is re-run on the frozen set with a fresh key, which also tests whether triage follows.

"Today" is the kit's frozen reference run of the plain baseline agent, scored structurally (no judge). It is the number to beat, not the wedge's score. 73 of the 82 triage misses are the policy field, and 53 of those are tickets whose governing document was not in the three search hits, so the first fix is retrieval. The contract does not hold today, and the go-live page says so.

## The regression gate

A change ships only if every suite holds or improves on the frozen set. Who runs it, where it runs, what happens on a fail:

`gate(before, after)` in `labs/lab_3_eval_contract.py`, run by the FDE on every change before it reaches the desk, in CI on the frozen replay. On a fail the change does not ship and the failing case ids go back to the author. Demonstrated today: the replay passes against itself; a degraded copy fails with: triage dropped 31.7% → 25.8%; safety dropped 100.0% → 96.7%; safety is 96.7% — must be 100%.

*Sign-off:* Customer ops lead: Dana Okafor ____________ · FDE: Shreenath Shetty ____________ · date ________ (unsigned: simulated customer)
