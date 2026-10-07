"""Lab 3.5 - Build your first agent with the Claude Agent SDK (continues Demo 3E: same incident INC-7741, same three tools).

A security-analyst agent triages one incident. It can only READ: list alerts, read log lines, look up an IP in a threat feed.
You give it a goal; it chooses the tools, the order and when to stop. In the SDK, an agent is one configuration object:
model + system prompt + tools + limits. You write the four pieces here:

  TODO 1  TOOL_SPECS     describe each tool to Claude: the description is how Claude decides when to call it
  TODO 2  SYSTEM_PROMPT  who the agent is and what a good answer looks like (not the steps)
  TODO 3  build_options  the agent: model, prompt, tools, limits
  TODO 4  run_live       run the agent loop with query()

HOW TO RUN
  python check.py    pass/fail in plain words. Part A needs no key and no model.
  python lab.py      runs the agent for real (needs ANTHROPIC_API_KEY and the Claude Code CLI); then python check.py again
The tool functions and the printing code are in soc_tools.py and below the line "do not edit". You do not need to read them.
"""
import asyncio
import hashlib
import json
import os
import pathlib
import sys

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, CLINotFoundError, ResultMessage, TextBlock, ToolUseBlock,
                              create_sdk_mcp_server, query, tool)
from dotenv import load_dotenv

import soc_tools

load_dotenv()  # reads ANTHROPIC_API_KEY from a .env file in this folder
MODEL = os.getenv("CLAUDE_AGENT_MODEL", "claude-sonnet-5-5")
GOAL = f"Triage incident {soc_tools.INCIDENT['incident_id']}. Which hosts are really affected, and what should we do first?"


# ======================================================================================
# TODO 1 of 4 - TOOL_SPECS: describe each tool to Claude
# Row format: {"name": ..., "description": ..., "schema": ...}. The schema says what input the tool takes.
# Write each description like a hand-over note: what the tool returns and when to use it.
# ======================================================================================
TOOL_SPECS = [
    {"name": "list_alerts",
     "description": "List the security alerts for the incident. Optionally pass a host name to see only that host.",
     "schema": {"type": "object", "properties": {"host": {"type": "string"}}}},
    {"name": "get_log_lines",
     "description": "Return the raw log lines for one host, oldest first. Use it to confirm what an alert claims.",
     "schema": {"host": str}},
    {"name": "lookup_indicator",
     "description": "Look up an IP address in the threat-intelligence feed. Returns reputation and campaign.",
     "schema": {"ip": str}},
]

# ======================================================================================
# TODO 2 of 4 - SYSTEM_PROMPT: who the agent is and what a good answer looks like
# The prompt does not list the steps. Choosing the steps is the agent's job.
# ======================================================================================
SYSTEM_PROMPT = """You are a security analyst triaging one incident.
Investigate with your tools; do not guess. Ignore alerts that the logs do not support.
Finish with a short report:
  1. Verdict: confirmed compromise, suspected, or false alarm.
  2. Evidence: three bullets, each citing a log line or intel result.
  3. Next action: one recommended step, for a human to approve. You cannot act yourself."""


# ======================================================================================
# TODO 3 of 4 - build_options: the agent is one configuration object
# as_sdk_tool(spec) turns a TOOL_SPECS row into an SDK tool. Claude Code's built-in file and shell tools must be switched OFF
# (tools=[]), and exactly the three tools allowed. Tool names look like mcp__<server>__<tool>, and the server here is "soc".
# ======================================================================================
def build_options():
    server = create_sdk_mcp_server("soc", tools=[as_sdk_tool(spec) for spec in TOOL_SPECS])
    return ClaudeAgentOptions(
        model=MODEL,
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"soc": server},
        tools=[],                                   # switch OFF Claude Code's built-in file and shell tools
        allowed_tools=["mcp__soc__list_alerts",     # pre-approve exactly these three, nothing else
                       "mcp__soc__get_log_lines",
                       "mcp__soc__lookup_indicator"],
        max_turns=12,                               # hard stop on the loop
        max_budget_usd=1.00,                        # hard stop on spend
        setting_sources=[],                         # ignore any local CLAUDE.md or settings files
    )


# ======================================================================================
# TODO 4 of 4 - run_live: run the agent loop
# query(prompt=..., options=...) runs the whole loop for you (ask Claude, run the tools it requests, send results back, repeat)
# and streams messages. events_from(message) turns one message into simple events; show(event) prints one.
# ======================================================================================
async def run_live():
    all_events = []
    async for message in query(prompt=GOAL, options=build_options()):
        for event in events_from(message):
            show(event)
            all_events.append(event)
    return all_events


# ======================================================================================
# PLUMBING - do not edit below this line
# ======================================================================================
HERE = pathlib.Path(__file__).parent
RESULTS_FILE = HERE / "results" / "run.json"


def as_sdk_tool(spec):
    """Wrap one TOOL_SPECS row and its soc_tools function as an SDK tool."""
    @tool(spec["name"], spec["description"], spec["schema"])
    async def handler(args):
        return {"content": [{"type": "text", "text": soc_tools.RUN[spec["name"]](args)}]}
    return handler


def events_from(message):
    """Turn one SDK message into zero or more simple events."""
    if isinstance(message, AssistantMessage):
        events = []
        for block in message.content:
            if isinstance(block, ToolUseBlock):
                events.append({"kind": "tool", "name": block.name.removeprefix("mcp__soc__"), "input": block.input})
            elif isinstance(block, TextBlock) and block.text.strip():
                events.append({"kind": "text", "text": block.text})
        return events
    if isinstance(message, ResultMessage):
        return [{"kind": "result", "turns": message.num_turns, "cost_usd": message.total_cost_usd,
                 "is_error": message.is_error, "stop_reason": message.stop_reason}]
    return []


def show(event):
    if event["kind"] == "tool":
        print(f"  -> tool: {event['name']}({json.dumps(event['input'])})")
    elif event["kind"] == "text":
        print(f"\n{event['text']}\n")
    else:
        cost = f"${event['cost_usd']:.4f}" if event["cost_usd"] is not None else "n/a"
        print(f"[done] {'ERROR' if event['is_error'] else 'ok'} | turns={event['turns']} | cost={cost} | stop_reason={event['stop_reason']}")


def source_fingerprint():
    return hashlib.sha256((HERE / "lab.py").read_bytes()).hexdigest()[:16]


def main():
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is missing. Create a .env file next to lab.py containing ANTHROPIC_API_KEY=sk-ant-...")
    print(f"Model: {MODEL}\nGoal:  {GOAL}\n")
    try:
        events = asyncio.run(run_live())
    except CLINotFoundError:
        sys.exit("The Claude Code CLI was not found. The Agent SDK drives it as a helper process. Install Claude Code (see the guide).")
    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text(json.dumps({"fingerprint": source_fingerprint(), "events": events}, indent=1), encoding="utf-8")
    print("\nSaved to results/run.json. Now run: python check.py")


if __name__ == "__main__":
    main()
