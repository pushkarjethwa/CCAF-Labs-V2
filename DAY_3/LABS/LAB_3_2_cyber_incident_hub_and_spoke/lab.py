"""Lab 3.2 - Cyber incident response: a hub-and-spoke coordinator that is thin, isolated and honest about failure.

At 03:14 a SIEM raised INC-7741 at Nordlicht Logistics. A hub (the orchestrator) delegates to four specialists:
    triage -> log_analysis -> threat_intel -> containment_plan
The hub also holds PRIVATE context (honeypot names, a legal hold, a customer email) that must never reach a specialist.
The log_analysis specialist is a REAL Claude call. The other three are scripted stand-ins. The delegation loop is provided.
YOU write the small rules the hub follows: what a valid hand-off looks like, what each specialist may see, and what to do when one fails.

WHERE THINGS ARE (this one file)
  Section 0  vocabulary      read, do not edit
  Section 1  CONTRACTS       TODO 1, 2, 3   what is a valid hand-off, and how do we ask for a fix?
  Section 2  BRIEFS          TODO 4         what may each specialist see?
  Section 3  FAILURE RULES   TODO 5, 6      when do we retry, and who depends on whom?
  Section 4  plumbing        do not edit    the specialists, the delegation loop that calls YOUR functions, the four scenarios

HOW TO WORK
  python check.py    tests YOUR functions with hand-made inputs. No API key. Run it after every TODO.
  python lab.py      runs 4 scenarios; Claude does the real log analysis. Needs ANTHROPIC_API_KEY.
  python check.py    now also checks the scenarios (leaks, validation, bounded retries, honest failure).
The starter is naive on purpose: it hands the full history to every specialist, computes IPs itself, and accepts any output. Run it once and read the leak.
"""
import argparse
import json
import pathlib
import sys
from collections import defaultdict

from claude_client import ask, text_of

# ======================================================================================
# SECTION 0 - VOCABULARY (read, do not edit)
# ======================================================================================
ORDER = ["triage", "log_analysis", "threat_intel", "containment_plan"]
REPUTATIONS = ("malicious", "benign", "unknown")
RISKS = ("low", "medium", "high")
MAX_REWORK = 1   # a rejected hand-off gets this many corrective re-asks
MAX_RETRY = 1    # an unavailable specialist gets this many plain retries
RUNAWAY_LIMIT = 5  # safety net: the loop stops any rule that never stops retrying


class HandoffError(Exception):
    """A specialist's output was unusable. Carries the list of problems."""

    def __init__(self, agent, problems):
        super().__init__(f"{agent} handoff rejected: " + "; ".join(problems))
        self.agent, self.problems = agent, problems


class SubagentError(Exception):
    """A specialist could not answer at all (backend down, timeout)."""

    def __init__(self, agent, message):
        super().__init__(f"{agent}: {message}")
        self.agent = agent


# ======================================================================================
# SECTION 1 - CONTRACTS: what a valid hand-off looks like
# ======================================================================================
# TODO 1. For each kind, name each field and its Python type (str, list, bool). triage is done as the worked example.
#   log_analysis     timeline (list of {ts, event}), suspicious_ips (list), compromised_accounts (list)
#   threat_intel     matches (list of {indicator, reputation, campaign})
#   containment_plan actions (list of {action, target, risk}), requires_approval (bool)
# Every payload also needs incident_id (str); the provided checker handles that and the "present and right type" test.
FIELDS = {
    "triage": {"severity": str, "category": str, "affected_hosts": list},
    "log_analysis": {},
    "threat_intel": {},
    "containment_plan": {},
}


def semantic_problems(kind, payload, incident_id):
    """TODO 2. A payload can have the right shape and still be wrong. Return a list of problem strings (empty = fine):
      - payload["incident_id"] differs from incident_id (a specialist answered about another incident)
      - threat_intel: a match whose reputation is not in REPUTATIONS
      - containment_plan: requires_approval is False while any action has risk "high"  (an unapproved isolation)
    This runs only after the shape is already right, so you can index fields directly."""
    return []  # the starter believes every specialist


def correction(problems):
    """TODO 3. The message sent back to the specialist for ONE rework. It MUST start with the word CORRECTION and list every problem."""
    return ""  # the starter never explains what was wrong


# ======================================================================================
# SECTION 2 - BRIEFS: least privilege. A specialist gets ONLY the fields it needs.
# ======================================================================================
def brief_for(agent, incident, results):
    """TODO 4. Build the brief (a dict) for `agent`. `incident` has incident_id, alerts, hosts, log_lines; `results` holds the validated
    outputs of earlier specialists, e.g. results["log_analysis"]["suspicious_ips"]. Every brief has "incident_id", plus:
      triage            alerts
      log_analysis      hosts, log_lines
      threat_intel      indicators = the suspicious_ips that log_analysis found     (the hub must not work them out itself)
      containment_plan  severity (from triage), hosts = triage's affected_hosts, accounts = log_analysis's compromised_accounts,
                        indicators = log_analysis's suspicious_ips
    Never include a "history" dump and never anything from PRIVATE."""
    import re  # the starter works out IPs itself and forwards everything it knows
    seen = " ".join(incident["log_lines"])
    ips = sorted(set(re.findall(r"src=(\d+\.\d+\.\d+\.\d+)", seen)) - {"10.4.2.17", "10.4.9.8", "10.4.1.5"})
    everything = json.dumps({"incident": incident, "private_context": PRIVATE["note"], "results": results})
    return {"history": everything, "incident_id": incident["incident_id"], "alerts": incident["alerts"], "hosts": incident["hosts"],
            "log_lines": incident["log_lines"], "indicators": ips, "severity": "high", "accounts": ["deploy"]}


# ======================================================================================
# SECTION 3 - FAILURE RULES
# ======================================================================================
def delegate_rule(failure, tries):
    """TODO 5. A specialist just failed. `failure` is "malformed" (it answered, but the hand-off was rejected) or "unavailable" (no answer);
    `tries` counts calls so far (1 = the first call just failed). Return "rework", "retry" or "give_up":
      malformed    -> "rework" (re-ask WITH a correction) while tries <= MAX_REWORK, then "give_up"
      unavailable  -> "retry"  (plain, no correction)     while tries <= MAX_RETRY,  then "give_up"
    Every path must end."""
    return "give_up"  # the starter never retries, never reworks


# TODO 6. Who depends on whom? If a specialist in the list fails, the dependants are SKIPPED (the hub stops that branch and says so).
# Only list real needs: containment needs triage and log_analysis. Does it need threat_intel? An outage of intel should not stop containment.
NEEDS = {
    # (the starter lists no dependencies, so downstream specialists run on missing data)
}

# ======================================================================================
# SECTION 4 - PLUMBING (do not edit). You never need to read this to finish the lab.
#   the specialists (one real Claude call) | fault injection | the delegation loop | the four scenarios
# ======================================================================================
HERE = pathlib.Path(__file__).parent
DATA = json.loads((HERE / "data.json").read_text(encoding="utf-8"))
INCIDENT, PRIVATE, INTEL = DATA["incident"], DATA["private"], DATA["intel"]
RESULTS_FILE = HERE / "results" / "scenarios.json"
SCENARIOS = {"S1": {}, "S2": {"threat_intel": "raise"}, "S3": {"log_analysis": "malformed_once"}, "S4": {"log_analysis": "malformed_always"}}
LABELS = {"S1": "normal run", "S2": "threat_intel backend is down", "S3": "log_analysis answers malformed once",
          "S4": "log_analysis answers malformed every time"}


def _echo(brief):
    """Specialists restate whatever 'history' they are handed, the way a real model often does. Private data you forward WILL come back."""
    return ("context restated: " + str(brief["history"])[:300]) if brief.get("history") else ""


def triage(brief):
    per_host = defaultdict(int)
    for a in brief["alerts"]:
        per_host[a["host"]] += 1
    severe = any(a["severity"] == "critical" for a in brief["alerts"]) or max(per_host.values()) >= 3
    hosts = sorted(h for h in per_host if any(a["host"] == h and a["severity"] in ("high", "critical") for a in brief["alerts"]))
    category = "credential_attack" if any("login" in a["summary"].lower() for a in brief["alerts"]) else "unknown"
    return {"incident_id": brief["incident_id"], "severity": "high" if severe else "medium", "category": category, "affected_hosts": hosts, "notes": _echo(brief)}


def threat_intel(brief):
    matches = [{"indicator": i, "reputation": INTEL.get(i, {}).get("reputation", "unknown"), "campaign": INTEL.get(i, {}).get("campaign")} for i in brief["indicators"]]
    return {"incident_id": brief["incident_id"], "matches": matches, "notes": _echo(brief)}


def containment_plan(brief):
    actions = [{"action": "block_ip", "target": i, "risk": "low"} for i in brief["indicators"]]
    actions += [{"action": "disable_account", "target": a, "risk": "medium"} for a in brief["accounts"]]
    actions += [{"action": "isolate_host", "target": h, "risk": "high"} for h in brief["hosts"]]
    return {"incident_id": brief["incident_id"], "actions": actions, "requires_approval": any(a["risk"] == "high" for a in actions), "notes": _echo(brief)}


LOG_SYSTEM = ("You are a log analyst in an incident response team. From the log lines, find: a timeline of the key events (list of {ts, event}), "
              "suspicious_ips (EXTERNAL addresses that attacked or received data; never 10.x internal addresses), and compromised_accounts "
              "(accounts with a successful login after repeated failures). Reply with JSON only: "
              '{"incident_id": "...", "timeline": [{"ts": "...", "event": "..."}], "suspicious_ips": ["..."], "compromised_accounts": ["..."], '
              '"notes": "one sentence"}. If a CORRECTION is given, fix exactly what it says.')


def log_analysis(brief):
    """The REAL Claude specialist. API trouble (429, 5xx) becomes SubagentError, so your rules treat it as 'unavailable'."""
    user = json.dumps({k: v for k, v in brief.items() if k != "feedback"}) + (f"\n\n{brief['feedback']}" if brief.get("feedback") else "")
    try:
        text = text_of(ask([{"role": "user", "content": user}], system=LOG_SYSTEM, max_tokens=4096))
    except Exception as exc:
        if getattr(exc, "status_code", None):
            raise SubagentError("log_analysis", f"{exc.status_code} {str(exc)[:80]}") from exc
        raise
    try:
        out = json.loads(text[text.find("{"):text.rfind("}") + 1])
    except ValueError:
        return {}  # unreadable reply: your contract will reject it
    out = out if isinstance(out, dict) else {}
    out.setdefault("incident_id", brief["incident_id"])
    return out


AGENTS = {"triage": triage, "log_analysis": log_analysis, "threat_intel": threat_intel, "containment_plan": containment_plan}


class Runtime:
    """Calls a specialist with ONLY the brief it is given. faults = {agent: 'raise' | 'malformed_once' | 'malformed_always'} (injected)."""

    def __init__(self, faults=None):
        self.faults, self.calls = dict(faults or {}), defaultdict(int)

    def call(self, agent, brief):
        self.calls[agent] += 1
        mode = self.faults.get(agent)
        if mode == "raise":
            raise SubagentError(agent, "503 backend unavailable")
        out = AGENTS[agent](brief)
        corrected = str(brief.get("feedback", "")).startswith("CORRECTION")
        if mode == "malformed_always" or (mode == "malformed_once" and not corrected):
            out = dict(out)
            out.pop("suspicious_ips", None)   # injected fault: a missing field ...
            out["timeline"] = "see logs"      # ... and a wrong type
        return out


def shape_problems(kind, payload):
    if not isinstance(payload, dict):
        return ["the output is not an object"]
    wanted = {"incident_id": str, **FIELDS[kind]}
    return [f"{name}: missing" if name not in payload else f"{name}: expected {t.__name__}, got {type(payload[name]).__name__}"
            for name, t in wanted.items() if name not in payload or not isinstance(payload[name], t)]


def handoff_problems(kind, payload, incident_id):
    """Shape first, then your semantic rules. Returns a list of problems (empty = the hand-off is acceptable)."""
    return shape_problems(kind, payload) or semantic_problems(kind, payload, incident_id)


def run_incident(incident, runtime):
    iid = incident["incident_id"]
    report = {"incident_id": iid, "status": "complete", "needs_human": False, "summary": "", "severity": None, "actions": [],
              "failures": [], "rejections": [], "trace": [], "briefs": {}, "results": {}, "skipped": []}

    def delegate(agent, brief):
        tries, feedback = 0, None
        while tries < RUNAWAY_LIMIT:
            tries += 1
            try:
                out = runtime.call(agent, dict(brief, feedback=feedback) if feedback else brief)
                problems = handoff_problems(agent, out, iid)
                if not problems:
                    return out
                failure, detail = "malformed", problems
            except SubagentError as err:
                failure, detail = "unavailable", [str(err)]
            if failure == "malformed":
                report["rejections"].append({"agent": agent, "reason": "; ".join(detail)})
            action = delegate_rule(failure, tries)
            if action not in ("rework", "retry"):
                break
            feedback = correction(detail) if action == "rework" else None
        report["failures"].append({"agent": agent, "class": "reasoning" if failure == "malformed" else "environment",
                                   "message": "; ".join(detail)[:160], "retries": tries - 1})
        return None

    for agent in ORDER:
        if any(need not in report["results"] for need in NEEDS.get(agent, [])):
            report["skipped"].append(agent)
            continue
        brief = brief_for(agent, incident, report["results"])
        report["briefs"][agent] = brief
        report["trace"].append({"step": len(report["trace"]) + 1, "agent": agent})
        out = delegate(agent, brief)
        if out is not None:
            report["results"][agent] = out
    r = report["results"]
    report["severity"] = (r.get("triage") or {}).get("severity")
    report["actions"] = (r.get("containment_plan") or {}).get("actions", [])
    broken = [f["agent"] for f in report["failures"]] + report["skipped"]
    report["status"] = "failed" if report["skipped"] else "partial" if report["failures"] else "complete"
    report["needs_human"] = bool(broken) or bool((r.get("containment_plan") or {}).get("requires_approval"))
    notes = [str(x.get("notes", "")) for x in r.values() if x.get("notes")]
    report["summary"] = " | ".join([f"{iid}: severity {report['severity']}, {len(report['actions'])} proposed action(s)"] + notes
                                   + ([f"INCOMPLETE: {', '.join(broken)} did not finish; a human must review"] if broken else []))
    return report


def run_scenario(sid, log=print):
    runtime = Runtime(SCENARIOS[sid])
    try:
        report = run_incident(INCIDENT, runtime)
    except Exception as err:  # a crash in your code is a finding, not a stack trace
        report = {"status": f"CRASH {type(err).__name__}: {err}", "needs_human": False, "failures": [], "rejections": [], "trace": [],
                  "briefs": {}, "results": {}, "actions": [], "summary": "", "skipped": []}
    report.update(scenario_id=sid, label=LABELS[sid], runtime_calls=dict(runtime.calls), faults=SCENARIOS[sid])
    return report


def main():
    parser = argparse.ArgumentParser(description="Run the incident scenarios with a real Claude log analyst.")
    parser.add_argument("--scenario", choices=list(SCENARIOS), help="run one scenario (default: all four)")
    chosen = [parser.parse_args().scenario] if "--scenario" in sys.argv else list(SCENARIOS)
    out = []
    print(f"{'id':<4}{'status':<10}{'human':<7}{'calls':<46}{'failed':<18}trace")
    for sid in chosen:
        rep = run_scenario(sid)
        out.append(rep)
        print(f"{sid:<4}{str(rep['status'])[:9]:<10}{str(rep['needs_human']):<7}{str(rep['runtime_calls'])[:45]:<46}"
              f"{str([f['agent'] for f in rep['failures']])[:17]:<18}{[t['agent'] for t in rep['trace']]}")
    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("\nSaved to results/scenarios.json. Now run: python check.py")


if __name__ == "__main__":
    main()
