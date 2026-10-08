---
lab:
    title: 'Day 4 Labs: Claude Code Configuration and Workflows'
    module: 'Day 4 - Claude Code Configuration and Workflows'
---

# Day 4 Labs

These labs use Claude Code itself. Each one repeats the method of the trainer's demo on a new repository, `shipcalc`, a small shipping-price calculator. If you watched the demo, you will recognize the steps.

To complete these exercises you need Python 3.10 or later, the Claude Code command-line tool (`claude --version`) and a login or API key. Setup is in **DAY_0_SETUP_GUIDE.md**.

Before Lab 4.1, run the intro demo, **DEMO_4_0_intro_to_claude**. It is a 38-minute tour of Claude Code on a tiny bookshop app: `@` and `!`, permission modes, CLAUDE.md, `/context`, a slash command, a skill, a subagent, a hook, an MCP server and headless `claude -p`. It needs no matching lab. Open its [README](DEMO_4_0_intro_to_claude/README.md), run `python check_offline.py`, then follow the **RUN_SHEET**. Part 8 needs `pip install mcp`.

| Lab | Follows | Folder |
|---|---|---|
| Intro to Claude Code (a demo, no lab) | Runs before Lab 4.1 | [DEMO_4_0_intro_to_claude](DEMO_4_0_intro_to_claude/README.md) |
| Explore, Plan and Refactor a Repository with Claude Code | Demo 4A | [LAB_4_1_shipping_repo_plan_mode](LAB_4_1_shipping_repo_plan_mode/README.md) |
| Layer the CLAUDE.md, Rules and Hooks of a Shipping Repo | Demo 4B | [LAB_4_2_shipping_config_layers](LAB_4_2_shipping_config_layers/README.md) |
| Build an API-Contract Review Skill, Hook and Subagent | Demo 4C | [LAB_4_3_shipping_skill_hook_subagent](LAB_4_3_shipping_skill_hook_subagent/README.md) |
| Put Claude Code in CI as a Review Gate | Demo 4D | [LAB_4_4_shipping_ci_review_gate](LAB_4_4_shipping_ci_review_gate/README.md) |

In every lab, work inside the `STARTER` folder, then run `python check.py` (no key needed) to see your progress.

## Optional: Build-It Assembly

When you finish the four labs, you can run the **Build-It Assembly**, one optional, ready-to-run project that brings the whole day together: [BUILD_IT_ASSEMBLY](../BUILD_IT_ASSEMBLY/README.md). It follows a cafe rewards service, "Brew & Bean Rewards", through rules, a skill, a hook, an MCP server and a CI review gate on GitHub. There is nothing to write. You run the commands, each one explains what it does and why, and you watch Claude Code work. It takes about 100 minutes.
