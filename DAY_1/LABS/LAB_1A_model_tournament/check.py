"""check.py - Part A tests your three TODOs with a scripted stand-in for Claude (no key needed).
Part B checks the evidence that your stage runs saved in the evidence/ folder.

Exit code 0 = everything passed.
"""
import json
import pathlib
import sys

import ap_data as data
import lab
import tournament_core as core

EVIDENCE = pathlib.Path(__file__).parent / "evidence"
results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f"\n         {detail}" if detail and not ok else ""))


class FakeClient:
    """Stands in for Claude. Records every request and returns a fixed reply."""

    def __init__(self):
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return "scripted response"


def attempt(function, *args):
    """Call a TODO function. If it is not written yet, say so instead of showing a traceback."""
    try:
        return function(*args)
    except NotImplementedError as exc:
        print(f"         ({exc})")
        return None


def with_fake():
    fake = FakeClient()
    lab.get_client = lambda: fake
    return fake


cases = {c.case_id: c for c in data.load_cases()}
case, policy = cases["inv_017"], data.load_policy()
M = core.MODEL_FAST

print("PART A - your code, tested with a scripted stand-in for Claude (no API key)\n")
print("TODO 1 - ask_plain (stage 1)")
fake = with_fake()
got = attempt(lab.ask_plain, case, M, policy)
call = fake.calls[0] if fake.calls else {}
check(got == "scripted response", "returns the whole response from the call", "write: return get_client().messages.create(...)")
check(len(fake.calls) == 1, "makes exactly one Claude call", f"made {len(fake.calls)}")
check(call.get("model") == M, "uses the model it was given", f"model={call.get('model')!r}")
check(call.get("max_tokens", 0) >= 1000, "sets a generous max_tokens", f"max_tokens={call.get('max_tokens')!r}")
check("accounts-payable" in str(call.get("system", "")), "the system prompt is plain_system(policy)", "pass system=plain_system(policy)")
check(call.get("messages") == [{"role": "user", "content": case.view}], "the user message is the invoice text, case.view", f"got {str(call.get('messages'))[:60]}")
check("output_config" not in call, "stage 1 asks for plain text: no output_config", "remove output_config from ask_plain")

print("\nTODO 2 - ask_structured (stage 2)")
fake = with_fake()
got = attempt(lab.ask_structured, case, M, policy, 1234)
call = fake.calls[0] if fake.calls else {}
fmt = (call.get("output_config") or {}).get("format") or {}
check(got == "scripted response" and len(fake.calls) == 1, "returns the response of exactly one call")
check(fmt.get("type") == "json_schema" and fmt.get("schema") == core.SCHEMA, "output_config={'format': OUTPUT_FORMAT} is passed", f"output_config={call.get('output_config')!r}"[:140])
check("confidence" in str(call.get("system", "")), "the system prompt is structured_system(policy)", "pass system=structured_system(policy)")
check(call.get("max_tokens") == 1234 and call.get("model") == M, "uses the model and max_tokens it was given", f"model={call.get('model')!r}, max_tokens={call.get('max_tokens')!r}")
check(call.get("messages") == [{"role": "user", "content": case.view}], "the user message is the invoice text, case.view")

print("\nTODO 3 - escalation_reasons (stage 4)")


def first(usable, confidence):
    verdict = core.Verdict(structural_ok=usable, semantic_ok=usable, label="low" if usable else None, confidence=confidence)
    return type("Result", (), {"verdict": verdict})()


er = lab.escalation_reasons
check(er(first(True, 0.9), 500.0) == [], "a confident, small invoice is not escalated", f"got {er(first(True, 0.9), 500.0)!r}")
check(er(first(True, 0.6), 500.0) == ["low_confidence"], "confidence below 0.75 gives 'low_confidence'", f"got {er(first(True, 0.6), 500.0)!r}")
check(er(first(True, 0.75), 500.0) == [], "confidence of exactly 0.75 is NOT low", f"got {er(first(True, 0.75), 500.0)!r}")
check(er(first(False, None), 500.0) == ["unusable_output"], "an invalid answer gives 'unusable_output' (and does not crash on a missing confidence)", f"got {er(first(False, None), 500.0)!r}")
check(er(first(True, 0.9), 12000.0) == ["high_value"], "an invoice of 10,000 or more gives 'high_value'", f"got {er(first(True, 0.9), 12000.0)!r}")
check(er(first(True, 0.9), -15000.0) == ["high_value"], "a credit note of -15,000 counts too (the sign does not matter)", f"got {er(first(True, 0.9), -15000.0)!r}")
check(er(first(True, 0.9), 10000.0) == ["high_value"], "exactly 10,000 counts", f"got {er(first(True, 0.9), 10000.0)!r}")
check(er(first(False, None), 20000.0) == ["unusable_output", "high_value"], "both reasons can apply at once, in that order", f"got {er(first(False, None), 20000.0)!r}")

print("\nThe given plumbing (checks that the data and validator are intact)")
vendors, truth = data.load_vendors(), data.load_truth()
all_cases = data.load_cases()
legacy = data.score({c.case_id: data.legacy_label(c.invoice, vendors, policy) for c in all_cases}, truth, policy["error_weights"])
check(len(all_cases) == 24 and legacy.correct == 12, "24 invoices; the old rules engine gets 12 right", f"{legacy.correct}/24")
rows = json.loads((pathlib.Path(__file__).parent / "data" / "bad_outputs.json").read_text(encoding="utf-8"))
check(all(core.check_output(r["text"], r["stop_reason"]).usable == r["usable"] for r in rows), "the validator agrees with all 10 bad-output examples")

print("\nPART B - the evidence your stage runs saved (needs `python lab.py --stage N` with a key)\n")


def load(name):
    path = EVIDENCE / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


s1, s2, s3, s4 = load("stage1.json"), load("stage2.json"), load("tournament.json"), load("routing.json")
if not any((s1, s2, s3, s4)):
    print("[SKIP] no evidence yet - run `python lab.py --stage 1`, then stages 2, 3 and 4, then this again.")
elif not all(results):
    print("[SKIP] fix Part A first, then run the stages again.")
else:
    if s1:
        check(set(s1["answers"]) == {"fast", "balanced", "premium"} and all(a.strip() for a in s1["answers"].values()), "stage 1: all three models answered in plain text")
    if s2:
        check(all(r["structural_ok"] for r in s2["part_a"].values()), "stage 2: all three models returned schema-valid JSON", "check TODO 2: output_config={'format': OUTPUT_FORMAT}")
        check(str(s2["part_b"].get("temperature_kwarg")) in ("TypeError", "400"), "stage 2: the temperature argument was rejected (by the SDK or by the API with a 400)", str(s2["part_b"].get("temperature_kwarg")))
    if s3:
        tiers = s3["tiers"]
        check(all(len(t["results"]) == s3["n"] for t in tiers.values()), f"stage 3: every model classified every one of the {s3['n']} invoices")
        check(all(sum(r["structural_ok"] for r in t["results"]) >= 0.9 * s3["n"] for t in tiers.values()), "stage 3: at least 90% of answers were schema-valid on every model")
        costs = {k: v["per_100k_usd"] for k, v in tiers.items()}
        check(costs["fast"] < costs["balanced"] < costs["premium"], "stage 3: cost per 100,000 rises fast < balanced < premium", str(costs))
    if s4:
        names = [s["name"] for s in s4["strategies"]]
        check("ROUTED cascade" in names and "Haiku-only" in names, "stage 4: the routed cascade and Haiku-only were compared")
        high_value = sum(1 for c in core.data.load_cases() if c.case_id in core.LAB_CASES and abs(c.amount_usd) >= 10_000) if s4["n"] == len(core.LAB_CASES) else None
        if high_value is not None:
            check(s4["routed"]["to_balanced"] >= high_value, f"stage 4: your rule sent every invoice of 10,000 or more ({high_value}) to a stronger model",
                  f"only {s4['routed']['to_balanced']} reached the balanced tier; check TODO 3")
        check(s4["routed"]["to_premium"] <= s4["routed"]["to_balanced"] <= s4["n"], "stage 4: the premium model sees no more cases than the balanced one")

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
