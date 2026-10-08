"""Lab 5.3 - Evals and provenance for an invoice checker (continues Demo 5C: same stages, a supplier-invoice story).

A model reads a supplier invoice and returns a decision, the line ids it relied on, the total and an escalate flag.
You write four small pieces here:

  TODO 1  the grader        plain code that checks one answer against its label
  TODO 2  the source check  how many of the cited line ids really exist in the invoice
  TODO 3  the release gate  GATE: PASS or GATE: BLOCKED from the v1 and v2 results
  TODO 4  the review queue  writes the answers that need a person to a file

HOW TO RUN
  python check.py            pass/fail in plain words. Part A needs no key and no model.
  python lab.py --stage 1    runs prompt v1 on 8 invoices and grades it (needs ANTHROPIC_API_KEY)
  python lab.py --stage 2    checks the sources of the v1 run (no key)
  python lab.py --stage 3    runs prompt v2, compares with v1, prints the gate (needs a key)
  python lab.py --stage 4    writes the human-review queue (no key)
The data, the prompts and the grade table are in invoice_core.py. You do not need to read it.
"""
import argparse
import json
import pathlib

import invoice_core as core
from claude_client import MODEL_BALANCED, cost_usd, get_client, text_of


# ======================================================================================
# TODO 1 of 4 - THE GRADER
# grade(output, case) returns a dictionary with five True or False checks:
#   schema    the answer has the right shape (core.schema_ok(output) tells you)
#   decision  output["decision"] equals case["expected_decision"]
#   items     every id in case["required_items"] is in output["citations"]
#   total     output["total"] is within 1 percent of case["expected_total"]
#   escalate  output["escalate"] equals case["expected_escalate"]
# When the shape is wrong, all five checks are False.
# ======================================================================================
def grade(output, case):
    if not core.schema_ok(output):
        return {name: False for name in core.CHECKS}
    return {
        "schema": True,
        "decision": output["decision"] == case["expected_decision"],
        "items": set(case["required_items"]) <= set(output["citations"]),
        "total": abs(output["total"] - case["expected_total"]) <= 0.01 * case["expected_total"],
        "escalate": output["escalate"] == case["expected_escalate"],
    }


# ======================================================================================
# TODO 2 of 4 - THE SOURCE CHECK
# coverage(output, invoice) returns the share of cited ids that exist in the invoice, from 0.0 to 1.0.
# invoice["lines"] is a list of {"id": ..., "text": ...}. output["citations"] is a list of ids.
# ======================================================================================
def coverage(output, invoice):
    ids = {line["id"] for line in invoice["lines"]}
    cited = output["citations"]
    return sum(item in ids for item in cited) / len(cited)


# ======================================================================================
# TODO 3 of 4 - THE RELEASE GATE
# old and new are dictionaries like {"I01": True, "I02": False}: True means the case passed all five checks.
# Return "GATE: BLOCKED" when any of these is true, otherwise "GATE: PASS":
#   a case that passed in old fails in new          (a regression)
#   a must-escalate case (expected_escalate is True) fails in new
#   fewer cases pass in new than in old
# ======================================================================================
def release_gate(old, new):
    regressed = [case for case in old if old[case] and not new[case]]
    missed = [case["id"] for case in core.CASES if case["expected_escalate"] and not new[case["id"]]]
    if regressed or missed or sum(new.values()) < sum(old.values()):
        return "GATE: BLOCKED"
    return "GATE: PASS"


# ======================================================================================
# TODO 4 of 4 - THE REVIEW QUEUE
# outputs is a dictionary {case id: answer}. An answer needs a person when its total is at or above core.ESCALATION_VALUE,
# or when its escalate flag is True. Make a list with one dictionary per such answer: case, total and evidence (its citations).
# Write the list to `path` as JSON, and return it.
# ======================================================================================
def write_queue(outputs, path):
    queue = []
    for case_id, output in outputs.items():
        if output["total"] >= core.ESCALATION_VALUE or output["escalate"]:
            queue.append({"case": case_id, "total": output["total"], "evidence": output["citations"]})
    path.write_text(json.dumps(queue, indent=2), encoding="utf-8")
    return queue


# ======================================================================================
# RUNNING THE STAGES - do not edit below this line
# ======================================================================================
COST = [0.0]


def ask(system, user):
    """The Claude call: one Messages API request, and the reply text."""
    response = get_client().messages.create(
        model=MODEL_BALANCED,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    COST[0] += cost_usd(response)
    return text_of(response)


def run_version(version):
    """Run one prompt version on all invoices and save the answers to results/run_<version>.json."""
    records = []
    for case in core.CASES:
        reply = ask(core.prompt(version), core.invoice_text(core.INVOICES[case["id"]]))
        records.append({"case": case["id"], "version": version, "model": MODEL_BALANCED, "output": core.parse_json(reply)})
        print(f"  {version} {case['id']} done")
    core.RESULTS.mkdir(exist_ok=True)
    (core.RESULTS / f"run_{version}.json").write_text(json.dumps(records, indent=1), encoding="utf-8")
    return records


def grade_run(records):
    cases = {c["id"]: c for c in core.CASES}
    return {r["case"]: grade(r["output"], cases[r["case"]]) for r in records}


def passed_by_case(records):
    return {case: all(checks.values()) for case, checks in grade_run(records).items()}


def stage1():
    print(f"Stage 1: run prompt v1 on {len(core.CASES)} invoices with {MODEL_BALANCED}, then grade with plain code.\n")
    records = run_version("v1")
    print()
    core.print_table(records, grade_run(records))
    print(f"\nPass rate for v1: {sum(passed_by_case(records).values())}/{len(core.CASES)}")
    print(f"Cost of this stage: ${COST[0]:.4f}")


def stage2():
    records = core.load_run("v1")
    print("Stage 2: do the line ids that v1 cited exist in the invoice?\n")
    print(f"{'case':<6}{'cited':<8}coverage")
    shares = []
    for record in records:
        if core.schema_ok(record["output"]):
            share = coverage(record["output"], core.INVOICES[record["case"]])
            shares.append(share)
            print(f"{record['case']:<6}{len(record['output']['citations']):<8}{100 * share:.0f}%" + ("" if share == 1 else "   <- an id that is not in the invoice"))
    print(f"\nProvenance coverage for v1: {100 * sum(shares) / len(shares):.0f}% of cited ids exist.")
    print("\nThe record kept for one answer:")
    print(json.dumps(core.audit_record(records[0]), indent=2))


def stage3():
    print(f"Stage 3: run prompt v2 on the same {len(core.CASES)} invoices, compare with v1, and apply the gate.\n")
    old = passed_by_case(core.load_run("v1"))
    new = passed_by_case(run_version("v2"))
    print(f"\n{'case':<6}{'v1':<7}{'v2':<7}change")
    for case in core.CASES:
        before, after = old[case["id"]], new[case["id"]]
        change = "improved" if after and not before else "REGRESSED" if before and not after else "same"
        print(f"{case['id']:<6}{'PASS' if before else 'FAIL':<7}{'PASS' if after else 'FAIL':<7}{change}")
    print(f"\nPass rate: v1 {sum(old.values())}/{len(old)}, v2 {sum(new.values())}/{len(new)}")
    print(f"\n{release_gate(old, new)}")
    print(f"Cost of this stage: ${COST[0]:.4f}")


def stage4():
    records = core.load_run("v2")
    print("Stage 4: send the v2 answers that need a person to the human-review queue.\n")
    outputs = {r["case"]: r["output"] for r in records if core.schema_ok(r["output"])}
    queue = write_queue(outputs, core.RESULTS / "human_review_queue.json")
    for item in queue:
        print(f"{item['case']}  total USD {item['total']:,.0f}  evidence: {', '.join(item['evidence'])}")
    must = {c["id"] for c in core.CASES if c["expected_escalate"]}
    queued = {item["case"] for item in queue}
    print(f"\nWritten to results/human_review_queue.json: {len(queue)} of {len(outputs)} answers.")
    print(f"Must-escalate cases in the queue: {len(must & queued)}/{len(must)}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, choices=[1, 2, 3, 4], help="run one stage; without it, all four run in order")
    args = parser.parse_args()
    for number, stage in enumerate([stage1, stage2, stage3, stage4], 1):
        if args.stage in (None, number):
            stage()
            print()
