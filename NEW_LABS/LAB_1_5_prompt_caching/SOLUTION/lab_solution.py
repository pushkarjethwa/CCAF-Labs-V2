"""LAB 1.5 - Prompt caching: pay once for a long, repeated prefix, and learn what breaks the cache.

Run:   python lab.py        (needs an API key; 15 short calls, a few cents)
Check: python check.py

Story: a support bot answers many questions, each time with the same 7,000-word policy in the system prompt.
Without caching you pay for the whole policy on every call. With caching you pay full price once, then about 10%.

Cache rules to remember:
  * you mark a block with cache_control {"type": "ephemeral"}; everything BEFORE and INCLUDING that block is the cached prefix
  * the prefix must match EXACTLY, from the first character. Change anything early and the cache misses
  * there is a minimum prefix size (512 tokens on Sonnet, 4096 on Haiku); smaller prefixes are silently not cached
  * a cache WRITE costs 1.25x the input price, a cache READ costs 0.1x
"""
import json
import pathlib
from datetime import datetime

from claude_client import MODEL_BALANCED, ask, cost_usd, text_of

HERE = pathlib.Path(__file__).parent
# a unique first line per run, so a warm cache from an earlier run cannot hide your results
RUN_ID = datetime.now().strftime("%Y%m%d-%H%M%S")
POLICY = f"(policy build {RUN_ID})\n" + (HERE / "data" / "policy.md").read_text(encoding="utf-8")
QUESTIONS = json.loads((HERE / "data" / "questions.json").read_text(encoding="utf-8"))
INSTRUCTIONS = "You are a support assistant. Answer using only the policy below, in two sentences or fewer."


# ---------------------------------------------------------------- STEP 1 (given): no caching
def plain_system():
    """The whole system prompt as ONE plain string. Nothing is cached."""
    return f"{INSTRUCTIONS}\n\n{POLICY}"


# ---------------------------------------------------------------- STEP 2 (you): mark the policy as cacheable
def cached_system():
    """Return the system prompt as a LIST of blocks, with the policy block marked for caching."""
    # TODO 1: return [{"type": "text", "text": ..., "cache_control": {"type": "ephemeral"}}] holding INSTRUCTIONS + POLICY.
    #   Only the block that carries cache_control (and everything before it) is cached.
    return [{"type": "text", "text": f"{INSTRUCTIONS}\n\n{POLICY}", "cache_control": {"type": "ephemeral"}}]


# ---------------------------------------------------------------- STEP 3 (you): keep changing data OUT of the cached prefix
def system_with_time(now):
    """The bot must also know the current time. The time changes on every call, the policy does not."""
    # TODO 2: put the time in a SECOND block placed AFTER the cached policy block, with no cache_control of its own.
    #   The starter puts the time first, so the prefix differs on every call and nothing is ever reused.
    return cached_system() + [{"type": "text", "text": f"The current time is {now}."}]


# ---------------------------------------------------------------- runner (given)
def run_questions(label, make_system):
    """Ask every question with the system prompt that make_system() returns (called once per question)."""
    calls = []
    for question in QUESTIONS:
        response = ask([{"role": "user", "content": question}], system=make_system(), model=MODEL_BALANCED, max_tokens=2048)
        usage = response.usage
        calls.append({"input": usage.input_tokens, "output": usage.output_tokens,
                      "cache_write": getattr(usage, "cache_creation_input_tokens", 0) or 0,
                      "cache_read": getattr(usage, "cache_read_input_tokens", 0) or 0,
                      "cost_usd": cost_usd(response), "answer": text_of(response)[:120]})
    total = sum(c["cost_usd"] for c in calls)
    print(f"\n[{label}]  total ${total:.5f}")
    print(f"  {'call':<5}{'input':>8}{'cache_write':>13}{'cache_read':>12}{'cost $':>10}")
    for number, c in enumerate(calls, 1):
        print(f"  {number:<5}{c['input']:>8}{c['cache_write']:>13}{c['cache_read']:>12}{c['cost_usd']:>10.5f}")
    return {"calls": calls, "total_cost_usd": total}


def main():
    print(f"model: {MODEL_BALANCED}   policy: about {len(POLICY.split())} words, {len(QUESTIONS)} questions per run")
    evidence = {"model": MODEL_BALANCED,
                "uncached": run_questions("1. no caching", plain_system),
                "cached": run_questions("2. cached policy block", cached_system),
                "with_time": run_questions("3. with the current time added", lambda: system_with_time(datetime.now().strftime("%H:%M:%S")))}
    saving = 1 - evidence["cached"]["total_cost_usd"] / evidence["uncached"]["total_cost_usd"]
    print(f"\ncaching saved {saving:.0%} of the cost over {len(QUESTIONS)} questions")
    path = HERE / "evidence" / "evidence.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print("saved evidence/evidence.json - now run: python check.py")


if __name__ == "__main__":
    main()
