"""Demo 5G - The detective's memory for one case. Plain Python: no SDK, no model, no network.

results/notes_<case>.md       the WORKING NOTES: facts found, hypotheses, next step. The agent writes and re-reads them.
                              They live on disk, so they survive a compaction and a restart.
results/case_history.jsonl    one line per finished run: the final findings. A new run of the same case starts from it.
results/archive/              copies of the transcript, saved by the PreCompact hook before the SDK compacts.
"""
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

NOTES_READ_MAX_CHARS = 3000  # read_notes returns at most this much (the newest part)
CASE_NAME = re.compile(r"^[a-z0-9-]{1,40}$")


# -- Paths ---------------------------------------------------------------------------------------------------

def check_case_name(case):
    """Only lower-case letters, digits and dashes. The name becomes part of a file name, so nothing else is allowed."""
    if not CASE_NAME.match(case):
        raise ValueError(f"Case name '{case}' must be 1-40 characters: a-z, 0-9 and dashes.")
    return case


def notes_path(folder, case):
    """The notes file of one case."""
    return Path(folder) / f"notes_{check_case_name(case)}.md"


def history_path(folder):
    """The one history file for all cases."""
    return Path(folder) / "case_history.jsonl"


# -- Working notes --------------------------------------------------------------------------------------------

def append_note(folder, case, text, run):
    """Add one line to the notes of this case and return it."""
    path = notes_path(folder, case)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = f"- (run {run}) {text.strip()}\n"
    with path.open("a", encoding="utf-8") as notes:
        notes.write(line)
    return line


def read_notes(folder, case):
    """The whole notes text of this case, or an empty string."""
    path = notes_path(folder, case)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_notes_bounded(folder, case):
    """The notes as the agent sees them: the newest NOTES_READ_MAX_CHARS characters, with a hint when the start was cut."""
    text = read_notes(folder, case)
    if not text:
        return "(no notes yet for this case)"
    if len(text) <= NOTES_READ_MAX_CHARS:
        return text
    return f"[Truncated: older notes not shown.]\n{text[-NOTES_READ_MAX_CHARS:]}"


# -- Case history -------------------------------------------------------------------------------------------

def load_history(folder, case):
    """The finished runs of this case, oldest first."""
    path = history_path(folder)
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [row for row in rows if row["case"] == case]


def add_history(folder, record):
    """Append one finished run to the history file."""
    path = history_path(folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), **record}
    with path.open("a", encoding="utf-8") as history:
        history.write(json.dumps(row) + "\n")
    return row


def describe_history(rows):
    """The history as lines for the screen."""
    if not rows:
        return "    (no finished runs yet)"
    return "\n".join(f"    run {row['run']}, {row['time']}, {row['turns']} turns, ${row['cost_usd']:.2f}, retention {row['retention']}\n"
                     f"      findings: {row['findings'][:200].strip()}..." for row in rows)


def start_block(history):
    """Text for the start of the task when this case was investigated before. Empty for a new case."""
    if not history:
        return ""
    last = history[-1]
    return (f"\n\nThis case was investigated {len(history)} time(s) before. The findings of the last run were:\n{last['findings']}\n"
            "Your working notes from earlier runs are saved. Call read_notes first, check only what is missing, then update your notes "
            "and give your findings again.")


# -- Retention check -----------------------------------------------------------------------------------------

def missing_facts(notes_text, key_facts):
    """The key facts that no keyword of theirs matches in the notes. The retention check passes when this is empty."""
    lowered = notes_text.lower()
    return [fact for fact, keywords in key_facts.items() if not any(word in lowered for word in keywords)]


# -- The PreCompact archive ------------------------------------------------------------------------------------

def archive_transcript(transcript_path, folder, case):
    """Copy the transcript file to results/archive before the SDK compacts. Return the new path, or None when there is no file."""
    source = Path(transcript_path or "")
    if not source.is_file():
        return None
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target = folder / f"{check_case_name(case)}_{stamp}.jsonl"
    shutil.copy(source, target)
    return target
