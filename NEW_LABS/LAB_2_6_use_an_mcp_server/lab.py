"""LAB 2.6 - Use an MCP server from an agent (you are the MCP CLIENT).

Run:   python lab.py        (needs an API key and `pip install mcp`; 3 short conversations, a few cents)
Check: python check.py      (Part A needs NO key and no MCP: it tests your functions with fakes)

Lab 2.4 built a server. Here you connect to one and let Claude use its tools.
What MCP changes: YOU no longer write the tool schemas or functions. The server describes its tools,
you pass those descriptions to Claude, and when Claude asks for a tool you forward the call to the server.

    start server (stdio) -> list_tools -> give Claude the definitions -> Claude asks -> session.call_tool -> tool_result -> Claude answers

Sections: 1 connect (given), 2 convert tool definitions (TODO 1), 3 convert results (TODO 2), 4 the loop (TODO 3).
"""
import asyncio
import json
import pathlib
import sys

from claude_client import MODEL_BALANCED, ask, text_of, tool_calls_of

# the MCP client pieces are imported inside main(), so check.py can test everything else without `mcp` installed
HERE = pathlib.Path(__file__).parent
MAX_TURNS = 6
SYSTEM = "You answer questions about the team's notes. Use the tools: search first, then read the note you need. Answer in one or two sentences."


# ---------------------------------------------------------------- 2. MCP tool definition -> Claude tool definition
def mcp_tool_to_claude(tool):
    """Claude wants {"name", "description", "input_schema"}. An MCP tool object carries the same three things."""
    # TODO 1: return that dict from the MCP tool object. name and description are attributes with those names.
    #   The JSON schema is `tool.input_schema` on SDK 2.x (older SDKs call it `tool.inputSchema`): try both.
    return {}


# ---------------------------------------------------------------- 3. MCP result -> tool_result content
def result_to_text(result):
    """Turn what session.call_tool returned into (text, is_error) for the tool_result block."""
    # TODO 2: join the .text of every item in result.content that has type "text". is_error comes from `result.is_error`
    #   (older SDKs: `result.isError`). If there is no text at all return ("(empty result)", is_error).
    return "", False


# ---------------------------------------------------------------- 4. the loop, with MCP doing the tool execution
async def answer(session, claude_tools, question, send=ask):
    """Same loop as Lab 2.5, but a tool call is forwarded to the MCP server: await session.call_tool(name, arguments)."""
    messages = [{"role": "user", "content": question}]
    tools_used = []
    for turn in range(1, MAX_TURNS + 1):
        response = send(messages, system=SYSTEM, tools=claude_tools, model=MODEL_BALANCED, max_tokens=2048)
        if response.stop_reason != "tool_use":
            return {"answer": text_of(response), "turns": turn, "tools_used": tools_used}
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in tool_calls_of(response):
            # TODO 3: result = await session.call_tool(block.name, dict(block.input)); then (text, is_error) = result_to_text(result);
            #   record block.name in tools_used and append a tool_result block (same tool_use_id, "is_error": True on errors).
            pass  # DEFECT: Claude's request is never forwarded to the server
        messages.append({"role": "user", "content": [{"type": "text", "text": "(no tool results)"}]})
    return {"answer": "", "turns": MAX_TURNS, "tools_used": tools_used, "gave_up": True}


QUESTIONS = [
    "Who is on call this week and what is the pager number?",
    "What is the limit above which an expense needs approval?",
    "What does the note with id N-9 say?",
]


# ---------------------------------------------------------------- 1. connect (given)
async def main():
    from mcp import ClientSession, StdioServerParameters, stdio_client

    server = StdioServerParameters(command=sys.executable, args=[str(HERE / "notes_server.py")])  # start the server as a child process
    async with stdio_client(server) as (read, write):  # its stdin/stdout are the MCP channel
        async with ClientSession(read, write) as session:
            await session.initialize()  # the MCP handshake
            listing = await session.list_tools()
            claude_tools = [mcp_tool_to_claude(t) for t in listing.tools]
            print(f"server offers {len(claude_tools)} tools: {[t['name'] for t in claude_tools]}")
            evidence = {"tool_names": [t["name"] for t in claude_tools], "runs": []}
            for question in QUESTIONS:
                result = await answer(session, claude_tools, question)
                print(f"\nQ: {question}\n  tools used: {result['tools_used']}  turns: {result['turns']}\n  A: {result['answer']}")
                evidence["runs"].append({"question": question, **result})
    path = HERE / "evidence" / "evidence.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print("\nsaved evidence/evidence.json - now run: python check.py")


if __name__ == "__main__":
    asyncio.run(main())
