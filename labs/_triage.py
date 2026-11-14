# -*- coding: utf-8 -*-
"""The desk's triage rules in code: category, priority, escalate, governing document.

Why this exists. On lab 3's 30-case sample the wedge (2026-11-14) got 14 of 20
triage cases wrong, and 11 of the 14 were PRIORITY: the model judged urgency
itself (a fryer fault "urgent", a parts query "high"). The desk does not judge
priority; its rubric defines it as a function of three facts:

    urgent   a warranty fault on reach-in refrigeration, walk-ins, ice machines
             or hoods (product loss or safety)
    high     any other warranty fault; a delivery query on an undelivered order
    normal   delivery (delivered), installation, parts, billing, returns
    low      training, other

Escalation is a rule too: billing and returns move money; a warranty claim
past the parts window (counted from delivery, the window is in the product
class's warranty terms) can only be met with goodwill; and nothing escalates
when the order on the ticket cannot be found (the first step is to find it).

A rule belongs in code, not in a prompt the model may or may not follow — the
same reasoning as labs/_retrieval.py. The model keeps the parts that need
reading: whether the proposed category is right for this customer's words,
and the reply.

    desk_triage(ticket, order, customer, library, order_missing=False) -> dict

What it does NOT read: the ticket's stored `category` and `priority`. A ticket
reaches first response with neither set (golden/_baseline.py strips them), and
the golden labels are built from the stored category, so reading it would be
reading the answer key. `as_arrived()` removes both; the wedge applies it to
every get_ticket result.

The category comes from the ticket as it arrived:
    1. the referenced order exists and is not delivered -> delivery
       (the one thing evident from the order, as the desk's rule says)
    2. otherwise the strongest topic in the subject and body
       (labs/_retrieval.infer_topics: subject weight 3, body weight 1)
    3. nothing matched -> other
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "estate"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_estate import CLASS_INFO  # noqa: E402  (class -> (label, labour months, parts months, ...))
from _retrieval import infer_topics, mapped, product_class  # noqa: E402

CATEGORY_OF_TOPIC = {"warranty": "warranty_claim", "delivery": "delivery", "installation": "installation",
                     "parts": "parts", "billing": "billing", "returns": "returns", "training": "training"}
TOPIC_OF_CATEGORY = {v: k for k, v in CATEGORY_OF_TOPIC.items()} | {"other": "other"}
CATEGORIES = tuple(CATEGORY_OF_TOPIC.values()) + ("other",)
URGENT_CLASSES = {"reach_in_refrigeration", "walk_in", "ice_machine", "hood"}
MONEY_CATEGORIES = {"billing", "returns"}


def as_arrived(ticket: dict) -> dict:
    """The ticket as first response sees it: no category, no priority."""
    return {k: v for k, v in ticket.items() if k not in ("category", "priority")}


def _date(s: str | None) -> date | None:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(s or "", fmt).date()
        except ValueError:
            continue
    return None


def desk_category(ticket: dict, order: dict | None) -> tuple[str, str]:
    if order and not order.get("delivered"):
        return "delivery", f"{order['id']} is not delivered yet, so delivery is evident from the order"
    topics = infer_topics(as_arrived(ticket), order)
    if topics and topics[0][1] > 0:
        top, score = topics[0]
        return CATEGORY_OF_TOPIC[top], f"the ticket's words point at {top} (score {score})"
    return "other", "nothing in the subject, body or order points at a category"


def desk_priority(category: str, order: dict | None) -> tuple[str, str]:
    cls = product_class(order)
    if category == "warranty_claim" and cls in URGENT_CLASSES:
        return "urgent", f"warranty fault on {cls.replace('_', ' ')}: product loss or safety"
    if category == "warranty_claim":
        return "high", "a warranty fault"
    if category == "delivery" and order and not order.get("delivered"):
        return "high", f"{order['id']} is not delivered yet"
    if category in ("delivery", "installation", "parts", "billing", "returns"):
        return "normal", f"{category}: the desk's normal queue"
    return "low", f"{category}: the desk's low queue"


def desk_escalate(category: str, ticket: dict, order: dict | None, order_missing: bool) -> tuple[bool, str]:
    if order_missing:
        return False, (f"order {ticket.get('order_id')} cannot be found: nothing to credit against; "
                       "the first step is to find the order")
    if category in MONEY_CATEGORIES:
        return True, f"{category} moves money: a named person decides"
    cls = product_class(order)
    if category == "warranty_claim" and order and cls in CLASS_INFO:
        start = _date(order.get("delivered") or order.get("ordered"))
        opened = _date(ticket.get("created"))
        months = CLASS_INFO[cls][1]
        if start and opened:
            age = (opened - start).days / 30.44
            if age > months:
                return True, (f"delivered {start}, ticket opened {opened}: {age:.0f} months, past the "
                              f"{months}-month parts window, so any remedy is goodwill")
            return False, f"{age:.0f} of {months} months: inside the parts window, the desk handles it"
    return False, "no money moves on a first response"


def desk_policy(category: str, ticket: dict, order: dict | None, customer: dict | None,
                library: list[dict]) -> str | None:
    """The governing document for the category, from the desk's map; None when no
    single document can be named (a warranty with no order or no terms for the class)."""
    docs = mapped(TOPIC_OF_CATEGORY[category], ticket, order, customer, library)
    return docs[0] if docs else None


def desk_triage(ticket: dict, order: dict | None, customer: dict | None, library: list[dict],
                order_missing: bool = False, category: str | None = None) -> dict:
    """Everything the desk's rubric decides by rule. Pass `category` to get the
    priority, escalation and document that follow from a category chosen elsewhere."""
    if category in CATEGORIES:
        cat, why_cat = category, "category given"
    else:
        cat, why_cat = desk_category(ticket, None if order_missing else order)
    pri, why_pri = desk_priority(cat, order)
    esc, why_esc = desk_escalate(cat, ticket, order, order_missing)
    doc = desk_policy(cat, ticket, order, customer, library)
    return {"category": cat, "priority": pri, "escalate": esc, "policy_doc_id": doc,
            "why": {"category": why_cat, "priority": why_pri, "escalate": why_esc,
                    "policy": doc and f"the desk's map for {cat}" or "no single document can be named"},
            "priority_by_category": {c: desk_priority(c, order)[0] for c in CATEGORIES}}


SUGGEST_NOTE = ("desk_triage is the desk's rubric applied by rule to this ticket as it arrived: use its category, "
                "priority and escalate unless the customer's words clearly say the category is something else; if "
                "you change the category, take the priority for it from priority_by_category and say why in your "
                "reason. candidates are the likely governing documents in order; read the one you choose with "
                "get_policy.")


def suggestion(ticket: dict, order: dict | None, customer: dict | None, library: list[dict],
               hits: list[dict], order_missing: bool = False) -> dict:
    """The payload of the read-only suggest_policies tool (wedge and lab 2b): the
    desk's triage by rule, and the policy candidates with the rule's document first."""
    from _retrieval import brief, rank
    t = as_arrived(ticket)
    desk = desk_triage(t, order, customer, library, order_missing=order_missing)
    cands = rank(t, order, customer, library, hits, k=3)
    doc = desk["policy_doc_id"]
    if doc:
        entry = next((d for d in library if d.get("doc_id") == doc), {"doc_id": doc})
        cands = [{**entry, "why": f"the desk's map for {desk['category']}"}] + [c for c in cands if c["doc_id"] != doc]
    return {"ticket_id": t.get("id"), "desk_triage": desk, "candidates": brief(cands[:3]), "note": SUGGEST_NOTE}


def arrived_text(result: str) -> str:
    """A get_ticket / list_tickets result as first response sees it. Non-JSON
    results (denials, errors) pass through untouched."""
    try:
        v = json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return result
    if isinstance(v, dict) and "subject" in v:
        return json.dumps(as_arrived(v), ensure_ascii=False, indent=1)
    if isinstance(v, list) and all(isinstance(x, dict) for x in v):
        return json.dumps([as_arrived(x) if "subject" in x else x for x in v], ensure_ascii=False, indent=1)
    return result
