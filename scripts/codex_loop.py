#!/usr/bin/env python3
"""Time-bounded lint+test loop to support an external agent (Codex) editing the repo.
This won't modify code itself; it just runs the checks repeatedly until clean or timeout.
"""

import json
import subprocess
import sys
import time

def run_cmd(cmd: str) -> int:
    print(f"$ {cmd}", flush=True)
    return subprocess.call(cmd, shell=True)

def loop(minutes: int = 60) -> None:
    start = time.time()
    it = 0
    while (time.time() - start) < minutes * 60:
        it += 1
        print(f"--- iteration {it} ---", flush=True)
        rc_lint = run_cmd("ruff check .")
        rc_test = run_cmd("pytest -q")
        summary = {
            "iter": it,
            "rc_lint": rc_lint,
            "rc_test": rc_test,
            "elapsed_s": round(time.time() - start, 1),
        }
        print(json.dumps(summary), flush=True)
        if rc_lint == 0 and rc_test == 0:
            print("CLEAN: lint+tests passed.", flush=True)
            break

if __name__ == "__main__":
    mins = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    loop(minutes=mins)
