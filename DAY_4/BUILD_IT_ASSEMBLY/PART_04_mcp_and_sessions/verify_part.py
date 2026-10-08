"""Part 4 check: the menu MCP server functions work, the data matches docs/MENU.md, the .mcp.json shape is right."""
import argparse
import json
import os
import re
import subprocess
import sys


def read(repo, path):
    full = os.path.join(repo, path)
    return open(full, encoding="utf-8").read() if os.path.isfile(full) else ""


def call(repo, expression):
    """Import mcp_server/menu_server.py in a fresh interpreter and evaluate an expression. Returns (ok, value)."""
    code = ("import sys, json, importlib.util\nsys.dont_write_bytecode = True\n"
            "spec = importlib.util.spec_from_file_location('menu_server', 'mcp_server/menu_server.py')\n"
            "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
            "print(json.dumps(" + expression + "))\n")
    done = subprocess.run([sys.executable, "-B", "-c", code], cwd=repo, capture_output=True, text=True,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    if done.returncode:
        return False, done.stderr
    return True, json.loads(done.stdout)


def valid_menu_entry(text):
    try:
        entry = json.loads(text)["mcpServers"]["menu"]
    except (ValueError, KeyError, TypeError):
        return False
    return entry.get("type") == "stdio" and entry.get("command") == "python" \
        and any(str(a).endswith("mcp_server/menu_server.py") for a in entry.get("args", []))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    repo = os.path.abspath(parser.parse_args().repo)
    results = []

    def check(name, ok):
        results.append(bool(ok))
        print("[%s] %s" % ("PASS" if ok else "FAIL", name))

    doc = {m.group(1): int(m.group(2)) for m in re.finditer(r"^- (.+): (\d+)$", read(repo, "docs/MENU.md"), re.M)}
    try:
        data = json.loads(read(repo, "mcp_server/menu.json"))
        check("mcp_server/menu.json is valid JSON with integer cent prices",
              bool(data) and all(isinstance(v, int) and not isinstance(v, bool) for v in data.values()))
    except ValueError:
        data = {}
        check("mcp_server/menu.json is valid JSON with integer cent prices", False)
    check("menu.json matches docs/MENU.md exactly", bool(doc) and data == doc)

    ok, value = call(repo, "m.get_menu_price('Latte')")
    check("get_menu_price('Latte') returns 450 (an int)", ok and value == 450 and isinstance(value, int))
    ok, value = call(repo, "[m.get_menu_price('espresso'), m.get_menu_price(' Blueberry muffin ')]")
    check("get_menu_price ignores case and spaces (300 and 325)", ok and value == [300, 325])
    ok, value = call(repo, "[m.get_menu_price(i) for i in %r]" % list(doc))
    check("get_menu_price returns every price in docs/MENU.md", ok and value == list(doc.values()))
    ok, value = call(repo, "m.list_menu()")
    check("list_menu returns every item with price_cents",
          ok and [(e["item"], e["price_cents"]) for e in value] == list(doc.items()))
    ok, value = call(repo, "(lambda: [m.get_menu_price('Pizza')])()")
    check("get_menu_price raises ValueError for an item not on the menu", (not ok) and "ValueError" in value)

    source = read(repo, "mcp_server/menu_server.py")
    check("the mcp import is inside main() so the file imports without mcp",
          re.search(r"^(from|import) mcp", source, re.M) is None and "def main" in source)
    check("mcp_server/mcp.json.reference shows the menu server entry", valid_menu_entry(read(repo, "mcp_server/mcp.json.reference")))
    live = read(repo, ".mcp.json")
    check(".mcp.json (once created by claude mcp add) holds the menu server entry, or is not created yet",
          not live or valid_menu_entry(live))
    try:
        hooks = json.loads(read(repo, ".claude/settings.json")).get("hooks", {})
    except ValueError:
        hooks = {}
    check("Part 3 settings still intact (both hooks present)", "PreToolUse" in hooks and "PostToolUse" in hooks)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
