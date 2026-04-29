"""Standalone launcher so uvicorn doesn't inherit a parent shell's lifecycle.

Run detached via PowerShell:
    Start-Process -WindowStyle Hidden python -ArgumentList "_run_backend.py"

It writes its PID to backend.pid so `Stop-Process -Id (Get-Content backend.pid)`
kills it cleanly later.
"""
import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Write PID so we can stop it later without guessing
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend.pid"), "w") as f:
    f.write(str(os.getpid()))

# Route logs to file so the hidden window doesn't discard them
log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend_live.log")
logging.basicConfig(
    level=logging.INFO,
    filename=log_path,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

import server
import uvicorn

uvicorn.run(server.app, host="0.0.0.0", port=8000, log_level="warning")
