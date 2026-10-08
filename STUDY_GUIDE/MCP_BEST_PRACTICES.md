# MCP Best Practices: Designing Servers, Clients and Claude Together

Study guide for the CCA-F course. Read it after the Day 2 MCP demos (`DEMO_2_0_intro_to_mcp`, `DEMO_2_0_mcp_separate_server_and_client`, Demo 2D) and before Labs 2.4 and 2.6.

This guide has one idea running through it: **an MCP server is a product that Claude uses.** Claude is the user. It reads your tool names and descriptions, picks a tool, fills in the arguments, and reads what comes back. Good MCP design is mostly good design for that reader.

> **Note**: Parts of this guide come from public sources and the MCP specification, which changes between revisions. Check the revision date at modelcontextprotocol.io before you rely on a detail. Model names and prices change often, so this guide talks about model tiers and leaves prices to Anthropic's pricing page.

## In one minute

| Question | Short answer |
|---|---|
| What does MCP give you? | One standard way for any client (an app, an agent, an IDE) to use tools, data and prompts from any server. |
| What are the three things a server offers? | Tools (actions), resources (read-only data) and prompts (reusable templates). |
| Which transport do I choose? | stdio for a local server started by the client. Streamable HTTP for a remote or shared server. |
| What is the most common design mistake? | Wrapping every API endpoint as a tool. Design tools around tasks, not endpoints. |
| Where does Claude fit? | Claude is the model that chooses tools. The quality of names, descriptions and results decides how well it chooses. |

## Where the pieces sit

| Piece | Job | Example from the course |
|---|---|---|
| Host | The app the user works in. It owns the model call and the user's approval. | Your Python script, Claude Desktop, an IDE |
| Client | Lives inside the host. Keeps one connection to one server. | `ClientSession` in the Day 2 demos |
| Server | Exposes tools, resources and prompts. | `kitchen_server.py`, `crm_server.py` |
| Model | Reads the tool list and decides which tool to call. | Claude |

The host and the model never talk to your database or API directly. They go through the server. That single doorway is what makes MCP easy to secure and easy to audit.

## 1. Design tools for Claude

Claude chooses a tool from its name, description and input schema only. It cannot read your code. If those three are vague, Claude guesses.

| Practice | Do this | Avoid this |
|---|---|---|
| Name by task | `place_order`, `check_stock` | `post_v2_orders`, `do_action` |
| Describe the when | "Use this to find out whether an item is in stock before placing an order." | "Stock tool." |
| Keep the set small | 5 to 15 focused tools per server | One tool per API endpoint (50 or more) |
| Use clear, typed inputs | `item: str`, `quantity: int`, with a one-line description each | A single free-text `params` field |
| Use enums for fixed choices | `status: "open" or "closed"` | Free text that has to be parsed |
| Make each tool do one job | `check_stock` and `place_order` | One `kitchen` tool with a `mode` argument |
| Return what the next step needs | A short, readable result with the ids Claude must use next | The raw API response with 200 fields |
| Return text Claude can act on | "Pepperoni: 0 left. Alternatives: margherita (12), veggie (8)." | A bare `false` |

### Tool description checklist

A good description answers four questions in two or three sentences.

1. What does the tool do?
2. When should Claude use it, and when should it not?
3. What does each argument mean, with an example?
4. What does the result look like?

Example:

```python
@mcp.tool()
def check_stock(item: str) -> str:
    """Check how many portions of one menu item are left.
    Use this before place_order. Example item: "margherita".
    Returns a short sentence such as "margherita: 12 left"."""
```

> **Important**: Tool descriptions go into Claude's context on every request. Long descriptions cost tokens and money. Write what Claude needs and stop.

## 2. Tools, resources and prompts: choose the right one

| Use a... | When | Who decides to use it | Example |
|---|---|---|---|
| Tool | Claude should do something or look something up on demand | The model | `place_order`, `search_tickets` |
| Resource | You are offering data to read, by address | The application or user | `menu://today`, a file, a database row |
| Prompt | You want a reusable, parameterized starting point | The user | "Review this order" template |

A simple rule: if it changes something or needs arguments to compute, make it a tool. If it is stable content to read, make it a resource. If a person picks it from a menu, make it a prompt.

## 3. Choose the transport

| | stdio | Streamable HTTP |
|---|---|---|
| Where the server runs | On the same machine, started by the client as a child process | Anywhere reachable by URL |
| Who can connect | Only the client that started it | Any client allowed by your network and auth |
| Authentication | The operating system user is the boundary | Required. Use OAuth based authorization. |
| Good for | Local tools, developer machines, desktop apps | Shared, hosted or enterprise servers |
| Rule you must follow | Write logs to stderr. **stdout is the wire.** Anything else printed there corrupts the protocol. | Serve over HTTPS and keep the server stateless where you can |
| Course example | `kitchen_server.py` (intro demo) | `server_app/kitchen_server.py`, Demo 2D |

## 4. Make results friendly to a model

| Practice | Why it helps Claude |
|---|---|
| Return the useful part, not the whole record | Smaller results leave room in the context window and reduce noise. |
| Paginate or cap long lists and say so ("showing 10 of 240") | Claude can ask for more instead of drowning. |
| Use stable, human-readable ids | Claude copies ids into the next call. |
| Put the answer first and details after | Models weigh the start of a result most. |
| Mark results that are errors with `is_error` and a plain reason | Claude reads the reason and chooses the next step. In the course demos, tools return `CallToolResult` for this. |
| Keep output formats consistent across tools | Claude learns the shape once. |

## 5. Keep context cost under control

Every connected tool definition is sent to the model with every request, and input tokens are billed. A large set of servers can use tens of thousands of tokens before the user has typed a word.

| Technique | What it does |
|---|---|
| Connect only the servers a task needs | Fewer definitions, lower cost, better tool choice. |
| Enable only the tools a task needs | MCP clients and the Claude API's MCP connector let you allow or deny tools per server. |
| Defer rarely used tools | The Claude API tool search tool lets you mark tools with `defer_loading` so definitions load only when needed. Anthropic reported large token savings and better tool-selection accuracy on MCP evaluations. |
| Use prompt caching for the stable part | Tool definitions and the system prompt rarely change, so cache them. |
| Trim descriptions and results | Short and exact beats long and vague. |

## 6. Put Claude into the design

An MCP system has two parts that need design: the servers, and the model that drives them. Treat the model as a design decision.

### Choose the model tier for the job

| Tier | Fits | Typical MCP role |
|---|---|---|
| Smaller, faster tier (Haiku class) | High volume, simple routing, classification, quick lookups | Triage, picking among a few tools, summarizing results |
| Balanced tier (Sonnet class) | Most production agents | The main tool-using agent over a normal-size toolset |
| Most capable tier (Opus class) | Long, multi-step work and hard reasoning | A coordinator, planning, many tools, ambiguous tasks |

Start with the balanced tier. Move down if a task is simple and cost or speed matters. Move up if tool choice or planning is poor. Measure on your own cases, as in Demo 3A.

### Choose how the model uses the tools

| Decision | Options | Guidance |
|---|---|---|
| Who runs the loop | Your own loop (Anthropic SDK), the Tool Runner, the Claude Agent SDK, Managed Agents | Use the least powerful option that works. See `DAY_3/ANTHROPIC_SDK_VS_CLAUDE_AGENT_SDK.md`. |
| How MCP is attached | Your own MCP client, or the Claude API MCP connector for remote servers | The connector removes the client code for remote servers. Your own client gives you full control. |
| Forcing a tool | `tool_choice` set to auto, any, or one named tool | Use auto by default. Force a tool only when the step is fixed. |
| Limits | Maximum turns, maximum tokens, budget | Always set them. |
| System prompt | Role, tool-use rules, answer format | Say which tool to prefer for which job. Keep it short. |

### Split work across models

A common pattern is a capable model as coordinator and smaller models as specialists, each connected to only the servers it needs. This keeps costs down and gives each agent fewer tools, which improves tool choice. Demos 3B and 3G build this shape.

## 7. Operate it well

| Area | Practice |
|---|---|
| Versioning | Version your server and your tool names. Do not change a tool's meaning silently. |
| Testing | Test each tool alone first, then with Claude on realistic requests. Keep a small set of test prompts and the tools they should trigger. |
| Observability | Log each call with a request id, tool name, caller and duration. Never log secrets. |
| Idempotence | Make tools that change things safe to repeat, or accept an idempotency key. Models and networks repeat calls. |
| Timeouts | Set a timeout on every outside call a tool makes. |
| Documentation | Write a short README per server: what it offers, who may use it, how to run it. |
| Ownership | Give every server an owner, a version and a review date. |

## 8. Quick design checklist

Use this before you publish a server.

1. Each tool does one job and has a task-based name.
2. Each description says what, when, arguments and result.
3. The tool set is small, and rarely used tools can be deferred.
4. Inputs are typed, and fixed choices use enums.
5. Results are short, readable and put the answer first.
6. Tools that change data are safe to repeat.
7. Logs go to stderr on stdio and never contain secrets.
8. Remote servers require authentication (see the security guide).
9. The model tier, loop type and limits are chosen on purpose and written down.
10. You tested with Claude on real requests, not only with unit tests.

## More information

- Security design for MCP: `MCP_SECURITY_ARCHITECTURE.md` in this folder.
- Course demos: `DAY_2/LABS/DEMO_2_0_intro_to_mcp`, `DAY_2/LABS/DEMO_2_0_mcp_separate_server_and_client`, Labs 2.4 and 2.6.
- Official specification and guides: modelcontextprotocol.io.
- Claude API tool use and MCP connector: Anthropic's documentation at platform.claude.com.

Sources used for this guide:

- [Introducing advanced tool use on the Claude Developer Platform (Anthropic)](https://www.anthropic.com/engineering/advanced-tool-use)
- [Tool use with Claude, Claude Platform Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
- [Connect Claude Code to tools via MCP (Claude Code Docs)](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [Anthropic brings MCP tool search to Claude Code (Tessl)](https://tessl.io/blog/anthropic-brings-mcp-tool-search-to-claude-code)
