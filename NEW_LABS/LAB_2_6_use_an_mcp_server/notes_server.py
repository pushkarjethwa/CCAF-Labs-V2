"""notes_server.py - a tiny MCP server (GIVEN, do not edit). lab.py starts it for you as a child process.

It exposes two read-only tools over stdio. Compare with Lab 2.4, where you build a server yourself.
"""
import json

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("team-notes")

NOTES = {
    "N-1": {"title": "On-call rotation", "text": "On-call rotates every Monday 09:00. Primary is Priya this week, backup is Marcus. Pager number is 555-0142."},
    "N-2": {"title": "Expense policy", "text": "Expenses under 75 USD need no approval. Above that, submit a receipt to finance within 14 days."},
    "N-3": {"title": "Release checklist", "text": "Release freeze starts Thursday 15:00. Run the smoke suite, tag the build, post in the releases channel."},
}


@mcp.tool()
def search_notes(query: str) -> str:
    """Search team notes by keyword in the title or text. Returns a JSON list of {id, title}. Use first, then get_note for the full text."""
    hits = [{"id": nid, "title": n["title"]} for nid, n in NOTES.items() if query.lower() in (n["title"] + " " + n["text"]).lower()]
    return json.dumps(hits)


@mcp.tool()
def get_note(note_id: str) -> str:
    """Return the full text of one note by id (for example N-1). Errors if the id does not exist."""
    if note_id not in NOTES:
        raise ValueError(f"no note with id {note_id}")
    return NOTES[note_id]["text"]


if __name__ == "__main__":
    mcp.run(transport="stdio")
