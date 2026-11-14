# FDE weekend portfolio — Shreenath Shetty

My work from the Modern AI Pro **Forward Deployed Engineer** weekend (Oct 30 – Nov 1, 2026): take a support agent into a simulated customer, Calder & Rowe, and make it useful, safe and measurable there.

This branch is a fork of the course lab kit by Dr. Balaji Viswanathan ([balajivis/mai-fde-labs](https://github.com/balajivis/mai-fde-labs)). The kit, the simulated customer, the golden set and the lab scripts are his. What I added is listed below, and [`README.md`](./README.md) is the kit's own.

**Where it stands:** all six deliverables are written; none is signed, because the customer is simulated. Both engineering gaps the eval contract found are closed in code and measured: the governing document is found 93% of the time (was 50%), and the desk's triage rules alone get 92.5% of the frozen triage cases right. The wedge with both scores **triage 40/50 (80%) against the baseline's 15/50 on the same cases**, above the proposed 75%, with safety 5/5 (2026-11-14). By its own gate it is still **not ready for go-live**: the contract's number needs all 120 triage cases, the model endpoint's U.S. residency is unconfirmed, and nobody can sign for a simulated customer. The chat runs on AWS EC2 for demonstration. What is open is listed under [What is still open](#what-is-still-open).

## What I built

| | Where | What it does |
|---|---|---|
| The three lab 2b decisions | [`labs/lab_2b_multiagent.py`](./labs/lab_2b_multiagent.py) | Routing rules for the router, `needs_person()` for the approval gate, and a hop budget of 3 |
| A PII boundary in code | [`labs/_pii.py`](./labs/_pii.py) | Redacts card numbers, addresses, emails and access codes from the message in, every tool result, and every reply out, so the model never holds them |
| Suggestions on a lookup miss | `labs/lab_2b_multiagent.py` | A mistyped ticket or order id comes back with the closest ids the user is allowed to see, instead of a dead end |
| The lab 2b checks as a command | [`scripts/check_lab2b.py`](./scripts/check_lab2b.py) | Runs the routing, gate and hop-budget checks from the lab guide and writes the result |
| Golden cases through the chat | [`scripts/eval_lab2b.py`](./scripts/eval_lab2b.py), [`scripts/selftest_eval_lab2b.py`](./scripts/selftest_eval_lab2b.py) | Scores the multi-agent chat on the frozen golden set the same way the baseline is scored; the self-test runs it offline with a scripted model |
| The desk's triage rules | [`labs/_triage.py`](./labs/_triage.py), [`scripts/measure_triage.py`](./scripts/measure_triage.py), [`scripts/selftest_triage.py`](./scripts/selftest_triage.py) | Category from the ticket as it arrived, then priority, escalation and the governing document by the desk's rubric — offered to the model, enforced at the write and in the answer, every override recorded. 111/120 on the frozen triage cases with no model; 384/390 on held-out tickets |
| Readout numbers | [`scripts/readout_impact.py`](./scripts/readout_impact.py) | The triage score under each labeller reading, so the readout decides with numbers ([decisions](./reports/readout-decisions.md)) |
| A deploy that keeps secrets out | [`deploy/ec2_update.sh`](./deploy/ec2_update.sh) | Builds `linux/amd64` from a commit, rolls the chat on EC2 with the key over SSH stdin, smoke-tests, rolls back on failure |
| The governing-policy step | [`labs/_retrieval.py`](./labs/_retrieval.py), [`scripts/measure_retrieval.py`](./scripts/measure_retrieval.py), [`scripts/selftest_retrieval.py`](./scripts/selftest_retrieval.py) | The desk's ticket-to-document map in code, offered to the wedge and the lab 2b policy specialist as a read-only `suggest_policies` tool; takes retrieval from 50% to 93% on the golden cases, measured without a model |
| A second product on the same stack | [`edtech/`](./edtech) | A student help desk for a fictional online school: scope enforced in the school's system, grade changes gated on a person, a role-scoped dashboard, 30 checks |

## The six deliverables

| # | Deliverable | What it says |
|---|---|---|
| I | [Engagement Brief](./reports/engagement-brief.md) | The lookup work, not the writing, is what slows the desk. ROI is $46,000 a year against $36,000, which is over the CFO's $25,000 signing limit |
| II | [Integration Map](./reports/integration-map.md) | Eight layers, each marked build, connect or never, with a proposed owner on the customer's side |
| III | [Eval Contract](./reports/eval-contract.md) | 180 frozen cases. Baseline: triage 31.7%, retrieval 50%, safety 100%. Wedge: triage 80% on 50 cases; judge calibrated on 40 (κ 1.0 with A, 0.48 with B) |
| IV | [Security Review Pack](./reports/security-review-pack.md) | 9 of 9 planted injections reached, 0 forbidden actions; 0 of 6 planted PII values leaked; 4 of 4 access traps denied; residency evidence in [data-residency](./reports/data-residency.md) |
| V | [Governance Canvas](./reports/governance-canvas.md) | Who approves what, the autonomy ladder per action, the incident path |
| VI | [Go-live & Handover](./reports/go-live-and-handover.md) | Not ready for go-live; ready for a pilot on the `approve` rung on the simulated estate. Quality on track (80% on 50 cases), residency unconfirmed, canvas unsigned |

The flow on one sheet: [`reports/calder-rowe-flow.svg`](./reports/calder-rowe-flow.svg).

## Measured results

| What | Result | Source |
|---|---|---|
| Latency per draft | p50 14.8 s, p95 17.5 s over 8 tickets | lab 5, 2026-11-08 |
| Under load | 6 tickets at once: all finished, p95 17.0 s, no rate-limit errors | lab 5 |
| Model cost per ticket | about $0.07 at an assumed price, against the customer's $31 | lab 5 |
| Spend cap | stopped the batch before ticket 9 of 10, as designed | lab 5 |
| Approval step | with nobody to approve, the credit was declined and logged | lab 5 |
| Routing | 5 of 5 questions reached the intended specialist, 3 runs out of 3 (after one rule fix the check itself caught) | [`reports/lab2b-checks.md`](./reports/lab2b-checks.md), 2026-11-14 |
| Approval gate | an internal note runs; closing a ticket stops; no credit tool runs (passed 3 of 4 runs; the diagnostics for the odd one are in the report) | same |
| Two-hop question | orders → policy → answer in one turn, a real warranty answer, **12,931 tokens** | same |
| Retrieval (governing document in top 3) | 50% → **93.3%** on the 30 golden retrieval cases; 34% → 94% on all 559 nameable tickets | [`reports/retrieval-measurement.md`](./reports/retrieval-measurement.md), 2026-11-09 |
| The desk's triage rules, no model | **111/120 (92.5%)** on the frozen triage cases; 384/390 agreement with the desk's category on held-out tickets | [`reports/triage-measurement.md`](./reports/triage-measurement.md), 2026-11-14 |
| The wedge on the golden set | triage **40/50 (80%) vs the baseline's 15/50** on the same cases (two samples: 16/20 and 24/30); was 6/20 before the triage rules; retrieval 4/5 = baseline; safety 5/5; 18k tokens per case | [`reports/wedge-triage-summary.md`](./reports/wedge-triage-summary.md), 2026-11-14 |
| Rule enforcement | the four cases the model got wrong for priority, escalation or document pass once the rubric is enforced (projected 44/50, not a full run) | [`reports/wedge-eval-enforcement-check.md`](./reports/wedge-eval-enforcement-check.md) |
| Golden cases through the lab 2b chat (10 chosen cases) | 6/10 structural in each of two runs (not the same six: run-to-run variation); safety 4/4 both times; 19–24k tokens per case. The chat's hop budget of 3 ends 2 of 10 turns before the policy specialist, and the final JSON names no document in 2 more | [`reports/lab2b-eval.md`](./reports/lab2b-eval.md), [first run](./reports/lab2b-eval-first-run.md), 2026-11-14 |
| Judge calibration | 40 cases: agrees with labeller A on all (κ 1.0), with B on 72.5% (κ 0.481), A–B themselves 72.5% on the sample | [`reports/eval-contract.md`](./reports/eval-contract.md), 2026-11-14 |
| Security review, re-run with the retrieval step | 9/9 plants reached; 0/6 PII leaked; 4/4 traps denied; 0/3 red-team attacks succeeded; 1 plant judged "followed" on an `escalate: false` reading, no action taken | [`reports/security-review-pack.md`](./reports/security-review-pack.md), 2026-11-14 |
| Container | `fde-chat` image built (no secrets inside); refuses to start without `CHAT_SECRET`; page 200, API 401 without the secret | 2026-11-09 |
| On AWS | rolled to `2fffd00` on EC2 (us-east-1): page 200; API 401 without / with a wrong secret; one real turn 200; old container kept for rollback | `deploy/ec2_update.sh`, 2026-11-14 |
| edtech product | 30 of 30 deterministic checks pass | `python edtech/checks.py` |

## The architecture on one page

A ticket arrives in the customer's ticketing system. The agent reads it, looks up the order, finds the governing policy, drafts a reply as an internal note, and proposes a category and priority. Anything that moves money stops for a named person.

| Layer | Decision | What it is here |
|---|---|---|
| UI | connect | The draft lands as an internal comment in the ticketing system the desk already uses |
| Graph | build | Router → orders, policy or desk specialist → answer, at most 3 hops |
| Integrations | connect | Tickets, orders and customers over MCP; the customer's server enforces who can see what |
| Knowledge | connect | The customer's 40-document policy library, filtered by scope before search |
| Memory | never | Nothing is kept between tickets in the pilot |
| Human in the loop | build | Credits, replacements, closing a ticket and customer-visible replies stop for a person |
| Eval | build | The frozen golden set, a judge checked against two labellers, a regression gate |
| Observability | connect | The customer's audit log records every call and every denial; traces add cost per ticket |

The rule everything else follows from: the permission check lives inside the customer's system, not in the prompt.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-graph.txt
cp .env.example .env                      # then paste your own key; .env is never committed

python scripts/check_lab2b.py --offline   # gate rules, no key needed
python scripts/selftest_eval_lab2b.py     # eval plumbing, no key needed
python scripts/selftest_retrieval.py      # the governing-policy step through MCP, no key needed
python scripts/measure_retrieval.py       # retrieval before/after on the golden set, no key needed
python scripts/measure_triage.py          # the desk's triage rules on the golden set, no key needed
python scripts/selftest_triage.py         # the triage rules through MCP, no key needed
python scripts/readout_impact.py          # the score under each labeller reading, no key needed
python edtech/checks.py                   # 30 checks, no key needed
python scripts/check_lab2b.py             # all three lab 2b checks (needs a key)
python scripts/eval_lab2b.py              # ten golden cases through the chat (needs a key)
```

## What is still open

- **The contract's triage number needs all 120 triage cases.** 40/50 (80%) is two samples, with a 95% interval of 67–89%; the full run is ~2.2M tokens and needs a fresh key. The rubric enforcement added after the samples is checked case by case (4/4), not as a run.
- **Readout decisions** (`reports/readout-decisions.md`): five labeller rules, with a recommendation and the score under each reading. The six remaining triage misses are all rule D1 ("category never set"); under B's reading the two samples score 45/50.
- **P-007** is recommended as held: the rubric itself gives `escalate: false` for that ticket and no action was taken.
- **U.S.-only data residency is unconfirmed** for the model endpoint (it answers as an Azure OpenAI deployment behind Cloudflare); the evidence and the question to send are in `reports/data-residency.md`.
- **The AWS demo has no TLS**; it is held to one allow-listed address. App Runner is closed to this account.
- **The deliverables are unsigned**, because the customer is simulated; every owner named in them is a proposal (checked against the estate's identity file).
