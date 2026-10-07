"""Key-free self-check for the intro-to-MCP demo. Run from this folder:   python check_offline.py
If the real `mcp` package is missing, the trainer's offline stand-ins (TRAINER_V2/DAY_2/_offline_shims) are used and the check says so.
It proves that this demo's own code works end to end. It does not prove how the real SDK reacts to the stage-4 stdout bug."""
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
SHIMS = HERE.parent.parent / "_offline_shims"
results = []


def check(ok, description):
    results.append(bool(ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {description}")


try:
    import mcp  # noqa: F401
    using_shim = False
except ImportError:
    using_shim = True
env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
if using_shim:
    env["PYTHONPATH"] = str(SHIMS)


def run(stage):
    return subprocess.run([sys.executable, "demo.py", "--stage", stage], cwd=HERE, capture_output=True, text=True, timeout=120, env=env)


out = {s: run(s) for s in "1234"}
check(all(r.returncode == 0 for r in out.values()), "all four stages run: " + "; ".join(f"{s}: {r.stderr[-150:]}" for s, r in out.items() if r.returncode))
check(out["1"].stdout.count("OK     order placed") == 3 and "3 of 3 apps broke" in out["1"].stdout, "stage 1: three apps work on kitchen v1, and all three break on v2")
check("tool check_stock(item)" in out["2"].stdout and "tool place_order(item, qty)" in out["2"].stdout, "stage 2: the client discovers both tools")
check("margherita: $9" in out["2"].stdout and "ERROR: " in out["2"].stdout, "stage 2: a resource is read, and an out-of-stock order is an error")
check(out["3"].stdout.count("OK     sent") == 6 and "BROKEN" not in out["3"].stdout, "stage 3: six app runs (3 apps x 2 kitchen versions), none broken")
check("'quantity': 2, 'table': 5" in out["3"].stdout, "stage 3: the client filled the NEW parameters from the schema")
check("server that prints to stdout" in out["4"].stdout and "server that logs to stderr" in out["4"].stdout, "stage 4: both servers are tried")
if using_shim:
    print("\nNOT VERIFIED here: the real mcp 2.3.0 SDK was not installed, so stand-ins ran. Run all four stages once with the real package.")
print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
