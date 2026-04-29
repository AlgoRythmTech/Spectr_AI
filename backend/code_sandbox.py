"""
Python Code Sandbox — Blaxel-powered Python execution for CA/lawyer file automation.

Separate from sandbox_research.py (which handles browser research) — this module
manages Python-capable sandboxes for executing LLM-generated code that produces
Excel, Word, PDF, JPG deliverables.

Setup installs: python3, pip, pandas, openpyxl, python-docx, pdfplumber, pillow,
matplotlib, reportlab, xlsxwriter, wkhtmltoimage/wkhtmltopdf, and common utilities.

Pool architecture mirrors sandbox_research but uses different setup scripts +
different sandbox naming so the two pools don't collide.
"""
import os
import re
import uuid
import time
import asyncio
import logging
from typing import Optional

logger = logging.getLogger("code_sandbox")

# === CONFIGURATION ===
BL_API_KEY = os.environ.get("BL_API_KEY", "")
# Prefer Debian-based image (pandas/numpy install reliably via pip binary wheels).
# Fallback to Blaxel base if custom image unavailable.
PY_SANDBOX_IMAGE = os.environ.get("BL_PY_IMAGE", "blaxel/base-image:latest")
PY_SANDBOX_MEMORY = 4096
PY_SANDBOX_REGION = "us-pdx-1"
PY_SANDBOX_TTL = 900        # 15 min idle → destroy
PY_CLEANUP_INTERVAL = 120   # Sweep every 2 min

# Sandbox pool — separate from browser pool
_py_sandbox_pool: dict[str, dict] = {}
_pool_lock = asyncio.Lock()
_POOL_MAX_SIZE = 2  # Smaller pool — Python sandboxes are heavier
_setup_in_progress: set[str] = set()
_cleanup_task_started = False


# === PYTHON SETUP SCRIPT ===
# Alpine-based — installs Python + pip + common CA/lawyer automation libraries
# Pure-Python libs only (avoid compilation) for faster startup.
PYTHON_SETUP_SCRIPT = """#!/bin/sh
set -e
echo "[SETUP] Installing Python and dependencies..."

# Core Python + build tools (only what's needed for pure-Python wheels)
apk add --no-cache \
    python3 py3-pip \
    ca-certificates \
    wget curl jq \
    fontconfig ttf-dejavu \
    wkhtmltopdf 2>/dev/null || true

# Upgrade pip
python3 -m pip install --upgrade pip --break-system-packages --quiet 2>/dev/null || \
python3 -m pip install --upgrade pip --quiet 2>/dev/null || true

# Install pure-Python libraries (no C compilation needed — fast install)
python3 -m pip install --no-cache-dir --break-system-packages --quiet \
    openpyxl \
    python-docx \
    pdfplumber \
    pypdf \
    reportlab \
    xlsxwriter \
    pillow \
    jinja2 \
    python-dateutil \
    rapidfuzz \
    tabulate \
    2>/dev/null || \
python3 -m pip install --no-cache-dir --quiet \
    openpyxl \
    python-docx \
    pdfplumber \
    pypdf \
    reportlab \
    xlsxwriter \
    pillow \
    jinja2 \
    python-dateutil \
    rapidfuzz \
    tabulate \
    2>/dev/null || true

# Try to install pandas + numpy via binary wheels if available (manylinux)
# On Alpine musl, these often fail — we'll degrade gracefully
python3 -m pip install --no-cache-dir --prefer-binary --break-system-packages --quiet \
    pandas numpy 2>/dev/null || \
python3 -m pip install --no-cache-dir --prefer-binary --quiet \
    pandas numpy 2>/dev/null || \
echo "[SETUP] pandas/numpy not installed (Alpine musl) — using openpyxl directly"

# Create workspace
mkdir -p /workspace/input /workspace/output
echo "PYTHON_READY"
"""


async def _get_or_create_py_sandbox(sandbox_name: Optional[str] = None):
    """Get or create a Python-capable sandbox from the pool."""
    from blaxel.core.sandbox import SandboxInstance

    async with _pool_lock:
        # Try to reuse an existing ready sandbox
        for name, info in _py_sandbox_pool.items():
            if info.get("ready") and name not in _setup_in_progress:
                info["last_used"] = time.time()
                logger.info(f"Reusing Python sandbox: {name}")
                return info["instance"]

        # Pool is full? Evict oldest
        if len(_py_sandbox_pool) >= _POOL_MAX_SIZE:
            oldest_name = min(_py_sandbox_pool.keys(),
                              key=lambda n: _py_sandbox_pool[n].get("last_used", 0))
            logger.info(f"Evicting oldest Python sandbox: {oldest_name}")
            try:
                await SandboxInstance.delete(oldest_name)
            except Exception as e:
                logger.warning(f"Eviction failed: {e}")
            _py_sandbox_pool.pop(oldest_name, None)

        # Create new
        name = sandbox_name or f"spectr-py-{uuid.uuid4().hex[:8]}"
        _setup_in_progress.add(name)

    try:
        logger.info(f"Creating new Python sandbox: {name}")
        sandbox = await SandboxInstance.create_if_not_exists({
            "name": name,
            "image": PY_SANDBOX_IMAGE,
            "memory": PY_SANDBOX_MEMORY,
            "region": PY_SANDBOX_REGION,
        })

        # Wait for sandbox to be ready
        await sandbox.wait()

        # Run setup
        logger.info(f"Running Python setup on {name}")
        await sandbox.fs.write("/tmp/setup_py.sh", PYTHON_SETUP_SCRIPT)
        setup_process = await sandbox.process.exec({
            "name": "python-setup",
            "command": "sh /tmp/setup_py.sh",
        })

        # Wait for setup (up to 5 min for installs)
        try:
            await setup_process.wait(timeout=300)
        except Exception as e:
            logger.warning(f"Setup wait failed (continuing anyway): {e}")

        # Verify Python is available
        try:
            verify = await sandbox.process.exec({
                "name": "python-verify",
                "command": "python3 -c 'import openpyxl, docx; print(chr(79)+chr(75))'",
            })
            await verify.wait(timeout=15)
        except Exception as e:
            logger.warning(f"Python sandbox verification failed on {name}: {e}")

        async with _pool_lock:
            _py_sandbox_pool[name] = {
                "instance": sandbox,
                "ready": True,
                "last_used": time.time(),
            }
            _setup_in_progress.discard(name)

        logger.info(f"Python sandbox ready: {name}")

        # Start cleanup task if not already running
        global _cleanup_task_started
        if not _cleanup_task_started:
            _cleanup_task_started = True
            asyncio.create_task(_idle_cleanup_loop())

        return sandbox

    except Exception as e:
        logger.error(f"Failed to create Python sandbox {name}: {e}")
        async with _pool_lock:
            _setup_in_progress.discard(name)
            _py_sandbox_pool.pop(name, None)
        raise


async def _idle_cleanup_loop():
    """Background task — destroy sandboxes idle > TTL."""
    from blaxel.core.sandbox import SandboxInstance
    while True:
        try:
            await asyncio.sleep(PY_CLEANUP_INTERVAL)
            now = time.time()
            to_delete = []
            async with _pool_lock:
                for name, info in list(_py_sandbox_pool.items()):
                    idle = now - info.get("last_used", now)
                    if idle > PY_SANDBOX_TTL:
                        to_delete.append(name)
                for name in to_delete:
                    _py_sandbox_pool.pop(name, None)

            for name in to_delete:
                try:
                    logger.info(f"Destroying idle Python sandbox: {name}")
                    await SandboxInstance.delete(name)
                except Exception as e:
                    logger.warning(f"Idle cleanup delete failed for {name}: {e}")
        except Exception as e:
            logger.warning(f"Cleanup loop error: {e}")


# === FILE I/O HELPERS ===

async def upload_file_to_sandbox(sandbox, filename: str, content: bytes, subdir: str = "input") -> str:
    """Upload a file's bytes to the sandbox via base64 intermediate.

    Blaxel's fs.write decodes binary content as UTF-8, which corrupts xlsx/docx/pdf etc.
    Solution: write the base64 string to a .b64 file, then decode it inside the sandbox.
    Returns the final absolute path of the decoded file.
    """
    import base64 as _b64
    safe_name = re.sub(r'[^\w\-.]', '_', filename)
    final_path = f"/workspace/{subdir}/{safe_name}"
    b64_path = f"/tmp/upload_{uuid.uuid4().hex[:8]}.b64"

    # Write base64-encoded content (safe as text)
    b64_content = _b64.b64encode(content).decode('ascii')
    await sandbox.fs.write(b64_path, b64_content)

    # Decode inside sandbox to produce the real binary file
    decode_cmd = (
        f"mkdir -p /workspace/{subdir} && "
        f"python3 -c \"import base64, sys; "
        f"open('{final_path}', 'wb').write(base64.b64decode(open('{b64_path}').read()))\""
    )
    proc = await sandbox.process.exec({
        "name": f"decode-upload-{uuid.uuid4().hex[:6]}",
        "command": decode_cmd,
    })
    try:
        await proc.wait(timeout=30)
    except Exception:
        pass

    # Poll for file existence + correct size
    deadline = asyncio.get_event_loop().time() + 20
    while asyncio.get_event_loop().time() < deadline:
        try:
            check = await sandbox.process.exec({
                "name": f"check-upload-{uuid.uuid4().hex[:6]}",
                "command": f"stat -c %s '{final_path}' 2>/dev/null || echo MISSING",
            })
            try:
                await check.wait(timeout=5)
            except Exception:
                pass
            out = ""
            try:
                out = await check.logs.all()
            except Exception:
                pass
            if out and "MISSING" not in str(out) and str(out).strip().isdigit():
                file_size = int(str(out).strip())
                if file_size == len(content):
                    return final_path
                logger.warning(f"Upload size mismatch for {filename}: expected {len(content)}, got {file_size}")
        except Exception:
            pass
        await asyncio.sleep(0.5)

    logger.warning(f"Upload of {filename} may have failed or is still propagating")
    return final_path


async def read_file_from_sandbox(sandbox, path: str) -> bytes:
    """Read a file's bytes from the sandbox (handles both bytes and str responses)."""
    content = await sandbox.fs.read(path)
    if isinstance(content, str):
        # Binary file was read as text — encode back to bytes
        content = content.encode('utf-8', errors='surrogateescape')
    return content


async def list_output_files(sandbox, subdir: str = "output") -> list[str]:
    """List all files generated by the code in /workspace/output/.

    Uses a two-step approach: write the file list to a manifest file, then read it.
    This is more reliable than parsing process stdout which can be flaky.
    """
    manifest_path = f"/tmp/manifest_{uuid.uuid4().hex[:6]}.txt"
    try:
        # Step 1: Write file list to manifest (more reliable than log capture)
        list_cmd = f"find /workspace/{subdir} -type f 2>/dev/null > {manifest_path}; echo done"
        proc = await sandbox.process.exec({
            "name": f"list-outputs-{uuid.uuid4().hex[:6]}",
            "command": list_cmd,
        })
        try:
            await proc.wait(timeout=10)
        except Exception:
            pass

        # Step 2: Read manifest file
        try:
            content = await sandbox.fs.read(manifest_path)
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='ignore')
            paths = [p.strip() for p in (content or "").strip().split("\n") if p.strip() and p.strip().startswith("/workspace")]
            return paths
        except Exception as e:
            logger.warning(f"Manifest read failed: {e}")

        # Fallback: try reading via logs
        try:
            stdout = await proc.logs.all()
            if stdout:
                paths = [p.strip() for p in stdout.strip().split("\n") if p.strip() and p.strip().startswith("/workspace")]
                return paths
        except Exception:
            pass
        return []
    except Exception as e:
        logger.warning(f"list_output_files failed: {e}")
        return []


# === CODE EXECUTION ===

async def execute_python(sandbox, code: str, timeout: int = 180) -> dict:
    """Execute Python code in the sandbox. Returns dict with stdout, stderr, exit_code.

    Wraps the user code in a harness that:
    1. Ensures /workspace/input + /workspace/output exist
    2. Redirects stdout/stderr to files we can read back via fs.read
    3. Writes a manifest JSON of /workspace/output contents after execution
    """
    script_id = uuid.uuid4().hex[:8]
    stdout_path = f"/tmp/stdout_{script_id}.txt"
    stderr_path = f"/tmp/stderr_{script_id}.txt"
    manifest_path = f"/tmp/manifest_{script_id}.json"
    user_script_path = f"/tmp/user_{script_id}.py"

    # Write user code
    await sandbox.fs.write(user_script_path, code)

    # Wrapper: ensures workspace dirs, installs required libs on-demand, runs user code,
    # base64-encodes all output files (binary-safe), writes manifest with encoded content.
    # Binary files → base64 text avoids UTF-8 decode corruption during fs.read.
    # Works on BOTH Debian (apt/deb) and Alpine (apk/musl) base images.
    b64_dir = f"/tmp/out_b64_{script_id}"
    wrapper = f"""#!/bin/sh
mkdir -p /workspace/input /workspace/output {b64_dir}

# Detect OS: Debian (has apt-get) or Alpine (has apk)
# On Debian, pandas/numpy install from binary wheels reliably. On Alpine musl, often fails.
IS_DEBIAN=$(command -v apt-get >/dev/null 2>&1 && echo 1 || echo 0)
if [ "$IS_DEBIAN" = "1" ]; then
    # Debian path — ensure pip + try to install pandas/numpy early
    which pip3 >/dev/null 2>&1 || apt-get install -y python3-pip --quiet 2>/dev/null || true
    python3 -c "import pandas" 2>/dev/null || pip3 install --quiet --prefer-binary pandas numpy 2>/dev/null || pip install --quiet --prefer-binary pandas numpy 2>/dev/null || true
fi

# Core libs (all platforms) — idempotent
PIP="pip3 install --quiet --break-system-packages"
alias pipfb="pip install --quiet"

python3 -c "import openpyxl" 2>/dev/null || $PIP openpyxl 2>/dev/null || pip install --quiet openpyxl 2>/dev/null
python3 -c "import docx" 2>/dev/null || $PIP python-docx 2>/dev/null || pip install --quiet python-docx 2>/dev/null
python3 -c "import xlsxwriter" 2>/dev/null || $PIP xlsxwriter 2>/dev/null || pip install --quiet xlsxwriter 2>/dev/null
python3 -c "import pdfplumber" 2>/dev/null || $PIP pdfplumber 2>/dev/null || pip install --quiet pdfplumber 2>/dev/null
python3 -c "import pypdf" 2>/dev/null || $PIP pypdf 2>/dev/null || pip install --quiet pypdf 2>/dev/null
python3 -c "import rapidfuzz" 2>/dev/null || $PIP rapidfuzz 2>/dev/null || pip install --quiet rapidfuzz 2>/dev/null
python3 -c "import PIL" 2>/dev/null || $PIP Pillow 2>/dev/null || pip install --quiet Pillow 2>/dev/null
python3 -c "import reportlab" 2>/dev/null || $PIP reportlab 2>/dev/null || pip install --quiet reportlab 2>/dev/null

cd /workspace
python3 {user_script_path} > {stdout_path} 2> {stderr_path}
EXIT_CODE=$?

# Base64-encode all output files (binary-safe transport through sandbox FS)
python3 -c "
import os, json, base64, hashlib
outputs = []
for root, dirs, files in os.walk('/workspace/output'):
    for f in files:
        p = os.path.join(root, f)
        try:
            with open(p, 'rb') as fh:
                content = fh.read()
            size = len(content)
            md5 = hashlib.md5(content).hexdigest()
            b64_content = base64.b64encode(content).decode('ascii')
            safe_name = p.replace('/', '_')
            b64_path = '{b64_dir}/' + safe_name + '.b64'
            with open(b64_path, 'w') as out:
                out.write(b64_content)
            outputs.append({{'path': p, 'size': size, 'md5': md5, 'b64_path': b64_path}})
        except Exception as e:
            outputs.append({{'path': p, 'size': 0, 'error': str(e)}})
with open('{manifest_path}', 'w') as m:
    json.dump({{'exit_code': $EXIT_CODE, 'outputs': outputs}}, m)
"
echo "WRAPPER_DONE"
"""
    wrapper_path = f"/tmp/wrap_{script_id}.sh"
    await sandbox.fs.write(wrapper_path, wrapper)

    try:
        process = await sandbox.process.exec({
            "name": f"py-run-{script_id}",
            "command": f"sh {wrapper_path}",
        })

        # The wrapper writes the manifest file LAST, so polling for it is the most reliable
        # signal that execution is complete. Blaxel's process.status() can lag.
        manifest_found = False
        poll_deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < poll_deadline:
            try:
                _test = await sandbox.fs.read(manifest_path)
                if _test:
                    # Verify it's valid JSON (fully written)
                    import json as _json
                    if isinstance(_test, bytes):
                        _test_str = _test.decode('utf-8', errors='replace')
                    else:
                        _test_str = _test
                    try:
                        _json.loads(_test_str)
                        manifest_found = True
                        break
                    except _json.JSONDecodeError:
                        # Partial write, keep polling
                        pass
            except Exception:
                pass
            await asyncio.sleep(1.0)

        if not manifest_found:
            logger.warning(f"Manifest never appeared for {script_id} within {timeout}s")

        # Read stdout + stderr via fs (more reliable than logs.all)
        stdout = ""
        stderr = ""
        try:
            stdout_bytes = await sandbox.fs.read(stdout_path)
            stdout = stdout_bytes.decode('utf-8', errors='replace') if isinstance(stdout_bytes, bytes) else (stdout_bytes or "")
        except Exception:
            pass
        try:
            stderr_bytes = await sandbox.fs.read(stderr_path)
            stderr = stderr_bytes.decode('utf-8', errors='replace') if isinstance(stderr_bytes, bytes) else (stderr_bytes or "")
        except Exception:
            pass

        # Read manifest for exit code + output files
        exit_code = -1
        outputs = []
        try:
            import json as _json
            manifest_bytes = await sandbox.fs.read(manifest_path)
            manifest_str = manifest_bytes.decode('utf-8', errors='replace') if isinstance(manifest_bytes, bytes) else manifest_bytes
            manifest = _json.loads(manifest_str)
            exit_code = manifest.get("exit_code", -1)
            outputs = manifest.get("outputs", [])
            # For each output, read the base64-encoded content via b64_path (binary-safe)
            import base64 as _base64
            for o in outputs:
                b64_path = o.get("b64_path")
                if not b64_path:
                    continue
                try:
                    b64_content = await sandbox.fs.read(b64_path)
                    if isinstance(b64_content, bytes):
                        b64_content = b64_content.decode('ascii', errors='ignore')
                    b64_content = b64_content.strip()
                    # Decode to original bytes (binary-safe)
                    raw = _base64.b64decode(b64_content)
                    # Integrity check via md5
                    expected_md5 = o.get("md5")
                    if expected_md5:
                        import hashlib as _hl
                        actual_md5 = _hl.md5(raw).hexdigest()
                        if actual_md5 != expected_md5:
                            logger.warning(f"MD5 mismatch for {o.get('path')}: expected {expected_md5} got {actual_md5}")
                    # Attach decoded bytes for downstream consumer
                    o["content_bytes"] = raw
                except Exception as e:
                    logger.warning(f"Base64 read failed for {o.get('path')}: {e}")
        except Exception as e:
            logger.warning(f"Manifest read failed: {e}")
            # Fallback: if stderr has content, assume non-zero
            if stderr.strip():
                exit_code = 1
            else:
                exit_code = 0

        return {
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "state": "completed",
            "output_files": outputs,  # [{path, size}, ...] — caller can use this directly
        }
    except asyncio.TimeoutError:
        return {"exit_code": 124, "stdout": "", "stderr": f"Execution timeout after {timeout}s", "state": "timeout", "output_files": []}
    except Exception as e:
        return {"exit_code": -1, "stdout": "", "stderr": f"Exception: {e}", "state": "error", "output_files": []}


# === ENVIRONMENT INTROSPECTION ===

async def check_libraries(sandbox) -> dict:
    """Check which Python libraries are installed — writes result to a file and reads it back.

    More reliable than log capture which can be empty even on success.
    """
    manifest = f"/tmp/lib_check_{uuid.uuid4().hex[:6]}.json"
    check_code = f"""
import importlib, json
libs = ['openpyxl', 'docx', 'pdfplumber', 'pypdf', 'reportlab', 'xlsxwriter', 'PIL', 'jinja2', 'dateutil', 'rapidfuzz', 'tabulate', 'pandas', 'numpy']
available = {{}}
for lib in libs:
    try:
        mod = importlib.import_module(lib)
        available[lib] = getattr(mod, '__version__', 'unknown')
    except ImportError:
        available[lib] = None
with open('{manifest}', 'w') as f:
    json.dump(available, f)
print('LIBS_CHECK_DONE')
"""
    result = await execute_python(sandbox, check_code, timeout=20)
    import json
    # Try reading from manifest file first (most reliable)
    try:
        content = await sandbox.fs.read(manifest)
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='ignore')
        return json.loads(content)
    except Exception:
        pass
    # Fallback to stdout parsing
    try:
        for line in (result.get("stdout") or "").splitlines():
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                return json.loads(line)
    except Exception:
        pass
    return {}


# === HIGH-LEVEL API ===

async def get_python_sandbox():
    """Public API: get (or create) a Python sandbox from the pool."""
    return await _get_or_create_py_sandbox()
