"""Run while you work.   python check.py
Part A tests YOUR code with hand-made calls: no API key, the mock airline with its latencies scaled down.
Part B reads evidence/stageN.json from the stages you have run with Claude (python lab.py --stage N).
Fails on the starter by design. Exit code 0 means every check passed."""
import json
import pathlib
import re
import sys
import time
from types import SimpleNamespace

import lab
import travel_core as core

HERE = pathlib.Path(__file__).parent
EVIDENCE = HERE / "evidence"
results = []


def check(description, test):
    """Run a test function that returns (ok, detail). A TODO that is still a stub counts as a failure, not a crash."""
    try:
        ok, detail = test()
    except NotImplementedError as stub:
        ok, detail = False, str(stub)
    except Exception as exc:  # noqa: BLE001 - show the student what broke
        ok, detail = False, f"{type(exc).__name__}: {exc}"
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f" ({detail})" if detail else ""))


def info(text):
    print(f"[info] {text}")


def call(i, name, **args):
    return SimpleNamespace(id=i, name=name, input=args)


print("== Part A: your code, tested directly (no API key) ==")


def t_loyalty_tool():
    tool = lab.LOYALTY_TIER_TOOL
    schema = tool["input_schema"]
    ok = (tool["name"] == "loyalty_tier" and "read-only" in tool["description"].lower() and schema["required"] == ["traveler_id"]
          and schema["additionalProperties"] is False and set(schema["properties"]) == {"traveler_id"})
    return ok, ""


def t_loyalty_description():
    words = lab.LOYALTY_TIER_TOOL["description"].lower()
    return all(w in words for w in ("tier", "hotel", "rate")) and len(words) > 60, ""


def t_concurrent():
    def run_one(c):
        time.sleep(0.15)
        return {"tool_use_id": c.id}
    calls = [call(f"c{i}", "flight_status") for i in range(4)]
    started = time.perf_counter()
    out = lab.run_concurrently(run_one, calls)
    took = time.perf_counter() - started
    return took < 0.35 and [b["tool_use_id"] for b in out] == ["c0", "c1", "c2", "c3"], f"{took:.2f}s for four 0.15s calls"


def t_order():
    out = lab.run_concurrently(lambda c: {"tool_use_id": c.id}, [call("a", "x"), call("b", "x"), call("c", "x")])
    return [b["tool_use_id"] for b in out] == ["a", "b", "c"], ""


def state(succeeded=(), refs=()):
    s = core.RunState()
    s.succeeded, s.refs = set(succeeded), set(refs)
    return s


def t_gate_prereq():
    problem = lab.gate("book_hotel", {"hotel_id": "H", "rebook_ref": "RB-0001"}, state())
    return bool(problem) and problem["error"] == "PREREQUISITE_NOT_MET" and problem["retryable"] is False and len(problem["hint"]) > 15, str(problem)[:80]


def t_gate_unknown_ref():
    problem = lab.gate("book_hotel", {"hotel_id": "H", "rebook_ref": "RB-9999"}, state({"rebook_flight"}, {"RB-0001"}))
    return bool(problem) and problem["error"] == "UNKNOWN_REFERENCE", str(problem)[:80]


def t_gate_ok():
    ok1 = lab.gate("book_hotel", {"hotel_id": "H", "rebook_ref": "RB-0001"}, state({"rebook_flight"}, {"RB-0001"})) is None
    ok2 = lab.gate("rebook_flight", {"pnr": "K7QD2L", "option_id": "OPT-B"}, state()) is None
    return ok1 and ok2, ""


def t_gate_notify():
    needs_both = lab.gate("notify_traveler", {"traveler_id": "T-1", "rebook_ref": "RB-0001", "hotel_ref": "HB-0001"}, state({"rebook_flight"}, {"RB-0001"}))
    ok = lab.gate("notify_traveler", {"traveler_id": "T-1", "rebook_ref": "RB-0001", "hotel_ref": "HB-0001"}, state({"rebook_flight", "book_hotel"}, {"RB-0001", "HB-0001"}))
    return bool(needs_both) and ok is None, ""


def t_replay_batch():
    measured, services = core.replay(core.RecordedBatch(), 3)
    return (measured["unverified"] == 0 and not measured["order_violations"] and measured["hotels"] == 0 and measured["notifications"] == 0 and measured["rebookings"] == 1,
            f"{measured}"[:110])


def t_key_stable():
    a = lab.key_for("rebook_flight", {"pnr": "K7QD2L", "option_id": "OPT-B"})
    b = lab.key_for("rebook_flight", {"option_id": "OPT-B", "pnr": "K7QD2L"})
    c = lab.key_for("rebook_flight", {"pnr": "K7QD2L", "option_id": "OPT-C"})
    return a == b and a != c and re.fullmatch(r"[0-9a-f]{16}", a) is not None, a


def t_timeout_result():
    r = lab.timeout_result("rebook_flight", Exception("no acknowledgement"))
    return (r.get("error") == "TIMEOUT" and r.get("retryable") is True and r.get("outcome_unknown") is True and "no acknowledgement" in r.get("message", "")
            and "identical" in r.get("hint", "").lower()), str(r)[:90]


def t_replay_retry():
    measured, services = core.replay(core.RecordedRetry(), 4)
    return measured["rebookings"] == 1 and measured["replays"] >= 1, f"rebookings {measured['rebookings']}, replays {measured['replays']}"


def t_guard():
    measured, services = core.replay(core.RecordedRunaway(), 4, max_turns=6)
    return measured.get("stopped") == "max_turns" and measured.get("turns") == 6, str(measured)[:100]


check("TODO 1: the loyalty_tier definition has the name, a read-only description and one required traveler_id", t_loyalty_tool)
check("TODO 1: the description says what it returns (tier, hotel rate cap)", t_loyalty_description)
check("TODO 2: four 0.15 s calls finish in well under 0.6 s (they overlap)", t_concurrent)
check("TODO 2: the results come back in the order of the calls", t_order)
check("TODO 3: a write whose prerequisite has not succeeded is refused (PREREQUISITE_NOT_MET, not retryable, with a hint)", t_gate_prereq)
check("TODO 3: a reference no tool returned is refused (UNKNOWN_REFERENCE)", t_gate_unknown_ref)
check("TODO 3: a ready write is allowed", t_gate_ok)
check("TODO 3: notify_traveler needs both the rebooking and the hotel", t_gate_notify)
check("TODO 3: the recorded batch leaves no unverified entry and no order violation", t_replay_batch)
check("TODO 4: the key is the same for the same call whatever the argument order (16 hex characters)", t_key_stable)
check("TODO 4: the timeout result says the outcome is unknown and a retry is safe", t_timeout_result)
check("TODO 4: the recorded retry books ONE seat and the second call is replayed", t_replay_retry)
check("TODO 5: a model that never stops is cut off at max_turns", t_guard)

print("\n== Part B: your real runs with Claude (evidence/stageN.json) ==")
found = sorted(EVIDENCE.glob("stage*.json")) if EVIDENCE.exists() else []
if not found:
    print("(Part B skipped: run `python lab.py --stage 1` and the later stages first)")
data = {int(p.stem[5:]): json.loads(p.read_text(encoding="utf-8")) for p in found}
for stage, d in sorted(data.items()):
    m = d["live"]
    print(f"\n-- stage {stage}: {core.STAGE_TITLES[stage]} --")
    info(f"rebookings {m['rebookings']}, hotels {m['hotels']}, notices {m['notifications']}, unverified {m['unverified']}, "
         f"order violations {len(m['order_violations'])}, read phase {m['read_span_s']}s, turns {m['turns']}")
    if stage == 1:
        info("stage 1 is the baseline: a second seat, no tier and a long read phase are expected here")
    if stage >= 2 and 1 in data and m["read_span_s"] and data[1]["live"]["read_span_s"]:
        info(f"read phase {data[1]['live']['read_span_s']}s in stage 1 against {m['read_span_s']}s now (it depends on how many reads the model batches)")
    if stage in (3, 4):
        check(f"stage {stage}: the recorded replay is safe with your code", lambda d=d: (d["replay_after"]["unverified"] == 0 and not d["replay_after"]["order_violations"], ""))
    if stage >= 3:
        check(f"stage {stage}: the live run has no unverified entries and no order violations", lambda m=m: (m["unverified"] == 0 and not m["order_violations"], ""))
    if stage >= 4:
        check(f"stage {stage}: the live run booked exactly one seat", lambda m=m: (m["rebookings"] == 1, f"{m['rebookings']} rebookings"))
    if stage == 5:
        check("stage 5: the runaway model was stopped by the guard", lambda d=d: (d["runaway"].get("stopped") == "max_turns", str(d["runaway"])[:80]))
print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
