"""OPTIONAL and NOT GRADED: your guard inside the real Claude Agent SDK.

lab.py drives a Claude tool loop through your guard by hand so every step is visible. This file hands the SAME guard to the Agent SDK,
which then calls your hooks and your can_use_tool itself. Read it: there is almost nothing in it, because the guard is the work.

Needs the Claude Code CLI installed (`claude --version`), claude-agent-sdk, and ANTHROPIC_API_KEY.   python live_run.py
Author's note: this file has not been run live. If it fails, the failure is in the SDK set-up, not in your guard.
"""
import asyncio
import json
import os
import pathlib
import sys

from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock, create_sdk_mcp_server, query, tool

import lab


async def main():
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set.")
    state = pathlib.Path(__file__).parent / "results" / "live_state"
    guard, dc = lab.MaintenanceGuard(lab.ApprovalStore(state / "approvals.json"), state / "audit.jsonl"), lab.DataCenter()

    def reply(name, args):
        return {"content": [{"type": "text", "text": json.dumps(dc.execute(lab.PREFIX + name, args))}]}

    @tool("get_rack_status", "Read the status of one rack.", {"rack": str})
    async def get_rack_status(args):
        return reply("get_rack_status", args)

    @tool("set_power_state", "Change a rack's power state. op is power_off or reboot.", {"rack": str, "op": str})
    async def set_power_state(args):
        return reply("set_power_state", args)

    @tool("update_firmware", "Push firmware to a rack. op is firmware_7.2.", {"rack": str, "op": str})
    async def update_firmware(args):
        return reply("update_firmware", args)

    options = guard.sdk_options()  # YOUR hooks, YOUR can_use_tool, YOUR allowed_tools
    options.mcp_servers = {"dc": create_sdk_mcp_server("dc", tools=[get_rack_status, set_power_state, update_firmware])}
    options.max_budget_usd = 0.50
    plan = "\n".join(f"{a['action_id']}: {a['tool']} on {a['rack']} ({a['op']})" for a in lab.DATA["plan"])
    async for message in query(prompt=f"Apply this maintenance plan now.\n\n{plan}", options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    print(f"  -> {block.name}({block.input})")
                elif isinstance(block, TextBlock) and block.text.strip():
                    print(block.text)
        elif isinstance(message, ResultMessage):
            print(f"\n[done] turns={message.num_turns} error={message.is_error}")
    print("\nWhat REALLY changed:", [(e["tool"], e["rack"], e["op"]) for e in dc.effects])
    print("Pending change requests:", {k: v["state"] for k, v in guard.store.records.items()})


if __name__ == "__main__":
    asyncio.run(main())
