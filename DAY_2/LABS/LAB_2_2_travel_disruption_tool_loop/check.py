"""Run while you work on lab.py.   python check.py
Part A tests YOUR code with small hand-made inputs. No API key and no model needed.
Part B reads evidence/evidence.json, which `python lab.py` writes after a real run. Exit code 0 means all passed."""
import json
import sys
from types import SimpleNamespace

import lab
from travel_services import TravelServices, analyse, load_scenario

HERE = lab.HERE
results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f" ({detail})" if detail else ""))


def use(number, name, **arguments):
    """A hand-made tool_use block (what Claude would send)."""
    return SimpleNamespace(type="tool_use", id=f"toolu_{number}", name=name, input=arguments)


def body(result):
    try:
        return json.loads(result["content"])
    except (ValueError, TypeError):
        return {}


scenario = load_scenario(HERE / "data" / "scenario.json")
pnr = scenario["travelers"]["T-1001"]["pnr"]
option = next(o["option_id"] for o in scenario["rebooking_options"] if o["seats_left"] > 0)
hotel = next(h["hotel_id"] for h in scenario["hotels"] if h["rooms_left"] > 0)
SCALE = 0.3  # shrink the mock latencies so the tests run fast

print("== Part A: your code on hand-made inputs (no API key needed) ==")
names = [t["name"] for t in lab.TOOLS]
tier = next((t for t in lab.TOOLS if t["name"] == "loyalty_tier"), None)
check(tier is not None and len(tier["description"]) >= 60 and "read" in tier["description"].lower()
      and tier["input_schema"].get("required") == ["traveler_id"] and tier["input_schema"].get("additionalProperties") is False,
      "TODO 0: loyalty_tier tool is defined (read-only description, required traveler_id, additionalProperties false)")

services = TravelServices(scenario, latency_scale=SCALE)
reads = [use(1, "flight_status", flight_no="XA482"), use(2, "rebooking_options", pnr=pnr),
         use(3, "hotel_availability", airport="LHR", date="2026-10-03"), use(4, "loyalty_tier", traveler_id="T-1001")]
out = lab.run_tools(services, reads, lab.RunState())
span = analyse(services.events, services.ledger())["read_phase_span_s"]
total = sum(scenario["latency_s"][r.name] for r in reads) * SCALE
check([r["tool_use_id"] for r in out] == [r.id for r in reads] and not any(r.get("is_error") for r in out),
      "TODO B: four reads return four results, in request order, ids matching")
check(span is not None and span < 0.7 * total, "TODO B: independent reads ran concurrently (total time close to the slowest read, not the sum)",
      f"{span}s vs {total:.2f}s if one at a time")

services, state = TravelServices(scenario, latency_scale=SCALE), lab.RunState()
batch = [use(10, "rebook_flight", pnr=pnr, option_id=option),
         use(11, "book_hotel", hotel_id=hotel, rebook_ref="RB-0001", nights=1, guest="Ana"),
         use(12, "notify_traveler", traveler_id="T-1001", rebook_ref="RB-0001", hotel_ref="HB-0001")]
out = lab.run_tools(services, batch, state)
facts = analyse(services.events, services.ledger())
check(out[1].get("is_error") and out[2].get("is_error") and facts["hotel_bookings"] == 0 and facts["notifications"] == 0 and facts["unverified_entries"] == 0,
      "TODO B: dependent writes sent in the same batch as the rebooking are blocked (nothing booked on an unconfirmed reference)")
check(body(out[1]).get("error") in ("PREREQUISITE_NOT_MET", "UNKNOWN_REFERENCE") and body(out[1]).get("hint"),
      "TODO B: a blocked call returns a structured error (PREREQUISITE_NOT_MET or UNKNOWN_REFERENCE) with a hint")
check(not facts["writes_overlap"] and not facts["order_violations"], "TODO B: writes never overlapped and never started before their prerequisite")

first = body(out[0])
check(out[0].get("is_error") and first.get("outcome_unknown") is True and first.get("retryable") is True and first.get("hint"),
      "TODO C2: the timed-out rebooking returns a structured error (outcome_unknown, retryable, hint)", str(out[0]["content"])[:70])
retry = lab.run_tools(services, [use(13, "rebook_flight", pnr=pnr, option_id=option)], state)
facts = analyse(services.events, services.ledger())
check(not retry[0].get("is_error") and facts["rebookings"] == 1 and facts["replays"] >= 1,
      "TODO C1: retrying the identical rebooking is replayed, not repeated (exactly 1 rebooking in the ledger)", f"rebookings={facts['rebookings']}")
later = lab.run_tools(services, [use(14, "book_hotel", hotel_id=hotel, rebook_ref=body(retry[0]).get("ref", "?"), nights=1, guest="Ana")], state)
check(not later[0].get("is_error"), "TODO B: once the rebooking is confirmed, the hotel booking with the real reference goes through")


def reply(stop_reason, *blocks):
    return SimpleNamespace(stop_reason=stop_reason, content=list(blocks), usage=None)


runaway_calls = []


def runaway(messages, **kw):
    runaway_calls.append(1)
    if len(runaway_calls) > 15:  # safety net so a loop WITHOUT a bound cannot hang this check
        raise RuntimeError("model called more than 15 times: the loop is not bounded")
    return reply("tool_use", use(len(messages), "flight_status", flight_no="XA482"))


calls = []


def two_then_done(messages, **kw):
    calls.append(list(messages))
    if len(calls) == 1:
        return reply("tool_use", use(20, "flight_status", flight_no="XA482"), use(21, "loyalty_tier", traveler_id="T-1001"))
    return reply("end_turn", SimpleNamespace(type="text", text="done"))


try:
    loop = lab.run_agent(runaway, TravelServices(scenario, latency_scale=0), "go", max_turns=3)
except RuntimeError as error:
    loop = {"stopped": str(error), "turns": "unbounded"}
check(loop["stopped"] == "max_turns" and loop["turns"] == 3, "TODO D: a model that never stops is cut off at max_turns", f"turns={loop['turns']} stopped={loop['stopped']}")
lab.run_agent(two_then_done, TravelServices(scenario, latency_scale=0), "go")
last = calls[1][-1] if len(calls) > 1 else {}
check(last.get("role") == "user" and isinstance(last.get("content"), list) and [b["tool_use_id"] for b in last["content"]] == ["toolu_20", "toolu_21"],
      "TODO A: both results of one assistant turn go back in ONE user message, ids matching")

evidence_file = lab.EVIDENCE_FILE
if not evidence_file.exists():
    print("\n(Part B skipped: run `python lab.py` first)")
    print(f"RESULT: {sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

print("\n== Part B: your real run with Claude (evidence.json) ==")
evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
analysis, run = evidence["analysis"], evidence["result"]
check(run["stopped"] == "end_turn", "the run finished with end_turn (not max_turns)", run["stopped"])
check(analysis["rebookings"] == 1 and analysis["hotel_bookings"] == 1 and analysis["notifications"] == 1, "exactly one rebooking, one hotel booking and one notification",
      f"{analysis['rebookings']}/{analysis['hotel_bookings']}/{analysis['notifications']}")
check(analysis["unverified_entries"] == 0 and not analysis["order_violations"] and not analysis["writes_overlap"], "no write used an unconfirmed reference and none overlapped")
used = {r["tool"] for r in run["tool_results"]}
check({"flight_status", "rebooking_options", "hotel_availability", "loyalty_tier"} <= used, "Claude used all four read tools (including your loyalty_tier)", str(sorted(used)))
print("info: stop_reason sequence:", [t["stop_reason"] for t in run["trace"]])

print(f"RESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
