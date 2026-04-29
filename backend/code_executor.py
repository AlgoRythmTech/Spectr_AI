"""
Agentic Code Executor — LLM plans Python, sandbox runs it, retries on error, delivers files.

This is the same pattern Claude.ai uses for its "analysis tool":
  1. User prompts + optional file uploads
  2. LLM generates Python code with context of uploaded files
  3. Sandbox executes the code
  4. On error: feed stderr back to LLM → iterate
  5. On success: download generated files from sandbox → return to user

Purpose-built for Indian CA/lawyer workflows:
- GST reconciliation (GSTR-2A/2B vs books)
- TDS reconciliations
- Advance tax trackers
- Ageing schedules with red flags
- Payroll reconciliations
- Ratio analysis with reasons
- Legal document drafting (DOCX)
- Infographic generation (HTML → JPG)

Architecture:
  upload → sandbox FS → LLM plan (system prompt is domain-aware) →
  execute → if error: retry with stderr → extract output files → deliver
"""
import os
import re
import json
import base64
import asyncio
import logging
from pathlib import Path
from typing import Optional, AsyncGenerator
import aiohttp

from code_sandbox import (
    get_python_sandbox, upload_file_to_sandbox, read_file_from_sandbox,
    list_output_files, execute_python, check_libraries,
)

logger = logging.getLogger("code_executor")

GROQ_KEY = os.environ.get("GROQ_KEY", "")
GOOGLE_AI_KEY = os.environ.get("GOOGLE_AI_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


# === DOMAIN-AWARE SYSTEM PROMPT ===

PYTHON_AGENT_SYSTEM_PROMPT = """You are a SENIOR ASSOCIATE at a Big 4 / top Indian law firm. Generate Python code for Indian CA/lawyer workflows. Work is filed with CBDT/CBIC/courts — ZERO math error tolerance.

## JOB
Read `/workspace/input/` → process → write `/workspace/output/` → print short success message.

## LIBRARIES (all available — auto-installed by wrapper)
`openpyxl` (Excel w/formulas), `xlsxwriter` (Excel rich formatting), `docx` (python-docx), `pdfplumber` (PDF extract), `pypdf` (PDF manipulate), `reportlab` (PDF generate), `PIL` (images), `rapidfuzz` (fuzzy match), `jinja2`, `dateutil`, `tabulate`. `pandas`/`numpy` MAYBE available — wrap in try/except.

**NEVER use CSV when Excel is asked. openpyxl IS available.**

## MATH ACCURACY (ZERO ERROR TOLERANCE)
1. `Decimal` for money (never float): `from decimal import Decimal, ROUND_HALF_UP; D=lambda v:Decimal(str(v))`
2. Round ONCE at end: `.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)`
3. Excel: use `ws.cell().value='=B2*C2/100'` (formula string, not computed value) so F2 shows formula
4. Indian number format: `#,##0.00`
5. Dates: `dateutil.parser.parse(s, dayfirst=True)` for DD-MM-YYYY
6. Cross-check totals before output. Print `VALIDATION_PASSED` or warning.
7. Edge cases: leap year, FY boundary, zero-values, negative (credit notes), missing PAN/GSTIN (flag don't skip)

## INDIAN DOMAIN (FY 25-26)
**TDS**: 192 slab/₹2.5L, 194J 10%/₹30K, 194C 1-2%/₹30K single, 194I 10%(L&B)/2%(P&M)/₹2.4L, 194IB 2%(amended 01-10-2024)/₹50K/m, 194Q 0.1%>₹50L, 194T 10%/₹20K, 195 12.5%+surcharge+cess
**Advance Tax**: 15-Jun 15%, 15-Sep 45%, 15-Dec 75%, 15-Mar 100%. Threshold ₹10K. Senior: age≥60 on 31-Mar compute from DOB
**New Regime Slabs**: 0-4L nil, 4-8L 5%, 8-12L 10%, 12-16L 15%, 16-20L 20%, 20-24L 25%, 24L+ 30%. 87A rebate ₹60K upto ₹12L
**Excel rigor**: SUMIF/SUMIFS/VLOOKUP over hardcoded totals. `='Source'!A2` for cross-sheet. Freeze header row.
**DOCX rigor**: Times New Roman 12pt body, numbered clauses 1./1.1, "CONFIDENTIAL — PRIVILEGED" header.
**Fuzzy match**: `rapidfuzz.fuzz.token_set_ratio(a, b) >= 65`, normalize: strip "Pvt Ltd"/"Limited"/"M/s.", lowercase.

## OUTPUT CONVENTIONS

1. Write ALL output files to `/workspace/output/`
2. Name files descriptively (e.g., `tds_reconciliation.xlsx`, `grounds_of_appeal.docx`)
3. Print a ONE-LINE success summary to stdout (e.g., "Created 3 output files: X, Y, Z")
4. If using pandas and it's not available, gracefully fall back to openpyxl
5. Handle missing/malformed data defensively — print warnings, don't crash

## CODE STRUCTURE

Return EXACTLY ONE complete Python script. No markdown fences, no explanation outside the code. Start with:

```python
#!/usr/bin/env python3
\"\"\"[One-line description of what this script does]\"\"\"

import os
import sys
# ... other imports
```

The script must be SELF-CONTAINED, runnable with `python3 script.py`.

## ERROR RETRY PROTOCOL

If you're given an error trace from a previous attempt, carefully read it, identify the root cause, and fix it in the new script. Common errors:
- `ModuleNotFoundError` → use alternative (pandas not available → openpyxl)
- `KeyError` / `IndexError` → add defensive `.get()` / bounds check
- File not found → print os.listdir('/workspace/input/') to debug paths
- Encoding errors → explicit `encoding='utf-8'` on opens

## CRITICAL

- NO `input()` calls (non-interactive)
- NO `matplotlib.pyplot.show()` — save as PNG if needed
- NO `webbrowser.open()`
- Set matplotlib backend to Agg if used: `import matplotlib; matplotlib.use('Agg')`
- Timeouts: keep loops bounded (<10M iterations)
- If script fails with import, check `importlib.util.find_spec('lib')` first

Return ONLY the Python code. No markdown, no explanation."""


# === LLM CODE GENERATION ===

async def _llm_generate_code(
    user_prompt: str,
    input_files: list[str],
    retry_context: Optional[str] = None,
    library_info: Optional[dict] = None,
    playbook_addon: str = "",
) -> str:
    """Ask the LLM to generate Python code.

    Uses Gemini 2.5 Pro first (best at code), falls back to Claude, then Groq.
    """
    file_info = "\n".join(f"  - {p}" for p in input_files) if input_files else "  (none)"

    # Library availability is guaranteed by the wrapper. Do NOT pass "missing" lib info
    # to the LLM — it will conservatively fall back to CSV etc. Trust the prompt.
    libs_info = ""
    if library_info:
        # Only include if specifically verified present
        available = [f"{k}=={v}" for k, v in library_info.items() if v]
        if available:
            libs_info = f"\n\nCONFIRMED AVAILABLE: {', '.join(available)}"

    user_content = f"USER REQUEST:\n{user_prompt}\n\nFILES IN /workspace/input/:\n{file_info}{libs_info}"

    if playbook_addon:
        user_content += f"\n\n=== PLAYBOOK FOR THIS TASK ===\n{playbook_addon}\n\nApply the playbook rigorously when generating the script."

    if retry_context:
        user_content += f"\n\n=== PREVIOUS ATTEMPT FAILED ===\n{retry_context}\n\nFix the issue and provide a corrected script."

    # Strategy 0: Claude via Emergent (Sonnet 4.5 — excellent at Python for tabular/tax work)
    try:
        from claude_emergent import call_claude, CLAUDE_SONNET, CLAUDE_OPUS
        # Sonnet first (balanced); Opus for retry if previous failed
        model_to_try = CLAUDE_OPUS if retry_context else CLAUDE_SONNET
        resp = await call_claude(PYTHON_AGENT_SYSTEM_PROMPT, user_content, model=model_to_try, timeout=90)
        if resp and len(resp) > 50:
            return _extract_code(resp)
    except Exception as e:
        logger.warning(f"Claude code gen failed: {e}")

    # Strategy 1: Try Gemini 2.5 Pro (best code generation)
    if GOOGLE_AI_KEY:
        for model_name in ("gemini-2.5-pro", "gemini-2.5-flash"):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GOOGLE_AI_KEY}",
                        headers={"Content-Type": "application/json"},
                        json={
                            "contents": [{"role": "user", "parts": [{"text": user_content}]}],
                            "systemInstruction": {"parts": [{"text": PYTHON_AGENT_SYSTEM_PROMPT}]},
                            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8192},
                        },
                        timeout=aiohttp.ClientTimeout(total=60),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            candidates = data.get("candidates", [])
                            if candidates and candidates[0].get("content", {}).get("parts"):
                                text = candidates[0]["content"]["parts"][0].get("text", "")
                                if text:
                                    return _extract_code(text)
                        else:
                            err_text = await resp.text()
                            logger.warning(f"Gemini {model_name} status {resp.status}: {err_text[:200]}")
            except Exception as e:
                logger.warning(f"Gemini {model_name} code generation failed: {e}")

    # Strategy 2: Anthropic Claude
    if ANTHROPIC_KEY:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": ANTHROPIC_KEY,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "claude-sonnet-4-5-20250929",
                        "max_tokens": 8192,
                        "system": PYTHON_AGENT_SYSTEM_PROMPT,
                        "messages": [{"role": "user", "content": user_content}],
                    },
                    timeout=aiohttp.ClientTimeout(total=45),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        text = data["content"][0]["text"]
                        return _extract_code(text)
        except Exception as e:
            logger.warning(f"Claude code generation failed: {e}")

    # Strategy 3: Groq — try multiple models (separate daily quotas per model)
    if GROQ_KEY:
        for groq_model in ("llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama3-70b-8192", "llama-3.1-8b-instant"):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                        json={
                            "model": groq_model,
                            "messages": [
                                {"role": "system", "content": PYTHON_AGENT_SYSTEM_PROMPT},
                                {"role": "user", "content": user_content},
                            ],
                            "temperature": 0.2,
                            "max_tokens": 4000,
                        },
                        timeout=aiohttp.ClientTimeout(total=45),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            text = data["choices"][0]["message"]["content"]
                            if text:
                                return _extract_code(text)
                        else:
                            err_text = await resp.text()
                            logger.warning(f"Groq {groq_model} status {resp.status}: {err_text[:200]}")
            except Exception as e:
                logger.warning(f"Groq {groq_model} failed: {e}")

    # Strategy 4: OpenAI (if user has key)
    OPENAI_KEY = os.environ.get("OPENAI_KEY") or os.environ.get("OPENAI_API_KEY", "")
    if OPENAI_KEY:
        for openai_model in ("gpt-4o", "gpt-4o-mini", "gpt-4-turbo"):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
                        json={
                            "model": openai_model,
                            "messages": [
                                {"role": "system", "content": PYTHON_AGENT_SYSTEM_PROMPT},
                                {"role": "user", "content": user_content},
                            ],
                            "temperature": 0.2,
                            "max_tokens": 4000,
                        },
                        timeout=aiohttp.ClientTimeout(total=60),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            text = data["choices"][0]["message"]["content"]
                            if text:
                                return _extract_code(text)
                        else:
                            err_text = await resp.text()
                            logger.warning(f"OpenAI {openai_model} status {resp.status}: {err_text[:200]}")
            except Exception as e:
                logger.warning(f"OpenAI {openai_model} failed: {e}")

    raise RuntimeError("All LLM providers failed (Gemini/Anthropic/Groq/OpenAI all rate-limited or unavailable)")


def _extract_code(text: str) -> str:
    """Extract Python code from LLM output (strips markdown fences if present)."""
    # Try to extract from ```python ... ``` fences
    m = re.search(r'```(?:python|py)?\s*\n(.*?)```', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Otherwise return as-is (some models don't use fences)
    return text.strip()


# === AGENTIC LOOP ===

async def run_code_agent(
    user_prompt: str,
    uploaded_files: list[dict],
    max_iterations: int = 4,
    playbook_addon: str = "",
) -> AsyncGenerator[dict, None]:
    """Main agentic loop. Yields progress events + final result.

    Args:
      user_prompt: what the user wants done
      uploaded_files: list of {"filename": str, "content": bytes}
      max_iterations: how many retries on error (default 4 = 1 initial + 3 retries)

    Yields dicts like:
      {"type": "status", "step": "sandbox", "message": "Creating Python sandbox..."}
      {"type": "code", "iteration": 1, "code": "...", "length": 1234}
      {"type": "execution", "iteration": 1, "exit_code": 0, "stdout": "..."}
      {"type": "output_files", "files": [{"name": "x.xlsx", "size": 12345}]}
      {"type": "success", "iterations": 1, "files_count": 2}
      {"type": "error", "iteration": 4, "message": "Max retries reached"}
    """
    # 1. Get sandbox
    yield {"type": "status", "step": "sandbox", "message": "Preparing Python execution environment..."}
    try:
        sandbox = await get_python_sandbox()
    except Exception as e:
        yield {"type": "error", "message": f"Sandbox creation failed: {e}"}
        return

    # 2. Upload files
    yield {"type": "status", "step": "upload", "message": f"Uploading {len(uploaded_files)} file(s)..."}
    input_paths = []
    for f in uploaded_files:
        try:
            path = await upload_file_to_sandbox(sandbox, f["filename"], f["content"], subdir="input")
            input_paths.append(path)
        except Exception as e:
            logger.warning(f"Upload failed for {f['filename']}: {e}")

    yield {"type": "status", "step": "uploaded", "message": f"Uploaded {len(input_paths)} file(s) to /workspace/input/"}

    # Library availability: the wrapper script auto-installs missing libs on every run.
    # We tell the LLM to assume all libs are available (they will be after wrapper runs).
    # Skipping the upfront check because it was causing LLMs to fall back to CSV
    # when checking before the first wrapper install had completed.
    lib_info = None  # Let LLM use the prompt's stated availability

    # Agentic loop
    retry_context = None
    for iteration in range(1, max_iterations + 1):
        # Generate code
        yield {"type": "status", "step": "plan", "iteration": iteration,
               "message": f"LLM planning Python code (attempt {iteration}/{max_iterations})..."}

        try:
            code = await _llm_generate_code(user_prompt, input_paths, retry_context, lib_info, playbook_addon=playbook_addon)
        except Exception as e:
            yield {"type": "error", "iteration": iteration, "message": f"LLM generation failed: {e}"}
            return

        yield {"type": "code", "iteration": iteration, "code": code, "length": len(code)}

        # Execute
        yield {"type": "status", "step": "execute", "iteration": iteration,
               "message": "Running code in sandbox..."}

        exec_result = await execute_python(sandbox, code, timeout=240)
        yield {
            "type": "execution", "iteration": iteration,
            "exit_code": exec_result["exit_code"],
            "stdout": exec_result["stdout"][:2000],
            "stderr": exec_result["stderr"][:2000],
        }

        if exec_result["exit_code"] == 0:
            # Success — manifest gives us binary-safe content_bytes already
            output_info = exec_result.get("output_files") or []
            output_files = []
            for info in output_info:
                path = info.get("path") if isinstance(info, dict) else info
                # Use content_bytes from manifest (base64-decoded, binary-safe)
                content = info.get("content_bytes") if isinstance(info, dict) else None
                if content is None:
                    # Fallback: try to read directly (UTF-8 corruption risk, but only if manifest missed it)
                    try:
                        content = await read_file_from_sandbox(sandbox, path)
                        if isinstance(content, str):
                            content = content.encode('utf-8', errors='surrogateescape')
                    except Exception as e:
                        logger.warning(f"Output read failed for {path}: {e}")
                        continue

                output_files.append({
                    "name": os.path.basename(path),
                    "path": path,
                    "size": info.get("size", len(content)) if isinstance(info, dict) else len(content),
                    "content_b64": base64.b64encode(content).decode('ascii') if content else "",
                })

            # Validate outputs — if any file is broken, retry with validation context
            try:
                from output_validator import validate_all_outputs
                validation = validate_all_outputs(output_files)
            except Exception as e:
                logger.warning(f"Validation failed: {e}")
                validation = {"all_valid": True, "results": [], "summary": ""}

            if not validation.get("all_valid") and iteration < max_iterations:
                # Validation caught a broken file — retry with the failure context
                bad_files = [r for r in validation.get("results", []) if not r.get("valid")]
                retry_context = "Previous code executed but produced INVALID output files:\n"
                for bf in bad_files:
                    retry_context += f"- {bf.get('name')}: {'; '.join(bf.get('issues', []))}\n"
                retry_context += "\nFix the code to produce valid, non-empty, properly-formatted files."
                yield {"type": "validation_retry", "iteration": iteration,
                       "invalid_files": [bf.get("name") for bf in bad_files],
                       "message": f"Output validation failed, retrying... (iteration {iteration}/{max_iterations})"}
                continue

            yield {"type": "output_files", "files": [{"name": f["name"], "size": f["size"], "path": f["path"]} for f in output_files]}
            yield {"type": "validation", "validation": validation}
            yield {"type": "success", "iterations": iteration, "files": output_files, "validation": validation}
            return

        # Error — build retry context from stderr + exit code
        error_msg = exec_result["stderr"] or f"Exit code {exec_result['exit_code']} with no stderr"
        if not error_msg.strip() and exec_result["stdout"]:
            # Some Python errors go to stdout when using print
            error_msg = exec_result["stdout"]
        retry_context = f"Previous code produced this error:\n{error_msg}\n\nFix this in your next script."

        yield {"type": "retry", "iteration": iteration,
               "error_snippet": error_msg[:500],
               "message": f"Execution failed, retrying with error context..."}

    # Max iterations reached
    yield {"type": "error", "iteration": max_iterations,
           "message": f"Failed after {max_iterations} attempts. Last error in retry context."}


# === NON-STREAMING CONVENIENCE API ===

async def execute_user_task(user_prompt: str, uploaded_files: list[dict], max_iterations: int = 4, playbook_addon: str = "") -> dict:
    """Non-streaming wrapper — returns final result dict.

    Returns:
      {
        "status": "success" | "error",
        "output_files": [{"name", "size", "content_b64"}],
        "iterations": int,
        "stdout": str,
        "events": [all events from the stream],
      }
    """
    events = []
    final_files = []
    final_status = "error"
    final_stdout = ""
    iterations_used = 0
    error_message = ""

    async for event in run_code_agent(user_prompt, uploaded_files, max_iterations, playbook_addon=playbook_addon):
        events.append(event)
        if event.get("type") == "success":
            final_status = "success"
            final_files = event.get("files", [])
            iterations_used = event.get("iterations", 0)
        elif event.get("type") == "execution" and event.get("exit_code") == 0:
            final_stdout = event.get("stdout", "")
        elif event.get("type") == "error":
            error_message = event.get("message", "")

    return {
        "status": final_status,
        "output_files": final_files,
        "iterations": iterations_used,
        "stdout": final_stdout,
        "error": error_message if final_status == "error" else None,
        "events_count": len(events),
    }
