"""Lab 2.1 - Facilities assistant: fix the tool boundaries, one stage at a time, and watch the score move.

This lab continues Demo 2A (same method: 16 prompts, tool_choice auto, a score after every change), on the campus facilities
assistant. The assistant has 11 overlapping tools with two-word descriptions ("Look up a room.", "Open a ticket.").

WHAT YOU EDIT (five places, each marked "TODO n of 5"; the guide in README.md gives the exact code for each)
  TODO 1  ask_with_tools  -> every stage: the Claude call with tools
  TODO 2  DESCRIPTIONS    -> stage 2: rewrite the descriptions
  TODO 3  CONSOLIDATED    -> stage 3: two consolidated tools with an `action` enum, and their capability map
  TODO 4  REMOVE          -> stage 4: remove the old duplicates
  TODO 5  SCOPES          -> stage 5: give each desk only its own tools

HOW TO RUN (in order)
  python lab.py --stage 1      the legacy 11 tools: the baseline
  python lab.py --stage 2      your descriptions
  python lab.py --stage 3      your consolidated tools (the old ones are still offered)
  python lab.py --stage 4      the old duplicates removed
  python lab.py --stage 5      scoped per desk
  python lab.py --stage gate   the gate: bar, lint, and a sprawl regression
  python check.py              pass/fail in plain words
Add --models balanced to use one model only (cheaper).
"""
import argparse

import facilities_core as core
from claude_client import get_client

S = core.S


# ======================================================================================
# TODO 1 of 5 - the Claude call with tools.
# `tools` is a list of tool definitions (name, description, input_schema), `prompt` is the user's request.
# Send core.SYSTEM as the system prompt and the prompt as the user message, offer the tools, and set
# tool_choice to {"type": "auto"} (the model decides; a forced choice would hide the confusion you are measuring).
# Return the response.
# ======================================================================================
def ask_with_tools(model, tools, prompt):
    raise NotImplementedError("TODO 1: call Claude with the tools")  # replace these lines in TODO 1


# ======================================================================================
# TODO 2 of 5 - rewrite the descriptions (stage 2).
# One new description for each of the 11 legacy tools: what it does, "Use when ...", and "Do NOT use ..." naming the sibling
# tool to use instead. Only the description changes; the names and parameters stay.
# ======================================================================================
DESCRIPTIONS = {}  # replace these lines in TODO 2


# ======================================================================================
# TODO 3 of 5 - consolidate (stage 3).
# CONSOLIDATED: two new tools made with core.tool(name, description, properties, required). Each has an `action` enum:
#   space              action = search | get | hold                (replaces room_lookup, space_search, find_room, reserve_slot)
#   maintenance_ticket action = create | list_open | log           (replaces ticket_create, ticket_open, maintenance_log)
# CONSOLIDATED_MAP: tool:action -> the capability it reaches, for the seven actions. The eval grades the capability.
# ======================================================================================
CONSOLIDATED = []  # replace these lines in TODO 3
CONSOLIDATED_MAP = {}


# ======================================================================================
# TODO 4 of 5 - remove the old duplicates (stage 4).
# The names of the legacy tools that the two consolidated tools replace. After this stage the toolset is
# space, maintenance_ticket, book_room, asset_lookup, vendor_lookup and badge_grant.
# ======================================================================================
REMOVE = []  # replace this line in TODO 4


# ======================================================================================
# TODO 5 of 5 - scope the tools per desk (stage 5).
# Each of the three task contexts sees only the tools it needs (at most 7; here 2 to 4). Keep `space` in the desks that
# also ask about rooms, or those prompts become impossible to answer.
# ======================================================================================
SCOPES = {}  # replace these lines in TODO 5


# ======================================================================================
# PLUMBING - do not edit below this line
# ======================================================================================
core.configure(ask_with_tools=ask_with_tools, descriptions=DESCRIPTIONS, consolidated=CONSOLIDATED,
               consolidated_map=CONSOLIDATED_MAP, remove=REMOVE, scopes=SCOPES)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["1", "2", "3", "4", "5", "gate"])
    parser.add_argument("--models", default="fast,balanced", help="comma list of fast, balanced")
    args = parser.parse_args()
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    print("models: " + ", ".join(f"{m}={core.MODELS[m]}" for m in models))
    if args.stage == "gate":
        core.stage_gate(models)
    else:
        core.run_stage(int(args.stage), models)
    if core.CALLS:
        core.print_ledger()


if __name__ == "__main__":
    main()
