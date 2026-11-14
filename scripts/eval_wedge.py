# -*- coding: utf-8 -*-
"""The wedge (labs/_wedge.py) on the frozen golden set, scored like the baseline.

Lab 3's `--live` re-runs the plain baseline agent. This runs the actual wedge —
the tool-calling loop with `suggest_policies` — on golden cases, each as the
case's acting user, and scores every case twice:

    structural   golden/_baseline.score(): field equality, top-3 membership,
                 what the wedge DID (its tool calls, held or declined writes
                 included), what the draft repeats
    judge        lab 3's calibrated judge (JUDGE), one call per case

and puts the frozen baseline's score on the same cases next to it.

    python scripts/eval_wedge.py               lab 3's fixed 30-case sample (seed 2026)
    python scripts/eval_wedge.py --n 10        a smaller sample
    python scripts/eval_wedge.py --ids G-001,G-121
    python scripts/eval_wedge.py --no-judge

How a wedge run becomes the record the scorer expects:

    hits      the doc ids `suggest_policies` returned, in order; if the wedge never
              called it, the first search_policies result instead
    denied    the estate's words when get_ticket refused the case's ticket (then
              output is None: nothing was read, nothing is scored)
    output    the wedge's final JSON (category, priority, policy_doc_id, escalate, draft)
    actions   what the wedge executed or TRIED: a write held or declined at the
              approval queue counts; nobody approves in this run

Results: reports/wedge-eval.md and reports/wedge-eval-run.jsonl. About 25k tokens
per case; 30 cases is roughly 0.8M tokens.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "labs"))
sys.path.insert(0, str(ROOT / "golden"))

GAP_SECONDS = 1.0


def attempted(tool: str, args: dict) -> list[str]:
    if tool == "add_comment":
        return ["add_comment"]
    if tool == "set_ticket":
        out = []
        if str(args.get("status") or "").lower() in ("resolved", "closed"):
            out.append("set_status_resolved")
        if args.get("category"):
            out.append("set_category")
        if args.get("priority"):
            out.append("set_priority")
        return out or ["set_ticket"]
    if tool in ("issue_credit", "authorise_replacement"):
        return [tool]
    return []


def hits_from(tool_calls: list) -> list[str]:
    """Doc ids the wedge was shown: suggest_policies first, else the first search."""
    for name, _args, result in tool_calls:
        if name == "suggest_policies" and result.startswith("{"):
            return re.findall(r'"doc_id":\s*"([A-Z0-9-]+)"', result)
    for name, _args, result in tool_calls:
        if name == "search_policies" and result.startswith("["):
            return re.findall(r'"doc_id":\s*"([A-Z0-9-]+)"', result)
    return []


def to_record(case: dict, r: dict) -> dict:
    rec = {"id": case["id"], "ticket_id": case["ticket_id"], "kind": case["kind"], "acting_user": case["input"]["acting_user"],
           "tokens": r.get("tokens", 0), "latency_ms": r.get("latency_ms"), "rounds": r.get("rounds"),
           "rule_overrides": r.get("rule_overrides", [])}
    ticket_denied = next((d for d in r["denied"] if d["tool"] == "get_ticket" and d["by"] == "estate"
                          and d["args"].get("ticket_id") == case["ticket_id"]), None)
    rec["hits"] = hits_from(r["tool_calls"])
    rec["tool_calls"] = [(n, a) for n, a, _ in r["tool_calls"]]
    if ticket_denied:
        rec["denied"] = "DENIED: " + ticket_denied["reason"]
        rec["output"] = None
        return rec
    actions: set[str] = set()
    for name, args, result in r["tool_calls"]:
        if not result.startswith(("DENIED", "ERROR", "HELD")) or name in ("issue_credit", "authorise_replacement"):
            actions |= set(attempted(name, args))
    for h in r.get("held", []) + [d for d in r["denied"] if d["by"] == "approval queue"]:
        actions |= set(attempted(h["tool"], h["args"]))
    rec["output"] = {"category": r.get("category"), "priority": r.get("priority"), "policy_doc_id": r.get("policy_doc_id"),
                     "escalate": bool(r.get("escalate")), "actions": sorted(actions), "draft": r.get("draft") or ""}
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description="the wedge on the frozen golden set")
    ap.add_argument("--n", type=int, default=30, help="size of lab 3's fixed sample (default 30)")
    ap.add_argument("--ids", default="", help="comma-separated case ids instead of the sample")
    ap.add_argument("--no-judge", action="store_true")
    args = ap.parse_args()

    import _baseline as B  # noqa: PLC0415
    import _wedge as W  # noqa: PLC0415
    import lab_3_eval_contract as L3  # noqa: PLC0415

    ok, _, _ = L3.verify_freeze()
    if not ok:
        print(L3.REFUSAL)
        return 2
    cases = B.load_jsonl(L3.CASES)
    by_id = {c["id"]: c for c in cases}
    chosen = [by_id[i.strip()] for i in args.ids.split(",") if i.strip()] if args.ids else L3.live_sample(cases, args.n)
    baseline = {r["id"]: r for r in B.load_jsonl(L3.RUN_FILE)}

    W.RESULT_CLIP = 6000                         # keep whole tool results so the doc ids can be read back
    cli = __import__("_kit").client()
    decline = lambda name, a: False              # noqa: E731  the approval queue with nobody at the keyboard

    rows, run = [], []
    print(f"{len(chosen)} golden case(s) through the wedge (suggest_policies on, approvals declined)\n")
    for case in chosen:
        user = case["input"]["acting_user"]
        started, r, err = time.time(), None, ""
        for attempt in (1, 2):
            try:
                r = asyncio.run(W.run_wedge(user, case["ticket_id"], cli=cli, autonomy="approve", approver=decline, label="wedge:golden"))
                break
            except Exception as e:  # noqa: BLE001
                err = f"{type(e).__name__}: {str(e)[:120]}"
                time.sleep(20 if attempt == 1 else 0)
        if r is None:
            rows.append({"id": case["id"], "kind": case["kind"], "s": "not scored", "s_reason": err, "j": "—", "j_reason": "",
                         "b": "—", "tokens": 0, "hits": []})
            print(f"  {case['id']:6} {case['kind']:9} NOT SCORED  {err}", flush=True)
            continue
        rec = to_record(case, r)
        s = B.score(case, rec)
        b = B.score(case, baseline[case["id"]])["label"] if case["id"] in baseline else "—"
        j = {"verdict": "—", "reason": ""}
        if not args.no_judge:
            try:
                j = L3.judge_one(cli, case, rec)
            except Exception as e:  # noqa: BLE001
                j = {"verdict": "not scored", "reason": f"{type(e).__name__}: {str(e)[:100]}"}
        rec["structural"], rec["judge"], rec["baseline_structural"] = s, j, b
        run.append(rec)
        rows.append({"id": case["id"], "kind": case["kind"], "s": s["label"], "s_reason": s["reason"], "j": j["verdict"],
                     "j_reason": str(j.get("reason", "")), "b": b, "tokens": rec["tokens"], "hits": rec["hits"][:3]})
        print(f"  {case['id']:6} {case['kind']:9} wedge {s['label']:4} (baseline {b:4}) · judge {j['verdict']:10} · "
              f"{rec['tokens']:,} tok · {round(time.time() - started)} s · hits {', '.join(rec['hits'][:3]) or '—'}", flush=True)
        print(f"         {s['reason'][:150]}", flush=True)
        time.sleep(GAP_SECONDS)

    def rate(kind: str, key: str) -> tuple[int, int]:
        k = [r for r in rows if r["kind"] == kind and r[key] in ("pass", "fail")]
        return sum(r[key] == "pass" for r in k), len(k)

    print("\nsuite            baseline (same cases)   wedge")
    md_rows = []
    for kind in ("triage", "retrieval", "safety"):
        bp, bn = rate(kind, "b")
        wp, wn = rate(kind, "s")
        jp, jn = rate(kind, "j")
        print(f"  {kind:12}   {bp}/{bn}                    {wp}/{wn}" + (f"   judge {jp}/{jn}" if jn else ""))
        md_rows.append(f"| {kind} | {bp}/{bn} ({100 * bp / bn:.0f}%) | **{wp}/{wn} ({100 * wp / wn:.0f}%)** | " +
                       (f"{jp}/{jn}" if jn else "—") + " |" if bn and wn else f"| {kind} | — | — | — |")
    tokens = sum(r["tokens"] for r in rows)
    print(f"tokens: {tokens:,} ({tokens // max(1, len(run)):,} per case)")

    md = [f"# The wedge on the golden set — {len(run)} cases, the baseline on the same cases beside it", "",
          f"*{date.today().isoformat()} · `python scripts/eval_wedge.py{' --ids ' + args.ids if args.ids else f' --n {args.n}'}` · "
          f"each case as its own acting user · approvals declined · frozen set sha256 `{L3.sha256_of(L3.CASES)[:12]}…`*", "",
          "The baseline column is the kit's frozen reference run (`golden/baseline_run.jsonl`) scored on exactly these cases, so the two "
          "columns differ only in the agent. The wedge has `suggest_policies` (the desk's map in code) and the other tools; "
          "nobody approves, so every write that reached the approval queue counts as attempted.", "",
          "| Suite | Baseline, same cases | Wedge | Wedge by the judge |", "|---|---|---|---|", *md_rows, "",
          "| Case | Kind | Baseline | Wedge | Judge | Hits shown | Tokens | Why |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        why = r["s_reason"] if r["s"] != "pass" else (r["j_reason"] if r["j"] == "fail" else r["s_reason"])
        md.append(f"| {r['id']} | {r['kind']} | {r['b']} | {r['s']} | {r['j']} | {', '.join(r['hits']) or '—'} | {r['tokens']:,} | {why[:200].replace('|', '/')} |")
    md += ["", f"Tokens: {tokens:,} in total, {tokens // max(1, len(run)):,} per case (the judge's calls not included).", "",
           "This is a sample, not the full set: the frozen set has 180 cases and the wedge costs about 25k tokens each. "
           "The sample is lab 3's fixed one (seed 2026), so two runs compare the same tickets.", ""]
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "wedge-eval.md").write_text("\n".join(md), encoding="utf-8")
    B.dump_jsonl(ROOT / "reports" / "wedge-eval-run.jsonl", run)
    print("written: reports/wedge-eval.md · reports/wedge-eval-run.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
