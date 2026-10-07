"""check.py - Part A tests your three TODOs with a scripted stand-in for Claude (no key needed).
Part B checks the real run that `python lab.py` saved.

Exit code 0 = everything passed.
"""
import json
import sys

import lab
from expense_core import BRIEFS, CLAIMS

results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f"\n         {detail}" if detail and not ok else ""))


class FakeClient:
    """Stands in for Claude. `reply(system, user)` returns the text Claude would send back. Records every call."""

    def __init__(self, reply):
        self.reply, self.calls = reply, []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        text = self.reply(kwargs.get("system", ""), kwargs["messages"][0]["content"])
        block = type("Block", (), {"type": "text", "text": text})()
        return type("Response", (), {"content": [block]})()


def with_fake(reply):
    fake = FakeClient(reply)
    lab.get_client = lambda: fake
    return fake


EXPECTED = {1: "conversational", 2: "workflow", 3: "workflow", 4: "agentic", 5: "agentic"}
claim = {c["id"]: c for c in CLAIMS}

print("PART A - your code, tested with a scripted stand-in for Claude (no API key)\n")
print("TODO 1 - architecture_for")
for brief in BRIEFS:
    got = lab.architecture_for(brief["signals"])
    check(got == EXPECTED[brief["id"]], f"Brief {brief['id']} {brief['title']}: {EXPECTED[brief['id']]}",
          f"your function returned {got!r}. Who controls the next step: {brief['signals']['next_step_controller']}?")

print("\nTODO 2 - run_conversational (Build 1)")
fake = with_fake(lambda system, user: '{"decision": "reject", "reasons": ["scripted"]}')
got = lab.run_conversational(claim["R07"])
check(got == "reject", "returns the decision found in Claude's JSON reply", f"returned {got!r}; use decision_in(text_of(response))")
check(len(fake.calls) == 1, "makes exactly one Claude call", f"made {len(fake.calls)}")
call = fake.calls[0] if fake.calls else {}
check(call.get("model") and call.get("max_tokens", 0) >= 2048, "passes model and a generous max_tokens", f"got model={call.get('model')!r}, max_tokens={call.get('max_tokens')!r}")
check("PER PERSON" in call.get("system", "").upper() or "ALCOHOL" in call.get("system", "").upper(), "the system prompt contains the T&E policy text",
      "the model cannot apply a policy it was never given: add policy_text() to the system prompt")
check("Gramercy" in str(call.get("messages", "")), "the user message contains the claim text", "send claim_facts(claim) as the user message")

print("\nTODO 3 - run_workflow (Build 2)")
claim_by_text = {c["text"]: c for c in CLAIMS}
fake = with_fake(lambda system, user: json.dumps({**claim_by_text[user]["truth"], "confidence": "high"}))  # Claude extracts perfectly
decisions = {cid: lab.run_workflow(claim[cid]) for cid in claim}
wrong = [f"{cid}: {decisions[cid]} (expected {claim[cid]['expected_decision']})" for cid in claim if decisions[cid] != claim[cid]["expected_decision"]]
check(not wrong, "when Claude extracts the fields correctly, code reaches the right decision on all 12 claims", "; ".join(wrong[:3]))
check(len(fake.calls) == len(claim), "makes exactly one Claude call per claim", f"made {len(fake.calls)} calls for {len(claim)} claims")
check(fake.calls and "merchant" in fake.calls[0].get("system", ""), "the system prompt contains the extraction schema", "add json.dumps(EXTRACTION_SCHEMA) to the system prompt")
check(fake.calls and fake.calls[0]["messages"][0]["content"] == CLAIMS[0]["text"], "the user message is just the claim text", "send claim['text'] as the user message")

print("\nPART B - your real run (needs `python lab.py` with a key)\n")
problems_a = not all(results)
if not lab.RESULTS_FILE.exists():
    print("[SKIP] results/run.json not found - run `python lab.py`, then this again.")
elif problems_a:
    print("[SKIP] fix Part A first, then run `python lab.py` again.")
else:
    saved = json.loads(lab.RESULTS_FILE.read_text(encoding="utf-8"))
    rows, score = saved["rows"], saved["score"]
    check(saved.get("fingerprint") == lab.code_fingerprint(), "the saved run is from your CURRENT code", "you edited a TODO after the last run - run `python lab.py` again")
    check(len(rows) == len(lab.LAB_CLAIMS), f"all {len(lab.LAB_CLAIMS)} claims were reviewed both ways")
    valid = {"approve", "reject", "escalate"}
    check(all(r["conversational"] in valid for r in rows), "every conversational answer was a decision",
          "check that TODO 2 returns decision_in(text_of(response))")
    check(all(r["workflow"] in valid for r in rows), "every workflow answer was a decision")
    check(score["workflow"] >= 5, f"the workflow got at least 5 of 6 right (it got {score['workflow']})",
          "the model extracts and code decides, so a miss means a bad extraction - read the table above")
    check(score["conversational"] >= 3, f"the conversational build got at least 3 of 6 right (it got {score['conversational']})")

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
