"""notes_server_plus.py - the same notes server, one release later (GIVEN, do not edit). Stage 4 of lab.py starts it for you.

The team added an admin tool, delete_note, to the server. Your client did not ask for it, but a server can add tools at any time.
"""
import notes_server  # the two read-only tools of the first server

mcp = notes_server.mcp
NOTES = notes_server.NOTES


@mcp.tool()
def delete_note(note_id: str) -> str:
    """Delete one note by id (for example N-3). Admin only. This cannot be undone."""
    if note_id not in NOTES:
        raise ValueError(f"no note with id {note_id}")
    del NOTES[note_id]
    return f"deleted {note_id}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
