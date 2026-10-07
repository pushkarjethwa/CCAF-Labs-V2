"""check.py - Part A tests your four TODOs with scripted data (no API key needed).
Part B checks the evidence that your stage runs saved in the evidence/ folder.

Exit code 0 = everything passed.
"""
import json
import pathlib

import failure_core as core
import lab

HERE = pathlib.Path(__file__).parent
EVIDENCE = HERE / "evidence"
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


docs = {d["doc_id"]: d["source_text"] for d in core.load_docs()}
truth = core.load_truth()
fixtures = {f["name"]: f for f in core.load_fixtures()}
vendors = core.load_vendors()
print("PART A - your code, tested with scripted data (no API key)\n")

print("TODO 1 - ask_extraction: the Claude call")
fake = FakeClient()
lab.get_client = lambda: fake
got = attempt(lab.ask_extraction, "model-x", "the user text", 777)
call = fake.calls[0] if fake.calls else {}
check(got == "scripted response" and len(fake.calls) == 1, "makes exactly one Claude call and returns its response", "return the response of messages.create")
check(call.get("model") == "model-x" and call.get("max_tokens") == 777, "passes the model and max_tokens it was given", f"model={call.get('model')!r}, max_tokens={call.get('max_tokens')!r}")
check(call.get("system") == core.SYSTEM, "sends core.SYSTEM as the system prompt", f"system={str(call.get('system'))[:60]!r}")
check(call.get("messages") == [{"role": "user", "content": "the user text"}], "sends the user text as one user message", f"messages={call.get('messages')!r}")
check((call.get("output_config") or {}).get("format") == core.OUTPUT_FORMAT, "asks for structured output: output_config={'format': core.OUTPUT_FORMAT}", f"output_config={str(call.get('output_config'))[:80]!r}")

print("\nTODO 2 - arithmetic_issues: subtotal + tax = total")
good = truth["inv_001"]["truth"]
check(attempt(lab.arithmetic_issues, good) == [], "a record that adds up (700.00 + 126.00 = 826.00) returns an empty list")
wrong_total = fixtures["wrong_total_only"]["record"]
found = attempt(lab.arithmetic_issues, wrong_total) or []
check(len(found) == 1 and found[0].path == "total" and found[0].kind == "semantic", "total 129 with subtotal 100 and tax 18 returns one issue on 'total'", f"got {found!r}"[:140])
check(bool(found) and "118" in found[0].message, "the message says what the total should be (118.00)", f"message: {found[0].message if found else None!r}")
rounding = dict(good, subtotal=333.33, tax_amount=25.0, total=358.33)
check(attempt(lab.arithmetic_issues, rounding) == [], "333.33 + 25.00 = 358.33 passes")
off_by_cent = dict(good, total=826.01)
check(attempt(lab.arithmetic_issues, off_by_cent) == [], "a one-cent difference is inside the rounding tolerance")
check(len(attempt(lab.arithmetic_issues, dict(good, total=830.0)) or []) == 1, "a four-unit difference is an issue")
silent = fixtures["silent_subtotal_edit"]["record"]
check(attempt(lab.arithmetic_issues, silent) == [], "the recorded 'silent subtotal edit' (109.32 + 19.68 = 129.00) PASSES the arithmetic rule - that is the point of stage 3")

print("\nTODO 3 - grounding_issues: every number must be printed in the document")
check(attempt(lab.grounding_issues, good, docs["inv_001"]) == [], "the true inv_001 record is fully grounded")
found = attempt(lab.grounding_issues, silent, docs["inv_002"]) or []
check({i.path for i in found} == {"subtotal", "tax_amount", "total"}, "the silent edit on inv_002: subtotal 109.32, tax 19.68 and total 129 are not printed", f"flagged {[i.path for i in found]}")
check(all(i.kind == "grounding" and i.message for i in found) and bool(found), "each issue has kind 'grounding' and a message")
found = attempt(lab.grounding_issues, fixtures["computed_illegible_tax"]["record"], docs["inv_009"]) or []
check(any(i.path == "tax_amount" for i in found), "the invented GST on inv_009 (198.00) is flagged", f"flagged {[i.path for i in found]}")
found = attempt(lab.grounding_issues, fixtures["locale_misparse"]["record"], docs["inv_004"]) or []
check({"tax_amount", "total"} <= {i.path for i in found}, "the locale misparse on inv_004 is flagged (tax 0.19 and total 1.19 are not printed) although the record is self-consistent", f"flagged {[i.path for i in found]}")
check(attempt(lab.grounding_issues, truth["inv_004"]["truth"], docs["inv_004"]) == [], "the true inv_004 record (1.000,00 printed in European format) is grounded")
check(attempt(lab.grounding_issues, truth["inv_010"]["truth"], docs["inv_010"]) == [], "the true 12-line invoice inv_010 is grounded")

print("\nTODO 4 - decide: the retry policy")
a, cap = 3, core.MAX_TOKENS_CAP


def decision(status, n_issues, attempt_no=1, max_tokens=400):
    issues = [core.issue("total", "semantic", "x")] * n_issues
    got = attempt(lab.decide, status, issues, attempt_no, a, max_tokens, cap)
    return got[0] if isinstance(got, tuple) and len(got) == 2 else None


check(decision("ok", 0) == core.ACCEPT, "ok with no issues -> ACCEPT")
check(decision("ok", 2) == core.RETRY_CORRECT, "ok with issues and attempts left -> RETRY_CORRECT")
check(decision("ok", 2, attempt_no=3) == core.REVIEW, "issues and no attempts left -> REVIEW")
check(decision("refusal", 0) == core.REVIEW, "refusal -> REVIEW (never retried)")
check(decision("truncated", 0) == core.RETRY_LARGER, "truncated -> RETRY_LARGER")
check(decision("truncated", 0, attempt_no=3) == core.REVIEW, "truncated with no attempts left -> REVIEW")
check(decision("truncated", 0, max_tokens=cap) == core.REVIEW, "truncated at the max_tokens cap -> REVIEW")
check(decision("unparseable", 1) == core.RETRY_CORRECT, "unparseable (a parse issue) with attempts left -> RETRY_CORRECT")
check(attempt(lab.decide, "ok", [], 1, a, 400, cap) is not None and all(isinstance(x, str) and x for x in (attempt(lab.decide, "ok", [], 1, a, 400, cap) or (0, ""))[1:]), "every decision carries a reason string")

print("\nThe given plumbing (checks that the data and helpers are intact)")
check(len(docs) == 11 and len(truth) == 11, "11 invoices with ground truth")
check(core.structural_issues(silent) == [] and core.structural_issues({"total": "x"}) != [], "the schema check accepts the silent edit (valid shape) and rejects a malformed record")
check({18, 126} <= {int(n) for n in core.extract_numbers(docs["inv_001"])} and 1000 in core.extract_numbers(docs["inv_004"]), "extract_numbers reads 18 and 126, and 1.000,00 as 1000")

print("\nPART B - the evidence your stage runs saved (needs `python lab.py --stage N` with a key)\n")


def load(name):
    path = EVIDENCE / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


ev = {n: load(f"stage{n}.json") for n in range(1, 6)}
if not any(ev.values()):
    print("[SKIP] no evidence yet - run `python lab.py --stage 1`, then 2, 3, 4 and 5, then this again.")
elif not all(results):
    print("[SKIP] fix Part A first, then run the stages again.")
else:
    if ev[1]:
        check(ev[1]["fixtures_schema_valid"], "stage 1: every recorded bad output passed the schema check (valid shape, wrong money)")
        check(len(ev[1]["live"]) >= 6, "stage 1: the live run covered the invoices", f"{len(ev[1]['live'])} rows")
        print(f"       info: posted {ev[1]['posted']}, posted but wrong {ev[1]['posted_wrong']} (a strong model may get all of them right)")
    if ev[2]:
        c = ev[2]["caught"]
        check(c["wrong_total_only"] and not c["silent_subtotal_edit"] and not c["locale_misparse"], "stage 2: the rules catch the wrong total, and MISS the silent edit and the locale misparse", f"caught={c}")
        print("       info: live rule findings: " + "; ".join(f"{r['doc_id']} {len(r['issues'])}" for r in ev[2]["live"] if r["issues"]) or "none")
    if ev[3]:
        check(ev[3]["fixture_passes_rules"], "stage 3: the recorded silent edit passes every business rule")
        print(f"       info: prompt={ev[3]['prompt']}, live accepted-but-wrong records: {ev[3]['live_corrupted'] or 'none'}")
    if ev[4]:
        c = ev[4]["caught"]
        check(all(c.values()), "stage 4: grounding catches every recorded bad output", f"caught={c}")
        by = {r["doc_id"]: r for r in ev[4]["results"]}
        check("inv_010" in by and len(by["inv_010"]["attempts"]) > 1 and by["inv_010"]["attempts"][0]["status"] == "truncated", "stage 4: inv_010 was truncated at 400 tokens and retried with a larger max_tokens", str(by.get("inv_010")))
        check(by["inv_009"]["status"] == "needs_review" or ev[4]["metrics"]["needs_review"] >= 1, "stage 4: the contradictory invoice inv_009 ended up in human review (it cannot be fixed by retrying)")
        check(not ev[4]["silent_corruptions"], "stage 4: no accepted record contradicts the document (silent corruptions = 0)", f"{ev[4]['silent_corruptions']}")
    if ev[5]:
        cfg = ev[5]["configs"]
        check(len(cfg) == 2 and all(v["documents"] >= 6 for v in cfg.values()), "stage 5: both configurations ran on every invoice")
        check(all(v["silent_corruptions"] == 0 for v in cfg.values()), "stage 5: neither configuration posted a wrong record", f"{ {k: v['silent_corruptions'] for k, v in cfg.items()} }")
        print("       info: " + "; ".join(f"{k}: cost per accepted ${v['cost_per_accepted']:.5f}, fallback {v['fallback_rate']:.0%}" for k, v in cfg.items()))

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
raise SystemExit(0 if all(results) else 1)
