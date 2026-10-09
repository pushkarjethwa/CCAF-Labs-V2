"""Demo 5E - Measuring the context size, as plain Python. No SDK, no model, no network.

The Agent SDK's ResultMessage has a `usage` dict. Its field names are the Messages API names (verify on your SDK version).
"""
USAGE_KEYS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens")


def context_tokens(usage):
    """Tokens the session holds after a reply: all input tokens (new and cached) plus the reply itself.

    When one reply used tools, the SDK sums several model calls, so this can overshoot a little. That is fine for a warning.
    """
    usage = usage or {}
    return sum(usage.get(key) or 0 for key in USAGE_KEYS)


def is_full(tokens, limit):
    """True when the context has reached the limit."""
    return tokens >= limit
