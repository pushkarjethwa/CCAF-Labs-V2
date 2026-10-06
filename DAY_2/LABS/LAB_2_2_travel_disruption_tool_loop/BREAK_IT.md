# Break it - Lab 2.2

Work on a copy of your solved `lab.py` (`copy lab.py lab_good.py`) and restore it after each exercise. For each one: predict first, then run `python check.py` (Part A is quick and needs no key).

## 1. Random idempotency key
Change `idempotency_key` so it includes `uuid.uuid4().hex` (a "fresh key per attempt").
- Predict: how many rebookings end up in the ledger after the timed-out call is retried? Which check catches it?
- Diagnose in one sentence: what property of the key makes a retry safe?

## 2. Gate only on tool names, not references
Delete the `_ref` argument check in `blocked_by_gate`; keep the `DEPENDS_ON` check.
- Predict: a model sends `rebook_flight` and `book_hotel` in the same turn, the hotel with a made-up `rebook_ref`. Which check now fails?
- Why is checking the tool NAME not enough? Which ledger field (`unverified_entries`) would catch the damage?

## 3. Results in the wrong order
In `run_tools` return the results sorted by tool name instead of request order (keep the ids correct).
- Predict: does the API care about order inside the one user message? Does `check.py` notice?
- Then give one block the id of a different tool call. What does the API do on the next turn (run `python lab.py`)?

## 4. A guard that counts the wrong thing
Make the loop guard count only turns where `stop_reason == "end_turn"`. Run `python check.py`.
- Explain why this is "a guard" that never fires.

## 5. (Live) Watch the real defect
In your `lab_good.py` copy, put back the starter's one-message-per-result loop (TODO A). Run `python lab.py` with your key.
- Predict: Claude usually asks for the four reads in one turn. What error does the API return, and on which turn?

Write one line per exercise: *change -> symptom -> check that caught it -> the rule it violates*.
