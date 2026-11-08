# -*- coding: utf-8 -*-
"""Northfield Online Academy's campus API — the customer's systems, as the desk sees them.

Same argument as labs/_estate.py, applied to a school: every function takes the
acting `user` first and the permission check lives INSIDE the function. The
chat, the router, the prompt — none of them decide who may see a grade. This
file does, and the MCP server in campus_mcp.py is a wire, not a wall.

Scope is not regions here, it is relationship:

    student     their own record, their enrolments, their submissions, their tickets
    tutor       the courses they teach, and the students enrolled in those
    viewer      (advisor) every course, read only
    registrar   every course, every write, the only one who can change a grade

Hard rules that are code, not prompt (and so not up for negotiation by a ticket body):

    grant_extension   tutor: up to 7 days, once per assignment, never an exam;
                      registrar: up to 21 days, exams included
    change_grade      registrar only, 0..100, a written reason, and in the product
                      a person approves it at the gate as well
    PII               contact details, date of birth, guardian, accommodation REASON:
                      masked unless can_see_pii; a tutor sees the accommodation TYPE
                      (they need it), never why

Every call, and every denial, is one line in edtech/data/audit.jsonl. Writes go
to edtech/data/state.json (gitignored), layered over the generated files;
reset() returns a clean campus. CAMPUS_STATE_DIR moves both (the container sets it).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "labs"))
from _estate import _bm25  # noqa: E402  (the kit's readable BM25, reused as is)

DATA = HERE / "data"
_MUT = Path(os.environ.get("CAMPUS_STATE_DIR", "") or DATA)
AUDIT = _MUT / "audit.jsonl"
STATE = _MUT / "state.json"
DEFAULT_USER = "advisor.ben"          # least privilege that can still read

STAFF = {"tutor", "registrar"}
STATUSES = {"open", "pending", "resolved", "closed"}
PRIORITIES = {"low", "normal", "high", "urgent"}
CATEGORIES = {"extension", "grade_query", "refund", "technical", "enrolment", "accessibility",
              "privacy", "other"}
PII_FIELDS = ("email", "phone", "address", "date_of_birth", "guardian")
EXT_LIMIT = {"tutor": 7, "registrar": 21}

RISK: dict[str, str] = {
    "whoami": "read", "get_student": "read", "find_students": "read", "list_enrolments": "read",
    "get_course": "read", "list_assignments": "read", "get_assignment": "read",
    "list_submissions": "read", "get_ticket": "read", "list_tickets": "read",
    "search_policies": "read", "get_policy": "read", "read_audit": "read",
    "add_comment": "write", "set_ticket": "write", "open_ticket": "write", "grant_extension": "write",
    "change_grade": "destructive",
}


class Denied(Exception):
    """Raised, never returned: a denial must not look like an empty result."""


# ── loading ──────────────────────────────────────────────────────────────────

_CACHE: dict[str, list] = {}


def _table(name: str) -> list[dict]:
    if name not in _CACHE:
        _CACHE[name] = json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))
    return _CACHE[name]


def _state() -> dict:
    st = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    for k, v in (("tickets", {}), ("extensions", []), ("grade_changes", [])):
        st.setdefault(k, v)
    return st


def _save(st: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _tickets() -> list[dict]:
    st = _state()
    rows = [st["tickets"].get(t["id"], t) for t in _table("tickets")]
    return rows + [t for tid, t in st["tickets"].items() if tid.startswith("K-9")]


def _submissions() -> list[dict]:
    changed = {g["submission_id"]: g["new_grade"] for g in _state()["grade_changes"]}
    return [dict(s, grade=changed.get(s["id"], s["grade"])) for s in _table("submissions")]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_user(user_id: str | None = None) -> str:
    return (user_id or os.environ.get("CAMPUS_USER", "") or DEFAULT_USER).strip()


# ── audit ────────────────────────────────────────────────────────────────────

def _audit(user: str, tool: str, args: dict, *, allowed: bool, reason: str | None = None,
           rows: int | None = None) -> None:
    line = {"ts": _now(), "user": user, "tool": tool, "args": args, "allowed": allowed}
    if reason is not None:
        line["reason"] = reason
    if rows is not None:
        line["rows_returned"] = rows
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


# ── the checks ───────────────────────────────────────────────────────────────

def _user(user) -> dict:
    uid = user["id"] if isinstance(user, dict) else str(user)
    for rec in _table("identity"):
        if rec["id"] == uid:
            return rec
    _audit(uid, "whoami", {}, allowed=False, reason="unknown user")
    raise Denied(f"unknown user {uid!r}")


def _deny(u: dict, tool: str, args: dict, reason: str):
    _audit(u["id"], tool, args, allowed=False, reason=reason)
    raise Denied(reason)


def _require(u: dict, roles: set[str], tool: str, args: dict) -> None:
    if u["role"] not in roles:
        _deny(u, tool, args, f"{tool} needs role {' or '.join(sorted(roles))}; {u['id']} is {u['role']}")


def _my_courses(u: dict) -> set[str]:
    """The course ids this user may see. A student's are the ones they are enrolled in."""
    if u["role"] == "student":
        return {e["course_id"] for e in _table("enrolments") if e["student_id"] == u["student_id"]}
    if "all" in u["courses"]:
        return {c["id"] for c in _table("courses")}
    return set(u["courses"])


def _student_visible(u: dict, student_id: str) -> bool:
    if u["role"] == "student":
        return student_id == u["student_id"]
    mine = _my_courses(u)
    return any(e["student_id"] == student_id and e["course_id"] in mine for e in _table("enrolments"))


def _not_found(u: dict, tool: str, args: dict, what: str):
    """One answer for 'missing' and 'not yours', so a denial never confirms an id exists."""
    _deny(u, tool, args, f"{what} not found in your scope")


def _mask(u: dict, s: dict) -> dict:
    out = dict(s)
    own = u["role"] == "student" and s["id"] == u.get("student_id")
    if u["can_see_pii"] or own:
        return out
    out["email"] = "***@" + s["email"].split("@")[-1]
    out["phone"] = "(***) ***-" + s["phone"][-4:]
    out["address"] = "*** (masked)"
    out["date_of_birth"] = "*** (masked)"
    out["guardian"] = "on file (masked)" if s.get("guardian") else None
    if s.get("accommodation"):
        out["accommodation"] = {"type": s["accommodation"]["type"], "reason": "held by the registrar"}
    if u["role"] == "student":                       # another student: name and id only
        out = {"id": s["id"], "name": s["name"]}
    return out


# ── reads ────────────────────────────────────────────────────────────────────

def whoami(user) -> dict:
    u = _user(user)
    _audit(u["id"], "whoami", {}, allowed=True, rows=1)
    return dict(u, courses=sorted(_my_courses(u)))


def get_student(user, student_id: str) -> dict:
    u = _user(user)
    args = {"student_id": student_id}
    rec = next((s for s in _table("students") if s["id"] == student_id), None)
    if rec is None or not _student_visible(u, student_id):
        _not_found(u, "get_student", args, f"student {student_id}")
    _audit(u["id"], "get_student", args, allowed=True, rows=1)
    return _mask(u, rec)


def find_students(user, name: str) -> list[dict]:
    """Staff only. Fuzzy on name, in scope, duplicates included on purpose."""
    u = _user(user)
    args = {"name": name}
    _require(u, STAFF | {"viewer"}, "find_students", args)
    q = " ".join(name.lower().split())
    scored = []
    for s in _table("students"):
        if not _student_visible(u, s["id"]):
            continue                                       # scope before scoring
        n = s["name"].lower()
        score = max(SequenceMatcher(None, q, n).ratio(), 0.9 if q in n else 0)
        if score >= 0.6:
            scored.append((score, s))
    scored.sort(key=lambda x: (-x[0], x[1]["id"]))
    rows = [_mask(u, s) for _, s in scored[:20]]
    _audit(u["id"], "find_students", args, allowed=True, rows=len(rows))
    return rows


def list_enrolments(user, student_id: str) -> list[dict]:
    u = _user(user)
    args = {"student_id": student_id}
    if not _student_visible(u, student_id):
        _not_found(u, "list_enrolments", args, f"student {student_id}")
    mine = _my_courses(u)
    rows = [dict(e) for e in _table("enrolments") if e["student_id"] == student_id
            and (u["role"] == "student" or e["course_id"] in mine)]
    _audit(u["id"], "list_enrolments", args, allowed=True, rows=len(rows))
    return rows


def get_course(user, course_id: str) -> dict:
    u = _user(user)
    args = {"course_id": course_id}
    rec = next((c for c in _table("courses") if c["id"] == course_id), None)
    if rec is None or course_id not in _my_courses(u):
        _not_found(u, "get_course", args, f"course {course_id}")
    _audit(u["id"], "get_course", args, allowed=True, rows=1)
    return dict(rec)


def _effective_due(assignment: dict, student_id: str | None) -> tuple[str, list[dict]]:
    exts = [x for x in _state()["extensions"]
            if x["assignment_id"] == assignment["id"] and x["student_id"] == student_id]
    due = date.fromisoformat(assignment["due"]) + timedelta(days=sum(x["days"] for x in exts))
    return due.isoformat(), exts


def list_assignments(user, course_id: str) -> list[dict]:
    u = _user(user)
    args = {"course_id": course_id}
    if course_id not in _my_courses(u):
        _not_found(u, "list_assignments", args, f"course {course_id}")
    me = u.get("student_id")
    rows = []
    for a in _table("assignments"):
        if a["course_id"] == course_id:
            row = dict(a)
            if me:
                row["your_due"], _ = _effective_due(a, me)
            rows.append(row)
    _audit(u["id"], "list_assignments", args, allowed=True, rows=len(rows))
    return rows


def get_assignment(user, assignment_id: str, student_id: str | None = None) -> dict:
    """The assignment; with a student id (or as a student), that student's due date
    after any extension, and the extensions granted so far."""
    u = _user(user)
    args = {"assignment_id": assignment_id, "student_id": student_id}
    a = next((x for x in _table("assignments") if x["id"] == assignment_id), None)
    if a is None or a["course_id"] not in _my_courses(u):
        _not_found(u, "get_assignment", args, f"assignment {assignment_id}")
    sid = u.get("student_id") or student_id
    out = dict(a)
    if sid:
        if not _student_visible(u, sid):
            _not_found(u, "get_assignment", args, f"student {sid}")
        out["student_id"] = sid
        out["effective_due"], out["extensions"] = _effective_due(a, sid)
    _audit(u["id"], "get_assignment", args, allowed=True, rows=1)
    return out


def list_submissions(user, student_id: str | None = None, assignment_id: str | None = None) -> list[dict]:
    u = _user(user)
    args = {"student_id": student_id, "assignment_id": assignment_id}
    if u["role"] == "student":
        if student_id not in (None, u["student_id"]):
            _not_found(u, "list_submissions", args, f"student {student_id}")
        student_id = u["student_id"]
    elif student_id and not _student_visible(u, student_id):
        _not_found(u, "list_submissions", args, f"student {student_id}")
    mine = _my_courses(u)
    rows = [s for s in _submissions() if s["course_id"] in mine
            and (student_id is None or s["student_id"] == student_id)
            and (assignment_id is None or s["assignment_id"] == assignment_id)]
    _audit(u["id"], "list_submissions", args, allowed=True, rows=len(rows))
    return rows[:100]


def _ticket_visible(u: dict, t: dict) -> bool:
    if u["role"] == "student":
        return t["student_id"] == u["student_id"]
    return t["course_id"] in _my_courses(u)


def get_ticket(user, ticket_id: str) -> dict:
    u = _user(user)
    args = {"ticket_id": ticket_id}
    t = next((x for x in _tickets() if x["id"] == ticket_id), None)
    if t is None or not _ticket_visible(u, t):
        _not_found(u, "get_ticket", args, f"ticket {ticket_id}")
    t = json.loads(json.dumps(t))
    if u["role"] == "student":                       # students never see the desk's internal notes
        t["comments"] = [c for c in t["comments"] if not c.get("internal")]
    _audit(u["id"], "get_ticket", args, allowed=True, rows=1)
    return t


def list_tickets(user, status: str | None = None, course_id: str | None = None, limit: int = 50) -> list[dict]:
    u = _user(user)
    args = {"status": status, "course_id": course_id, "limit": limit}
    if course_id is not None and course_id not in _my_courses(u):
        _deny(u, "list_tickets", args, f"course {course_id!r} is outside your scope")
    rows = [t for t in _tickets() if _ticket_visible(u, t)
            and (course_id is None or t["course_id"] == course_id)
            and (status is None or t["status"] == status)]
    rows.sort(key=lambda t: t["id"], reverse=True)
    rows = [{k: t[k] for k in ("id", "student_id", "course_id", "assignment_id", "subject", "category",
                               "priority", "status", "created")} for t in rows[:max(0, int(limit))]]
    _audit(u["id"], "list_tickets", args, allowed=True, rows=len(rows))
    return rows


def search_policies(user, query: str, k: int = 4) -> list[dict]:
    u = _user(user)
    args = {"query": query, "k": k}
    ranked = _bm25(query, _table("policies"))[:max(0, int(k))]
    rows = [dict(d, score=round(s, 3)) for s, d in ranked]
    _audit(u["id"], "search_policies", args, allowed=True, rows=len(rows))
    return rows


def get_policy(user, doc_id: str) -> dict:
    u = _user(user)
    args = {"doc_id": doc_id}
    rec = next((d for d in _table("policies") if d["doc_id"] == doc_id), None)
    if rec is None:
        _not_found(u, "get_policy", args, f"policy {doc_id}")
    _audit(u["id"], "get_policy", args, allowed=True, rows=1)
    return dict(rec)


def read_audit(user, limit: int = 100) -> list[dict]:
    u = _user(user)
    args = {"limit": limit}
    _require(u, {"registrar"}, "read_audit", args)
    lines = AUDIT.read_text(encoding="utf-8").splitlines() if AUDIT.exists() else []
    rows = [json.loads(x) for x in lines[-max(0, int(limit)):] if x.strip()]
    _audit(u["id"], "read_audit", args, allowed=True, rows=len(rows))
    return rows


# ── writes ───────────────────────────────────────────────────────────────────

def open_ticket(user, course_id: str, subject: str, body: str, assignment_id: str | None = None) -> dict:
    """A student opens one for themselves; staff open one on a student's behalf by
    putting the student id in the body. Ids from K-90001, clear of the generated range."""
    u = _user(user)
    args = {"course_id": course_id, "subject": subject, "body": body, "assignment_id": assignment_id}
    _require(u, STAFF | {"student"}, "open_ticket", args)
    if course_id not in _my_courses(u):
        _not_found(u, "open_ticket", args, f"course {course_id}")
    st = _state()
    n = 90001 + sum(1 for tid in st["tickets"] if tid.startswith("K-9"))
    rec = {"id": f"K-{n}", "student_id": u.get("student_id"), "course_id": course_id,
           "assignment_id": assignment_id, "subject": subject, "body": body, "category": None,
           "priority": None, "status": "open", "created": _now(), "comments": [], "opened_by": u["id"]}
    st["tickets"][rec["id"]] = rec
    _save(st)
    _audit(u["id"], "open_ticket", args, allowed=True, rows=1)
    return rec


def add_comment(user, ticket_id: str, body: str, internal: bool = True) -> dict:
    """Staff: internal note (default) or a reply the student sees. Students: always
    a visible reply on their own ticket; they cannot write an internal note."""
    u = _user(user)
    args = {"ticket_id": ticket_id, "body": body, "internal": internal}
    _require(u, STAFF | {"student"}, "add_comment", args)
    t = next((x for x in _tickets() if x["id"] == ticket_id), None)
    if t is None or not _ticket_visible(u, t):
        _not_found(u, "add_comment", args, f"ticket {ticket_id}")
    if u["role"] == "student":
        internal = False
    t = json.loads(json.dumps(t))
    c = {"by": u["id"], "at": _now(), "body": body, "internal": bool(internal)}
    t["comments"].append(c)
    st = _state()
    st["tickets"][ticket_id] = t
    _save(st)
    _audit(u["id"], "add_comment", args, allowed=True, rows=1)
    return c


def set_ticket(user, ticket_id: str, status: str | None = None, priority: str | None = None,
               category: str | None = None) -> dict:
    u = _user(user)
    args = {"ticket_id": ticket_id, "status": status, "priority": priority, "category": category}
    _require(u, STAFF, "set_ticket", args)
    for v, ok, name in ((status, STATUSES, "status"), (priority, PRIORITIES, "priority"),
                        (category, CATEGORIES, "category")):
        if v is not None and v not in ok:
            raise ValueError(f"{name} must be one of {sorted(ok)}, not {v!r}")
    t = next((x for x in _tickets() if x["id"] == ticket_id), None)
    if t is None or not _ticket_visible(u, t):
        _not_found(u, "set_ticket", args, f"ticket {ticket_id}")
    t = json.loads(json.dumps(t))
    for name, v in (("status", status), ("priority", priority), ("category", category)):
        if v is not None:
            t[name] = v
    st = _state()
    st["tickets"][ticket_id] = t
    _save(st)
    _audit(u["id"], "set_ticket", args, allowed=True, rows=1)
    return t


def grant_extension(user, student_id: str, assignment_id: str, days: int, reason: str) -> dict:
    """EXT-STD, as code. Tutor: 1..7 days, once per assignment, never an exam, own
    course only. Registrar: 1..21 days, exams included. Past these limits the
    answer is a denial that names who can decide, not a bigger number."""
    u = _user(user)
    args = {"student_id": student_id, "assignment_id": assignment_id, "days": days, "reason": reason}
    _require(u, STAFF, "grant_extension", args)
    a = next((x for x in _table("assignments") if x["id"] == assignment_id), None)
    if a is None or a["course_id"] not in _my_courses(u):
        _not_found(u, "grant_extension", args, f"assignment {assignment_id}")
    enrolled = any(e["student_id"] == student_id and e["course_id"] == a["course_id"]
                   and e["status"] == "active" for e in _table("enrolments"))
    if not enrolled:
        _not_found(u, "grant_extension", args, f"active enrolment of {student_id} in {a['course_id']}")
    if not isinstance(days, int) or days < 1:
        raise ValueError("days must be a whole number of at least 1")
    _, prior = _effective_due(a, student_id)
    if u["role"] == "tutor":
        if a["is_exam"]:
            _deny(u, "grant_extension", args, "exams are never extended by a tutor (EXT-STD); "
                  "the registrar decides a deferred exam")
        if days > EXT_LIMIT["tutor"]:
            _deny(u, "grant_extension", args, f"a tutor may grant up to {EXT_LIMIT['tutor']} days "
                  "(EXT-STD); longer extensions go to the registrar")
        if prior:
            _deny(u, "grant_extension", args, "this assignment already has an extension; a second "
                  "one goes to the registrar (EXT-STD)")
    elif days > EXT_LIMIT["registrar"]:
        _deny(u, "grant_extension", args, f"no extension beyond {EXT_LIMIT['registrar']} days (EXT-STD)")
    st = _state()
    rec = {"extension_id": f"X-{len(st['extensions']) + 1:04d}", "student_id": student_id,
           "assignment_id": assignment_id, "days": days, "reason": reason, "by": u["id"], "at": _now()}
    st["extensions"].append(rec)
    _save(st)
    rec["new_due"], _ = _effective_due(a, student_id)
    _audit(u["id"], "grant_extension", args, allowed=True, rows=1)
    return rec


def change_grade(user, submission_id: str, new_grade: int, reason: str) -> dict:
    """GRD-APPEAL, as code: registrar only, a reason every time, old grade kept."""
    u = _user(user)
    args = {"submission_id": submission_id, "new_grade": new_grade, "reason": reason}
    _require(u, {"registrar"}, "change_grade", args)
    s = next((x for x in _submissions() if x["id"] == submission_id), None)
    if s is None:
        _not_found(u, "change_grade", args, f"submission {submission_id}")
    if not isinstance(new_grade, (int, float)) or not 0 <= new_grade <= 100:
        raise ValueError("new_grade must be between 0 and 100")
    if not (reason or "").strip():
        raise ValueError("a grade change needs a written reason")
    st = _state()
    rec = {"change_id": f"G-{len(st['grade_changes']) + 1:04d}", "submission_id": submission_id,
           "student_id": s["student_id"], "old_grade": s["grade"], "new_grade": new_grade,
           "reason": reason, "by": u["id"], "at": _now()}
    st["grade_changes"].append(rec)
    _save(st)
    _audit(u["id"], "change_grade", args, allowed=True, rows=1)
    return rec


def reset() -> None:
    """A clean campus: drop every write. The audit log stays — that is what makes it one."""
    if STATE.exists():
        STATE.unlink()
