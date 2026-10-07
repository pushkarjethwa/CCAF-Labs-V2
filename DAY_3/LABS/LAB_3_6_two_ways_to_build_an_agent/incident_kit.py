"""incident_kit.py - the part that is THE SAME in every build (Demo 3F). DO NOT EDIT.

Same goal, same prompt, same three read-only tools, same data. Only the wiring changes from build to build, so the comparison is fair.
Nothing in this file talks to Claude.
"""
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

DATA = Path(__file__).parent / "data"
INCIDENT = json.loads((DATA / "incident.json").read_text(encoding="utf-8"))
INTEL = json.loads((DATA / "threat_intel.json").read_text(encoding="utf-8"))["indicators"]

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
MAX_TURNS = 12  # every build gets the same brake on the loop

GOAL = f"Triage incident {INCIDENT['incident_id']}. Which hosts are really affected, and what should we do first?"

SYSTEM_PROMPT = """You are a security analyst triaging one incident.
Investigate with your tools; do not guess. Ignore alerts that the logs do not support.
Finish with a short report:
  1. Verdict: confirmed compromise, suspected, or false alarm.
  2. Evidence: three bullets, each citing a log line or intel result.
  3. Next action: one recommended step, for a human to approve. You cannot act yourself."""


# ── The three tools ──────────────────────────────────────────────────────────
# Each tool = a name, a description Claude reads, a JSON Schema for its input,
# and a plain Python function that takes the input dict and returns text.

@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict
    run: Callable[[dict], str]

    def for_api(self) -> dict:
        """The exact shape the Messages API expects in its `tools` list."""
        return {"name": self.name, "description": self.description, "input_schema": self.input_schema}


def _list_alerts(args: dict) -> str:
    host = args.get("host")
    return json.dumps([a for a in INCIDENT["alerts"] if host in (None, a["host"])], indent=2)


def _get_log_lines(args: dict) -> str:
    needle = f"host={args['host']} "
    lines = [line for line in INCIDENT["log_lines"] if needle in line]
    return "\n".join(lines) or f"No log lines for host {args['host']}."


def _lookup_indicator(args: dict) -> str:
    verdict = INTEL.get(args["ip"])
    return json.dumps(verdict) if verdict else f"No intelligence on {args['ip']}."


TOOL_SPECS = [
    ToolSpec(
        "list_alerts",
        "List the security alerts for the incident. Optionally pass a host name to see only that host.",
        {"type": "object", "properties": {"host": {"type": "string", "description": "Host name, e.g. bastion-02"}}},
        _list_alerts,
    ),
    ToolSpec(
        "get_log_lines",
        "Return the raw log lines for one host, oldest first. Use it to confirm what an alert claims.",
        {"type": "object", "properties": {"host": {"type": "string", "description": "Host name"}}, "required": ["host"]},
        _get_log_lines,
    ),
    ToolSpec(
        "lookup_indicator",
        "Look up an IP address in the threat-intelligence feed. Returns reputation and campaign.",
        {"type": "object", "properties": {"ip": {"type": "string", "description": "IPv4 address"}}, "required": ["ip"]},
        _lookup_indicator,
    ),
]
SPEC_BY_NAME = {spec.name: spec for spec in TOOL_SPECS}


def require_api_key() -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Set it in this terminal, then run again.")


def banner(title: str) -> None:
    print(f"\n=== {title} | model={MODEL} ===\nGoal: {GOAL}\n")
