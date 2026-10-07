"""Lab 1A - Larkspur Components: which Claude model should label 100,000 invoices?

This lab continues Demo 1A (same company, same 24 labelled invoices, same four risk labels, same three model tiers).
You run the demo's stages yourself, in order, and at three of them you write one small piece.

WHAT YOU EDIT (three places, each marked "TODO n of 3"; the guide in README.md gives the exact code for each)
  TODO 1  ask_plain            -> stage 1: one Claude call, plain-text answer
  TODO 2  ask_structured       -> stage 2: the same call, but the answer must match a JSON schema
  TODO 3  escalation_reasons   -> stage 4: the rule that sends a case from the cheap model to a stronger one

HOW TO RUN (in order)
  python lab.py --stage 0     the "before": data and the old rules engine (no Claude call)
  python lab.py --stage 1     one hard invoice, three models, plain text
  python lab.py --stage 2     the same invoice with a strict answer format, plus the errors the API gives for bad requests
  python lab.py --stage 3     the tournament: 8 invoices x 3 models (read-only, no code to write)
  python lab.py --stage 4     cheap-first routing and a recommendation for 100,000 invoices
  python check.py             pass/fail in plain words
Add --all-cases to stages 0, 3 and 4 to use all 24 invoices (slower and dearer).
"""
import argparse

import tournament_core as core
from claude_client import get_client
from tournament_core import OUTPUT_FORMAT, plain_system, structured_system


# ======================================================================================
# TODO 1 of 3 - STAGE 1: one Claude call.
# Send the invoice text (case.view) to `model`, with the plain-text instructions in plain_system(policy).
# Return the whole response. The demo prints what each model says.
# ======================================================================================
def ask_plain(case, model, policy):
    return get_client().messages.create(
        model=model,
        max_tokens=2000,
        system=plain_system(policy),
        messages=[{"role": "user", "content": case.view}],
    )


# ======================================================================================
# TODO 2 of 3 - STAGE 2: the same call, with an answer format.
# structured_system(policy) asks for label, reasons and confidence. OUTPUT_FORMAT is the JSON schema the API must follow.
# Pass it as output_config={"format": OUTPUT_FORMAT}. Return the whole response.
# ======================================================================================
def ask_structured(case, model, policy, max_tokens=4000):
    return get_client().messages.create(
        model=model,
        max_tokens=max_tokens,
        system=structured_system(policy),
        messages=[{"role": "user", "content": case.view}],
        output_config={"format": OUTPUT_FORMAT},
    )


# ======================================================================================
# TODO 3 of 3 - STAGE 4: when does the cheap model hand a case to a stronger one?
# `first` is the cheap model's result: first.verdict.usable (valid answer?) and first.verdict.confidence (0 to 1).
# Return a list of reasons. An empty list means "the cheap model's answer stands".
#   unusable_output  the answer was not valid
#   low_confidence   confidence below MIN_CONFIDENCE
#   high_value       the invoice amount is HIGH_VALUE_USD or more (the sign does not matter)
# ======================================================================================
MIN_CONFIDENCE = 0.75
HIGH_VALUE_USD = 10_000


def escalation_reasons(first, amount_usd):
    reasons = []
    if not first.verdict.usable:
        reasons.append("unusable_output")
    elif first.verdict.confidence < MIN_CONFIDENCE:
        reasons.append("low_confidence")
    if abs(amount_usd) >= HIGH_VALUE_USD:
        reasons.append("high_value")
    return reasons


# ======================================================================================
# PLUMBING - do not edit below this line
# ======================================================================================
core.configure(ask_plain=ask_plain, ask_structured=ask_structured, escalation_reasons=escalation_reasons,
               min_confidence=MIN_CONFIDENCE, high_value_usd=HIGH_VALUE_USD)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["0", "1", "2", "3", "4"])
    parser.add_argument("--case", default="inv_017", help="the invoice for stages 1 and 2")
    parser.add_argument("--all-cases", action="store_true", help="use all 24 invoices in stages 0, 3 and 4")
    args = parser.parse_args()
    limit = 24 if args.all_cases else None
    print(f"models: fast={core.MODEL_FAST} balanced={core.MODEL_BALANCED} premium={core.MODEL_PREMIUM}\n")
    if args.stage == "0":
        core.stage0(limit)
    elif args.stage == "1":
        core.stage1(args.case)
    elif args.stage == "2":
        core.stage2(args.case)
    elif args.stage == "3":
        core.stage3(limit)
    else:
        core.stage4(limit)
    if core.CALLS:
        core.print_ledger()


if __name__ == "__main__":
    main()
