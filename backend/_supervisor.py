"""Spectr backend supervisor.

Keeps uvicorn alive. If the backend exits for any reason — crash, OOM,
parent-shell GC, unhandled exception — this loop restarts it within
seconds. Includes crash-loop protection so a permanently broken backend
doesn't spin the CPU.

Launch detached (survives your terminal / Claude session / IDE restart):
    pythonw.exe _supervisor.py
...or via the companion backend_start.ps1 wrapper.

PID files:
    supervisor.pid  — this process
    backend.pid     — the uvicorn child
Logs:
    supervisor.log  — supervisor events (restart, crash-loop, exit)
    backend_stdout.log / backend_stderr.log — uvicorn's own output
"""

import os
import sys
import time
import subprocess
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = sys.executable
BACKEND_SCRIPT = os.path.join(BASE, "_run_backend.py")
SUPERVISOR_PID_FILE = os.path.join(BASE, "supervisor.pid")
SUPERVISOR_LOG = os.path.join(BASE, "supervisor.log")
BACKEND_STDOUT = os.path.join(BASE, "backend_stdout.log")
BACKEND_STDERR = os.path.join(BASE, "backend_stderr.log")


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts}  {msg}\n"
    try:
        with open(SUPERVISOR_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def main() -> None:
    # Record our PID so the stop script can find us
    with open(SUPERVISOR_PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    log(f"Supervisor starting. supervisor_pid={os.getpid()}")

    consecutive_fast_failures = 0
    while True:
        started_at = time.time()

        stdout_fh = open(BACKEND_STDOUT, "ab")
        stderr_fh = open(BACKEND_STDERR, "ab")
        log(f"Launching backend: {PYTHON_EXE} {BACKEND_SCRIPT}")
        try:
            # CREATE_NO_WINDOW = 0x08000000 on Windows to keep it headless
            creationflags = 0
            if os.name == "nt":
                creationflags = 0x08000000  # CREATE_NO_WINDOW
            proc = subprocess.Popen(
                [PYTHON_EXE, BACKEND_SCRIPT],
                cwd=BASE,
                stdout=stdout_fh,
                stderr=stderr_fh,
                creationflags=creationflags,
            )
            log(f"Backend launched PID={proc.pid}")
            exit_code = proc.wait()
        except Exception as e:
            log(f"Failed to launch backend: {e}")
            exit_code = -1
        finally:
            try:
                stdout_fh.close()
            except Exception:
                pass
            try:
                stderr_fh.close()
            except Exception:
                pass

        uptime = time.time() - started_at
        log(f"Backend exited code={exit_code} uptime={uptime:.1f}s")

        # Crash-loop protection
        if uptime < 15:
            consecutive_fast_failures += 1
        else:
            consecutive_fast_failures = 0

        if consecutive_fast_failures >= 5:
            log("Five consecutive fast failures — backing off 60s.")
            time.sleep(60)
            consecutive_fast_failures = 0
        else:
            time.sleep(3)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Supervisor interrupted by KeyboardInterrupt — exiting.")
    except Exception as e:
        log(f"Supervisor fatal: {e!r}")
        raise
