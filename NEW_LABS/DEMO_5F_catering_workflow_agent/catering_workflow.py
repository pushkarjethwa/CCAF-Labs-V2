"""Demo 5F - A workflow agent with state, memory and guardrails (Brew & Bean catering) on the Claude Agent SDK.

    python catering_workflow.py --request R-1                 run the whole workflow for one request, then look at the files
    python catering_workflow.py --request R-1 --stop-after 2  stop after two steps, the checkpoint is saved
    python catering_workflow.py --resume R-1                  go on from the checkpoint, finished steps are not repeated
    python catering_workflow.py --approve R-2                 a manager approves an order that waits, and it finishes
    python catering_workflow.py --list                        show the run history and the orders that wait

Setup: pip install claude-agent-sdk==0.2.163 (it bundles the Claude Code CLI) and set ANTHROPIC_API_KEY.
Every step runs on CLAUDE_MODEL_FAST (claude-haiku-5-5). Add --model balanced for CLAUDE_MODEL_BALANCED (claude-sonnet-5-5).
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import catering_tools
import steps
import workflow_state

try:
    import claude_agent_sdk as sdk
except ImportError:
    sdk = None

# -- Settings ---------------------------------------------------------------------------------------------

HERE = Path(__file__).parent
STORE = workflow_state.RunStore(HERE / "results")
REQUESTS = {r["id"]: r["text"] for r in json.loads((HERE / "data" / "requests.json").read_text(encoding="utf-8"))["requests"]}
MODELS = {"fast": os.getenv("CLAUDE_MODEL_FAST", "claude-haiku-5-5"), "balanced": os.getenv("CLAUDE_MODEL_BALANCED", "claude-sonnet-5-5")}
ITEMS_SCHEMA = {"type": "object", "required": ["items"], "properties": {"items": {"type": "array", "items": {
    "type": "object", "required": ["name", "qty"], "properties": {"name": {"type": "string"}, "qty": {"type": "integer"}}}}}}
TOTAL_STEPS = len(steps.ORDER)


# -- Small helpers ----------------------------------------------------------------------------------------

def need_live():
    """One guard: the SDK and an API key."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    if sdk is None or not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("The workflow needs `pip install claude-agent-sdk==0.2.163` (it bundles the Claude Code CLI) and ANTHROPIC_API_KEY.")


def show_banner(text):
    """Print a section title."""
    print(f"\n=== {text} ===")


def short(value, width=70):
    """A value as one short line of text."""
    text = json.dumps(value) if not isinstance(value, str) else value
    return text if len(text) <= width else text[:width - 3] + "..."


# -- Tools and the gate (the step table lives in steps.json) ------------------------------------------------

def build_server(order_id, step):
    """An in-process tool server with ONLY the tools this step may use. The order id is closed over, so the model cannot pick another order."""
    def text(content):
        return {"content": [{"type": "text", "text": content}]}

    @sdk.tool("check_stock", "Check the stock for a list of items.", ITEMS_SCHEMA)
    async def check_stock(args):
        return text(json.dumps(catering_tools.check_stock(args["items"])))

    @sdk.tool("price_items", "Price a list of items from the price table.", ITEMS_SCHEMA)
    async def price_items(args):
        return text(json.dumps(catering_tools.price_items(args["items"])))

    @sdk.tool("send_confirmation", "Send the confirmation message for this order. It sends once, even if called twice.", {"message": str})
    async def send_confirmation(args):
        sent = catering_tools.send_confirmation(STORE.outbox, order_id, args["message"])
        return text("Confirmation sent." if sent else "Already sent earlier. Nothing was sent again.")

    everything = {"check_stock": check_stock, "price_items": price_items, "send_confirmation": send_confirmation}
    return sdk.create_sdk_mcp_server(steps.SERVER, tools=[everything[name] for name in steps.tools_for(step)])


def make_gate(order_id, step, state):
    """The PreToolUse hook of ONE step. It checks every tool call against steps.json and writes the audit log."""
    async def gate(input_data, tool_use_id, context):
        tool = input_data["tool_name"].removeprefix(steps.PREFIX)
        allowed, reason = steps.gate_decision(step, tool, state)
        STORE.log_decision(order_id, step, tool, input_data["tool_input"], allowed, reason)
        if not allowed:
            print(f"    [guardrail] {reason}")
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow" if allowed else "deny",
                                       "permissionDecisionReason": reason}}
    return gate


def build_options(order_id, step, state, model):
    """The options of one small SDK call: this step's prompt, tools, gate and limits. Nothing is shared with the other steps."""
    rules = steps.STEPS[step]
    return sdk.ClaudeAgentOptions(
        model=model, system_prompt=steps.system_prompt(step), setting_sources=[],  # no CLAUDE.md, no settings files
        tools=[], mcp_servers={steps.SERVER: build_server(order_id, step)},
        allowed_tools=[steps.PREFIX + name for name in steps.tools_for(step)],
        permission_mode="dontAsk",  # a tool that is not allowed is denied, never asked about. Verify on your SDK version.
        hooks={"PreToolUse": [sdk.HookMatcher(hooks=[make_gate(order_id, step, state)])]},
        max_turns=rules["max_turns"], max_budget_usd=rules["max_budget_usd"])


async def ask_claude(order_id, step, prompt, state, model):
    """ONE short SDK call, with a fresh context. Return the ResultMessage."""
    async for message in sdk.query(prompt=prompt, options=build_options(order_id, step, state, model)):
        if isinstance(message, sdk.ResultMessage):
            return message


# -- One step ---------------------------------------------------------------------------------------------

def show_given(number, step, prompt, record, model):
    """Print what the step is given, and what one growing chat would carry instead. Return the size of the prompt in tokens."""
    rules = steps.STEPS[step]
    given_tokens = steps.rough_tokens(prompt)
    chat_tokens = sum(t["given"] + t["output"] for t in record["trace"]) + given_tokens
    how = f"model {model}, tools: {', '.join(rules['tools']) or 'none'}, max_turns {rules['max_turns']}, budget ${rules['max_budget_usd']}" \
        if rules["kind"] == "model" else "plain code, no model call"
    print(f"\nStep {number} of {TOTAL_STEPS}: {step}   ({how})")
    print(f"    given     : {', '.join(rules['reads'])}   (~{given_tokens} tokens)")
    print(f"    one chat  : would already carry ~{chat_tokens} tokens")
    return given_tokens


async def run_step(record, step, number, model):
    """Run one step: build its small prompt, call Claude (or plain code), check the output. Return a problem text or None."""
    state, order_id = record["state"], record["order_id"]
    prompt = steps.build_prompt(steps.inputs_for(step, state))
    given_tokens = show_given(number, step, prompt, record, model)
    if steps.STEPS[step]["kind"] == "code":
        output, reply, cost = steps.approval_decision(state["total"]), "", 0.0
    else:
        result = await ask_claude(order_id, step, prompt, state, model)
        reply, cost = result.result or "", result.total_cost_usd or 0.0
        output = steps.parse_reply(reply)
        if output is None:
            return f"{step} did not return a JSON object"
        output = steps.keep_declared(step, output)
    problem = steps.validate(step, output, state)
    if problem:
        return problem
    print(f"    result    : {short(output)}")
    print(f"    check     : output shape and meaning OK (cost ${cost:.4f})")
    state.update(output)
    workflow_state.mark_done(record, step, given_tokens, steps.rough_tokens(reply or json.dumps(output)), cost)
    return None


def load_preferences(state):
    """Memory: the customer's standing preferences, loaded by code into the state once the customer is known."""
    state["preferences"] = catering_tools.preferences_for(state["customer"])
    print(f"    memory    : standing preferences for {state['customer']}: {state['preferences'] or 'none'}")


# -- The workflow -----------------------------------------------------------------------------------------

def hold_for_manager(record):
    """The approval gate said no. Take the approve step off the finished list, queue the order, and pause the workflow."""
    record["done"].remove("approve")
    record["trace"].pop()
    STORE.add_to_queue(record["order_id"], record["state"]["total"], steps.APPROVAL_LIMIT)
    record["status"] = "waiting for manager"
    print(f"    approval  : ${record['state']['total']:.2f} is over the ${steps.APPROVAL_LIMIT} limit. Queued in results/approval_queue.json.")


async def advance(record, model, stop_after):
    """Walk the fixed steps. Finished steps are skipped, and the checkpoint is saved after every step. Return (steps run, steps skipped)."""
    ran, skipped = [], []
    for number, step in enumerate(steps.ORDER, 1):
        if step in record["done"]:
            print(f"\nStep {number} of {TOTAL_STEPS}: {step}   skipped, it is already in the checkpoint. No model call, no cost.")
            skipped.append(step)
            continue
        if stop_after and len(record["done"]) >= stop_after:
            record["status"] = f"stopped after {len(record['done'])} steps"
            break
        problem = await run_step(record, step, number, model)
        if problem:
            record["status"] = f"stopped by the {step} check"
            print(f"    check     : STOP. {problem}. The checkpoint keeps the finished steps.")
            break
        if step == "approve" and not record["state"]["approved"]:
            hold_for_manager(record)
            break
        if step == "parse":
            load_preferences(record["state"])
        ran.append(step)
        print(f"    saved     : results/runs/{STORE.save(record).name}")
    else:
        record["status"] = "done"
    return ran, skipped


def finish(record, ran, skipped):
    """Save the checkpoint, add a history line and print the summary."""
    STORE.save(record)
    STORE.add_history(record, ran, skipped)
    show_banner(f"{record['order_id']}: {record['status']}")
    print(f"    steps run {ran or 'none'}, skipped {skipped or 'none'}, cost so far ${workflow_state.total_cost(record):.4f}")
    if record["status"] == "waiting for manager":
        print(f"    next: python catering_workflow.py --approve {record['order_id']}")
    elif record["status"].startswith("stopped"):
        print(f"    next: python catering_workflow.py --resume {record['order_id']}")


async def start(request_id, model, stop_after):
    """--request: a new run for one sample request."""
    if request_id not in REQUESTS:
        sys.exit(f"Unknown request {request_id}. Use one of: {', '.join(REQUESTS)}")
    if STORE.load(request_id):
        sys.exit(f"{request_id} already has a run. Use --resume {request_id}, or --list to see where it is.")
    record = workflow_state.new_record(request_id, REQUESTS[request_id])
    show_banner(f"Order {request_id}")
    print(steps.quote_untrusted(REQUESTS[request_id]))
    finish(record, *await advance(record, model, stop_after))


async def resume(order_id, model, stop_after):
    """--resume: go on from the checkpoint."""
    record = STORE.load(order_id)
    if record is None:
        sys.exit(f"No checkpoint for {order_id}. Start it with --request {order_id}.")
    if record["status"] in ("done", "waiting for manager"):
        sys.exit(f"{order_id} is '{record['status']}'. Nothing to resume.")
    show_banner(f"Resuming {order_id} from its checkpoint (steps done: {', '.join(record['done']) or 'none'})")
    finish(record, *await advance(record, model, stop_after))


async def approve(order_id, model):
    """--approve: a manager signs off an order that waits, and the workflow goes on to the confirm step."""
    record = STORE.load(order_id)
    if record is None or record["status"] != "waiting for manager":
        sys.exit(f"{order_id} is not waiting for a manager. Use --list.")
    record["state"].update({"approved": True, "approved_by": "manager"})
    record["done"].append("approve")
    STORE.remove_from_queue(order_id)
    show_banner(f"Manager approved {order_id}")
    finish(record, *await advance(record, model, None))


def show_list():
    """--list: the run history and the orders that wait."""
    show_banner("Run history (results/run_history.jsonl)")
    for row in STORE.history():
        print(f"    {row['time']}  {row['order_id']:<5} {row['status']:<28} run {row['steps_run']} skipped {row['steps_skipped']} ${row['cost_usd']:.4f}")
    if not STORE.history():
        print("    No runs yet.")
    show_banner("Waiting for a manager (results/approval_queue.json)")
    for entry in STORE.queue():
        print(f"    {entry['order_id']}  ${entry['total']:.2f}  {entry['reason']}")
    if not STORE.queue():
        print("    Nobody waits.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--request", help="start a sample request: R-1, R-2 or R-3")
    actions.add_argument("--resume", metavar="ORDER", help="go on from the checkpoint of an order")
    actions.add_argument("--approve", metavar="ORDER", help="a manager approves an order that waits")
    actions.add_argument("--list", action="store_true", help="show the run history and the approval queue")
    parser.add_argument("--stop-after", type=int, metavar="N", help="stop once N steps are finished")
    parser.add_argument("--model", choices=list(MODELS), default="fast")
    args = parser.parse_args()
    if args.list:
        return show_list()
    need_live()
    model = MODELS[args.model]
    if args.request:
        asyncio.run(start(args.request, model, args.stop_after))
    elif args.resume:
        asyncio.run(resume(args.resume, model, args.stop_after))
    else:
        asyncio.run(approve(args.approve, model))


if __name__ == "__main__":
    main()
