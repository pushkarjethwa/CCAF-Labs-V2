"""LAB 0.1 - Hello Claude: the Messages API from scratch.   Run:  python lab.py

You will make five small calls to Claude and learn what every part of a call does.
Read claude_client.py first: it shows the key, the client and the messages.create call.
Results are saved to evidence/evidence.json; then run  python check.py
"""
import json
import pathlib

import anthropic

from claude_client import MODEL_BALANCED, ask, cost_usd, print_usage, text_of

EVIDENCE_FILE = pathlib.Path(__file__).parent / "evidence" / "evidence.json"

SYSTEM = "You are a help-desk assistant. Answer in two short sentences."
TICKET = "My laptop will not connect to the office Wi-Fi since this morning. Other devices work fine."
FOLLOW_UP = "I already restarted it. What should I try next?"


def step1_single_call():
    """STEP 1 - one question, one answer."""
    print("\nSTEP 1: single call")
    # TODO 1: call ask() with one user message containing TICKET, and pass system=SYSTEM.
    raise NotImplementedError("TODO 1: call ask([...], system=SYSTEM) and keep the response")
    print("Claude:", text_of(response))
    print_usage(response)
    return response


def step2_second_turn(first_response):
    """STEP 2 - the API has no memory. YOU send the whole conversation every time."""
    print("\nSTEP 2: follow-up question")
    # TODO 2: build a messages list with 3 entries: the first user message (TICKET), Claude's first
    #         answer as an "assistant" message, then FOLLOW_UP as a new "user" message. Call ask().
    raise NotImplementedError("TODO 2: build the 3-message conversation and call ask()")
    print("Claude:", text_of(response))
    print_usage(response)
    return response


def step3_truncated_answer():
    """STEP 3 - max_tokens is a hard limit. Check stop_reason to know whether the answer was cut off."""
    print("\nSTEP 3: answer cut off by a tiny max_tokens")
    # TODO 3: call ask() with the TICKET but max_tokens=20 (Sonnet 5.5 may need more room to start answering;
    #         if you get an empty answer that is also fine). Then set was_cut_off = True when
    #         response.stop_reason == "max_tokens".
    raise NotImplementedError("TODO 3: call ask(..., max_tokens=20) and check stop_reason")
    print("Claude (cut off):", text_of(response))
    print_usage(response)
    print("was_cut_off =", was_cut_off)
    return response, was_cut_off


def step4_handle_error():
    """STEP 4 - a bad request raises an exception. Catch it and show a useful message."""
    print("\nSTEP 4: a deliberately wrong request")
    bad_messages = [{"role": "assistant", "content": "Hello, I speak first."}]  # the first message must be a user message
    # TODO 4: call ask(bad_messages) inside try/except anthropic.BadRequestError as error.
    #         On error, save str(error) in error_text. If no error happens, error_text stays "".
    raise NotImplementedError("TODO 4: wrap the call in try/except anthropic.BadRequestError")
    print("Error caught:", error_text[:200] or "(none)")
    return error_text


def step5_total_cost(responses):
    """STEP 5 - tokens cost money. Add up what this lab spent."""
    print("\nSTEP 5: cost")
    # TODO 5: total = sum of cost_usd(r) for every response in the list.
    raise NotImplementedError("TODO 5: sum cost_usd(response) over the responses")
    print(f"Total cost of this lab: ${total:.6f}")
    return total


def main():
    first = step1_single_call()
    second = step2_second_turn(first)
    truncated, was_cut_off = step3_truncated_answer()
    error_text = step4_handle_error()
    total = step5_total_cost([first, second, truncated])

    EVIDENCE_FILE.parent.mkdir(exist_ok=True)
    evidence = {
        "model": MODEL_BALANCED,
        "first_answer": text_of(first),
        "second_answer": text_of(second),
        "first_stop_reason": first.stop_reason,
        "truncated_stop_reason": truncated.stop_reason,
        "was_cut_off": was_cut_off,
        "error_text": error_text,
        "total_cost_usd": total,
    }
    EVIDENCE_FILE.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print("\nSaved", EVIDENCE_FILE.name, "- now run: python check.py")


if __name__ == "__main__":
    main()
