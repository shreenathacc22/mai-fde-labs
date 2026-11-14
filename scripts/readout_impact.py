# -*- coding: utf-8 -*-
"""What each disputed labelling rule does to the triage score — for the readout.

golden/DISAGREEMENTS.md lists five rules on which labeller A and labeller B read
the same output differently. The ops lead picks one reading per rule; this
script shows, for a given set of outputs, the triage score under A (the frozen
scorer) and under B's reading of each rule on its own, so the decision is made
with the numbers in front of it. It changes nothing in the frozen set.

    python scripts/readout_impact.py              rules alone + the baseline + the last wedge run
    python scripts/readout_impact.py --write      also writes reports/readout-impact.md

B's readings, made general (the list in DISAGREEMENTS.md names cases; a rule
has to apply to any output):
  category-never-set   the desk set no category and the set expects 'other': accept
                       any category whose priority, escalation and document are what
                       the desk's rubric gives for that category
  same-policy-family   accept PRT-AVAIL for PRT-ORDER and CRD-REFUND for CRD-ISSUE
  priority-normal-high accept 'high' where the set expects 'normal' on a delivery
                       ticket whose order cannot be found
  honest-null          accept policy_doc_id null when everything else matches and the
                       governing document was not among the top 3 hits the agent was shown
(doc-at-rank-4-5 is a retrieval rule and does not touch triage.)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "labs"), str(ROOT / "golden"), str(ROOT / "estate")]
import _baseline as B  # noqa: E402
import _triage as TR  # noqa: E402

DATA = ROOT / "estate" / "data"
T = {t["id"]: t for t in json.loads((DATA / "tickets.json").read_text())}
O = {o["id"]: o for o in json.loads((DATA / "orders.json").read_text())}
CU = {c["id"]: c for c in json.loads((DATA / "customers.json").read_text())}
LIB = json.loads((DATA / "policies.json").read_text())
LIB = LIB if isinstance(LIB, list) else list(LIB.values())
CASES = {c["id"]: c for c in B.load_jsonl(ROOT / "golden" / "cases.jsonl")}
FAMILY = {("PRT-ORDER", "PRT-AVAIL"), ("CRD-ISSUE", "CRD-REFUND")}
RULES = ("category-never-set", "same-policy-family", "priority-normal-high", "honest-null")


def facts(case):
    t = T[case["ticket_id"]]
    oid = t.get("order_id")
    order = O.get(oid) if oid else None
    return t, order, bool(oid) and order is None


def passes(case, out, rule: str | None, hits=None) -> bool:
    if not out:
        return False
    if B.score(case, {"output": out})["label"] == "pass":
        return True
    exp = case["expected"]
    t, order, missing = facts(case)
    got = {k: out.get(k) for k in ("category", "priority", "escalate", "policy_doc_id")}
    if rule == "category-never-set" and exp["category"] == "other" and not t.get("category") \
            and got["category"] in TR.CATEGORIES:
        d = TR.desk_triage(TR.as_arrived(t), order, CU.get(t["customer_id"]), LIB,
                           order_missing=missing, category=got["category"])
        return all(got[k] == d[k] for k in ("priority", "escalate")) and \
            (d["policy_doc_id"] is None or got["policy_doc_id"] == d["policy_doc_id"])
    if rule == "same-policy-family" and (exp["policy_doc_id"], got["policy_doc_id"]) in FAMILY:
        return B.score(case, {"output": {**got, "policy_doc_id": exp["policy_doc_id"]}})["label"] == "pass"
    if rule == "priority-normal-high" and exp["category"] == "delivery" and missing \
            and exp["priority"] == "normal" and got["priority"] == "high":
        return B.score(case, {"output": {**got, "priority": "normal"}})["label"] == "pass"
    if rule == "honest-null" and got["policy_doc_id"] is None and hits is not None \
            and exp["policy_doc_id"] not in hits[:3]:
        return B.score(case, {"output": {**got, "policy_doc_id": exp["policy_doc_id"]}})["label"] == "pass"
    return False


def table(name: str, outputs: dict[str, dict]) -> list[str]:
    ids = [i for i in outputs if CASES[i]["kind"] == "triage"]
    n = len(ids)
    out = {i: (outputs[i][0] if isinstance(outputs[i], tuple) else outputs[i]) for i in ids}
    hit = {i: (outputs[i][1] if isinstance(outputs[i], tuple) else None) for i in ids}
    a = sum(passes(CASES[i], out[i], None, hit[i]) for i in ids)
    row = [name, f"{n}", f"{a} ({a / n:.0%})"]
    for r in RULES:
        b = sum(passes(CASES[i], out[i], r, hit[i]) for i in ids)
        row.append(f"{b} (+{b - a})" if b != a else f"{b}")
    allb = sum(any(passes(CASES[i], out[i], r, hit[i]) for r in (None, *RULES)) for i in ids)
    row.append(f"{allb} ({allb / n:.0%})")
    return row


def main() -> int:
    runs = []
    rules_out = {}
    for cid, c in CASES.items():
        if c["kind"] != "triage":
            continue
        t, order, missing = facts(c)
        d = TR.desk_triage(TR.as_arrived(t), order, CU.get(t["customer_id"]), LIB, order_missing=missing)
        rules_out[cid] = {k: d[k] for k in ("category", "priority", "escalate", "policy_doc_id")}
    runs.append(table("Rules alone (`labs/_triage.py`), all 120", rules_out))
    base = {r["id"]: (r.get("output"), r.get("hits") or []) for r in B.load_jsonl(ROOT / "golden" / "baseline_run.jsonl")}
    runs.append(table("Baseline model, frozen run, all 120", base))
    for label, p in (("Wedge before the triage rules (30-case sample)", ROOT / "reports" / "wedge-eval-run-before-triage-rules.jsonl"),
                     ("Wedge with the triage rules (30-case sample)", ROOT / "reports" / "wedge-eval-run.jsonl"),
                     ("Wedge with the triage rules (30 more triage cases)", ROOT / "reports" / "wedge-eval-extension-run.jsonl")):
        if p.exists():
            outs = {}
            for r in B.load_jsonl(p):
                o = r.get("output")
                if isinstance(o, str):
                    try:
                        import ast  # noqa: PLC0415
                        o = ast.literal_eval(o)
                    except (ValueError, SyntaxError):
                        o = None
                hits = r.get("hits")
                if isinstance(hits, str):
                    import ast  # noqa: PLC0415
                    hits = ast.literal_eval(hits)
                outs[r["id"]] = (o, hits or [])
            runs.append(table(label, outs))
    head = ["Outputs", "Triage cases", "A (frozen scorer)", *[f"B: {r}" for r in RULES], "B on all four"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(r) + " |" for r in runs]
    print("\n".join(lines))
    if "--write" in sys.argv:
        (ROOT / "reports" / "readout-impact.md").write_text(
            "# What each disputed labelling rule does to the triage score\n\n"
            "*`python scripts/readout_impact.py --write` · nothing in the frozen set is changed*\n\n"
            "Each B column applies labeller B's reading of one rule (from `golden/DISAGREEMENTS.md`, made general "
            "so it applies to any output) on top of the frozen scorer. The ops lead picks one reading per rule at the "
            "readout; see `reports/readout-decisions.md` for the recommendation on each.\n\n" + "\n".join(lines) + "\n")
        print("wrote reports/readout-impact.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
