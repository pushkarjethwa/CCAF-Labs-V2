"""Lab 3.1 - ACME expense desk: build the same review two ways and compare them.

This lab continues Demo 3A (same company, same briefs, same T&E policy, same claims R01-R12, same two builds).

WHAT YOU EDIT (three places, each marked "TODO n of 3"; the guide in README.md gives the exact code for each)
  TODO 1  architecture_for      -> the rule from Demo 3A: who controls the next step?
  TODO 2  run_conversational    -> Build 1: ONE Claude call reads the policy and decides alone
  TODO 3  run_workflow          -> Build 2: ONE Claude call extracts fields, plain code applies the policy

HOW TO RUN
  python lab.py          vote on the five briefs, then review six claims both ways and compare
  python check.py        pass/fail in plain words
"""
import hashlib
import inspect
import json
import pathlib

from claude_client import MODEL_BALANCED, get_client
from expense_core import (ANSWER_FORMAT, BRIEFS, CLAIMS, EXTRACTION_SCHEMA, POLICY, apply_policy, claim_facts,
                          decision_in, json_in, policy_text, text_of)

# ======================================================================================
# TODO 1 of 3 - the rubric from Demo 3A, stage 1
# `signals` is a dict like {"next_step_controller": "human", ...}.
# human   -> "conversational"   (the person steers every turn)
# process -> "workflow"         (a written procedure fixes the path)
# model   -> "agentic"          (only the model can choose the path as it goes)
# ======================================================================================
def architecture_for(signals):
    controller = signals["next_step_controller"]
    if controller == "human":
        return "conversational"
    if controller == "process":
        return "workflow"
    return "agentic"


# ======================================================================================
# TODO 2 of 3 - Build 1 from Demo 3A: CONVERSATIONAL. One Claude call, no tools.
# The model reads the whole policy and decides alone. Return "approve", "reject" or "escalate".
# ======================================================================================
def run_conversational(claim):
    system = f"You review expense claims against this policy ({POLICY['version']}).\n{policy_text()}\n{ANSWER_FORMAT}"
    response = get_client().messages.create(
        model=MODEL_BALANCED,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": claim_facts(claim)}],
    )
    return decision_in(text_of(response))


# ======================================================================================
# TODO 3 of 3 - Build 2 from Demo 3A: WORKFLOW. Fixed steps.
# Step 1: ONE Claude call turns the free-text claim into fields (the model's only job).
# Step 2: plain code, apply_policy(), makes the decision. Return "approve", "reject" or "escalate".
# ======================================================================================
def run_workflow(claim):
    system = ("Extract the expense fields from the claim text. Reply with JSON only, matching this schema exactly:\n"
              + json.dumps(EXTRACTION_SCHEMA))
    response = get_client().messages.create(
        model=MODEL_BALANCED,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": claim["text"]}],
    )
    fields = json_in(text_of(response))
    return apply_policy(fields, claim)[0]


# ======================================================================================
# PLUMBING - do not edit below this line
# ======================================================================================
HERE = pathlib.Path(__file__).parent
RESULTS_FILE = HERE / "results" / "run.json"
LAB_CLAIMS = ["R02", "R03", "R05", "R07", "R09", "R10"]  # six of the demo's twelve claims: approve, reject and escalate


def code_fingerprint():
    source = "".join(inspect.getsource(f) for f in (architecture_for, run_conversational, run_workflow))
    return hashlib.sha256(source.encode()).hexdigest()[:16]


def main():
    print(f"\nPART 1 - vote on the five briefs from Demo 3A (policy {POLICY['version']})\n")
    votes = {}
    for brief in BRIEFS:
        votes[brief["id"]] = architecture_for(brief["signals"])
        print(f"  Brief {brief['id']}: {brief['title']:<58} -> {votes[brief['id']]}")

    print(f"\nPART 2 - review {len(LAB_CLAIMS)} claims two ways (this calls Claude {2 * len(LAB_CLAIMS)} times)\n")
    print(f"  {'claim':<6}{'expected':<10}{'conversational':<16}{'workflow':<10}")
    rows = []
    for claim in (c for c in CLAIMS if c["id"] in LAB_CLAIMS):
        conversational, workflow = run_conversational(claim), run_workflow(claim)
        rows.append({"claim": claim["id"], "expected": claim["expected_decision"], "conversational": conversational, "workflow": workflow})
        print(f"  {claim['id']:<6}{claim['expected_decision']:<10}{conversational:<16}{workflow:<10}")
    score = {build: sum(r[build] == r["expected"] for r in rows) for build in ("conversational", "workflow")}
    print(f"\n  correct: conversational {score['conversational']}/{len(rows)}, workflow {score['workflow']}/{len(rows)}")
    print("  Same task, two builds. In the workflow the model reads the claim and code applies the policy.")

    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text(json.dumps({"fingerprint": code_fingerprint(), "votes": votes, "rows": rows, "score": score}, indent=1), encoding="utf-8")
    print("\nSaved to results/run.json. Now run: python check.py")


if __name__ == "__main__":
    main()
