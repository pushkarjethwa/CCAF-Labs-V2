"""Key-free self-check for the separate server and client demo. Run from this folder:   python check_offline.py
It starts the server as its own process, runs the client against it, and then runs the client with no server.
If the real `mcp` package is missing, the trainer's offline stand-ins are used and the check says so."""
import os
import pathlib
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

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
env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUNBUFFERED": "1"}
if using_shim:
    env["PYTHONPATH"] = str(SHIMS)

sock = socket.socket()
sock.bind(("127.0.0.1", 0))
port = sock.getsockname()[1]
sock.close()
url = f"http://127.0.0.1:{port}/mcp"


def run_client(*extra):
    return subprocess.run([sys.executable, "kitchen_client.py", "--url", url, *extra], cwd=HERE / "client_app", capture_output=True, text=True, timeout=60, env=env)


check(not (HERE / "client_app" / "kitchen.py").exists() and "import kitchen" not in (HERE / "client_app" / "kitchen_client.py").read_text(), "the client app has no kitchen code")
down = run_client()
check(down.returncode == 1 and "Is the kitchen server running?" in down.stdout, "with no server, the client explains what is wrong")

server = subprocess.Popen([sys.executable, "kitchen_server.py", "--port", str(port)], cwd=HERE / "server_app", env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
try:
    for _ in range(100):
        try:
            urllib.request.urlopen(url, timeout=1)
            break
        except urllib.error.HTTPError:
            break
        except OSError:
            time.sleep(0.15)
    tour = run_client()
    check(tour.returncode == 0, "the client talks to the separate server: " + tour.stderr[-200:])
    check("tool check_stock(item)" in tour.stdout and "tool place_order(item, qty)" in tour.stdout, "the client discovers both tools")
    check("margherita: $9" in tour.stdout, "the client reads the menu resource")
    check("order placed: 2 x margherita = $18" in tour.stdout, "the client places an order")
    sold_out = run_client("--item", "pepperoni", "--qty", "1")
    check("ERROR: " in sold_out.stdout and "only 0 pepperoni left" in sold_out.stdout, "an out-of-stock order comes back as an error, and the client survives")
finally:
    server.terminate()
    server.wait(10)
if using_shim:
    print("\nNOT VERIFIED here: the real mcp 2.3.0 SDK was not installed, so stand-ins ran. Run it once with the real package.")
print(f"\nRESULT: {sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
