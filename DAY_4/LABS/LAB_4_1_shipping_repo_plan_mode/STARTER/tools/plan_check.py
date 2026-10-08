"""Plan gate: a plan is accepted only if it names the blast radius, orders the work and says
how each step is verified.   Run: python tools/plan_check.py docs/PLAN.md"""
import pathlib
import re
import sys

SECTIONS = ["files to change", "callers", "risks", "order", "verification", "rollback"]
MENTIONS = {
    "pounds are converted in the zipfast adapter": r"pound|\blb\b",
    "dimensional weight (inches vs centimetres) is called out": r"dimensional|volumetric",
    "acceptance script is run": r"hidden_regression_units",
    "characterization test comes first": r"characteri[sz]ation",
    "unrelated finding is a separate step": r"separate",
}
MODULES = ["acme.py", "zipfast.py", "packaging.py", "units.py"]   # found by the blast-radius scan


def check(text):
    results = [("section: " + s, bool(re.search(r"^#+\s.*" + re.escape(s), text.lower(), re.M))) for s in SECTIONS]
    results += [(label, bool(re.search(pattern, text, re.I))) for label, pattern in MENTIONS.items()]
    results += [("names module " + m, m in text) for m in MODULES]
    return results


if __name__ == "__main__":
    results = check(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    passed = sum(ok for _, ok in results)
    print("PLAN %s (%d/%d checks)" % ("ACCEPTED" if passed == len(results) else "REJECTED", passed, len(results)))
