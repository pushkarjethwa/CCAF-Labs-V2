"""Lab 2.5 - Library assistant: build a tool and the tool loop yourself, one stage at a time.

This lab continues Demos 2B and 2C (the loop as a state machine, and tool errors that the model can read), on a small library assistant.
Claude cannot know where a book is shelved or when a loan is due. You write the tool schema, the dispatcher and the loop with the plain
Anthropic SDK, so no magic is left.

WHAT YOU EDIT (four places, each marked "TODO n of 4"; the guide in README.md gives the exact code for each)
  TODO 1  CHECK_DUE_DATE_TOOL  -> stage 2: the schema, the only thing Claude knows about your tool
  TODO 2  run_tool             -> stage 3: run the function Claude asked for
  TODO 3  answer               -> stage 3: the loop: send, run tools, send ALL results back in one message, repeat
  TODO 4  run_tool_safely      -> stage 4: errors and crashes become tool_results, so the loop never dies

HOW TO RUN (in order)
  python lab.py --stage 1      no tools: the baseline (needs no code from you)
  python lab.py --stage 2      your schema: Claude asks for a tool
  python lab.py --stage 3      your loop: the tool runs
  python lab.py --stage 4      errors, crashes and a loop that always ends
  python check.py              pass/fail in plain words
"""
import argparse
import json

import library_core as core
from claude_client import MODEL_BALANCED, ask, text_of, tool_calls_of

MAX_TURNS = 6  # a loop must always have an exit
SYSTEM = "You are a helpful library assistant. Use the tools for facts about books and loans. Answer in one or two sentences."

# ---------------------------------------------------------------- the real functions (given). No Claude in here.
BOOKS = {"dune": {"title": "Dune", "shelf": "SF-12", "copies_available": 2},
         "emma": {"title": "Emma", "shelf": "CL-03", "copies_available": 0}}
LOANS = {"M-100": {"title": "Dune", "due": "2026-10-20"}, "M-200": {"title": "Emma", "due": "2026-10-08"}}


def find_book(title):
    book = BOOKS.get(title.strip().lower())
    return book if book else {"error": "book_not_found", "title": title}


def check_due_date(member_id):
    loan = LOANS.get(member_id)
    return {"member_id": member_id, **loan} if loan else {"error": "no_loan_found", "member_id": member_id}


# ---------------------------------------------------------------- the schemas
FIND_BOOK_TOOL = {  # a finished example: read how the description says WHEN to use the tool
    "name": "find_book",
    "description": "Look up one book by title: its shelf code and how many copies are available. Use when someone asks where a book is or whether it is in. Read-only.",
    "input_schema": {"type": "object", "properties": {"title": {"type": "string", "description": "Book title, e.g. Dune"}}, "required": ["title"]},
}


# ======================================================================================
# TODO 1 of 4 - the schema of check_due_date (stage 2).
# Write the same three parts as FIND_BOOK_TOOL: a name, a description that says WHEN to use the tool, and an input_schema with one
# required string property, member_id (format M-123). This text is all Claude knows about the tool.
# ======================================================================================
CHECK_DUE_DATE_TOOL = {}  # replace these lines in TODO 1
TOOLS = [FIND_BOOK_TOOL, CHECK_DUE_DATE_TOOL]


# ======================================================================================
# TODO 2 of 4 - the dispatcher (stage 3).
# Claude only asks. Your program runs the function it named: find_book for "find_book", check_due_date for "check_due_date".
# An unknown name must return {"error": "unknown_tool", "name": name} instead of crashing.
# ======================================================================================
def run_tool(name, tool_input):
    raise NotImplementedError("TODO 2: run the function Claude asked for")  # replace these lines in TODO 2


# ======================================================================================
# TODO 3 of 4 - the loop (stage 3).
# After each reply from Claude: if stop_reason is not "tool_use", return the answer. Otherwise (a) append the assistant message
# (response.content), (b) run EVERY tool Claude asked for with run_tool_safely and build one tool_result block for each, with the
# SAME id as the tool_use, and (c) append ONE user message that holds ALL the tool_result blocks. Then the loop sends again.
# ======================================================================================
def answer(question, send=ask):
    """Ask Claude a question and keep going until it stops asking for tools.
    Returns {"answer": text, "turns": n, "tools_used": [names]}. send is ask() by default; the stages and check.py swap in a recorder."""
    messages = [{"role": "user", "content": question}]
    tools_used = []
    for turn in range(1, MAX_TURNS + 1):
        response = send(messages, system=SYSTEM, tools=TOOLS, model=MODEL_BALANCED, max_tokens=2048)
        return {"answer": text_of(response), "turns": turn, "tools_used": tools_used}  # replace these lines in TODO 3
    return {"answer": "", "turns": MAX_TURNS, "tools_used": tools_used, "gave_up": True}


# ======================================================================================
# TODO 4 of 4 - the safe runner (stage 4). The loop above calls it.
# Return (content_json_string, is_error). A crash inside a tool must NOT crash the loop, and a result with an "error" key
# (for example book_not_found) is flagged is_error=True so Claude knows the call failed.
# ======================================================================================
def run_tool_safely(name, tool_input):
    return json.dumps(run_tool(name, tool_input)), False  # replace these lines in TODO 4


# ======================================================================================
# PLUMBING - do not edit below this line
# ======================================================================================
core.configure(system=SYSTEM, tools=TOOLS, answer=answer, run_tool_safely=run_tool_safely, max_turns=MAX_TURNS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["1", "2", "3", "4"])
    args = parser.parse_args()
    core.run_stage(int(args.stage))


if __name__ == "__main__":
    main()
