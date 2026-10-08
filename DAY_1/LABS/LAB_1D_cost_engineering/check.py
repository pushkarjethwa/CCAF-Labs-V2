"""check.py - Part A tests your four TODOs with a scripted stand-in for Claude (no API key needed).
Part B checks the evidence that your stage runs saved in the evidence/ folder.

Exit code 0 = everything passed.
"""
import json
import pathlib

import cost_core as core
import lab

HERE = pathlib.Path(__file__).parent
EVIDENCE = HERE / "evidence"
results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f"\n         {detail}" if detail and not ok else ""))


class FakeClient:
    """Stands in for Claude. Records every request and returns fixed replies."""

    def __init__(self):
        self.calls = []
        self.counts = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return "scripted response"

    def count_tokens(self, *, model, system, messages, **extra):
        """Like the real endpoint: it does not accept max_tokens."""
        if "max_tokens" in extra:
            raise TypeError("count_tokens() got an unexpected keyword argument 'max_tokens'")
        self.counts.append({"model": model, "system": system, "messages": messages, **extra})
        return type("Counted", (), {"input_tokens": 1234})()


def attempt(function, *args):
    """Call a TODO function. If it is not written yet, say so instead of showing a traceback."""
    try:
        return function(*args)
    except NotImplementedError as exc:
        print(f"         ({exc})")
        return None


print("PART A - your code, tested with scripted data (no API key)\n")
request = {"model": "model-x", "max_tokens": 600, "system": [{"type": "text", "text": "policy"}],
           "messages": [{"role": "user", "content": "invoice"}], "output_config": {"format": core.VERDICT_FORMAT}}

print("TODO 1 - ask_checker: the Claude call")
fake = FakeClient()
lab.get_client = lambda: fake
got = attempt(lab.ask_checker, request)
call = fake.calls[0] if fake.calls else {}
check(got == "scripted response" and len(fake.calls) == 1, "makes exactly one Claude call and returns its response")
check(call.get("model") == "model-x" and call.get("max_tokens") == 600, "passes model and max_tokens", f"model={call.get('model')!r}, max_tokens={call.get('max_tokens')!r}")
check(call.get("system") == request["system"] and call.get("messages") == request["messages"], "passes the system blocks and the messages unchanged", f"keys sent: {sorted(call)}")
check(call.get("output_config") == request["output_config"], "passes output_config (the verdict schema)", f"output_config={call.get('output_config')!r}")

print("\nTODO 2 - count_request_tokens")
fake = FakeClient()
lab.get_client = lambda: fake
try:
    counted = attempt(lab.count_request_tokens, request)
    error = ""
except TypeError as exc:
    counted, error = None, str(exc)
check(counted == 1234, "returns the input_tokens that the counting endpoint reports", error or f"got {counted!r}")
sent = fake.counts[0] if fake.counts else {}
check(sent.get("model") == "model-x" and sent.get("system") == request["system"] and sent.get("messages") == request["messages"], "sends the model, the system blocks and the messages", f"sent {sorted(sent)}")
check(not error, "does not send max_tokens (this endpoint rejects it)", error)

print("\nTODO 3 - system_blocks: the cache breakpoint")
plain = attempt(lab.system_blocks, "policy text", False)
check(plain == [{"type": "text", "text": "policy text"}], "cache=False gives one plain text block, with no cache_control", f"got {plain!r}")
cached = attempt(lab.system_blocks, "policy text", True)
check(cached == [{"type": "text", "text": "policy text", "cache_control": {"type": "ephemeral"}}], "cache=True marks the block: cache_control={'type': 'ephemeral'}", f"got {cached!r}")
hour = attempt(lab.system_blocks, "policy text", True, "1h")
check(bool(hour) and hour[0].get("cache_control") == {"type": "ephemeral", "ttl": "1h"}, "cache=True with ttl='1h' adds 'ttl': '1h' inside cache_control", f"got {hour!r}")
check(bool(cached) and len(cached) == 1 and cached[0]["text"] == "policy text", "there is exactly one block and its text is unchanged")

print("\nTODO 4 - batch_requests and join_by_custom_id")
built = attempt(lab.batch_requests, ["INV-1", "INV-2"], [{"a": 1}, {"b": 2}])
check(built == [{"custom_id": "INV-1", "params": {"a": 1}}, {"custom_id": "INV-2", "params": {"b": 2}}], "batch_requests pairs each invoice id with its request", f"got {built!r}"[:140])


class Entry:
    def __init__(self, custom_id):
        self.custom_id = custom_id


entries = [Entry("INV-3"), Entry("INV-1"), Entry("INV-2")]
joined = attempt(lab.join_by_custom_id, entries)
check(isinstance(joined, dict) and set(joined) == {"INV-1", "INV-2", "INV-3"}, "join_by_custom_id returns a dict keyed by custom_id", f"got {joined!r}"[:140])
check(isinstance(joined, dict) and joined.get("INV-1") is entries[1] and joined.get("INV-3") is entries[0], "each key maps to its own entry, whatever the arrival order")

print("\nThe given plumbing (checks that the data and helpers are intact)")
invoices = core.load_invoices()
check(len(invoices) == 30 and len(core.lab_invoices(invoices)) == 10, "30 invoices; the lab uses 10 of them")
policy = core.load_policy("full")
check(len(policy) > 20000 and len(core.load_policy("lite")) < 12000, "the full policy is about 25,000 characters; the lite policy is short")
usage = type("U", (), {"input_tokens": 100, "cache_creation_input_tokens": 1000, "cache_read_input_tokens": 1000, "output_tokens": 50})()
cost = core.request_cost("claude-haiku-5-5", usage)
check(abs(cost - (100 * 1.0 + 1000 * 1.0 * 1.25 + 1000 * 1.0 * 0.1 + 50 * 5.0) / 1e6) < 1e-12, "the cost formula: cache write 1.25x, cache read 0.1x, output at the output price")
check(abs(core.request_cost("claude-haiku-5-5", usage, batch=True) - cost / 2) < 1e-12, "the batch discount is exactly 50%")
check(abs(core.breakeven_hit_rate("5m") - 0.25 / 1.15) < 1e-9 and abs(core.breakeven_hit_rate("1h") - 1.0 / 1.9) < 1e-9, "break-even hit rate: 22% for a 5-minute write, 53% for a 1-hour write")
a = {"system": [{"type": "text", "text": core.stamp() + "policy", "cache_control": {"type": "ephemeral"}}]}
b = {"system": [{"type": "text", "text": core.stamp() + "policy", "cache_control": {"type": "ephemeral"}}]}
identical, report = core.diff_prefixes(a, b)
check(not identical and "uuid" in report, "diff_prefixes finds a request id and a timestamp at the top of two consecutive prompts", report[:120])

print("\nPART B - the evidence your stage runs saved (needs `python lab.py --stage N` with a key)\n")


def load(name):
    path = EVIDENCE / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


ev = {n: load(f"stage{n}.json") for n in range(1, 5)}
if not any(ev.values()):
    print("[SKIP] no evidence yet - run `python lab.py --stage 1`, then 2, 3 and 4, then this again.")
elif not all(results):
    print("[SKIP] fix Part A first, then run the stages again.")
else:
    if ev[1]:
        check(ev[1]["requests"] >= 10 and ev[1]["parsed"] >= ev[1]["requests"] - 1, "stage 1: the invoices were checked and the verdicts parsed", f"{ev[1]['parsed']}/{ev[1]['requests']}")
        check(ev[1]["cache_read"] == 0, "stage 1: nothing was cached, so cache reads are 0 (this is the expensive baseline)")
        check(0 < ev[1]["monthly"]["fast"] < ev[1]["monthly"]["balanced"], "stage 1: the balanced model costs more per month than the fast one", str(ev[1]["monthly"]))
        print(f"       info: projected ${ev[1]['monthly']['fast']:,.0f} a month on the fast model, ${ev[1]['monthly']['balanced']:,.0f} on the balanced model")
    if ev[2]:
        d = {x["invoice_id"]: x for x in ev[2]["decisions"]}
        check(d["INV-2026-9999"]["allowed"] is False and d[next(i for i in d if i != "INV-2026-9999")]["allowed"] is True, "stage 2: the gate refuses the 60-page OCR dump and allows a normal invoice", str(ev[2]["decisions"]))
        check(min(ev[2]["counts"]) > 2000, "stage 2: a normal request is thousands of tokens (the policy is most of it)", f"smallest {min(ev[2]['counts'])}")
    if ev[3]:
        h, b, f = ev[3]["healthy"], ev[3]["broken"], ev[3]["fixed"]
        check(h["write_first"] > 0 and all(x > 0 for x in h["reads_after"]), "stage 3 A: the first request writes the cache and every later request reads it", str(h))
        check(b["cache_read_total"] == 0, "stage 3 B: with the stamp at the top, cache reads stay 0 although caching is switched on", str(b))
        check(not ev[3]["diff"]["identical"] and "inspect manually" not in ev[3]["diff"]["report"], "stage 3 C: the prefix diff names the volatile content", ev[3]["diff"]["report"][:160])
        check(f["reads"] >= f["requests"] - 2, "stage 3 D: after the fix, nearly every request reads the cache", f"{f['reads']}/{f['requests']}")
        check(f["cost"] < f["nocache_cost"], "stage 3 D: the fixed cache is cheaper than no cache", f"${f['cost']:.4f} vs ${f['nocache_cost']:.4f}")
    if ev[4]:
        check(ev[4]["joined_ok"], "stage 4: the join on custom_id is complete and every echoed invoice_id matches")
        check(ev[4]["positional_wrong"] >= 3, "stage 4: joining by position pairs several invoices with the wrong verdict when results arrive in another order", f"{ev[4]['positional_wrong']} wrong")
        c = ev[4]["cost"]
        print(f"       info: cost of the same invoices: normal ${c['normal']:.4f}, cached ${c['cached']:.4f}, batch+cache ${c['batch+cache']:.4f} (batch caching is best-effort)")

print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
raise SystemExit(0 if all(results) else 1)
