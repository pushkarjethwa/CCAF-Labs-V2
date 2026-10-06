"""check.py - Part A tests YOUR functions (no key needed). Part B checks the saved results of `python lab.py`.

Each line says what is expected in plain words. Exit code 0 = everything passed.
"""
import json
import sys

import lab

results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f"\n         {detail}" if detail and not ok else ""))


def safe(fn, *args):
    try:
        return fn(*args)
    except Exception as err:  # a crash in student code is a failed check, not a crashed checker
        return f"crashed: {err!r}"


def rejects(kind, payload, iid="I"):
    got = safe(lab.handoff_problems, kind, payload, iid)
    return isinstance(got, list) and len(got) > 0


def accepts(kind, payload, iid="I"):
    return safe(lab.handoff_problems, kind, payload, iid) == []


ALLOWED_KEYS = {"triage": {"incident_id", "alerts"}, "log_analysis": {"incident_id", "hosts", "log_lines"},
                "threat_intel": {"incident_id", "indicators"},
                "containment_plan": {"incident_id", "severity", "hosts", "accounts", "indicators"}}

# ---------------------------------------------------------------- PART A
print("PART A - your functions, tested with hand-made inputs (no API key)\n")

print("TODO 1, 2 - contracts")
log_ok = {"incident_id": "I", "timeline": [{"ts": "t", "event": "e"}], "suspicious_ips": ["1.1.1.1"], "compromised_accounts": []}
check(accepts("log_analysis", log_ok), "log_analysis: a good payload is accepted")
check(rejects("log_analysis", {k: v for k, v in log_ok.items() if k != "suspicious_ips"}), "log_analysis: a missing field is rejected")
check(rejects("log_analysis", dict(log_ok, timeline="see logs")), "log_analysis: a wrong type (timeline as text) is rejected")
check(rejects("log_analysis", log_ok, "OTHER"), "log_analysis: an answer about another incident is rejected")
intel_ok = {"incident_id": "I", "matches": [{"indicator": "x", "reputation": "malicious", "campaign": None}]}
check(accepts("threat_intel", intel_ok) and not accepts("threat_intel", {"incident_id": "I"}), "threat_intel: needs a matches list")
check(rejects("threat_intel", {"incident_id": "I", "matches": [{"indicator": "x", "reputation": "evil", "campaign": None}]}),
      "threat_intel: an unknown reputation value is rejected")
plan = {"incident_id": "I", "actions": [{"action": "isolate_host", "target": "h", "risk": "high"}], "requires_approval": False}
check(rejects("containment_plan", plan), "containment_plan: a high-risk action without approval is rejected")
check(accepts("containment_plan", dict(plan, requires_approval=True)), "containment_plan: the same plan WITH approval is accepted")
check(rejects("containment_plan", dict(plan, requires_approval="yes")), "containment_plan: requires_approval must be true or false, not text")

print("\nTODO 3 - correction message")
msg = safe(lab.correction, ["field a is missing", "field b has the wrong type"])
check(isinstance(msg, str) and msg.startswith("CORRECTION") and "field a is missing" in msg and "field b has the wrong type" in msg,
      "the message starts with CORRECTION and lists every problem", f"got {msg!r}")

print("\nTODO 4 - briefs (least privilege)")
incident, private = lab.INCIDENT, lab.PRIVATE
sample = {"triage": {"severity": "high", "affected_hosts": ["bastion-02"]},
          "log_analysis": {"suspicious_ips": ["9.9.9.9"], "compromised_accounts": ["acct-x"]}}
briefs = {a: safe(lab.brief_for, a, incident, sample) for a in lab.ORDER}
check(all(isinstance(b, dict) for b in briefs.values()), "brief_for returns a dict for every specialist", str(briefs)[:150])
if all(isinstance(b, dict) for b in briefs.values()):
    check(all("history" not in b for b in briefs.values()), "no brief carries a 'history' dump")
    extra = {a: sorted(set(b) - ALLOWED_KEYS[a]) for a, b in briefs.items() if set(b) - ALLOWED_KEYS[a]}
    check(not extra, "every brief has only the fields that specialist needs", f"extra fields: {extra}")
    missing = {a: sorted(ALLOWED_KEYS[a] - set(b)) for a, b in briefs.items() if ALLOWED_KEYS[a] - set(b)}
    check(not missing, "every brief has ALL the fields that specialist needs", f"missing: {missing}")
    leaked = [t for t in private["scan_terms"] if t in json.dumps(briefs)]
    check(not leaked, "no private-context term appears in any brief", f"leaked: {leaked}")
    check(briefs["threat_intel"].get("indicators") == ["9.9.9.9"] and briefs["containment_plan"].get("indicators") == ["9.9.9.9"],
          "indicators come from the log_analysis hand-off (the hub does no analysis itself)", f"got {briefs['threat_intel'].get('indicators')}")
    check(briefs["containment_plan"].get("hosts") == ["bastion-02"] and briefs["containment_plan"].get("accounts") == ["acct-x"]
          and briefs["containment_plan"].get("severity") == "high", "containment gets hosts and severity from triage, accounts from log_analysis")

print("\nTODO 5 - delegate_rule")
rules = [(("malformed", 1), "rework"), (("malformed", 2), "give_up"), (("unavailable", 1), "retry"), (("unavailable", 2), "give_up")]
for args, want in rules:
    got = safe(lab.delegate_rule, *args)
    check(got == want, f"{args[0]:<12} after call {args[1]} -> {want}", f"got {got!r}")

print("\nTODO 6 - NEEDS")
needs = lab.NEEDS
check(isinstance(needs, dict) and "log_analysis" in needs.get("threat_intel", []), "threat_intel needs log_analysis")
check(isinstance(needs, dict) and {"triage", "log_analysis"} <= set(needs.get("containment_plan", [])), "containment_plan needs triage and log_analysis")
check(isinstance(needs, dict) and "threat_intel" not in needs.get("containment_plan", []),
      "containment_plan does NOT need threat_intel (an intel outage must not stop containing an attack)")

part_a_ok = all(results)

# ---------------------------------------------------------------- PART B
print("\nPART B - the four scenarios from `python lab.py` (log analysis is a real Claude call)\n")
if not lab.RESULTS_FILE.exists():
    print("[SKIP] results/scenarios.json not found - run `python lab.py` (needs ANTHROPIC_API_KEY), then this again.")
elif not part_a_ok:
    print("[SKIP] fix Part A first; the scenarios call your functions, so they would only repeat the same mistakes.")
else:
    rows = {r["scenario_id"]: r for r in json.loads(lab.RESULTS_FILE.read_text(encoding="utf-8"))}
    s1, s2, s3, s4 = (rows.get(k, {}) for k in ("S1", "S2", "S3", "S4"))
    check(len(rows) == 4 and not any(str(r.get("status", "")).startswith("CRASH") for r in rows.values()), "all four scenarios ran without crashing",
          str({k: r.get("status") for k, r in rows.items()}))
    blob = lambda r: json.dumps({"b": r.get("briefs"), "r": r.get("results"), "s": r.get("summary")})  # noqa: E731
    leaks = {k: [t for t in private["scan_terms"] if t in blob(r)] for k, r in rows.items()}
    check(not any(leaks.values()), "LEAK TEST: no private term in any brief, result or summary, in any scenario", f"leaked: { {k: v for k, v in leaks.items() if v} }")
    ips = {m["indicator"] for m in s1.get("results", {}).get("threat_intel", {}).get("matches", [])}
    check(ips == {"203.0.113.50", "198.51.100.77"}, "S1: threat-intel looked up the two attacker addresses from Claude's log analysis",
          f"got {sorted(ips)}. If Claude listed other addresses, re-run `python lab.py`")
    acts = {(a["action"], a["target"]) for a in s1.get("actions", [])}
    check(s1.get("status") == "complete" and s1.get("needs_human") is True and {("isolate_host", "bastion-02"), ("disable_account", "deploy")} <= acts,
          "S1: complete; the plan isolates bastion-02 and disables deploy; the high-risk action goes to a human", f"status={s1.get('status')} actions={sorted(acts)}")
    check([t["agent"] for t in s1.get("trace", [])] == lab.ORDER, "S1: the trace shows triage, log_analysis, threat_intel, containment_plan in order")
    f2 = [f for f in s2.get("failures", []) if f.get("agent") == "threat_intel"]
    check(s2.get("status") == "partial" and len(f2) == 1 and f2[0].get("class") == "environment" and s2.get("needs_human") is True,
          "S2: an unavailable specialist is NOT hidden: status partial, environment failure recorded, a human flagged", f"status={s2.get('status')} failures={s2.get('failures')}")
    check("threat_intel" in str(s2.get("summary")) and "containment_plan" in s2.get("results", {}) and s2.get("runtime_calls", {}).get("threat_intel") == 2,
          "S2: the summary names the failure, containment still ran, and there was exactly one retry")
    check(s3.get("status") == "complete" and len(s3.get("rejections", [])) == 1 and s3.get("runtime_calls", {}).get("log_analysis") == 2,
          "S3: a malformed hand-off was rejected once and fixed by ONE corrective re-ask", f"rejections={s3.get('rejections')} calls={s3.get('runtime_calls')}")
    trace4 = [t["agent"] for t in s4.get("trace", [])]
    check(s4.get("status") == "failed" and s4.get("needs_human") is True and s4.get("runtime_calls", {}).get("log_analysis") == 2
          and "threat_intel" not in trace4 and "containment_plan" not in trace4 and any(f["agent"] == "log_analysis" and f["class"] == "reasoning" for f in s4.get("failures", [])),
          "S4: a stubborn bad hand-off stops after one rework, fails loudly, runs nothing downstream, and goes to a human",
          f"status={s4.get('status')} calls={s4.get('runtime_calls')} trace={trace4}")
    check(all(sum(r.get("runtime_calls", {}).values()) <= 8 for r in rows.values()), "every scenario makes a bounded number of specialist calls (8 or fewer)")

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
