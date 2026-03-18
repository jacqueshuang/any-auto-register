"""Turnstile Solver 进程管理 - 后端启动时自动拉起"""
import os
import subprocess
import sys
import threading
import time

import requests

SOLVER_PORT = 8889
SOLVER_URL = f"http://localhost:{SOLVER_PORT}"
FALSE_VALUES = {"0", "false", "no", "off"}
_proc: subprocess.Popen = None
_lock = threading.Lock()


def autostart_enabled() -> bool:
    return os.getenv("ENABLE_SOLVER_AUTOSTART", "true").strip().lower() not in FALSE_VALUES


def is_running() -> bool:
    try:
        r = requests.get(f"{SOLVER_URL}/", timeout=2)
        return r.status_code < 500
    except Exception:
        return False


def start():
    global _proc
    with _lock:
        if is_running():
            print("[Solver] 已在运行")
            return
        solver_script = os.path.join(
            os.path.dirname(__file__), "turnstile_solver", "start.py"
        )
        _proc = subprocess.Popen(
            [sys.executable, solver_script, "--browser_type", "camoufox"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(30):
            time.sleep(1)
            if is_running():
                print(f"[Solver] 已启动 PID={_proc.pid}")
                return
        print("[Solver] 启动超时")


def stop():
    global _proc
    with _lock:
        if _proc and _proc.poll() is None:
            _proc.terminate()
            _proc.wait(timeout=5)
            print("[Solver] 已停止")
            _proc = None


def start_async():
    t = threading.Thread(target=start, daemon=True)
    t.start()
