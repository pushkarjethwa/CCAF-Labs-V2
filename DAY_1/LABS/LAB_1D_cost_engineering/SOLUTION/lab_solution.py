"""Lab 1D - Larkspur invoices: the same policy check, four times cheaper, without breaking it.

This lab continues Demo 1D (same 30 invoices, same 6,000-token procurement policy, same four stages).
You run the demo's stages yourself, in order, and at four of them you write one small piece.

WHAT YOU EDIT (four places, each marked "TODO n of 4"; the guide in README.md gives the exact code for each)
  TODO 1  ask_checker          -> every stage: the Claude call
  TODO 2  count_request_tokens -> stage 2: count the tokens before you send
  TODO 3  system_blocks        -> stage 3: where the cache breakpoint goes (prompt caching)
  TODO 4  batch_requests and join_by_custom_id -> stage 4: batch the work, and join the answers safely

HOW TO RUN (in order)
  python lab.py --stage 1      meter it: usage, cost, monthly projection
  python lab.py --stage 2      count before you send: the token gate (needs TODO 2)
  python lab.py --stage 3      cache the policy, break the cache without an error, find it, fix it (needs TODO 3)
  python lab.py --stage 4      batch the work and compare four strategies (needs TODO 4)
  python check.py              pass/fail in plain words
Add --all-docs to use all 30 invoices instead of 10 (slower and dearer).
"""
import argparse

import cost_core as core
from claude_client import get_client

# ======================================================================================
# TODO 1 of 4 - the Claude call that every stage uses.
# `request` is a dict that is already complete: request["model"], request["max_tokens"],
# request["system"] (a list of text blocks), request["messages"] and request["output_config"]
# (the JSON schema for the verdict). Send all five to the Messages API and return the response.
# ======================================================================================
def ask_checker(request):
    return get_client().messages.create(
        model=request["model"],
        max_tokens=request["max_tokens"],
        system=request["system"],
        messages=request["messages"],
        output_config=request["output_config"],
    )


# ======================================================================================
# TODO 2 of 4 - count the tokens of a request without running it.
# Call the token-counting endpoint with the request's model, system and messages (NOT max_tokens,
# which this endpoint does not accept), and return the number of input tokens it reports.
# ======================================================================================
def count_request_tokens(request):
    counted = get_client().messages.count_tokens(
        model=request["model"],
        system=request["system"],
        messages=request["messages"],
    )
    return counted.input_tokens


# ======================================================================================
# TODO 3 of 4 - the system prompt as a block, with an optional cache breakpoint.
# `text` is the instructions plus the policy. `cache` says whether to mark the block for caching.
# `ttl` is None (the default five-minute lifetime) or "1h".
# Return a list with ONE block: {"type": "text", "text": text}. When `cache` is true, add to the block
# "cache_control": {"type": "ephemeral"}, and add "ttl": ttl inside cache_control when ttl is given.
# ======================================================================================
def system_blocks(text, cache, ttl=None):
    block = {"type": "text", "text": text}
    if cache:
        block["cache_control"] = {"type": "ephemeral", **({"ttl": ttl} if ttl else {})}
    return [block]


# ======================================================================================
# TODO 4 of 4 - batching.
# batch_requests(invoice_ids, requests): return one dict per request, {"custom_id": <the invoice id>, "params": <the request>}.
# join_by_custom_id(entries): batch results arrive in ANY order. Return a dict that maps each result's
# custom_id (entry.custom_id) to the result entry itself.
# ======================================================================================
def batch_requests(invoice_ids, requests):
    return [{"custom_id": invoice_id, "params": request} for invoice_id, request in zip(invoice_ids, requests)]


def join_by_custom_id(entries):
    return {entry.custom_id: entry for entry in entries}


# ======================================================================================
# PLUMBING - do not edit below this line
# ======================================================================================
core.configure(ask_checker=ask_checker, system_blocks=system_blocks, count_request_tokens=count_request_tokens,
               batch_requests=batch_requests, join_by_custom_id=join_by_custom_id)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["1", "2", "3", "4"])
    parser.add_argument("--all-docs", action="store_true", help="use all 30 invoices")
    parser.add_argument("--collect", metavar="BATCH_ID", help="stage 4 only: collect a batch that had not finished")
    args = parser.parse_args()
    invoices = core.load_invoices()
    invoices = invoices if args.all_docs else core.lab_invoices(invoices)
    truth = core.load_truth()
    print(f"models: fast={core.MODEL_FAST} balanced={core.MODEL_BALANCED}   invoices: {len(invoices)}")
    if args.stage == "1":
        core.stage1(invoices, truth)
    elif args.stage == "2":
        core.stage2(invoices, truth)
    elif args.stage == "3":
        core.stage3(invoices, truth)
    else:
        core.stage4(invoices, truth, collect_id=args.collect)
    if core.CALLS:
        core.print_ledger()


if __name__ == "__main__":
    main()
