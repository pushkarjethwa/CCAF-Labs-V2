"""LAB 5.4 - Context management for a long run: keep what matters, shrink the rest.

Run:   python lab.py        (needs an API key; two runs of 10 turns plus a final question, roughly 30-50 cents)
Check: python check.py      (Part A needs NO key: it tests your functions on hand-made messages)

Story: an ops assistant reads 10 long incident reports in ONE conversation, one per turn. Every turn re-sends the whole
history, so input tokens (and cost, and latency) grow with every report. At the end you ask about reports 2 and 9.

You build the "compact old turns, keep the important line" step. Run it twice: without and with compaction, and compare.
Key idea: the model only knows what is in `messages`. Old bulky content must shrink, but the facts you will need later must survive.
"""
import json
import pathlib

from claude_client import MODEL_BALANCED, ask, text_of

HERE = pathlib.Path(__file__).parent
BUDGET_TOKENS = 5000  # compact when the estimated history is bigger than this
KEEP_LAST = 2  # the most recent messages are never touched
SYSTEM = "You are an ops assistant. For each incident report, reply with ONE short sentence. Remember the FINDING of every report."

CAUSES = ["a bad config push", "an expired TLS certificate", "a noisy neighbour VM", "DNS misrouting", "a memory leak in the worker",
          "a failed database failover", "an overloaded load balancer", "a stuck cron job", "a full disk on the cache node", "a faulty network card"]


# ---------------------------------------------------------------- the data (given)
def report(number):
    """A long report. Line 1 is the one line that matters later; the rest is bulky log noise."""
    cause = CAUSES[number - 1]
    noise = "\n".join(f"  [{number:02d}:{minute:02d}] worker-{minute % 7} handled request batch {minute * number} with retry budget {minute % 5} and no further alerts"
                      for minute in range(1, 61))
    return f"FINDING {number}: the latency spike in service-{number} was caused by {cause}.\n{noise}"


# ---------------------------------------------------------------- STEP 1 (you): measure the context
def message_text(message):
    """The text of one message (a string, or a list of blocks that may hold text)."""
    content = message["content"]
    if isinstance(content, str):
        return content
    return " ".join(block.get("text", "") for block in content if isinstance(block, dict))


def estimate_tokens(messages):
    """A cheap estimate with no API call: about 4 characters per token."""
    # TODO 1: return the sum over all messages of len(message_text(m)) // 4.
    return sum(len(message_text(m)) // 4 for m in messages)


# ---------------------------------------------------------------- STEP 2 (you): compact old turns
def compact(messages, keep_last=KEEP_LAST):
    """Return a NEW list where old, bulky USER messages are shrunk to their first line. Never change the input list."""
    # TODO 2: for every message EXCEPT the last `keep_last`:
    #   - assistant messages stay exactly as they are
    #   - a user message whose text is longer than 400 characters becomes {"role": "user", "content": "[compacted] " + its first line}
    #   - shorter messages stay as they are
    #   The last `keep_last` messages are copied unchanged.
    result = []
    cutoff = len(messages) - keep_last
    for index, message in enumerate(messages):
        text = message_text(message)
        if index < cutoff and message["role"] == "user" and len(text) > 400:
            result.append({"role": "user", "content": "[compacted] " + text.splitlines()[0]})
        else:
            result.append(dict(message))
    return result


# ---------------------------------------------------------------- STEP 3 (given): the long run
def run(use_compaction):
    """Feed the 10 reports one per turn, then ask about reports 2 and 9. Records real input tokens per call."""
    messages, per_call = [], []

    def send(user_text):
        nonlocal messages
        messages.append({"role": "user", "content": user_text})
        if use_compaction and estimate_tokens(messages) > BUDGET_TOKENS:
            messages = compact(messages)
        response = ask(messages, system=SYSTEM, model=MODEL_BALANCED, max_tokens=1024)
        messages.append({"role": "assistant", "content": text_of(response)})
        per_call.append(response.usage.input_tokens)
        return text_of(response)

    for number in range(1, 11):
        send(report(number))
    final = send("Using only this conversation: what caused the latency spike in report 2, and what caused it in report 9?")
    label = "with compaction" if use_compaction else "no compaction"
    print(f"\n[{label}] input tokens per call: {per_call}\n  peak {max(per_call)}, total {sum(per_call)}\n  final answer: {final[:200]}")
    return {"input_tokens_per_call": per_call, "peak": max(per_call), "total": sum(per_call), "final_answer": final}


def main():
    print(f"model: {MODEL_BALANCED}   budget: {BUDGET_TOKENS} estimated tokens")
    evidence = {"model": MODEL_BALANCED, "budget": BUDGET_TOKENS, "plain": run(False), "compacted": run(True)}
    saving = 1 - evidence["compacted"]["total"] / evidence["plain"]["total"]
    print(f"\ncompaction cut total input tokens by {saving:.0%}")
    path = HERE / "evidence" / "evidence.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print("saved evidence/evidence.json - now run: python check.py")


if __name__ == "__main__":
    main()
