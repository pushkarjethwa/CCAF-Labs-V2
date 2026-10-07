"""research_tools.py - the deterministic tool layer of the research desk (Demo 3G). DO NOT EDIT.

Facts and arithmetic belong in code, not in a model's head: search and fetch read a local 40-document corpus, dates are parsed by rules,
and CAGR and division are computed exactly. No model calls in this file.
"""
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

DATA = Path(__file__).parent / "data"
CORPUS = {doc["doc_id"]: doc
          for doc in (json.loads(p.read_text(encoding="utf-8")) for p in sorted((DATA / "corpus").glob("DOC-*.json")))}


def search_corpus(args: dict) -> str:
    """Rank documents by how many query words they contain. Returns metadata and a snippet only."""
    words = {w for w in re.findall(r"[a-z0-9$%.]+", args["query"].lower()) if len(w) > 2}
    scored = []
    for doc in CORPUS.values():
        haystack = " ".join([doc["title"], doc["text"], *doc["companies"], *(f["topic"] for f in doc["facts"])]).lower()
        hits = sum(word in haystack for word in words)
        if hits:
            scored.append((hits, doc))
    scored.sort(key=lambda pair: -pair[0])
    return json.dumps([
        {"doc_id": d["doc_id"], "title": d["title"], "publisher": d["publisher"], "source_type": d["source_type"],
         "published_raw": d["published_raw"], "date_format": d["date_format"], "reliability": d["reliability"],
         "superseded_by": d["superseded_by"], "mirror_of": d["mirror_of"], "snippet": d["text"][:160]}
        for _, d in scored[: int(args.get("limit", 6))]
    ], indent=1)


def fetch_document(args: dict) -> str:
    doc = CORPUS.get(args["doc_id"])
    return json.dumps(doc, indent=1) if doc else f"No document {args['doc_id']}."


def normalize_date(args: dict) -> str:
    raw, fmt = args["raw"], args["date_format"]
    patterns = {"Mon D, YYYY": "%b %d, %Y", "YYYY-MM-DD": "%Y-%m-%d", "DD/MM/YYYY": "%d/%m/%Y", "MM/DD/YYYY": "%m/%d/%Y"}
    if fmt == "Qn YYYY":
        quarter, year = raw.split()
        return f"{year}-{quarter}"
    if fmt not in patterns:
        return f"Unknown date_format {fmt!r}."
    return datetime.strptime(raw, patterns[fmt]).date().isoformat()


def cagr(args: dict) -> str:
    start, end, years = float(args["start_value"]), float(args["end_value"]), float(args["years"])
    return f"{((end / start) ** (1 / years) - 1) * 100:.1f}%"


def divide(args: dict) -> str:
    return f"{float(args['numerator']) / float(args['denominator']):.2f}"


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict
    run: Callable[[dict], str]


def _obj(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


_TEXT, _NUM = {"type": "string"}, {"type": "number"}

TOOL_SPECS = [
    ToolSpec("search_corpus", "Search the document corpus. Returns ranked metadata (reliability, date, superseded_by, "
             "mirror_of) and a snippet. Call fetch_document for the full text.",
             _obj({"query": _TEXT, "limit": {"type": "integer"}}, ["query"]), search_corpus),
    ToolSpec("fetch_document", "Return one full document, including its facts, by doc_id (for example DOC-002).",
             _obj({"doc_id": _TEXT}, ["doc_id"]), fetch_document),
    ToolSpec("normalize_date", "Convert a document's published_raw date to ISO form, using its date_format field. "
             "Needed because 03/04/2026 can mean 3 April or 4 March.",
             _obj({"raw": _TEXT, "date_format": _TEXT}, ["raw", "date_format"]), normalize_date),
    ToolSpec("cagr", "Compound annual growth rate in percent. years = the number of years BETWEEN the two values.",
             _obj({"start_value": _NUM, "end_value": _NUM, "years": _NUM}, ["start_value", "end_value", "years"]), cagr),
    ToolSpec("divide", "Divide two numbers exactly, rounded to 2 decimals. Use it for every ratio or per-unit price.",
             _obj({"numerator": _NUM, "denominator": _NUM}, ["numerator", "denominator"]), divide),
]
