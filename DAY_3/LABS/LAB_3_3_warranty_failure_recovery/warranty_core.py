"""warranty_core.py - the warranty claims agent's mock world and helpers (Demo 3C). DO NOT EDIT.

You do not need to read this file to finish the lab. It holds the mock warranty tools, the tool and system-prompt definitions
the agent sends to Claude, the fixed pipeline from stage 2 of the demo, and the check that a decision matches the tool results.
Everything you write is in lab.py.
"""
import calendar
import datetime as dt
import json
from pathlib import Path

DATA = Path(__file__).parent / "data"


def load(name):
    """Read one JSON file from the data folder."""
    return json.loads((DATA / name).read_text(encoding="utf-8"))


REGISTRY = load("registry.json")["registrations"]
TERMS = load("warranty_terms.json")
CASES = load("cases.json")
TODAY = dt.date.fromisoformat(CASES["today"])
CLAIMS = {}


def add_months(start, months):
    """Return the date `months` after `start`."""
    year, month = divmod(start.month - 1 + months, 12)
    year, month = start.year + year, month + 1
    return dt.date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


def lookup_product_registration(serial):
    """Find the product registration for a serial number."""
    return {"serial": serial, **REGISTRY[serial]}


def check_warranty_terms(serial, issue_type):
    """Apply the warranty terms: is this issue covered today, and which rule says so?"""
    record = REGISTRY[serial]
    plan = TERMS["plans"][record["plan"]]
    expires = add_months(dt.date.fromisoformat(record["purchase_date"]), plan["months"])
    if TODAY > expires:
        covered, rule_id, reason = False, TERMS["expired_rule_id"], f"the {record['plan']} plan expired on {expires}"
    elif issue_type not in plan["covered"]:
        covered, rule_id, reason = False, TERMS["excluded_rule_id"], f"{issue_type} is not covered by the {record['plan']} plan"
    else:
        covered, rule_id, reason = True, plan["rule_id"], f"{issue_type} is covered by the {record['plan']} plan until {expires}"
    return {"serial": serial, "issue_type": issue_type, "covered": covered, "rule_id": rule_id, "reason": reason}


def create_claim(serial, issue_type, customer_id):
    """File the claim and return its number."""
    number = f"WC-{100231 + len(CLAIMS):06d}"
    CLAIMS[number] = {"claim_number": number, "serial": serial, "issue_type": issue_type, "customer_id": customer_id, "status": "filed"}
    return dict(CLAIMS[number])


def schedule_pickup(claim_number, preferred_date, zone):
    """Book the courier pickup for a filed claim."""
    return {"pickup_id": "PU-" + claim_number[3:], "claim_number": claim_number, "date": preferred_date, "zone": zone, "status": "scheduled"}


def submit_decision(decision, reason, claim_number="", pickup_id=""):
    """Record the final decision. This is the last step of every run."""
    return {"decision": decision, "reason": reason, "claim_number": claim_number, "pickup_id": pickup_id}


TOOL_FUNCTIONS = {f.__name__: f for f in (lookup_product_registration, check_warranty_terms, create_claim, schedule_pickup, submit_decision)}


MAX_TURNS = 10   # the agent loop never runs longer than this


# ── THE AGENT'S DEFINITIONS ──────────────────────────────────────────────────

TOOLS = [
    {"name": "lookup_product_registration", "description": "Look up the product registration for a serial number (two capital letters and eight digits).",
     "input_schema": {"type": "object", "properties": {"serial": {"type": "string"}}, "required": ["serial"]}},
    {"name": "check_warranty_terms", "description": "Check whether the issue is covered by the warranty today. Returns covered, rule_id and reason.",
     "input_schema": {"type": "object", "properties": {"serial": {"type": "string"}, "issue_type": {"type": "string"}}, "required": ["serial", "issue_type"]}},
    {"name": "create_claim", "description": "File a warranty claim. Returns the claim_number. Only for covered issues.",
     "input_schema": {"type": "object", "properties": {"serial": {"type": "string"}, "issue_type": {"type": "string"}, "customer_id": {"type": "string"}},
                      "required": ["serial", "issue_type", "customer_id"]}},
    {"name": "schedule_pickup", "description": "Schedule the courier pickup for a filed claim.",
     "input_schema": {"type": "object", "properties": {"claim_number": {"type": "string"}, "preferred_date": {"type": "string"}, "zone": {"type": "string"}},
                      "required": ["claim_number", "preferred_date", "zone"]}},
    {"name": "submit_decision", "description": "Record the final decision. Call this last. decision is approved or denied.",
     "input_schema": {"type": "object", "properties": {"decision": {"type": "string", "enum": ["approved", "denied"]}, "reason": {"type": "string"},
                      "claim_number": {"type": "string"}, "pickup_id": {"type": "string"}}, "required": ["decision", "reason"]}},
]

AGENT_SYSTEM = ("You are a warranty claims agent. For each request: 1) look up the registration; 2) check the warranty terms; "
                "3) if the issue is covered, create the claim and schedule the pickup; 4) call submit_decision with the final decision. "
                "If the issue is not covered, do not create a claim: submit a denied decision with the reason. Use the tools, one step at a time.")


# ── THE CHECK AND THE FIXED PIPELINE ─────────────────────────────────────────

def summarize(case, records, turns):
    """Boil a run down to one row: the decision, how many turns it took, and whether the decision agrees with the tool results."""
    data = {record["tool"]: record["data"] for record in records}
    decision = data.get("submit_decision")
    verified = decision is not None and decision["decision"] == ("approved" if data["check_warranty_terms"]["covered"] else "denied")
    if verified and decision["decision"] == "approved":
        verified = decision["claim_number"] == data["create_claim"]["claim_number"] and decision["pickup_id"] == data["schedule_pickup"]["pickup_id"]
    return {"case": case["id"], "decision": decision, "turns": turns, "tools": [record["tool"] for record in records], "verified": verified}


def run_pipeline(hooks, case):
    """The fixed pipeline from stage 2: the same tools, called in a fixed order by plain code. Uses YOUR run_tool and decide."""
    run_tool, decide = hooks["run_tool"], hooks["decide"]
    form, records = case["form"], []
    records.append(run_tool("lookup_product_registration", {"serial": form["serial"]}))
    terms = run_tool("check_warranty_terms", {"serial": form["serial"], "issue_type": form["issue_type"]})
    records.append(terms)
    verdict = decide(terms["data"])
    if verdict["decision"] == "approved":
        claim = run_tool("create_claim", {"serial": form["serial"], "issue_type": form["issue_type"], "customer_id": form["customer_id"]})
        pickup = run_tool("schedule_pickup", {"claim_number": claim["data"]["claim_number"], "preferred_date": form["preferred_date"], "zone": form["zone"]})
        records += [claim, pickup]
    decision = {"decision": verdict["decision"], "reason": verdict["reason"]}
    if verdict["decision"] == "approved":
        decision.update(claim_number=claim["data"]["claim_number"], pickup_id=pickup["data"]["pickup_id"])
    records.append(run_tool("submit_decision", decision))
    return summarize(case, records, turns=0)
