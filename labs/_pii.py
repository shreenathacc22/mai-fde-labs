# -*- coding: utf-8 -*-
"""PII sanitization for the lab 2b chat — nothing comes in or goes out.

One function, `redact()`, applied at every boundary of the chat (see lab_2b_multiagent.py):

    IN    the person's message, before the graph (or the model) sees it
    TOOLS every MCP tool result, before any specialist sees it; every tool argument,
          before it is written back to the estate
    OUT   every message and gate card returned to the page or terminal

Code, not a prompt: a prompt asks the model not to repeat a card number; this makes sure
the model never had it. Two layers:

    1. structured: in JSON tool results, the customer PII fields (_estate.PII_FIELDS:
       contact_name, email, phone, address) are replaced whole, whatever they contain;
    2. patterns: card numbers (Luhn-checked, last four kept), expiry, CVV, SSN, email, phone,
       street addresses, gate / door / access codes, bank account and routing numbers.

Ids the desk works with (T-30031, O-27595, C-1041) are never touched: they are short and
prefixed, and none of the patterns below can match them.
"""
from __future__ import annotations

import json
import re

PII_FIELDS = ("contact_name", "email", "phone", "address")   # same list as _estate.PII_FIELDS


def _luhn(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
        alt = not alt
    return total % 10 == 0


def _card(m: re.Match) -> str:
    digits = re.sub(r"\D", "", m.group(0))
    if not 13 <= len(digits) <= 19 or not _luhn(digits):
        return m.group(0)
    return f"[REDACTED CARD ending {digits[-4:]}]"


_SUFFIX = (r"(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Way|Court|Ct|Boulevard|Blvd|Place|Pl|"
           r"Terrace|Ter|Circle|Cir|Parkway|Pkwy|Highway|Hwy|Hill|Trail|Trl|Row|Square|Sq)\b\.?")

# order matters: the most specific patterns run first
_PATTERNS: list[tuple[re.Pattern, object]] = [
    (re.compile(r"\b(?:\d[ -]?){12,18}\d\b"), _card),
    (re.compile(r"(?i)\b(?:exp(?:iry|ires|iration)?\.?|valid thru)\s*:?\s*\d{1,2}\s*/\s*\d{2,4}"), "exp [REDACTED]"),
    (re.compile(r"(?i)\b(?:CVV2?|CVC2?|CID|security code)\s*:?\s*#?\s*\d{3,4}\b"), "[REDACTED CVV]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED SSN]"),
    (re.compile(r"(?i)\b(?:SSN|social(?: security)?(?: number| no\.?)?)\s*(?:is|:|#)?\s*\d{9}\b"), "[REDACTED SSN]"),
    (re.compile(r"(?i)\b(?:account|acct|routing|IBAN|sort code)\s*(?:number|no\.?|#)?\s*(?:is|:)?\s*[A-Z0-9][A-Z0-9 -]{5,32}\d\b"),
     "[REDACTED ACCOUNT]"),
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[REDACTED EMAIL]"),
    (re.compile(r"(?:\+?1[ .-]?)?(?:\(\d{3}\)\s?|\b\d{3}[ .-])\d{3}[ .-]\d{4}\b"), "[REDACTED PHONE]"),
    (re.compile(r"\b\d{1,6}\s+(?:[A-Z][A-Za-z'-]*\s+){1,4}" + _SUFFIX +
                r"(?:,?\s*(?:Apt|Apartment|Suite|Ste|Unit|#)\.?\s*[\w-]+)?"
                r"(?:,\s*[A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)*)?(?:,?\s*[A-Z]{2})?(?:\s+\d{5}(?:-\d{4})?)?"),
     "[REDACTED ADDRESS]"),
    (re.compile(r"(?i)\b(?:gate|door|access|entry|alarm|lockbox|key ?pad)\s*(?:code|pin)\s*(?:is|:|#)?\s*[\w*#-]*\d[\w*#-]*"),
     "[REDACTED ACCESS CODE]"),
]


def redact_text(text: str) -> str:
    """Pattern layer only. Safe on any string; returns it unchanged when there is no PII."""
    if not text:
        return text
    for pat, repl in _PATTERNS:
        text = pat.sub(repl, text)
    return text


def _walk(v):
    if isinstance(v, dict):
        return {k: ("[REDACTED]" if k in PII_FIELDS and v[k] not in (None, "") else _walk(x)) for k, x in v.items()}
    if isinstance(v, list):
        return [_walk(x) for x in v]
    if isinstance(v, str):
        return redact_text(v)
    return v


def redact(value):
    """Any value: dicts and lists are walked (PII fields dropped whole), strings are
    pattern-redacted, and a string that is a JSON document is parsed, cleaned and
    re-serialised so structured tool results get the field layer too."""
    if isinstance(value, str):
        s = value.strip()
        if s[:1] in "{[":
            try:
                return json.dumps(_walk(json.loads(s)), ensure_ascii=False)
            except (json.JSONDecodeError, ValueError):
                pass
        return redact_text(value)
    return _walk(value)
