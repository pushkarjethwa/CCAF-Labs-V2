"""Demo 5E - Chat with Pip (Brew & Bean) on the Claude Agent SDK.

    python pip_agent_sdk.py                                  you type, Pip answers, until you type /end
    python pip_agent_sdk.py --card C-1042 --tier gold        skip the two questions at the start
    python pip_agent_sdk.py --limit real                     use the real context limit instead of the small demo limit
    python pip_agent_sdk.py --script data/sample_chat_gold.txt --card C-1042 --tier gold     read the messages from a file

In the chat:  /end  /memory  /compact  /help.   Ctrl+C and end-of-input also end the chat, and the memory is saved in every case.
Setup: pip install claude-agent-sdk==0.2.163 (it bundles the Claude Code CLI) and set ANTHROPIC_API_KEY.
Pip runs on CLAUDE_MODEL_FAST (claude-haiku-5-5). Add --model balanced for CLAUDE_MODEL_BALANCED (claude-sonnet-5-5).
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

import audit_log
import context_limit
import memory_store
import pip_tools
import tiers

try:
    import claude_agent_sdk as sdk
except ImportError:
    sdk = None

# -- Settings ---------------------------------------------------------------------------------------------

HERE = Path(__file__).parent
WORKSPACE = HERE / "workspace"  # holds CLAUDE.md, Pip's standing shop rules. It is the working folder of every session.
MEMORY_DIR = HERE / "results" / "memory"  # one file per customer card
AUDIT_LOG = HERE / "results" / "audit_log.jsonl"
MODELS = {"fast": os.getenv("CLAUDE_MODEL_FAST", "claude-haiku-5-5"), "balanced": os.getenv("CLAUDE_MODEL_BALANCED", "claude-sonnet-5-5")}
DEMO_LIMIT = 3000  # tokens. Small on purpose, so a few turns reach it.
MODEL_WINDOW = 200_000  # tokens. Assumed size of the model's context window. Verify on your model.
REAL_LIMIT_FRACTION = 0.8  # warn at 80 percent of the window, long before the model runs out
REAL_LIMIT = int(MODEL_WINDOW * REAL_LIMIT_FRACTION)
LIMITS = {"demo": DEMO_LIMIT, "real": REAL_LIMIT}
MAX_TURNS = 4  # model calls per message (a tool call needs a second one)
MAX_BUDGET_USD = 0.50  # per SDK session
PIP_PROMPT = ("You are Pip, the loyalty-card assistant for Brew & Bean, a small coffee shop. "
              "Answer questions about points, rewards and opening hours.\n" + pip_tools.opening_hours() +
              "\nUse your tools to answer. If a tool is refused, say so kindly and offer what you can help with.")
SUMMARY_REQUEST = ("Summarize this conversation for the next time this customer chats. At most six lines. "
                   "Keep every customer rule and every open request. Drop small talk. Reply with the summary only.")
FACTS_REQUEST = ('List what we must remember about this customer for good. Reply with JSON only, in this shape: '
                 '{"pinned_rules": ["..."], "facts": ["..."]}. pinned_rules are the customer\'s own rules and requests, '
                 'in their exact words (for example "never send marketing email", "allergic to nuts"). '
                 'facts are short durable facts (name, favourite drink). Include the ones already saved above.')
RECAP = [("SDK handles", "the conversation across turns, CLAUDE.md loading, prompt caching, sessions"),
         ("You still own", "customer memory files, the pinned-rule check, tier rules, the audit log, the token limit")]
HELP_TEXT = ("Commands:  /end  save the memory and finish    /memory  show what is saved for this customer\n"
             "           /compact  compact now    /help  this text")


# -- Small helpers ----------------------------------------------------------------------------------------

def need_live():
    """One guard: the SDK and an API key."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    if sdk is None or not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Pip needs `pip install claude-agent-sdk==0.2.163` (it bundles the Claude Code CLI) and ANTHROPIC_API_KEY.")


def print_table(rows):
    """Print rows of (left, right) as two aligned columns."""
    width = max(len(left) for left, _ in rows)
    for left, right in rows:
        print(f"    {left:<{width}}   {right}")


def make_reader(script_path):
    """Return read(prompt). It reads the keyboard, or the lines of a script file (and echoes them like a chat)."""
    if script_path is None:
        return input
    lines = iter([line.strip() for line in Path(script_path).read_text(encoding="utf-8").splitlines()
                  if line.strip() and not line.startswith("#")])

    def read(prompt):
        line = next(lines, None)
        if line is None:
            raise EOFError
        print(prompt + line)
        return line
    return read


def ask_with_default(read, question, default):
    """Ask one question at the start. An empty answer means the default."""
    return read(f"{question} [{default}]: ").strip() or default


def choose_login(args, read):
    """The card id and the tier, asked once. They stay fixed for the whole chat, like a real login."""
    print("Demo customers:\n  " + "\n  ".join(pip_tools.customer_lines()))
    first_card = next(iter(pip_tools.CUSTOMERS))
    card = args.card or (first_card if args.script else ask_with_default(read, "Card id", first_card))
    if card not in pip_tools.CUSTOMERS:
        sys.exit(f"Unknown card {card}. Use one of: {', '.join(pip_tools.CUSTOMERS)}")
    default_tier = pip_tools.CUSTOMERS[card]["tier"]
    tier = args.tier or (default_tier if args.script else ask_with_default(read, f"Tier ({'/'.join(tiers.TIERS)})", default_tier))
    if tier not in tiers.TIERS:
        sys.exit(f"Unknown tier {tier}. Use one of: {', '.join(tiers.TIERS)}")
    return card, tier


# -- Tools and the guardrail gate (the tier rules live in tiers.py) ------------------------------------------

def build_server(card_id):
    """The Pip tools for ONE customer. The card id is closed over, so the model has no way to choose another customer."""
    def text(content):
        return {"content": [{"type": "text", "text": content}]}

    @sdk.tool("read_menu", "Show the menu and prices.", {})
    async def read_menu(args):
        return text(pip_tools.read_menu())

    @sdk.tool("opening_hours", "Show the opening hours.", {})
    async def opening_hours(args):
        return text(pip_tools.opening_hours())

    @sdk.tool("get_points_balance", "Show this customer's points balance.", {})
    async def get_points_balance(args):
        return text(pip_tools.get_points_balance(card_id))

    @sdk.tool("redeem_points", "Redeem points for this customer.", {"points": int})
    async def redeem_points(args):
        return text(pip_tools.redeem_points(card_id, args["points"]))

    return sdk.create_sdk_mcp_server(pip_tools.SERVER, tools=[read_menu, opening_hours, get_points_balance, redeem_points])


def make_gate(tier, card_id):
    """The PreToolUse hook for ONE customer. It checks every tool call against the tier table and prints a note on a denial."""
    async def gate(input_data, tool_use_id, context):
        tool = input_data["tool_name"].removeprefix(pip_tools.PREFIX)
        allowed, reason = tiers.decide(tier, tool, input_data["tool_input"], pip_tools.balance_of(card_id))
        audit_log.write(AUDIT_LOG, tier, card_id, tool, input_data["tool_input"], allowed, reason)
        if not allowed:
            print(f"    [guardrail] {reason}")
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow" if allowed else "deny",
                                       "permissionDecisionReason": reason}}
    return gate


def build_options(tier, card_id, memory, model):
    """The options for one SDK session: the customer's tools, their gate, the shop rules and what we saved about them."""
    return sdk.ClaudeAgentOptions(
        model=model, system_prompt=PIP_PROMPT + memory_store.prompt_block(memory), cwd=str(WORKSPACE),
        setting_sources=["project"],  # the SDK reads workspace/CLAUDE.md and sends it with every request
        tools=[], mcp_servers={pip_tools.SERVER: build_server(card_id)},
        allowed_tools=[pip_tools.PREFIX + name for name in tiers.tools_for(tier)],
        disallowed_tools=["Bash", "Write", "Edit"],
        permission_mode="dontAsk",  # a tool that is not allowed is denied, never asked about. Verify on your SDK version.
        hooks={"PreToolUse": [sdk.HookMatcher(hooks=[make_gate(tier, card_id)])]},
        max_turns=MAX_TURNS, max_budget_usd=MAX_BUDGET_USD)


# -- The chat ---------------------------------------------------------------------------------------------

class PipChat:
    """One customer's chat: the fixed login, the saved memory, the token limit and the current SDK client."""

    def __init__(self, card_id, tier, limit, model, read):
        self.card_id, self.tier, self.limit, self.model, self.read = card_id, tier, limit, model, read
        saved = memory_store.load(MEMORY_DIR, card_id)  # only THIS card's file is ever loaded
        self.is_new = saved is None
        self.memory = saved or memory_store.blank(card_id)
        self.client = None
        self.tokens = 0
        self.unsaved_turns = 0  # customer messages since the memory was last saved

    def greet(self):
        """Say whether this customer is new or back, and show what we loaded."""
        if self.is_new:
            print(f"\nNew customer, starting a new session. (limit {self.limit} tokens, type /help for commands)\n")
        else:
            print(f"\nWelcome back! Here is what we saved for card {self.card_id}:\n{memory_store.describe(self.memory)}\n")
            print(f"Loaded into a brand-new session. (limit {self.limit} tokens, type /help for commands)\n")

    async def start_session(self):
        """Open a brand-new SDK session. Its system prompt carries the saved summary, rules and facts."""
        self.client = sdk.ClaudeSDKClient(options=build_options(self.tier, self.card_id, self.memory, self.model))
        await self.client.connect()

    async def send(self, text):
        """Send ONE message. The SDK holds the earlier turns, so we send only the new text. Return the ResultMessage."""
        await self.client.query(text)
        async for message in self.client.receive_response():
            if isinstance(message, sdk.ResultMessage):
                return message

    async def ask_text(self, request):
        """Ask Claude for text, in this session, and return it."""
        return (await self.send(request)).result or ""

    async def turn(self, text):
        """One chat turn: Pip replies, then we measure the context and ask about compaction when it is full."""
        result = await self.send(text)
        print(f"Pip: {result.result}\n")
        self.unsaved_turns += 1
        self.tokens = context_limit.context_tokens(result.usage)
        print(f"    [context] {self.tokens} of {self.limit} tokens")
        if context_limit.is_full(self.tokens, self.limit):
            await self.offer_compaction()

    async def offer_compaction(self):
        """Warn that the context is full and ask. On n we simply continue, and ask again after the next reply."""
        print(f"    WARNING: the context has reached the limit ({self.tokens} of {self.limit} tokens).")
        answer = self.read(f"Context is full ({self.tokens} of {self.limit} tokens). Compact it and save to memory? [y/n] ")
        if answer.strip().lower().startswith("y"):
            await self.compact()
        else:
            print("    OK, continuing with the long context. I will ask again after the next reply.\n")

    async def save_memory(self):
        """Summary, durable facts, merge, retention check, write. Return True when the file was written."""
        summary = await self.ask_text(SUMMARY_REQUEST)
        found = memory_store.parse_found(await self.ask_text(FACTS_REQUEST))
        merged = memory_store.merge(self.memory, summary, found, self.unsaved_turns)
        lost = memory_store.missing_rules(self.memory, merged)
        print(f"    Retention check, every old pinned rule is still present: {'PASS' if not lost else 'STOP, missing ' + str(lost)}")
        if lost:
            return False
        path = memory_store.save(MEMORY_DIR, merged)
        self.memory, self.unsaved_turns = merged, 0
        print(f"    Memory saved to results/memory/{path.name}")
        return True

    async def compact(self):
        """Save the memory, then replace the old session with a new, small one that starts from the saved memory."""
        if not self.unsaved_turns:
            print("    Nothing new to compact yet.\n")
            return
        before = self.tokens
        if not await self.save_memory():
            return
        await self.client.disconnect()
        await self.start_session()
        self.tokens = (await self.client.get_context_usage())["totalTokens"]  # verify on your SDK version
        print(f"    Compacted. Context: {before} tokens before, {self.tokens} after. A new session has started.\n")

    async def run_command(self, command):
        """Handle /memory, /compact and /help."""
        if command == "/memory":
            saved = memory_store.load(MEMORY_DIR, self.card_id)
            print(memory_store.describe(saved) if saved else "    Nothing saved yet for this card.")
        elif command == "/compact":
            await self.compact()
        elif command == "/help":
            print(HELP_TEXT)
            print_table(RECAP)
        else:
            print("    Unknown command. Type /help.")

    async def loop(self):
        """Read messages until /end. Ctrl+C and end-of-input also leave the loop cleanly."""
        try:
            while True:
                text = self.read("You: ").strip()
                if text == "/end":
                    break
                if text.startswith("/"):
                    await self.run_command(text)
                elif text:
                    await self.turn(text)
        except (EOFError, KeyboardInterrupt):
            print("\n    (input ended)")

    async def finish(self):
        """Save the memory (when there is something new), close the session and print the recap."""
        if self.unsaved_turns:
            print("\nSaving the memory...")
            await self.save_memory()
        await self.client.disconnect()
        print("\nChat ended. What the SDK did, and what stayed ours:")
        print_table(RECAP)


async def run_chat(card_id, tier, limit, model, read):
    """The whole chat. The memory is saved in every case, because finish() runs in a finally block."""
    chat = PipChat(card_id, tier, limit, model, read)
    chat.greet()
    await chat.start_session()
    try:
        await chat.loop()
    finally:
        await chat.finish()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--card", help="customer card id, for example C-1042")
    parser.add_argument("--tier", choices=list(tiers.TIERS), help="guest, member or gold (fixed for the whole chat)")
    parser.add_argument("--limit", choices=list(LIMITS), default="demo", help="demo: a small limit. real: 80 percent of the window")
    parser.add_argument("--script", help="a text file with one message per line, ending with /end")
    parser.add_argument("--model", choices=list(MODELS), default="fast")
    args = parser.parse_args()
    need_live()
    read = make_reader(args.script)
    card_id, tier = choose_login(args, read)
    asyncio.run(run_chat(card_id, tier, LIMITS[args.limit], MODELS[args.model], read))


if __name__ == "__main__":
    main()
