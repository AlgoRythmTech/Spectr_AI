"""Spawn the supervisor as a fully-detached Windows process.

Problem: Start-Process, cmd /c start, and pythonw.exe all leave the child
tied to the parent's console handle or job object on Windows 10/11. When
the parent terminal/IDE/Claude session closes, Windows kills the children.

Fix: subprocess.Popen with CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
explicitly severs the console attachment. The resulting supervisor runs
under services.exe / svchost lineage, independent of any user session
process tree. Only a reboot or explicit kill stops it.

Usage:
    python _launch_detached.py
"""
import os
import sys
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable  # whatever interpreter launched this
SUPERVISOR = os.path.join(BASE, "_supervisor.py")

# Windows-specific flags
if os.name == "nt":
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    CREATE_NO_WINDOW = 0x08000000
    creationflags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
else:
    creationflags = 0

# Null-out stdio so the child doesn't inherit handles that could link it
# back to our console
DEVNULL = subprocess.DEVNULL
stdout_path = os.path.join(BASE, "supervisor_launch_stdout.log")
stderr_path = os.path.join(BASE, "supervisor_launch_stderr.log")

# Preload files to ensure they exist and can be appended to
open(stdout_path, "a").close()
open(stderr_path, "a").close()

proc = subprocess.Popen(
    [PY, SUPERVISOR],
    cwd=BASE,
    stdin=DEVNULL,
    stdout=open(stdout_path, "ab"),
    stderr=open(stderr_path, "ab"),
    creationflags=creationflags,
    close_fds=True,
)

# Don't wait — exit immediately so the supervisor is orphaned to init
print(f"spawned supervisor PID={proc.pid}")
