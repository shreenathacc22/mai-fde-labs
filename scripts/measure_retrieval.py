# -*- coding: utf-8 -*-
"""Does the governing document reach the top 3? The baseline search against the
desk's map in code (labs/_retrieval.py), measured with no model and no key.

    python scripts/measure_retrieval.py

Two populations:
  - the 30 retrieval cases of the frozen golden set (what the eval contract scores)
  - every ticket in the estate with a nameable governing document, labelled by the
    same rules that built the golden set (golden/build_golden.expected_for), so the
    30 are not the only thing the method is tuned on

Both methods run as the case's acting user through the estate, so scope is
enforced the same way the agent meets it. Writes reports/retrieval-measurement.md.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "labs"))
sys.path.insert(0, str(ROOT / "golden"))

import _estate as E  # noqa: E402
import _retrieval as R  # noqa: E402
import build_golden as G  # noqa: E402
from _baseline import load_jsonl  # noqa: E402


def baseline_hits(user: str, t: dict, order: dict | None) -> list[str]:
    cls = (R.product_class(order) or "").replace("_", " ")
    query = " ".join(x for x in (t.get("subject", ""), cls, t.get("body") or "") if x)
    return [d["doc_id"] for d in E.search_policies(user, query, k=5)]


def mapped_hits(user: str, t: dict, order: dict | None, cust: dict | None) -> list[dict]:
    return R.candidates(t, order, cust, lambda q, k: E.search_policies(user, q, k=k), k=3)


def context(user: str, t: dict) -> tuple[dict | None, dict | None]:
    order = cust = None
    if t.get("order_id"):
        try:
            order = E.get_order(user, t["order_id"])
        except E.Denied:
            order = None
    try:
        cust = E.get_customer(user, t["customer_id"])
    except E.Denied:
        cust = None
    return order, cust


def score(rows: list[tuple[str, dict, str]]) -> dict:
    """rows: (acting_user, ticket, expected doc) -> top-3 rates and the misses."""
    out = {"n": len(rows), "baseline3": 0, "baseline5": 0, "mapped3": 0, "mapped1": 0, "misses": [], "topic_conf": Counter()}
    for user, t, want in rows:
        order, cust = context(user, t)
        b = baseline_hits(user, t, order)
        m = [d["doc_id"] for d in mapped_hits(user, t, order, cust)]
        out["baseline3"] += want in b[:3]
        out["baseline5"] += want in b[:5]
        out["mapped3"] += want in m[:3]
        out["mapped1"] += bool(m) and m[0] == want
        topics = R.infer_topics(t, order)
        out["topic_conf"][(topics[0][0] if topics else "other")] += 1
        if want not in m[:3]:
            out["misses"].append((t["id"], want, m, (topics[0][0] if topics else "other"), t.get("subject", "")[:50]))
    return out


def pct(a: int, n: int) -> str:
    return f"{100.0 * a / n:.1f}%" if n else "—"


def main() -> int:
    cases = load_jsonl(ROOT / "golden" / "cases.jsonl")
    tickets = {t["id"]: t for t in E._table("tickets")}  # noqa: SLF001
    golden_rows = [(c["input"]["acting_user"], tickets[c["ticket_id"]], c["expected"]["policy_doc_id"])
                   for c in cases if c["kind"] == "retrieval"]

    orders = {o["id"]: o for o in G._load("orders")}  # noqa: SLF001
    customers = {c["id"]: c for c in G._load("customers")}  # noqa: SLF001
    # an in-scope user per region, as the golden set picks them
    user_for = {"west": "agent.priya", "central": "agent.mei", "east": "agent.jonah"}
    all_rows = []
    for t in tickets.values():
        exp, _ = G.expected_for(t, orders, customers)
        if exp["policy_doc_id"]:
            all_rows.append((user_for[t["region"]], t, exp["policy_doc_id"]))

    print("retrieval: is the governing document in the top 3?\n")
    results = {}
    for name, rows in (("golden retrieval cases", golden_rows), ("every ticket with a nameable document", all_rows)):
        s = score(rows)
        results[name] = s
        print(f"{name} (n={s['n']})")
        print(f"  baseline search, top 3   {pct(s['baseline3'], s['n']):>7}   (top 5 {pct(s['baseline5'], s['n'])})")
        print(f"  desk map + search, top 3 {pct(s['mapped3'], s['n']):>7}   (first hit right {pct(s['mapped1'], s['n'])})")
        print(f"  misses: {len(s['misses'])}")
        for tid, want, got, topic, subj in s["misses"][:12]:
            print(f"    {tid}  want {want:14} got {', '.join(got):40}  read as {topic:12} {subj!r}")
        print()

    g, a = results["golden retrieval cases"], results["every ticket with a nameable document"]
    md = [f"# Retrieval — the desk's map in code against the baseline search", "",
          f"*{date.today().isoformat()} · `python scripts/measure_retrieval.py` · no model, no key; both methods run through the estate as the acting user*", "",
          "The retrieval suite is scored on the search hits, not the answer, so this is the number the eval contract's retrieval row would move to "
          "once the wedge takes its candidates from `labs/_retrieval.py` instead of a raw keyword search.", "",
          "| Population | n | Baseline search, top 3 | Desk map + search, top 3 | First hit right |", "|---|---|---|---|---|",
          f"| The 30 golden retrieval cases | {g['n']} | {pct(g['baseline3'], g['n'])} | **{pct(g['mapped3'], g['n'])}** | {pct(g['mapped1'], g['n'])} |",
          f"| Every ticket with a nameable document | {a['n']} | {pct(a['baseline3'], a['n'])} | **{pct(a['mapped3'], a['n'])}** | {pct(a['mapped1'], a['n'])} |", "",
          "## How it works", "",
          "1. **Topic** from the subject (weight 3) and body (weight 1): warranty, delivery, installation, parts, billing, returns, training; nothing matched means other. An undelivered order adds weight to delivery.",
          "2. **The desk's map** (the one in the triage rubric): topic + the order's product class + region + the customer's tier name the governing document, with the rubric's own second choices behind it.",
          "3. **Fill** from the text search, documents of the inferred topic first.", "",
          "Scope is the customer's: candidates come only from `search_policies` called as the acting user, so a document the user may not see is never suggested. The ticket's stored category is not read; the agent sees a ticket as it arrived.", "",
          f"## Where it still misses ({len(a['misses'])} of {a['n']} tickets)", "", "| Ticket | Wanted | Got | Read as | Subject |", "|---|---|---|---|---|"]
    for tid, want, got, topic, subj in a["misses"][:40]:
        md.append(f"| {tid} | {want} | {', '.join(got)} | {topic} | {subj.replace('|', '/')} |")
    by_want = Counter(w for _, w, _, _, _ in a["misses"])
    md += ["", "Misses by wanted document: " + ", ".join(f"{k} ×{v}" for k, v in by_want.most_common(8)), "",
           "## What this does not show", "",
           "- Triage accuracy. The policy field was the main triage miss, so this should lift it, but that needs a model run against the frozen set to confirm.",
           "- A better model. The baseline's 50% was the search, not the model; this fixes the search.", ""]
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "retrieval-measurement.md").write_text("\n".join(md), encoding="utf-8")
    print("written: reports/retrieval-measurement.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
