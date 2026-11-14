# Triage rules in code — measured on the frozen set, no model

*Calder & Rowe · `labs/_triage.py` · `python scripts/measure_triage.py --write`*

All 120 triage cases, scored the way `golden/_baseline.score()` scores them, each ticket as it arrived (stored category and priority removed).

| | Triage pass | |
|---|---|---|
| Baseline (model with the rubric, frozen run) | 38/120 = 31.7% | `golden/baseline_run.jsonl` |
| Rules alone, category from the ticket's words | 111/120 = 92.5% | no model |
| Rules, given the right category | 120/120 = 100.0% | the ceiling once category is right |

Fields the rules alone miss: category 9, priority 9, policy_doc_id 9, escalate 6

Category confusions (expected → rules): other → billing ×5; other → parts ×1; other → returns ×1; training → delivery ×1; parts → delivery ×1

Reading it: priority, escalation and the governing document are functions of the category in the desk's rubric, so once the category is right they follow (the 'given' row). What remains is category, and most of that is tickets the desk never categorised: the golden set labels them `other` (it does not guess from text) while the words say billing or freight — the labeller A/B disagreement in `golden/DISAGREEMENTS.md`.
