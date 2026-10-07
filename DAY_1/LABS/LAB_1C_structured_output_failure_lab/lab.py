"""Lab 1C - Larkspur invoices: a JSON schema guarantees the shape of a record, not the money in it.

This lab continues Demo 1C (same invoices, same recorded bad outputs, same five stages).
You run the demo's stages yourself, in order, and at four of them you write one small piece.

WHAT YOU EDIT (four places, each marked "TODO n of 4"; the guide in README.md gives the exact code for each)
  TODO 1  ask_extraction   -> every stage: the Claude call, with structured output (the JSON schema)
  TODO 2  arithmetic_issues -> stage 2: the business rule subtotal + tax = total
  TODO 3  grounding_issues  -> stage 4: every number must be printed in the document
  TODO 4  decide            -> stage 4: when to retry, when to stop, when to send to a human

HOW TO RUN (in order)
  python lab.py --stage 1      schema passes, business is wrong
  python lab.py --stage 2      the business rules (needs TODO 2)
  python lab.py --stage 3      one corrective retry: it can make things worse
  python lab.py --stage 4      grounding and a bounded retry loop (needs TODO 3 and TODO 4)
  python lab.py --stage 5      review queue, metrics, cheap-first cascade
  python check.py              pass/fail in plain words
Add --all-docs to use all 11 invoices instead of 8. Add --prompt naive to stage 3 to use a weaker retry prompt.
"""
import argparse

import failure_core as core
from claude_client import get_client

# ======================================================================================
# TODO 1 of 4 - the Claude call that every stage uses.
# `model` is a model name, `user` is the user message text (it already contains the invoice),
# `max_tokens` is the reply limit. Send core.SYSTEM as the system prompt, and ask for
# structured output with core.OUTPUT_FORMAT (the JSON schema for an invoice record).
# Return the response.
# ======================================================================================
def ask_extraction(model, user, max_tokens):
    raise NotImplementedError("TODO 1: call Claude with the system prompt and the schema")  # replace these lines in TODO 1


# ======================================================================================
# TODO 2 of 4 - the arithmetic rule.
# `rec` is one extracted record (a dict). subtotal + tax_amount must equal total, allowing
# core.TOLERANCE for rounding. Return a list: empty when it adds up, otherwise ONE issue made with
# core.issue("total", "semantic", "<what is wrong>"). Use core.D(...) to turn a value into a Decimal
# and core.money(...) to round to cents.
# ======================================================================================
def arithmetic_issues(rec):
    return []  # replace these lines in TODO 2


# ======================================================================================
# TODO 3 of 4 - grounding: every number in the record must be printed in the document.
# core.extract_numbers(source_text) gives the set of numbers printed in the document.
# core.numeric_fields(rec) gives (path, value) pairs for the numbers in the record.
# Return one core.issue(path, "grounding", "<message>") for every value that is NOT within
# core.TOL of some printed number. Return an empty list when all numbers are printed.
# ======================================================================================
def grounding_issues(rec, source_text):
    return []  # replace these lines in TODO 3


# ======================================================================================
# TODO 4 of 4 - the retry policy. Retrying is a decision, not a reflex.
# status       what happened: "ok", "refusal", "truncated" (stop_reason max_tokens) or "unparseable"
# issues       the problems found in an "ok" or "unparseable" answer (empty list = clean)
# attempt      the number of the attempt that just finished (1, 2, 3 ...)
# Return a pair (action, reason). The actions are core.ACCEPT, core.RETRY_CORRECT (re-ask with the failures
# listed), core.RETRY_LARGER (same request, bigger max_tokens) and core.REVIEW (give up: a human decides).
#   refusal                       -> REVIEW, never retried
#   truncated                     -> RETRY_LARGER while attempts are left and max_tokens < max_tokens_cap, else REVIEW
#   no issues                     -> ACCEPT
#   issues, attempts left         -> RETRY_CORRECT
#   issues, no attempts left      -> REVIEW
# ======================================================================================
def decide(status, issues, attempt, max_attempts, max_tokens, max_tokens_cap):
    return core.ACCEPT, "TODO 4 not written yet"  # replace these lines in TODO 4


# ======================================================================================
# PLUMBING - do not edit below this line
# ======================================================================================
core.configure(ask_extraction=ask_extraction, arithmetic_issues=arithmetic_issues, grounding_issues=grounding_issues, decide=decide)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["1", "2", "3", "4", "5"])
    parser.add_argument("--all-docs", action="store_true", help="use all 11 invoices")
    parser.add_argument("--prompt", choices=["careful", "naive"], default="careful", help="stage 3 only: the correction prompt")
    args = parser.parse_args()
    docs = core.load_docs(None if args.all_docs else core.LAB_DOCS)
    truth = core.load_truth()
    print(f"model: balanced={core.MODEL_BALANCED}   invoices: {len(docs)} ({', '.join(d['doc_id'] for d in docs)})")
    if args.stage == "3":
        core.stage3(docs, truth, naive=args.prompt == "naive")
    else:
        {"1": core.stage1, "2": core.stage2, "4": core.stage4, "5": core.stage5}[args.stage](docs, truth)
    if core.CALLS:
        core.print_ledger()


if __name__ == "__main__":
    main()
