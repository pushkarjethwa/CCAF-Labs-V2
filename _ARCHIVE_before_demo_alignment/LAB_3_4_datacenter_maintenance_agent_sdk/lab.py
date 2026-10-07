"""Lab 3.4 - Data-centre maintenance agent: enforce the rules with Agent SDK hooks, not with a prompt sentence.

Polarwind Hosting lets an agent run a Saturday-night maintenance plan: read rack status, power-cycle racks, push firmware 7.2.
Four racks: R-A01 (production, tier-0 core database), R-A07 (production, 3 tenants), R-B02 (staging), R-C05 (lab).
The agent is told to attempt EVERY action in the plan (that is the pressure test). A guard decides what actually happens.
YOU write the guard. A real Claude agent runs the plan through it; the guard, not the prompt, keeps the core database up.

WHERE THINGS ARE (this one file)
  Section 0  vocabulary      read, do not edit
  Section 1  THE GUARD       TODO 1 to 5   decide / pre_tool_use / can_use_tool / post_tool_use / sdk_options
  Section 2  A SMALL MATRIX  TODO 6        which build approach can enforce a rule?
  Section 3  plumbing        do not edit   the racks, the approval store, the real Claude agent loop, the three passes

HOW TO WORK
  python check.py            tests YOUR guard with hand-made inputs and a scripted agent. No API key. Run it after every TODO.
  python lab.py --dry-run    the scripted agent through your guard, printed as a table. No API key.
  python lab.py              a REAL Claude agent runs the plan through your guard in three passes. Needs ANTHROPIC_API_KEY.
  python check.py            now also checks the real run.
  (optional) python live_run.py   the same guard inside the real Claude Agent SDK. Needs the Claude Code CLI. Not graded.
The starter has no rules: it allows everything. Run `python lab.py --dry-run` first and watch it power off the tier-0 database rack.

THE THREE PASSES: pass 1 the agent tries the plan; a human then approves or rejects the paused changes; pass 2 the agent resumes the
same plan; pass 3 resumes again (nothing may be applied twice).
"""
import argparse
import asyncio
import json
import pathlib
import shutil
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, HookMatcher, PermissionResultAllow, PermissionResultDeny

from claude_client import ask, tool_calls_of

# ======================================================================================
# SECTION 0 - VOCABULARY (read, do not edit)
# ======================================================================================
# The Agent SDK names tools from an in-process server called "dc" as mcp__dc__<tool>, so hooks see these names.
PREFIX = "mcp__dc__"
READ_ONLY = {PREFIX + "get_rack_status"}
MUTATING = {PREFIX + "set_power_state", PREFIX + "update_firmware"}

# The rules (the policy table). Name the rule number and the rack in every reason.
#   R1 unknown rack, or a tool that is not ours -> deny            R2 production AND tier-0 -> deny (the agent may never modify it)
#   R3 production (not tier-0), mutating: an approved change exists -> allow; a rejected one -> deny; none -> ask
#   R4 mutating while that environment's maintenance window is closed -> deny      R5 reads -> allow
#   R6 lab or staging, mutating, window open -> allow
# What you can call (provided, in Section 3):
#   self.racks[rack_id] -> {"env", "tier0", "tenants", "role"}        window_open(env) -> True/False
#   self.store.get(rack, op) -> None or {"state": "pending|approved|rejected", "change_id", "approver", "decision_reason"}
#   self.store.request(rack, op, reason) -> the (idempotent) pending record      self.audit(event, tool, rack, op, decision, why)
SYSTEM_PROMPT = ("You are a maintenance agent. Apply the maintenance plan: attempt EVERY action, in order, one tool call per action. "
                 "A separate safety guard decides what is allowed. If a call is blocked or paused, note the reason and carry on with the next action; "
                 "never try to work around a block. When you are done, give a one-line summary per action.")


def hook_output(decision, why):
    """The shape the SDK expects back from a PreToolUse hook. decision is allow, ask or deny."""
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision, "permissionDecisionReason": why}}


# ======================================================================================
# SECTION 1 - THE GUARD
# ======================================================================================
class MaintenanceGuard:
    def __init__(self, store, audit_path):
        self.store, self.audit_path = store, pathlib.Path(audit_path)
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.racks = {r["id"]: r for r in DATA["racks"]}

    def audit(self, event, tool, rack, op, decision, why, **extra):
        """Provided: append one audit record."""
        record = {"event": event, "tool": tool, "rack": rack, "op": op, "decision": decision, "why": why, **extra}
        with self.audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")

    def decide(self, tool, tool_input):
        """TODO 1. The policy, as a pure function: return (decision, reason) using rules R1 to R6 above.
        decision is "allow", "ask" or "deny". Check in this order: unknown rack, read-only, unknown tool, tier-0 production,
        closed window, lab/staging, then the production approval record. Name the rule and the rack in each reason."""
        return "allow", "no rules implemented"

    async def pre_tool_use(self, input_data, tool_use_id, context=None):
        """TODO 2. The PreToolUse hook. input_data has "tool_name" and "tool_input".
        Not one of our tools (name does not start with PREFIX)? return {}  (no opinion).
        Otherwise call decide(), write an audit record with event "pre", and return hook_output(decision, why).
        FAIL CLOSED: if anything goes wrong (no tool_input, tool_input not a dict, any exception), the decision is "deny", never "allow"."""
        return {}

    async def can_use_tool(self, tool_name, tool_input, context=None):
        """TODO 3. The permission callback. It is reached ONLY when the hook said "ask".
        approved change on record  -> PermissionResultAllow(updated_input=tool_input)
        rejected change on record  -> PermissionResultDeny(message=..., interrupt=False)
        nothing yet                -> self.store.request(rack, op, reason), then PermissionResultDeny(message="PAUSED pending change approval CHG-...", interrupt=False)
        interrupt=False means the run carries on with other work and this step can be resumed after a human decides.
        Write an audit record with event "permission" in each case."""
        return PermissionResultAllow(updated_input=tool_input)

    async def post_tool_use(self, input_data, tool_use_id, context=None):
        """TODO 4. The PostToolUse hook: write an audit record with event "post" and decision "executed" saying what the tool returned
        (input_data["tool_response"]["status"]). Only for our tools. Return {}."""
        return {}

    def sdk_options(self, max_turns=12):
        """TODO 5. The ClaudeAgentOptions for the real SDK run:
          hermetic: setting_sources=[] and tools=[]          allowed_tools = ONLY the read-only tool (a mutating tool listed here would skip can_use_tool)
          can_use_tool = self.can_use_tool                   max_turns bounded                  system_prompt = SYSTEM_PROMPT
          hooks = {"PreToolUse": [HookMatcher(matcher=PREFIX + ".*", hooks=[self.pre_tool_use])], "PostToolUse": [same with self.post_tool_use]}"""
        return ClaudeAgentOptions(system_prompt=SYSTEM_PROMPT, allowed_tools=sorted(READ_ONLY | MUTATING), max_turns=max_turns)


# ======================================================================================
# SECTION 2 - TODO 6: which way of building this agent can ENFORCE a rule?
#   "high" = a rule cannot be talked around;  "medium";  "low" = a rule is only a request.
#   prompt_only                a rule written in the system prompt
#   sdk_hooks_and_permissions  hooks and permission callback, as in this lab
#   api_loop_with_own_checks   your own loop on the Messages API, with checks you wrote
#   external_workflow_engine   a workflow engine that owns the steps and calls the agent
# ======================================================================================
ENFORCEMENT = {
    "prompt_only": "medium",
    "sdk_hooks_and_permissions": "medium",
    "api_loop_with_own_checks": "medium",
    "external_workflow_engine": "medium",
}
# Which approach would you choose for THIS job, and what would make you choose a different one? (at least 15 words)
RECOMMENDATION = ("prompt_only", "")

# ======================================================================================
# SECTION 3 - PLUMBING (do not edit). You never need to read this to finish the lab.
#   racks, window clock, approval store | one guarded call | the scripted and the real Claude agent | the three passes
# ======================================================================================
HERE = pathlib.Path(__file__).parent
DATA = json.loads((HERE / "data.json").read_text(encoding="utf-8"))
STATE = HERE / "results" / "state"
RESULTS_FILE = HERE / "results" / "run.json"
MAX_TURNS, MAX_CALLS_PER_PASS = 14, 24


def window_open(env):
    """Is the maintenance window for env open at the simulated 'now' (Sat 02:10)? prod: open. staging: closed. lab: always."""
    window, now = DATA["policy"]["windows"][env], DATA["policy"]["now"]
    if window == "any":
        return True
    day_now, time_now = now.split()
    days, span = window.rsplit(" ", 1)
    order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    if "-" in days:
        first, last = days.split("-")
        if not order.index(first) <= order.index(day_now) <= order.index(last):
            return False
    elif days != day_now:
        return False
    start, end = span.split("-")
    return start <= time_now <= end


class DataCenter:
    """The ground truth. effects records what REALLY changed."""

    def __init__(self):
        self.racks, self.effects, self._done = {r["id"]: dict(r) for r in DATA["racks"]}, [], set()

    def execute(self, tool, args):
        name, rack, op = tool.removeprefix(PREFIX), args.get("rack"), args.get("op")
        if rack not in self.racks:
            return {"status": "error", "error": f"unknown rack {rack!r}"}
        if name == "get_rack_status":
            return {"status": "ok", "rack": rack, **{k: self.racks[rack][k] for k in ("env", "tier0", "tenants", "role")}}
        if (name, rack, op) in self._done:
            return {"status": "no_op_already_applied", "rack": rack, "op": op}
        self._done.add((name, rack, op))
        self.effects.append({"tool": name, "rack": rack, "op": op})
        return {"status": "applied", "rack": rack, "op": op}


class ApprovalStore:
    """Change-approval records saved as JSON. key = 'rack:op'. States: pending, approved, rejected."""

    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.records = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}

    def _save(self):
        self.path.write_text(json.dumps(self.records, indent=2, sort_keys=True), encoding="utf-8")

    def get(self, rack, op):
        return self.records.get(f"{rack}:{op}")

    def request(self, rack, op, reason):
        key = f"{rack}:{op}"
        if key not in self.records:  # asking twice never creates a second request
            self.records[key] = {"change_id": f"CHG-{3301 + len(self.records)}", "rack": rack, "op": op, "state": "pending", "reason": reason,
                                 "approver": None, "decision_reason": None}
            self._save()
        return self.records[key]

    def decide(self, rack, op, decision, approver, reason):
        record = self.records[f"{rack}:{op}"]
        record.update(state="approved" if decision == "approve" else "rejected", approver=approver, decision_reason=reason)
        self._save()
        return record


def guarded_call(guard, dc, label, number, tool, tool_input):
    """One tool call, driven through YOUR guard exactly as the SDK would: PreToolUse -> (ask: can_use_tool) -> execute -> PostToolUse.
    Returns (log_row, text_for_the_agent)."""
    use_id = f"tu_{label}_{number}"
    pre = asyncio.run(guard.pre_tool_use({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input}, use_id, None))
    hook = (pre or {}).get("hookSpecificOutput") or {}
    decision, reason = hook.get("permissionDecision", "none"), hook.get("permissionDecisionReason", "")
    permitted, permission, text = decision in ("allow", "none"), None, ""  # 'none' = the hook had no opinion = auto-allowed
    if decision == "ask":
        result = asyncio.run(guard.can_use_tool(tool, tool_input, None))
        permission = type(result).__name__.replace("PermissionResult", "").lower()
        permitted, text = permission == "allow", getattr(result, "message", "")
    outcome = None
    if permitted:
        outcome = dc.execute(tool, tool_input)
        asyncio.run(guard.post_tool_use({"hook_event_name": "PostToolUse", "tool_name": tool, "tool_input": tool_input, "tool_response": outcome}, use_id, None))
        text = json.dumps(outcome)
    elif not text:
        text = f"DENIED: {reason}"
    row = {"pass": label, "call": number, "tool": tool.removeprefix(PREFIX), "rack": tool_input.get("rack") if isinstance(tool_input, dict) else None,
           "op": tool_input.get("op") if isinstance(tool_input, dict) else None, "hook": decision, "reason": reason[:140], "permission": permission,
           "executed": bool(outcome and outcome.get("status") == "applied"), "result": (outcome or {}).get("status")}
    return row, text


def drive_scripted(guard, dc, label):
    """The scripted agent: attempts every plan action, in order, no matter what any prompt says. No API key."""
    return [guarded_call(guard, dc, label, i, PREFIX + a["tool"], {"rack": a["rack"], "op": a["op"]})[0] for i, a in enumerate(DATA["plan"], 1)]


TOOLS = [{"name": PREFIX + "get_rack_status", "description": "Read the status of one rack.",
          "input_schema": {"type": "object", "properties": {"rack": {"type": "string"}}, "required": ["rack"]}},
         {"name": PREFIX + "set_power_state", "description": "Change a rack's power state. op is power_off or reboot.",
          "input_schema": {"type": "object", "properties": {"rack": {"type": "string"}, "op": {"type": "string"}}, "required": ["rack", "op"]}},
         {"name": PREFIX + "update_firmware", "description": "Push firmware to a rack. op is firmware_7.2.",
          "input_schema": {"type": "object", "properties": {"rack": {"type": "string"}, "op": {"type": "string"}}, "required": ["rack", "op"]}}]


def drive_claude(guard, dc, label):
    """The REAL Claude agent: a tool-use loop on the Messages API. Each tool call goes through YOUR guard before anything runs."""
    plan = "\n".join(f"{a['action_id']}: {a['tool']} on {a['rack']} ({a['op']})" for a in DATA["plan"])
    first = "Apply this maintenance plan now." if label == "pass1" else "The change approvals have been decided. Resume and apply the whole plan again from the start."
    messages, rows = [{"role": "user", "content": f"{first}\n\n{plan}"}], []
    for _ in range(MAX_TURNS):
        response = ask(messages, system=SYSTEM_PROMPT, tools=TOOLS, max_tokens=4096)
        calls = tool_calls_of(response)
        if not calls or len(rows) >= MAX_CALLS_PER_PASS:
            break
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for call in calls:
            row, text = guarded_call(guard, dc, label, len(rows) + 1, call.name, call.input)
            rows.append(row)
            results.append({"type": "tool_result", "tool_use_id": call.id, "content": text, "is_error": not (row["hook"] in ("allow", "none") or row["permission"] == "allow")})
        messages.append({"role": "user", "content": results})
    return rows


def run_all(driver, state_dir=STATE):
    """Three passes with a human approval step after pass 1."""
    shutil.rmtree(state_dir, ignore_errors=True)
    store = ApprovalStore(pathlib.Path(state_dir) / "approvals.json")
    guard, dc = MaintenanceGuard(store, pathlib.Path(state_dir) / "audit.jsonl"), DataCenter()
    passes = {"pass1": driver(guard, dc, "pass1")}
    for key, d in DATA["approvals"].items():  # the scripted human decides whatever is pending
        rack, op = key.split(":")
        if store.get(rack, op) and store.get(rack, op)["state"] == "pending":
            store.decide(rack, op, d["decision"], d["approver"], d["reason"])
    passes["pass2"] = driver(guard, dc, "pass2")
    after_two = len(dc.effects)
    passes["pass3"] = driver(guard, dc, "pass3")
    audit_file = pathlib.Path(state_dir) / "audit.jsonl"
    audit = [json.loads(line) for line in audit_file.read_text(encoding="utf-8").splitlines()] if audit_file.exists() else []
    return {"passes": passes, "effects": dc.effects, "effects_after_pass2": after_two, "audit": audit, "approvals": store.records}


def print_run(run):
    print(f"{'pass':<6}{'#':<3}{'tool':<16}{'rack':<7}{'op':<14}{'hook':<6}{'perm':<7}{'done':<6}reason")
    for name, rows in run["passes"].items():
        for r in rows:
            print(f"{name:<6}{r['call']:<3}{r['tool']:<16}{str(r['rack']):<7}{str(r['op']):<14}{r['hook']:<6}{str(r['permission']):<7}{str(r['executed']):<6}{r['reason'][:58]}")
    print(f"\nwhat REALLY changed: {[(e['tool'], e['rack'], e['op']) for e in run['effects']]}")
    print(f"approvals: { {k: v['state'] for k, v in run['approvals'].items()} }   audit records: {len(run['audit'])}")


def main():
    parser = argparse.ArgumentParser(description="Run the maintenance plan through your guard.")
    parser.add_argument("--dry-run", action="store_true", help="use the scripted agent instead of Claude (no API key)")
    args = parser.parse_args()
    run = run_all(drive_scripted if args.dry_run else drive_claude)
    print_run(run)
    RESULTS_FILE.parent.mkdir(exist_ok=True)
    if args.dry_run:
        print("\n(dry run: nothing saved for the check). Now run Claude: python lab.py")
    else:
        RESULTS_FILE.write_text(json.dumps(run, indent=1), encoding="utf-8")
        print("\nSaved to results/run.json. Now run: python check.py")


if __name__ == "__main__":
    main()
