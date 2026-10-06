# Solution guide: Lab 2.2 - Travel Disruption Assistant: the tool loop, parallel reads, safe writes

> **Spoiler warning.** Try the lab yourself first, using `README.md`, the TODO comments and `check.py`. Open this guide when you are stuck, or after you finish to compare. Your solution does not have to match line for line: if `check.py` passes and you can explain why, it is correct.

## 1. What this lab teaches

The tool loop done safely: one user message with all tool_results, independent reads concurrent but dependent writes sequential behind a gate, idempotent retries with a stable key, a structured 'unknown outcome' error, and a bounded loop.

## 2. Solutions, one TODO at a time

Each block shows the TODO text, then the code that solves it. Names follow the starter file.

### Block 1: LOYALTY_TIER_TOOL

What the TODO asks:

> TODO 0: write the definition of the `loyalty_tier` tool (it is the one tool missing below).
> - name "loyalty_tier"; a description that says it is READ-ONLY, what it returns (tier and perks: fee waiver,
> hotel rate cap, priority) and when to use it; input_schema requiring one string `traveler_id`; additionalProperties False.

Solution:

```python
LOYALTY_TIER_TOOL = {
    "name": "loyalty_tier",
    "description": "Read-only. Loyalty tier and perks (fee waiver, hotel rate cap, priority) for a traveler id. "
                   "Use it before booking a hotel to learn the traveler's hotel rate cap. Does not change anything.",
    "input_schema": _object({"traveler_id": TEXT}, ["traveler_id"]),
}
```

### Block 2: def call_one()

Solution:

```python
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
```

### Block 3: def call_one()

What the TODO asks:

> <<<SOLUTION

Solution:

```python
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
```

### Block 4: def run_tools()

What the TODO asks:

> TODO B: the starter runs EVERYTHING at once. Run READ_ONLY tools concurrently, but run writes one at a time in
> request order, and only when every tool in DEPENDS_ON[tool] already succeeded AND every *_ref argument is
> a reference a tool actually returned (state.refs). Otherwise do NOT call the service: return an is_error
> result with error PREREQUISITE_NOT_MET (or UNKNOWN_REFERENCE) and a hint.

Solution:

```python
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
```

### Block 5: def run_agent()

Solution:

```python
for turn in range(1, max_turns + 1):
```

### Block 6: def run_agent()

Solution:

```python
messages.append({"role": "user", "content": results})
```

### Block 7: def run_agent()

What the TODO asks:

> <<<SOLUTION

Solution:

```python
return {"turns": max_turns, "stopped": "max_turns", "final_text": "", "trace": trace, "tool_results": tool_results, "messages": messages}
```

## 3. What a passing `check.py` looks like

`check.py` runs these checks (descriptions as printed). Part A needs no API key; Part B reads the evidence from your live run.

- TODO 0: loyalty_tier tool is defined (read-only description, required traveler_id, additionalProperties false)
- TODO B: four reads return four results, in request order, ids matching
- TODO B: independent reads ran concurrently (total time close to the slowest read, not the sum)
- TODO B: dependent writes sent in the same batch as the rebooking are blocked (nothing booked on an unconfirmed reference)
- TODO B: a blocked call returns a structured error (PREREQUISITE_NOT_MET or UNKNOWN_REFERENCE) with a hint
- TODO B: writes never overlapped and never started before their prerequisite
- TODO C2: the timed-out rebooking returns a structured error (outcome_unknown, retryable, hint)
- TODO C1: retrying the identical rebooking is replayed, not repeated (exactly 1 rebooking in the ledger)
- TODO B: once the rebooking is confirmed, the hotel booking with the real reference goes through
- TODO D: a model that never stops is cut off at max_turns
- TODO A: both results of one assistant turn go back in ONE user message, ids matching
- the run finished with end_turn (not max_turns)
- exactly one rebooking, one hotel booking and one notification
- no write used an unconfirmed reference and none overlapped
- Claude used all four read tools (including your loyalty_tier)

## 4. Common mistakes

- Returning each tool_result in its own user message (HTTP 400 on the next turn).
- Running dependent writes concurrently: the hotel gets booked with a reference that does not exist yet.
- A random idempotency key per attempt: a retry then creates a second booking. Derive the key from the business operation (traveler + flight + option).
- A `while True` loop with no guard.

## 5. Answers to BREAK_IT

Same order as `BREAK_IT.md`. Results from live models vary: if yours differs, note it and explain why; that is the exercise.

1. Random key: the timed-out first rebooking was already committed, so the retry creates a second one: two rebookings in the ledger; the idempotency check catches it. A key is safe to retry when it is a pure function of the operation, never of the attempt.
2. Gate on names only: `book_hotel` with a made-up `rebook_ref` is allowed through; the unverified-references check fails and `unverified_entries` shows the damage. A name check cannot know the reference is real.
3. Result order inside one user message does not matter to the API, and `check.py` does not notice; a wrong id does matter: HTTP 400 on the next turn.
4. A guard that counts only `end_turn` turns never fires: the runaway turns have `stop_reason == 'tool_use'`.
5. Live with one message per result: the API returns HTTP 400 on the second turn (tool_use ids without tool_result blocks immediately after).

## 6. Files in this folder

- `lab_solution.py`: complete reference solution (replace the matching file in the lab folder to test it)
- `SOLUTION_GUIDE.md`: this file
