# Lab 2.4 - Procurement MCP server with authentication

**Time:** 60 min | **No API key and no model needed** | **Exam:** D2 Tool Design and MCP

## Story
Procurement wants an MCP server so an AI assistant can look up suppliers and purchase orders and, for people allowed to, approve them. The starter works but has classic defects: it prints debug text to stdout (this breaks the stdio protocol), logs keys, compares keys with `==`, answers a bad key with a leaky body, enforces no approval rules, and serves HTTP with no authentication.

| Role | May do | Spend limit |
|---|---|---|
| analyst | read | cannot approve |
| approver | approve PENDING POs | $25,000 |
| director | approve PENDING POs | $250,000 |

Also: the PO's supplier must be `active`, and nobody approves their own request.

## Files
| File | Role |
|---|---|
| `security.py` | **You edit**: TODO 1 constant-time key check, 2 non-leaky 401, 3 log redaction, 6 authorization rules. Plain Python |
| `server.py` | **You edit**: TODO 4 `po://` resource, 5 `get_po` tool, 6 wire-up in `approve_po`, 7 wrap HTTP in auth. Delete the `print()` lines |
| `client.py` | Given MCP client: `python client.py --transport stdio --role approver` |
| `procurement_db.py`, `data/` | SQLite mock and seed data. Do not edit |
| `check.py` | Part A tests `security.py` directly. Part B starts your server and talks to it |

## Run
```
pip install -r requirements.txt
python check.py        # start here; Part A needs no MCP at all
```
Keys: `check.py` creates throw-away random keys, you never type one. To use `client.py` by hand, set `PROC_KEY_ANALYST`, `PROC_KEY_APPROVER`, `PROC_KEY_DIRECTOR` (16+ characters each) in your terminal first.

## Version note
Written for MCP Python SDK 2.3.0 (`from mcp.server.mcpserver import MCPServer`, not `FastMCP`; the HTTP client uses `httpx2`). If an import fails, check `pip show mcp`.

## Optional
Connect the finished server to Claude Code over HTTP (`claude mcp add --transport http procurement http://127.0.0.1:8765/mcp --header "Authorization: Bearer <approver key>"`) and ask it to approve PO-2001, then PO-2005.
