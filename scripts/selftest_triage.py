# -*- coding: utf-8 -*-
"""Self-test for the desk's triage rules (labs/_triage.py) and their wiring.
No key, no model: the estate and the MCP server are real.

    python scripts/selftest_triage.py

  1. as_arrived() removes the stored category and priority, and nothing else
  2. the rules alone on all 120 frozen triage cases score at least 90% with the
     golden scorer (the baseline model scored 31.7%)
  3. the wedge's suggest_policies, through MCP as each case's acting user, returns
     the same desk_triage as the rules computed locally, on every triage case
  4. every wedge get_ticket result reaches the model without category or priority
  5. an orphan-order ticket is never escalated; billing always is
  6. the lab 2b helper returns the same desk_triage as the wedge tool
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("MAI_TRACE", "0")
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "labs"), str(ROOT / "golden")]

import _baseline as B  # noqa: E402
import _estate as E  # noqa: E402
import _triage as TR  # noqa: E402
from _mcp_client import call, estate_session  # noqa: E402

ok = True


def check(name: str, cond: bool, detail: str = "") -> None:
    global ok
    ok = ok and bool(cond)
    print(("  ok    " if cond else "  WRONG ") + name + (f" — {detail}" if detail else ""))


def main() -> int:
    cases = [c for c in B.load_jsonl(ROOT / "golden" / "cases.jsonl") if c["kind"] == "triage"]
    tickets = {t["id"]: t for t in E._table("tickets")}  # noqa: SLF001
    some = tickets[cases[0]["ticket_id"]]
    arr = TR.as_arrived(some)
    check("as_arrived() drops category and priority only", set(some) - set(arr) <= {"category", "priority"}
          and "category" not in arr and "priority" not in arr and arr["subject"] == some["subject"])

    async def through_mcp():
        import _wedge as W  # noqa: PLC0415
        import lab_2b_multiagent as lab  # noqa: PLC0415
        passed = same = n = 0
        orphan_esc = billing_noesc = 0
        by_user: dict[str, list] = {}
        for c in cases:
            by_user.setdefault(c["input"]["acting_user"], []).append(c)
        for user, cs in by_user.items():
            async with estate_session(user) as session:
                for c in cs:
                    out = json.loads(await W.suggest_policies(session, {"ticket_id": c["ticket_id"]}))
                    d = out["desk_triage"]
                    t = tickets[c["ticket_id"]]
                    order = None
                    try:
                        order = E.get_order(user, t["order_id"]) if t.get("order_id") else None
                    except Exception:  # noqa: BLE001  (missing or denied)
                        order = None
                    missing = bool(t.get("order_id")) and order is None
                    local = TR.desk_triage(TR.as_arrived(t), order, E.get_customer(user, t["customer_id"]),
                                           E.search_policies(user, "warranty installation returns parts credit service delivery pricing data escalation region policy", k=60),
                                           order_missing=missing)
                    same += all(d[k] == local[k] for k in ("category", "priority", "escalate", "policy_doc_id"))
                    rec = {"output": {k: d[k] for k in ("category", "priority", "escalate", "policy_doc_id")}}
                    passed += B.score(c, rec)["label"] == "pass"
                    orphan_esc += missing and d["escalate"]
                    billing_noesc += d["category"] == "billing" and not d["escalate"] and not missing
                    n += 1
        check(f"rules through MCP: {passed} of {n} triage cases pass the golden scorer", passed >= 0.9 * n,
              f"{passed / n:.1%}; the baseline model scored 31.7%")
        check(f"wedge tool and local rules agree on {same} of {n}", same == n)
        check("no orphan-order ticket is escalated; every billing ticket with an order is", orphan_esc == 0 and billing_noesc == 0,
              f"orphan escalated {orphan_esc}, billing not escalated {billing_noesc}")
        user, c = cases[0]["input"]["acting_user"], cases[0]
        async with estate_session(user) as session:
            raw = TR.arrived_text(await call(session, "get_ticket", {"ticket_id": c["ticket_id"]}))
            v = json.loads(raw)
            check("a get_ticket result reaches the wedge's model without category or priority",
                  "category" not in v and "priority" not in v and v.get("id") == c["ticket_id"])
            tools = {t.name: t for t in await lab.mcp_tools(session)}
            helper = lab.suggest_policies_tool(tools)
            a = json.loads(await helper.coroutine(ticket_id=c["ticket_id"]))["desk_triage"]
            b = json.loads(await W.suggest_policies(session, {"ticket_id": c["ticket_id"]}))["desk_triage"]
            check("lab 2b helper and the wedge tool give the same desk_triage", a == b)

    asyncio.run(through_mcp())
    print("\nself-test", "passed" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
