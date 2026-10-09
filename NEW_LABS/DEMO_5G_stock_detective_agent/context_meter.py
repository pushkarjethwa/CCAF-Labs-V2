"""Demo 5G - Counts how much the tool results add to the context. Plain Python: no SDK, no model, no network.

The count is an estimate: about 4 characters per token. It is for watching the trend, not for billing.
"""
CHARS_PER_TOKEN = 4
WINDOW_TOKENS = 200_000  # assumed size of the model's context window. Verify on your model.


def estimate_tokens(text):
    """A rough token count for a text."""
    return len(text) // CHARS_PER_TOKEN


class ContextMeter:
    """Keeps the running total of tool-result tokens, and counts the compactions the SDK reports."""

    def __init__(self, window=WINDOW_TOKENS):
        self.window = window
        self.running = 0
        self.peak = 0  # the largest running total seen
        self.compactions = 0

    def add_result(self, text):
        """Add one tool result to the running total. Return (chars, tokens, running)."""
        tokens = estimate_tokens(text)
        self.running += tokens
        self.peak = max(self.peak, self.running)
        return len(text), tokens, self.running

    def result_line(self, text):
        """The screen line for one tool result."""
        chars, tokens, running = self.add_result(text)
        percent = 100 * running / self.window
        return f"result {chars:>6} chars  ~{tokens:>5} tokens  running {running:>6} of {self.window} ({percent:.1f} percent)"

    def compacted(self):
        """The SDK summarised the old turns. The earlier results no longer count, so the total starts again."""
        self.compactions += 1
        self.running = 0
        return "the SDK compacted the earlier turns here (compact_boundary). The running total starts again."
