# MCP Security Architecture: Designing a Safe MCP System Around Claude

Study guide for the CCA-F course. Read it after Demo 2D (authentication and authorization) and `MCP_BEST_PRACTICES.md`.

The guide answers one question: **if Claude can call tools through MCP, how do you keep the system safe?** The answer is layers. No single control is enough, and a sentence in a prompt is not a control.

> **Note**: This guide combines the MCP specification's security guidance with widely shared industry practice. The specification has been revised several times (public sources mention revisions in June 2025, November 2025 and later). Check the current revision at modelcontextprotocol.io before you build. Names such as Client ID Metadata Documents or Dynamic Client Registration have changed status between revisions.

## In one minute

| Idea | Meaning |
|---|---|
| The model is not a trusted component | Claude can be steered by text it reads (a web page, a ticket, a tool description). Treat its requests like input from a user, and check them in code. |
| Enforce rules outside the prompt | Permissions, limits and approvals belong in the server, the gateway and the host. |
| Least privilege | Each server, token and agent gets only what its job needs. |
| One doorway | All access to data and actions goes through MCP servers you can log and control. |
| Prove who is calling | Remote servers authenticate every request, and tokens are meant for that server only. |

## 1. The threat map

Where can things go wrong in an MCP system? Each row has a first control to apply.

| Threat | What happens | First control |
|---|---|---|
| Prompt injection | Text the model reads (a document, web page, ticket, tool result) contains instructions, and the model follows them. | Least privilege, human approval for risky actions, output checks. |
| Tool poisoning | A tool's name or description hides instructions meant for the model. | Review and pin tool definitions. Approve by exact description. |
| Rug pull | A server you trusted changes its tools after you approved it. | Pin versions. Re-approve when definitions change. |
| Malicious or fake server | A server pretends to be a trusted one, or does harm when started. | Match servers by URL or signed package, not by name. Run in a sandbox. |
| Token passthrough | A server accepts a token that was not issued for it, or forwards the client's token to another API. | Validate the audience. Never forward tokens. |
| Confused deputy | A proxy server with its own client id is tricked into granting access to the wrong party. | Per-client consent, exact redirect matching, state checks. |
| Session hijacking | A stolen session id is replayed. | Do not use sessions for authentication. Bind them to the user. |
| SSRF | A tool that fetches URLs is steered to internal addresses or cloud metadata. | Egress allowlist and URL checks. |
| Over-broad scopes | One token can do everything, so any leak is a disaster. | Narrow scopes and short lifetimes. |
| Data exposure | Secrets or personal data reach the model, the logs or another tool. | Redact, mask and keep secrets out of the model context. |
| Runaway agent | A loop spends money or repeats an action. | Turn, token and budget limits. Idempotent tools. |

## 2. The architecture in layers

```
User
  |
Host application (approval prompts, policy, limits)
  |
Claude model (chooses tools; not trusted to enforce rules)
  |
MCP client  ---- audit log ----
  |
Gateway / proxy (authentication, allowlists, rate limits, filtering)
  |
MCP servers (validate every call, least privilege)
  |
Data and APIs (own permissions, row-level rules)
```

| Layer | Security job |
|---|---|
| Host | Show the user what will happen and ask before risky actions. Set turn, token and budget limits. Decide which servers load. |
| Model | Choose the tool. Receives only the data it needs. Never holds secrets. |
| Client | Connects only to approved servers. Records every call. |
| Gateway or proxy | One place for authentication, allowlists, rate limits and logging when many servers exist. |
| Server | Validates the token, checks the arguments, checks what this user may do, and returns only what is needed. |
| Data and APIs | Apply their own permissions. They are the last line of defense. |

> **Important**: Every layer checks, and none trusts the layer above it. A server must work safely even if the model is fooled.

## 3. Authentication and authorization

Authentication asks "who are you?" Authorization asks "what may you do?" They are different, and you need both.

### The standard flow for remote servers

The MCP specification builds on OAuth 2.1. In plain words:

| Step | What happens |
|---|---|
| 1 | The client calls the server with no token. The server replies **401** and points to its protected resource metadata (RFC 9728). |
| 2 | The client reads that metadata to find the authorization server. |
| 3 | The client sends the user to the authorization server to sign in and consent. It uses PKCE. |
| 4 | The client asks for a token for this one server, using the `resource` parameter (RFC 8707). |
| 5 | The client calls the server with the token. |
| 6 | The server checks the token's signature, expiry, **audience** (is it for me?) and scopes, and then runs the tool. |

The server plays the role of a resource server. It validates tokens and does not issue them. A separate authorization server, often your company's identity provider, signs users in and issues tokens.

### 401 versus 403

| Code | Meaning | Example |
|---|---|---|
| 401 | I do not know who you are, or your token is missing or invalid. | No token, expired token |
| 403 | I know who you are, and you may not do this. | A valid token that lacks the `orders:write` scope |

### Rules that prevent the classic mistakes

| Rule | Reason |
|---|---|
| Accept only tokens whose audience is this server | Stops token passthrough and reuse of a token meant for another service. |
| Never forward the client's token to another API | If the server needs a downstream API, use its own credentials or exchange the token for a new one scoped to that API. |
| Use narrow scopes, and ask for more only when needed | A leaked token then does limited harm. |
| Use short-lived access tokens and refresh tokens carefully | Limits the time a stolen token works. |
| Match redirect URIs exactly and check the `state` value | Stops redirect and confused-deputy attacks. |
| Do not use the session id as authentication | A session id is a label for a conversation. The token proves identity on every request. |
| Bind the session to the user | A stolen session id is then useless to someone else. |
| Use HTTPS for every remote server | Protects tokens in transit. |
| Keep secrets in a secret store | Never in code, prompts, tool results or config files in source control. |

For stdio servers on one machine, the operating system user is the boundary. Do not put OAuth on stdio. Pass credentials through the environment or a secret store, and keep them away from the model.

## 4. Securing the model's side

Claude reads text from many places, and some of it may be written by someone hostile. This is prompt injection. Training and system prompts help, but they do not remove the risk. Design so that a fooled model can do little harm.

| Defense | How it works |
|---|---|
| Least privilege tools | Give the agent read-only tools unless it must write. Connect only the servers the task needs. |
| Separate reading from acting | One agent reads untrusted content and has no powerful tools. Another acts, and receives only a short, checked summary. |
| Human approval for risky actions | Payments, deletions, outgoing messages and permission changes wait for a person. |
| Checks in code before a tool runs | A hook or server rule inspects the call (for example, the amount limit or the allowed recipient) and allows or denies it. In the Claude Agent SDK this is a `PreToolUse` hook. |
| Checks on results | Treat tool output as data, not instructions. Strip or flag suspicious content before it goes back to the model. |
| Pin and approve tool definitions | Approve a tool by name and exact description, so a changed description is reviewed again. |
| Limit what can leave | Restrict network access and outgoing channels so a fooled agent cannot send data out. |
| Keep secrets out of context | The model should never see an API key or a password, because anything in context can be repeated. |
| Redact personal data | Mask data the task does not need before results reach the model. |
| Set limits | Maximum turns, tokens and budget stop loops. |

### Choose the Claude model with security in mind

| Decision | Guidance |
|---|---|
| Model tier | A stronger model usually follows instructions and resists manipulation better and chooses tools more accurately, but no model is immune. Never depend on the model alone. |
| One powerful agent or several small ones | Several small agents with narrow tools limit the damage of one fooled agent. Use a capable model as coordinator and smaller models for narrow jobs. |
| System prompt | State the role, the tools to prefer and what to refuse. Treat it as guidance. The real rules live in code. |
| Where the loop runs | A manual loop gives you a check before every tool call. The Claude Agent SDK gives you hooks and permission lists. Choose the one that lets you enforce your rules. |
| Tool choice | Use `allowed_tools` or an equivalent list, so the agent cannot call a tool you did not intend. |
| Fixed workflows | If the path is known, use a workflow, not an agent. Fewer decisions for the model means fewer chances to be steered. |

## 5. Securing the server

| Control | What to do |
|---|---|
| Validate input | Check type, length, range and allowed values for every argument. Reject the rest. |
| Authorize per call | Check what **this user** may do with **this tool** on **this record**, every time. |
| Use parameterized queries | Never build SQL or shell commands by joining strings from the model. |
| Restrict file and network access | Allow only named folders. Allow only listed hosts. Block internal and metadata addresses. |
| Return the minimum | Return only the fields the task needs. |
| Rate limit | Limit calls per user and per tool. |
| Make writes safe to repeat | Accept an idempotency key for payments and similar actions. |
| Log safely | Record who, which tool, which arguments (redacted) and the outcome. Do not log secrets. |
| Run with a low-privilege account | A compromised server then reaches little. |
| Sandbox | Run local servers in a container or restricted environment. |

### URL-fetching tools (SSRF)

A tool that fetches a URL can be pointed at your internal network. Allow only `https` to named hosts, resolve and check the address before connecting, block private and link-local ranges (including the cloud metadata address), and limit redirects and response size.

## 6. Supply chain and governance

| Area | Practice |
|---|---|
| Server registry | Keep an approved list of servers with owner, version, purpose and review date. |
| Matching | Identify a server by its URL or a verified package, not by the label someone typed. |
| Pinning | Pin versions and review changes before upgrading. |
| Third-party servers | Read the code or the vendor's security statement first. Anthropic and others review listings, but a listing is not a security audit. |
| Project config | Do not trust server settings found in a downloaded repository. Review them. |
| Environments | Separate development, test and production servers and credentials. |
| Access reviews | Review who and what has access on a schedule. Remove unused servers and scopes. |
| Incident plan | Know how to revoke tokens, disable a server and review logs quickly. |

## 7. Monitoring and audit

| Record | Why |
|---|---|
| Who called which tool, with which arguments (redacted), when, and the result | Investigation and compliance. |
| Approvals and denials, including which hook or rule decided | Shows the controls work. |
| Model, version and prompt version used | Explains behaviour changes. |
| Cost, turns and tokens per task | Detects runaway use. |

Alert on unusual volume, new tools appearing on a server, calls to unusual hosts, and repeated denials.

## 8. Putting it together: a worked example

The scenario: a support agent can look up orders and issue refunds through an MCP server.

| Layer | Design decision |
|---|---|
| Model | Balanced tier for the agent. It sees order summaries only and never sees payment card data. |
| Tools | `lookup_order` (read-only) and `issue_refund`. The agent may call `lookup_order` freely. |
| Server | HTTPS, OAuth, audience check, scopes `orders:read` and `refunds:write`. Each user sees only their own region's orders. |
| Rule in code | `issue_refund` rejects any amount above the user's limit, and requires an idempotency key. |
| Approval | Refunds above a threshold wait for a human reviewer before the server accepts them. |
| Hook | A `PreToolUse` hook denies `issue_refund` unless the order was looked up in this session. |
| Limits | Ten turns and a small budget per conversation. |
| Audit | Every call is logged with the user, the tool, the redacted arguments and the decision. |

If the model is fooled by text in a customer's message, the server still refuses a refund above the limit, and a person still approves the large ones.

## 9. Design review checklist

1. Is every server on the approved list, with an owner and a pinned version?
2. Does each remote server require authentication, validate the audience and use narrow scopes?
3. Are tokens never passed through to other services?
4. Does each agent have only the servers and tools it needs?
5. Are risky actions behind a code check or a human approval, and not only a prompt?
6. Are secrets kept out of prompts, results, logs and source control?
7. Can a URL-fetching tool reach only allowed hosts?
8. Are turns, tokens and budget limited?
9. Is everything logged, and can you revoke access quickly?
10. Have you tested with hostile input, such as a document that tells the model to ignore its rules, and confirmed the controls hold?

## More information

- Design practices: `MCP_BEST_PRACTICES.md` in this folder.
- Course material: Demo 2D and Lab 2.4 (authentication and scopes), Demo 3D and Lab 3.4 (a code gate and human approval), Demo 3E and Lab 3.5 (agent limits and tool lists).
- Primary sources to read: the MCP specification pages on Authorization and Security Best Practices at modelcontextprotocol.io, and Anthropic's Claude Code security and API documentation.

Sources used for this guide (most are third-party summaries of the specification, so confirm details in the specification itself):

- [Model Context Protocol: Security Risks and Mitigations (SOC Prime)](https://socprime.com/blog/mcp-security-risks-and-mitigations/)
- [Understanding Model Context Protocol Security in 2026 (Wiz)](https://www.wiz.io/academy/ai-security/model-context-protocol-security)
- [MCP Threat Modeling: Understanding the 6 Critical Attack Vectors (Aembit)](https://aembit.io/blog/mcp-threat-modeling-attack-surface-security/)
- [Securing MCP: a defense-first architecture guide (Christian Schneider)](https://christian-schneider.net/blog/securing-mcp-defense-first-architecture/)
- [OAuth on MCP: The Comprehensive Implementation Guide (Permit.io)](https://www.permit.io/blog/oauth-on-mcp)
- [Diving Into the MCP Authorization Specification (Descope)](https://www.descope.com/blog/post/mcp-auth-spec)
- [How MCP Authorization Actually Works (MojoAuth)](https://mojoauth.com/blog/how-mcp-authorization-actually-works-oauth-2-1-resource-servers-and-resource-indicators)
- [What is MCP authorization? (WorkOS)](https://workos.com/blog/what-is-mcp-authorization)
- [Connect Claude Code to tools via MCP (Claude Code Docs)](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [Securing Claude Code MCP Connections for Engineering Teams (MCP Manager)](https://mcpmanager.ai/blog/claude-code-security/)
- [Anthropic Claude Code Security Best Practices (General Analysis)](https://generalanalysis.com/guides/anthropic-claude-code-security-best-practices)
