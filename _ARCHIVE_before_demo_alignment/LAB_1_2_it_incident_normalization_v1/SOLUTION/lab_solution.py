"""LAB 1.2 - IT incident normalization: evolve a prompt and a schema, and MEASURE every change.

Run:   python lab.py [--model fast|balanced] [--compare-balanced]       (needs an API key)
Check: python check.py
Lint:  python schema_lint.py versions/v1.schema.json                    (offline, no key)

A "version" is a pair of files in versions/: vN.prompt.txt and vN.schema.json. You write v1..v4 and add each
one to the VERSIONS list below. This file runs every version on 30 tickets, scores 7 fields per ticket, then
attacks the first and the last version with 5 hostile tickets (data/break_it.jsonl).

Your code changes here are the three TODOs. Most of your work is in the versions/ folder (see README).
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import re

import anthropic
from jsonschema import validators

from schema_lint import lint

HERE = pathlib.Path(__file__).parent
DATA = HERE / "data"
EVIDENCE = HERE / "evidence"

MAX_TOKENS = 2048          # on Sonnet/Opus 5.5 this also covers hidden thinking tokens
MAX_TICKET_CHARS = 2000    # cost cap per ticket; HOW you trim matters (see prepare_text)
FIELDS = ["severity", "category", "affected_systems", "impact.users_affected", "impact.business_unit", "reported_at", "needs_followup"]
MISSING = "<MISSING>"

# Add one line per version you create:  (name, prompt file, schema file). A later version may reuse an earlier schema file.
VERSIONS = [
    ("v0", "versions/v0.prompt.txt", "versions/v0.schema.json"),
    ("v1", "versions/v1.prompt.txt", "versions/v1.schema.json"),
    ("v2", "versions/v2.prompt.txt", "versions/v2.schema.json"),
    ("v3", "versions/v3.prompt.txt", "versions/v3.schema.json"),
    ("v4", "versions/v4.prompt.txt", "versions/v4.schema.json"),
]

TARGET = json.loads((DATA / "target_schema.json").read_text(encoding="utf-8"))  # the downstream contract


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ----------------------------------------------------------------------------------------------
# YOUR TODOs 1 and 2 (do them after BREAK_IT cases B1 and B5)
# ----------------------------------------------------------------------------------------------
def prepare_text(text):
    """TODO 2: this keeps only the HEAD of a long ticket. In a log-heavy ticket the real incident is often the
    last paragraph. Keep the head AND the tail, and tell the model that part of the middle was omitted."""
    if len(text) <= MAX_TICKET_CHARS:
        return text
    half = MAX_TICKET_CHARS // 2
    return text[:half] + "\n[... middle of the ticket omitted for length ...]\n" + text[-half:]


def render_user_message(ticket_id, text):
    """TODO 1: the ticket text is pasted raw next to the instructions. Wrap it as
    <ticket id="...">...</ticket> and make your v4 prompt say that tag content is untrusted data, not instructions."""
    return f'<ticket id="{ticket_id}">\n{prepare_text(text)}\n</ticket>'


# ----------------------------------------------------------------------------------------------
# The Claude call (provided). output_config.format asks Claude for JSON that matches the schema.
# Note: no temperature - this SDK has no such option.
# ----------------------------------------------------------------------------------------------
def call_claude(model, system_prompt, schema, ticket_id, text):
    from claude_client import ask  # imported here so schema_lint and check.py work without an API key
    return ask([{"role": "user", "content": render_user_message(ticket_id, text)}],
               system=system_prompt, model=model, max_tokens=MAX_TOKENS,
               output_config={"format": {"type": "json_schema", "schema": schema}})


def parse_reply(response):
    """Return (parsed_json_or_None, reason)."""
    if response.stop_reason != "end_turn":
        return None, f"stop_reason={response.stop_reason}"
    text = "".join(block.text for block in response.content if block.type == "text")
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text), "ok"
    except json.JSONDecodeError as error:
        return None, f"invalid JSON: {error.msg}"


def schema_errors(prediction, schema):
    return list(validators.validator_for(schema)(schema).iter_errors(prediction))


# ----------------------------------------------------------------------------------------------
# Scoring (provided): compare 7 fields against the ground truth.
# ----------------------------------------------------------------------------------------------
def flatten(obj):
    def get(mapping, key):
        return mapping.get(key, MISSING) if isinstance(mapping, dict) else MISSING

    impact = get(obj, "impact")
    return {"severity": get(obj, "severity"), "category": get(obj, "category"), "affected_systems": get(obj, "affected_systems"),
            "impact.users_affected": get(impact, "users_affected"), "impact.business_unit": get(impact, "business_unit"),
            "reported_at": get(obj, "reported_at"), "needs_followup": get(obj, "needs_followup")}


def to_utc(value):
    if value is None or value == MISSING:
        return value
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(datetime.timezone.utc).isoformat()
    except ValueError:
        return f"<BAD:{value}>"


def same(field, got, want):
    if got == MISSING:
        return False
    if field == "reported_at":
        return to_utc(got) == to_utc(want)
    if field == "affected_systems":
        return isinstance(got, list) and sorted(map(str, got)) == sorted(want)
    return got == want


def score_ticket(prediction, truth):
    got, want = flatten(prediction), flatten(truth)
    return {field: same(field, got[field], want[field]) for field in FIELDS}


# ----------------------------------------------------------------------------------------------
# Running a version (provided)
# ----------------------------------------------------------------------------------------------
def read_version(name, prompt_file, schema_file):
    prompt = (HERE / prompt_file).read_text(encoding="utf-8").strip()
    schema = json.loads((HERE / schema_file).read_text(encoding="utf-8"))
    return {"version": name, "prompt": prompt, "schema": schema, "prompt_file": prompt_file, "schema_file": schema_file,
            "fingerprint": hashlib.sha256((prompt + json.dumps(schema, sort_keys=True)).encode()).hexdigest()[:16]}


def run_version(model, version, tickets):
    from claude_client import cost_usd
    entry = {"version": version["version"], "prompt_file": version["prompt_file"], "schema_file": version["schema_file"],
             "fingerprint": version["fingerprint"], "lint_issues": lint(version["schema"]), "rejected": None,
             "outputs": {}, "failures": []}
    hits = {field: 0 for field in FIELDS}
    compliant = 0
    cost = 0.0
    for ticket in tickets:
        try:
            response = call_claude(model, version["prompt"], version["schema"], ticket["id"], ticket["text"])
        except anthropic.BadRequestError as error:  # a bad schema is rejected by the API: that is a measured result
            entry["rejected"] = (getattr(error, "message", None) or str(error))[:300]
            break
        cost += cost_usd(response)
        prediction, reason = parse_reply(response)
        is_compliant = prediction is not None and not schema_errors(prediction, TARGET)
        compliant += is_compliant
        scores = score_ticket(prediction, ticket["truth"])
        for field in FIELDS:
            hits[field] += scores[field]
            if not scores[field]:
                entry["failures"].append({"version": version["version"], "ticket_id": ticket["id"], "field": field,
                                          "expected": flatten(ticket["truth"])[field], "got": flatten(prediction)[field]})
        entry["outputs"][ticket["id"]] = {"pred": prediction, "schema_valid": is_compliant, "reason": reason}
    count = len(tickets)
    rejected = entry["rejected"] is not None
    entry.update(
        field_accuracy={field: 0.0 if rejected else hits[field] / count for field in FIELDS},
        overall_field_accuracy=0.0 if rejected else sum(hits.values()) / (count * len(FIELDS)),
        schema_compliance=0.0 if rejected else compliant / count,
        failed_ids=[t["id"] for t in tickets] if rejected else sorted({f["ticket_id"] for f in entry["failures"]}),
        cost_usd=cost)
    if rejected:
        entry["failures"] = []
    return entry


def run_adversarial(model, version, cases):
    results = {}
    for case in cases:
        try:
            response = call_claude(model, version["prompt"], version["schema"], case["id"], case["text"])
        except anthropic.BadRequestError as error:
            results[case["id"]] = {"pass": False, "reason": "request rejected: " + str(error)[:120], "pred": None, "kind": case["kind"]}
            continue
        prediction, _ = parse_reply(response)
        problems = []
        if prediction is None or schema_errors(prediction, TARGET):
            problems.append("not schema-valid")
        else:
            got = flatten(prediction)
            for key, value in case["expect"].items():
                wanted = {f"impact.{k}": v for k, v in value.items()} if key == "impact" else {key: value}
                for field, want in wanted.items():
                    if not same(field, got[field], want):
                        problems.append(f"{field}: expected {want!r}, got {got[field]!r}")
        results[case["id"]] = {"pass": not problems, "reason": "; ".join(problems) or "ok", "pred": prediction, "kind": case["kind"]}
    return results


def write_failed_cases(version_entries):
    """TODO 3: write evidence/failed_cases.json as
    {"failed_cases": [every item of entry["failures"] for every version entry], "rejected_versions": {version: message}}.
    check.py compares this file with the stored outputs."""
    failed_cases = [failure for entry in version_entries for failure in entry["failures"]]
    rejected = {entry["version"]: entry["rejected"] for entry in version_entries if entry["rejected"]}
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "failed_cases.json").write_text(json.dumps({"failed_cases": failed_cases, "rejected_versions": rejected}, indent=2), encoding="utf-8")


def main():
    from claude_client import MODEL_BALANCED, MODEL_FAST

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="fast", choices=["fast", "balanced"])
    parser.add_argument("--compare-balanced", action="store_true", help="also run the latest version on the balanced model")
    args = parser.parse_args()
    model = MODEL_FAST if args.model == "fast" else MODEL_BALANCED
    print(f"model: {model}")

    tickets = load_jsonl(DATA / "tickets.jsonl")
    cases = load_jsonl(DATA / "break_it.jsonl")
    versions = [read_version(*spec) for spec in VERSIONS]

    entries, adversarial = [], {}
    print(f"\n{'ver':<5}{'overall':>9}{'compl.':>8}{'lint':>6}  note")
    for version in versions:
        entry = run_version(model, version, tickets)
        entries.append(entry)
        note = "REJECTED by API: " + entry["rejected"][:70] if entry["rejected"] else f"failed tickets: {len(entry['failed_ids'])}"
        print(f"{entry['version']:<5}{entry['overall_field_accuracy']:>9.3f}{entry['schema_compliance']:>8.2f}{len(entry['lint_issues']):>6}  {note}")

    first_accepted = next((v for v, e in zip(versions, entries) if not e["rejected"]), None)
    picks = [first_accepted] if first_accepted else []
    if versions[-1] not in picks:
        picks.append(versions[-1])
    for version in picks:  # attack the first working version and the latest one
        adversarial[version["version"]] = run_adversarial(model, version, cases)
        passed = sum(r["pass"] for r in adversarial[version["version"]].values())
        print(f"BREAK_IT {version['version']}: {passed}/{len(cases)} pass")

    final_balanced = None
    if args.compare_balanced:
        entry = run_version(MODEL_BALANCED, versions[-1], tickets)
        final_balanced = {k: entry[k] for k in ("version", "overall_field_accuracy", "schema_compliance", "cost_usd", "failed_ids")}
        print(f"final version on balanced model: accuracy {entry['overall_field_accuracy']:.3f}  cost ${entry['cost_usd']:.4f}")

    write_failed_cases(entries)
    final = versions[-1]
    EVIDENCE.mkdir(exist_ok=True)
    (EVIDENCE / "evidence.json").write_text(json.dumps({
        "model": model, "n_tickets": len(tickets), "versions": entries, "adversarial": adversarial,
        "final_version": final["version"], "final_schema_file": final["schema_file"], "final_prompt_file": final["prompt_file"],
        "final_balanced": final_balanced, "spent_usd": round(sum(e["cost_usd"] for e in entries), 6),
    }, indent=2), encoding="utf-8")
    print("\nsaved evidence/evidence.json - now run: python check.py")


if __name__ == "__main__":
    main()
