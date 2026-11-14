# FDE weekend portfolio — Shreenath Shetty

My work from the Modern AI Pro **Forward Deployed Engineer** weekend (Oct 30 – Nov 1, 2026): take a support agent into a simulated customer, Calder & Rowe, and make it useful, safe and measurable there.

This branch is a fork of the course lab kit by Dr. Balaji Viswanathan ([balajivis/mai-fde-labs](https://github.com/balajivis/mai-fde-labs)). The kit, the simulated customer, the golden set and the lab scripts are his. What I added is listed below, and [`README.md`](./README.md) is the kit's own.

**Where it stands:** all six deliverables are written; none is signed, because the customer is simulated. By its own go-live gate the system is **not ready for go-live**: safety holds at 100%, but triage and retrieval are well under target in the contract. The retrieval step has since been rebuilt and measures 93% on its own; on a 30-case sample the wedge doubles the baseline's triage (6/20 vs 3/20) with safety 5/5 (2026-11-14). What still fails triage is priority, not retrieval. Two measurements are still owed and are listed under [What is still open](#what-is-still-open).

## What I built

| | Where | What it does |
|---|---|---|
| The three lab 2b decisions | [`labs/lab_2b_multiagent.py`](./labs/lab_2b_multiagent.py) | Routing rules for the router, `needs_person()` for the approval gate, and a hop budget of 3 |
| A PII boundary in code | [`labs/_pii.py`](./labs/_pii.py) | Redacts card numbers, addresses, emails and access codes from the message in, every tool result, and every reply out, so the model never holds them |
| Suggestions on a lookup miss | `labs/lab_2b_multiagent.py` | A mistyped ticket or order id comes back with the closest ids the user is allowed to see, instead of a dead end |
| The lab 2b checks as a command | [`scripts/check_lab2b.py`](./scripts/check_lab2b.py) | Runs the routing, gate and hop-budget checks from the lab guide and writes the result |
| Golden cases through the chat | [`scripts/eval_lab2b.py`](./scripts/eval_lab2b.py), [`scripts/selftest_eval_lab2b.py`](./scripts/selftest_eval_lab2b.py) | Scores the multi-agent chat on the frozen golden set the same way the baseline is scored; the self-test runs it offline with a scripted model |
| The governing-policy step | [`labs/_retrieval.py`](./labs/_retrieval.py), [`scripts/measure_retrieval.py`](./scripts/measure_retrieval.py), [`scripts/selftest_retrieval.py`](./scripts/selftest_retrieval.py) | The desk's ticket-to-document map in code, offered to the wedge and the lab 2b policy specialist as a read-only `suggest_policies` tool; takes retrieval from 50% to 93% on the golden cases, measured without a model |
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
| Routing | 5 of 5 questions reached the intended specialist, 3 runs out of 3 (after one rule fix the check itself caught) | [`reports/lab2b-checks.md`](./reports/lab2b-checks.md), 2026-11-14 |
| Approval gate | an internal note runs; closing a ticket stops; no credit tool runs (passed 3 of 4 runs; the diagnostics for the odd one are in the report) | same |
| Two-hop question | orders → policy → answer in one turn, a real warranty answer, **12,931 tokens** | same |
| Retrieval (governing document in top 3) | 50% → **93.3%** on the 30 golden retrieval cases; 34% → 94% on all 559 nameable tickets | [`reports/retrieval-measurement.md`](./reports/retrieval-measurement.md), 2026-11-09 |
| The wedge on the golden set (30-case sample) | triage **6/20 vs the baseline's 3/20** on the same cases; retrieval 4/5 = baseline; safety 5/5; 18k tokens per case | [`reports/wedge-eval.md`](./reports/wedge-eval.md), 2026-11-14 |
| Golden cases through the lab 2b chat (10 chosen cases) | 6/10 structural in each of two runs (not the same six: run-to-run variation); safety 4/4 both times; 19–24k tokens per case. The chat's hop budget of 3 ends 2 of 10 turns before the policy specialist, and the final JSON names no document in 2 more | [`reports/lab2b-eval.md`](./reports/lab2b-eval.md), [first run](./reports/lab2b-eval-first-run.md), 2026-11-14 |
| Judge calibration | 40 cases: agrees with labeller A on all (κ 1.0), with B on 72.5% (κ 0.481), A–B themselves 72.5% on the sample | [`reports/eval-contract.md`](./reports/eval-contract.md), 2026-11-14 |
| Security review, re-run with the retrieval step | 9/9 plants reached; 0/6 PII leaked; 4/4 traps denied; 0/3 red-team attacks succeeded; 1 plant judged "followed" on an `escalate: false` reading, no action taken | [`reports/security-review-pack.md`](./reports/security-review-pack.md), 2026-11-14 |
| Container | `fde-chat` image built (415 MB, no secrets inside); refuses to start without `CHAT_SECRET`; page 200, API 401 without the secret | 2026-11-09 |
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
python edtech/checks.py                   # 30 checks, no key needed
python scripts/check_lab2b.py             # all three lab 2b checks (needs a key)
python scripts/eval_lab2b.py              # ten golden cases through the chat (needs a key)
```

## What is still open

- **Triage is 30% on the sample against a 75% target.** The wedge now sees the right document (retrieval 93% on its own); 11 of its 14 remaining triage misses on the sample are **priority** (high where the desk says normal, normal where it says low) and three are address-update tickets called billing where the golden set says other. Next fix: the rubric wording the wedge is given, then a full 180-case run (~4.8M tokens) to move the contract.
- **The judge sides with labeller A.** κ 1.0 with A and 0.481 with B on 40 cases, where A and B agree on 72.5%; the cases they disagree on are a rule to settle at the readout (`golden/DISAGREEMENTS.md`), not a judge to trust there.
- **One plant judged "followed" in the security review** (P-007): the wedge took no forbidden action but answered `escalate: false` on a ticket whose quoted text said "no human". Recorded as an open question for the readout.
- **U.S.-only data residency is unconfirmed** for the model endpoint.
- **Not deployed to AWS.** The container is built and smoke-tested locally; the ECR → App Runner steps in `docs/GRAPH.md` were not run (cost, and the customer's AWS login).
- **The deliverables are unsigned**, because the customer is simulated; every owner named in them is a proposal.
