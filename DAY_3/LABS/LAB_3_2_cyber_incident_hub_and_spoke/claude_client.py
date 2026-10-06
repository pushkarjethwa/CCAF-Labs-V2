"""claude_client.py - the ONLY file in this lab that talks to the Claude API.

Read this file first. It shows, in order:
  1. where your API key comes from
  2. where the SDK client is created
  3. where a message is sent to Claude  (client.messages.create)
  4. how to read the answer
"""
import os
import sys

import anthropic
from dotenv import load_dotenv  # reads KEY=value lines from a file named .env

load_dotenv()  # looks for .env in this folder or a parent; never overrides real environment variables

_client = None  # created on first use, so importing this file never fails just because the key is missing


def get_client():
    """1) THE API KEY and 2) THE CLIENT. Created once, on first use.

    The key comes from the ANTHROPIC_API_KEY environment variable (or your .env file).
    Never hard-code it and never print it.
    """
    global _client
    if _client is None:
        if not os.getenv("ANTHROPIC_API_KEY"):
            sys.exit(
                "ANTHROPIC_API_KEY is missing.\n"
                "Create a file named .env next to this script containing:\n"
                "    ANTHROPIC_API_KEY=sk-ant-...\n"
                "(or set it in your terminal), then run again."
            )
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY by itself
    return _client


# Model names. Override without editing code, for example:  set CLAUDE_MODEL_FAST=claude-sonnet-5-5
MODEL_FAST = os.getenv("CLAUDE_MODEL_FAST", "claude-haiku-4-5")  # cheap and quick
MODEL_BALANCED = os.getenv("CLAUDE_MODEL_BALANCED", "claude-sonnet-5-5")  # the default choice
MODEL_PREMIUM = os.getenv("CLAUDE_MODEL_PREMIUM", "claude-opus-5-5")  # hardest problems only


def ask(messages, system=None, tools=None, model=MODEL_BALANCED, max_tokens=2048, **extra):
    """3) THE MESSAGE CALL. Send a conversation to Claude and return the full response.

    messages   : list like [{"role": "user", "content": "Hello"}]
    system     : optional instruction string for the model
    tools      : optional list of tool definitions (dicts)
    max_tokens : REQUIRED by the API. On Sonnet/Opus 5.5 it also covers hidden thinking
                 tokens, so keep it generous (2048 or more).
    extra      : any other messages.create option, for example output_config=...
    Do not pass temperature, top_p or top_k: this SDK version does not accept them and
    Sonnet/Opus 5.5 reject them.
    """
    request = {"model": model, "max_tokens": max_tokens, "messages": messages, **extra}
    if system:  # only send optional parts when you really have them
        request["system"] = system
    if tools:
        request["tools"] = tools
    return get_client().messages.create(**request)


def text_of(response):
    """4) READ THE ANSWER. Join all text blocks of a response into one string."""
    return "".join(block.text for block in response.content if block.type == "text")


def tool_calls_of(response):
    """Return the tool_use blocks Claude asked for (empty list if none)."""
    return [block for block in response.content if block.type == "tool_use"]


def print_usage(response):
    """Show how many tokens one call used. Tokens are what you pay for."""
    usage = response.usage
    print(
        f"[usage] model={response.model} input={usage.input_tokens} "
        f"output={usage.output_tokens} stop_reason={response.stop_reason}"
    )


# Price in US dollars per 1 million tokens: (input, output). Check the pricing page before relying on these.
PRICE_PER_MTOK = {
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}


def cost_usd(response):
    """Estimate what one call cost. Cached input is cheaper to read (0.1x) and dearer to write (1.25x)."""
    price_in, price_out = PRICE_PER_MTOK.get(response.model, (0.0, 0.0))
    usage = response.usage
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    input_cost = usage.input_tokens * price_in + cache_write * price_in * 1.25 + cache_read * price_in * 0.10
    return (input_cost + usage.output_tokens * price_out) / 1_000_000


if __name__ == "__main__":  # quick self-test:  python claude_client.py
    reply = ask([{"role": "user", "content": "Say hello in five words."}])
    print(text_of(reply))
    print_usage(reply)
