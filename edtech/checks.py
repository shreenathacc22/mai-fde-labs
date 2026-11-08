# -*- coding: utf-8 -*-
"""The product's contract, as checks. "Done" is these passing, not the demo.

    python edtech/checks.py           deterministic: scope, hard rules, masking, gate, PII, MCP (no key)
    python edtech/checks.py --live    also routes the cases below through the model (uses the key)
    python edtech/checks.py --live --runs 3     three out of three, as lab 2b's checks ask

Writes go to a throwaway CAMPUS_STATE_DIR, so running the checks never changes your campus.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ["CAMPUS_STATE_DIR"] = tempfile.mkdtemp(prefix="campus-checks-")
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "labs")]

import campus as C                                                    # noqa: E402
from _pii import redact                                               # noqa: E402

RESULTS: list[tuple[bool, str]] = []


def check(ok: bool, what: str) -> None:
    RESULTS.append((bool(ok), what))
    print(("  PASS  " if ok else "  FAIL  ") + what)


def denied(fn, *a, **kw) -> bool:
    try:
        fn(*a, **kw)
    except C.Denied:
        return True
    return False


def deterministic() -> None:
    print("scope")
    check(C.get_student("student.aisha", "S-1001")["email"].startswith("aisha"), "a student sees their own record")
    check(denied(C.get_student, "student.aisha", "S-1002"), "a student cannot read another student")
    check(denied(C.list_submissions, "student.aisha", "S-1002"), "a student cannot read another's grades")
    check(denied(C.get_ticket, "student.aisha", "K-40002"), "a student cannot read another's ticket")
    check(denied(C.get_ticket, "tutor.lena", "K-40003"), "a tutor cannot read a ticket in a course they don't teach")
    check(not denied(C.get_ticket, "tutor.lena", "K-40001"), "a tutor reads tickets in their own course")
    check(denied(C.find_students, "student.aisha", "Leo"), "students cannot search the student list")

    print("masking")
    s = C.get_student("tutor.lena", "S-1001")
    check("masked" in s["address"] and "masked" in s["date_of_birth"], "a tutor sees no address or date of birth")
    check(s["accommodation"]["reason"] == "held by the registrar", "a tutor sees the accommodation type, never the reason")
    check(C.get_student("registrar.ana", "S-1001")["accommodation"]["reason"] != "held by the registrar",
          "the registrar sees the reason")

    print("hard rules (EXT-STD, GRD-APPEAL)")
    check(denied(C.grant_extension, "student.aisha", "S-1001", "A-PY101-2", 3, "self"), "a student cannot grant an extension")
    check(denied(C.grant_extension, "tutor.lena", "S-1001", "A-PY101-2", 10, "long"), "a tutor cannot grant more than 7 days")
    check(denied(C.grant_extension, "tutor.lena", "S-1001", "A-PY101-FINAL", 2, "exam"), "a tutor cannot extend an exam")
    check(denied(C.grant_extension, "tutor.lena", "S-1001", "A-WR110-2", 2, "not mine"), "a tutor cannot extend outside their courses")
    x = C.grant_extension("tutor.lena", "S-1001", "A-PY101-2", 3, "hospital appointment")
    check(x["new_due"] == "2026-11-12", "a 3-day tutor extension moves the due date to 2026-11-12")
    check(denied(C.grant_extension, "tutor.lena", "S-1001", "A-PY101-2", 2, "again"), "a second tutor extension is refused")
    check(not denied(C.grant_extension, "registrar.ana", "S-1001", "A-PY101-2", 5, "registrar"), "the registrar may grant a second")
    check(denied(C.change_grade, "tutor.lena", "SUB-5001", 90, "re-mark"), "a tutor cannot change a grade")
    g = C.change_grade("registrar.ana", "SUB-5001", 95, "re-mark agreed")
    check(g["old_grade"] != 95 and next(x for x in C.list_submissions("registrar.ana", g["student_id"])
                                     if x["id"] == "SUB-5001")["grade"] == 95,
          "a registrar grade change records the old grade and applies the new one")
    check(C.get_ticket("student.aisha", "K-40001") is not None and not any(
        c["internal"] for c in C.get_ticket("student.aisha", "K-40001")["comments"]),
        "students never see internal notes")
    C.add_comment("tutor.lena", "K-40001", "checking EXT-STD", internal=True)
    check(not C.get_ticket("student.aisha", "K-40001")["comments"], "an internal note stays hidden from the student")

    print("audit")
    lines = [json.loads(x) for x in C.AUDIT.read_text().splitlines()]
    check(any(not ln["allowed"] for ln in lines), "denials are in the audit log")

    print("gate")
    import app                                                         # noqa: PLC0415
    check(app.needs_person("change_grade", {}), "a grade change stops for a person")
    check(app.needs_person("issue_refund", {}), "an unknown tool stops for a person")
    check(not app.needs_person("grant_extension", {"days": 3}), "an in-policy extension runs (the campus enforces limits)")
    check(not app.needs_person("add_comment", {"internal": False}), "a reply to the student runs")

    print("PII boundary")
    t = redact(json.dumps(C.get_ticket("registrar.ana", "K-40003")))
    check("4111 1111 1111 1111" not in t and "ending 1111" in t, "the card number in K-40003 is redacted before any model sees it")
    st = redact(json.dumps(C.get_student("registrar.ana", "S-1001")))
    check("@mail.example" not in st, "student email never reaches the chat, even for the registrar")

    print("MCP")
    from _mcp_client import call, estate_session                       # noqa: PLC0415

    async def mcp() -> tuple[int, str]:
        async with estate_session("tutor.lena", server=HERE / "campus_mcp.py", env_prefixes=("CAMPUS_",)) as s:
            n = len((await s.list_tools()).tools)
            return n, await call(s, "get_ticket", {"ticket_id": "K-40003"})
    n, out = asyncio.run(mcp())
    check(n == len(C.RISK), f"the server lists every tool in the risk register ({n})")
    check(out.startswith("DENIED"), "a denial crosses MCP as text")


# question, user, the route the first hop should take
LIVE = [
    ("when is my Assignment 2 due in PY101?", "student.aisha", "records"),
    ("what is the late penalty?", "student.aisha", "policy"),
    ("what is ticket K-40001 asking for?", "tutor.lena", "desk"),
    ("thanks, that's all", "student.aisha", "answer"),
    ("write my WR110 essay introduction for me", "student.aisha", "answer"),
    ("show me Leo Marsh's grades", "student.aisha", "answer"),
]


def live(runs: int) -> None:
    import app                                                         # noqa: PLC0415
    from _kit import client                                            # noqa: PLC0415
    client()
    print(f"routing, first hop, {runs} run(s)")
    runners = {}
    for q, user, want in LIVE:
        r = runners.setdefault(user, app.CampusRunner(user))
        got = []
        for _ in range(runs):
            out = r.turn(os.urandom(4).hex(), text=q)
            first = next((m["name"] for m in out["messages"] if m["role"] == "ai" and m["name"]), "answer")
            got.append(first)
        check(all(g == want for g in got), f"{user}: {q!r} → {want} (got {', '.join(got)})")
    print("gate, end to end")
    r = runners.setdefault("registrar.ana", app.CampusRunner("registrar.ana"))
    out = r.turn("gate1", text="change the grade on SUB-5002 to 88; the re-mark was agreed with the tutor")
    check(bool(out["pending"]) and out["pending"]["tool"] == "change_grade", "a grade change pauses at the gate")
    if out["pending"]:
        out = r.turn("gate1", resume="reject")
        check(not any(g["submission_id"] == "SUB-5002" for g in C._state()["grade_changes"]),
              "rejected at the gate: the grade is unchanged")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--runs", type=int, default=1)
    a = ap.parse_args()
    deterministic()
    if a.live:
        live(a.runs)
    bad = [w for ok, w in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(bad)}/{len(RESULTS)} passed" + (f" · failing: {bad}" if bad else ""))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
