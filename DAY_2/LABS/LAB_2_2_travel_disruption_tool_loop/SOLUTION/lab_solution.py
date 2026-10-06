"""LAB 2.2 - Travel disruption assistant: the tool loop, parallel reads, and safe writes.

Run:   python lab.py                 (needs an API key; ~6 short turns, a few cents)
Check: python check.py               (Part A tests YOUR code with no API key; Part B reads evidence/evidence.json)

Scenario: flight XA482 was cancelled. For traveler T-1001 the assistant checks the flight, lists alternatives, checks
airport hotels and looks up the loyalty tier (four INDEPENDENT reads), then does rebook -> book hotel -> notify
(three DEPENDENT writes: each needs the reference returned by the one before).

The starter loop is wrong in four ways (your TODOs):
  A  it sends tool results back one message at a time           -> the API rejects the next turn (400)
  B  it runs every tool call at once, even dependent writes     -> a hotel is booked with a reference that does not exist yet
  C  a timed-out write is retried without an idempotency key    -> the traveler is rebooked twice
  D  `while True` with no iteration guard                       -> a model that never stops loops forever
and one tool definition you write yourself (TODO 0).

Files: travel_services.py is the mock airline/hotel/CRM (read it, do not edit). claude_client.py talks to Claude.
"""
import hashlib
import json
import pathlib
from concurrent.futures import ThreadPoolExecutor

from claude_client import text_of, tool_calls_of
from travel_services import PREREQ, READ_TOOLS, ServiceTimeout, TravelServices, analyse, load_scenario

HERE = pathlib.Path(__file__).parent
EVIDENCE_FILE = HERE / "evidence" / "evidence.json"
DEFAULT_MAX_TURNS = 10

READ_ONLY = frozenset(READ_TOOLS)  # no side effects: safe to run at the same time
DEPENDS_ON = dict(PREREQ)          # a write may only run after the listed tools have SUCCEEDED

SYSTEM = """You are the disruption desk assistant for an airline. A flight was cancelled; rebook the traveler,
book a hotel within their tier's hotel rate cap, and notify them. Check status, alternatives, hotels and loyalty
tier first (they are independent - request them together). Writes depend on each other: the hotel needs the
confirmed rebooking reference, the notification needs both references. Use only references that tool results
returned. If a tool result says the outcome is unknown, retry with IDENTICAL arguments. Finish with one short summary."""


# ----------------------------------------------------------------------------------------------
# STEP 1: tool definitions. This text is ALL Claude knows about each tool.
# ----------------------------------------------------------------------------------------------
def _object(properties, required):
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


TEXT = {"type": "string"}

# TODO 0: write the definition of the `loyalty_tier` tool (it is the one tool missing below).
#   - name "loyalty_tier"; a description that says it is READ-ONLY, what it returns (tier and perks: fee waiver,
#     hotel rate cap, priority) and when to use it; input_schema requiring one string `traveler_id`; additionalProperties False.
LOYALTY_TIER_TOOL = {
    "name": "loyalty_tier",
    "description": "Read-only. Loyalty tier and perks (fee waiver, hotel rate cap, priority) for a traveler id. "
                   "Use it before booking a hotel to learn the traveler's hotel rate cap. Does not change anything.",
    "input_schema": _object({"traveler_id": TEXT}, ["traveler_id"]),
}

TOOLS = [tool for tool in [
    {"name": "flight_status", "description": "Read-only. Current status and reason for one flight number. Use first to confirm the cancellation. Does not change anything.",
     "input_schema": _object({"flight_no": TEXT}, ["flight_no"])},
    {"name": "rebooking_options", "description": "Read-only. Alternative flights (with seats left and change fee) for a PNR whose flight was cancelled. Does not rebook.",
     "input_schema": _object({"pnr": TEXT}, ["pnr"])},
    {"name": "hotel_availability", "description": "Read-only. Hotels near an airport for a date with rate, rooms left and shuttle. Does not book.",
     "input_schema": _object({"airport": TEXT, "date": TEXT}, ["airport", "date"])},
    LOYALTY_TIER_TOOL,
    {"name": "rebook_flight", "description": "WRITE. Rebook the PNR onto a chosen option_id. Returns a confirmation ref (RB-...). Needed before any hotel or notification. May time out; the outcome is then unknown.",
     "input_schema": _object({"pnr": TEXT, "option_id": TEXT}, ["pnr", "option_id"])},
    {"name": "book_hotel", "description": "WRITE. Book one hotel for the stranded traveler. Requires the confirmed rebook_ref returned by rebook_flight; never guess it.",
     "input_schema": _object({"hotel_id": TEXT, "rebook_ref": TEXT, "nights": {"type": "integer"}, "guest": TEXT}, ["hotel_id", "rebook_ref", "nights", "guest"])},
    {"name": "notify_traveler", "description": "WRITE. Send the traveler the final itinerary. Requires both the rebook_ref and the hotel_ref returned by the earlier writes.",
     "input_schema": _object({"traveler_id": TEXT, "rebook_ref": TEXT, "hotel_ref": TEXT, "channel": TEXT}, ["traveler_id", "rebook_ref", "hotel_ref"])},
] if tool]


def request_text(scenario):
    traveler = scenario["travelers"]["T-1001"]
    return (f"Flight {scenario['flight']['flight_no']} ({scenario['flight']['route']}) is cancelled. Traveler T-1001 {traveler['name']}, "
            f"PNR {traveler['pnr']}. Rebook them, book a hotel at LHR for 2026-10-03 (1 night), and notify them.")


# ----------------------------------------------------------------------------------------------
# STEP 2: running the tools Claude asked for
# ----------------------------------------------------------------------------------------------
class RunState:
    """Facts about this conversation (provided). `succeeded`: tool names that returned OK. `refs`: references tools returned."""

    def __init__(self):
        self.succeeded = set()
        self.refs = set()


def tool_result(tool_call, content, is_error=False):
    """One tool_result block. tool_use_id MUST equal the id of the tool_use block it answers."""
    block = {"type": "tool_result", "tool_use_id": tool_call.id, "content": content if isinstance(content, str) else json.dumps(content)}
    if is_error:
        block["is_error"] = True
    return block


def idempotency_key(name, args):
    """Same tool + same arguments -> same key, so a retry of an unacknowledged write is replayed, not repeated."""
    canonical = json.dumps({"tool": name, "args": args}, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def call_one(services, tool_call, state):
    args = dict(tool_call.input)
    key = idempotency_key(tool_call.name, args) if tool_call.name not in READ_ONLY else None
    try:
        output = services.call(tool_call.name, args, idempotency_key=key)
        state.succeeded.add(tool_call.name)
        if isinstance(output, dict) and output.get("ref"):
            state.refs.add(output["ref"])
        return tool_result(tool_call, output)
    except ServiceTimeout as error:
        return tool_result(tool_call, {
            "error": "TIMEOUT_OUTCOME_UNKNOWN", "retryable": True, "outcome_unknown": True, "message": str(error),
            "hint": "The write may have been applied. Retry with IDENTICAL arguments; the service de-duplicates, so it cannot book twice."}, True)
    except Exception as error:
        return tool_result(tool_call, {"error": type(error).__name__, "retryable": False, "message": str(error)}, True)


def blocked_by_gate(tool_call, state):
    """Return an is_error result if this write must not run yet, else None."""
    missing = [p for p in DEPENDS_ON.get(tool_call.name, ()) if p not in state.succeeded]
    if missing:
        return tool_result(tool_call, {"error": "PREREQUISITE_NOT_MET", "retryable": True, "missing": missing,
                                       "hint": f"Call {', '.join(missing)} first and wait for a successful result before {tool_call.name}."}, True)
    unknown = {k: v for k, v in dict(tool_call.input).items() if k.endswith("_ref") and v not in state.refs}
    if unknown:
        return tool_result(tool_call, {"error": "UNKNOWN_REFERENCE", "retryable": True, "arguments": sorted(unknown),
                                       "hint": "Use only references returned by earlier tool results; never invent or guess one."}, True)
    return None


def run_tools(services, tool_calls, state):
    """Return ONE tool_result block per tool_use, in the order the tool_use blocks were requested."""
    # TODO B: the starter runs EVERYTHING at once. Run READ_ONLY tools concurrently, but run writes one at a time in
    #         request order, and only when every tool in DEPENDS_ON[tool] already succeeded AND every *_ref argument is
    #         a reference a tool actually returned (state.refs). Otherwise do NOT call the service: return an is_error
    #         result with error PREREQUISITE_NOT_MET (or UNKNOWN_REFERENCE) and a hint.
    results = {}
    reads = [c for c in tool_calls if c.name in READ_ONLY]
    if reads:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for call, result in zip(reads, pool.map(lambda c: call_one(services, c, state), reads)):
                results[call.id] = result
    for call in tool_calls:
        if call.name not in READ_ONLY:
            results[call.id] = blocked_by_gate(call, state) or call_one(services, call, state)
    return [results[call.id] for call in tool_calls]


# ----------------------------------------------------------------------------------------------
# STEP 3: the loop. `create` is claude_client.ask (or any function with the same signature).
# ----------------------------------------------------------------------------------------------
def run_agent(create, services, user_text, max_turns=None):
    max_turns = max_turns or DEFAULT_MAX_TURNS
    messages = [{"role": "user", "content": user_text}]
    trace, tool_results = [], []
    state = RunState()
    for turn in range(1, max_turns + 1):
        response = create(messages, system=SYSTEM, tools=TOOLS, max_tokens=1024)
        tool_calls = tool_calls_of(response)
        trace.append({"turn": turn, "stop_reason": response.stop_reason, "tools": [c.name for c in tool_calls]})
        if response.stop_reason != "tool_use" or not tool_calls:
            return {"turns": turn, "stopped": "end_turn", "final_text": text_of(response), "trace": trace,
                    "tool_results": tool_results, "messages": messages}
        messages.append({"role": "assistant", "content": response.content})
        results = run_tools(services, tool_calls, state)
        names_by_id = {c.id: c.name for c in tool_calls}
        for result in results:
            tool_results.append({"turn": turn, "tool": names_by_id.get(result["tool_use_id"], "?"), "tool_use_id": result["tool_use_id"],
                                 "is_error": bool(result.get("is_error")), "content": result["content"]})
        messages.append({"role": "user", "content": results})
    return {"turns": max_turns, "stopped": "max_turns", "final_text": "", "trace": trace, "tool_results": tool_results, "messages": messages}


def main():
    from claude_client import ask

    scenario = load_scenario(HERE / "data" / "scenario.json")
    services = TravelServices(scenario)
    result = run_agent(ask, services, request_text(scenario))
    analysis = analyse(services.events, services.ledger())

    print("turn trace:")
    for step in result["trace"]:
        print(f"  turn {step['turn']}: stop_reason={step['stop_reason']:<9} tools={step['tools']}")
    print("\nfinal answer:", result["final_text"])
    print("\nledger:", {k: len(v) for k, v in services.ledger().items()})
    print("analysis:", analysis)

    EVIDENCE_FILE.parent.mkdir(exist_ok=True)
    EVIDENCE_FILE.write_text(json.dumps({"result": {k: v for k, v in result.items() if k != "messages"}, "analysis": analysis,
                                         "ledger": services.ledger()}, indent=2, default=str), encoding="utf-8")
    print("\nsaved evidence/evidence.json - now run: python check.py")


if __name__ == "__main__":
    main()
