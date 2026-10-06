"""LAB 2.0 - Intro to tool use: why tools, how to create one, how Claude uses it.

Run one step at a time (read the code of each step first):
    python lab.py --step 1      Claude with NO tools: it cannot see your data
    python lab.py --step 2      create ONE tool and watch the full round trip
    python lab.py --step 3      two tools: Claude picks the right one, or none
    python lab.py               all three, and saves evidence/evidence.json
Then:  python check.py          (needs an API key; each step is a handful of short calls, a few cents)

The one idea: Claude never runs your code. It ASKS for a tool call (stop_reason = "tool_use").
Your program runs the function and sends the result back. Then Claude writes the answer.

    question -> Claude: "please call get_order_status(ORD-1001)"    stop_reason = tool_use
             -> YOUR code runs the real function
             -> you send the result back                            -> Claude answers, stop_reason = end_turn

A tool has exactly three parts (PART A below): a function, a schema, a dispatcher.
"""
import argparse
import json
import pathlib

from claude_client import MODEL_BALANCED, ask, text_of, tool_calls_of

HERE = pathlib.Path(__file__).parent
SYSTEM = "You are the Northwind Outfitters support assistant. Use tools for order and policy data. Never invent details."
QUESTION = "Where is my order ORD-1001?"


# ================================================================ PART A: how to create a tool (three parts)
# Part 1: the functions. Plain Python. No Claude involved.
ORDERS = {
    "ORD-1001": {"item": "Trail Jacket", "status": "shipped", "carrier": "Northwind Express", "arrives": "2026-10-09"},
    "ORD-1002": {"item": "Camp Stove", "status": "delivered", "delivered_on": "2026-10-02"},
}
RETURN_POLICY = {"window_days": 30, "condition": "unused, in original packaging", "refund_to": "original payment method"}


def get_order_status(order_id):
    order = ORDERS.get(order_id)
    if order is None:
        return {"error": "order_not_found", "order_id": order_id}
    return {"order_id": order_id, **order}


def get_return_policy():
    return dict(RETURN_POLICY)


# Part 2: the schemas. This text is ALL Claude knows about your tools. Notice each description says WHEN to use the tool.
ORDER_STATUS_TOOL = {
    "name": "get_order_status",
    "description": ("Look up the current status of one customer order: item, shipping status, carrier and delivery date. "
                    "Use it when the customer asks where an order is or whether it arrived. It never changes anything."),
    "input_schema": {"type": "object", "properties": {"order_id": {"type": "string", "description": "Order id in the form ORD-1234."}},
                     "required": ["order_id"]},
}
RETURN_POLICY_TOOL = {
    "name": "get_return_policy",
    "description": ("Get the store's return policy: how many days a customer has to return an item and in what condition. "
                    "Use it when the customer asks about returning or refunding something. Takes no input."),
    "input_schema": {"type": "object", "properties": {}},
}
TOOLS = [ORDER_STATUS_TOOL, RETURN_POLICY_TOOL]


# Part 3: the dispatcher. Maps the tool name Claude chose to your function.
def run_tool(name, tool_input):
    if name == "get_order_status":
        return get_order_status(**tool_input)
    if name == "get_return_policy":
        return get_return_policy()
    return {"error": "unknown_tool", "name": name}


# ================================================================ PART B: the three steps
def step1_no_tools():
    print("\nSTEP 1: a question that needs LIVE company data, but Claude gets no tools.\n")
    print(f"  customer> {QUESTION}")
    response = ask([{"role": "user", "content": QUESTION}], model=MODEL_BALANCED, max_tokens=1024)
    answer = text_of(response)
    print(f"  claude  > {answer}")
    print("\n  Why: the model only knows its training data and this conversation. Your orders live in your system.")
    print("  Fix: give Claude a TOOL so it can ask your code for the answer. -> step 2")
    return {"question": QUESTION, "answer": answer, "tool_calls": len(tool_calls_of(response)), "stop_reason": response.stop_reason}


def step2_one_tool():
    print("\nSTEP 2A: the tool definition (this text is ALL Claude knows about the tool)\n")
    print(json.dumps(ORDER_STATUS_TOOL, indent=2))

    print("\nSTEP 2B: send the question WITH the tool attached\n")
    print(f"  customer> {QUESTION}")
    messages = [{"role": "user", "content": QUESTION}]
    first = ask(messages, system=SYSTEM, tools=[ORDER_STATUS_TOOL], model=MODEL_BALANCED, max_tokens=1024)
    print(f"\n  stop_reason = {first.stop_reason}   <- 'tool_use' means: Claude is asking YOU to run something")
    call = tool_calls_of(first)[0]
    print(f"  Claude's request (it did NOT run anything): {call.name}({json.dumps(call.input)})  id={call.id}")

    print("\nSTEP 2C: OUR code runs the real function\n")
    output = run_tool(call.name, call.input)
    print(f"  {call.name}({json.dumps(call.input)}) -> {json.dumps(output)}")

    print("\nSTEP 2D: send the result back, matched by tool_use_id. Claude writes the final answer\n")
    messages.append({"role": "assistant", "content": first.content})
    messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": call.id, "content": json.dumps(output)}]})
    final = ask(messages, system=SYSTEM, tools=[ORDER_STATUS_TOOL], model=MODEL_BALANCED, max_tokens=1024)
    answer = text_of(final)
    print(f"  stop_reason = {final.stop_reason}   <- 'end_turn' means: done")
    print(f"  claude  > {answer}")
    print("\n  The whole pattern: ask -> Claude requests a tool -> your code runs it -> send result -> Claude answers.")
    return {"first_stop_reason": first.stop_reason, "tool_name": call.name, "tool_input": dict(call.input),
            "tool_output": output, "final_stop_reason": final.stop_reason, "answer": answer}


def answer_with_tools(question):
    """The same loop as step 2, packaged: keep going until Claude stops asking for tools."""
    messages = [{"role": "user", "content": question}]
    tools_used = []
    for _ in range(6):  # a loop always needs an exit
        response = ask(messages, system=SYSTEM, tools=TOOLS, model=MODEL_BALANCED, max_tokens=1024)
        calls = tool_calls_of(response)
        if not calls:
            return text_of(response), tools_used
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for call in calls:
            output = run_tool(call.name, call.input)
            tools_used.append(call.name)
            print(f"    Claude asked for {call.name}({json.dumps(call.input)}) -> our code returned {json.dumps(output)}")
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": json.dumps(output)})
        messages.append({"role": "user", "content": results})
    return "(gave up after 6 turns)", tools_used


STEP3_QUESTIONS = [("needs the ORDER tool", "Where is my order ORD-1002?"),
                   ("needs the POLICY tool", "How long do I have to return something?"),
                   ("needs BOTH tools", "Has ORD-1001 shipped, and what is your return policy?"),
                   ("needs NO tool", "Hi there!")]


def step3_two_tools():
    print("\nSTEP 3: the same two tools every time. WE never choose; Claude reads the descriptions and decides.")
    runs = []
    for label, question in STEP3_QUESTIONS:
        print(f"\n--- {label} ---\n  customer> {question}")
        answer, tools_used = answer_with_tools(question)
        print(f"  claude  > {answer}")
        runs.append({"label": label, "question": question, "answer": answer, "tools_used": tools_used})
    print("\n  Takeaway: good tool NAMES and DESCRIPTIONS are how Claude decides.")
    return runs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", choices=["1", "2", "3", "all"], default="all")
    args = parser.parse_args()
    path = HERE / "evidence" / "evidence.json"
    evidence = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    print(f"model: {MODEL_BALANCED}")
    if args.step in ("1", "all"):
        evidence["step1"] = step1_no_tools()
    if args.step in ("2", "all"):
        evidence["step2"] = step2_one_tool()
    if args.step in ("3", "all"):
        evidence["step3"] = step3_two_tools()
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print("\nsaved evidence/evidence.json - now run: python check.py")


if __name__ == "__main__":
    main()
