"""Lab 3.1 - ACME expense desk: choose the architecture, then decompose with the least power that works.

This lab continues Demo 3A (same company, same T&E policy, same signals, same seven-step claim review).

WHAT YOU EDIT (four places, each marked "TODO n of 4"; the guide in README.md gives the exact code for each)
  TODO 1  Table 1  four briefs      -> conversational, workflow or agentic
  TODO 2  Table 2  seven steps      -> agent, tool or fixed_step
  TODO 3  one value                 -> how the steps pass the claim along
  TODO 4  one Claude API call       -> a second opinion on your design

HOW TO RUN
  python lab.py --show   print the briefs and steps with their facts
  python lab.py          check your tables against the rules, then (if they pass) ask Claude for a second opinion
  python check.py        pass/fail in plain words
"""
import argparse
import hashlib
import json
import pathlib

from claude_client import MODEL_BALANCED, get_client, text_of

# ======================================================================================
# VOCABULARY (read only). Same words as the Stage 1 rubric in Demo 3A.
# ======================================================================================
ARCHITECTURES = ("conversational", "workflow", "agentic")
CONTROLLERS = ("human", "process", "model")  # who decides the next step?
PREDICTABILITY = ("single_step", "known_branches", "fixed_sequence", "open_ended")
KINDS = ("agent", "tool", "fixed_step")  # agent: model picks next action | tool: plain code | fixed_step: plain code + at most one model call
TEST_TYPES = ("exact", "schema", "rubric")  # exact: one right answer | schema: right shape | rubric: scored against criteria
DATA_FLOWS = ("one_shared_db", "explicit_handoffs")


def architecture_for(controller):
    """The same rule as Demo 3A: who controls the next step decides the architecture."""
    return {"human": "conversational", "process": "workflow", "model": "agentic"}[controller]


# ======================================================================================
# TODO 1 of 4 - TABLE 1: the four briefs
# Row format:   "FB-n": (architecture, next_step_controller, path_predictability),
# Allowed words are in VOCABULARY above. Run `python lab.py --show` to see each brief's facts.
# ======================================================================================
ARCHITECTURE = {
    "FB-1": ("conversational", "human", "single_step"),
    "FB-2": ("workflow", "process", "fixed_sequence"),
    "FB-3": ("workflow", "process", "known_branches"),
    "FB-4": ("agentic", "model", "open_ended"),
}

# ======================================================================================
# TODO 2 of 4 - TABLE 2: the seven steps of the claim review
# Row format:   "E-n": (kind, "one-sentence reason", test_type),
# kind is agent, tool or fixed_step. An agent's reason must name why the path is unknown.
# ======================================================================================
STEPS = {
    "E1": ("fixed_step", "The claim text is free-form but the step never changes, so one scripted model call turns it into fields.", "schema"),
    "E2": ("tool", "The finance rates are fixed and the conversion is plain arithmetic with no judgment.", "exact"),
    "E3": ("tool", "Comparing employee, merchant, date and amount with history is a deterministic lookup.", "exact"),
    "E4": ("tool", "A pre-approval ticket either exists and is valid or it does not, so a lookup decides.", "exact"),
    "E5": ("tool", "The caps and violation codes are written in the policy so plain code applies them every time.", "exact"),
    "E6": ("agent", "Which record to pull next depends on what the last lookup revealed, so nobody can write the path in advance.", "rubric"),
    "E7": ("fixed_step", "The decision and codes are fixed inputs and only the wording needs one scripted model call.", "schema"),
}

# ======================================================================================
# TODO 3 of 4 - how do the steps pass the claim along? One of DATA_FLOWS.
# (If E5 and E6 both write the same shared claim row, one can overwrite the other.)
# ======================================================================================
DATA_FLOW = "explicit_handoffs"

# ======================================================================================
# TODO 4 of 4 - your first Claude API call
# `prompt` is the text to send. CRITIC_SYSTEM is the instruction that makes Claude act as a reviewer.
# ======================================================================================
CRITIC_SYSTEM = ("You are a senior architect reviewing an expense-desk design. Judge it ONLY on: least powerful mechanism per step, "
                 "agents only where the path is unknown, one clear test per step. Be brief and concrete. Reply with JSON only: "
                 '{"weakest_pick": "<id of the pick you trust least>", "why": "<one sentence>", '
                 '"findings": [{"item": "<id>", "issue": "<one sentence>"}], "verdict": "<one sentence>"}. '
                 "An empty findings list is fine if the design is sound.")


def call_claude(prompt):
    """Send `prompt` to Claude and return the answer text."""
    response = get_client().messages.create(
        model=MODEL_BALANCED,
        max_tokens=2048,
        system=CRITIC_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return text_of(response)


# ======================================================================================
# PLUMBING - do not edit below this line
# ======================================================================================
HERE = pathlib.Path(__file__).parent
DATA = json.loads((HERE / "data.json").read_text(encoding="utf-8"))
RESULTS_FILE = HERE / "results" / "design.json"
NONDETERMINISM_TERMS = ("depends on what", "nobody can", "open-ended", "not known in advance", "cannot be written", "unpredictable", "unknown")


def words(text):
    return len(str(text or "").split())


def check_tables(architecture, steps, data_flow):
    """Return a list of (where, rule, message). An empty list means the design passes every rule."""
    found = []

    def add(where, rule, message):
        found.append((where, rule, message))

    for brief in DATA["briefs"]:
        bid, facts = brief["id"], brief["facts"]
        arch, controller, predictability = architecture.get(bid, (None, None, None))
        if arch not in ARCHITECTURES:
            add(bid, "A1", f"architecture {arch!r} must be one of {ARCHITECTURES}")
            continue
        if controller != facts["next_step_controller"]:
            add(bid, "A2", f"next_step_controller {controller!r} does not match the brief. Who decides the next step? ({brief['evidence']['next_step_controller']})")
        if predictability != facts["path_predictability"]:
            add(bid, "A3", f"path_predictability {predictability!r} does not match the brief. How predictable is the path? ({brief['evidence']['path_predictability']})")
        if arch != architecture_for(facts["next_step_controller"]):
            add(bid, "A4", f"{arch} is not what the Demo 3A rubric gives for a brief where the {facts['next_step_controller']} decides the next step")
    agent_steps = []
    for step in DATA["steps"]:
        sid, facts = step["id"], step["facts"]
        kind, reason, test_type = steps.get(sid, (None, None, None))
        if kind not in KINDS:
            add(sid, "S1", f"kind {kind!r} must be one of {KINDS}")
            continue
        if kind == "agent":
            agent_steps.append(sid)
            if facts["path_known_in_advance"]:
                add(sid, "S2", f"{step['name']}: the path IS known in advance, so an agent is more power than needed. Use a tool or fixed_step")
            elif words(reason) < 8 or not any(t in str(reason).lower() for t in NONDETERMINISM_TERMS):
                add(sid, "S3", "an agent needs a reason of at least 8 words that says why the path is unknown (for example 'depends on what the last lookup revealed')")
        else:
            if not facts["path_known_in_advance"]:
                add(sid, "S4", f"{step['name']}: the path is NOT known in advance, so a tool or fixed step cannot do it")
            if words(reason) < 6:
                add(sid, "S5", f"reason has {words(reason)} words; write at least 6")
            if kind == "tool" and facts["needs_free_text_judgment"]:
                add(sid, "S6", f"{step['name']} needs a model call to read or write free text, and a tool never calls a model. Which kind may hold one scripted model call?")
        if test_type not in TEST_TYPES:
            add(sid, "T1", f"test type {test_type!r} must be one of {TEST_TYPES}")
        elif kind == "agent" and test_type == "exact":
            add(sid, "T2", "an agent's output varies, so an exact-match test cannot work; use rubric or schema")
        elif kind != "agent" and test_type == "rubric":
            add(sid, "T2", "a deterministic component needs an exact or schema test; a rubric means it is not deterministic")
    if len(agent_steps) > DATA["max_agents"]:
        add("design", "L1", f"{len(agent_steps)} agents; the limit is {DATA['max_agents']}")
    chose_agentic = any(row[0] == "agentic" for row in architecture.values())
    if bool(agent_steps) != chose_agentic:
        add("design", "L2", f"coherence: the design has {len(agent_steps)} agent step(s) but your briefs {'do' if chose_agentic else 'do not'} include an agentic one. The two tables must agree")
    if data_flow != "explicit_handoffs":
        add("design", "L3", "steps that share one mutable claim row can overwrite each other. Pass the claim along through explicit hand-offs")
    return found


def table_fingerprint(architecture, steps, data_flow):
    return hashlib.sha256(json.dumps([architecture, steps, data_flow], sort_keys=True).encode()).hexdigest()[:16]


def critique_with_claude(architecture, steps, data_flow):
    """Build the prompt, call Claude (your TODO 4), and parse the JSON reply. Advisory: the rules are the judge."""
    summary = {"briefs": {k: {"architecture": v[0], "controller": v[1], "predictability": v[2]} for k, v in architecture.items()},
               "steps": {k: {"kind": v[0], "reason": v[1], "test_type": v[2]} for k, v in steps.items()},
               "data_flow": data_flow}
    facts = [{"id": s["id"], "name": s["name"], "facts": s["facts"]} for s in DATA["steps"]]
    text = call_claude(f"Known facts about the claim-review steps:\n{json.dumps(facts)}\n\nThe design to review:\n{json.dumps(summary)}")
    try:
        parsed = json.loads(text[text.find("{"):text.rfind("}") + 1])
        return parsed if isinstance(parsed, dict) else {"raw": text}
    except ValueError:
        return {"raw": text}


def show():
    print(f"\n{DATA['company']} (policy {DATA['policy_version']})\n\nTABLE 1 - the four briefs")
    for brief in DATA["briefs"]:
        print(f"\n{brief['id']}  {brief['title']}\n  {brief['text']}\n  facts: {json.dumps(brief['facts'])}")
    print("\nTABLE 2 - the seven steps of the claim review")
    for step in DATA["steps"]:
        print(f"\n{step['id']}  {step['name']}\n  {step['description']}\n  facts: {json.dumps(step['facts'])}")
    print(f"\nlimit: at most {DATA['max_agents']} agent")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--show", action="store_true", help="print the briefs and steps, then stop")
    if parser.parse_args().show:
        return show()
    problems = check_tables(ARCHITECTURE, STEPS, DATA_FLOW)
    print("YOUR DESIGN, checked against the rules (no model involved)\n")
    for where, rule, message in problems:
        print(f"[FAIL] {rule} {where:<7} {message}")
    print(f"\n{len(problems)} problem(s)" if problems else "All rules pass.")
    result = {"fingerprint": table_fingerprint(ARCHITECTURE, STEPS, DATA_FLOW), "rule_problems": [list(p) for p in problems],
              "kinds": {k: sum(1 for v in STEPS.values() if v[0] == k) for k in KINDS}, "critique": None}
    if problems:
        print("Fix these first; Claude's critique is only worth asking for once the rules pass.")
    else:
        print("\nAsking Claude for a second opinion ...")
        result["critique"] = critique_with_claude(ARCHITECTURE, STEPS, DATA_FLOW)
        crit = result["critique"]
        print(f"  weakest pick : {crit.get('weakest_pick')} - {crit.get('why')}")
        for f in crit.get("findings", []):
            print(f"  - {f.get('item')}: {f.get('issue')}")
        print(f"  verdict      : {crit.get('verdict')}\n(Advisory. Where Claude and the rules disagree, the rules win, but ask yourself why.)")
    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print("\nSaved to results/design.json. Now run: python check.py")


if __name__ == "__main__":
    main()
