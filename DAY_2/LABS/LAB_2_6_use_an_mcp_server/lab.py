"""Lab 2.6 - Team notes: use an MCP server from your own agent, one stage at a time.

This lab continues Demo 2D (the MCP client that lists a server's tools and calls one, and "descriptions are advice, the client enforces").
In Lab 2.5 you wrote the tool schemas and the tool functions yourself. Here you are the MCP CLIENT: a notes server (notes_server.py,
given) describes two read-only tools, you hand those descriptions to Claude, and you forward Claude's requests to the server.

WHAT YOU EDIT (six places, each marked "TODO n of 6"; the guide in README.md gives the exact code for each)
  TODO 1  open_session        -> stage 1: connect to the server and shake hands
  TODO 2  mcp_tool_to_claude  -> stage 2: turn an MCP tool into the dict Claude expects
  TODO 3  result_to_text      -> stage 3: turn an MCP result into tool_result text plus an error flag
  TODO 4  answer (forwarding) -> stage 3: send Claude's request to the server with session.call_tool
  TODO 5  answer (guard)      -> stage 4: refuse a request for any tool that is not on your allow-list (deny by default)
  TODO 6  ALLOWED_TOOLS, offer -> stage 4: the allow-list, and hand Claude only the tools on it

HOW TO RUN (in order)
  python lab.py --stage 1      connect and look: no Claude
  python lab.py --stage 2      Claude sees the server's tools
  python lab.py --stage 3      the server answers
  python lab.py --stage 4      a newer server adds delete_note
  python check.py              pass/fail in plain words
"""
import argparse
import contextlib
import sys

import notes_core as core
from claude_client import MODEL_BALANCED, ask, text_of, tool_calls_of

MAX_TURNS = 6  # the same exit as the loop in Lab 2.5
SYSTEM = "You answer questions about the team's notes. Use the tools: search first, then read the note you need. Answer in one or two sentences."


# ======================================================================================
# TODO 1 of 6 - connect to the server (stage 1).
# open_session starts the server file as a child process, connects to it over stdio, and does the MCP handshake. It yields the session.
# The three MCP names come from the mcp package: StdioServerParameters, stdio_client and ClientSession.
# They are imported inside the function, so that check.py can run on a machine without the mcp package.
# ======================================================================================
@contextlib.asynccontextmanager
async def open_session(server_file):
    raise NotImplementedError("TODO 1: connect to the MCP server")  # replace these lines in TODO 1
    yield  # keeps this function a generator; leave it


# ======================================================================================
# TODO 2 of 6 - convert an MCP tool into a Claude tool (stage 2).
# `tool` is an MCP tool object from session.list_tools(). Claude wants a dict with three keys: name, description and input_schema.
# The tool object has attributes with the same three names. A missing description becomes an empty string.
# ======================================================================================
def mcp_tool_to_claude(tool):
    return {}  # replace these lines in TODO 2


# ======================================================================================
# TODO 3 of 6 - convert an MCP result into tool_result content (stage 3).
# `result` is what session.call_tool returns. result.content is a list of items; the ones with item.type == "text" have .text.
# Return (text, is_error): the texts joined with a newline ("(empty result)" if there is none) and the flag result.is_error.
# ======================================================================================
def result_to_text(result):
    return "", False  # replace these lines in TODO 3


# ======================================================================================
# The loop is the one from Lab 2.5. The tool now runs on the server.
# TODO 4 of 6 (stage 3): for each tool Claude asked for, forward it with session.call_tool, convert the result with
#   result_to_text, record the name in tools_used, and add a tool_result block with the SAME id as the tool_use.
#   If the call itself raises an exception, report the failure to Claude as an error tool_result instead of crashing.
# TODO 5 of 6 (stage 4): BEFORE forwarding, refuse a name that is not in ALLOWED_TOOLS: add an error tool_result and skip the call.
# ======================================================================================
async def answer(session, claude_tools, question, send=ask):
    """Ask Claude a question; forward its tool requests to the MCP server until it stops asking.
    Returns {"answer": text, "turns": n, "tools_used": [names]}. send is ask() by default; the stages swap in a recorder."""
    messages = [{"role": "user", "content": question}]
    tools_used = []
    for turn in range(1, MAX_TURNS + 1):
        response = send(messages, system=SYSTEM, tools=claude_tools, model=MODEL_BALANCED, max_tokens=2048)
        if response.stop_reason != "tool_use":
            return {"answer": text_of(response), "turns": turn, "tools_used": tools_used}
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in tool_calls_of(response):
            # TODO 5: the guard goes here  # replace this line in TODO 5
            pass  # replace these lines in TODO 4
        messages.append({"role": "user", "content": results})
    return {"answer": "", "turns": MAX_TURNS, "tools_used": tools_used, "gave_up": True}


# ======================================================================================
# TODO 6 of 6 - the allow-list (stage 4).
# A server can add tools after you wrote your client. ALLOWED_TOOLS is the set of tool names YOU approved: search_notes and get_note.
# offer keeps only the Claude tool dicts whose "name" is in ALLOWED_TOOLS.
# ======================================================================================
ALLOWED_TOOLS = set()  # replace this line in TODO 6


def offer(claude_tools):
    return claude_tools  # replace this line in TODO 6


# ======================================================================================
# PLUMBING - do not edit below this line
# ======================================================================================
core.configure(open_session=open_session, system=SYSTEM, mcp_tool_to_claude=mcp_tool_to_claude, result_to_text=result_to_text, answer=answer, offer=offer)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=["1", "2", "3", "4"])
    args = parser.parse_args()
    core.run_stage(int(args.stage))


if __name__ == "__main__":
    main()
