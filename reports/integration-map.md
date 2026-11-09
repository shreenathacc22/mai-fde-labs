# Integration Map — Deliverable II

*Calder & Rowe · service-desk wedge · filled in during Lab 2*

The eight layers of a production agent, laid over the customer's estate. For each layer, one of three words: **build** (we write it), **connect** (it exists; we integrate over MCP), **never** (we do not touch it, and here is why). A layer with no owner is the one that stalls the pilot.

| Layer | Build / connect / never | What it is at Calder & Rowe | Owner on their side |
|---|---|---|---|
| UI | **connect** — the draft lands as an internal ticket comment; HelpTrack is the UI the desk already has | where the desk agent sees the draft (ticket comment? side panel?) | Dana Okafor (operations lead) |
| Graph | **build** — read → look up → policy → draft → propose → write back → escalate; `run_wedge` is the graph | the triage flow: read → look up → policy → draft → propose → write back → escalate | Dana Okafor (the desk's process); built and run by the FDE |
| Integrations | **connect** — tickets, orders, customers over MCP, scoped per user by the customer's server | ticketing (on-prem), orders, customers — over MCP, scoped per user | Ruth Castellanos (IT security owner; HelpTrack host and SSO) |
| Knowledge | **connect** — the policy library is theirs; `search_policies` filters by scope before ranking | the policy library; retrieval filtered by scope before search | Dana Okafor (the desk keeps the policy library current) |
| Memory | **never** — nothing is kept between tickets in the pilot: no store means nothing to leak or go stale | what the agent keeps between tickets, if anything | Ruth Castellanos (any future store is a data decision) |
| HITL | **build** — credits / refunds / replacements stop for a named person (Lab 5); the wedge only proposes | which actions stop for a named person (credits, replacements) | Marcus Lindqvist (CFO; approves credits) with Ruth Castellanos |
| Eval | **build** — the frozen golden set and the regression gate (Lab 3); the customer does not have one | the frozen golden set, the judge, the regression gate | Dana Okafor (owns the golden set after go-live) |
| Observability | **connect** — their audit.jsonl is the record; our traces.jsonl and the meter add cost per ticket | the audit log, traces, cost per ticket | Ruth Castellanos (audit log); Marcus Lindqvist (cost per ticket) |

## Identity and scope

| Who calls the agent | Role | Regions | Sees PII | Can write |
|---|---|---|---|---|
| viewer.sam (Sam Whitfield) | viewer | west | no | no |
| agent.priya (Priya Raman) | agent | west, central | no | yes |
| agent.jonah (Jonah Adeyemi) | agent | east | yes | yes |
| admin.ruth (Ruth Castellanos) | admin | west, central, east | yes | yes (+ credits, replacements) |
| viewer.dana (Dana Okafor) | viewer | west, central, east | no | no |
| agent.mei (Mei Tanaka) | agent | central | no | yes |
| agent.luis (Luis Delgado) | agent | east | no | yes |
| admin.marcus (Marcus Lindqvist) | admin | west, central, east | yes | yes (+ credits, replacements) |

## What we never touch, and why

- `issue_credit` and `authorise_replacement`: money and goods; admin-only on the server and a named person's decision under ESC-MATRIX. The wedge sets `escalate: true` and names the policy.
- Ticket status: the wedge never resolves or closes; a person does, after reading the draft.
- PII: masked by the server for everyone without `can_see_pii`; the draft repeats nothing from a body.
- The audit log: append-only, written by their server, read by their admins. We never edit it.

## Every call is audited

Where the audit log lives, who can read it, how long it is kept: `estate/data/audit.jsonl` on the ticketing host (on-prem, US); `read_audit` is admin-only (Ruth, Marcus); retention 7 years per DAT-RETENTION (the figure used in the security review pack).

*Rendered by lab_2_wedge.py on 2026-10-31. Owners added 2026-11-08 from each person's role in the estate's identity file; they are proposed and need each person's yes.*

*Sign-off:* Customer IT owner: Ruth Castellanos ____________ · FDE: Shreenath Shetty ____________ · date ________ (unsigned: simulated customer)
