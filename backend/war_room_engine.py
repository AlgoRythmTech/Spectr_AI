"""
War Room Engine — Deep Reasoning Architecture.
Single-model deep reasoning with structured phases, not multi-model averaging.
Produces streaming responses: fast baseline → deep analysis with citations.
"""
import os
import asyncio
import aiohttp
import json
import logging
import re
from citation_linker import find_citation_links
from ai_engine import ASSOCIATE_SYSTEM_PROMPT, TOOL_DESCRIPTIONS_FOR_PROMPT, auto_detect_tools_needed, execute_agent_tool, format_tool_results

def extract_sections(text: str) -> list:
    if not text: return []
    return list(set(re.findall(r'Section \d+[A-Z]*', text)))

logger = logging.getLogger("war_room")

from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / '.env')

GROQ_KEY_LIVE = os.environ.get("GROQ_KEY", "")
GOOGLE_AI_KEY = os.environ.get("GOOGLE_AI_KEY", "")
OPENAI_KEY = os.environ.get("OPENAI_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


DEEP_REASONING_PROMPT = """You are generating a FINAL DELIVERABLE DOCUMENT — not a chat reply. A senior professional will save this, forward it to colleagues, and make decisions based on it.

BEFORE WRITING, you MUST complete these reasoning phases:

**PHASE 1 — DECOMPOSE**: What exact legal/tax issues are embedded? What jurisdiction and time period? What statutes DIRECTLY apply?

**PHASE 2 — VERIFY CURRENCY**: For every provision, is this the CURRENT version? Check amendment dates. Rule 36(4) was AMENDED not removed (01-01-2022). GSTR-9C is self-certified from FY 2020-21. Section 194T is NEW from 01-04-2025. BNS/BNSS/BSA apply only from 01-07-2024.

**PHASE 3 — ADVERSARIAL**: What will the Revenue/opposing counsel argue? What's the weakest point? Pre-emptively rebut.

**PHASE 4 — QUANTIFY**: Calculate exact numbers — penalties, interest, limitation deadlines, exposure amounts. Show the math.

**PHASE 5 — SELF-CHECK**:
- Every section number: current version?
- Every case: actually exists?
- Every calculation: math verified?
- No FEMA/PMLA unless facts warrant it?

MANDATORY OUTPUT STRUCTURE:

## I. CORE ISSUE CLASSIFICATION
The precise legal question, classified under statute and jurisdiction.

## II. COMPLETE STATUTORY FRAMEWORK
| Section | Provision | Applicability | Key Threshold/Limit |
Every applicable section, sub-section, proviso, and rule.

## III. LEADING CASE LAW
For each point: Case Name, Year, Citation, ratio in 1-2 sentences. Minimum 3 cases.

## IV. QUANTIFIED RISK ASSESSMENT
| Scenario | Principal | Interest | Penalty | Total |
Best-case, worst-case, most-likely.

## V. MULTI-TRACK DEFENSE STRATEGY
Primary defense → Secondary → Procedural. With specific case law backing each.

## VI. IMMEDIATE ACTION PROTOCOL
Numbered list: what to do in the next 48 hours with specific deadlines.

## VII. CRITICAL WARNINGS
What goes catastrophically wrong if ignored.

RULES:
- Every factual claim MUST have a section number or case citation
- Use RICH MARKDOWN: ## Headers, **bold**, > blockquotes, | tables |, numbered lists
- If panels contradict on a legal point, state which position is stronger and why
- For greetings or non-legal queries, respond with a single professional sentence only
"""


async def call_groq_fast(session, system_instruction, user_content):
    """Fast baseline via Groq LLaMA 70B."""
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": "Provide a direct, substantive answer. Start with the conclusion. Cite sections. Use markdown.\n\n" + user_content[:15000]}
        ],
        "temperature": 0.08,
        "max_tokens": 4096
    }
    try:
        async with session.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY_LIVE}", "Content-Type": "application/json"},
            json=payload, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Groq fast error: {e}")
    return ""


async def call_deep_reasoning(session, system_instruction, user_content):
    """Deep reasoning: Gemini 2.5 Pro (thinking) → Flash → Claude → GPT-4o → Groq."""
    reasoning_content = DEEP_REASONING_PROMPT + "\n\nUSER QUERY + CONTEXT:\n" + user_content[:50000]

    # === TIER 1: Gemini 2.5 Pro with thinking (best deep reasoning available) ===
    if GOOGLE_AI_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GOOGLE_AI_KEY}"
            payload = {
                "system_instruction": {"parts": [{"text": system_instruction}]},
                "contents": [{"role": "user", "parts": [{"text": reasoning_content}]}],
                "tools": [{"googleSearch": {}}],
                "generationConfig": {"temperature": 0.05, "maxOutputTokens": 16384, "thinkingConfig": {"thinkingBudget": 8192}}
            }
            async with session.post(
                url, headers={"Content-Type": "application/json"},
                json=payload, timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    candidate = data.get("candidates", [{}])[0]
                    parts = candidate.get("content", {}).get("parts", [])
                    text_output = "\n".join([p.get("text", "") for p in parts if "text" in p])

                    grounding = candidate.get("groundingMetadata", {})
                    web_chunks = grounding.get("groundingChunks", [])
                    if web_chunks:
                        urls = list(set(c.get("web", {}).get("uri", "") for c in web_chunks if c.get("web", {}).get("uri")))
                        if urls:
                            text_output += "\n\n---\n**Live Sources Verified:**\n"
                            for u in urls[:10]:
                                text_output += f"- {u}\n"

                    return text_output
                else:
                    err = await resp.text()
                    logger.warning(f"Gemini 2.5 Pro failed ({resp.status}): {err[:200]}")
        except Exception as e:
            logger.warning(f"Gemini 2.5 Pro error: {e}")

    # === TIER 2: Gemini 2.5 Flash (fast, web-grounded fallback) ===
    if GOOGLE_AI_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GOOGLE_AI_KEY}"
            payload = {
                "system_instruction": {"parts": [{"text": system_instruction}]},
                "contents": [{"role": "user", "parts": [{"text": reasoning_content}]}],
                "tools": [{"googleSearch": {}}],
                "generationConfig": {"temperature": 0.05, "maxOutputTokens": 16384}
            }
            async with session.post(
                url, headers={"Content-Type": "application/json"},
                json=payload, timeout=aiohttp.ClientTimeout(total=90)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    candidate = data.get("candidates", [{}])[0]
                    parts = candidate.get("content", {}).get("parts", [])
                    text_output = "\n".join([p.get("text", "") for p in parts if "text" in p])

                    grounding = candidate.get("groundingMetadata", {})
                    web_chunks = grounding.get("groundingChunks", [])
                    if web_chunks:
                        urls = list(set(c.get("web", {}).get("uri", "") for c in web_chunks if c.get("web", {}).get("uri")))
                        if urls:
                            text_output += "\n\n---\n**Live Sources Verified:**\n"
                            for u in urls[:10]:
                                text_output += f"- {u}\n"

                    return text_output
                else:
                    logger.warning(f"Gemini 2.5 Flash failed ({resp.status})")
        except Exception as e:
            logger.warning(f"Gemini 2.5 Flash error: {e}")

    # === TIER 3: Claude Sonnet (Anthropic — strong reasoning) ===
    if ANTHROPIC_KEY:
        try:
            payload = {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 8192,
                "system": system_instruction[:12000],
                "messages": [{"role": "user", "content": reasoning_content[:60000]}],
                "temperature": 0.08,
            }
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json=payload, timeout=aiohttp.ClientTimeout(total=90)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content_blocks = data.get("content", [])
                    return "\n".join([b["text"] for b in content_blocks if b.get("type") == "text"])
        except Exception as e:
            logger.warning(f"Claude Sonnet fallback error: {e}")

    # === TIER 4: GPT-4o ===
    if OPENAI_KEY:
        try:
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": system_instruction[:12000]},
                    {"role": "user", "content": reasoning_content[:30000]}
                ],
                "temperature": 0.05,
                "max_tokens": 8192
            }
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
                json=payload, timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"GPT-4o fallback error: {e}")

    # === TIER 5: Groq LLaMA 70B (always available) ===
    if GROQ_KEY_LIVE:
        try:
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_instruction[:12000]},
                    {"role": "user", "content": reasoning_content[:25000]}
                ],
                "temperature": 0.05,
                "max_tokens": 8192
            }
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY_LIVE}", "Content-Type": "application/json"},
                json=payload, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Groq deep reasoning fallback failed: {e}")

    return ""


async def process_query_streamed(user_query: str, mode: str, matter_context: str, statute_context: str, firm_context: str):
    """Stream: auto-tool execution → fast baseline → deep analysis with citations."""
    system_instruction = ASSOCIATE_SYSTEM_PROMPT + TOOL_DESCRIPTIONS_FOR_PROMPT
    full_context = ""

    # === AGENT TOOL AUTO-EXECUTION (runs before AI call) ===
    auto_tool_calls = auto_detect_tools_needed(user_query)
    if auto_tool_calls:
        logger.info(f"War Room agent auto-detected {len(auto_tool_calls)} tool(s)")
        tool_tasks = [execute_agent_tool(c["tool"], c.get("args", {})) for c in auto_tool_calls]
        tool_results = await asyncio.gather(*tool_tasks, return_exceptions=True)
        successful = [r for r in tool_results if isinstance(r, dict) and r.get("success")]
        if successful:
            full_context += format_tool_results(successful) + "\n\n"

    if statute_context: full_context += f"=== DB STATUTES ===\n{statute_context}\n\n"
    if matter_context: full_context += f"=== MATTER ===\n{matter_context}\n\n"
    if firm_context: full_context += f"=== FIRM CONTEXT ===\n{firm_context}\n\n"

    user_content = f"QUERY: {user_query}\n\nCONTEXT:\n{full_context}"
    source_labels = extract_sections(statute_context) if statute_context else []
    if statute_context: source_labels.append("MongoDB Statute DB")

    async with aiohttp.ClientSession() as session:
        # Phase 1: Fast baseline (Groq — sub-2 second)
        yield json.dumps({"type": "war_room_status", "status": "Rapid analysis in progress..."})

        baseline_result = await call_groq_fast(session, system_instruction, user_content)
        if baseline_result:
            yield json.dumps({"type": "fast_chunk", "content": baseline_result})
            citations = await find_citation_links(baseline_result)
            yield json.dumps({"type": "fast_complete", "models_used": ["fast-engine"], "sections": source_labels, "citations": citations})
        else:
            yield json.dumps({"type": "fast_chunk", "content": "System Error: Fast inference failed."})

        # Phase 2: Deep reasoning (Gemini with web grounding → GPT-4o fallback → Groq fallback)
        yield json.dumps({"type": "war_room_status", "status": "Deploying deep reasoning engine with live legal research..."})

        deep_result = await call_deep_reasoning(session, system_instruction, user_content)

        if deep_result and len(deep_result) > 100:
            citations = await find_citation_links(deep_result)
            yield json.dumps({"type": "partner_payload", "content": deep_result, "citations": citations})

        yield json.dumps({"type": "war_room_status", "status": "Analysis complete."})
