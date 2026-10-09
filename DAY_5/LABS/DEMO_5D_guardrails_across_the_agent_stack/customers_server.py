"""Demo 5D - The `customers` server: two tools, two layers of protection.

TOOL layer (stage 2)  read_customer() and issue_refund() protect themselves: argument limits, minimal results, idempotency.
MCP layer (stage 3)   handle() is the front door: token, scope, allow-list by full tool name, server-side validation.

The data is author-written sample data in data/customers.json. The refund ledger lives in memory.
In production the token would travel in an Authorization header to a remote MCP server. Here the server runs
inside the script, so each tool wrapper presents its own scoped token. The checks are the same.
"""
import json
import os
import secrets
import time

import policy
from policy import POLICY, mcp

SCOPE_OF_TOOL = POLICY["tool_scopes"]  # full tool name -> the scope a token needs
ARGUMENTS = {  # what each tool accepts: names and types
    "read_customer": {"customer_id": str, "country": str},
    "issue_refund": {"customer_id": str, "amount": (int, float), "idempotency_key": str},
}


def fail(reason):
    return {"ok": False, "error": reason}


def load_tokens():
    """Read the two scoped tokens from the environment. Without them, make safe demo tokens for this run."""
    return {"read": os.environ.get("CUSTOMERS_READ_TOKEN") or "demo-read-" + secrets.token_hex(8),
            "write": os.environ.get("CUSTOMERS_WRITE_TOKEN") or "demo-write-" + secrets.token_hex(8)}


class CustomersServer:
    def __init__(self, tokens=None):
        self.tokens = tokens or load_tokens()
        self.scopes = {self.tokens["read"]: "customers:read", self.tokens["write"]: "refunds:write"}
        self.expires_at = time.time() + POLICY["token_ttl_seconds"]  # short-lived: 15 minutes
        rows = json.loads((policy.DATA / "customers.json").read_text(encoding="utf-8"))["customers"]
        self.customers = {row["customer_id"]: row for row in rows}
        self.refunds = {}  # idempotency key -> the refund that key created
        self.log = []      # the server's own log, redacted
        self.calls = []    # names of the tools that really ran, for the offline check

    # -- TOOL layer (stage 2) --------------------------------------------------------------------------------

    def read_customer(self, args):
        problem = policy.check_customer_id(args["customer_id"]) or policy.check_country(args["country"])
        if problem:
            return fail(problem)
        row = self.customers.get(args["customer_id"])
        if row is None or row["country"] != args["country"]:
            return fail("no matching customer")
        name, email = row["name"].split(), row["email"]
        return {"ok": True, "customer_id": row["customer_id"], "display_name": f"{name[0]} {name[-1][0]}.",
                "email_masked": email[0] + "***@" + email.split("@")[1], "country": row["country"], "plan": row["plan"],
                "order_id": row["last_order_id"], "order_amount": row["last_order_amount"]}  # no phone, address or notes

    def issue_refund(self, args):
        problem = (policy.check_customer_id(args["customer_id"]) or policy.check_refund_amount(args["amount"])
                   or policy.check_key(args["idempotency_key"]))
        if problem:
            return fail(problem)
        row = self.customers.get(args["customer_id"])
        if row is None or policy.check_country(row["country"]):
            return fail("no refundable customer with that id")
        earlier = self.refunds.get(args["idempotency_key"])
        if earlier:  # the same key again: report the first refund and do nothing new
            if (earlier["customer_id"], earlier["amount"]) != (args["customer_id"], args["amount"]):
                return fail("this idempotency_key was used for a different refund")
            return {"ok": True, **earlier, "status": "duplicate"}
        refund = {"refund_id": f"RF-{len(self.refunds) + 1:04d}", "customer_id": args["customer_id"], "amount": args["amount"]}
        self.refunds[args["idempotency_key"]] = refund
        return {"ok": True, **refund, "status": "issued"}

    # -- MCP layer (stage 3) ---------------------------------------------------------------------------------

    def scope_of(self, token, now):
        """Return (scope, None) for a good token, or (None, the reason) for a bad one."""
        if not token:
            return None, "401 no token"
        for known, scope in self.scopes.items():
            if secrets.compare_digest(token, known):
                return (scope, None) if now < self.expires_at else (None, "401 token expired")
        return None, "401 unknown token"

    def handle(self, tool, args, token, now=None):
        """The front door. `tool` is the full name, such as mcp__customers__read_customer."""
        now = now or time.time()
        scope, problem = self.scope_of(token, now)
        if tool not in SCOPE_OF_TOOL:
            result = fail("403 tool is not on the allow-list")
        elif problem:
            result = fail(problem)
        elif scope != SCOPE_OF_TOOL[tool]:
            result = fail(f"403 scope {scope} cannot call {tool}")
        else:
            result = self.run(tool.removeprefix(mcp("")), args)
        shown = {**args, "customer_id": policy.mask_id(args.get("customer_id"))}  # ids are masked in logs
        self.log.append(policy.redact(f"call {tool} token={token} args={shown} -> {'ok' if result['ok'] else result['error']}",
                                      self.tokens.values()))
        return result

    def run(self, name, args):
        """Check the argument names and types on the server, then run the tool. Never trust the client's own checks."""
        wanted = ARGUMENTS[name]
        if set(args) != set(wanted) or not all(isinstance(args[key], wanted[key]) for key in wanted):
            return fail(f"arguments must be exactly {sorted(wanted)} with the right types")
        self.calls.append(name)
        return getattr(self, name)(args)

    def reply_text(self, result):
        """Wrap a result for the model. It is data from a system, not an instruction."""
        return policy.wrap_untrusted(json.dumps(result), "tool_result")
