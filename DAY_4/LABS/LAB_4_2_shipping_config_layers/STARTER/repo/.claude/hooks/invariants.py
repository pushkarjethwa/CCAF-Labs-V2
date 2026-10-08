"""Independently enforceable money rule: no float arithmetic on prices in src/shipcalc.
Used by the PostToolUse hook and from the command line.  CLAUDE.md can ask; this can refuse."""
import ast
import pathlib
import re
import sys

MONEY_NAME = re.compile(r"cents|price|cost|fee|total|charge", re.I)


def has_float_literal(node):
    return any(isinstance(n, ast.Constant) and isinstance(n.value, float) for n in ast.walk(node))


def scan_source(source):
    """Return [(lineno, reason)] for float-on-money patterns."""
    violations = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "float":
                violations.append((node.lineno, "float() call"))
            elif node.func.id == "round":
                violations.append((node.lineno, "builtin round() (float semantics)"))
        if isinstance(node, ast.FunctionDef) and MONEY_NAME.search(node.name):
            for inner in ast.walk(node):
                if isinstance(inner, ast.Constant) and isinstance(inner.value, float):
                    violations.append((inner.lineno, "float literal in money function '%s'" % node.name))
        if isinstance(node, ast.Assign) and has_float_literal(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name) and MONEY_NAME.search(target.id):
                    violations.append((node.lineno, "float literal assigned to money name '%s'" % target.id))
    return sorted(set(violations))


def scan_tree(src_dir):
    violations_by_file = {}
    for path in sorted(pathlib.Path(src_dir).rglob("*.py")):
        violations = scan_source(path.read_text(encoding="utf-8"))
        if violations:
            violations_by_file[path.as_posix()] = violations
    return violations_by_file


if __name__ == "__main__":
    violations_by_file = scan_tree(sys.argv[1])
    for file_name, violations in violations_by_file.items():
        for lineno, reason in violations:
            print("%s:%d %s" % (file_name, lineno, reason))
    print("MONEY INVARIANT: %s" % ("VIOLATED" if violations_by_file else "ok"))
    sys.exit(1 if violations_by_file else 0)
