"""The 'before': the regex extractor the AP team has maintained for years. No Claude anywhere.

It was written against the first vendor templates (US layouts, English labels, dot decimals) and has
been patched whenever a new vendor complained. It is the baseline every prompt version must beat -
and the thing a CFO will compare you against.
"""
from __future__ import annotations

import re
from datetime import datetime

_NUM = r"([\d][\d,]*\.\d{2})"
_DATE_FORMATS = ["%B %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%d %b %Y"]


def _first(pattern: str, text: str, flags=re.I):
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else None


def _to_iso(raw: str | None):
    if not raw:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _money(raw: str | None):
    return float(raw.replace(",", "")) if raw else None


def extract(text: str) -> dict:
    lines = [line for line in text.splitlines() if line.strip()]
    currency = "USD" if "$" in text else None
    return {
        "invoice_number": _first(r"invoice\s*(?:no\.?|number|#)\s*:?\s*([A-Z0-9][\w\-/]+)", text),
        "vendor": lines[0].title() if lines else None,
        "invoice_date": _to_iso(_first(r"\bdate\s*:?\s*([A-Za-z0-9 ,/\-]+?)(?:\s{2,}|$)", text, re.I | re.M)),
        "due_date": _to_iso(_first(r"due(?:\s*date)?\s*:\s*([A-Za-z0-9 ,/\-]+?)(?:\s{2,}|$)", text, re.I | re.M)),
        "currency": currency,
        "subtotal": _money(_first(r"subtotal\s*\$?" + _NUM, text)),
        "tax": _money(_first(r"(?:sales\s*)?tax[^\n$]*\$" + _NUM, text)),
        "total": _money(_first(r"total(?:\s*due)?\s*\$" + _NUM, text)),
        "line_items": [],
        "po_number": _first(r"(?:PO\s*(?:number|no\.?)?|customer po)\s*:?\s*([A-Z0-9][\w\-]+)", text),
    }
