# Day 4 Quick Guide and Recap: Claude Code at Work

## What this day is about

You use Claude Code, an AI coding assistant that runs in your terminal, on small sample projects.
You learn to look first, teach it your rules, extend it, plug it into other tools, and run it in CI.
One idea runs through the day: put each need in the mechanism that fits, and check the critical ones with code.

The bookshop story from Demo 4.0 helps all day. A shop owner hires a new assistant.
The handbook is CLAUDE.md. The sticky note is a slash command. The binder is a skill.
The back-room colleague is a subagent. The door chime is a hook. The phone line is MCP.

## The day in plain English

**The big picture:** Claude Code is an AI helper that lives in your terminal and works on your project files. Think of hiring a new assistant for a shop. You show them around first, give them a handbook, teach them routines, introduce them to colleagues, and install a check at the door so mistakes are caught.

- **Explore, then plan.** Ask Claude to look before it changes anything. Plan Mode lets it propose a plan that you approve first. Like a builder who walks the site and shows you drawings before knocking a wall.
- **CLAUDE.md.** A file of standing rules that Claude reads at the start of every session. Like the staff handbook. Put project rules in it, and path rules in smaller rule files so they load only where they apply.
- **Slash command.** A saved prompt you run by name. Like a sticky note with a routine on it.
- **Skill.** A folder of instructions Claude loads when the task matches. Like a binder on the shelf that the assistant takes down when needed.
- **Subagent.** A helper with its own context and its own limited tools, such as a read-only reviewer. Like a colleague in the back room who reports back with a summary.
- **Hook.** A script that runs automatically at a set moment, such as before or after an edit. Like a door chime or a lock: it fires every time, whether or not Claude remembers the rule.
- **MCP in Claude Code.** Connects Claude to outside tools and data, such as a ticket system. Like giving the assistant a phone line.
- **CI review gate.** Claude reviews each pull request in your build pipeline, and a script decides pass or fail from its findings. Like a security guard who checks every delivery and follows a written rule.

Remember this: put each need in the right place. A wish goes in CLAUDE.md. A rule that must never break goes in a hook or the CI gate.

## Your day at a glance

You watch the demos run. You do the labs yourself. Each lab repeats the demo on a new repo, `shipcalc`.

| Session | What it is | Idea you practise |
|---|---|---|
| Demo 4.0 Intro to Claude Code | A 43-minute tour of a bookshop app (watch) | The whole toolbox: `@`, `!`, modes, CLAUDE.md, command, skill, subagent, hook |
| Demo 4A and Lab 4.1 | Explore, plan and refactor a repo | Look first, decide direct or plan, plan in Plan Mode, implement in small steps |
| Demo 4B and Lab 4.2 | Layer CLAUDE.md, rules and hooks | Files combine and do not rank, so write each fact once |
| Demo 4C and Lab 4.3 | A skill, a hook and a read-only subagent | The right tool for each need: procedure, guarantee, delegation |
| Demo 4D and Lab 4.4 | Claude Code as a CI review gate | The model finds, the code decides |

In every lab, work in the `STARTER` folder and run `python check.py` to see your progress. It needs no key.

## 1. Claude Code basics and Plan Mode

**In one line:** Claude Code is Claude plus tools in your folder. Explore first, plan risky changes, and review every diff.

**Analogy:** A new assistant spends day one reading the shop layout. She makes no change until she knows who uses what.

**Tiny example:**

```text
Before changing anything: find every place that reads a parcel's weight,
every caller, and every test for it. Do not edit files.
```

Press `Shift+Tab` to switch permission modes (what Claude may do without asking). Use `@file` to point at a file. Use `!command` to run a shell command yourself.

**Recap:**
- Plan Mode is a permission mode. Claude researches and proposes, and edits stay blocked until you approve.
- Plan when a change is wide, risky or unfamiliar. Go direct when you can describe the diff in one sentence.
- A good plan names files, callers, risks, order, how to verify, and how to roll back.
- Green tests only prove what the tests cover. Read the diff (`/diff`) and run the checks yourself.

## 2. CLAUDE.md, memory and rules

**In one line:** CLAUDE.md is the handbook Claude reads at the start of every session. It guides Claude. It cannot force it.

**Analogy:** The handbook is on the desk. A sticky note on one door only matters to whoever opens that door.

**Tiny example:** a rule file `.claude/rules/api.md` that loads only for matching files.

```markdown
---
paths:
  - "src/api/**/*.py"
---
- Every handler returns {"ok": bool, ...}.
```

**Recap:**
- Levels: managed (company), user (you), project (team, in git), local (you, this project), subdirectory (one folder).
- Files are combined, not ranked. If two disagree, Claude may pick either. Write each fact once.
- Keep files short (under about 200 lines) and concrete. `paths` is the only field a rule file reads.
- An `@` import tidies a file but does not save tokens. A path-scoped rule does.
- Run `/init` for a first draft. Never put secrets in these files.

## 3. Skills, hooks and subagents

**In one line:** A skill is a procedure, a hook is a guarantee, and a subagent is a helper with its own context.

**Analogy:** The binder holds recipe cards. The door chime rings every time, whatever anyone decides. The back-room colleague reads the long report and brings you one page.

**Tiny example:** a hook in `.claude/settings.json` that runs a guard script before every edit.

```json
{"hooks":{"PreToolUse":[{"matcher":"Edit|Write",
  "hooks":[{"type":"command","command":"python \"$CLAUDE_PROJECT_DIR/.claude/hooks/guard.py\""}]}]}}
```

The script exits with code 2 to block, and 0 to allow.

**Recap:**
- A skill is a folder with `SKILL.md`. Its description says when to use it. Claude reads that description to decide when to load it.
- Only exit code 2 blocks. Exit code 1 is a non-blocking error, and the action goes ahead.
- A subagent returns only a summary. List its `tools`, for example `Read, Grep, Glob`, so it cannot edit. If you leave `tools` out, it gets every tool.
- To check that Claude found your subagent, type `@` and the start of its name. (The `/agents` command is gone in newer versions. Check on your Claude Code version.)
- Custom commands have merged into skills. Old command files still work.

## 4. MCP and context in Claude Code

**In one line:** MCP plugs outside tools into Claude Code. Context is limited, so keep the session tidy.

**Analogy:** MCP is the phone line from the shop to the supplier. The context window is a desk with little space.

**Tiny example:** a project file `.mcp.json` that the whole team shares.

```json
{ "mcpServers": { "supplier": {
    "command": "python", "args": ["mcp_server/supplier_server.py"] } } }
```

Check your servers with `claude mcp list`, or `/mcp` inside a session.

**Recap:**
- Scopes: local (only you, this project), project (`.mcp.json`, shared), user (only you, every project).
- Claude Code asks you to approve a project server before using it. Keep tokens out of the file. Use `${VAR}`.
- Each server adds tool names and answers to context. Switch off servers you do not use.
- `/context` shows how full the window is. `/compact` shrinks a long chat. `/clear` starts fresh for an unrelated task.
- `claude --continue` resumes the latest session. `claude --resume` lets you pick one.
- Glob finds files by name. Grep finds text inside files. Pick the one that matches your clue.

## 5. Claude Code in CI as a review gate

**In one line:** Claude reviews every pull request, and plain code turns its findings into pass or fail.

**Analogy:** An airport scanner gives green or red for every bag. A chat with a guard gives you no fixed answer.

**Tiny example:** a headless review (no person at the keyboard) with answers in a fixed shape.

```text
claude --bare -p "$(cat .ci/review_prompt.md)" --output-format json \
  --json-schema "$(cat .ci/findings.schema.json)" --tools "" < pr.diff
```

**Recap:**
- `-p` runs Claude once, prints the answer and exits. `--json-schema` fixes the shape of the findings.
- The gate is plain code. It reads typed fields only. Any BLOCKER fails the build.
- Exit codes: 0 pass, 1 block, 2 invalid output, 3 no review. Fail closed: a missing review is never a pass.
- Least privilege: `--tools ""` removes all tools. `--allowedTools` only skips prompts, so it does not restrict. A cost cap and a timeout bound every run.
- Treat the diff as data. Add a plain-code scanner for secrets. Keep a human in charge of risky merges.

## Common mix-ups

- **Plan Mode is not a smarter model.** It changes what Claude may do, not how well it thinks.
- **A later CLAUDE.md does not win.** All files are read together, so contradictions get settled at random.
- **A rule in CLAUDE.md is advice, not a lock.** For "must never happen", use a hook, a permission rule or a test.
- **Exit 1 in a hook does not block.** Only exit 2 blocks. A crashing hook lets the action through.
- **`--allowedTools` is not a restriction.** Use `--tools` to remove tools.

## Day recap: remember these

1. Explore read-only first. Green tests only prove what they cover.
2. Plan wide or risky changes. Go direct for small, clear, reversible ones.
3. Permission modes decide what runs without asking. Start narrow.
4. CLAUDE.md guides Claude. Files combine, so write each fact once.
5. Path-scoped rules load only when matching files are touched.
6. A skill is a procedure. A hook is a guarantee. A subagent is delegation.
7. Limit a subagent's tools. The tool list is the real boundary.
8. MCP servers cost context. Use scopes, keep secrets in environment variables.
9. `/context`, `/compact` and `/clear` keep a long session healthy.
10. In CI, the model finds and the code decides. Fail closed.

## Quick self-check

1. What does Plan Mode change?
2. Two CLAUDE.md files disagree. Which one does Claude follow?
3. A rule must hold every time. What do you add besides the sentence?
4. What exit code makes a PreToolUse hook block?
5. Why does the CI gate read fields instead of searching the review text?

**Answers**

1. What Claude may do: it reads and plans, and cannot edit until you approve. It does not change how well Claude thinks.
2. Neither is guaranteed. Files are combined, not ranked. Remove the clash and state each fact once.
3. A hook, a permission rule or a test, because those run whatever Claude decides.
4. Exit code 2. Exit code 1 is a non-blocking error.
5. Free text can mislead (for example "no blockers"). A schema gives typed fields that code can check the same way every time.

## Go deeper

Full guides (about 20 minutes each):

- [Claude Code basics and Plan Mode](../STUDY_GUIDES/DAY_4/CLAUDE_CODE_BASICS_AND_PLAN_MODE.md)
- [CLAUDE.md, memory and rules](../STUDY_GUIDES/DAY_4/CLAUDE_MD_MEMORY_AND_RULES.md)
- [Skills, hooks and subagents](../STUDY_GUIDES/DAY_4/SKILLS_HOOKS_AND_SUBAGENTS.md)
- [MCP and context in Claude Code](../STUDY_GUIDES/DAY_4/MCP_AND_CONTEXT_IN_CLAUDE_CODE.md)
- [CI review gate](../STUDY_GUIDES/DAY_4/CI_REVIEW_GATE.md)

Open these to practise:

- [Demo 4.0 student copy](../DAY_4/LABS/DEMO_4_0_intro_to_claude/README.md) to follow the bookshop tour.
- [Lab 4.1](../DAY_4/LABS/LAB_4_1_shipping_repo_plan_mode/README.md) for explore and plan. [Lab 4.2](../DAY_4/LABS/LAB_4_2_shipping_config_layers/README.md) for CLAUDE.md, rules and `.mcp.json`.
- [Lab 4.3](../DAY_4/LABS/LAB_4_3_shipping_skill_hook_subagent/README.md) for skill, hook and subagent. [Lab 4.4](../DAY_4/LABS/LAB_4_4_shipping_ci_review_gate/README.md) for the CI gate.
- [Build-It Assembly](../DAY_4/BUILD_IT_ASSEMBLY/README.md), an optional 100-minute run-through on one small service.
