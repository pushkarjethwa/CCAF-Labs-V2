"""Lab 3.1 - Product recall: choose the architecture, then decompose with the least power that works.

Halvorsen Home Appliances is recalling a kettle line. You make two sets of decisions, as two small tables:
  TABLE 1  four briefs  -> conversational, workflow or agentic?   (who controls the next step?)
  TABLE 2  seven recall steps -> agent, tool or fixed_step?       (and how will you test each one?)
There is no JSON and no schema to author. You fill in rows. The rules and a real Claude critique are provided.

WHERE THINGS ARE (this one file)
  Section 0  vocabulary    the allowed words              (read, do not edit)
  Section 1  TABLE 1       4 rows                         YOU fill in
  Section 2  TABLE 2       7 rows + 1 pick                YOU fill in
  Section 3  plumbing      the rules, the Claude critique (do not edit)

HOW TO WORK
  python lab.py --show   prints the four briefs and the seven steps with their known facts
  python lab.py          checks your tables against the rules; if they pass, Claude critiques your design (needs ANTHROPIC_API_KEY)
  python check.py        pass/fail in plain words (no key needed for the rules part)
Read the facts, not your intuition. The starter says "everything is an agent"; run it once to see what the rules say.
"""
import argparse
import hashlib
import json
import pathlib

from claude_client import ask, text_of

# ======================================================================================
# SECTION 0 - VOCABULARY (read, do not edit)
# ======================================================================================
# conversational: the USER decides each next turn.   workflow: the PROCEDURE decides, steps known in advance.
# agentic: the model decides its own next action because nobody can write the path in advance.
ARCHITECTURES = ("conversational", "workflow", "agentic")
SIGNALS = {  # the "deciding signal": what really decides the next step
    "conversational": ("user_driven_turns",),
    "workflow": ("fixed_known_steps", "route_by_category", "parallel_independent_items"),
    "agentic": ("open_ended_path",),
}
# agent: a model chooses its own next action in a loop.   tool: deterministic, typed, no model decisions.
# fixed_step: position and logic are fixed in code; it may contain at most ONE scripted model call.
KINDS = ("agent", "tool", "fixed_step")
# exact: compare to one right answer.  schema: check the shape/fields.  rubric: score against criteria (for non-deterministic output).
TEST_TYPES = ("exact", "schema", "rubric")
DATA_FLOWS = ("one_shared_db", "explicit_handoffs")   # how do the components share data?

# ======================================================================================
# SECTION 1 - TABLE 1: the four briefs.   row = (architecture, deciding signal, one-sentence reason from the brief's facts)
#   architecture: conversational | workflow | agentic      signal: see SIGNALS above      reason: at least 10 words, cite a fact
# ======================================================================================
ARCHITECTURE = {
    "RB-1": ("conversational", "user_driven_turns", "The customer decides each next turn and may switch topic, and every chat concerns exactly one customer."),
    "RB-2": ("workflow", "fixed_known_steps", "The regulators publish the procedure, the steps are always the same, and approval is recorded before submission."),
    "RB-3": ("workflow", "route_by_category", "Each reply gets one label and a fixed routing table picks the queue, and replies never affect each other."),
    "RB-4": ("agentic", "open_ended_path", "Which record to query next depends on what the last query revealed, so nobody can write the path in advance."),
}

# ======================================================================================
# SECTION 2 - TABLE 2: the seven recall steps.   row = (kind, reason, test type, what the test checks)
#   kind: agent | tool | fixed_step      reason: at least 6 words (an AGENT needs at least 8 and must name the source of non-determinism)
#   test type: agent -> rubric or schema;  tool / fixed_step -> exact or schema      test: at least 4 words, concrete
#   Hints: least power wins (fixed_step < tool < agent... the rules tell you where a step may NOT be an agent).
#   A step that needs one piece of generated text is a fixed_step (it may hold one scripted model call); a tool never calls a model.
# ======================================================================================
STEPS = {
    "R1": ("agent", "The evidence trail is unknown in advance and each query depends on what the previous one revealed.", "rubric", "Every lot on the planted list is found with evidence and a confidence."),
    "R2": ("fixed_step", "The regulators publish fixed templates and the procedure never changes.", "exact", "A lot with a missing mandatory field is stopped and reported, never submitted."),
    "R3": ("fixed_step", "The approved text and contact list are fixed so only code needs to loop over them.", "exact", "Every contact on the export receives exactly one approved notice."),
    "R4": ("tool", "One WMS call places a hold on stock and the logic is fully deterministic.", "exact", "After the call every affected lot shows status HOLD in all warehouses."),
    "R5": ("tool", "Assigning pickups is a deterministic capacity calculation with no judgment needed.", "exact", "No carrier is booked above its capacity and every request gets a slot."),
    "R6": ("tool", "Reconciling counts against units shipped is arithmetic on two databases.", "exact", "Returned plus destroyed plus outstanding equals units shipped for every lot."),
    "R7": ("fixed_step", "The inputs are fixed counts and receipts and only the wording needs one model call.", "schema", "The status has the required sections and quotes the reconciled counts exactly."),
}

# How do your components share data? One of DATA_FLOWS. (Two components writing one record in different orders is a real recall bug.)
DATA_FLOW = "explicit_handoffs"

# ======================================================================================
# SECTION 3 - PLUMBING (do not edit): the rules, the Claude critique, the saved result
# ======================================================================================
HERE = pathlib.Path(__file__).parent
DATA = json.loads((HERE / "data.json").read_text(encoding="utf-8"))
RESULTS_FILE = HERE / "results" / "design.json"
NONDETERMINISM_TERMS = ("non-determin", "open-ended", "unknown", "unpredictable", "cannot be written", "not known in advance", "ambiguous",
                        "judgment", "free-text", "free text", "varies", "depends on what", "nobody can")
ARCH_HINT = {  # shown when a pick is wrong: the fact to look at, never the answer
    "RB-1": "who decides what happens after the assistant's reply?",
    "RB-2": "who decides the steps, and do they ever change from night to night?",
    "RB-3": "does one reply change how the next one is handled? what picks the queue?",
    "RB-4": "can anyone write the query sequence in advance? what decides which record to check next?",
}


def words(text):
    return len(str(text or "").split())


def check_tables(architecture, steps, data_flow):
    """Return a list of (where, rule, plain-language message). Empty list = your design passes every rule."""
    found = []

    def add(where, rule, message):
        found.append((where, rule, message))

    expected = {"RB-1": "conversational", "RB-2": "workflow", "RB-3": "workflow", "RB-4": "agentic"}
    for brief in DATA["briefs"]:
        bid = brief["id"]
        arch, signal, reason = architecture.get(bid, (None, None, None))
        if arch not in ARCHITECTURES:
            add(bid, "A1", f"architecture {arch!r} must be one of {ARCHITECTURES}")
            continue
        if arch != expected[bid]:
            add(bid, "A2", f"{arch} is not the least powerful mechanism that works. Ask: {ARCH_HINT[bid]}")
        if signal not in SIGNALS[arch]:
            add(bid, "A3", f"deciding signal {signal!r} does not fit {arch}; choose from {SIGNALS[arch]}")
        if words(reason) < 10:
            add(bid, "A4", f"reason has {words(reason)} words; write at least 10 and cite a fact from the brief")
    agent_steps = []
    for step in DATA["steps"]:
        sid, facts = step["id"], step["facts"]
        kind, reason, test_type, test = steps.get(sid, (None,) * 4)
        if kind not in KINDS:
            add(sid, "S1", f"kind {kind!r} must be one of {KINDS}")
            continue
        if kind == "agent":
            agent_steps.append(sid)
            if facts["path_known_in_advance"]:
                add(sid, "S2", f"{step['name']}: the path IS known in advance, so an agent is more power than needed. Use a tool or fixed_step")
            elif words(reason) < 8 or not any(t in str(reason).lower() for t in NONDETERMINISM_TERMS):
                add(sid, "S3", "an agent needs a reason of at least 8 words that names the source of non-determinism (e.g. 'depends on what the last query revealed')")
        else:
            if not facts["path_known_in_advance"]:
                add(sid, "S4", f"{step['name']}: the path is NOT known in advance, so a fixed step or tool cannot do it")
            if words(reason) < 6:
                add(sid, "S5", f"reason has {words(reason)} words; write at least 6")
            if sid == "R7" and kind == "tool":
                add(sid, "S6", "this step must produce free text from numbers; a tool has no model call. Which kind may hold one scripted model call?")
        if test_type not in TEST_TYPES:
            add(sid, "T1", f"test type {test_type!r} must be one of {TEST_TYPES}")
        elif kind == "agent" and test_type == "exact":
            add(sid, "T2", "an agent's output varies, so an exact-match test cannot work; use rubric or schema")
        elif kind != "agent" and test_type == "rubric":
            add(sid, "T2", "a deterministic component needs an exact or schema test; a rubric means it is not deterministic")
        if words(test) < 4:
            add(sid, "T3", f"the test has {words(test)} words; say concretely what it checks (at least 4)")
    if len(agent_steps) > DATA["max_agents"]:
        add("design", "L1", f"{len(agent_steps)} agents; the limit is {DATA['max_agents']}")
    chose_agentic = any(row[0] == "agentic" for row in architecture.values())
    if bool(agent_steps) != chose_agentic:
        add("design", "L2", f"coherence: the design has {len(agent_steps)} agent step(s) but your briefs {'do' if chose_agentic else 'do not'} include an agentic one. The two tables must agree")
    if data_flow != "explicit_handoffs":
        add("design", "L3", "components that share one mutable database overwrite each other. Pass data through explicit hand-offs")
    return found


def table_fingerprint(architecture, steps, data_flow):
    blob = json.dumps([architecture, steps, data_flow], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


CRITIC_SYSTEM = ("You are a senior architect reviewing a recall-programme design. Judge it ONLY on: least powerful mechanism per step, "
                 "agents only where the path is unknown, one clear test per step. Be brief and concrete. Reply with JSON only: "
                 '{"weakest_pick": "<id of the pick you trust least>", "why": "<one sentence>", '
                 '"findings": [{"item": "<id>", "issue": "<one sentence>"}], "verdict": "<one sentence>"}. An empty findings list is fine if the design is sound.')


def critique_with_claude(architecture, steps, data_flow):
    """One real Claude call. Advisory: the rules above are the judge, Claude is a second opinion."""
    summary = {"briefs": {k: {"architecture": v[0], "signal": v[1], "reason": v[2]} for k, v in architecture.items()},
               "steps": {k: {"kind": v[0], "reason": v[1], "test_type": v[2], "test": v[3]} for k, v in steps.items()},
               "data_flow": data_flow}
    facts = [{"id": s["id"], "name": s["name"], "facts": s["facts"]} for s in DATA["steps"]]
    prompt = f"Known facts about the recall steps:\n{json.dumps(facts)}\n\nThe design to review:\n{json.dumps(summary)}"
    text = text_of(ask([{"role": "user", "content": prompt}], system=CRITIC_SYSTEM, max_tokens=4096))
    try:
        parsed = json.loads(text[text.find("{"):text.rfind("}") + 1])
        return parsed if isinstance(parsed, dict) else {"raw": text}
    except ValueError:
        return {"raw": text}


def show():
    print(f"\n{DATA['company']} - recall case {DATA['case']}\n\nTABLE 1 - the four briefs")
    for brief in DATA["briefs"]:
        print(f"\n{brief['id']}  {brief['title']}\n  {brief['text']}\n  facts: {json.dumps(brief['facts'])}")
    print("\nTABLE 2 - the seven recall steps (facts decide, not intuition)")
    for step in DATA["steps"]:
        print(f"\n{step['id']}  {step['name']}\n  {step['description']}\n  facts: {json.dumps(step['facts'])}")
    print(f"\nlimit: at most {DATA['max_agents']} agents")


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
