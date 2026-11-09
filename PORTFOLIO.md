# FDE weekend portfolio — Shreenath Shetty

My work from the Modern AI Pro **Forward Deployed Engineer** weekend (Oct 30 – Nov 1, 2026): take a support agent into a simulated customer, Calder & Rowe, and make it useful, safe and measurable there.

This branch is a fork of the course lab kit by Dr. Balaji Viswanathan ([balajivis/mai-fde-labs](https://github.com/balajivis/mai-fde-labs)). The kit, the simulated customer, the golden set and the lab scripts are his. What I added is listed below, and [`README.md`](./README.md) is the kit's own.

**Where it stands:** all six deliverables are written; none is signed, because the customer is simulated. By its own go-live gate the system is **not ready for go-live**: safety holds at 100%, but triage and retrieval are well under target. Two measurements are still owed and are listed under [What is still open](#what-is-still-open).

## What I built

| | Where | What it does |
|---|---|---|
| The three lab 2b decisions | [`labs/lab_2b_multiagent.py`](./labs/lab_2b_multiagent.py) | Routing rules for the router, `needs_person()` for the approval gate, and a hop budget of 3 |
| A PII boundary in code | [`labs/_pii.py`](./labs/_pii.py) | Redacts card numbers, addresses, emails and access codes from the message in, every tool result, and every reply out, so the model never holds them |
| Suggestions on a lookup miss | `labs/lab_2b_multiagent.py` | A mistyped ticket or order id comes back with the closest ids the user is allowed to see, instead of a dead end |
| The lab 2b checks as a command | [`scripts/check_lab2b.py`](./scripts/check_lab2b.py) | Runs the routing, gate and hop-budget checks from the lab guide and writes the result |
| Golden cases through the chat | [`scripts/eval_lab2b.py`](./scripts/eval_lab2b.py), [`scripts/selftest_eval_lab2b.py`](./scripts/selftest_eval_lab2b.py) | Scores the multi-agent chat on the frozen golden set the same way the baseline is scored; the self-test runs it offline with a scripted model |
| A second product on the same stack | [`edtech/`](./edtech) | A student help desk for a fictional online school: scope enforced in the school's system, grade changes gated on a person, a role-scoped dashboard, 30 checks |

## The six deliverables

| # | Deliverable | What it says |
|---|---|---|
| I | [Engagement Brief](./reports/engagement-brief.md) | The lookup work, not the writing, is what slows the desk. ROI is $46,000 a year against $36,000, which is over the CFO's $25,000 signing limit |
| II | [Integration Map](./reports/integration-map.md) | Eight layers, each marked build, connect or never, with a proposed owner on the customer's side |
| III | [Eval Contract](./reports/eval-contract.md) | 180 frozen cases. Baseline: triage 31.7%, retrieval 50%, safety 100%. The judge is not calibrated yet |
| IV | [Security Review Pack](./reports/security-review-pack.md) | 9 of 9 planted injections reached, 0 followed; 0 of 6 planted PII values leaked; 4 of 4 access traps denied |
| V | [Governance Canvas](./reports/governance-canvas.md) | Who approves what, the autonomy ladder per action, the incident path |
| VI | [Go-live & Handover](./reports/go-live-and-handover.md) | Two of four gates do not hold; the recommendation is a suggest-only pilot |

The flow on one sheet: [`reports/calder-rowe-flow.svg`](./reports/calder-rowe-flow.svg).

## Measured results

| What | Result | Source |
|---|---|---|
| Latency per draft | p50 14.8 s, p95 17.5 s over 8 tickets | lab 5, 2026-11-08 |
| Under load | 6 tickets at once: all finished, p95 17.0 s, no rate-limit errors | lab 5 |
| Model cost per ticket | about $0.07 at an assumed price, against the customer's $31 | lab 5 |
| Spend cap | stopped the batch before ticket 9 of 10, as designed | lab 5 |
| Approval step | with nobody to approve, the credit was declined and logged | lab 5 |
| Routing | 5 of 5 questions reached the intended specialist, 3 runs out of 3 | [`reports/lab2b-checks.md`](./reports/lab2b-checks.md) |
| Approval gate | an internal note runs; closing a ticket stops; no credit tool runs | same |
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
python edtech/checks.py                   # 30 checks, no key needed
python scripts/check_lab2b.py             # all three lab 2b checks (needs a key)
python scripts/eval_lab2b.py              # ten golden cases through the chat (needs a key)
```

## What is still open

- **The two-hop check is not demonstrated.** The lab guide's question names order O-27612, which does not exist in this estate, so the chat correctly answered "not found". The check now asks about a real order, but the class practice key ran out of tokens before the rerun.
- **`scripts/eval_lab2b.py` has not been run against the model**, for the same reason. Its plumbing passes the offline self-test; it has produced no scores yet.
- **The judge is not calibrated.** Its last run stopped at 14 of 40 cases, all triage. Trust the structural scores until it is rerun.
- **Triage (31.7%) and retrieval (50%) are baseline numbers**, well under the proposed 75% and 90%. Most triage misses are the policy field, so retrieval is the first fix.
- **Only one red-team attack of my own** is in the security pack, beyond the nine planted ones.
- **U.S.-only data residency is unconfirmed** for the model endpoint.
- **Not deployed.** The container builds are written but were not built or run for this branch.
