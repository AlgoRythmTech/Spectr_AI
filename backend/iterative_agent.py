"""
Iterative Agent Mode — multi-round Python exploration with progressive findings.

Unlike single-shot code_executor.py (LLM writes ONE script that does everything),
this agent breaks the task into rounds:

  Round 1: Explore — LLM writes Python that prints findings about the data
  Round 2: Analyze — Based on round 1 output, LLM writes next script with deeper analysis
  Round 3: Act — With full context, LLM writes final script that produces the deliverable
  Round 4: Verify — LLM validates output

Each round's stdout is fed into the next round's prompt, so the LLM progressively
builds understanding of messy/large/unknown data without needing to see everything.

Use this for:
- "Find the anomaly in this 50-col audit trial balance"
- "Figure out what's in this unknown CSV and build a reconciliation"
- "This sheet has weird structure — explore it and fix it"

NOT needed for:
- Simple generation ("make an NDA") — single-shot is fine
- Well-specified tasks ("sum column B") — single-shot is fine
"""
import os
import re
import json
import base64
import logging
from typing import Optional, AsyncGenerator

from code_sandbox import (
    get_python_sandbox, upload_file_to_sandbox, read_file_from_sandbox,
    execute_python, list_output_files,
)
from sheet_profiler import profile_uploaded_files

logger = logging.getLogger("iterative_agent")


EXPLORATION_PROMPT = """You are a senior Indian CA/lawyer data analyst. You're working iteratively — this is Round {round_num} of up to {max_rounds}.

Write a Python script that EXPLORES the data and prints findings. DO NOT produce final output files yet (unless this is the final round).

CURRENT GOAL: {goal}

CONTEXT FROM PREVIOUS ROUNDS:
{findings_so_far}

UPLOADED FILES PROFILE (from sheet_profiler):
{file_profile}

ROUND {round_num} MISSION:
{round_mission}

RULES:
- PRINT findings to stdout (LLM reads stdout to plan next round)
- Keep prints CONCISE — top 5-10 bullet points max
- Don't dump full data. Aggregate, sample, or summarize.
- Libraries available: openpyxl, pandas, numpy, pdfplumber, docx, rapidfuzz, reportlab, xlsxwriter
- Wrap pandas import in try/except (Alpine fallback)
- For numeric: use decimal.Decimal for money

Output ONE complete Python script. No markdown fences. Just runnable Python."""


FINAL_ROUND_PROMPT = """You are a senior Indian CA/lawyer data analyst. This is the FINAL round.

Based on everything we've learned, write the Python script that produces the DELIVERABLE(s).

ORIGINAL GOAL: {goal}

EVERYTHING LEARNED:
{findings_so_far}

UPLOADED FILES PROFILE:
{file_profile}

FINAL ROUND MISSION:
{round_mission}

OUTPUT REQUIREMENTS:
- Write files to /workspace/output/
- Use FORMULAS not hardcoded values in Excel
- Use Decimal for money
- Format currency as #,##0.00
- Add validation checks and print 'VALIDATION_PASSED' if OK
- Print a concise success summary with what was created

Output ONE complete Python script."""


ROUND_PLAN_PROMPT = """You are planning an iterative data analysis session.

USER GOAL: {goal}

UPLOADED FILES PROFILE:
{file_profile}

Plan {max_rounds} rounds of Python exploration. Each round should build on the previous.

Output ONLY a JSON array of mission statements:
[
  "Round 1 mission description",
  "Round 2 mission description",
  ...
]

GUIDELINES:
- Round 1: Structure discovery + data sanity (header detection, type check, row counts, obvious issues)
- Round 2: Semantic understanding (what do the columns mean? what's the business context?)
- Round 3: Core analysis (reconciliation / aggregation / filtering / pattern detection)
- Round 4 (final): Produce deliverable file(s) + verification

Return ONLY the JSON array — no explanation."""


async def _llm_call(prompt: str, system: str = "", model: str = "auto", max_tokens: int = 4000) -> str:
    """Unified LLM call with provider cascade."""
    import aiohttp

    GROQ_KEY = os.environ.get("GROQ_KEY", "")
    GOOGLE_AI_KEY = os.environ.get("GOOGLE_AI_KEY", "")
    ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    OPENAI_KEY = os.environ.get("OPENAI_KEY") or os.environ.get("OPENAI_API_KEY", "")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # Gemini 2.5 Pro first
    if GOOGLE_AI_KEY:
        for model_name in ("gemini-2.5-pro", "gemini-2.5-flash"):
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GOOGLE_AI_KEY}",
                        json={
                            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                            "systemInstruction": {"parts": [{"text": system}]} if system else None,
                            "generationConfig": {"temperature": 0.2, "maxOutputTokens": max_tokens},
                        },
                        timeout=aiohttp.ClientTimeout(total=60),
                    ) as r:
                        if r.status == 200:
                            d = await r.json()
                            c = d.get("candidates", [])
                            if c and c[0].get("content", {}).get("parts"):
                                return c[0]["content"]["parts"][0].get("text", "")
            except Exception:
                continue

    # Groq cascade
    if GROQ_KEY:
        for m in ("llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "llama3-70b-8192", "llama-3.1-8b-instant"):
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                        json={"model": m, "messages": messages, "temperature": 0.2, "max_tokens": max_tokens},
                        timeout=aiohttp.ClientTimeout(total=45),
                    ) as r:
                        if r.status == 200:
                            d = await r.json()
                            return d["choices"][0]["message"]["content"]
            except Exception:
                continue

    # OpenAI
    if OPENAI_KEY:
        for m in ("gpt-4o", "gpt-4o-mini"):
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
                        json={"model": m, "messages": messages, "temperature": 0.2, "max_tokens": max_tokens},
                        timeout=aiohttp.ClientTimeout(total=60),
                    ) as r:
                        if r.status == 200:
                            d = await r.json()
                            return d["choices"][0]["message"]["content"]
            except Exception:
                continue

    raise RuntimeError("All LLM providers failed")


def _extract_code(text: str) -> str:
    m = re.search(r'```(?:python|py)?\s*\n(.*?)```', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


async def _plan_rounds(goal: str, file_profile: str, max_rounds: int = 4) -> list[str]:
    """Ask LLM to decompose the task into N rounds."""
    prompt = ROUND_PLAN_PROMPT.format(goal=goal, file_profile=file_profile[:3000], max_rounds=max_rounds)
    try:
        text = await _llm_call(prompt, max_tokens=600)
        # Extract JSON array
        m = re.search(r'\[[\s\S]*?\]', text)
        if m:
            missions = json.loads(m.group(0))
            if isinstance(missions, list) and missions:
                return [str(m) for m in missions[:max_rounds]]
    except Exception as e:
        logger.warning(f"Round planning failed: {e}")

    # Fallback: generic 4-round plan
    return [
        "Explore the uploaded files. Print structure, column types, anomalies, row counts, and any obvious data quality issues.",
        "Understand the business context. Infer what each column represents, spot relationships between columns/sheets, and note any domain-specific patterns (GST, TDS, party names, etc).",
        "Perform the core analysis the user asked for. Print preliminary findings.",
        "Produce the final deliverable file(s) and validate correctness.",
    ][:max_rounds]


async def run_iterative_agent(
    user_goal: str,
    uploaded_files: list[dict],
    max_rounds: int = 4,
) -> AsyncGenerator[dict, None]:
    """Main entry point. Runs a multi-round exploration + delivery loop.

    Yields SSE-style events so frontend can show progress per round.
    """
    yield {"type": "status", "step": "start", "message": f"Iterative agent starting ({max_rounds} rounds planned)"}

    # 1. Generate file profiles (compact, LLM-ready)
    yield {"type": "status", "step": "profiling", "message": "Generating smart data profile..."}
    file_profile_text = profile_uploaded_files(uploaded_files, max_total_chars=6000) if uploaded_files else "(no files uploaded)"
    yield {"type": "profile", "file_profile": file_profile_text, "chars": len(file_profile_text)}

    # 2. Plan rounds
    yield {"type": "status", "step": "planning", "message": "Planning exploration rounds..."}
    missions = await _plan_rounds(user_goal, file_profile_text, max_rounds=max_rounds)
    yield {"type": "plan", "missions": missions, "rounds": len(missions)}

    # 3. Get sandbox
    try:
        sandbox = await get_python_sandbox()
    except Exception as e:
        yield {"type": "error", "message": f"Sandbox creation failed: {e}"}
        return

    # 4. Upload files
    if uploaded_files:
        for f in uploaded_files:
            try:
                await upload_file_to_sandbox(sandbox, f["filename"], f["content"], subdir="input")
            except Exception as e:
                logger.warning(f"Upload {f['filename']} failed: {e}")

    # 5. Round-by-round execution
    findings_so_far = ""
    final_output_files = []

    for round_idx, mission in enumerate(missions, 1):
        is_final = round_idx == len(missions)
        yield {"type": "round_start", "round": round_idx, "mission": mission, "is_final": is_final}

        # Build prompt for this round
        prompt_template = FINAL_ROUND_PROMPT if is_final else EXPLORATION_PROMPT
        prompt = prompt_template.format(
            round_num=round_idx,
            max_rounds=len(missions),
            goal=user_goal,
            findings_so_far=findings_so_far[:4000] if findings_so_far else "(Round 1 — no prior findings yet)",
            file_profile=file_profile_text[:3000],
            round_mission=mission,
        )

        # Generate Python
        yield {"type": "status", "step": f"round_{round_idx}_llm", "message": f"Round {round_idx}: LLM planning code..."}
        try:
            raw = await _llm_call(prompt, max_tokens=4000)
            code = _extract_code(raw)
        except Exception as e:
            yield {"type": "error", "round": round_idx, "message": f"LLM generation failed: {e}"}
            return

        yield {"type": "code", "round": round_idx, "code_length": len(code)}

        # Execute
        yield {"type": "status", "step": f"round_{round_idx}_exec", "message": f"Round {round_idx}: running Python..."}
        exec_result = await execute_python(sandbox, code, timeout=180)

        # Record findings (stdout + any errors)
        round_findings = f"--- Round {round_idx}: {mission[:80]} ---\n"
        if exec_result["exit_code"] == 0:
            round_findings += f"STDOUT:\n{exec_result.get('stdout', '')[:3000]}\n"
        else:
            round_findings += f"ERROR (exit {exec_result['exit_code']}):\n{exec_result.get('stderr', '')[:2000]}\n"
            # Retry this round once with error context
            yield {"type": "round_retry", "round": round_idx, "message": "Retrying with error context..."}
            retry_prompt = prompt + f"\n\nPREVIOUS ATTEMPT FAILED:\n{exec_result.get('stderr', '')[:1500]}\nFix and retry."
            try:
                raw2 = await _llm_call(retry_prompt, max_tokens=4000)
                code2 = _extract_code(raw2)
                exec_result = await execute_python(sandbox, code2, timeout=180)
                if exec_result["exit_code"] == 0:
                    round_findings = f"--- Round {round_idx} (retry): {mission[:80]} ---\nSTDOUT:\n{exec_result.get('stdout', '')[:3000]}\n"
            except Exception as e:
                yield {"type": "error", "round": round_idx, "message": f"Retry failed: {e}"}
                return

        yield {
            "type": "round_complete",
            "round": round_idx,
            "exit_code": exec_result["exit_code"],
            "stdout_preview": exec_result.get("stdout", "")[:500],
            "output_files_found": len(exec_result.get("output_files", [])),
        }

        # Accumulate findings (capped)
        findings_so_far += round_findings + "\n"
        if len(findings_so_far) > 8000:
            # Keep most recent findings
            findings_so_far = findings_so_far[-8000:]

        # Collect output files (mostly final round)
        if is_final:
            for info in (exec_result.get("output_files") or []):
                content = info.get("content_bytes")
                if content is None:
                    try:
                        content = await read_file_from_sandbox(sandbox, info.get("path"))
                        if isinstance(content, str):
                            content = content.encode('utf-8', errors='surrogateescape')
                    except Exception:
                        continue
                final_output_files.append({
                    "name": os.path.basename(info.get("path", "")),
                    "path": info.get("path", ""),
                    "size": info.get("size", len(content) if content else 0),
                    "content_b64": base64.b64encode(content).decode('ascii') if content else "",
                })

    # 6. Final response
    if final_output_files:
        # Validate
        try:
            from output_validator import validate_all_outputs
            validation = validate_all_outputs(final_output_files)
        except Exception as e:
            logger.warning(f"Validation failed: {e}")
            validation = {"all_valid": True, "results": [], "summary": ""}

        yield {
            "type": "success",
            "files": final_output_files,
            "rounds_run": len(missions),
            "validation": validation,
            "findings_summary": findings_so_far[-2000:],
        }
    else:
        yield {
            "type": "completed_no_files",
            "rounds_run": len(missions),
            "findings_summary": findings_so_far[-3000:],
            "message": "Iterative exploration complete, no deliverable files produced (exploratory mode).",
        }


async def run_iterative_task(user_goal: str, uploaded_files: list[dict], max_rounds: int = 4) -> dict:
    """Non-streaming wrapper."""
    events = []
    final = {"status": "error", "files": [], "findings": ""}
    async for event in run_iterative_agent(user_goal, uploaded_files, max_rounds):
        events.append(event)
        if event.get("type") == "success":
            final = {
                "status": "success",
                "files": event.get("files", []),
                "validation": event.get("validation", {}),
                "rounds_run": event.get("rounds_run", 0),
                "findings": event.get("findings_summary", ""),
            }
        elif event.get("type") == "completed_no_files":
            final = {
                "status": "completed",
                "files": [],
                "findings": event.get("findings_summary", ""),
                "rounds_run": event.get("rounds_run", 0),
            }
        elif event.get("type") == "error":
            final["error"] = event.get("message")
    final["events_count"] = len(events)
    return final
