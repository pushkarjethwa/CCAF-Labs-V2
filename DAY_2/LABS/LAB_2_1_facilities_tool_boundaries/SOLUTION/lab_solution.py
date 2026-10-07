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
    return get_client().messages.create(
        model=model,
        max_tokens=1024,
        system=core.SYSTEM,
        tools=tools,
        tool_choice={"type": "auto"},
        messages=[{"role": "user", "content": prompt}],
    )


# ======================================================================================
# TODO 2 of 5 - rewrite the descriptions (stage 2).
# One new description for each of the 11 legacy tools: what it does, "Use when ...", and "Do NOT use ..." naming the sibling
# tool to use instead. Only the description changes; the names and parameters stay.
# ======================================================================================
DESCRIPTIONS = {
    "room_lookup": "Read the facts of ONE named room: seating capacity, AV equipment, wheelchair accessibility and which floor it is on. Use when the request names a room such as Harbor 3 or Birch and asks about its facilities. Do NOT use to find rooms that are free (use space_search), to hold or book a room (use reserve_slot or book_room), or for tagged equipment (use asset_lookup).",
    "space_search": "Search for rooms that are free in a time window and match criteria such as minimum seats, whiteboard or floor. Use when no specific room is named and the user wants options to choose from. Do NOT use for facts about one named room (use room_lookup), or to hold or confirm a booking (use reserve_slot or book_room).",
    "find_room": "Resolve ONE room from a partial or misspelled name and return the matching room with its facts. Use when the name given is only approximate, for example 'the big harbor room'. Do NOT use when the exact room name is known (use room_lookup) or to search by time window or capacity (use space_search).",
    "book_room": "Create a confirmed, binding reservation for a named room and time slot, and send calendar invites. Use when the user explicitly wants the booking locked in, confirmed or finalized. Do NOT use for tentative holds or pencil-ins (use reserve_slot), for searching free rooms (use space_search), or for room facts (use room_lookup).",
    "reserve_slot": "Place a tentative hold of about 15 minutes on a named room and slot; it expires by itself and sends no invites. Use when the user wants to pencil a room in while they check with others. Do NOT use for a confirmed reservation (use book_room) or to search for rooms (use space_search).",
    "ticket_create": "Open a NEW repair request for a fault that has no ticket yet, with a summary, a location and a severity. Use when something is broken or faulty, for example a flickering projector. Do NOT use to list existing tickets (use ticket_open), to add a note to a ticket (use maintenance_log), or to look up equipment history (use asset_lookup).",
    "ticket_open": "List every unresolved (open) maintenance ticket for a building. Use when someone asks what is outstanding, unresolved or still open in a building. Do NOT use to create a new ticket (use ticket_create) or to add a note to an existing ticket id (use maintenance_log).",
    "maintenance_log": "Append a work note and labour minutes to an EXISTING ticket id. Use when a technician reports work performed on a ticket such as MT-2291. Do NOT use to open a new ticket (use ticket_create) or to list open tickets (use ticket_open).",
    "asset_lookup": "Look up ONE tagged piece of equipment by asset tag or unit name: warranty expiry, last service date, installed condition and install location. Use when the question is about the history or status of a chiller, projector or other tagged asset. Do NOT use to report a fault (use ticket_create), to find a contractor (use vendor_lookup), or for facts about a room (use room_lookup).",
    "vendor_lookup": "Look up approved vendors and contractors: trade, contact, emergency callout number, approval status and insurance certificate expiry. Use when someone needs to know who the approved contractor is for a trade, or whether a named company is approved and insured. Do NOT use to give a contractor building access (use badge_grant) or to log work (use maintenance_log).",
    "badge_grant": "Grant physical building access to a person for named zones and a date range: new hires, employees changing floors, and visiting technicians or contractors. Use when someone must be able to enter a floor, lab or plant room. Do NOT use to check whether a vendor is approved (use vendor_lookup) or to read room facts (use room_lookup).",
}


# ======================================================================================
# TODO 3 of 5 - consolidate (stage 3).
# CONSOLIDATED: two new tools made with core.tool(name, description, properties, required). Each has an `action` enum:
#   space              action = search | get | hold                (replaces room_lookup, space_search, find_room, reserve_slot)
#   maintenance_ticket action = create | list_open | log           (replaces ticket_create, ticket_open, maintenance_log)
# CONSOLIDATED_MAP: tool:action -> the capability it reaches, for the seven actions. The eval grades the capability.
# ======================================================================================
CONSOLIDATED = [
    core.tool(
        "space",
        "Read and hold meeting rooms and spaces. Use when someone wants to find rooms that are free for a time window and match criteria, to read facts about one known room (seating capacity, AV equipment, accessibility, which floor), or to pencil in a tentative hold on a known room. Do NOT use this tool to confirm a reservation or send invites (use book_room), to report broken equipment (use maintenance_ticket), or to look up tagged equipment (use asset_lookup).",
        {"action": {"type": "string", "enum": ["search", "get", "hold"],
                    "description": "search: find free rooms for a time window by minimum seats, whiteboard or floor, when no room is named; get: facts about one named room; hold: tentative auto-releasing hold on a named room, never confirmed"},
         "room": S, "start": S, "end": S, "min_capacity": {"type": "integer"}, "floor": S, "equipment": S},
        ["action"]),
    core.tool(
        "maintenance_ticket",
        "Work with facility repair requests. Use when something is broken and needs a new repair request, when someone wants every unresolved request for a building, or when a technician note or labour minutes must be added to an existing ticket id. Do NOT use this tool to look up warranty or service history of equipment (use asset_lookup), to find a contractor (use vendor_lookup), or to book rooms.",
        {"action": {"type": "string", "enum": ["create", "list_open", "log"],
                    "description": "create: open a new repair request for a fault; list_open: list unresolved requests for a building; log: append a technician note and labour minutes to an existing ticket id"},
         "summary": S, "location": S, "severity": S, "building": S, "ticket_id": S, "note": S, "minutes": {"type": "integer"}},
        ["action"]),
]
CONSOLIDATED_MAP = {
    "space:search": "room.search",
    "space:get": "room.get",
    "space:hold": "room.hold",
    "maintenance_ticket:create": "ticket.create",
    "maintenance_ticket:list_open": "ticket.list_open",
    "maintenance_ticket:log": "ticket.log",
}


# ======================================================================================
# TODO 4 of 5 - remove the old duplicates (stage 4).
# The names of the legacy tools that the two consolidated tools replace. After this stage the toolset is
# space, maintenance_ticket, book_room, asset_lookup, vendor_lookup and badge_grant.
# ======================================================================================
REMOVE = ["room_lookup", "space_search", "find_room", "reserve_slot", "ticket_create", "ticket_open", "maintenance_log"]


# ======================================================================================
# TODO 5 of 5 - scope the tools per desk (stage 5).
# Each of the three task contexts sees only the tools it needs (at most 7; here 2 to 4). Keep `space` in the desks that
# also ask about rooms, or those prompts become impossible to answer.
# ======================================================================================
SCOPES = {
    "workplace_booking": ["space", "book_room"],
    "maintenance_desk": ["maintenance_ticket", "asset_lookup", "vendor_lookup", "space"],
    "security_desk": ["badge_grant", "vendor_lookup", "space"],
}


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
