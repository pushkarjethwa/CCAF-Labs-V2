---
lab:
    title: 'Demo 5E: Chat with Pip on the Claude Agent SDK'
    module: 'Day 5 - Context, Memory and Reliability'
---

# Demo 5E: Chat with Pip on the Claude Agent SDK

Brew & Bean, a small coffee shop, has a loyalty card. Its assistant, Pip, runs on the Claude Agent SDK, and in this demo you talk to it. You type each message at a `You: ` prompt, Pip replies, and the chat goes on for as many turns as you like. It ends only when you type `/end`. The SDK keeps the conversation inside the chat and reads a `CLAUDE.md` file of standing shop rules. Your code keeps what the SDK does not: one memory file for each customer card, a token limit that asks before the context gets too long, a compaction that never drops a customer's rule, and tier rules that decide which tools each customer may use. The whole run takes about 20 minutes. There is no matching lab yet, so there is nothing to write: chat with Pip and read the output. Everything works the first time, so this is a tour, not a test.

**Where it fits**: Follow it after Demo 5.0 (it reuses Pip). The recommended order is 5.0, 5D, 5E, 5A, 5B, 5C.

## The idea

**The idea**: The SDK keeps the conversation and the shop rules. You keep the customer memory, the token limit, the tier rules and the log.

## What you see

1. **A user-driven chat**: `python pip_agent_sdk.py` opens a chat. The card id and the tier are asked once, like a login. Commands: `/end`, `/memory`, `/compact`, `/help`.
2. **One memory file per customer card**: `results/memory/<card_id>.json` holds a summary, the pinned rules in the customer's exact words, a short list of facts, the time of the last session and a message count. Only that card's file is loaded, into the system prompt of a brand-new SDK session.
3. **A token limit**: After every reply the code measures the context size from the SDK result. At the limit, Pip warns and asks `Compact it and save to memory? [y/n]`.
4. **Compaction you control**: Claude writes a summary of at most six lines and a small JSON of facts and rules. Your code merges them with the old file, so no pinned rule is lost, and prints a retention check. Then a new SDK session starts from the saved memory, with a small context.
5. **Tier guardrails**: Guest, member and gold get different tools from `data/tiers.json`. The tools are built for one card, a hook checks every call, and a denial shows as `[guardrail] ...` in the chat.

## Files in this folder

- **pip_agent_sdk.py**: The chat, about 260 lines. Read it top to bottom. It is the only file that uses the SDK.
- **memory_store.py**: Load, save and merge the memory file, and the retention check. No SDK.
- **tiers.py**: The tier rules as plain Python. No SDK.
- **pip_tools.py**: What each Pip tool does. No SDK.
- **audit_log.py**: One masked JSON line per tool decision. No SDK.
- **context_limit.py**: Turns the SDK `usage` fields into one token count, and checks the limit. No SDK.
- **data/menu.json**, **data/customers.json**: The menu and hours, and three demo customers: Maya (gold, C-1042), Ben (member, C-2001) and Sam (guest, C-3003).
- **data/tiers.json**: The tool list for each tier, and the limit of 100 points per visit. The single source for the options and the gate.
- **data/sample_chat_guest.txt**, **sample_chat_member.txt**, **sample_chat_gold.txt**: Author-written chats for `--script`. The gold one reaches the demo limit, answers `y` and ends.
- **data/sample_transcript.jsonl**: Left from the earlier version of this demo. The chat does not use it.
- **workspace/CLAUDE.md**: Pip's standing shop rules. The SDK reads it with `setting_sources=["project"]`.
- **results/**: Written by the demo: `memory/<card_id>.json` and `audit_log.jsonl`. It starts empty, with only a `.gitkeep`.
- **check_offline.py**: A key-free self-check against a scripted fake SDK.

## Prerequisites

- Python 3.10 or later: `python --version`.
- The Agent SDK: `pip install claude-agent-sdk==0.2.163`. It bundles the Claude Code CLI.
- `ANTHROPIC_API_KEY` set in your terminal, or in a **.env** file in this folder or a parent folder. The self-check needs neither.

## Commands you will meet

Every command has two reasons: what it does, and why we run it here.

| Command | What it does | Why we run it here |
|---|---|---|
| `python check_offline.py` | Runs the whole chat against a scripted fake SDK and prints PASS and FAIL lines | It shows the files and the code are intact before you go live, with no key. Run it first |
| `python pip_agent_sdk.py` | Opens the chat. It asks for a card id and a tier, then waits for your messages | It is the demo. You type, Pip answers, and nothing is fixed in advance |
| `python pip_agent_sdk.py --card C-1042 --tier gold` | The same, without the two questions | It saves time when you restart the chat |
| `python pip_agent_sdk.py --limit real` | Uses 80 percent of the model window as the limit instead of 3000 tokens | It shows the limit you would use in a real product. A short chat never reaches it |
| `python pip_agent_sdk.py --script data/sample_chat_gold.txt --card C-1042 --tier gold` | Plays the messages in the file as if you typed them | It is the same chat without typing. The runner uses it |
| `--model balanced` (add to a command) | Runs Pip on `claude-sonnet-5-5` instead of `claude-haiku-5-5` | The fast model is enough for Pip. The main model shows the lessons do not depend on the model |
| `/end` (in the chat) | Saves the memory and ends the chat | It is the only way to finish on purpose. Ctrl+C and end-of-input also save |
| `/memory` (in the chat) | Shows what is saved for this customer card | It lets you see the memory without opening the file |
| `/compact` (in the chat) | Compacts now, without waiting for the limit | It shows the compaction at a time you choose |
| `/help` (in the chat) | Lists the commands and the table of what the SDK handles and what you own | It is the one-page recap |
| `type results\memory\C-1042.json` | Prints the memory file (on macOS or Linux: `cat results/memory/C-1042.json`) | It shows the memory is a small, readable file that you own |

## What to type

The model words its replies differently every time, so read what you get. These messages follow the demo. Type them one at a time.

**Guest** (card `C-3003`, tier `guest`):

1. `Hi, I'm Sam. What is on the menu?` Pip answers from the menu tool.
2. `How many points do I have?` The line `[guardrail] guest cannot use get_points_balance` appears, and Pip declines kindly.
3. `Please redeem 50 points for me.` The line `[guardrail] guest cannot use redeem_points` appears.
4. `Please never send me marketing email. I am allergic to nuts.`
5. `/end`. The memory is saved to `results/memory/C-3003.json`.

**Member** (card `C-2001`, tier `member`): `How many points do I have?` works (40). `Please redeem 20 points.` is refused.

**Gold** (card `C-1042`, tier `gold`):

1. `Hi, I'm Maya. When do you open on Saturday?`
2. `Please never send me marketing email. I am allergic to nuts.`
3. `How many points do I have?` Pip says 120.
4. `Please redeem 80 points for me.` It works. The demo changes no balance.
5. `Please redeem 150 points for me.` The guardrail refuses: the limit is 100 per visit.

**Reaching the limit**: keep chatting until the line `[context] N of 3000 tokens` shows N at or above 3000. Long questions get there faster, for example `Tell me about every item on the menu, and what goes well with coffee.` Pip then warns and asks `Compact it and save to memory? [y/n]`. Type `y`. Look at the token counts before and after, and at the retention check. Then ask `What are my rules?`. Pip still knows them, from the new session's system prompt. Type `/end`.

**A second run**: start again with `--card C-1042 --tier gold`. The start screen says `Welcome back` and lists the summary, rules and facts. Ask `Can you send me your newsletter?` and watch Pip refuse. Typing `n` at the question instead of `y` continues the chat with the long context, and the question comes again after the next reply.

## What is saved where

| What | Where | Written when |
|---|---|---|
| Customer memory (one per card) | `results/memory/<card_id>.json`: `card_id`, `summary`, `pinned_rules`, `facts`, `last_session`, `turns_total` | At `y`, at `/compact` and at the end of the chat |
| Audit log | `results/audit_log.jsonl`: one line per tool decision, with the card id masked | At every tool call |
| Shop rules | `workspace/CLAUDE.md`: read by the SDK, never written | You edit it |

The summary is replaced at every save. The pinned rules and facts are old plus new, so a rule the customer stated once is never lost. Pinned rules are never trimmed, and facts keep the newest 12.

## How the token limit works

`DEMO_LIMIT` (3000 tokens) and `REAL_LIMIT` (80 percent of an assumed 200,000-token window) are constants at the top of **pip_agent_sdk.py**. `--limit demo` is the default. After every reply, `context_limit.context_tokens()` adds `input_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens` and `output_tokens` from the `usage` of the SDK result. When the sum reaches the limit, Pip asks. After a compaction, the count for the new session comes from `client.get_context_usage()["totalTokens"]`.

## What was checked, and what was not

**Checked offline** (`python check_offline.py`, with a scripted fake SDK): that the chat ends only on `/end`, and that Ctrl+C and end-of-input save the memory; a first run, a second run with `Welcome back` and the memory in the system prompt of a new session; that card A never loads card B's file; the limit question, `y` (new session, token count drops, old pinned rules survive a summary that omits them, retention check, file written) and `n`; the six-line summary clip and the JSON validation; guest, member and gold tool rules and the argument checks; the card id fixed inside each tool; the audit log; the single source `tiers.json`; and `--script`. The replies, summaries and token counts in the fake are author-written. They are not model results.

**Checked against the SDK source** (version 0.2.163, downloaded and read): the names `ClaudeAgentOptions`, `ClaudeSDKClient` (`connect`, `disconnect`, `query`, `receive_response`, `get_context_usage`), `HookMatcher`, `ResultMessage` (with a `usage` dict), `create_sdk_mcp_server`, the options used here, and the `dontAsk` permission mode.

**Not checked**: Nothing in this demo has been run live. Check on your SDK version:

- The key names inside `ResultMessage.usage`. The code assumes the Messages API names (`input_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, `output_tokens`).
- That `get_context_usage()` works on a client that has just connected and has sent no message.
- That the baseline context (system prompt, `CLAUDE.md` and four tool definitions) stays well under `DEMO_LIMIT`. If it does not, raise `DEMO_LIMIT`.
- That `permission_mode="dontAsk"` denies a tool that is not allowed, and that the `PreToolUse` gate fires first.
- That `CLAUDE.md` is found when `cwd` is `workspace/`.
- That the model returns the JSON you ask for (the code ignores anything else), and that the summary and facts requests work inside the open session.
- That the line after the message that fills the context is the `y` in `sample_chat_gold.txt`. With a real model the turn that reaches the limit can differ.

## Design notes

- **Same Pip, different build.** The shop, the customers and the rules match Demo 5.0.
- **One memory per card.** The file name is the card id, and only the file of the card you log in with is opened.
- **The SDK keeps the conversation.** There is no messages list in the code. A new session is a new client, which is why a compaction needs the saved memory.
- **Compaction is yours here.** Code asks for the summary and the facts, merges, checks and starts a new session. A pinned rule can only grow, never shrink.
- **The tier table is the single source.** `data/tiers.json` feeds both `allowed_tools` and the gate.
- **The card id is not a tool argument.** Each customer gets their own tools with the card id fixed inside.
- **The demo changes no balance.** `redeem_points` only reports what would happen.

## More information

- Demo 5.0 shows the same ideas with the plain Messages API. Demo 5D puts guardrails across a whole agent stack.
- There is no matching lab yet.
