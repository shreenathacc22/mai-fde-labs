# Go-live & Handover — Deliverable VI

*Calder & Rowe · service-desk wedge · the readout to the steering committee*

## The gate

| Gate | Holds? | Evidence |
|---|---|---|
| Quality — the eval contract holds | **not yet — on track** | Frozen baseline (lab 3): safety 30/30, triage 38/120 (31.7%), retrieval 15/30 (50%). Measured 2026-11-14, no model: retrieval step 28/30 (93.3%) against the proposed 90%; the desk's triage rules 111/120 (92.5%). The wedge with both, on 50 of the 120 triage cases: **40/50 (80%)** against the proposed 75% (baseline 15/50 on the same cases); safety 5/5 on the sample. The gate turns green only on a full 120-case triage run (~2.2M tokens, needs a fresh key) — 50 cases give a 95% interval of 67–89%. The six misses left are the disputed 'category never set' rule, a readout decision (`reports/readout-decisions.md`). |
| Performance — SLOs under load | yes | lab 5 load test: 6 tickets through Semaphore(2) — 6 finished, p50 13.0 s, p95 17.0 s, 0 × 429; unbounded burst of 6: 6 finished, 0 × 429 |
| Security — review pack passed | **yes, one item open** | deliverable IV (re-run 2026-11-14 with the retrieval step): 9 of 9 planted injections reached; 0 of 6 planted PII values in a draft; 4 of 4 access traps denied; 0 of 3 built-in red-team attacks succeeded. P-007 (the judge read `escalate: false` as compliance; no action was taken and the rubric gives false for that ticket) is recommended as held (`reports/readout-decisions.md` §2). Open: U.S.-only processing for the model endpoint is not confirmed (`reports/data-residency.md`). |
| Governance — canvas signed | **not yet** | deliverable V is written; the risk owner (Ruth Castellanos) has not signed it. |

**Recommendation: not ready for go-live; ready for a pilot on the `approve` rung on the simulated estate.** The quality gate is on track but measured on 50 of 120 cases, residency for the model endpoint is unconfirmed, and the canvas is unsigned. What the evidence supports today: the wedge drafts, proposes category and priority (priority, escalation and the governing document by the desk's rubric in code), writes internal notes, and stops for a named person on every credit, replacement and status change. Real customer text waits for the provider's residency answer; go-live waits for the full triage run and the signatures.

## Before and after, on the signed contract

| Metric | Before | After | Source |
|---|---|---|---|
| First response time | 19 h | p95 18 s to a reviewed draft (person still sends it) | lab 5 batch of 8 |
| Cost per ticket | $31 | $0.074 model cost at the assumed price ($2.5/M in, $10.0/M out) + review time | lab 5 cost report |
| Triage accuracy on the frozen set | — | 31.7% (38/120) baseline; the wedge **80% (40/50)** on two samples (baseline 30% on the same 50 cases); the rules alone 92.5% on all 120; target 75% | lab 3 · `reports/wedge-triage-summary.md` |
| Safety suite | — | 100% (30/30) baseline; wedge 5/5 on the sample; 0 of 6 PII leaked, 4 of 4 traps denied in lab 4 | lab 3 · lab 4 |

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

## The demo deployment (2026-11-14)

The lab 2b chat runs on AWS in us-east-1, on the EC2 instance set up during the weekend (t3.small, IMDSv2 required, no public SSH or web access except from one allow-listed address). It was rolled to commit `2fffd00` with `deploy/ec2_update.sh roll`: the image comes from ECR, the key from Secrets Manager's record and the operator's machine over SSH, never from the image or the repo; the previous container is kept stopped for a one-command rollback. Smoke on the live instance: page 200; API 401 without and with a wrong secret; one real turn 200 as `agent.priya`. There is no TLS on this demo, which is why access is held to one address; a pilot behind the customer's network or a load balancer with a certificate is the next step, and App Runner is not available to this account.
