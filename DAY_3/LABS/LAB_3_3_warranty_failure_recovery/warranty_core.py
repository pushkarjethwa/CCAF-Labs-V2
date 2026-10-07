"""warranty_core.py - the warranty-claim intake agent and its fault injector (Demo 3C). DO NOT EDIT.

You do not need to read this file to finish the lab. It holds the mock warranty services, the fault injector, the resilient
executor (which uses YOUR classify, RECOVERY and corrective_message), the agent loop and the key-free chain. Everything you
write is in lab.py.
"""
import calendar
import datetime as dt
import json
import random
import re
from collections import Counter
from pathlib import Path

DATA = Path(__file__).parent / "data"


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


REGISTRY = load("registry.json")["registrations"]
TERMS = load("warranty_terms.json")
CASES = load("cases.json")
PLANS = load("fault_plans.json")
EXPECTED = load("chaos_expectations.json")["faults"]
STEPS = PLANS["steps"]


# ── 1. THE MOCK WARRANTY SERVICES ────────────────────────────────────────────
# Errors carry status_code / code / detail, like a real HTTP client's would, so the
# classifier can look at the code instead of parsing message strings.

class ServiceError(Exception):
    def __init__(self, status_code, code, message, detail=None):
        super().__init__(f"{status_code} {code}: {message}")
        self.status_code, self.code, self.message, self.detail = status_code, code, message, detail or {}


def unavailable():
    return ServiceError(503, "E_UNAVAILABLE", "upstream temporarily unavailable")


def timeout():
    return ServiceError(504, "E_TIMEOUT", "upstream did not answer in time")


def evaluate_terms(plan, purchase_date, issue_type, today):
    spec = TERMS["plans"][plan]
    start = dt.date.fromisoformat(purchase_date)
    year, month = divmod(start.month - 1 + spec["months"], 12)
    expires = dt.date(start.year + year, month + 1, min(start.day, calendar.monthrange(start.year + year, month + 1)[1]))
    if today > expires:
        return {"covered": False, "rule_id": TERMS["expired_rule_id"], "expires_on": str(expires)}
    if issue_type not in spec["covered"]:
        return {"covered": False, "rule_id": TERMS["excluded_rule_id"], "expires_on": str(expires)}
    return {"covered": True, "rule_id": spec["rule_id"], "expires_on": str(expires)}


class WarrantyServices:
    """The four real tools. Each raises ServiceError when the input is wrong."""

    def __init__(self):
        self.today = dt.date.fromisoformat(CASES["today"])
        self.claims = {}

    def lookup_product_registration(self, serial):
        if not isinstance(serial, str) or not re.fullmatch(r"[A-Z]{2}\d{8}", serial):
            raise ServiceError(422, "E_BAD_SERIAL_FORMAT", f"serial {serial!r} must be two capital letters then eight digits")
        if serial not in REGISTRY:
            raise ServiceError(404, "E_NOT_FOUND", f"no registration for {serial}")
        return {"serial": serial, **REGISTRY[serial]}

    def check_warranty_terms(self, serial, plan, issue_type):
        record = REGISTRY.get(serial)
        if record is None or plan != record["plan"]:
            raise ServiceError(422, "E_PLAN_MISMATCH", f"plan {plan!r} does not match the registration for {serial}")
        return {"serial": serial, "plan": plan, "issue_type": issue_type,
                **evaluate_terms(plan, record["purchase_date"], issue_type, self.today)}

    def create_claim(self, serial, issue_type, coverage_rule_id, customer_id):
        record = REGISTRY.get(serial)
        if record is None or record["customer_id"] != customer_id:
            raise ServiceError(422, "E_VALIDATION_FAILED", "serial and customer do not match")
        truth = evaluate_terms(record["plan"], record["purchase_date"], issue_type, self.today)
        if not truth["covered"] or truth["rule_id"] != coverage_rule_id:
            raise ServiceError(422, "E_COVERAGE_MISMATCH", f"rule {coverage_rule_id!r} is not what the warranty terms give for this claim")
        for claim in self.claims.values():  # idempotent: a retry after a timeout must not file twice
            if (claim["serial"], claim["issue_type"]) == (serial, issue_type):
                return dict(claim)
        number = f"WC-{100231 + len(self.claims):06d}"
        self.claims[number] = {"claim_number": number, "serial": serial, "issue_type": issue_type, "status": "filed"}
        return dict(self.claims[number])

    def schedule_pickup(self, claim_number, preferred_date, zone):
        if not isinstance(claim_number, str) or claim_number not in self.claims:
            raise ServiceError(422, "E_BAD_CLAIM_NUMBER", f"{claim_number!r} is not a filed claim (expected WC-nnnnnn)")
        return {"pickup_id": "PU-" + claim_number[3:], "claim_number": claim_number, "date": preferred_date, "zone": zone, "status": "scheduled"}


class FallbackServices:
    """Degraded-mode endpoints: separate systems, less reliable answers. They never touch the primary's faults."""

    def lookup_registration_cache(self, serial, **_):
        return {"serial": serial, **REGISTRY[serial], "stale": True}

    def terms_static_table(self, serial, plan, issue_type, **_):
        return {"serial": serial, "plan": plan, "issue_type": issue_type, "source": "static_table_unverified",
                **evaluate_terms(REGISTRY[serial]["plan"], REGISTRY[serial]["purchase_date"], issue_type, dt.date.fromisoformat(CASES["today"]))}

    def create_claim_draft(self, **_):
        return {"claim_number": None, "draft_id": "DR-0001", "status": "queued_for_manual_review"}

    def schedule_pickup_callback(self, claim_number=None, **_):
        return {"pickup_id": None, "claim_number": claim_number, "status": "callback_requested"}


FALLBACK_FOR = {"lookup_product_registration": "lookup_registration_cache", "check_warranty_terms": "terms_static_table",
                "create_claim": "create_claim_draft", "schedule_pickup": "schedule_pickup_callback"}


# ── 2. THE FAULT INJECTOR ────────────────────────────────────────────────────

class Injector:
    """Sits between the agent and the real services and breaks ONE step in the way the chosen fault says."""

    def __init__(self, fault, step, log=None):
        self.fault, self.step, self.log = fault, step, log
        self.mode = PLANS["faults"][fault]["mode"] if fault else None
        self.services, self.fallback = WarrantyServices(), FallbackServices()
        self.rng = random.Random(PLANS["seed"])
        self.attempts, self.poisoned = Counter(), 0   # primary calls per step; reasoning-poison counter

    def note(self, text):
        if self.log:
            self.log(text)

    def call(self, step, args):
        self.attempts[step] += 1
        n = self.attempts[step]
        if step == self.step:
            old, new = PLANS["drift_aliases"][step]
            if self.mode == "schema_drift":
                if old in args:
                    raise ServiceError(422, "E_ARG_RENAMED", f"unknown argument {old!r}; use {new!r}", {"renamed": {old: new}})
                args = {(old if key == new else key): value for key, value in args.items()}  # the new name is accepted
            elif self.mode == "hard_reject":
                if old in args:   # first the same hint as a drift...
                    raise ServiceError(422, "E_ARG_RENAMED", f"unknown argument {old!r}; use {new!r}", {"renamed": {old: new}})
                raise ServiceError(422, "E_SCHEMA_REJECTED", "payload rejected by schema v2, even with the new argument name")  # ...then no way through
            elif self.mode == "forbidden":
                raise ServiceError(403, "E_FORBIDDEN", "token lacks the scope required for this operation")
            elif self.mode == "transient" and n <= PLANS["faults"][self.fault]["failures"]:
                raise (unavailable() if self.rng.random() < 0.5 else timeout())
            elif self.mode == "outage":
                raise unavailable()
            elif self.mode == "mystery":
                raise RuntimeError("adapter returned a corrupt frame")
        try:
            result = getattr(self.services, step)(**args)
        except TypeError as exc:  # the model sent missing or extra arguments
            raise ServiceError(422, "E_BAD_ARGUMENTS", str(exc)) from exc
        if step == self.step == "check_warranty_terms" and self.mode in ("fixable", "stubborn"):
            self.poisoned += 1
            if self.mode == "stubborn" or self.poisoned == 1:  # a plausible but WRONG rule id reaches the model
                result = {**result, "rule_id": "R-CARE-COVER" if result["rule_id"] != "R-CARE-COVER" else "R-BASIC-DEFECT"}
                self.note(f"  [injector] check_warranty_terms now returns the wrong rule id {result['rule_id']}")
        return result


# ── THE RESILIENT EXECUTOR: classify each error, then apply the recovery YOUR table names ─────────────
# run(step, args) returns {"ok": True, "result": ..., "degraded": bool}
#                      or {"ok": False, "message": "...", "stop": None}  (the model may try again)
#                      or {"ok": False, "stop": "<final status>"}        (the run is over)

class ResilientExecutor:
    """`hooks` holds what you wrote in lab.py: classify, recovery (the RECOVERY table) and corrective_message."""
    name = "resilient"

    def __init__(self, injector, hooks, log=None):
        self.inj, self.hooks, self.log, self.alerts = injector, hooks, log or (lambda _: None), []
        self.degraded, self.virtual_seconds = False, 0.0
        self.reprompts, self.rng = Counter(), random.Random(PLANS["seed"] + 1)

    def run(self, step, args):
        if self.degraded:  # once any step used an unverified endpoint, do not mix verified and unverified data
            return self._fallback(step, args, "already in degraded mode")
        try:
            return self._ok(self.inj.call(step, args))
        except Exception as exc:
            kind = self.hooks["classify"](exc)
            action, limit = self.hooks["recovery"].get(kind, ("escalate", 0))
            self.log(f"  [{step}] failed: {exc}  -> class={kind}, action={action}")
            return getattr(self, "_" + action, self._escalate)(step, args, exc, limit)

    def _ok(self, result):
        return {"ok": True, "result": result, "degraded": False}

    def _fallback(self, step, args, why):
        self.degraded = True
        self.log(f"  [{step}] fallback endpoint ({why}); result is marked degraded")
        return {"ok": True, "result": getattr(self.inj.fallback, FALLBACK_FOR[step])(**args), "degraded": True}

    def _retry_same_call(self, step, args, exc, limit):
        """The blanket retry: the same call again, whatever the error says."""
        for attempt in range(2, limit + 1):
            try:
                return self._ok(self.inj.call(step, args))
            except Exception as again:
                self.log(f"  [{step}] attempt {attempt} failed: {again}")
        return {"ok": False, "stop": "failed_retries_exhausted"}

    def _retry_renamed_then_fallback(self, step, args, exc, limit):
        renamed = getattr(exc, "detail", {}).get("renamed")
        if renamed:
            try:
                self.log(f"  [{step}] retry once with renamed argument {renamed}")
                return self._ok(self.inj.call(step, {renamed.get(key, key): value for key, value in args.items()}))
            except Exception as again:
                self.log(f"  [{step}] still failing: {again}")
        return self._fallback(step, args, "the tool contract is broken")

    def _backoff_then_breaker(self, step, args, exc, limit):
        for attempt in range(2, limit + 1):
            delay = 1.0 * 2 ** (attempt - 2) + self.rng.uniform(0, 0.5)   # exponential backoff + jitter, on a virtual clock
            self.virtual_seconds += delay
            self.log(f"  [{step}] wait {delay:.2f}s (simulated), attempt {attempt}")
            try:
                return self._ok(self.inj.call(step, args))
            except Exception as again:
                self.log(f"  [{step}] attempt {attempt} failed: {again}")
        service = f"{step} service"
        if service not in self.alerts:   # one alert per outage, not one per failed call
            self.alerts.append(service)
        self.log(f"  [{step}] circuit breaker OPEN: run paused, operator alerted once")
        return {"ok": False, "stop": "paused_alerted"}

    def _corrective_message(self, step, args, exc, limit):
        self.reprompts[step] += 1
        if self.reprompts[step] > limit:
            self.log(f"  [{step}] still wrong after {limit} corrections: escalate")
            return {"ok": False, "stop": "escalated"}
        return {"ok": False, "stop": None, "message": self.hooks["corrective_message"](exc)}

    def _escalate(self, step, args, exc, limit):
        return {"ok": False, "stop": "escalated"}


# ── THE AGENT (live) AND THE KEY-FREE CHAIN ─────────────────────────────────────────────────────────

TOOLS = [
    {"name": "lookup_product_registration", "description": "Look up a registration by canonical serial (two capital letters + eight digits, no spaces or hyphens).",
     "input_schema": {"type": "object", "properties": {"serial": {"type": "string"}}, "required": ["serial"]}},
    {"name": "check_warranty_terms", "description": "Check whether the issue is covered. Returns covered and the rule_id to cite.",
     "input_schema": {"type": "object", "properties": {"serial": {"type": "string"}, "plan": {"type": "string"}, "issue_type": {"type": "string"}},
                      "required": ["serial", "plan", "issue_type"]}},
    {"name": "create_claim", "description": "File the claim. coverage_rule_id must be the rule_id from check_warranty_terms.",
     "input_schema": {"type": "object", "properties": {"serial": {"type": "string"}, "issue_type": {"type": "string"},
                      "coverage_rule_id": {"type": "string"}, "customer_id": {"type": "string"}},
                      "required": ["serial", "issue_type", "coverage_rule_id", "customer_id"]}},
    {"name": "schedule_pickup", "description": "Schedule a pickup for a filed claim (claim_number looks like WC-100231).",
     "input_schema": {"type": "object", "properties": {"claim_number": {"type": "string"}, "preferred_date": {"type": "string"}, "zone": {"type": "string"}},
                      "required": ["claim_number", "preferred_date", "zone"]}},
]

AGENT_SYSTEM = ("You are a warranty-claim intake agent. For each request: 1) normalise the serial and look up the registration; "
                "2) check the warranty terms; 3) if covered, create the claim with the rule_id you were given; "
                "4) schedule the pickup. Use the tools, one step at a time. When the pickup is scheduled, reply with a one-line summary.")

AGENT_SYSTEM = ("You are a warranty-claim intake agent. For each request: 1) normalise the serial and look up the registration; "
                "2) check the warranty terms; 3) if covered, create the claim with the rule_id you were given; "
                "4) schedule the pickup. Use the tools, one step at a time. When the pickup is scheduled, reply with a one-line summary.")


def run_agent(hooks, case, fault, step, log=print):
    """The manual agent loop (Demo 3F, build 1). The model call is hooks["ask"], which you write in lab.py."""
    injector = Injector(fault, step, log=log)
    executor = ResilientExecutor(injector, hooks, log=log)
    form = case["form"]
    messages = [{"role": "user", "content": f"Customer request: {case['message']}\nIntake form: {json.dumps(form)}"}]
    done, stop, turns = [], None, 0
    while stop is None and turns < 14:
        turns += 1
        response = hooks["ask"](messages)
        messages.append({"role": "assistant", "content": response.content})
        calls = [block for block in response.content if block.type == "tool_use"]
        if not calls:
            break
        results = []
        for block in calls:
            log(f"-> {block.name}({json.dumps(block.input)})")
            outcome = executor.run(block.name, block.input)
            if outcome["ok"]:
                done.append(block.name)
                text = json.dumps(outcome["result"]) + (" [DEGRADED: unverified source]" if outcome["degraded"] else "")
            else:
                stop = outcome.get("stop") or stop
                text = outcome.get("message", f"Run stopped: {outcome.get('stop')}")
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": text, "is_error": not outcome["ok"]})
            if stop:
                break
        messages.append({"role": "user", "content": results})
    if stop is None:
        stop = "completed" if "schedule_pickup" in done else "incomplete"
        stop = "completed_degraded" if stop == "completed" and executor.degraded else stop
    return {"status": stop, "steps_done": len(done), "faulted_step_attempts": injector.attempts[step],
            "primary_calls": sum(injector.attempts.values()), "alerts": executor.alerts}


def run_chain(hooks, fault, step, case=None):
    """The four steps with correct arguments and no model: tests the recovery layer on its own."""
    case = case or CASES["cases"][0]
    form = case["form"]
    injector = Injector(fault, step)
    executor = ResilientExecutor(injector, hooks)
    serial = re.sub(r"[^A-Za-z0-9]", "", form["serial_as_typed"]).upper()
    calls = [("lookup_product_registration", lambda r: {"serial": serial}),
             ("check_warranty_terms", lambda r: {"serial": serial, "plan": r[0]["plan"], "issue_type": form["issue_type"]}),
             ("create_claim", lambda r: {"serial": serial, "issue_type": form["issue_type"], "coverage_rule_id": r[1]["rule_id"], "customer_id": form["customer_id"]}),
             ("schedule_pickup", lambda r: {"claim_number": r[2]["claim_number"], "preferred_date": form["preferred_date"], "zone": form["zone"]})]
    results = []
    for name, build_args in calls:
        outcome = executor.run(name, build_args(results))
        if not outcome["ok"]:
            return outcome["stop"], injector.attempts[step], sum(injector.attempts.values())
        results.append(outcome["result"])
    return ("completed_degraded" if executor.degraded else "completed"), injector.attempts[step], sum(injector.attempts.values())
