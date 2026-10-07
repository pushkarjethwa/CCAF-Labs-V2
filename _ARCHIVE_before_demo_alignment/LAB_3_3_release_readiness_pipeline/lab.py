"""Lab 3.3 - Release readiness pipeline: classify the error, then recover the way that class deserves.

A release goes through four stages:   EXTRACT (Claude) -> ENRICH (tools) -> ASSESS (rules) -> REPORT (code)
Things break. A bad model answer, a tool that returns nothing, a service that is down. The wrong response
(retry everything, trust any cache, ship on empty data) causes bad release decisions. YOU write the six small
decisions; the loops, bookkeeping and the real Claude call are given.

WHERE THINGS ARE (this one file)
  Section 0  vocabulary         read it, do not edit
  Section 1  VALIDATE           TODO 1, TODO 2   is a stage's output fit to pass on?
  Section 2  CLASSIFY           TODO 3           which kind of error is this?
  Section 3  RECOVER            TODO 4, 5, 6     what do we do about it?
  Section 4  plumbing           do not edit      mock tools, real Claude call, the loops that call YOUR functions

HOW TO WORK
  python check.py     tests YOUR functions with hand-made inputs. No API key. Run it after every TODO.
  python lab.py       runs 8 scenarios; Claude does the real EXTRACT step. Needs ANTHROPIC_API_KEY.
  python check.py     now also checks the scenario results.
The starter is deliberately naive (accepts everything, retries everything, trusts any cache). Run it once first and read what it does.
"""
import argparse
import json
import pathlib
import sys

from claude_client import ask, text_of

# ======================================================================================
# SECTION 0 - VOCABULARY (read, do not edit)
# ======================================================================================
CATEGORIES = ["db_migration", "config_change", "bugfix", "feature", "dependency_bump"]
RISKS = ["low", "medium", "high"]
MAX_CORRECTIONS = 2        # corrective re-asks of the model before a human takes over
MAX_ENV_ATTEMPTS = 4       # tries (first try included) against a failing service before giving up
RUNAWAY_LIMIT = 6          # safety net: the loops below stop any policy that never stops retrying


class ToolError(Exception):
    """A tool failed. status 404/422 = the call or result was wrong; 408/429/5xx = the service is struggling.
    hint is a dict the tool may give you, e.g. {"expected_id": "REL-2041"}."""

    def __init__(self, code, status, message, hint=None):
        super().__init__(f"{status} {code}: {message}")
        self.code, self.status, self.message, self.hint = code, status, message, hint or {}


class StageValidationError(Exception):
    """A stage's output is not fit to pass on. stage is "extract" or "enrich"; rule is a short name; message says what is wrong."""

    def __init__(self, stage, rule, message):
        super().__init__(f"[{stage}/{rule}] {message}")
        self.stage, self.rule, self.message = stage, rule, message


# ======================================================================================
# SECTION 1 - VALIDATE: check every stage's output before the next stage trusts it
# ======================================================================================
def validate_extract(out, tickets):
    """TODO 1. `out` is the model's answer: {"items": [{"ticket_id", "category", "risk"}, ...]}; `tickets` is the list we asked about.
    Raise StageValidationError("extract", <rule>, <message>) if ANY of these is wrong:
      no items | an unknown ticket_id | a ticket missing or listed twice | category not in CATEGORIES | risk not in RISKS.
    The message goes straight back to the model, so make it say exactly what is wrong. Return nothing when all is fine."""
    pass  # the starter accepts anything the model says


def validate_enrich(enrich):
    """TODO 2. `enrich` is {"ci": {...}, "deps": {...}, "oncall": {...}} from three tools. Raise StageValidationError("enrich", ...) if:
      the CI record is empty or has no "pipeline_status" | deps lacks "critical" or "high" | oncall has no "primary".
    A tool that answers with an empty record has not failed loudly, so nothing else would notice."""
    pass  # the starter accepts anything the tools say


# ======================================================================================
# SECTION 2 - CLASSIFY: three kinds of error, three different recoveries
# ======================================================================================
def classify(exc):
    """TODO 3. Return "reasoning", "tool", "environment" or "unknown".
      StageValidationError from "extract"   -> reasoning     (the MODEL broke a rule)
      StageValidationError from "enrich"    -> tool          (a tool answered with something unusable)
      ToolError with status >= 500, 408 or 429 -> environment (the service is struggling; not our fault)
      any other ToolError                   -> tool
      anything else                         -> unknown
    Decide from the type and the status code, never from the message text."""
    return "unknown"  # the starter cannot tell errors apart


# ======================================================================================
# SECTION 3 - RECOVER: the policy
# ======================================================================================
def backoff_delay(tries):
    """TODO 4. Seconds to wait after the `tries`-th failed try (1 = the first try just failed): 0.5, then 1.0, then 2.0 (doubling)."""
    return 0.0  # the starter hammers a struggling service with no pause


def cache_is_usable(cache, release):
    """TODO 5. `cache` is an older dependency-scan result (or None); `release` has a "version". A cache is usable ONLY if it was
    taken for this exact version: cache["for_version"] == release["version"]. Evidence about version 3.0.4 says nothing about 3.1.0."""
    return cache is not None  # the starter trusts any cache


def decide_recovery(error_class, tries, hint, cache_ok):
    """TODO 6. The whole recovery policy in one place. Return exactly one of:
         "corrective_reprompt" | "retry_changed_args" | "backoff_retry" | "fallback_cache" | "pause_alert" | "escalate"
    error_class  from classify()          tries  how many tries so far for this step (1 = the first try just failed)
    hint         the tool's hint dict or None            cache_ok  True if cache_is_usable() said yes (environment errors only)

      reasoning    -> "corrective_reprompt" while tries <= MAX_CORRECTIONS, then "escalate" (the model keeps failing: a human decides)
      tool         -> "retry_changed_args" ONCE (tries == 1) if the tool gave a hint, otherwise "escalate"
                      (an unusable answer will not improve if you ask the same thing again)
      environment  -> "backoff_retry" while tries < MAX_ENV_ATTEMPTS; then "fallback_cache" if cache_ok, else "pause_alert"
      anything else -> "escalate"
    Every path must be bounded."""
    return "backoff_retry"  # the starter retries everything, whatever went wrong


# ======================================================================================
# SECTION 4 - PLUMBING (do not edit). You never need to read this to finish the lab.
#   mock tools + fault injection | the real Claude EXTRACT call | assess and report | run_release() | the 8 scenarios
# ======================================================================================
HERE = pathlib.Path(__file__).parent
DATA = json.loads((HERE / "data.json").read_text(encoding="utf-8"))
RESULTS_FILE = HERE / "results" / "scenarios.json"
INVALID_CATEGORY = "schema_change"   # plausible-sounding, not in CATEGORIES

# The eight scenarios. extract_fault is injected into Claude's reply; tool_faults are injected into the mock tools.
SCENARIOS = [
    {"id": "F0", "release": "REL-2045", "extract_fault": None, "tool_faults": [], "label": "no fault (baseline)"},
    {"id": "F1", "release": "REL-2041", "extract_fault": None, "tool_faults": [{"tool": "ci_results", "mode": "lowercase_id_once"}],
     "label": "TOOL: first CI call uses a sloppy id; the error carries a hint"},
    {"id": "F2", "release": "REL-2043", "extract_fault": None, "tool_faults": [{"tool": "ci_results", "mode": "empty"}],
     "label": "TOOL: CI returns an empty record"},
    {"id": "F3", "release": "REL-2041", "extract_fault": "fixable", "tool_faults": [],
     "label": "REASONING: the model's first answer invents a category (it fixes it when corrected)"},
    {"id": "F4", "release": "REL-2043", "extract_fault": "stubborn", "tool_faults": [],
     "label": "REASONING: every model answer invents a category"},
    {"id": "F5", "release": "REL-2041", "extract_fault": None, "tool_faults": [{"tool": "dependency_scan", "mode": "transient", "failures": 2}],
     "label": "ENVIRONMENT: the scanner times out twice, then recovers"},
    {"id": "F6", "release": "REL-2043", "extract_fault": None, "tool_faults": [{"tool": "dependency_scan", "mode": "outage"}],
     "label": "ENVIRONMENT: scanner down, the cache matches the release version"},
    {"id": "F7", "release": "REL-2044", "extract_fault": None, "tool_faults": [{"tool": "dependency_scan", "mode": "outage"}],
     "label": "ENVIRONMENT: scanner down, the cache is for an OLDER version"},
]


class SimClock:
    """Time is simulated: sleep() records the wait instead of waiting, so backoff is instant but visible."""

    def __init__(self):
        self.sleeps = []

    def sleep(self, seconds):
        self.sleeps.append(round(seconds, 3))


class Tools:
    """Read-only mock systems with fault injection. Every failure is a ToolError (or ToolOutage, a 503)."""

    def __init__(self, faults=None):
        self.faults, self.calls, self.clock = faults or [], {}, SimClock()

    def _fault(self, tool):
        return next((f for f in self.faults if f["tool"] == tool), None)

    def _count(self, tool):
        self.calls[tool] = self.calls.get(tool, 0) + 1
        return self.calls[tool]

    def release(self, release_id):
        return next(r for r in DATA["releases"] if r["release_id"] == release_id)

    def tickets(self, release_id):
        return DATA["tickets"][release_id]

    def ci_results(self, release_id):
        n, fault = self._count("ci_results"), self._fault("ci_results")
        if fault and fault["mode"] == "lowercase_id_once" and n == 1:
            release_id = release_id.lower()  # the first call goes out with a sloppy id
        if release_id not in DATA["ci"]:
            raise ToolError("E_NOT_FOUND", 404, f"no CI record for {release_id!r}", {"expected_id": release_id.upper()})
        return {} if fault and fault["mode"] == "empty" else DATA["ci"][release_id]

    def dependency_scan(self, release_id):
        n, fault = self._count("dependency_scan"), self._fault("dependency_scan")
        if fault and (fault["mode"] == "outage" or (fault["mode"] == "transient" and n <= fault.get("failures", 2))):
            raise ToolError("E_UNAVAILABLE", 503, "dependency_scan backend unavailable")
        return DATA["deps"][release_id]

    def dependency_scan_cache(self, release_id):
        return DATA["deps_cache"].get(release_id)

    def oncall(self, team):
        return DATA["oncall"][team]


EXTRACT_SYSTEM = (f"You review engineering change tickets before a release. For each ticket give its category (one of {CATEGORIES}) "
                  f"and its risk (one of {RISKS}). Reply with JSON only: "
                  '{"items": [{"ticket_id": "...", "category": "...", "risk": "..."}]}. If you are given a CORRECTION, fix exactly what it says.')


def extract_with_model(tickets, feedback=None):
    """The real Claude call for the EXTRACT stage. API trouble (429, 5xx) becomes a ToolError, so YOUR classify() handles it too."""
    request = json.dumps([{k: t[k] for k in ("ticket_id", "title", "description")} for t in tickets], indent=1)
    try:
        text = text_of(ask([{"role": "user", "content": request + (f"\n\n{feedback}" if feedback else "")}], system=EXTRACT_SYSTEM, max_tokens=4096))
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        if status:
            raise ToolError("E_MODEL_API", status, str(exc)[:120]) from exc
        raise
    start, end = text.find("{"), text.rfind("}")
    try:
        parsed = json.loads(text[start:end + 1])
        return parsed if isinstance(parsed, dict) else {}
    except ValueError:
        return {}  # unreadable reply: your validator will see an empty answer


def make_extract_fn(fault, log):
    """Wraps the real model. fixable/stubborn INJECT a bad category into the reply, to simulate a model that slips."""
    def extract(tickets, feedback):
        out = extract_with_model(tickets, feedback)
        corrected = (feedback or "").startswith("CORRECTION")
        items = out.get("items")
        if isinstance(items, list) and items and isinstance(items[0], dict) and (fault == "stubborn" or (fault == "fixable" and not corrected)):
            items[0]["category"] = INVALID_CATEGORY
            log(f"    [injected fault] the first ticket's category was replaced by {INVALID_CATEGORY!r}")
        return out
    return extract


def assess(extract_out, enrich_out):
    """Deterministic rules. A degraded (cache) evidence base can never produce a clean 'go'."""
    ci, deps = enrich_out.get("ci") or {}, enrich_out.get("deps") or {}
    categories = {i.get("category") for i in extract_out.get("items", [])}
    reasons = []
    if ci.get("pipeline_status") != "passed":
        reasons.append(f"CI {ci.get('pipeline_status', 'missing')}")
    if deps.get("critical", 0) > 0:
        reasons.append(f"{deps['critical']} critical vulnerabilities")
    verdict = "no-go" if reasons else "go"
    if verdict == "go":
        if deps.get("high", 0) >= 2:
            reasons.append(f"{deps['high']} high vulnerabilities")
        if "db_migration" in categories:
            reasons.append("contains a database migration")
        if enrich_out.get("degraded"):
            reasons.append("dependency evidence is degraded (cache fallback)")
        verdict = "needs-review" if reasons else "go"
    return {"verdict": verdict, "reasons": reasons or ["all checks clean"]}


def report(release, assessment, enrich_out):
    oncall = (enrich_out.get("oncall") or {}).get("primary", {}).get("name", "unassigned")
    return f"{release['release_id']} {release['service']} {release['version']}: {assessment['verdict'].upper()} ({'; '.join(assessment['reasons'])}). On-call: {oncall}."


class _Stop(Exception):
    pass


def run_release(release_id, tools, extract_fn, log=print):
    """The pipeline. It calls YOUR validate_*, classify, decide_recovery, backoff_delay and cache_is_usable, and records what happened."""
    res = {"release_id": release_id, "outcome": None, "stage_failed": None, "error_class": None, "recovery": None, "attempts": 1,
           "corrections": 0, "backoff_sleeps": [], "alerts": [], "stages_run": [], "verdict": None, "report": None, "degraded": False}
    release, tickets = tools.release(release_id), tools.tickets(release_id)

    def note(stage, error_class, action, attempts, why):
        res.update(stage_failed=stage, error_class=error_class, recovery=action, attempts=attempts)
        log(f"    {stage}: {error_class} error -> {action} ({why})")

    def give_up(stage, error_class, action, tries, why):
        """escalate / pause_alert / anything we cannot retry: the run ends here."""
        outcome = "paused" if action == "pause_alert" else "escalated"
        if action == "pause_alert":
            res["alerts"].append(f"{stage}: {why}")
        note(stage, error_class, action, tries, why)
        raise _Stop(outcome)

    def sleep_if_backoff(action, tries):
        if action == "backoff_retry":
            delay = backoff_delay(tries)
            tools.clock.sleep(delay)
            res["backoff_sleeps"].append(round(delay, 3))

    def runaway(stage, tries):
        if tries > RUNAWAY_LIMIT:
            note(stage, "?", "runaway_stopped", tries, "the recovery policy never stopped retrying")
            raise _Stop("runaway_stopped")

    try:
        # ---- EXTRACT: Claude answers; we validate; failures are reasoning errors (or an API outage)
        feedback, tries = None, 0
        while True:
            tries += 1
            runaway("extract", tries)
            try:
                out = {**extract_fn(tickets, feedback), "release_id": release_id}
                validate_extract(out, tickets)
                break
            except (StageValidationError, ToolError) as err:
                error_class = classify(err)
                action = decide_recovery(error_class, tries, getattr(err, "hint", None), False)
                why = err.message
                if action in ("escalate", "pause_alert", "fallback_cache"):
                    give_up("extract", error_class, "escalate" if action == "fallback_cache" else action, tries, why)
                res["corrections"] += action == "corrective_reprompt"
                note("extract", error_class, action, tries + 1, why)
                sleep_if_backoff(action, tries)
                feedback = f"CORRECTION {tries} of {MAX_CORRECTIONS}: {why}. Allowed categories: {CATEGORIES}." if action == "corrective_reprompt" else None
        res["stages_run"].append("extract")

        # ---- ENRICH: three tools, each retried the way its error class deserves
        enrich = {"degraded": False}

        def call_step(name, fn, arg):
            tries = 0
            while True:
                tries += 1
                runaway("enrich", tries)
                try:
                    return fn(arg)
                except ToolError as err:
                    error_class = classify(err)
                    cache = tools.dependency_scan_cache(release_id) if name == "deps" else None
                    action = decide_recovery(error_class, tries, err.hint, cache_is_usable(cache, release))
                    why = f"{name}: {err.status} {err.code}"
                    if action == "fallback_cache" and cache:
                        enrich["degraded"] = res["degraded"] = True
                        note("enrich", error_class, action, tries, why + "; using the cached scan (degraded evidence)")
                        return {k: cache[k] for k in ("critical", "high", "medium")}
                    if action in ("escalate", "pause_alert", "fallback_cache"):
                        give_up("enrich", error_class, "pause_alert" if action == "fallback_cache" else action, tries, why)
                    note("enrich", error_class, action, tries + 1, why)
                    sleep_if_backoff(action, tries)
                    if action == "retry_changed_args" and err.hint.get("expected_id"):
                        arg = err.hint["expected_id"]

        enrich["ci"] = call_step("ci", tools.ci_results, release_id)
        enrich["oncall"] = call_step("oncall", tools.oncall, release["team"])
        enrich["deps"] = call_step("deps", tools.dependency_scan, release_id)
        try:
            validate_enrich(enrich)
        except StageValidationError as err:  # the tools answered, but with something unusable: stop the line
            error_class = classify(err)
            action = decide_recovery(error_class, 1, None, False)
            give_up("enrich", error_class, action, 1, err.message)
        res["stages_run"].append("enrich")

        # ---- ASSESS + REPORT: deterministic code, only reached with validated inputs
        assessment = assess(out, enrich)
        res["stages_run"].append("assess")
        res.update(verdict=assessment["verdict"], report=report(release, assessment, enrich), degraded=enrich["degraded"])
        res["stages_run"].append("report")
        res["outcome"] = "completed_degraded" if enrich["degraded"] else "completed"
    except _Stop as stop:
        res["outcome"] = str(stop)
    return res


def run_scenario(scenario, log=print):
    tools = Tools(scenario["tool_faults"])
    res = run_release(scenario["release"], tools, make_extract_fn(scenario["extract_fault"], log), log)
    return {"scenario_id": scenario["id"], "label": scenario["label"], **res}


def print_table(results):
    print(f"\n{'id':<4}{'release':<10}{'outcome':<20}{'stage':<9}{'class':<13}{'recovery':<21}{'att':>3}  verdict")
    for r in results:
        print(f"{r['scenario_id']:<4}{r['release_id']:<10}{r['outcome']:<20}{str(r['stage_failed']):<9}{str(r['error_class']):<13}"
              f"{str(r['recovery']):<21}{r['attempts']:>3}  {r['verdict']}" + (f"   waits {r['backoff_sleeps']}" if r["backoff_sleeps"] else "")
              + (f"   alerts {len(r['alerts'])}" if r["alerts"] else ""))


def main():
    parser = argparse.ArgumentParser(description="Run the release-readiness scenarios with a real Claude EXTRACT step.")
    parser.add_argument("--scenario", choices=[s["id"] for s in SCENARIOS], help="run just one scenario (default: all eight)")
    chosen = [s for s in SCENARIOS if s["id"] == parser.parse_args().scenario] if "--scenario" in sys.argv else SCENARIOS
    results = []
    for scenario in chosen:
        print(f"\n{scenario['id']} {scenario['release']}: {scenario['label']}")
        results.append(run_scenario(scenario))
        print(f"    => {results[-1]['outcome']}")
    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(results, indent=1), encoding="utf-8")
    print_table(results)
    print("\nSaved to results/scenarios.json. Now run: python check.py")


if __name__ == "__main__":
    main()
