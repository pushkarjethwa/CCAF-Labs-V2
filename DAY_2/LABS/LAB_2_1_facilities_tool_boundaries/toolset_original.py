"""The LEGACY facilities toolset exactly as the platform team shipped it.

READ-ONLY reference: main.py scores this file as the 'before' baseline. Do not edit it -
copy ideas into toolset.py instead.

Eleven tools, eight overlapping purposes, descriptions written by whoever built each endpoint.
CAPABILITY_MAP says which real capability each tool provides (see DATA/capabilities.json);
the eval grades the capability the model reached, not the tool name, so you may rename,
merge and split tools freely as long as you keep the map honest.
"""


def _obj(props: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props, "required": required or [], "additionalProperties": False}


S = {"type": "string"}

LEGACY_TOOLS = [
    {"name": "room_lookup", "description": "Look up a room.",
     "input_schema": _obj({"room": S})},
    {"name": "space_search", "description": "Search spaces.",
     "input_schema": _obj({"query": S, "capacity": {"type": "integer"}, "date": S})},
    {"name": "find_room", "description": "Find a room.",
     "input_schema": _obj({"name_or_query": S})},
    {"name": "book_room", "description": "Book a room.",
     "input_schema": _obj({"room_id": S, "start": S, "end": S, "organizer": S})},
    {"name": "reserve_slot", "description": "Reserve a slot.",
     "input_schema": _obj({"room_id": S, "start": S, "end": S})},
    {"name": "ticket_create", "description": "Create a ticket.",
     "input_schema": _obj({"summary": S, "location": S, "severity": S})},
    {"name": "ticket_open", "description": "Open a ticket.",
     "input_schema": _obj({"building": S, "ticket_id": S})},
    {"name": "maintenance_log", "description": "Log maintenance.",
     "input_schema": _obj({"ticket_id": S, "note": S, "minutes": {"type": "integer"}})},
    {"name": "asset_lookup", "description": "Look up an asset.",
     "input_schema": _obj({"asset_tag": S})},
    {"name": "vendor_lookup", "description": "Look up a vendor.",
     "input_schema": _obj({"trade": S, "vendor_name": S})},
    {"name": "badge_grant", "description": "Grant a badge.",
     "input_schema": _obj({"person": S, "zones": {"type": "array", "items": S}, "start": S, "end": S})},
]

# tool name (or "tool:action" for tools with an `action` enum) -> capability id
LEGACY_MAP = {
    "room_lookup": "room.get",
    "space_search": "room.search",
    "find_room": "room.get",
    "book_room": "booking.create",
    "reserve_slot": "room.hold",
    "ticket_create": "ticket.create",
    "ticket_open": "ticket.list_open",
    "maintenance_log": "ticket.log",
    "asset_lookup": "asset.lookup",
    "vendor_lookup": "vendor.lookup",
    "badge_grant": "badge.grant",
}

CONTEXTS = ["workplace_booking", "maintenance_desk", "security_desk"]

ALL_CAPABILITIES = ["room.search", "room.get", "room.hold", "booking.create", "ticket.create",
                    "ticket.list_open", "ticket.log", "asset.lookup", "vendor.lookup", "badge.grant"]
