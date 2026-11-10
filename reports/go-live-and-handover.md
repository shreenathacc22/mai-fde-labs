# Go-live & Handover — Deliverable VI

*Calder & Rowe · service-desk wedge · the readout to the steering committee*

## The gate

| Gate | Holds? | Evidence |
|---|---|---|
| Quality — the eval contract holds | **no** | lab 3 report: safety 30/30 (100%, holds); triage 38/120 (31.7%) against a proposed 75%; retrieval 15/30 (50%) against a proposed 90%. Most triage misses are the policy field, which is the retrieval problem showing up in the triage score. The retrieval step was rebuilt on 2026-11-09 (desk map in code, 93.3% top-3 on the retrieval cases, measured without a model); the gate stays red until the wedge is re-run on the frozen set. |
| Performance — SLOs under load | yes | lab 5 load test: 6 tickets through Semaphore(2) — 6 finished, p50 13.0 s, p95 17.0 s, 0 × 429; unbounded burst of 6: 6 finished, 0 × 429 |
| Security — review pack passed | **yes, one item open** | deliverable IV: 9 of 9 planted injections reached, 0 followed; 0 of 6 planted PII values in a draft; 4 of 4 access traps denied. Open: the model endpoint must be confirmed as U.S.-only before real customer data is used. |
| Governance — canvas signed | **not yet** | deliverable V is written; the risk owner (Ruth Castellanos) has not signed it. |

**Recommendation: not ready for go-live.** Two of four gates do not hold. What the evidence supports today is a pilot on the `suggest` rung only: the system drafts and proposes, writes nothing, and a person does everything else, while retrieval is fixed and the eval contract is re-run.

## Before and after, on the signed contract

| Metric | Before | After | Source |
|---|---|---|---|
| First response time | 19 h | p95 18 s to a reviewed draft (person still sends it) | lab 5 batch of 8 |
| Cost per ticket | $31 | $0.074 model cost at the assumed price ($2.5/M in, $10.0/M out) + review time | lab 5 cost report |
| Triage accuracy on the frozen set | — | 31.7% (38/120) for the baseline agent; target 75% | lab 3 |
| Safety suite | — | 100% (30/30) | lab 3 |

## Where it runs

Cloud · on-prem · air-gapped — and why (Ruth's residency constraint): **on-prem for everything that touches customer records.** The wedge and its MCP server run beside HelpTrack on the Dallas office server, so tickets, orders and the audit log never leave it in bulk. The one thing that leaves is the text of the ticket being drafted, sent to the model endpoint per call; that endpoint must be pinned to a U.S. region and confirmed in writing with the provider. The lab runs used the class proxy, which is not confirmed as U.S.-only, so no real customer data should go through it.

## SLOs and cost controls

| SLO | Target | Measured |
|---|---|---|
| p95 latency per draft | 60 s | 17.5 s sequential, 17.0 s with 6 queued through Semaphore(2) |
| Availability | 99.5% in desk hours | not measured in a lab run; 0 rate-limit hits in the load test |
| Spend cap per day | 220,000 tokens per batch (Budget in lab 5) ≈ 8 tickets | cap fired at ticket 9 of the batch |

## The runbook (so they can run it without you)

1. How to switch it off: stop the wedge process; the estate and HelpTrack are untouched — the desk works as before
2. On-call path: Dana Okafor (desk lead) first; the FDE during the pilot for anything the system did wrong; Ruth Castellanos for access, customer data or an unapproved write
3. Who owns the golden set: Dana Okafor, the desk lead, not the FDE
4. How a complaint becomes a test case: the desk files the ticket id and what the right answer was; it is added to `golden/cases.jsonl` with `--unfreeze`, which re-freezes the set and logs the change in `FREEZE_LOG.md`
5. How to rotate the key / token: replace OPENAI_API_KEY in .env on the box, restart; the estate's own identity is per-user (`--as`), nothing to rotate there
6. Training done for the desk team: not done yet. Planned: one hour with Tomas, Keisha and Bill on reading a draft, overturning it, and what the system will never do (credits, replacements, closing a ticket)

*Steering committee:* operations: Dana Okafor ______ · finance: Marcus Lindqvist ______ · security: Ruth Castellanos ______ · risk: Ruth Castellanos ______ · date ______ (unsigned: simulated customer)

*Prepared by Shreenath Shetty (FDE). Numbers measured by `labs/lab_5_hitl_operate.py` on 2026-11-08 against the class model: a batch of 8 tickets as agent.priya (the token budget stopped it before ticket 9, as designed) and two load rounds of 6. The $0.074 per ticket uses an assumed price, not a quoted one.*
