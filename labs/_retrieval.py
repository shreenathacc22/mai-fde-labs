# -*- coding: utf-8 -*-
"""Finding the governing policy document: the desk's map in code, BM25 as the fallback.

The baseline searches the policy library with the ticket's words and shows the
agent the top three. Measured on the frozen set, the governing document is in
those three half the time (retrieval 50%), and 53 of the 82 triage misses are
tickets where the right document was never shown. The desk, meanwhile, has a
map it applies by hand (it is in the triage rubric): a warranty fault on a
fryer is governed by the fryer warranty terms; a west delivery query by the
west zones addendum; parts for small wares by the consumables document. That
map is a rule, and rules belong in code, not in a prompt the model may or may
not follow.

    candidates(ticket, order, customer, search, k=3) -> list[dict]

`search(query, k)` is the customer's own `search_policies`, called as the acting
user, so scope is still enforced by their system: a document the user may not
see is never returned here either. The module reads the library's metadata
(topic, product_class) through that same call, so nothing is hard-coded about
which documents exist.

How a ticket is read (no model):

    1. topic      keywords in the subject (weight 3) and body (weight 1):
                  warranty · delivery · installation · parts · billing ·
                  returns · training. Nothing matched -> "other".
                  An undelivered order on the ticket adds weight to delivery.
    2. the map    topic + the order's product class (from the SKU) + the ticket's
                  region + the customer's tier -> the governing document, with the
                  rubric's own second choices behind it
    3. fill       BM25 hits for the ticket text, documents of the inferred topic
                  first, until there are k

The ticket's stored category is deliberately NOT used: the agent sees a ticket
as it arrived, with no category set, and the golden labels are built from that
field, so reading it would be reading the answer key.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "estate"))
from build_estate import SKU_INDEX  # noqa: E402  (the catalogue: SKU -> (class, name, price))

TOPICS = ("warranty", "delivery", "installation", "parts", "billing", "returns", "training")

# subject patterns are matched on the subject only; text patterns on subject + body
RULES: dict[str, tuple[list[str], list[str]]] = {
    "warranty": ([r"\bwarrant", r"not working", r"faulty", r"fault on", r"\bfault\b"],
                 [r"\bwarrant", r"error code", r"\bleak", r"stopped (working|cooling|heating)", r"\bbroken\b",
                  r"compressor", r"tripp(ing|ed)", r"not (heating|cooling|draining|turning on)", r"won't (start|heat|cool)",
                  r"\bfail(s|ed|ing)\b", r"under warranty", r"\bfault"]),
    "delivery": ([r"where is my order", r"late delivery", r"damaged on arrival", r"short ship", r"\bdeliver"],
                 [r"\bdeliver(y|ed|ies)?\b", r"\bshipment\b", r"\bshipped\b", r"\beta\b", r"\barriv(e|ed|al)\b",
                  r"tracking", r"\bcarrier\b", r"\bpallet", r"\bcrate\b.*damag", r"wrong (site|address|location)"]),
    "installation": ([r"\binstall", r"commissioning"],
                     [r"\binstall", r"commission", r"hook-?up", r"start-?up visit", r"\binstaller\b",
                      r"3-phase|three-phase", r"water filter cartridge"]),
    "parts": ([r"\bparts?\b", r"replacement part", r"need part"],
              [r"\bparts?\b", r"\bgaskets?\b", r"\bfilters?\b", r"\belement\b", r"\bthermostat\b", r"\bbeater\b",
               r"rack tracks?", r"\bspares?\b", r"\bpump\b", r"stocked part", r"\bconsumable"]),
    "billing": ([r"invoice", r"double charged", r"wrong amount", r"freight charge", r"\bbilling\b", r"\bstatement\b"],
                [r"\binvoice", r"double[- ]charged", r"\bcharged\b", r"\bstatement\b", r"\bbalance\b", r"\bdiscount\b",
                 r"\boverchar", r"freight charge", r"credit note", r"\brefund", r"\bbilled\b", r"\bquote was\b"]),
    "returns": ([r"\breturn", r"\bexchange\b", r"wrong model", r"want to return"],
                [r"\breturn(s|ed|ing)?\b", r"\bexchange\b", r"send (it|them) back", r"\brma\b", r"\bunopened\b",
                 r"wrong (model|item|unit)", r"still in the crate"]),
    "training": ([r"\btraining\b", r"\bmanual\b"],
                 [r"\btraining\b", r"\bmanual\b", r"refresher", r"\btutorial\b", r"operator guide", r"how to (use|clean|program)",
                  r"documentation", r"\bsession\b.*(staff|chef|team)"]),
}
SUBJECT_WEIGHT, BODY_WEIGHT = 3, 1

SPECIAL_ORDER_CLASSES = {"walk_in", "hood"}      # the rubric: special-order returns for walk-ins and hoods


def product_class(order: dict | None) -> str | None:
    if not order:
        return None
    entry = SKU_INDEX.get(order.get("sku", ""))
    return entry[0] if entry else None


def infer_topics(ticket: dict, order: dict | None = None) -> list[tuple[str, int]]:
    """Topics ranked by evidence, best first. Empty when nothing matched."""
    subject = (ticket.get("subject") or "").lower()
    body = (ticket.get("body") or "").lower()
    text = subject + "\n" + body
    scores: dict[str, int] = {}
    for topic, (subj_pats, text_pats) in RULES.items():
        s = sum(SUBJECT_WEIGHT for p in subj_pats if re.search(p, subject))
        s += sum(BODY_WEIGHT for p in text_pats if re.search(p, text))
        if s:
            scores[topic] = s
    if order and not order.get("delivered"):
        scores["delivery"] = scores.get("delivery", 0) + 2      # an undelivered order is a structural signal
    return sorted(scores.items(), key=lambda kv: (-kv[1], TOPICS.index(kv[0])))


def mapped(topic: str, ticket: dict, order: dict | None, customer: dict | None, library: list[dict]) -> list[str]:
    """The desk's map: the governing document for a topic, then the rubric's own
    second choices. Only documents that exist in the (scoped) library are named."""
    ids = {d["doc_id"] for d in library}
    cls = product_class(order)
    by_class = {(d.get("topic"), d.get("product_class")): d["doc_id"] for d in library if d.get("product_class")}
    out: list[str] = []
    if topic == "warranty":
        if cls and (doc := by_class.get(("warranty", cls))):
            out.append(doc)                                     # no class on the ticket: no guessing; the text search fills
    elif topic == "delivery":
        west = ticket.get("region") == "west"
        out += ["REG-WEST-ZONES", "PRC-FREIGHT"] if west else ["PRC-FREIGHT"]
        out += [d["doc_id"] for d in library if d.get("topic") == "regional"]
    elif topic == "installation":
        if cls and (doc := by_class.get(("installation", cls))):
            out.append(doc)
    elif topic == "parts":
        out += ["PRT-CONSUM", "PRT-ORDER", "PRT-AVAIL"] if cls == "small_wares" else ["PRT-ORDER", "PRT-CONSUM", "PRT-AVAIL"]
    elif topic == "billing":
        text = ((ticket.get("subject") or "") + " " + (ticket.get("body") or "")).lower()
        out += ["CRD-ISSUE"]
        out += ["CRD-REFUND", "CRD-GOODWILL"] if re.search(r"double[- ]charged|chargeback|dispute", text) else ["CRD-GOODWILL", "CRD-REFUND"]
        if re.search(r"freight charge", text):
            out.append("PRC-FREIGHT")
    elif topic == "returns":
        first = "RET-SMALL" if cls == "small_wares" else "RET-SPECIAL" if cls in SPECIAL_ORDER_CLASSES else "RET-GEN"
        out += [first] + [d for d in ("RET-GEN", "RET-SMALL", "RET-SPECIAL") if d != first]
    else:                                                       # training and other -> the service-level document for the tier
        tier = (customer or {}).get("tier") or "standard"
        sla = {"standard": "SLA-STD", "preferred": "SLA-PREF", "key": "SLA-KEY"}
        out += [sla.get(tier, "SLA-STD")] + [d for d in ("SLA-STD", "SLA-PREF", "SLA-KEY") if d != sla.get(tier)]
    seen: list[str] = []
    for d in out:
        if d in ids and d not in seen:
            seen.append(d)
    return seen


LIBRARY_QUERY = "warranty installation returns parts credit service delivery pricing data escalation region policy"


def text_query(ticket: dict, order: dict | None) -> str:
    """The baseline's query: subject, the product class from the order's SKU, body."""
    cls = (product_class(order) or "").replace("_", " ")
    return " ".join(x for x in (ticket.get("subject", ""), cls, ticket.get("body") or "") if x)


def rank(ticket: dict, order: dict | None, customer: dict | None, library: list[dict], hits: list[dict],
         k: int = 3) -> list[dict]:
    """Pure: `library` is every document the user may see (with metadata), `hits`
    the text-search results for the ticket. Returns the k most likely governing
    documents, best first, each with `why`."""
    by_id = {d["doc_id"]: d for d in library}
    topics = infer_topics(ticket, order) or [("other", 0)]
    out: list[dict] = []

    def add(doc_id: str, why: str) -> None:
        if doc_id in by_id and all(o["doc_id"] != doc_id for o in out) and len(out) < k:
            out.append(dict(by_id[doc_id], why=why))

    best, best_score = topics[0]
    for doc in mapped(best, ticket, order, customer, library):
        add(doc, f"desk map: {best}")
    for topic, score in topics[1:]:
        if score * 2 >= best_score and len(out) < k:            # a close second topic gets its first document in
            for doc in mapped(topic, ticket, order, customer, library)[:1]:
                add(doc, f"desk map: {topic} (also plausible)")
    for d in sorted(hits, key=lambda d: (d.get("topic") != best, -d.get("score", 0))):   # fill, same topic first
        add(d["doc_id"], "text search" + (f", {best}" if d.get("topic") == best else ""))
    return out


def candidates(ticket: dict, order: dict | None, customer: dict | None, search, k: int = 3) -> list[dict]:
    """`search(query, k)` is the customer's `search_policies` as the acting user.
    Two calls: the whole in-scope library (for metadata), then the ticket's text."""
    library = search(LIBRARY_QUERY, 60)
    hits = search(text_query(ticket, order), 10) if len(library) else []
    return rank(ticket, order, customer, library, hits, k)


def brief(cands: list[dict]) -> list[dict]:
    """What a model should see: id, title, why — not forty paragraphs of policy text."""
    return [{"doc_id": c["doc_id"], "title": c.get("title"), "topic": c.get("topic"), "why": c["why"]} for c in cands]
