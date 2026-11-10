# -*- coding: utf-8 -*-
"""Self-test for the governing-policy step (labs/_retrieval.py) and its two wirings.
No key, no model: the estate and the MCP server are real.

    python scripts/selftest_retrieval.py

  1. rank() on the frozen retrieval cases: the governing document is in the top 3
     at least 90% of the time (it was 50% for the plain search)
  2. the wedge's local tool (labs/_wedge.suggest_policies) through MCP as agent.priya
  3. the same for an east ticket as agent.priya: the estate denies the read and the
     tool says so, suggesting nothing
  4. the lab 2b policy specialist's helper tool returns the same candidates
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

import _estate as E  # noqa: E402
import _retrieval as R  # noqa: E402
from _baseline import load_jsonl  # noqa: E402
from _mcp_client import estate_session  # noqa: E402

ok = True


def check(name: str, cond: bool, detail: str = "") -> None:
    global ok
    ok = ok and bool(cond)
    print(("  ok    " if cond else "  WRONG ") + name + (f" — {detail}" if detail else ""))


def main() -> int:
    cases = [c for c in load_jsonl(ROOT / "golden" / "cases.jsonl") if c["kind"] == "retrieval"]
    tickets = {t["id"]: t for t in E._table("tickets")}  # noqa: SLF001
    hit = 0
    for c in cases:
        u, t = c["input"]["acting_user"], tickets[c["ticket_id"]]
        order = None
        if t.get("order_id"):
            try:
                order = E.get_order(u, t["order_id"])
            except E.Denied:
                pass
        cust = E.get_customer(u, t["customer_id"])
        top = [d["doc_id"] for d in R.candidates(t, order, cust, lambda q, k, u=u: E.search_policies(u, q, k=k))]
        hit += c["expected"]["policy_doc_id"] in top
    check(f"rank(): governing document in the top 3 for {hit} of {len(cases)} retrieval cases", hit >= 0.9 * len(cases))

    west_ticket = next(t["id"] for t in tickets.values() if t["region"] == "west" and t.get("category") == "parts")
    east_ticket = next(t["id"] for t in tickets.values() if t["region"] == "east")

    async def through_mcp():
        import _wedge as W  # noqa: PLC0415
        import lab_2b_multiagent as lab  # noqa: PLC0415
        async with estate_session("agent.priya") as session:
            out = json.loads(await W.suggest_policies(session, {"ticket_id": west_ticket}))
            ids = [c["doc_id"] for c in out["candidates"]]
            check(f"wedge tool: {west_ticket} (west, parts) -> {ids}", ids[:1] in (["PRT-ORDER"], ["PRT-CONSUM"]) and all("why" in c for c in out["candidates"]))
            denied = await W.suggest_policies(session, {"ticket_id": east_ticket})
            check(f"wedge tool: east ticket {east_ticket} as agent.priya is refused, nothing suggested",
                  denied.startswith("ERROR") and "DENIED" in denied.upper(), denied[:90])
            tools = {t.name: t for t in await lab.mcp_tools(session)}
            helper = lab.suggest_policies_tool(tools)
            out2 = json.loads(await helper.coroutine(ticket_id=west_ticket))
            check("lab 2b helper returns the same candidates as the wedge tool",
                  [c["doc_id"] for c in out2["candidates"]] == ids, str([c["doc_id"] for c in out2["candidates"]]))
            check("lab 2b helper is named suggest_policies and is not in the write register (so never gated)",
                  helper.name == "suggest_policies" and E.RISK.get("suggest_policies") is None)

    asyncio.run(through_mcp())
    print("\nself-test", "passed" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
