# Day 2 findings (working notes for the final QA report)

Date: 2026-10-08. Guides written in `STUDENT_V2/STUDY_GUIDES/DAY_2/`: TOOL_USE_LOOP (pilot), TOOL_DESIGN, TOOL_ERRORS_AND_RETRIES, PARALLEL_TOOL_CALLS, MCP_BASICS, MCP_SECURITY_AND_GOVERNANCE. Writers were worker agents running the same model as the lead (no separate Opus or Haiku calls were made).

## Validation actually run
- Python code blocks: syntax-checked with `python3 -I`; the starter samples were also run against stub objects. No call to the live API or the real `mcp` SDK was possible (no key, package install blocked).
- Relative links, anchors, Mermaid bracket balance and required sections checked by script. No broken links.
- Official pages fetched as page text: how-tool-use-works, build-a-tool-using-agent, define-tools, handle-tool-calls, troubleshooting-tool-use, tool-runner, handling-stop-reasons, tool-search-tool, strict-tool-use, tool-reference, overview, parallel-tool-use, MCP intro, architecture, server concepts, transports, authorization, security best practices, Claude Code MCP page, Claude API MCP connector page.

## Old Day 2 guide: audit
- Keep: tool_result rules, retryability classes, tool-versus-MCP table, primitives table, stdout rule on stdio.
- Corrected: sequential-versus-parallel table said "one tool_result per turn" (it is one user message holding every result); error field named `code` (current exercises use `error_code` or `error`); "session handling" for HTTP MCP is outdated for the 2026-07-28 spec; unverified limits (20 strict tools, 24 optional params) dropped.
- Missing and now covered: ambiguous-outcome timeouts, fail-closed errors, preflight, Tool Runner exception handling, scoping failure ("right tool missing"), tool search, built-in versus custom tools, N x M framing for MCP, how MCP tools reach Claude through your own loop, SSE status, scope minimisation, connector allow-list.

## Existing `STUDENT_V2/STUDY_GUIDE/` MCP files (left untouched)
- Keep: roles table, 401/403 table, layered model, threat map, transport table, stdout rule, `${VAR}` advice.
- Wrong or to clarify: `MCP_BEST_PRACTICES.md` names `server_app/kitchen_server.py` as the Demo 2D HTTP example (Demo 2D uses `crm_server.py`; `kitchen_server.py` belongs to the separate server and client demo); says HTTP authentication is "required, OAuth based" (the spec makes authorization optional, and the lab uses static bearer keys); cites old `docs.anthropic.com` URLs; "do not use sessions for authentication" row is outdated against the 2026-07-28 spec.

## Demo and lab discrepancies (not fixed, flagged for the trainer)
- Old guide, `TRAINER/MASTER_TEACHING_REFERENCE.md` and some cheatsheets map the tool loop to Lab 2.2; in V2, Demo 2B pairs with Lab 2.3, Demo 2C with Lab 2.2, Demo 2A with Lab 2.1, and Lab 2.5 (optional) builds the loop.
- Error field names differ: Demo 2B and Lab 2.3 use `error_code`/`category`; Lab 2.2 uses `error` with `outcome_unknown`; Lab 2.5 uses only `error`. Lab 2.3 gives `PAY_PERIOD_CLOSED` the category `tool`, which Demo 2B reserves for "our own tool is broken".
- Idempotency key: built by the harness in Demo 2B and Lab 2.2; an input field filled in by Claude in Lab 2.3.
- Demo 2A uses 12 tools and 20 prompts; Lab 2.1 uses 11 tools and 16 prompts. Tool search appears only as a request shape in Demo 2A stage 5.
- Demo 2C README says "five reads"; its certification question uses four. Lab 2.2 `max_turns` default is 10 in `lab.py`, but stage 5 uses 8.
- Lab 2.4 real files differ from the older names (`lab.py`, `procurement_core.py`, `procurement_db.py`, `check.py`); roles are analyst and approver with `PROC_KEY_*` keys, while Demo 2D uses reader and agent with `CRM_API_KEY_*` and supports comma-separated keys for rotation.
- Lab 2.4 and Demo 2D return a 403 as a tool result; the MCP spec describes an HTTP 403 for OAuth servers. The guide tells learners to pick one and use it everywhere.
- The two `DEMO_2_0_*` folders inside `STUDENT_V2/DAY_2/LABS` are identical to the trainer copies so learners can run them without a key. Their READMEs say the real MCP SDK was never run.

## Open items
- Starter MCP server (MCP_BASICS) not run against the real `mcp` 2.3.0 package.
- Beta header names for the Claude API MCP connector should be re-checked before the course runs.
- Behaviour when Claude names a tool outside the offered set is not stated (could not be verified).
