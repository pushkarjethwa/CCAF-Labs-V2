"""Demo 5E - The tier rules, as plain Python. No SDK, no model, no network.

tiers.json is the single source: the options and the gate both read the tool lists from here.
The model never sees these rules and cannot change them.
"""
import json
from pathlib import Path

RULES = json.loads((Path(__file__).parent / "data" / "tiers.json").read_text(encoding="utf-8"))
TIERS = RULES["tiers"]
MAX_REDEEM = RULES["max_redeem_per_visit"]


def tools_for(tier):
    """The short tool names this tier may call. An unknown tier may call nothing."""
    return TIERS.get(tier, {}).get("tools", [])


def check_redeem(points, balance):
    """Return None when a redemption is fine, or a short reason when it is not."""
    if isinstance(points, bool) or not isinstance(points, int) or points <= 0:
        return "points must be a whole number above zero"
    if points > MAX_REDEEM:
        return f"the limit is {MAX_REDEEM} points per visit"
    if points > balance:
        return f"the balance is only {balance} points"
    return None


def decide(tier, tool, args, balance):
    """Return (allowed, reason) for one tool call. Anything no rule allows is denied."""
    if tool not in tools_for(tier):
        return False, f"{tier} cannot use {tool}"
    if tool == "redeem_points":
        problem = check_redeem(args.get("points"), balance)
        if problem:
            return False, f"{tier} cannot redeem: {problem}"
    return True, f"the {tier} tier may use {tool}"
