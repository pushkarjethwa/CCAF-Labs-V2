# Break It - Lab 1.4

Start from your working solution (all of `check.py` green). After each break, run `python lab.py` and read section [1] of the output.

## Break 1 - the invalidator comes back, somewhere else
Add a line to the **user** message builder (`user_message` in `lab.py`) that puts the timestamp at the start of the message, before the invoice JSON.
Predict: does the cache break? (The timestamp is after the breakpoint, so the system prefix is unchanged.) Then move the timestamp into the `INSTRUCTIONS` constant instead and predict again.
Observe: `cache_read_input_tokens` stays > 0 for the first change and drops to 0 for the second. Write the rule: *nothing before the cache breakpoint may vary between requests*; anything that must vary goes after it.

## Break 2 - the marker on the wrong block
In `make_params` in `lab.py`, send the user content as a block list `[{"type": "text", "text": user_message(ctx), "cache_control": {"type": "ephemeral"}}]` and strip `cache_control` from the system block (delete the `cache_control` key in `build_system`).
Predict: what does the second call report?
Observe: `cache_creation_input_tokens` > 0 on **both** calls and `cache_read_input_tokens == 0`: you are paying the 1.25x write premium on a block that is different every time. The marker belongs at the end of the shared portion, never on the varying block.

## Break 3 - below the floor
In `make_params` in `lab.py` pass only the first 60% of the policy text to `build_system` (about 3,600 tokens by chars/4). Re-run with `SERVICE_MODEL_ALIAS = "fast"`, then `"balanced"`.
Predict for each model: write? read?
Observe: on the fast alias both are 0 with no error (below the 4096 floor); on the balanced alias (floor 512) caching works. Check that your `budget_gate(...)["cache_eligible"]` says so beforehand. This is the silent failure the gate exists to expose.

## Break 4 - positional join returns
Temporarily restore `zip(contexts, results)` joining. Which `check.py` line catches it, and which evidence field would you have to inspect by eye if the checker did not exist?
