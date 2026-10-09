"""Demo 5H - Measuring context sizes, as plain Python. No SDK, no model, no network.

Sizes are ESTIMATES: one token is about four characters. That is enough to compare one design with another.
"""
CHARS_PER_TOKEN = 4


def chars_to_tokens(chars):
    """The estimated token count for a number of characters, rounded up."""
    return (chars + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


def tokens(text):
    """The estimated token count of a text."""
    return chars_to_tokens(len(text))


class Meter:
    """Counts the characters each tool has returned, so we can say what a subagent had to read."""

    def __init__(self):
        self.chars = {}

    def add(self, tool, text):
        """Record the text one tool returned."""
        self.chars[tool] = self.chars.get(tool, 0) + len(text)

    def take(self, tools):
        """Return the characters returned by these tools since the last take, and start counting again."""
        return sum(self.chars.pop(tool, 0) for tool in tools)


def comparison_lines(orchestrator, biggest_subagent, one_agent):
    """Three printed lines: the team's contexts against one agent that holds everything. Arguments are token counts."""
    return [f"    one agent holding all requests and all raw data  ~{one_agent:>5} tokens in ONE context",
            f"    the orchestrator (briefs and short results)      ~{orchestrator:>5} tokens",
            f"    the biggest subagent (its brief and its data)    ~{biggest_subagent:>5} tokens"]
