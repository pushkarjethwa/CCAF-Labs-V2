"""REFERENCE SOLUTION toolset for Lab 2.1 (trainer copy).

Design decisions (see TRAINER_NOTES.md):
  1. Consolidate: four room tools -> `space(action=search|get|hold)`; three ticket tools ->
     `maintenance_ticket(action=create|list_open|log)`. Fewer, wider tools with an enum action.
  2. Keep `book_room` SEPARATE from `space`: it is the one binding, side-effecting room action
     (sends invites). Mixing it into a read-mostly tool hides the commit point from permissions/review.
  3. Prune find_room and room_lookup/reserve_slot/ticket_open/maintenance_log as standalone tools.
  4. Scope per desk so no context sees more than 4 tools.
"""
from toolset_original import CONTEXTS

S = {"type": "string"}


def _obj(props, required=None):
    return {"type": "object", "properties": props, "required": required or [], "additionalProperties": False}


TOOLS = [
    {"name": "space",
     "description": (
         "Read and hold meeting rooms and spaces. Use when someone wants to find rooms that are free for a time window "
         "and match criteria (capacity, whiteboard, floor), to read facts about one known room (seating capacity, AV "
         "equipment, accessibility, which floor it is on), or to pencil in a tentative hold on a known room. "
         "Do NOT use this tool to confirm a reservation or send invites (use book_room), to report broken equipment "
         "(use maintenance_ticket), or to look up tagged equipment such as chillers or projectors (use asset_lookup)."),
     "input_schema": _obj({
         "action": {"type": "string", "enum": ["search", "get", "hold"],
                    "description": ("search: find free, available rooms for a time window by minimum seats, whiteboard or floor, when no specific room is named; "
                                    "get: facts about one named room - seating capacity (how many people it holds), AV equipment, wheelchair accessibility, which floor; "
                                    "hold: tentative pencil-in hold on a named room that auto-releases, never confirmed")},
         "room": S, "start": S, "end": S, "min_capacity": {"type": "integer"}, "floor": S, "equipment": S}, ["action"])},
    {"name": "book_room",
     "description": (
         "Create a confirmed, binding reservation for a named room and slot and send calendar invites. Use when the "
         "user explicitly wants the booking locked in, confirmed or finalized with invites. "
         "Do NOT use this tool for tentative holds or pencil-ins (use space with action hold), for searching free "
         "rooms (use space with action search), or for room facts (use space with action get)."),
     "input_schema": _obj({"room_id": S, "start": S, "end": S, "organizer": S, "attendees": {"type": "array", "items": S}},
                          ["room_id", "start", "end"])},
    {"name": "maintenance_ticket",
     "description": (
         "Work with facility repair requests. Use when something is broken or faulty and needs a new repair request, "
         "when someone wants every unresolved or outstanding request for a building, or when a technician note, work "
         "performed or labour minutes must be added to an existing ticket id. "
         "Do NOT use this tool to look up warranty or service history of equipment (use asset_lookup), to find a "
         "contractor or callout number (use vendor_lookup), or to book rooms."),
     "input_schema": _obj({
         "action": {"type": "string", "enum": ["create", "list_open", "log"],
                    "description": ("create: open a new repair request for a fault with a location and severity; "
                                    "list_open: list unresolved outstanding requests for a building; "
                                    "log: append a technician note and labour minutes to an existing ticket id")},
         "summary": S, "location": S, "severity": S, "building": S, "ticket_id": S, "note": S, "minutes": {"type": "integer"}},
         ["action"])},
    {"name": "asset_lookup",
     "description": (
         "Look up one tagged piece of equipment by asset tag or unit name: warranty expiry, last service date, "
         "installed condition and install location. Use when the question is about the history or status of a chiller, "
         "projector or other tagged asset. "
         "Do NOT use this tool to report a fault (use maintenance_ticket), to find a vendor or contractor "
         "(use vendor_lookup), or for facts about a room (use space with action get)."),
     "input_schema": _obj({"asset_tag": S}, ["asset_tag"])},
    {"name": "vendor_lookup",
     "description": (
         "Look up approved vendors and contractors: trade, contact, emergency callout number, approval status and "
         "insurance certificate expiry. Use when someone needs to know who the approved contractor is for a trade, or "
         "whether a named company is approved and insured. "
         "Do NOT use this tool to give a contractor physical access (use badge_grant) or to log work performed "
         "(use maintenance_ticket)."),
     "input_schema": _obj({"trade": S, "vendor_name": S})},
    {"name": "badge_grant",
     "description": (
         "Grant physical building access to a person for named zones and a date range: new hires, employees changing "
         "floors, and visiting technicians or contractors needing a temporary pass. "
         "Use when someone must be able to enter a floor, lab or plant room. "
         "Do NOT use this tool to check whether a vendor is approved or insured (use vendor_lookup) or to read "
         "room facts (use space with action get)."),
     "input_schema": _obj({"person": S, "zones": {"type": "array", "items": S}, "start": S, "end": S}, ["person", "zones"])},
]

CAPABILITY_MAP = {
    "space:search": "room.search",
    "space:get": "room.get",
    "space:hold": "room.hold",
    "book_room": "booking.create",
    "maintenance_ticket:create": "ticket.create",
    "maintenance_ticket:list_open": "ticket.list_open",
    "maintenance_ticket:log": "ticket.log",
    "asset_lookup": "asset.lookup",
    "vendor_lookup": "vendor.lookup",
    "badge_grant": "badge.grant",
}

SCOPES = {
    "workplace_booking": ["space", "book_room"],
    "maintenance_desk": ["maintenance_ticket", "asset_lookup", "vendor_lookup", "space"],
    "security_desk": ["badge_grant", "vendor_lookup", "space"],
}
assert set(SCOPES) == set(CONTEXTS)
