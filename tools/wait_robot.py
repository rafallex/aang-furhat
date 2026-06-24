"""Wait until the robot's Realtime API is reachable (e.g. after a reboot).

Polls the configured FURHAT_HOST:FURHAT_PORT every few seconds. Handy right after
powering the robot on, before running aang_app.py.

Run:  python tools/wait_robot.py     (exit 0 = up, 1 = timed out after ~5 min)
"""
import os
import sys
import time
import socket

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aang.config import Config

c = Config()
host, port = c.host, c.port
print(f"waiting for robot Realtime API at {host}:{port} (Furhat boot ~1-3 min)...", flush=True)
deadline = time.time() + 300
n = 0
while time.time() < deadline:
    n += 1
    s = socket.socket(); s.settimeout(2.0)
    try:
        s.connect((host, port)); s.close()
        print(f"READY after {n} tries: robot is up at {host}:{port}", flush=True)
        sys.exit(0)
    except Exception:
        s.close()
        time.sleep(4)
print("TIMEOUT: robot not reachable after 5 min", flush=True)
sys.exit(1)
