"""desk_core.py - the machinery of the research desk (Demo 3B, stage 4). DO NOT EDIT.

You do not need to read this file to finish the lab. It runs the specialists, validates their hand-offs, applies your failure
policy and scores the answers. Everything you write is in lab.py.
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


class SubagentError(Exception):
    """A specialist failed to run (an environment problem)."""


class HandoffError(Exception):
    """A specialist's reply broke its contract even after the allowed re-asks (a reasoning problem)."""

    def __init__(self, role, errors):
        super().__init__(f"{role}: {'; '.join(errors)}")
        self.role, self.errors = role, errors


class LeakError(Exception):
    """A brief contained the confidential client note. Blocked before any model saw it."""


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


def guard_brief(brief):
    if any(marker.lower() in brief.lower() for marker in desk.LEAK_MARKERS):
        raise LeakError("brief contains the confidential client note")


def call_with_contract(role, brief, caller, contracts, policy):
    """Ask a specialist, validate its hand-off, re-ask with the exact problems, and classify what is left. Uses YOUR policy."""
    if policy["confidential_leak"]["action"] == "block_and_escalate":
        guard_brief(brief)
    max_rework = policy["malformed_handoff"]["max_attempts"] if policy["malformed_handoff"]["action"] == "re_ask_with_errors" else 0
    max_retry = policy["specialist_crashed"]["max_attempts"]
    feedback, errors = "", []
    for rework in range(max_rework + 1):
        for retry in range(max_retry + 1):
            try:
                text = caller(role, brief + feedback)
                break
            except SubagentError:
                if retry == max_retry:
                    raise
        data = json_in(text)
        errors = ["the reply is not valid JSON"] if data is None else validate(data, contracts[role])
        if not errors:
            return data, rework
        feedback = "\n\nYour previous reply was rejected: " + "; ".join(errors) + ". Reply again with JSON that satisfies the contract."
    raise HandoffError(role, errors)


def real_specialist(role, brief):
    """Run one specialist as a real Claude agent with its own small tool set (the manual tool loop from Demo 3F, build 1)."""
    spec, state = ROLES[role], desk.Desk(enriched=True)
    system = spec["prompt"] + f"\nReply with JSON only, shaped like: {CONTRACT_TEXT[role]}"
    tools, messages = desk.tool_defs(spec["tools"], True), [{"role": "user", "content": brief}]
    try:
        for _ in range(spec["turns"]):
            response = ask(messages, system=system, tools=tools, max_tokens=4096)
            messages.append({"role": "assistant", "content": response.content})
            calls = tool_calls_of(response)
            if not calls:
                return text_of(response)
            messages.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": block.id, "content": state.call(block.name, block.input)} for block in calls]})
    except Exception as exc:  # network or API trouble is an environment problem, not a reasoning one
        raise SubagentError(str(exc)) from exc
    return "(no final answer: turn limit reached)"


def escalated(report):
    low = report.lower()
    return "escalation:" in low and not re.search(r"escalation:\s*\**\s*none", low)


def orchestrate(q, hooks, caller=None):
    """The hardened desk (Demo 3B stage 4). `hooks` holds what YOU wrote in lab.py. Returns (report, briefs, notes)."""
    caller = caller or real_specialist
    contracts, policy = hooks["contracts"], hooks["policy"]
    notes, briefs = {"reworks": 0, "leaks_blocked": 0, "checks": 0, "status": "complete"}, []

    def call(role, brief):
        briefs.append(brief)
        return call_with_contract(role, brief, caller, contracts, policy)

    try:
        found, reworks = call("searcher", hooks["searcher_brief"](q))
        notes["reworks"] += reworks
        if not found["findings"]:
            if policy["no_findings"]["action"] == "partial_report":
                raise HandoffError("searcher", ["no findings returned"])
        results = []
        if found["needs_calculation"]:
            data, reworks = call("analyst", hooks["analyst_brief"](found))
            results, notes["reworks"] = data["results"], notes["reworks"] + reworks
        with ThreadPoolExecutor(max_workers=4) as pool:
            checked = list(pool.map(lambda finding: call("fact_checker", hooks["fact_check_brief"](finding)), found["findings"]))
        checks = [c for data, _ in checked for c in data["checks"]]
        notes["reworks"] += sum(r for _, r in checked)
        notes["checks"] = len(checks)
        conflict = hooks["has_conflict"](checks)
        brief = (f"Question: {q['text']}\nVerified findings: {json.dumps(found['findings'])}\nFact-check verdicts: {json.dumps(checks)}\n"
                 f"Calculations: {json.dumps(results)}\nUnconfirmed rumours (label them as such if you mention them): {json.dumps(found['rumours'])}\n"
                 + ("The fact-checker found a CONFLICT between reliable sources: report both values and escalate to a human.\n" if conflict else ""))
        briefs.append(brief)
        guard_brief(brief)
        report = hooks["call_writer"](brief)
        if hooks["must_re_ask_writer"](report, conflict):  # escalation is a rule, not a hope: one corrective re-ask
            notes["reworks"] += 1
            report = hooks["call_writer"](brief + "\nYour report did not escalate. The ESCALATION line must describe the conflict and name who decides.")
        return report, briefs, notes
    except LeakError:
        reason, notes["leaks_blocked"] = "a brief contained confidential client context and was blocked", 1
    except HandoffError as exc:
        reason = f"{exc.role} could not deliver a valid hand-off ({'; '.join(exc.errors)[:160]})"
    except SubagentError:
        reason = "a specialist kept failing to run"
    notes["status"] = "partial"
    return f"ANSWER: not available.\nCONFIDENCE: low\nSOURCES: none\nESCALATION: {reason}; a human must take over.", briefs, notes


def score(q, report):
    """Plain string checks against the ground truth in data/questions.json."""
    low = report.lower()
    checks = {f"fact:{kf['id']}": all(s.lower() in low for s in kf["must_contain"]) for kf in q["key_facts"]}
    checks["citations"] = all(doc_id in report for doc_id in q["required_citations"])
    for rule in q["qualified_only"]:
        checks[f"qualified:{rule['term']}"] = rule["term"].lower() not in low or any(w in low for w in rule["qualifiers"])
    checks["escalation"] = escalated(report) == q["expect_escalation"]
    return checks


def leaks_in(briefs, report):
    return sum(any(m.lower() in t.lower() for m in desk.LEAK_MARKERS) for t in [*briefs, report])
