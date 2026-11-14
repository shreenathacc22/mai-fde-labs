"""The desk's triage rules (labs/_triage.py) on the frozen golden set, no model.

Scores every triage case the way golden/_baseline.score() does, with the ticket
as it arrived (no stored category or priority). Two numbers:
  rules alone       category from the ticket's words, the rest by rule
  given category    the golden category handed in: how far priority,
                    escalation and the document follow once the category is right
Run: python scripts/measure_triage.py [--write]
"""
import json, sys, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "labs"), str(ROOT / "golden"), str(ROOT / "estate")]
import _triage as TR
import _baseline as B

data = ROOT / "estate" / "data"
T = {t["id"]: t for t in json.loads((data / "tickets.json").read_text())}
O = {o["id"]: o for o in json.loads((data / "orders.json").read_text())}
CU = {c["id"]: c for c in json.loads((data / "customers.json").read_text())}
LIB = json.loads((data / "policies.json").read_text())
LIB = LIB if isinstance(LIB, list) else list(LIB.values())
cases = [json.loads(l) for l in (ROOT / "golden" / "cases.jsonl").open()]
triage = [c for c in cases if c["kind"] == "triage"]
base = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "golden" / "baseline_run.jsonl").open()}

def fields_ok(exp, got):
    """The golden scorer itself, so the rules and the baseline are scored identically."""
    m = B.score({"kind": "triage", "expected": exp}, {"output": got})["mismatch"]
    return [x.split(":")[0] for x in m]

res = {"rules": collections.Counter(), "given": collections.Counter()}
miss_rules = collections.Counter(); rows = []
for c in triage:
    t = TR.as_arrived(T[c["ticket_id"]]); oid = t.get("order_id")
    order = O.get(oid) if oid else None; missing = bool(oid) and order is None
    cust = CU.get(t["customer_id"])
    a = TR.desk_triage(t, order, cust, LIB, order_missing=missing)
    g = TR.desk_triage(t, order, cust, LIB, order_missing=missing, category=c["expected"]["category"])
    ba, bg = fields_ok(c["expected"], a), fields_ok(c["expected"], g)
    res["rules"]["pass" if not ba else "fail"] += 1; res["given"]["pass" if not bg else "fail"] += 1
    for f in ba: miss_rules[f] += 1
    rows.append((c["id"], c["expected"]["category"], a["category"], ba, bg))

n = len(triage)
b_pass = sum(1 for c in triage if B.score(c, base[c["id"]])["label"] == "pass")
print(f"triage cases: {n}")
print(f"baseline (model, frozen run): {b_pass}/{n}" if b_pass is not None else "")
print(f"rules alone (no model):       {res['rules']['pass']}/{n} = {res['rules']['pass']/n:.1%}")
print(f"given the right category:     {res['given']['pass']}/{n} = {res['given']['pass']/n:.1%}")
print("fields missed by rules alone:", dict(miss_rules))
conf = collections.Counter((e, g) for _, e, g, ba, _ in rows if e != g)
print("category confusions (expected -> rules):", conf.most_common(8))
if "--write" in sys.argv:
    out = ROOT / "reports" / "triage-measurement.md"
    lines = ["# Triage rules in code — measured on the frozen set, no model", "",
             "*Calder & Rowe · `labs/_triage.py` · `python scripts/measure_triage.py --write`*", "",
             f"All {n} triage cases, scored the way `golden/_baseline.score()` scores them, each ticket as it arrived "
             "(stored category and priority removed).", "",
             "| | Triage pass | |", "|---|---|---|",
             f"| Baseline (model with the rubric, frozen run) | {b_pass}/{n} = {b_pass/n:.1%} | `golden/baseline_run.jsonl` |",
             f"| Rules alone, category from the ticket's words | {res['rules']['pass']}/{n} = {res['rules']['pass']/n:.1%} | no model |",
             f"| Rules, given the right category | {res['given']['pass']}/{n} = {res['given']['pass']/n:.1%} | the ceiling once category is right |",
             "", "Fields the rules alone miss: " + ", ".join(f"{k} {v}" for k, v in miss_rules.most_common()), "",
             "Category confusions (expected → rules): " + "; ".join(f"{e} → {g} ×{k}" for (e, g), k in conf.most_common(8)), "",
             "Reading it: priority, escalation and the governing document are functions of the category in the desk's rubric, "
             "so once the category is right they follow (the 'given' row). What remains is category, and most of that is "
             "tickets the desk never categorised: the golden set labels them `other` (it does not guess from text) "
             "while the words say billing or freight — the labeller A/B disagreement in `golden/DISAGREEMENTS.md`."]
    out.write_text("\n".join(lines) + "\n"); print("wrote", out.relative_to(ROOT))
