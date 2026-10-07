"""Lab 3.2 - Build the research desk (continues Demo 3B: same corpus, specialists and tools).

The desk answers a client question with four specialists: searcher -> analyst -> fact_checker -> writer.
Demo 3B's stage 4 wired them together with four ideas. You write them here:

  TODO 1  contracts   what a valid hand-off from the analyst and the fact-checker looks like
  TODO 2  briefs      what each specialist is given: only the task and the facts it needs
  TODO 3  escalation  when a conflict between reliable sources must go to a human
  TODO 4  API call    the writer: one real Claude call

HOW TO RUN
  python check.py    pass/fail in plain words. Part A needs no key.
  python lab.py      runs the desk on three questions with real Claude (needs ANTHROPIC_API_KEY); then python check.py again
The machinery (running specialists, validating hand-offs, scoring) is in desk_core.py. You do not need to read it.
"""
import hashlib
import json
import pathlib

import desk_core as core
import desk_tools as desk
from claude_client import MODEL_BALANCED, get_client, text_of

# ======================================================================================
# TODO 1 of 4 - CONTRACTS: what each specialist must hand back
# The searcher's contract is given as an example. Write the analyst's and the fact-checker's.
# Types: "str", "bool", "doc_id" (must exist in the corpus), a list of allowed values, ("list", item_type), or a nested dict.
# ======================================================================================
CONTRACTS = {
    "searcher": {"findings": ("list", {"doc_id": "doc_id", "fact": "str", "value": "str"}), "rumours": ("list", "str"),
                 "needs_calculation": "bool", "calc_request": "str"},
    "analyst": {"results": "str"},
    "fact_checker": {"checks": "str"},
}

# ======================================================================================
# TODO 2 of 4 - BRIEFS: the least a specialist needs to do its job
# Replace each function so it returns a brief that carries only the task and the facts.
# ======================================================================================
def searcher_brief(q):
    return ""  # replace this function in TODO 2


def analyst_brief(found):
    return ""  # replace this function in TODO 2


def fact_check_brief(finding):
    return ""  # replace this function in TODO 2


# ======================================================================================
# TODO 3 of 4 - ESCALATION decided in code, not by hope
# checks: the fact-checker's list of {"doc_id", "claim", "verdict", "detail"}
# ======================================================================================
def has_conflict(checks):
    """True when any check found two reliable sources that disagree."""
    return False  # replace this line in TODO 3


# ======================================================================================
# TODO 4 of 4 - your Claude API call: the writer (no tools, one call)
# `brief` is the verified facts. core.WRITER_SYSTEM tells the writer how to write the report.
# ======================================================================================
def call_writer(brief):
    """Send `brief` to Claude and return the report text."""
    return ""  # replace this line in TODO 4


# ======================================================================================
# RUNNING THE DESK - do not edit below this line
# ======================================================================================
HERE = pathlib.Path(__file__).parent
RESULTS_FILE = HERE / "results" / "run.json"
QUESTION_IDS = ("Q2", "Q4", "Q5")  # Q2 two reliable reports disagree, Q4 needs a calculation, Q5 has a rumour
HOOKS = {"contracts": CONTRACTS, "searcher_brief": searcher_brief, "analyst_brief": analyst_brief,
         "fact_check_brief": fact_check_brief, "has_conflict": has_conflict, "call_writer": call_writer}


def source_fingerprint():
    return hashlib.sha256((HERE / "lab.py").read_bytes()).hexdigest()[:16]


def run_all(caller=None):
    rows = []
    for qid in QUESTION_IDS:
        q = desk.QUESTIONS[qid]
        report, notes = core.orchestrate(q, HOOKS, caller)
        checks = core.score(q, report)
        rows.append({"id": qid, "checks": checks, "notes": notes, "report": report})
        failed = [k for k, ok in checks.items() if not ok]
        print(f"{qid}: {'FAIL' if failed else 'PASS'} | {notes}" + (f" | failed: {', '.join(failed)}" if failed else ""))
    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text(json.dumps({"fingerprint": source_fingerprint(), "rows": rows}, indent=1), encoding="utf-8")
    print("\nSaved to results/run.json. Now run: python check.py")


if __name__ == "__main__":
    run_all()
