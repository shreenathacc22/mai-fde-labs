# The wedge on triage — what changed on 2026-11-14 and what it measures

*Calder & Rowe · the eval contract's triage row · all runs on the frozen golden set, scored with `golden/_baseline.score()` and lab 3's judge*

## The change

On lab 3's 30-case sample the wedge (with the retrieval step) scored triage 6/20; 11 of its 14 misses were **priority** and three were **category** on tickets the desk never categorised. The cause was not wording: the wedge's prompt never stated the desk's rubric, so the model judged urgency itself, and the MCP `get_ticket` showed it the stored category the golden labels are built from.

1. **`labs/_triage.py`** — the desk's rubric in code: category from the ticket as it arrived (an undelivered order means delivery; otherwise the ticket's words), then priority, escalation and the governing document as functions of that category. Rules alone: **111/120 (92.5%)** on the frozen triage cases, no model; 384/390 agreement with the desk's category on tickets outside the set (`reports/triage-measurement.md`).
2. **The wedge** gets the result through `suggest_policies` (`desk_triage`), sees every ticket without its stored category and priority (as the baseline always did), and is told the rubric.
3. **Enforcement** (after the two samples below): priority, escalation and the document follow from the wedge's category by rule, at the `set_ticket` write and in the answer; the category stays the model's, and every override is recorded in the case's `rule_overrides`.

## Results

| Run | Cases | Triage, wedge | Triage, baseline on the same cases | Safety | Tokens | Report |
|---|---|---|---|---|---|---|
| Before the triage rules (sample, seed 2026) | 20 triage of 30 | 6/20 (30%) | 3/20 | 5/5 | 545k | `wedge-eval-before-triage-rules.md` |
| With the triage rules (same sample) | 20 triage of 30 | **16/20 (80%)**, judge 16/20 | 3/20 | **5/5** | 547k | `wedge-eval.md` |
| With the triage rules, 30 more triage cases (drawn with `Random(2026)` from the 100 not in the sample) | 30 | **24/30 (80%)**, judge 24/30 | 12/30 | — | 546k | `wedge-eval-extension.md` |
| **Both samples together** | **50 triage** | **40/50 (80%)** | **15/50 (30%)** | 5/5 | 1.09M | — |
| Enforcement check — the four cases the model got wrong for a non-category reason | 4 | 4/4 | 3/4 | — | 70k | `wedge-eval-enforcement-check.md` |

Retrieval on the sample: 4/5, the same as the baseline (G-128: the governing document is the service-level one; the desk's map points at warranty).

**Measured:** 40/50 (80%) without enforcement, against the contract's proposed 75%, on 50 of the 120 triage cases.
**Projected, not measured:** with enforcement, the four non-category misses pass (checked one by one above), which gives **44/50 (88%)**. A run of the remaining 70 triage cases needs ~1.3M tokens; the key has ~0.15M left.

## What still fails

The six remaining misses are all **category on tickets the desk never categorised** (G-011, G-013, G-014, G-015, G-016, G-111): the golden set expects its abstention `other`; the wedge proposes billing or parts from the subject. That is disputed rule D1 in `reports/readout-decisions.md` — labeller B accepts the proposal when the rest of the triage follows from it, and under that reading the two samples score 45/50 (90%) as measured (`reports/readout-impact.md`). It is a decision for the ops lead, not an engineering fix.

## Reading these numbers honestly

- Two samples of 20 and 30 triage cases are not the full set: the 95% interval on 40/50 is roughly 67–89%. The full 120-case triage run is the number that should go in the contract.
- The rules were written from the desk's rubric, which is also what the golden labels are built from. That is the point — the rubric is the customer's own definition — but it means the triage score now mostly measures whether the wedge applies the rubric, not whether a model can infer it. The held-out category check (98.5% on 390 tickets) is the evidence the category reading generalises within this estate; the estate's ticket text is generated, so real email needs its own measurement in the pilot's first week.
- Safety held at 5/5 throughout; the enforcement only touches fields the rubric defines, never the gate.
