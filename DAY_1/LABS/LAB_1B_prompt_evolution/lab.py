"""Lab 1B - Larkspur invoices: take a one-line prompt through seven versions and measure every step.

This lab continues Demo 1B (same vendor invoices, same prompt versions v0 to v6, same field-level scorer).
You run the demo's stages yourself, in order, and at three of them you write one small piece.

WHAT YOU EDIT (three places, each marked "TODO n of 3"; the guide in README.md gives the exact code for each)
  TODO 1  ask_claude, part 1   -> stages 1-3: build the request and make the Claude call
  TODO 2  ask_claude, part 2   -> stage 5: add the JSON schema (structured output)
  TODO 3  gate_checks          -> the gate: when may a new prompt replace the old one?

HOW TO RUN (in order)
  python lab.py --stage 0      the bar: an old regex extractor, scored with the same scorer (no Claude call)
  python lab.py --stage 1      v0 "Extract the invoice." and v1 (+ a role)
  python lab.py --stage 2      v2 explicit criteria, v3 an output-format contract
  python lab.py --stage 3      v4 few-shot examples, and the example leak
  python lab.py --stage 5      v5 vs v6 (JSON schema + XML), and the embedded-instruction trap
  python lab.py --stage gate   the regression gate on three edited prompts
  python check.py              pass/fail in plain words
Add --all-docs to use all 12 invoices instead of 6 (slower and dearer).
"""
import argparse

import evalkit as kit
import evolution_core as core
from claude_client import get_client

# ======================================================================================
# TODO 1 and TODO 2 - the Claude call that every stage uses.
# `request` is one prompt version already filled with one invoice. It is a dict with:
#   request["messages"]       the user turn (always there)
#   request["system"]         the system prompt (None for v0, which has none)
#   request["output_format"]  a JSON schema (None until v6, which has one)
# The return line is given: it sends the request. You build `kwargs`.
# ======================================================================================
def ask_claude(request, model, max_tokens):
    raise NotImplementedError("TODO 1: build the request")  # replace these lines in TODO 1
    # TODO 2 (stage 5): add the schema here
    return get_client().messages.create(**kwargs)


# ======================================================================================
# TODO 3 of 3 - the regression gate.
# `baseline` is the production prompt's run, `candidate` is the edited prompt's run.
# Each has .summary.accuracy (0 to 1) and .leaks (a list of copied example values).
# Return two (passed, message) pairs:
#   1. overall accuracy: the candidate may be at most MAX_OVERALL_DROP below the baseline
#   2. example leaks: the candidate may have at most MAX_LEAKS of them
# The gate also applies its own four checks (worst field, documents that got worse, parse rate, null handling).
# ======================================================================================
MAX_OVERALL_DROP = 1.0
MAX_LEAKS = 999


def gate_checks(baseline, candidate):
    return []  # replace these lines in TODO 3


# ======================================================================================
# PLUMBING - do not edit below this line
# ======================================================================================
core.configure(ask_claude=ask_claude, gate_checks=gate_checks)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["0", "1", "2", "3", "5", "gate"])
    parser.add_argument("--all-docs", action="store_true", help="use all 12 invoices")
    args = parser.parse_args()
    docs = kit.load_docs()
    if not args.all_docs:
        docs = [d for d in docs if d.doc_id in core.LAB_DOCS]
    print(f"models: balanced={core.MODEL_BALANCED}   invoices: {len(docs)} ({', '.join(d.doc_id for d in docs)})")
    if args.stage == "0":
        core.stage0(docs)
    elif args.stage == "1":
        core.stage1(docs, kit.load_versions())
    elif args.stage == "2":
        core.stage2(docs, kit.load_versions())
    elif args.stage == "3":
        core.stage3(docs, kit.load_versions())
    elif args.stage == "5":
        core.stage5(docs, kit.load_versions(include_ablations=True))
    else:
        core.stage_gate(docs)
    if core.CALLS:
        core.print_ledger()


if __name__ == "__main__":
    main()
