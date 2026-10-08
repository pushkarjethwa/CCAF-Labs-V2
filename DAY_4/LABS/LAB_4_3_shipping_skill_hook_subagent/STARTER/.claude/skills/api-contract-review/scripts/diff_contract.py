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
        # TODO 2 of 4 - find the function in the tree and compare its parameters with the contract
    return hits


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    hits = scan(parser.parse_args().root)
    for file_name, lineno, reason in hits:
        print("%s:%d %s" % (file_name, lineno, reason))
    print("contract scan: %d candidate(s)" % len(hits))
