"""check.py - Part A tests your three TODOs with a scripted stand-in for Claude (no key needed).
Part B checks the evidence that your stage runs saved in the evidence/ folder.

Exit code 0 = everything passed.
"""
import json
import pathlib

import evalkit as kit
import lab
from vault import Vault

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


def with_fake():
    fake = FakeClient()
    lab.get_client = lambda: fake
    return fake


schema = kit.load_schema()
user = [{"role": "user", "content": "the invoice text"}]
print("PART A - your code, tested with a scripted stand-in for Claude (no API key)\n")

print("TODO 1 - ask_claude: build the request")
fake = with_fake()
got = attempt(lab.ask_claude, {"messages": user, "system": "You are a data-entry specialist."}, "model-x", 2048)
call = fake.calls[0] if fake.calls else {}
check(got == "scripted response" and len(fake.calls) == 1, "makes exactly one Claude call and returns its response", "the return line is given; build `kwargs` above it")
check(call.get("model") == "model-x" and call.get("max_tokens") == 2048, "passes the model and max_tokens it was given", f"model={call.get('model')!r}, max_tokens={call.get('max_tokens')!r}")
check(call.get("messages") == user, "passes the user message", f"messages={call.get('messages')!r}")
check(call.get("system") == "You are a data-entry specialist.", "passes the system prompt when the version has one", f"system={call.get('system')!r}")
fake = with_fake()
attempt(lab.ask_claude, {"messages": user}, "model-x", 2048)
call = fake.calls[0] if fake.calls else {}
check(bool(call) and "system" not in call, "v0 has no system prompt, so no `system` argument is sent at all (not None)", f"keys sent: {sorted(call)}")
check(bool(call) and "output_config" not in call, "a version with no schema sends no output_config", f"keys sent: {sorted(call)}")

print("\nTODO 2 - ask_claude: add the JSON schema (stage 5)")
fake = with_fake()
attempt(lab.ask_claude, {"messages": user, "system": "s", "output_format": {"type": "json_schema", "schema": schema}}, "model-x", 2048)
call = fake.calls[0] if fake.calls else {}
check((call.get("output_config") or {}).get("format") == {"type": "json_schema", "schema": schema}, "output_config={'format': <the version's output_format>} is sent",
      f"output_config={call.get('output_config')!r}"[:140])
check(call.get("messages") == user and call.get("system") == "s", "the rest of the request is still sent")

print("\nTODO 3 - gate_checks")


def run(accuracy, leaks=0):
    summary = type("Summary", (), {"accuracy": accuracy})()
    return type("Run", (), {"summary": summary, "leaks": ["leak"] * leaks})()


gc = lab.gate_checks
rows = gc(run(0.90), run(0.895))
check(isinstance(rows, list) and len(rows) == 2 and all(isinstance(r, tuple) and len(r) == 2 for r in rows), "returns two (passed, message) pairs", f"got {rows!r}"[:120])
check(len(rows) == 2 and rows[0][0] is True and rows[1][0] is True, "a candidate that is half a point lower, with no leaks, passes both rules", f"got {rows!r}"[:140])
check(len(gc(run(0.90), run(0.85))) == 2 and gc(run(0.90), run(0.85))[0][0] is False, "a candidate that is 5 points lower fails the accuracy rule")
check(len(gc(run(0.90), run(0.90))) == 2 and gc(run(0.90), run(0.90))[0][0] is True, "an equal candidate passes the accuracy rule")
check(len(gc(run(0.90), run(0.95))) == 2 and gc(run(0.90), run(0.95))[0][0] is True, "a better candidate passes the accuracy rule")
check(len(gc(run(0.90), run(0.90, 1))) == 2 and gc(run(0.90), run(0.90, 1))[1][0] is False, "one example leak fails the leak rule")
check(all(isinstance(r[1], str) and r[1] for r in gc(run(0.90), run(0.85, 1))), "each rule has a message that says what it measured")

print("\nThe given plumbing (checks that the data, scorer and vault are intact)")
docs = kit.load_docs()
check(len(docs) == 12 and kit.score_doc("D01", dict(docs[0].truth), docs[0].truth, strict_parsed=True).accuracy == 1.0, "12 invoices; the ground truth scores 100%")
check(kit.score_field("total", "$5.40", 5.40) == 0.0 and kit.score_field("po_number", "N/A", None) == 0.0, "the scorer is strict: '$5.40' and 'N/A' are wrong")
check(Vault().verify().ok, "the prompt vault: every released prompt matches its recorded sha256")

print("\nPART B - the evidence your stage runs saved (needs `python lab.py --stage N` with a key)\n")


def load(name):
    path = EVIDENCE / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


stages = {name: load(name) for name in ("stage1.json", "stage2.json", "stage3.json", "stage5.json", "gate.json")}
if not any(stages.values()):
    print("[SKIP] no evidence yet - run `python lab.py --stage 1`, then 2, 3, 5 and gate, then this again.")
elif not all(results):
    print("[SKIP] fix Part A first, then run the stages again.")
else:
    for name in ("stage1.json", "stage2.json", "stage3.json", "stage5.json"):
        ev = stages[name]
        if ev:
            n = len(ev["runs"][0]["per_doc"])
            check(n in (6, 12) and all(len(r["per_doc"]) == n for r in ev["runs"]), f"{name}: every version ran on all {n} invoices",
                  ", ".join(f"{r['version']} {100 * r['accuracy']:.1f}%" for r in ev["runs"]))
    s1 = stages["stage1.json"]
    if s1:
        v0 = next(r for r in s1["runs"] if r["version"] == "v0")
        v1 = next(r for r in s1["runs"] if r["version"] == "v1")
        print(f"       info: parse rate v0 {v0['parse_rate']:.0%}, v1 {v1['parse_rate']:.0%}; accuracy v0 {100 * v0['accuracy']:.1f}%, v1 {100 * v1['accuracy']:.1f}%")
    s2 = stages["stage2.json"]
    if s2:
        by = {r["version"]: r for r in s2["runs"]}
        check(by["v3"]["parse_rate"] >= by["v1"]["parse_rate"], "stage 2: the format contract (v3) parses at least as often as the plain role prompt (v1)")
    s3 = stages["stage3.json"]
    if s3:
        print(f"       info: v4 leaks {s3['runs'][1]['leaks'] or 'none'}; documents regressed vs v3: {s3['regressed']} (a strong model may show none)")
    s5 = stages["stage5.json"]
    if s5:
        n = len(s5["runs"][0]["per_doc"])
        check(s5["schema_audit_ok"], "stage 5: the schema passed the audit")
        check(s5["stats"]["v6"]["schema_valid"] >= n - 1, f"stage 5: v6 returned schema-valid output for at least {n - 1} of {n} invoices (TODO 2)", f"{s5['stats']['v6']['schema_valid']}/{n}")
        print(f"       info: D11 total without XML {s5['d11_total']['v6_no_xml']}, with XML {s5['d11_total']['v6']} (truth 1122.84)")
    gate = stages["gate.json"]
    if gate:
        check(set(gate["verdicts"]) == {"v7_reordered", "v7_trim_rules", "v7_extra_example"}, "gate: all three edited prompts were judged")
        print("       info: " + "; ".join(f"{n}: {'PASS' if v['passed'] else 'FAIL'} (designed {'PASS' if v['designed_to_pass'] else 'FAIL'})" for n, v in gate["verdicts"].items()))

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
raise SystemExit(0 if all(results) else 1)
