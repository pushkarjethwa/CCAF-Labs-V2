"""Blast-radius scanner: which modules read a parcel's weight or dimensions, which call the
conversion and dimensional-weight helpers, and which tests import them.
Run it AFTER Claude's own exploration, to cross-check the answer.   python tools/blast_radius.py"""
import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PARCEL_FIELDS = {"weight", "dims", "weight_unit", "dim_unit"}
HELPER_CALLS = {"lb_to_kg", "in_to_cm", "billable_weight_kg", "dim_weight_kg"}


def scan():
    readers, callers = {}, {}
    for path in sorted((ROOT / "src" / "shipcalc").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Attribute) and node.attr in PARCEL_FIELDS:
                readers.setdefault(path.stem, set()).add(node.attr)
            if isinstance(node, ast.Call):
                f = node.func
                name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
                if name in HELPER_CALLS:
                    callers.setdefault(path.stem, set()).add(name)
    return readers, callers


if __name__ == "__main__":
    readers, callers = scan()
    touched = sorted(set(readers) | set(callers))
    print("BLAST RADIUS of 'unit handling'")
    print("  read parcel fields :", ", ".join("%s.py" % m for m in readers))
    print("  call the helpers   :", ", ".join("%s.py" % m for m in callers))
    print("  tests touching these modules:")
    for test in sorted((ROOT / "tests").glob("test_*.py")):
        text = test.read_text(encoding="utf-8")
        hit = [m for m in touched if m in text]
        if hit:
            print("    %-22s -> %s" % (test.name, ", ".join(hit)))
