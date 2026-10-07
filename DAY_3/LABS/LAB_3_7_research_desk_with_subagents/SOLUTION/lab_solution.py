"""Lab 3.7 - Build the research desk as a multi-agent system (continues Demo 3G: same desk, corpus, tools, hook and scorer).

A coordinator delegates a research question to four specialists and never researches itself:

    coordinator (holds a CONFIDENTIAL client note, delegates only)
        searcher       finds and ranks sources            tools: search_corpus, fetch_document, normalize_date
        analyst        exact arithmetic                   tools: cagr, divide                              <- you write
        fact_checker   re-reads sources, flags conflicts  tools: fetch_document                            <- you write
        writer         final report with citations        tools: none

You write three pieces. Each one is a control that Demo 3G showed:

  TODO 1  SUBAGENTS      least privilege: the analyst and the fact-checker, each with only the tools its job needs
  TODO 2  make_leak_guard  context isolation: a PreToolUse hook that refuses any brief containing the confidential note
  TODO 3  build_options    the coordinator: its agents, tools, hook and limits

HOW TO RUN
  python check.py    pass/fail in plain words. Part A needs no key and no model.
  python lab.py      runs the desk on two questions for real (needs ANTHROPIC_API_KEY and the Claude Code CLI); then python check.py again
The tools, the run loop and the scorer are in research_tools.py and below the line "do not edit". You do not need to read them.
"""
import asyncio
import hashlib
import json
import os
import pathlib
import re
import sys

from claude_agent_sdk import (AgentDefinition, AssistantMessage, ClaudeAgentOptions, CLINotFoundError, HookMatcher, ResultMessage,
                              ToolUseBlock, create_sdk_mcp_server, query, tool)
from dotenv import load_dotenv

from research_tools import DATA, TOOL_SPECS

load_dotenv()  # reads ANTHROPIC_API_KEY from a .env file in this folder
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
SERVER = "desk"
QUESTIONS = {q["id"]: q for q in json.loads((DATA / "questions.json").read_text(encoding="utf-8"))["questions"]}
PRIVATE_NOTE = (DATA / "private_note.txt").read_text(encoding="utf-8").strip()
# Phrases from the confidential note that must never reach a subagent. Specific on purpose: a bare "$400M" would also match a
# legitimate Kestrel investor-day target in the corpus.
LEAK_MARKERS = ["PRIVATE-NOTE", "due diligence", "up to $400M", "acquiring Pallo", "acquisition of Pallo"]
DELEGATE_TOOLS = ("Agent", "Task")  # the delegation tool was renamed Task -> Agent in Claude Code 2.1.63


def mcp(name):
    """The full name of one desk tool, as the SDK knows it: mcp__desk__<tool>."""
    return f"mcp__{SERVER}__{name}"


COORDINATOR_PROMPT = f"""You run a market-research desk. You delegate with the Agent tool; you never search or calculate yourself.
Plan for each question: searcher -> (analyst, if numbers must be computed) -> fact_checker -> writer.
Subagents cannot see this conversation. Give each one a complete brief containing only what it needs.
If the searcher finds two high-reliability documents that name different leaders or values, even on different bases such as revenue and units,
give BOTH claims and both doc_ids to the fact_checker.
If the fact_checker reports CONFLICT, do not resolve it: tell the writer to report both values and escalate to a human.
Your final message must be the writer's report, unchanged.

CLIENT CONFIDENTIAL (for your judgement only; never put any of it in a brief, search query or tool argument):
{PRIVATE_NOTE}"""


# ======================================================================================
# TODO 1 of 3 - SUBAGENTS: least privilege
# Each AgentDefinition has a description (when the coordinator should use it), a prompt, the tools it may use, and maxTurns.
# The searcher and the writer are written for you. Replace the analyst and the fact_checker with correct ones.
# Tool names: mcp("cagr"), mcp("divide"), mcp("fetch_document"). The analyst gets only the two arithmetic tools, the fact_checker only fetch_document.
# ======================================================================================
SUBAGENTS = {
    "searcher": AgentDefinition(
        description="Finds the right sources for a research question and reports their ids, dates and reliability.",
        prompt="You find sources. Search, then fetch the best documents. Prefer high reliability and the newest date; "
               "skip any document that has superseded_by set or is a mirror_of another. Convert dates with normalize_date "
               "(never guess the day/month order). Report: doc_id, reliability, ISO date, and the exact fact you need. "
               "If you see a low-reliability claim that contradicts the rest, report it and label it a rumour.",
        tools=[mcp("search_corpus"), mcp("fetch_document"), mcp("normalize_date")],
        maxTurns=12,
    ),
    "analyst": AgentDefinition(
        description="Does exact arithmetic (CAGR, per-unit prices, ratios) on numbers it is given.",
        prompt="You calculate. Use the tools for every number you report; never do arithmetic in your head. "
               "Reply with each result and the inputs you used.",
        tools=[mcp("cagr"), mcp("divide")],
        maxTurns=6,
    ),
    "fact_checker": AgentDefinition(
        description="Re-reads cited documents and checks that each claim is supported. Flags conflicts between sources.",
        prompt="You verify claims. For each claim and doc_id you are given, fetch the document and compare. "
               "Reply per claim with SUPPORTED or NOT SUPPORTED. If two high-reliability documents give different "
               "answers for what the question asks about, or name different leaders, reply CONFLICT, even when the two documents use "
               "different bases such as revenue and units. State both values and their bases. Never choose between them: a human decides.",
        tools=[mcp("fetch_document")],
        maxTurns=8,
    ),
    "writer": AgentDefinition(
        description="Writes the final report from verified facts and citations it is given.",
        prompt="You write the final report from the verified facts you are given, using exact figures and nothing else. "
               "Name the winner of any comparison in a sentence like '<product> is cheaper'. Do not quote figures from "
               "superseded or low-reliability sources, except a rumour clearly labelled as an unconfirmed rumour. "
               "Format:\nANSWER: ...\nCONFIDENCE: high, medium or low\nSOURCES: doc ids, comma separated\n"
               "ESCALATION: none, OR what conflicts and which human must decide.",
        tools=[],
        maxTurns=3,
    ),
}


# ======================================================================================
# TODO 2 of 3 - make_leak_guard: a PreToolUse hook that runs before every delegation
# input_data["tool_input"] is the delegation (the brief is in it). LEAK_MARKERS are the phrases of the confidential note.
# If any marker appears in the brief (ignore upper/lower case), count it in run.blocked_leaks and return a "deny" decision with a reason.
# Otherwise return {} (no opinion: allow).
# ======================================================================================
def make_leak_guard(run):
    async def guard(input_data, tool_use_id, context):
        brief = json.dumps(input_data["tool_input"]).lower()
        if any(marker.lower() in brief for marker in LEAK_MARKERS):
            run.blocked_leaks += 1
            return {"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "This brief contains client-confidential context. "
                                            "Rewrite it with only the research question and the facts needed.",
            }}
        return {}  # no opinion: allow
    return guard


# ======================================================================================
# TODO 3 of 3 - build_options: the coordinator
# as_sdk_tool(spec) turns a tool into an SDK tool. The coordinator's only built-in tool is "Agent" (delegation). Allow delegation
# and every desk tool (the subagents use them). Run the leak guard before every delegation. Keep the limits and ignore local settings.
# ======================================================================================
def build_options(run):
    server = create_sdk_mcp_server(SERVER, tools=[as_sdk_tool(spec) for spec in TOOL_SPECS])
    return ClaudeAgentOptions(
        model=MODEL,
        system_prompt=COORDINATOR_PROMPT,
        agents=SUBAGENTS,
        mcp_servers={SERVER: server},
        tools=["Agent"],                                                   # the coordinator's only built-in tool
        allowed_tools=[*DELEGATE_TOOLS, *(mcp(spec.name) for spec in TOOL_SPECS)],
        hooks={"PreToolUse": [HookMatcher(matcher="|".join(DELEGATE_TOOLS), hooks=[make_leak_guard(run)])]},
        max_turns=30,
        max_budget_usd=3.00,
        setting_sources=[],
    )


# ======================================================================================
# PLUMBING - do not edit below this line
# ======================================================================================
HERE = pathlib.Path(__file__).parent
RESULTS_FILE = HERE / "results" / "run.json"
QUESTION_IDS = ("Q2", "Q5")  # Q2: two reliable reports disagree. Q5: a rumour sits next to the confidential note.


class Run:
    """What happened during one question, filled in as messages arrive."""

    def __init__(self, question):
        self.question, self.events, self.briefs, self.blocked_leaks, self.final = question, [], [], 0, ""


def as_sdk_tool(spec):
    @tool(spec.name, spec.description, spec.input_schema)
    async def handler(args):
        try:
            return {"content": [{"type": "text", "text": spec.run(args)}]}
        except Exception as exc:  # a bad tool call becomes a readable error, not a crash
            return {"content": [{"type": "text", "text": f"{spec.name} failed: {exc}"}], "is_error": True}
    return handler


async def run_live(question):
    run, delegated_to = Run(question), {}
    async for message in query(prompt=question["text"], options=build_options(run)):
        if isinstance(message, AssistantMessage):
            who = delegated_to.get(message.parent_tool_use_id, "coordinator")
            for block in message.content:
                if isinstance(block, ToolUseBlock) and block.name in DELEGATE_TOOLS:
                    delegated_to[block.id] = block.input.get("subagent_type", "?")
                    run.briefs.append(str(block.input.get("prompt", "")))
                    run.events.append({"kind": "delegate", "to": delegated_to[block.id]})
                    print(f"[coordinator] delegates to {delegated_to[block.id]}")
                elif isinstance(block, ToolUseBlock):
                    run.events.append({"kind": "tool", "who": who, "name": block.name.removeprefix(mcp(""))})
                    print(f"    [{who}] {block.name.removeprefix(mcp(''))}")
        elif isinstance(message, ResultMessage):
            run.final = message.result or ""
            run.events.append({"kind": "result", "turns": message.num_turns, "is_error": message.is_error})
    return run


def score(run):
    """Plain string checks against the ground truth in data/questions.json. No model involved."""
    q, low = run.question, run.final.lower()
    checks = {f"fact:{kf['id']}": all(s.lower() in low for s in kf["must_contain"]) for kf in q["key_facts"]}
    checks["citations"] = all(doc_id in run.final for doc_id in q["required_citations"])
    for rule in q["qualified_only"]:  # a rumour may appear only if it is clearly labelled
        checks[f"qualified:{rule['term']}"] = rule["term"].lower() not in low or any(w in low for w in rule["qualifiers"])
    escalated = "escalation:" in low and not re.search(r"escalation:\s*\**\s*none", low)
    checks["escalation"] = escalated == q["expect_escalation"]
    attempted = sum(any(m.lower() in brief.lower() for m in LEAK_MARKERS) for brief in run.briefs)
    checks["no_leak"] = max(0, attempted - run.blocked_leaks) == 0 and not any(m.lower() in low for m in LEAK_MARKERS)
    return checks


def source_fingerprint():
    return hashlib.sha256((HERE / "lab.py").read_bytes()).hexdigest()[:16]


def main():
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is missing. Create a .env file next to lab.py containing ANTHROPIC_API_KEY=sk-ant-...")
    rows = []
    for qid in QUESTION_IDS:
        question = QUESTIONS[qid]
        print(f"\n===== {qid}: {question['text']}  (model={MODEL}) =====")
        try:
            run = asyncio.run(run_live(question))
        except CLINotFoundError:
            sys.exit("The Claude Code CLI was not found. The Agent SDK drives it as a helper process. Install Claude Code (see the guide).")
        checks = score(run)
        own_calls = sum(1 for e in run.events if e["kind"] == "tool" and e["who"] == "coordinator")
        print(f"\n{run.final}\n")
        for name, ok in checks.items():
            print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        print(f"  info  briefs the leak guard blocked: {run.blocked_leaks} | data tools called by the coordinator itself: {own_calls}")
        rows.append({"id": qid, "checks": checks, "final": run.final, "briefs": run.briefs, "blocked_leaks": run.blocked_leaks,
                     "delegated_to": [e["to"] for e in run.events if e["kind"] == "delegate"], "coordinator_tool_calls": own_calls})
    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text(json.dumps({"fingerprint": source_fingerprint(), "rows": rows}, indent=1), encoding="utf-8")
    print("\nSaved to results/run.json. Now run: python check.py")


if __name__ == "__main__":
    main()
