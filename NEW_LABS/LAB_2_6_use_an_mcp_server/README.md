# Lab 2.6 - Use an MCP server from an agent (new)

**Time:** 45 min | **Needs API key** and `pip install mcp` for `lab.py`; `check.py` Part A needs neither | **Exam:** D2 MCP integration

## Story
Lab 2.4 built a server. Now you are the client. A small notes server (`notes_server.py`, given) offers two read-only tools. You connect to it, hand its tool definitions to Claude, and forward Claude's tool requests to the server. You write no tool schemas and no tool functions: the server provides them.

## What you do (edit `lab.py`)
- TODO 1: turn an MCP tool object into the dict Claude expects.
- TODO 2: turn an MCP tool result into `tool_result` text plus an error flag.
- TODO 3: in the loop, forward each of Claude's tool requests with `session.call_tool(...)`.

## Run
```
pip install -r requirements.txt
python check.py     # Part A: tests with fakes, no key and no MCP
python lab.py       # starts the server, asks 3 questions (the last asks for a note that does not exist)
python check.py
```

## Notes
`lab.py` starts the server itself as a child process over stdio. Written for MCP Python SDK 2.3.0 (`from mcp.server.mcpserver import MCPServer`). If an attribute name differs on your version, `pip show mcp` and check TODO 1 and 2 comments.
