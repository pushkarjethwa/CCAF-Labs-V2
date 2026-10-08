"""Lab 4.1 checker.   python check.py [--workdir STARTER]      (no API key, no Claude Code, no network)

Part A re-measures the repository you worked on: the files you created, the plan, the tests and the
acceptance script.  The lines under each stage turn to [PASS] as you finish it."""
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent

UNTOUCHED = {   # files the lab never edits: first 16 hex chars of the sha256
    "src/shipcalc/models.py": "f8d3fcf7eee1e717",
    "tests/test_packaging.py": "adc104df6a28e750",
    "tests/test_quote.py": "e4763a5028105b69",
    "tests/test_rates.py": "352dad83a2aabd54",
    "tests/test_units.py": "e5d99a983c2c0f81",
}
results = []


def check(ok, label, detail=""):
    results.append(bool(ok))
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", label, "  (%s)" % detail if detail and not ok else ""))


def read(path):
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def run_python(wd, args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    out = subprocess.run([sys.executable, "-B"] + args, cwd=str(wd), capture_output=True, text=True, env=env)
    text = out.stdout + out.stderr
    found = re.search(r"Ran (\d+) test", text)
    return (int(found.group(1)) if found else 0), out.returncode == 0


def raises_value_error(call):
    try:
        call()
    except ValueError as err:
        return str(err)
    except Exception:
        return None
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", default=str(HERE / "STARTER"))
    wd = pathlib.Path(parser.parse_args().workdir).resolve()
    print("Lab 4.1 - shipcalc: explore, plan, refactor   (checking %s)" % wd)

    print("Stage 1 - explore")
    claude_md = read(wd / "CLAUDE.md")
    agreement = claude_md.lower().split("working agreement")[-1] if "working agreement" in claude_md.lower() else ""
    bullets = [l for l in agreement.splitlines() if l.startswith("- ")]
    check("TODO" not in claude_md and len(bullets) >= 2, "CLAUDE.md has a working agreement with at least two bullets")
    check("unittest discover" in claude_md, "CLAUDE.md names the test command")

    print("Stage 2 - direct or plan?")
    triage = read(wd / ".claude" / "commands" / "triage.md")
    check(triage.startswith("---\n") and "description:" in triage.split("\n---", 1)[0], "/triage has front matter with a description")
    check("$ARGUMENTS" in triage and "DIRECT" in triage and "PLAN" in triage, "/triage takes the request and answers DIRECT or PLAN")
    sys.path.insert(0, str(wd / "src"))
    from shipcalc.models import Parcel
    from shipcalc.quote import get_quote
    message = raises_value_error(lambda: get_quote(Parcel(1.0), "nope"))
    check(message == "Unknown carrier: nope", "the small change is done: the unknown-carrier message reads 'Unknown carrier: nope'", repr(message))
    check("Unknown carrier" in read(wd / "tests" / "test_errors.py"), "tests/test_errors.py tests that message")

    print("Stage 3 - Plan Mode")
    plan_text = read(wd / "docs" / "PLAN.md")
    spec = importlib.util.spec_from_file_location("plan_gate", wd / "tools" / "plan_check.py")
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    gate_results = gate.check(plan_text) if plan_text else [("docs/PLAN.md exists", False)]
    failed = [label for label, ok in gate_results if not ok]
    check(not failed, "docs/PLAN.md passes the plan gate (%d/%d)" % (len(gate_results) - len(failed), len(gate_results)), "missing: " + "; ".join(failed))

    print("Stage 4 - implement and verify")
    try:
        hooks = json.loads(read(wd / ".claude" / "settings.json")).get("hooks", {}).get("PostToolUse", [])
    except ValueError:
        hooks = []
    hook_ok = any(h.get("matcher") == "Edit|Write" and any("unittest" in x.get("command", "") for x in h.get("hooks", [])) for h in hooks)
    check(hook_ok, ".claude/settings.json runs the tests after every Edit or Write (PostToolUse hook)")
    check(any((wd / "tests").glob("*characteri*.py")), "a characterization test file exists in tests/")
    check((wd / "tests" / "test_imperial_regression.py").is_file(), "tests/test_imperial_regression.py exists")
    ran, ok = run_python(wd, ["-m", "unittest", "discover", "-s", "tests"])
    check(ok and ran >= 14, "visible tests green and you added tests (at least 14 run)", "ran=%d ok=%s" % (ran, ok))
    ran, ok = run_python(wd, ["scripts/hidden_regression_units.py"])
    check(ok and ran == 4, "acceptance script: 4 of 4 imperial-unit checks pass", "ran=%d ok=%s" % (ran, ok))
    src = wd / "src" / "shipcalc"
    pattern = r"0\.4535|2\.54\b|2\.2046?"
    duplicates = [p.name for p in src.rglob("*.py") if p.name != "units.py" and re.search(pattern, read(p))]
    check(not duplicates, "unit constants live only in units.py", "also in %s" % duplicates)
    adapters = [read(src / "carriers" / n) for n in ("acme.py", "zipfast.py")]
    check(all("units." in a for a in adapters), "both adapters convert through units.py")

    print("The separate change")
    from shipcalc import rates
    zone_message = raises_value_error(lambda: rates.price_cents(1.0, 4))
    check(zone_message is not None, "an unknown zone raises ValueError instead of KeyError")
    check("zone" in read(wd / "tests" / "test_errors.py").lower(), "tests/test_errors.py tests the zone case")
    changed = [n for n, digest in UNTOUCHED.items()
               if hashlib.sha256((wd / n).read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:16] != digest]
    check(not changed, "models.py and the original tests are untouched", "changed: %s" % changed)

    print("RESULT: %d/%d checks passed" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
