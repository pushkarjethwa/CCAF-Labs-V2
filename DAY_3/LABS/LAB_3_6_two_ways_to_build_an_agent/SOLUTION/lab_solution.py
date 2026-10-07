"""Lab 3.6 - Build the same agent two ways with the Anthropic SDK (continues Demo 3F: same incident, goal, prompt and tools).

Demo 3F built one incident-triage agent four ways. The goal, prompt, tools and data never changed; only WHO RUNS THE LOOP changed.
You build the first two ways here, and compare them:

  Build 1  MANUAL LOOP   you write the loop around client.messages.create        (TODO 1)
  Build 2  TOOL RUNNER   the SDK runs the loop; you hand it Python functions     (TODO 2)

HOW TO RUN
  python check.py    pass/fail in plain words. Part A needs no key: it tests your code with a scripted stand-in for Claude.
  python lab.py      runs both builds for real (needs ANTHROPIC_API_KEY, no extra tools); then python check.py again
The shared goal, prompt and tools are in incident_kit.py. You do not need to read it.
"""
import hashlib
import json
import pathlib

from anthropic import beta_tool

import incident_kit as kit
from claude_client import get_client


# ======================================================================================
# TODO 1 of 2 - BUILD 1: THE MANUAL LOOP. Three small pieces, marked 1a, 1b and 1c.
# `messages` is the whole conversation so far. Each turn: ask Claude, keep its answer, run any tools it asked for, send the results back.
# ======================================================================================
def manual_loop(client):
    tools = kit.TOOLS
    messages = [{"role": "user", "content": kit.GOAL}]
    called, tokens_in, tokens_out = [], 0, 0
    for turn in range(1, kit.MAX_TURNS + 1):
        # 1a - ask Claude: model, max_tokens (4096, which also covers hidden thinking), the system prompt, the tools and the messages
        response = client.messages.create(
            model=kit.MODEL,
            max_tokens=4096,
            system=kit.SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )
        tokens_in += response.usage.input_tokens
        tokens_out += response.usage.output_tokens
        # 1b - keep Claude's turn in the conversation, tool_use blocks included
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":  # end_turn means Claude is finished
            return summary(response, "manual loop", called, turn, tokens_in, tokens_out)
        # 1c - answer EVERY tool request of this turn, all in ONE user message of tool_result blocks
        results = []
        for block in response.content:
            if block.type == "tool_use":
                called.append(block.name)
                text = kit.RUN_TOOL[block.name](block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": text})
        messages.append({"role": "user", "content": results})


# ======================================================================================
# TODO 2 of 2 - BUILD 2: THE TOOL RUNNER. Two small pieces.
# The runner calls your Python functions for you. It passes the model's arguments as keyword arguments.
# ======================================================================================
def as_runner_tool(tool):
    """Wrap one entry of kit.TOOLS for the runner with beta_tool(function, name=..., description=..., input_schema=...)."""
    def call(**kwargs):
        return kit.RUN_TOOL[tool["name"]](kwargs)
    return beta_tool(call, name=tool["name"], description=tool["description"], input_schema=tool["input_schema"])


def runner_loop(client):
    # Create the runner: client.beta.messages.tool_runner(...) takes model, max_tokens, system, tools, messages and max_iterations (the brake)
    runner = client.beta.messages.tool_runner(
        model=kit.MODEL,
        max_tokens=4096,
        system=kit.SYSTEM_PROMPT,
        tools=[as_runner_tool(tool) for tool in kit.TOOLS],
        messages=[{"role": "user", "content": kit.GOAL}],
        max_iterations=kit.MAX_TURNS,
    )
    called, turns = [], 0
    for message in runner:  # one item per model turn; the tools already ran between turns
        turns += 1
        called += [block.name for block in message.content if block.type == "tool_use"]
    final = runner.until_done()
    return summary(final, "tool runner", called, turns, final.usage.input_tokens, final.usage.output_tokens)


# ======================================================================================
# RUNNING BOTH BUILDS - do not edit below this line
# ======================================================================================
HERE = pathlib.Path(__file__).parent
RESULTS_FILE = HERE / "results" / "run.json"


def summary(response, build, called, turns, tokens_in, tokens_out):
    text = "".join(block.text for block in response.content if block.type == "text")
    return {"build": build, "stop_reason": response.stop_reason, "turns": turns, "tools_called": called, "final_text": text,
            "tokens_in": tokens_in, "tokens_out": tokens_out}


def source_fingerprint():
    return hashlib.sha256((HERE / "lab.py").read_bytes()).hexdigest()[:16]


def run_all(client=None):
    client = client or get_client()
    rows = []
    for build in (manual_loop, runner_loop):
        row = build(client)
        rows.append(row)
        print(f"{row['build']:<12} stop_reason={row['stop_reason']:<9} turns={row['turns']:<3} tools called={len(row['tools_called'])} "
              f"tokens in/out={row['tokens_in']}/{row['tokens_out']}")
    for row in rows:
        print(f"\n--- {row['build']} ---\n{row['final_text']}")
    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text(json.dumps({"fingerprint": source_fingerprint(), "rows": rows}, indent=1), encoding="utf-8")
    print("\nSaved to results/run.json. Now run: python check.py")


if __name__ == "__main__":
    run_all()
