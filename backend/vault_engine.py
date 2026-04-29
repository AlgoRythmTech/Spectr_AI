"""
Vault Engine — Deep Document Intelligence.
Reads massive legal/financial documents and produces forensic-grade analysis.
Uses structured reasoning to find what junior CAs and lawyers miss.
"""
import os
import re
import logging
import asyncio
import aiohttp
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json

logger = logging.getLogger("vault_engine")
vault_router = APIRouter()

GROQ_KEY_LIVE = os.environ.get("GROQ_KEY", "")
GOOGLE_AI_KEY = os.environ.get("GOOGLE_AI_KEY", "")


class VaultAnalysisRequest(BaseModel):
    vault_id: str
    documents: List[dict]
    analysis_type: str
    custom_prompt: Optional[str] = None


_ACTIVE_VAULTS = {}

VAULT_REASONING_PREAMBLE = """BEFORE generating any output, you MUST perform these internal reasoning steps:

1. CLASSIFY each document: What type is it? (judgment, contract, notice, financial report, ledger, etc.)
2. CROSS-VERIFY numbers: If Amount X appears in one document and Amount Y in another for the same item, FLAG the discrepancy.
3. TRACE every date: Extract dates, calculate their legal significance (limitation, deadlines, effective dates).
4. MAP obligations: Who must do what, by when, with what penalty for failure.
5. FIND hidden risks: Unsigned schedules, missing annexures, contradictions between parts, ambiguous language.
6. CITE the law: Every statute, rule, or principle applicable — with exact section numbers.
"""


def get_system_prompt_for_type(analysis_type: str) -> str:
    base_expert = (
        "You are a forensic document analyst with 30 years of Indian litigation and audit experience. "
        "Your output is a DELIVERABLE REFERENCE DOCUMENT that a Senior Partner will forward to clients.\n\n"
        f"{VAULT_REASONING_PREAMBLE}\n"
    )

    if analysis_type == "timeline":
        return f"""{base_expert}
TASK: Extract a perfect Chronological Timeline of Events from ALL documents.

OUTPUT FORMAT (Markdown table):
| Date | Event Description | Source Document | Legal Significance |
|---|---|---|---|

RULES:
- Never hallucinate dates. If ambiguous, state the ambiguity explicitly.
- Sort chronologically oldest to newest.
- For each event, state its legal significance (limitation trigger, deadline, effective date, breach date, etc.).
- Calculate days between critical events (e.g., "Notice served on X, reply due in 30 days = deadline Y").
- Flag events that are MISSING but should exist (e.g., no acknowledgment of receipt for a notice)."""

    elif analysis_type == "contradictions":
        return f"""{base_expert}
TASK: Find EVERY contradiction, discrepancy, and inconsistency across documents.

You are preparing a cross-examination strategy. Find what the opposing side is hiding.

OUTPUT FORMAT:
For each contradiction found:
> **Document A** ({doc_name}): "[exact quote or figure]"
> **Document B** ({doc_name}): "[contradicting quote or figure]"
> **Significance**: [Why this matters legally/financially]
> **Cross-examination question**: [The devastating question to ask]

RULES:
- Compare amounts across documents — even small differences (Rs 100) can indicate manipulation.
- Compare dates — inconsistent timelines suggest fabrication.
- Compare party names and designations — different representations of authority.
- Check internal arithmetic — do the numbers in tables actually add up?
- Flag missing documents that SHOULD exist based on references in other documents."""

    elif analysis_type == "night_before":
        return f"""{base_expert}
TASK: Produce a "Night Before" Hearing Digest. The Senior Advocate has 3 MINUTES to read this before walking into the tribunal.

MANDATORY STRUCTURE:

## 1. THE BLUF (Bottom Line Up Front)
3 crisp sentences: What is the dispute? What is the strongest argument? What is the ask?

## 2. FATAL ERRORS BY THE OTHER SIDE
Bulleted list of 3-5 major procedural or factual errors. Each must cite the specific document and page/paragraph.

## 3. MASTER PRECEDENT MATRIX
| Point of Law | Our Strongest Case | Ratio (1 sentence) | Court |
For each legal issue, the single best case to cite.

## 4. OPENING ARGUMENT SCRIPT (3 minutes)
A literal script: "My Lords, this matter concerns..." Written in first person, ready to be read aloud.

## 5. ANTICIPATED QUESTIONS FROM BENCH
3 likely questions the judge will ask, with prepared answers."""

    else:  # custom_query
        return f"""{base_expert}
Answer the user's specific query by forensically cross-referencing all provided documents.
- Cite specific document names and page/paragraph references.
- If the answer requires information not in the documents, say so explicitly.
- If documents contain contradictory answers, present BOTH and explain which is more reliable and why."""


@vault_router.post("/stream-analyze")
async def analyze_vault_stream(req: Request):
    """Deep document analysis with streaming response."""
    data = await req.json()
    documents = data.get("documents", [])
    analysis_type = data.get("analysis_type", "timeline")
    custom_prompt = data.get("custom_prompt", "")

    if not documents:
        raise HTTPException(status_code=400, detail="Vault is empty.")

    mega_context = "=== VAULT CONTENTS ===\n\n"
    for idx, doc in enumerate(documents):
        mega_context += f"--- DOCUMENT {idx+1}: {doc.get('filename', 'Unknown')} ---\n"
        mega_context += f"{doc.get('content', '')[:20000]}\n\n"

    system_prompt = get_system_prompt_for_type(analysis_type)

    user_prompt = "Execute the required analysis on the Vault Contents below.\n\n"
    if analysis_type == "custom_query" and custom_prompt:
        user_prompt = f"USER INSTRUCTION: {custom_prompt}\n\n"

    user_prompt += mega_context

    async def stream_generator():
        async with aiohttp.ClientSession() as session:
            yield json.dumps({"type": "vault_status", "status": "Reading documents..."}) + "\n"

            # Try Gemini first (longer context, web grounding)
            used_gemini = False
            if GOOGLE_AI_KEY:
                try:
                    yield json.dumps({"type": "vault_status", "status": "Deep forensic analysis in progress..."}) + "\n"

                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GOOGLE_AI_KEY}"
                    payload = {
                        "system_instruction": {"parts": [{"text": system_prompt}]},
                        "contents": [{"role": "user", "parts": [{"text": user_prompt[:200000]}]}],
                        "generationConfig": {"temperature": 0.08, "maxOutputTokens": 16384}
                    }
                    async with session.post(
                        url, headers={"Content-Type": "application/json"},
                        json=payload, timeout=aiohttp.ClientTimeout(total=120)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                            full_text = "\n".join([p.get("text", "") for p in parts if "text" in p])
                            if full_text:
                                # Strip internal strategy tags
                                full_text = re.sub(r'<internal_strategy>.*?</internal_strategy>', '', full_text, flags=re.DOTALL).strip()
                                # Stream in chunks for smooth UI
                                chunk_size = 200
                                for i in range(0, len(full_text), chunk_size):
                                    yield json.dumps({"type": "vault_chunk", "content": full_text[i:i+chunk_size]}) + "\n"
                                used_gemini = True
                        else:
                            logger.warning(f"Gemini vault analysis failed ({resp.status})")
                except Exception as e:
                    logger.warning(f"Gemini vault error: {e}")

            # Fallback: Groq streaming
            if not used_gemini and GROQ_KEY_LIVE:
                yield json.dumps({"type": "vault_status", "status": "Executing document cross-examination..."}) + "\n"

                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt[:25000]}
                    ],
                    "temperature": 0.08,
                    "max_tokens": 8192,
                    "stream": True
                }
                try:
                    async with session.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {GROQ_KEY_LIVE}", "Content-Type": "application/json"},
                        json=payload, timeout=aiohttp.ClientTimeout(total=60)
                    ) as resp:
                        if resp.status != 200:
                            err = await resp.text()
                            yield json.dumps({"type": "vault_chunk", "content": f"Vault Error: {err}"}) + "\n"
                            return

                        async for chunk in resp.content:
                            if chunk:
                                chunk_str = chunk.decode('utf-8').strip()
                                if chunk_str.startswith('data: ') and chunk_str != 'data: [DONE]':
                                    try:
                                        data_json = json.loads(chunk_str[6:])
                                        delta = data_json['choices'][0]['delta'].get('content', '')
                                        if delta:
                                            yield json.dumps({"type": "vault_chunk", "content": delta}) + "\n"
                                    except Exception:
                                        pass
                except Exception as e:
                    logger.error(f"Groq vault stream error: {e}")
                    yield json.dumps({"type": "vault_chunk", "content": f"\n\n**Error:** {str(e)}"}) + "\n"

            yield json.dumps({"type": "vault_complete"}) + "\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")
