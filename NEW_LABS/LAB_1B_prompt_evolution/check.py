"""Run after the stages.   python check.py
Part A needs no API key: it tests the scorer, validators, schema audit and prompt vault.
Part B checks whichever evidence files exist (written by `python demo.py --stage N`).
It checks that the demo RAN CORRECTLY, not that the model scored well: model results vary by run and version.
Exit code 0 means every check passed."""
import json
import pathlib
import shutil
import sys
import tempfile

import evalkit as kit
import legacy_extractor
from vault import Vault

HERE = pathlib.Path(__file__).parent
EVIDENCE = HERE / "evidence"
results = []


def check(ok, description, detail=""):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}" + (f" ({detail})" if detail else ""))


def load(name):
    path = EVIDENCE / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


print("== Part A: scorer, validators, schema audit, vault (no API key) ==")
docs = kit.load_docs()
preds = {d.doc_id: legacy_extractor.extract(d.text) for d in docs}
legacy = kit.summarize([kit.score_doc(d.doc_id, preds[d.doc_id], d.truth, strict_parsed=True) for d in docs], {d.doc_id: d.truth for d in docs}, preds)
check(len(docs) == 12 and 0.38 <= legacy.accuracy <= 0.46, "legacy regex extractor scores about 42% (the bar)", f"{100 * legacy.accuracy:.1f}%")
check(kit.score_field("total", "$5.40", 5.40) == 0.0 and kit.score_field("total", 5.40, 5.40) == 1.0, "scorer: a string '$5.40' is wrong, the number 5.40 is right")
check(kit.score_field("po_number", "N/A", None) == 0.0 and kit.score_field("po_number", None, None) == 1.0, "scorer: a null truth needs JSON null, not 'N/A'")
check(kit.score_doc("D01", None, docs[0].truth).accuracy == 0.0, "scorer: an unparseable answer scores 0 on every field")
perfect = kit.score_doc("D01", dict(docs[0].truth), docs[0].truth, strict_parsed=True)
check(perfect.accuracy == 1.0, "scorer: the ground truth itself scores 100%")
check(kit.parse_response('```json\n{"a": 1}\n```').loose_ok and not kit.parse_response('```json\n{"a": 1}\n```').strict_ok, "parsing: a fenced answer parses loosely but fails strict json.loads")
check(not kit.parse_response("Here you go: nothing").loose_ok, "parsing: prose with no JSON does not parse")
bad = dict(docs[0].truth, total=docs[0].truth["total"] + 10)
check(kit.semantic_issues(docs[0].truth) == [] and any("subtotal + tax" in i.message for i in kit.semantic_issues(bad)), "semantic check: catches subtotal + tax != total with no ground truth")
check(kit.has_ambiguous_date("Date: 04/03/2025") and not kit.has_ambiguous_date("Date: 2025-03-04 and 13/03/2025"), "ambiguous-date detector: 04/03/2025 yes, 13/03/2025 no")
example_a = kit.load_examples()["ex_a_kestrel"][1]
check(len(kit.find_leaks("D10", {"po_number": example_a["po_number"]}, docs[9].truth, [("x", example_a)])) == 1, "leak check: an example PO number in an unrelated document is flagged")
schema = kit.load_schema()
check(kit.audit(schema)["ok"], "schema audit: the invoice schema meets the structured-output limits")
check(not kit.audit({"type": "object", "properties": {"t": {"type": ["number", "null"], "minimum": 0}}})["ok"], "schema audit: a type array, minimum and missing additionalProperties are all flagged")
check(Vault().verify().ok, "vault: every released prompt matches its recorded sha256")
with tempfile.TemporaryDirectory() as tmp:
    copy = pathlib.Path(tmp) / "prompts"
    shutil.copytree(HERE / "prompts", copy)
    (copy / "v6.md").write_text((copy / "v6.md").read_text(encoding="utf-8") + " ", encoding="utf-8")
    tampered = Vault(copy).verify()
    check(not tampered.ok and any("v6" in p for p in tampered.problems), "vault: adding one space to v6.md is detected as tampering")

found = [n for n in ("stage0.json", "stage1.json", "stage2.json", "stage3.json", "stage4.json", "stage5.json", "stage6.json", "vault.json", "gate.json") if (EVIDENCE / n).exists()]
if not found:
    print("\n(Part B skipped: run `python demo.py --stage 1` and later stages first)")
    print(f"RESULT: {sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)

print(f"\n== Part B: your runs ({', '.join(found)}) ==")
for name in ("stage1.json", "stage2.json", "stage3.json", "stage4.json", "stage5.json"):
    ev = load(name)
    if ev:
        check(all(len(r["per_doc"]) == 12 for r in ev["runs"]), f"{name}: every version was run on all 12 documents", ", ".join(f"{r['version']} {100 * r['accuracy']:.1f}%" for r in ev["runs"]))
s2 = load("stage2.json")
if s2:
    by_version = {r["version"]: r for r in s2["runs"]}
    print(f"       info: parse rate v0 {by_version['v0']['parse_rate']:.0%}, v3 {by_version['v3']['parse_rate']:.0%}; strict parse v3 {by_version['v3']['strict_parse_rate']:.0%}")
s3 = load("stage3.json")
if s3:
    print(f"       info: v4 leaks {s3['runs'][1]['leaks'] or 'none'}; documents regressed vs v3: {s3['regressed']} (strong models may show none)")
s5 = load("stage5.json")
if s5:
    check(s5["schema_audit_ok"], "stage 5: the schema passed the audit")
    v6 = s5["stats"]["v6"]
    check(v6["schema_valid"] >= 11, "stage 5: v6 returned schema-valid output for at least 11 of 12 documents", f"{v6['schema_valid']}/12")
    print(f"       info: D11 total without XML {s5['d11_total']['v6_no_xml']}, with XML {s5['d11_total']['v6']} (truth 1122.84)")
s6 = load("stage6.json")
if s6:
    p = s6["projection_usd_per_10k"]
    check(p["fast, batch (-50%)"] < p["fast, standard"] and p["balanced + cache + batch"] < p["balanced + cache (95% hit)"] < p["balanced, standard"], "stage 6: batch and caching each lower the projected cost", str({k: round(v, 2) for k, v in p.items()}))
    check(0.0 <= s6["cascade"]["escalation_rate"] <= 1.0, "stage 6: the cascade escalation rate was measured", f"{s6['cascade']['escalation_rate']:.0%}")
    print(f"       info: prefix tokens {s6['prefix_tokens']} (the fast model's cache floor is 4096)")
gate = load("gate.json")
if gate:
    check(set(gate["verdicts"]) == {"v7_reordered", "v7_trim_rules", "v7_extra_example"}, "gate: all three candidate edits were judged")
    print("       info: " + "; ".join(f"{n}: {'PASS' if v['passed'] else 'FAIL'} (designed {'PASS' if v['designed_to_pass'] else 'FAIL'})" for n, v in gate["verdicts"].items()))
print(f"RESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
