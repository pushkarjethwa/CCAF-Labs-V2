"""soc_tools.py - the three read-only tools of the incident-triage agent (Demo 3E). DO NOT EDIT.

Plain Python functions: each takes the tool's input as a dict and returns text. No model calls here.
In lab.py you describe each tool to Claude; these functions do the actual work.
"""
import json
from pathlib import Path

DATA = Path(__file__).parent / "data"
INCIDENT = json.loads((DATA / "incident.json").read_text(encoding="utf-8"))
INTEL = json.loads((DATA / "threat_intel.json").read_text(encoding="utf-8"))["indicators"]


def list_alerts(args):
    host = args.get("host")
    return json.dumps([a for a in INCIDENT["alerts"] if host in (None, a["host"])], indent=2)


def get_log_lines(args):
    needle = f"host={args['host']} "
    lines = [line for line in INCIDENT["log_lines"] if needle in line]
    return "\n".join(lines) or f"No log lines for host {args['host']}."


def lookup_indicator(args):
    verdict = INTEL.get(args["ip"])
    return json.dumps(verdict) if verdict else f"No intelligence on {args['ip']}."


RUN = {"list_alerts": list_alerts, "get_log_lines": get_log_lines, "lookup_indicator": lookup_indicator}
