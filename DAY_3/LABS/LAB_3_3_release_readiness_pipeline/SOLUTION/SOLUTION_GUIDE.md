# Lab 3.3 solution guide

The full working file is `lab_solution.py` (same folder). Copy it over `lab.py` to compare.

## The six decisions

| TODO | Decision | Why |
|---|---|---|
| 1 `validate_extract` | Reject empty, unknown or duplicate or missing tickets, categories not in `CATEGORIES`, risks not in `RISKS`. Messages say exactly what is wrong. | The message goes back to the model as the correction, so a vague message gives a vague fix. |
| 2 `validate_enrich` | Reject empty CI, missing `critical` or `high`, no on-call primary. | An empty record is not an error to the tool, so only a validator can catch it. |
| 3 `classify` | Validation of extract = reasoning; validation of enrich = tool; ToolError with status >= 500, 408, 429 = environment; other ToolError = tool; else unknown. | Decide from type and status, never message text. |
| 4 `backoff_delay` | `0.5 * 2 ** (tries - 1)` | Gives a struggling service room to recover. |
| 5 `cache_is_usable` | `bool(cache) and cache.get("for_version") == release["version"]` | Evidence about 3.0.4 says nothing about 3.1.0. |
| 6 `decide_recovery` | reasoning: re-prompt while `tries <= 2`, then escalate. tool: change args once if there is a hint, else escalate. environment: back off while `tries < 4`, then cache if usable, else pause and alert. Else escalate. | Each class has a different cause, so a different cure. Every branch ends. |

## Why the table comes out as it does

- F1: the 404 carries `expected_id`, so one retry with the fixed id works (attempts 2).
- F2: an empty CI record fails `validate_enrich` (tool class, no hint) and escalates at once. No verdict from no evidence.
- F3/F4: a rule-breaking model answer gets up to two corrections. F3 fixes it on the second ask; F4 never does and escalates at attempt 3.
- F5: two timeouts, waits 0.5 then 1.0, third try works.
- F6/F7: after 4 tries the scanner is still down. F6's cache is for this version: use it, mark degraded, and `assess` turns a `go` into `needs-review`. F7's cache is for 3.0.4: pause and raise one alert; no verdict.

## Common mistakes

- Checking `tries < MAX_CORRECTIONS` instead of `<=` (one correction too few).
- Returning `"fallback_cache"` without checking `cache_ok`.
- Classifying by `"503" in str(exc)`.
- A validator that only checks types, so `schema_change` slips through.
