"""Deterministic helper for the api-contract-review skill: compare docs/API_CONTRACT.json with the code.

    python diff_contract.py --root <repo>

Flags every public function whose parameter list differs from the contract. Exit 0 always;
the output is evidence for the reviewer, not a verdict.
"""
import argparse
import ast
import json
import pathlib


def scan(root):
    root = pathlib.Path(root)
    contract = json.loads((root / "docs" / "API_CONTRACT.json").read_text(encoding="utf-8"))
    hits = []
    for entry in contract["public"]:
        tree = ast.parse((root / entry["file"]).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == entry["function"]:
                params = [arg.arg for arg in node.args.args]
                if params != entry["params"]:
                    hits.append((entry["file"], node.lineno, "%s params %s != contract %s" % (node.name, params, entry["params"])))
    return hits


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    hits = scan(parser.parse_args().root)
    for file_name, lineno, reason in hits:
        print("%s:%d %s" % (file_name, lineno, reason))
    print("contract scan: %d candidate(s)" % len(hits))
