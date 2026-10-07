"""desk_core.py - the machinery of the research desk (Demo 3B, stage 4). DO NOT EDIT.

You do not need to read this file to finish the lab. It runs the specialists, checks their hand-offs against your contracts
and scores the answers. Everything you write is in lab.py.
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor

import desk_tools as desk
from claude_client import ask, text_of, tool_calls_of

REPORT_FORMAT = ("Finish with exactly this format:\nANSWER: ...\nCONFIDENCE: high, medium or low\nSOURCES: document ids, comma separated\n"
                 "ESCALATION: none, OR what conflicts and which human must decide. If two reliable sources disagree, do not pick one: "
                 "give both values and escalate.")
CONTRACT_TEXT = {  # shown to each specialist so it knows the shape to reply with
    "searcher": '{"findings": [{"doc_id": "DOC-002", "fact": "the exact fact", "value": "the figure"}], "rumours": ["unconfirmed claims, if any"], '
                '"needs_calculation": true or false, "calc_request": "what to compute, or empty"}',
    "analyst": '{"results": [{"label": "what was computed", "value": "the result", "inputs": "the numbers used"}]}',
    "fact_checker": '{"checks": [{"doc_id": "DOC-002", "claim": "the claim", "verdict": "SUPPORTED" | "NOT_SUPPORTED" | "CONFLICT", "detail": "one sentence"}]}',
}
ROLES = {
    "searcher": {"prompt": "You find sources. Search, then fetch the best documents. Prefer high reliability and the newest date; skip superseded or mirrored "
                           "documents; convert dates carefully. Report the exact facts that answer the question, and label any low-reliability claim as a rumour.",
                 "tools": ["search_corpus", "fetch_document"], "turns": 10},
    "analyst": {"prompt": "You calculate. Use your tools for every number; never do arithmetic in your head.", "tools": ["cagr", "divide"], "turns": 5},
    "fact_checker": {"prompt": "You verify claims. Fetch the cited document and compare. If another current, high-reliability document gives a different leader or a different value for what the "
                               "question asks about, the verdict is CONFLICT, even when the two documents use different bases such as revenue and units. "
                               "State both values and both bases in the detail. Never choose between them: a human decides which basis counts.", "tools": ["fetch_document", "search_corpus"], "turns": 8},
}
WRITER_SYSTEM = ("You write the final report from the facts you are given, using exact figures and nothing else. Name the winner of any comparison in a "
                 "sentence such as '<product> is cheaper'. Quote no figure from a superseded or low-reliability source, except a rumour clearly "
                 "labelled as an unconfirmed rumour. " + REPORT_FORMAT)


def json_in(text):
    start, end = text.find("{"), text.rfind("}")
    try:
        return json.loads(text[start:end + 1]) if start != -1 and end > start else None
    except json.JSONDecodeError:
        return None


def check_value(value, kind, where):
    if kind == "str":
        return [] if isinstance(value, str) else [f"{where} must be a string"]
    if kind == "bool":
        return [] if isinstance(value, bool) else [f"{where} must be true or false"]
    if kind == "doc_id":
        return [] if isinstance(value, str) and value in desk.CORPUS else [f"{where}: {value!r} is not a document in the corpus"]
    if isinstance(kind, list):
        return [] if value in kind else [f"{where} must be one of {kind}"]
    if isinstance(kind, tuple):
        return [e for i, item in enumerate(value) for e in check_value(item, kind[1], f"{where}[{i}]")] if isinstance(value, list) else [f"{where} must be a list"]
    return validate(value, kind, where + ".")


def validate(data, spec, path=""):
    """Check a hand-off against its contract. Returns a list of problems (empty = valid)."""
    if not isinstance(data, dict):
        return [f"{path or 'the reply'} must be a JSON object"]
    errors = [f"missing field '{path}{field}'" for field in spec if field not in data]
    errors += [f"unexpected field '{path}{field}'" for field in data if field not in spec]
    for field, kind in spec.items():
        if field in data:
            errors += check_value(data[field], kind, f"{path}{field}")
    return errors


def call_with_contract(role, brief, caller, contracts):
    """Ask a specialist and check that its hand-off matches YOUR contract."""
    data = json_in(caller(role, brief))
    problems = ["the reply is not valid JSON"] if data is None else validate(data, contracts[role])
    if problems:
        raise SystemExit(f"The {role} hand-off does not match its contract: {'; '.join(problems)}")
    return data


def real_specialist(role, brief):
    """Run one specialist as a real Claude agent with its own small tool set (the manual tool loop from Demo 3F, build 1)."""
    spec, state = ROLES[role], desk.Desk(enriched=True)
    system = spec["prompt"] + f"\nReply with JSON only, shaped like: {CONTRACT_TEXT[role]}"
    tools, messages = desk.tool_defs(spec["tools"], True), [{"role": "user", "content": brief}]
    for _ in range(spec["turns"]):
        response = ask(messages, system=system, tools=tools, max_tokens=4096)
        messages.append({"role": "assistant", "content": response.content})
        calls = tool_calls_of(response)
        if not calls:
            return text_of(response)
        messages.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": block.id, "content": state.call(block.name, block.input)} for block in calls]})
    return "(no final answer: turn limit reached)"


def escalated(report):
    low = report.lower()
    return "escalation:" in low and not re.search(r"escalation:\s*\**\s*none", low)


def orchestrate(q, hooks, caller=None):
    """The desk (Demo 3B stage 4). `hooks` holds what YOU wrote in lab.py. Returns (report, notes)."""
    caller = caller or real_specialist
    contracts = hooks["contracts"]

    def call(role, brief):
        return call_with_contract(role, brief, caller, contracts)

    found = call("searcher", hooks["searcher_brief"](q))
    results = []
    if found["needs_calculation"]:
        results = call("analyst", hooks["analyst_brief"](found))["results"]
    with ThreadPoolExecutor(max_workers=4) as pool:   # the fact-checks are independent, so they run in parallel
        replies = list(pool.map(lambda finding: call("fact_checker", hooks["fact_check_brief"](finding)), found["findings"]))
    checks = [c for data in replies for c in data["checks"]]
    brief = (f"Question: {q['text']}\nVerified findings: {json.dumps(found['findings'])}\nFact-check verdicts: {json.dumps(checks)}\n"
             f"Calculations: {json.dumps(results)}\nUnconfirmed rumours (label them as such if you mention them): {json.dumps(found['rumours'])}\n")
    if hooks["has_conflict"](checks):
        brief += "The fact-checker found a CONFLICT between reliable sources: report both values and escalate to a human.\n"
    return hooks["call_writer"](brief), {"checks": len(checks)}


def score(q, report):
    """Plain string checks against the ground truth in data/questions.json."""
    low = report.lower()
    checks = {f"fact:{kf['id']}": all(s.lower() in low for s in kf["must_contain"]) for kf in q["key_facts"]}
    checks["citations"] = all(doc_id in report for doc_id in q["required_citations"])
    for rule in q["qualified_only"]:
        checks[f"qualified:{rule['term']}"] = rule["term"].lower() not in low or any(w in low for w in rule["qualifiers"])
    checks["escalation"] = escalated(report) == q["expect_escalation"]
    return checks
