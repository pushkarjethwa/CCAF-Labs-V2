"""Lab 5.2 - Guardrails in code for a refund agent (continues Demo 5B: same story shape, tools, fallback source, untrusted text, limit and human queue).

A shop agent decides refund requests. The model can ask for a refund, but your code decides whether it happens.
You write four small functions:

  TODO 1  find_order        the live orders database first, then the archive, with a note about the source
  TODO 2  wrap_ticket_text  the customer's text, passed to the model as quoted data
  TODO 3  check_refund      the approval limit and the new-customer rule, checked BEFORE any money moves
  TODO 4  add_to_queue      the record for a person to review

HOW TO RUN
  python check.py    pass/fail in plain words. Part A needs no key and no model.
  python lab.py      runs the agent on 5 tickets (needs ANTHROPIC_API_KEY); then python check.py again
The data, the tools, the model loop and the printing are in refund_core.py. You do not need to edit it.
"""
import json

import refund_core as core


# ======================================================================================
# TODO 1 of 4 - THE FALLBACK LOOKUP
# Try core.lookup_orders(order_id). If it finds nothing, try core.lookup_archive(order_id).
# Return {"found", "source", "order", "note"}. The note says where the order was read from.
# ======================================================================================
def find_order(order_id):
    order = core.lookup_orders(order_id)
    if order:
        return {"found": True, "source": "orders", "order": order, "note": "Read from the live orders database."}
    order = core.lookup_archive(order_id)
    if order:
        return {"found": True, "source": "archive", "order": order,
                "note": f"Not in the live orders database. Read from the archive copy of {order['archived_on']}."}
    return {"found": False, "source": "none", "note": f"No record of {order_id}."}


# ======================================================================================
# TODO 2 of 4 - THE QUOTED TEXT
# Return the text between <customer_text untrusted="true"> and </customer_text> tags, one tag per line.
# ======================================================================================
def wrap_ticket_text(text):
    return f'<customer_text untrusted="true">\n{text}\n</customer_text>'


# ======================================================================================
# TODO 3 of 4 - THE APPROVAL CHECK
# Return ("refund", []) when the refund may go ahead, or ("human", reasons) when a person must decide.
# Three rules, each adds one reason: over the agent limit, over the order total, a customer account that is too new.
# ======================================================================================
def check_refund(order, amount, policy):
    reasons = []
    if amount > policy["agent_refund_limit"]:
        reasons.append(f"{amount:,.2f} is above the agent limit of {policy['agent_refund_limit']:,.2f}")
    if amount > order["total"]:
        reasons.append(f"{amount:,.2f} is above the order total of {order['total']:,.2f}")
    if order["customer_age_days"] < policy["new_customer_days"]:
        reasons.append(f"the customer account is only {order['customer_age_days']} days old")
    return ("human" if reasons else "refund"), reasons


# ======================================================================================
# TODO 4 of 4 - THE HUMAN QUEUE
# `path` is a JSON file that holds a list. Add `record` to the end of that list and save the file.
# The file may not exist yet.
# ======================================================================================
def add_to_queue(record, path):
    queue = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    queue.append(record)
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(queue, indent=2), encoding="utf-8")


# ======================================================================================
# RUNNING THE AGENT - do not edit below this line
# ======================================================================================
HOOKS = {"find_order": find_order, "wrap_ticket_text": wrap_ticket_text, "check_refund": check_refund, "add_to_queue": add_to_queue}

if __name__ == "__main__":
    core.run_all(HOOKS, __file__)
