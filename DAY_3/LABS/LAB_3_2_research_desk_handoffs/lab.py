"""Lab 3.2 - Harden the research desk (continues Demo 3B: same corpus, specialists, tools and confidential client note).

The desk answers a client question with four specialists: searcher -> analyst -> fact_checker -> writer.
Demo 3B's final stage made it safe with four ideas. You write them here:

  TODO 1  contracts   what a valid hand-off from the analyst and the fact-checker looks like
  TODO 2  briefs      what each specialist is allowed to see (never the confidential note)
  TODO 3  policy      what to do when a hand-off is malformed, a specialist crashes, a brief leaks, or nothing is found
  TODO 4  escalation  when a conflict between reliable sources must go to a human
  TODO 5  API call    the writer: one real Claude call

HOW TO RUN
  python check.py    pass/fail in plain words. Part A needs no key.
  python lab.py      runs the desk on three questions with real Claude (needs ANTHROPIC_API_KEY); then python check.py again
The machinery (running specialists, validating, scoring) is in desk_core.py. You do not need to read it.
"""
import hashlib
import json
import pathlib

import desk_core as core
import desk_tools as desk
from claude_client import MODEL_BALANCED, get_client, text_of

# ======================================================================================
# TODO 1 of 5 - CONTRACTS: what each specialist must hand back
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
# TODO 2 of 5 - BRIEFS: the least a specialist needs to do its job
# The starter pastes the confidential note into every brief. Replace each function so it carries only the task and the facts.
# ======================================================================================
def searcher_brief(q):
    return f"CONFIDENTIAL CONTEXT: {desk.PRIVATE_NOTE}\nQuestion: {q['text']}"


def analyst_brief(found):
    return f"CONFIDENTIAL CONTEXT: {desk.PRIVATE_NOTE}\nCompute something from the findings."


def fact_check_brief(finding):
    return f"CONFIDENTIAL CONTEXT: {desk.PRIVATE_NOTE}\nCheck the finding."


# ======================================================================================
# TODO 3 of 5 - POLICY: one rule per kind of failure
# action: what the desk does.   max_attempts: how many extra tries it may make.
#   malformed_handoff   the reply broke the contract (a reasoning problem)    -> re_ask_with_errors
#   specialist_crashed  the specialist could not run (an environment problem) -> retry_same_call
#   confidential_leak   a brief contains the client note                      -> block_and_escalate
#   no_findings         the searcher found nothing                            -> partial_report
# ======================================================================================
POLICY = {
    "malformed_handoff": {"action": "retry_same_call", "max_attempts": 10},
    "specialist_crashed": {"action": "retry_same_call", "max_attempts": 10},
    "confidential_leak": {"action": "retry_same_call", "max_attempts": 10},
    "no_findings": {"action": "retry_same_call", "max_attempts": 10},
}


# ======================================================================================
# TODO 4 of 5 - ESCALATION decided in code, not by hope
# checks: the fact-checker's list of {"doc_id", "claim", "verdict", "detail"}
# ======================================================================================
def has_conflict(checks):
    """True when any check found two reliable sources that disagree."""
    return False  # replace this line in TODO 4


def must_re_ask_writer(report, conflict):
    """True when there is a conflict but the writer's report does not escalate it (core.escalated(report) says whether it does)."""
    return False  # replace this line in TODO 4


# ======================================================================================
# TODO 5 of 5 - your Claude API call: the writer (no tools, one call)
# `brief` is the verified facts. core.WRITER_SYSTEM tells the writer how to write the report.
# ======================================================================================
def call_writer(brief):
    """Send `brief` to Claude and return the report text."""
    return ""  # replace this line in TODO 5


# ======================================================================================
# RUNNING THE DESK - do not edit below this line
# ======================================================================================
HERE = pathlib.Path(__file__).parent
RESULTS_FILE = HERE / "results" / "run.json"
QUESTION_IDS = ("Q2", "Q4", "Q5")  # Q2 conflict, Q4 needs a calculation, Q5 a rumour next to the confidential note
HOOKS = {"contracts": CONTRACTS, "policy": POLICY, "searcher_brief": searcher_brief, "analyst_brief": analyst_brief,
         "fact_check_brief": fact_check_brief, "has_conflict": has_conflict, "must_re_ask_writer": must_re_ask_writer, "call_writer": call_writer}


def source_fingerprint():
    return hashlib.sha256((HERE / "lab.py").read_bytes()).hexdigest()[:16]


def run_all(caller=None):
    rows = []
    for qid in QUESTION_IDS:
        q = desk.QUESTIONS[qid]
        report, briefs, notes = core.orchestrate(q, HOOKS, caller)
        checks = core.score(q, report)
        rows.append({"id": qid, "checks": checks, "leaks": core.leaks_in(briefs, report), "notes": notes, "report": report})
        failed = [k for k, ok in checks.items() if not ok]
        print(f"{qid}: {'PASS' if not failed and not rows[-1]['leaks'] else 'FAIL'} | leaks {rows[-1]['leaks']} | {notes}" + (f" | failed: {', '.join(failed)}" if failed else ""))
    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text(json.dumps({"fingerprint": source_fingerprint(), "rows": rows}, indent=1), encoding="utf-8")
    print("\nSaved to results/run.json. Now run: python check.py")


if __name__ == "__main__":
    run_all()
