# Retrieval — the desk's map in code against the baseline search

*2026-11-09 · `python scripts/measure_retrieval.py` · no model, no key; both methods run through the estate as the acting user*

The retrieval suite is scored on the search hits, not the answer, so this is the number the eval contract's retrieval row would move to once the wedge takes its candidates from `labs/_retrieval.py` instead of a raw keyword search.

| Population | n | Baseline search, top 3 | Desk map + search, top 3 | First hit right |
|---|---|---|---|---|
| The 30 golden retrieval cases | 30 | 50.0% | **93.3%** | 93.3% |
| Every ticket with a nameable document | 559 | 34.2% | **94.3%** | 94.3% |

## How it works

1. **Topic** from the subject (weight 3) and body (weight 1): warranty, delivery, installation, parts, billing, returns, training; nothing matched means other. An undelivered order adds weight to delivery.
2. **The desk's map** (the one in the triage rubric): topic + the order's product class + region + the customer's tier name the governing document, with the rubric's own second choices behind it.
3. **Fill** from the text search, documents of the inferred topic first.

Scope is the customer's: candidates come only from `search_policies` called as the acting user, so a document the user may not see is never suggested. The ticket's stored category is not read; the agent sees a ticket as it arrived.

## Where it still misses (32 of 559 tickets)

| Ticket | Wanted | Got | Read as | Subject |
|---|---|---|---|---|
| T-30043 | SLA-STD | PRT-ORDER, PRT-CONSUM, PRT-AVAIL | parts | Need part: Walk-in cooler 8x10 |
| T-30062 | SLA-KEY | PRT-ORDER, PRT-CONSUM, PRT-AVAIL | parts | Parts request — Spiral dough mixer, 80lb flo |
| T-30064 | SLA-STD | CRD-ISSUE, CRD-GOODWILL, CRD-REFUND | billing | Billing |
| T-30068 | SLA-PREF | PRT-ORDER, PRT-CONSUM, PRT-AVAIL | parts | Parts pricing |
| T-30069 | SLA-STD | INS-REACHIN, CRD-ISSUE, INS-FRYER | warranty | Unit faulty — 36in griddle top range |
| T-30074 | SLA-STD | WAR-CONV, WAR-RANGE, WAR-COMBI | warranty | Fault on — Half-size convection oven, e |
| T-30108 | SLA-STD | WAR-COMBI, WAR-CONV, WAR-RANGE | warranty | Unit faulty — 10-pan combi oven, gas |
| T-30120 | SLA-STD | CRD-ISSUE, CRD-REFUND, CRD-GOODWILL | billing | Double charged: Hotel pans |
| T-30136 | SLA-STD | REG-WEST-ZONES, PRC-FREIGHT, REG-CENTRAL-WINTER | delivery | Where is my order O-20231 |
| T-30149 | SLA-PREF | PRT-ORDER, PRT-CONSUM, PRT-AVAIL | parts | Replacement part — Countertop electric fryer, 1 |
| T-30155 | SLA-STD | WAR-DISH, WAR-RANGE, INS-DISH | warranty | Fault on |
| T-30160 | SLA-STD | CRD-ISSUE, CRD-GOODWILL, CRD-REFUND | billing | Invoice query: Hotel pans |
| T-30176 | SLA-KEY | CRD-ISSUE, CRD-GOODWILL, CRD-REFUND | billing | Billing |
| T-30224 | SLA-STD | WAR-REACHIN, INS-REACHIN, REG-EAST-HOURS | warranty | Not working — — Two-section reach-in refrige |
| T-30228 | SLA-KEY | WAR-FRYER, WAR-SMALLWARES, PRT-CONSUM | warranty | Not working — O-20391 |
| T-30254 | SLA-STD | PRT-ORDER, PRT-CONSUM, PRT-AVAIL | parts | Need part: 20qt planetary mixer with bowl guard |
| T-30264 | SLA-STD | RET-GEN, RET-SMALL, RET-SPECIAL | returns | Return request: Conveyor dishwasher |
| T-30279 | SLA-STD | REG-WEST-ZONES, PRC-FREIGHT, REG-CENTRAL-WINTER | delivery | Where is my order — Countertop electric fryer, 1 |
| T-30285 | SLA-STD | CRD-ISSUE, CRD-GOODWILL, CRD-REFUND | billing | Freight charge |
| T-30307 | SLA-STD | WAR-DISH, WAR-CONV, PRT-CONSUM | warranty | Not working — — Conveyor dishwasher, 44in, 2 |
| T-30321 | SLA-STD | RET-GEN, RET-SMALL, RET-SPECIAL | returns | Wrong model |
| T-30322 | SLA-PREF | RET-SMALL, RET-GEN, RET-SPECIAL | returns | Wrong model — Sheet pans, full size, alumi |
| T-30337 | SLA-STD | REG-WEST-ZONES, PRC-FREIGHT, REG-CENTRAL-WINTER | delivery | Where is my order O-20483 |
| T-30395 | SLA-STD | WAR-RANGE, WAR-DISH, WAR-SMALLWARES | warranty | Warranty claim |
| T-30405 | SLA-PREF | CRD-ISSUE, CRD-GOODWILL, CRD-REFUND | billing | Invoice query: (item not in catalogue) |
| T-30481 | SLA-STD | CRD-ISSUE, CRD-REFUND, CRD-GOODWILL | billing | Invoice query: Cambro-style food storage boxes |
| T-30489 | SLA-PREF | PRT-CONSUM, PRT-ORDER, PRT-AVAIL | parts | Question — Sheet pans, full size, alumi |
| T-30502 | SLA-PREF | WAR-MIXER, WAR-WALKIN, WAR-DISH | warranty | Warranty claim — Spiral dough mixer, 80lb flo |
| T-30535 | SLA-STD | WAR-WALKIN, WAR-REACHIN, INS-WALKIN | warranty | Fault on: Walk-in cooler 8x10 |
| T-30555 | SLA-KEY | CRD-ISSUE, CRD-GOODWILL, CRD-REFUND | billing | Freight charge — Stock pots, 60qt, aluminium, |
| T-30568 | SLA-STD | PRC-FREIGHT, REG-CENTRAL-WINTER, PRC-TIERS | delivery | Short shipped O-20582 |
| T-30577 | SLA-PREF | PRC-FREIGHT, REG-EAST-HOURS, PRT-CONSUM | delivery | Quick one: Countertop electric fryer |

Misses by wanted document: SLA-STD ×21, SLA-PREF ×7, SLA-KEY ×4

## What this does not show

- Triage accuracy. The policy field was the main triage miss, so this should lift it, but that needs a model run against the frozen set to confirm.
- A better model. The baseline's 50% was the search, not the model; this fixes the search.
