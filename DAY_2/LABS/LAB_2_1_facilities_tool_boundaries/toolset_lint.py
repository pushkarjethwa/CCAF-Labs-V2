"""Cheap static checks on a toolset. Used by lab.py (feedback) and check.py (gate). No API key needed.

These are lint rules, not proof of good selection: they catch structural mistakes (missing when-NOT-to-use,
too many tools per scope, two routes to one capability).
"""
import re

from toolset_original import ALL_CAPABILITIES

MAX_TOOLS_PER_SCOPE = 7
MAX_TOOLS_TOTAL = 8
SIMILARITY_LIMIT = 0.5  # two tools whose "use when" text overlaps this much are probably duplicates
WHEN = re.compile(r"\b(use (this tool |this )?(when|to|for)|call (this )?(when|to))\b", re.I)
WHEN_NOT = re.compile(r"(do not use|don't use|not for)", re.I)
NAME = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")
FILLER = set("a an the and or of to for in on at is are be it its this that with from by as i we you me my our can could would should "
             "please need want get give show tell what which who when where how do does any all some new use used using tool then than "
             "into about only also not no if so up out over per via has have had will am been being was were there their they them".split())


def use_words(description):
    """The words of the 'use when' part of a description (everything before 'Do NOT use' / 'Not for')."""
    marker = WHEN_NOT.search(description or "")
    text = description[:marker.start()] if marker else (description or "")
    return {w.lower().rstrip("s") for w in re.findall(r"[A-Za-z0-9]+", text) if w.lower() not in FILLER and len(w) > 1}


def routes(cap_map):
    """capability -> list of routes ("tool" or "tool:action") that reach it."""
    out = {}
    for route, capability in cap_map.items():
        out.setdefault(capability, []).append(route)
    return out


def lint(tools, cap_map, scopes):
    """Return a list of (check name, passed, detail)."""
    results = []
    names = [t["name"] for t in tools]
    bad_schema = [t["name"] for t in tools if not NAME.match(t["name"]) or t.get("input_schema", {}).get("type") != "object"]
    results.append(("schema", not bad_schema and len(set(names)) == len(names), f"bad or duplicate names: {bad_schema or 'none'}"))
    results.append(("tool_count", len(tools) <= MAX_TOOLS_TOTAL, f"{len(tools)} tools (limit {MAX_TOOLS_TOTAL})"))

    no_when = [t["name"] for t in tools if not WHEN.search(t.get("description", ""))]
    no_not = [t["name"] for t in tools if not WHEN_NOT.search(t.get("description", ""))]
    short = [t["name"] for t in tools if len(t.get("description", "")) < 100]
    results.append(("when_to_use", not no_when, f"missing 'Use when ...': {no_when or 'none'}"))
    results.append(("when_not_to_use", not no_not, f"missing 'Do NOT use ... / Not for ...': {no_not or 'none'}"))
    results.append(("description_length", not short, f"under 100 chars: {short or 'none'}"))

    too_big = {ctx: len(v) for ctx, v in scopes.items() if len(v) > MAX_TOOLS_PER_SCOPE}
    unknown = sorted({n for v in scopes.values() for n in v if n not in names})
    results.append(("scope_size", not too_big and bool(scopes), f"scopes over {MAX_TOOLS_PER_SCOPE}: {too_big or 'none'}"))
    results.append(("scope_names", not unknown, f"unknown tool names in scopes: {unknown or 'none'}"))

    by_capability = routes(cap_map)
    missing = [c for c in ALL_CAPABILITIES if c not in by_capability]
    duplicated = {c: r for c, r in by_capability.items() if len(r) > 1}
    action_enum = {t["name"]: (t.get("input_schema", {}).get("properties", {}).get("action") or {}).get("enum") for t in tools}
    dangling = []
    for route in cap_map:
        tool, _, action = route.partition(":")
        if tool not in names or (action and action not in (action_enum.get(tool) or [])) or (not action and action_enum.get(tool)):
            dangling.append(route)
    results.append(("capability_coverage", not missing, f"capabilities with no route: {missing or 'none'}"))
    results.append(("capability_map_valid", not dangling, f"map routes pointing at nothing: {dangling or 'none'}"))
    results.append(("no_duplicate_routes", not duplicated, f"capabilities reachable by more than one route: {duplicated or 'none'}"))

    words = {t["name"]: use_words(t.get("description", "")) for t in tools}
    similar = []
    for i, first in enumerate(words):
        for second in list(words)[i + 1:]:
            union = words[first] | words[second]
            overlap = len(words[first] & words[second]) / len(union) if union else 0.0
            if overlap >= SIMILARITY_LIMIT:
                similar.append((first, second, round(overlap, 2)))
    results.append(("no_duplicate_purpose_text", not similar, f"'use when' text too similar (>= {SIMILARITY_LIMIT}): {similar or 'none'}"))
    return results
