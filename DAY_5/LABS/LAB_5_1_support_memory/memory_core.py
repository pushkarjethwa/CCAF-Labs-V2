"""memory_core.py - the plumbing for Lab 5.1 (continues Demo 5A). You do not need to read or edit this file.

It loads the guest and the five booking sessions, and holds the small helpers that lab.py uses:
reading and writing the files in results/, matching a message to topics, and the check for marketing offers.
"""
import json
import pathlib
import re
from datetime import date

HERE = pathlib.Path(__file__).parent
RESULTS_DIR = HERE / "results"

DATA = json.loads((HERE / "data" / "sessions.json").read_text(encoding="utf-8"))
CUSTOMER = DATA["customer"]
SESSIONS = DATA["sessions"]
SCOPE = {"tenant": CUSTOMER["tenant"], "user": CUSTOMER["user_id"]}
TODAY = date.fromisoformat(SESSIONS[-1]["date"])  # "today" is the day of the last session, so the lab is repeatable
DEFAULT_TTL_DAYS = 90
REQUEST = SESSIONS[-1]["turns"][0][1]  # session 5 holds only this one message

SUPPORT_SYSTEM = (f"You are a reservations agent for Harbor Lane Hotels, helping {CUSTOMER['user']} from {CUSTOMER['company']}. "
                  "Reply in at most 70 words. Follow every rule and fact you are given exactly.")
TAGS = ["contact", "billing", "room", "booking", "schedule"]
EXTRACT_SYSTEM = ("Extract the durable facts from this hotel booking session. A durable fact is still true next month. "
                  "Skip small talk and one-off events. Return only a JSON list. Each item has: "
                  "\"fact\" (one short sentence), \"tags\" (a list chosen from " + ", ".join(TAGS) + "), "
                  "\"hard_rule\" (true only for a rule we must never break).")
SUMMARY_SYSTEM = "Summarise these hotel booking sessions in at most 90 words. Plain sentences. Keep names, numbers and decisions."
TAG_WORDS = {"contact": ["email", "e-mail", "newsletter", "offer", "message", "phone", "chat", "marketing"],
             "billing": ["receipt", "card", "payment", "invoice", "charge"],
             "room": ["room type", "pillow", "bedding", "floor", "quiet"],
             "booking": ["stay", "night", "book", "extend", "cancel", "rate", "porto", "lisbon"],
             "schedule": ["check-in", "arrive", "arrival", "flight", "late"]}


def transcript(sessions):
    """Turn sessions into plain text, one line per turn."""
    lines = []
    for session in sessions:
        lines.append(f"Session {session['id']} ({session['date']}), {session['topic']}:")
        lines.extend(f"  {speaker}: {words}" for speaker, words in session["turns"])
    return "\n".join(lines)


def read_json(name, default=None):
    """Read a file from results/, or return the default when it does not exist yet."""
    path = RESULTS_DIR / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(name, data):
    """Write a file into results/, creating the folder if needed."""
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / name).write_text(json.dumps(data, indent=2), encoding="utf-8")


def parse_json_list(text):
    """Find the JSON list inside a reply, even if the model wrapped it in prose or a code fence."""
    return json.loads(text[text.index("["):text.rindex("]") + 1])


def add_new_facts(memory, records):
    """Append the records whose fact text is not stored yet. Returns how many were added."""
    known = {record["fact"] for record in memory}
    fresh = [record for record in records if record["fact"] not in known]
    memory.extend(fresh)
    return len(fresh)


def is_current(record, today):
    """A fact is current when it has no time to live, or when it has not run out yet."""
    age = (today - date.fromisoformat(record["saved_at"])).days
    return record["ttl_days"] is None or age <= record["ttl_days"]


def tags_for(text):
    """Find the topics a message is about, by simple keyword match."""
    lowered = text.lower()
    return {tag for tag, words in TAG_WORDS.items() if any(word in lowered for word in words)}


def estimate_tokens(text):
    """A rough token count: one token is about four characters."""
    return len(text) // 4


MARKETING_WORDS = ("offer", "deal", "newsletter", "marketing", "promotion")
EMAIL_WORDS = ("email", "e-mail", "mail", "send", "subscribe")
NEGATIONS = ("not", "never", "cannot", "no", "without", "instead")


def offers_marketing(reply):
    """True when a sentence promises marketing email and does not refuse it. A plain string check, no model."""
    text = reply.lower().replace("’", "'")
    for sentence in re.split(r"[.!?]", text):
        words = re.findall(r"[a-z'-]+", sentence)
        marketing = any(w.startswith(MARKETING_WORDS) for w in words)
        emails = any(w.startswith(EMAIL_WORDS) for w in words)
        refuses = any(w in NEGATIONS or w.endswith("n't") for w in words)
        if marketing and emails and not refuses:
            return True
    return False
