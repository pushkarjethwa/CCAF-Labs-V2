"""check.py - Part A tests your four TODOs with no API key and no model. Part B checks the real runs saved by `python lab.py`.

Exit code 0 = everything passed.
"""
import json
import pathlib
import sys
import tempfile

import invoice_core as core
import lab

results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f"\n         {detail}" if detail and not ok else ""))


def guarded(fn, *args):
    try:
        return fn(*args)
    except Exception as exc:  # a TODO that crashes is reported as a failure, not a traceback
        return f"{type(exc).__name__}: {exc}"


CASES = {c["id"]: c for c in core.CASES}
case = CASES["I01"]
good = {"decision": "pay", "escalate": False, "total": 8400, "citations": ["L1", "GR", "PO"], "explanation": "Everything matches."}


def graded(**changes):
    return guarded(lab.grade, {**good, **changes}, case)


print("PART A - your four TODOs, tested with no API key and no model\n")
print("TODO 1 - the grader")
check(graded() == {"schema": True, "decision": True, "items": True, "total": True, "escalate": True}, "grade: a correct answer passes all five checks", f"you returned {graded()!r}")
check(isinstance(graded(decision="hold"), dict) and graded(decision="hold").get("decision") is False and graded(decision="hold").get("items") is True, "grade: a wrong decision fails only the decision check")
check(isinstance(graded(citations=["L1"]), dict) and graded(citations=["L1"]).get("items") is False, "grade: a missing required line id fails the items check")
check(isinstance(graded(total=8450), dict) and graded(total=8450).get("total") is True and graded(total=8600).get("total") is False, "grade: a total within 1 percent passes (8,450) and 2 percent fails (8,600)")
check(isinstance(graded(escalate=True), dict) and graded(escalate=True).get("escalate") is False, "grade: a wrong escalate flag fails the escalate check")
check(guarded(lab.grade, None, case) == {name: False for name in core.CHECKS} and graded(decision="maybe") == {name: False for name in core.CHECKS}, "grade: an answer with the wrong shape fails all five checks")

print("\nTODO 2 - the source check")
invoice = core.INVOICES["I01"]
for cited, share in ((["L1", "GR"], 1.0), (["L1", "L9"], 0.5), (["L9"], 0.0)):
    got = guarded(lab.coverage, {**good, "citations": cited}, invoice)
    check(got == share, f"coverage: {cited} gives {share}", f"you returned {got!r}")

print("\nTODO 3 - the release gate")
ok_old = {"I01": True, "I02": True, "I03": False, "I04": False, "I05": True, "I06": True, "I07": False, "I08": False}
all_pass = {key: True for key in ok_old}
check(guarded(lab.release_gate, ok_old, all_pass) == "GATE: PASS", "release_gate: more cases pass, none regress, must-escalate cases pass: GATE: PASS", f"you returned {guarded(lab.release_gate, ok_old, all_pass)!r}")
regressed = {**all_pass, "I01": False}
check(guarded(lab.release_gate, ok_old, regressed) == "GATE: BLOCKED", "release_gate: I01 passed in v1 and fails in v2, so it is blocked", f"you returned {guarded(lab.release_gate, ok_old, regressed)!r}")
missed = {**all_pass, "I07": False}
check(guarded(lab.release_gate, ok_old, missed) == "GATE: BLOCKED", "release_gate: a must-escalate case (I07) fails in v2, so it is blocked", f"you returned {guarded(lab.release_gate, ok_old, missed)!r}")

print("\nTODO 4 - the review queue")
small = {"decision": "pay", "escalate": False, "total": 5000, "citations": ["L1"], "explanation": "ok"}
big = {"decision": "pay", "escalate": False, "total": 150000, "citations": ["L1", "PO"], "explanation": "ok"}
flagged = {"decision": "escalate", "escalate": True, "total": 27600, "citations": ["L1", "PO"], "explanation": "ok"}
path = pathlib.Path(tempfile.mkdtemp()) / "queue.json"
queue = guarded(lab.write_queue, {"A": small, "B": big, "C": flagged}, path)
check(isinstance(queue, list) and [item.get("case") for item in queue] == ["B", "C"], "write_queue: a USD 150,000 answer (B) and an escalate=true answer (C) are queued, a small one (A) is not", f"you returned {queue!r}")
saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
check(saved == queue and queue != [], "write_queue: the same list is written to the file as JSON", "the file was not written, or it differs from the returned list")
check(isinstance(queue, list) and queue[:1] == [{"case": "B", "total": 150000, "evidence": ["L1", "PO"]}], "write_queue: each item has case, total and evidence", f"first item: {queue[:1]!r}")

print("\nPART B - the real runs (needs `python lab.py` with a key)\n")
runs = {v: (core.RESULTS / f"run_{v}.json") for v in ("v1", "v2")}
if not all(p.exists() for p in runs.values()):
    print("[SKIP] results/run_v1.json or run_v2.json not found - finish the TODOs, run `python lab.py`, then this again.")
else:
    v1, v2 = core.load_run("v1"), core.load_run("v2")
    check(len(v1) == len(core.CASES) and len(v2) == len(core.CASES), "Claude answered all 8 invoices with both prompt versions", f"v1 {len(v1)}, v2 {len(v2)}")
    check(all(r["model"] for r in v1 + v2) and sum(core.schema_ok(r["output"]) for r in v1 + v2) > 0, "the saved answers come from a model run and at least some have the right shape")
    old, new = guarded(lab.passed_by_case, v1), guarded(lab.passed_by_case, v2)
    check(isinstance(old, dict) and isinstance(new, dict) and len(old) == 8 and len(new) == 8, "your grader grades every saved answer", f"{old!r}")
    if isinstance(old, dict) and isinstance(new, dict):
        gate = guarded(lab.release_gate, old, new)
        check(gate in ("GATE: PASS", "GATE: BLOCKED"), "your gate gives a decision on the real v1 and v2 results", f"got {gate!r}")
        shares = [guarded(lab.coverage, r["output"], core.INVOICES[r["case"]]) for r in v1 if core.schema_ok(r["output"])]
        check(shares and all(isinstance(s, float) and 0 <= s <= 1 for s in shares), "your source check returns a share from 0 to 1 for every v1 answer", f"{shares!r}")
        print(f"info: pass rate v1 {sum(old.values())}/8, v2 {sum(new.values())}/8. {gate}. v1 provenance coverage {100 * sum(shares) / max(len(shares), 1):.0f}%.")
    queue_file = core.RESULTS / "human_review_queue.json"
    outputs = {r["case"]: r["output"] for r in v2 if core.schema_ok(r["output"])}
    expected = guarded(lab.write_queue, outputs, pathlib.Path(tempfile.mkdtemp()) / "q.json")
    check(queue_file.exists() and json.loads(queue_file.read_text(encoding="utf-8")) == expected and expected != [], "results/human_review_queue.json holds the v2 answers that need a person", "run `python lab.py --stage 4` after TODO 4")
    must = {c["id"] for c in core.CASES if c["expected_escalate"]}
    print(f"info: must-escalate cases in the queue: {len(must & {i['case'] for i in expected if isinstance(i, dict)})}/{len(must)}.")

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
