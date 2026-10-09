"""Demo 5E - One memory file per customer card. Plain Python: no SDK, no model, no network.

results/memory/<card_id>.json holds:
    card_id        the customer card this file belongs to
    summary        a short text (at most six lines) of what the customer asked for and what is still open
    pinned_rules   the customer's rules in their exact words. They are never dropped.
    facts          a short list of durable facts (name, allergy, favourite drink)
    last_session   when the file was last saved
    turns_total    how many customer messages this card has sent, over all chats
"""
import json
from datetime import datetime, timezone
from pathlib import Path

SUMMARY_MAX_LINES = 6
MAX_FACTS = 12  # the oldest facts go first. Pinned rules are never trimmed.


# -- Read and write -----------------------------------------------------------------------------------------

def path_for(folder, card_id):
    """The one file for one card. No other card's file is ever opened."""
    return Path(folder) / f"{card_id}.json"


def blank(card_id):
    """An empty memory, for a customer we have not met."""
    return {"card_id": card_id, "summary": "", "pinned_rules": [], "facts": [], "last_session": None, "turns_total": 0}


def load(folder, card_id):
    """The saved memory for this card, or None when the file does not exist."""
    path = path_for(folder, card_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def save(folder, memory):
    """Write the memory file for its card and return the path."""
    path = path_for(folder, memory["card_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(memory, indent=2), encoding="utf-8")
    return path


# -- Clean up what the model returns -----------------------------------------------------------------------

def clip_summary(text, max_lines=SUMMARY_MAX_LINES):
    """Keep at most six non-empty lines of the model's summary."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines[:max_lines])


def clean_list(value):
    """A list of non-empty strings. Anything else becomes an empty list."""
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def parse_found(text):
    """Turn the model's JSON reply into {'pinned_rules': [...], 'facts': [...]}. Unusable text gives two empty lists."""
    try:
        data = json.loads(text[text.find("{"):text.rfind("}") + 1])
    except ValueError:
        data = {}
    data = data if isinstance(data, dict) else {}
    return {"pinned_rules": clean_list(data.get("pinned_rules")), "facts": clean_list(data.get("facts"))}


# -- Merge and check ---------------------------------------------------------------------------------------

def union(old_items, new_items):
    """Old items first, then the new ones that are not already there (compared without capital letters)."""
    result = list(old_items)
    for item in new_items:
        if item.lower() not in [kept.lower() for kept in result]:
            result.append(item)
    return result


def merge(old, summary, found, new_turns):
    """The memory to save. The summary is replaced. Pinned rules and facts are old plus new, so no rule is lost."""
    return {"card_id": old["card_id"], "summary": clip_summary(summary),
            "pinned_rules": union(old["pinned_rules"], found["pinned_rules"]),
            "facts": union(old["facts"], found["facts"])[-MAX_FACTS:],
            "last_session": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "turns_total": old["turns_total"] + new_turns}


def missing_rules(old, new):
    """The old pinned rules that the new memory does not hold. The retention check passes when this is empty."""
    kept = [rule.lower() for rule in new["pinned_rules"]]
    return [rule for rule in old["pinned_rules"] if rule.lower() not in kept]


# -- Show it ------------------------------------------------------------------------------------------------

def describe(memory):
    """The memory as lines for the screen."""
    rules = "\n".join(f"      - {rule}" for rule in memory["pinned_rules"]) or "      (none)"
    facts = "\n".join(f"      - {fact}" for fact in memory["facts"]) or "      (none)"
    summary = memory["summary"].replace("\n", "\n      ") or "(none)"
    return (f"    card {memory['card_id']}, {memory['turns_total']} messages so far, last session {memory['last_session']}\n"
            f"    summary:\n      {summary}\n    pinned rules:\n{rules}\n    facts:\n{facts}")


def prompt_block(memory):
    """The memory as text for the system prompt of a new session. Empty for a customer with no memory."""
    if not (memory["summary"] or memory["pinned_rules"] or memory["facts"]):
        return ""
    rules = "\n".join(f"- {rule}" for rule in memory["pinned_rules"]) or "- (none)"
    facts = "\n".join(f"- {fact}" for fact in memory["facts"]) or "- (none)"
    return (f"\n\nWhat we saved about this customer (card {memory['card_id']}):\nSummary of earlier chats:\n{memory['summary'] or '(none)'}\n"
            f"Pinned rules (follow them exactly, always):\n{rules}\nFacts:\n{facts}")
