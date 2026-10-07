"""incident_kit.py - what is THE SAME in every build (Demo 3F and Lab 3.6). DO NOT EDIT.

Same goal, same prompt, same three read-only tools, same data. Only the wiring
changes from build to build, so the comparison is fair. Nothing here calls Claude.
"""
import json
import os
import sys
from pathlib import Path

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


# ---- The three tools ---------------------------------------------------------
# Each tool has two halves. TOOLS is what Claude reads: a name, a description
# and a JSON Schema for the input. The functions below do the work and return text.

TOOLS = [
    {"name": "list_alerts",
     "description": "List the security alerts for the incident. Optionally pass a host name to see only that host.",
     "input_schema": {"type": "object", "properties": {"host": {"type": "string", "description": "Host name, e.g. bastion-02"}}}},
    {"name": "get_log_lines",
     "description": "Return the raw log lines for one host, oldest first. Use it to confirm what an alert claims.",
     "input_schema": {"type": "object", "properties": {"host": {"type": "string", "description": "Host name"}}, "required": ["host"]}},
    {"name": "lookup_indicator",
     "description": "Look up an IP address in the threat-intelligence feed. Returns reputation and campaign.",
     "input_schema": {"type": "object", "properties": {"ip": {"type": "string", "description": "IPv4 address"}}, "required": ["ip"]}},
]


def list_alerts(args):
    host = args.get("host")
    return json.dumps([a for a in INCIDENT["alerts"] if host in (None, a["host"])], indent=2)


def get_log_lines(args):
    needle = f"host={args['host']} "
    return "\n".join(line for line in INCIDENT["log_lines"] if needle in line)


def lookup_indicator(args):
    return json.dumps(INTEL.get(args["ip"], {"reputation": "unknown"}))  # internal addresses are not in the feed


# Tool name -> function. Each function takes the input dict and returns text.
RUN_TOOL = {"list_alerts": list_alerts, "get_log_lines": get_log_lines, "lookup_indicator": lookup_indicator}


def require_api_key():
    """Stop with a one-line message when the key is missing."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Set it in this terminal, then run again.")


def banner(title):
    """Print the build title, model and goal."""
    print(f"\n=== {title} | model={MODEL} ===\nGoal: {GOAL}\n")
