"""LAB 2.5 - Build a tool and the tool loop from scratch (raw Anthropic SDK, no framework).

Run:   python lab.py        (needs an API key; 4 short conversations, a few cents)
Check: python check.py      (Part A needs NO key: it tests your loop with hand-made model replies)

The one idea: Claude never runs your code. It ASKS for a tool call (stop_reason = "tool_use").
Your program runs the function and sends the result back. Then Claude writes the answer.

    question -> Claude: "call find_book(Dune)"   -> YOUR code runs it -> you send tool_result -> Claude answers

A tool has three parts, in this file in this order:
  1. a Python function that does the real work   (STEP 1, given)
  2. a schema that tells Claude what it is       (STEP 2, TODO 1)  <- the text is ALL Claude knows about your tool
  3. a dispatcher that runs the one Claude chose (STEP 3, TODO 2 + TODO 4)
Then the loop that ties them together (STEP 4, TODO 3).
"""
import json
import pathlib

from claude_client import MODEL_BALANCED, ask, text_of, tool_calls_of

HERE = pathlib.Path(__file__).parent
MAX_TURNS = 6  # a loop must always have an exit

SYSTEM = "You are a helpful library assistant. Use the tools for facts about books and loans. Answer in one or two sentences."

# ---------------------------------------------------------------- STEP 1 (given): the real functions. No Claude in here.
BOOKS = {"dune": {"title": "Dune", "shelf": "SF-12", "copies_available": 2},
         "emma": {"title": "Emma", "shelf": "CL-03", "copies_available": 0}}
LOANS = {"M-100": {"title": "Dune", "due": "2026-10-20"}, "M-200": {"title": "Emma", "due": "2026-10-08"}}


def find_book(title):
    book = BOOKS.get(title.strip().lower())
    return book if book else {"error": "book_not_found", "title": title}


def check_due_date(member_id):
    loan = LOANS.get(member_id)
    return {"member_id": member_id, **loan} if loan else {"error": "no_loan_found", "member_id": member_id}


# ---------------------------------------------------------------- STEP 2: the schemas
FIND_BOOK_TOOL = {  # a finished example: read how the description says WHEN to use the tool
    "name": "find_book",
    "description": "Look up one book by title: its shelf code and how many copies are available. Use when someone asks where a book is or whether it is in. Read-only.",
    "input_schema": {"type": "object", "properties": {"title": {"type": "string", "description": "Book title, e.g. Dune"}}, "required": ["title"]},
}

# TODO 1: write the schema for check_due_date(member_id). Needs: name, a description that says when to use it,
#   and an input_schema with a required string property member_id (format M-123). Mirror FIND_BOOK_TOOL.
CHECK_DUE_DATE_TOOL = {
    "name": "check_due_date",
    "description": "Look up the book a library member currently has on loan and its due date. Use when someone asks when something is due or what a member has borrowed. Read-only.",
    "input_schema": {"type": "object", "properties": {"member_id": {"type": "string", "description": "Member id in the form M-123"}}, "required": ["member_id"]},
}
TOOLS = [FIND_BOOK_TOOL, CHECK_DUE_DATE_TOOL]


# ---------------------------------------------------------------- STEP 3: the dispatcher
def run_tool(name, tool_input):
    """Run the function Claude asked for and return its result as a dict."""
    # TODO 2: call find_book for "find_book" (given below) and check_due_date for "check_due_date".
    #   An unknown tool name must return {"error": "unknown_tool", "name": name}, not crash.
    if name == "find_book":
        return find_book(**tool_input)
    if name == "check_due_date":
        return check_due_date(**tool_input)
    return {"error": "unknown_tool", "name": name}


def run_tool_safely(name, tool_input):
    """Return (content_json_string, is_error). A crash inside a tool must NOT crash the loop."""
    # TODO 4: wrap run_tool in try/except Exception. On a crash return (json string of {"error": "tool_crashed", "detail": str(exc)}, True).
    #   Also return is_error True when the result dict has an "error" key (for example book_not_found), so Claude knows the call failed.
    try:
        result = run_tool(name, tool_input)
    except Exception as exc:  # noqa: BLE001 - a tool crash is reported to the model, not raised
        return json.dumps({"error": "tool_crashed", "detail": str(exc)}), True
    return json.dumps(result), "error" in result


# ---------------------------------------------------------------- STEP 4: the loop
def answer(question, send=ask):
    """Ask Claude a question and keep the conversation going until it stops asking for tools.
    Returns {"answer": text, "turns": n, "tools_used": [names]}. send is ask() by default; check.py swaps in a fake."""
    messages = [{"role": "user", "content": question}]
    tools_used = []
    for turn in range(1, MAX_TURNS + 1):
        response = send(messages, system=SYSTEM, tools=TOOLS, model=MODEL_BALANCED, max_tokens=2048)
        # TODO 3: if response.stop_reason is not "tool_use", return {"answer": text_of(response), "turns": turn, "tools_used": tools_used}.
        #   Otherwise: (a) append {"role": "assistant", "content": response.content} to messages,
        #   (b) for EVERY block in tool_calls_of(response) run run_tool_safely(block.name, block.input) and build
        #       {"type": "tool_result", "tool_use_id": block.id, "content": <string>} (add "is_error": True on errors),
        #   (c) append ONE user message whose content is the list of ALL those tool_result blocks. Then loop.
        if response.stop_reason != "tool_use":
            return {"answer": text_of(response), "turns": turn, "tools_used": tools_used}
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in tool_calls_of(response):
            content, is_error = run_tool_safely(block.name, dict(block.input))
            tools_used.append(block.name)
            result = {"type": "tool_result", "tool_use_id": block.id, "content": content}
            if is_error:
                result["is_error"] = True
            results.append(result)
        messages.append({"role": "user", "content": results})
    return {"answer": "", "turns": MAX_TURNS, "tools_used": tools_used, "gave_up": True}


QUESTIONS = [
    ("needs find_book", "Where is the book Dune and is a copy in?"),
    ("needs check_due_date", "When is member M-200's book due back?"),
    ("needs both", "Member M-100 asked when their loan is due and where I can find another copy of that title."),
    ("needs none", "What is the capital of France?"),
]


def main():
    print(f"model: {MODEL_BALANCED}")
    evidence = {"model": MODEL_BALANCED, "runs": []}
    for label, question in QUESTIONS:
        result = answer(question)
        print(f"\n[{label}] {question}\n  tools used: {result['tools_used']}  turns: {result['turns']}\n  answer: {result['answer']}")
        evidence["runs"].append({"label": label, "question": question, **result})
    path = HERE / "evidence" / "evidence.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print("\nsaved evidence/evidence.json - now run: python check.py")


if __name__ == "__main__":
    main()
