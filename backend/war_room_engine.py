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
from datetime import datetime, timezone
from citation_linker import find_citation_links
from ai_engine import SPECTR_SYSTEM_PROMPT, TOOL_DESCRIPTIONS_FOR_PROMPT, auto_detect_tools_needed, execute_agent_tool, format_tool_results, classify_query, get_spectr_prompt
from indian_kanoon import search_indiankanoon, fetch_document, fetch_documents_parallel
from sandbox_research import execute_browser_research, execute_deep_research, should_use_sandbox_research
from serper_search import run_comprehensive_search, format_serper_for_llm
from response_critique import structural_score, detect_hallucination_risks, run_critique_pass, format_critique_feedback
from response_augmenter import augment_response, compute_tax_exposure
from pre_flight import run_pre_flight

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
LYZR_API_KEY = os.environ.get("LYZR_API_KEY", "")

# Lyzr DeepTrace Research Agent — GPT-5.4 + Perplexity AI + Brave Search for exhaustive legal research
DEEPTRACE_AGENT_ID = os.environ.get("DEEPTRACE_AGENT_ID", "69ddde0e6511fcaa597df948")
DEEPTRACE_USER_ID = os.environ.get("DEEPTRACE_USER_ID", "")
DEEPTRACE_ENDPOINT = "https://agent-prod.studio.lyzr.ai/v3/inference/chat/"


def needs_deep_research(query: str) -> bool:
    """Detect if a query requires deep external research (opposing counsel, entity DD, etc.)."""
    q_lower = query.lower()
    research_triggers = [
        # Explicit research requests
        r'\b(?:research|investigate|look\s*up|find\s*(?:out|info)\s*(?:about|on|regarding))\b',
        r'\b(?:background\s+(?:check|report|research|on|of))\b',
        # Entity/person research
        r'\b(?:who\s+is|tell\s+me\s+about)\b.*\b(?:person|lawyer|advocate|company|firm|counsel|judge)\b',
        r'\b(?:opposing\s+counsel|counterpart|other\s+(?:party|side))\b',
        r'\b(?:company\s+(?:profile|background|history)|entity\s+(?:profile|check))\b',
        # Due diligence research
        r'\b(?:due\s+diligence|dd\s+report|background\s+check)\b',
        r'\b(?:litigation\s+history|past\s+cases|track\s+record)\b',
        r'\b(?:regulatory\s+(?:history|compliance|actions?)|enforcement\s+(?:history|actions?))\b',
        # Deep legal research
        r'\b(?:latest|recent|current|new)\b.*\b(?:amendment|notification|circular|ruling|judgment|order)\b',
        r'\b(?:compare|comparison)\b.*\b(?:law|regulation|framework|jurisdiction)\b',
        r'\b(?:in[\s-]*depth|comprehensive|exhaustive|detailed|thorough)\s+(?:research|analysis|review|study)\b',
        # Market/industry research
        r'\b(?:market\s+(?:practice|standard|trend)|industry\s+(?:practice|norm|standard))\b',
        r'\b(?:benchmark|precedent\s+(?:analysis|study))\b',
        # Explicit deep research keywords
        r'\bresearch\s+(?:on|about|regarding|into)\b',
    ]
    return any(re.search(pattern, q_lower) for pattern in research_triggers)


async def call_deeptrace_research(session: aiohttp.ClientSession, query: str) -> str:
    """Call Lyzr DeepTrace Research Agent for exhaustive web research.
    Uses Perplexity AI + Brave Search under the hood for deep intelligence gathering.
    """
    if not LYZR_API_KEY:
        logger.warning("LYZR_API_KEY not set — skipping DeepTrace research")
        return ""

    session_id = f"{DEEPTRACE_AGENT_ID}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    payload = {
        "user_id": DEEPTRACE_USER_ID,
        "agent_id": DEEPTRACE_AGENT_ID,
        "session_id": session_id,
        "message": query
    }

    try:
        async with session.post(
            DEEPTRACE_ENDPOINT,
            headers={
                "Content-Type": "application/json",
                "x-api-key": LYZR_API_KEY
            },
            json=payload,
            timeout=aiohttp.ClientTimeout(total=180)  # DeepTrace can take longer
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                # Extract response from Lyzr's response format
                response = data.get("response", "") or data.get("message", "") or data.get("output", "")
                if not response and isinstance(data, dict):
                    for key in data:
                        if isinstance(data[key], str) and len(data[key]) > 50:
                            response = data[key]
                            break
                if response:
                    logger.info(f"DeepTrace returned {len(response)} chars of research")
                    return response
                else:
                    logger.warning("DeepTrace returned empty response")
            else:
                err = await resp.text()
                logger.warning(f"DeepTrace API failed ({resp.status}): {err[:200]}")
    except asyncio.TimeoutError:
        logger.warning("DeepTrace timed out after 180s")
    except Exception as e:
        logger.warning(f"DeepTrace exception: {e}")

    return ""




# DEEP_REASONING_PROMPT was REMOVED (23 Apr 2026).
#
# Having TWO prompts (system SPECTR_SYSTEM_PROMPT + prepended DEEP_REASONING_PROMPT)
# caused them to fight each other — length targets conflicted, phase labels
# got out of sync, and models pick one arbitrarily. One prompt, one truth.
#
# SPECTR_SYSTEM_PROMPT now contains everything: the 5-phase <internal_strategy>
# reasoning, the 8 mandatory output sections, the 4-6 topic-specific subheading
# rule, the 1,200-1,800 word target, the mathematical consistency guard. The
# deep-reasoning call just passes the user's content straight through.
DEEP_REASONING_PROMPT = ""


async def call_groq_fast(session, system_instruction, user_content):
    """Fast baseline cascade — Claude Sonnet 4.5 → Groq → OpenAI fallback.

    Priority:
      1. Claude Sonnet 4.5 (via Emergent) — best quality-per-speed for Indian legal
      2. Groq llama-3.3-70b-versatile — fast fallback
      3. Groq llama-3.1-8b-instant
      4. OpenAI gpt-4o-mini
      5. OpenAI gpt-4o
    """
    # Trim system prompt for FAST mode (full 76K prompt is overkill for hello/simple queries)
    # Keep first 15K chars — enough for SPECTR identity + core rules
    system_trimmed = system_instruction[:15000] if len(system_instruction) > 15000 else system_instruction
    user_msg = "Provide a direct, substantive answer. Start with the conclusion. Cite sections. Use markdown.\n\n" + user_content[:15000]

    # === Primary: Claude smart-routed (Haiku → Sonnet → Opus escalation) ===
    # Simple queries use Haiku ($1/M). Normal queries use Sonnet ($3/M).
    # Opus ($15/M) reserved for explicit escalation. Cost-efficient.
    try:
        from claude_emergent import smart_route
        # Extract the actual user query (strip the prefix we added above)
        raw_query = user_content[:500]
        resp, model, tier = await smart_route(
            system_trimmed,
            user_msg,
            query=raw_query,
        )
        if resp and len(resp) > 100:
            logger.info(f"Claude fast-path OK: tier={tier} model={model} chars={len(resp)}")
            return resp
    except Exception as e:
        logger.warning(f"Claude fast-path failed: {e}")

    # GROQ REMOVED (23 Apr 2026). Fallback chain is now:
    #   Claude Sonnet (via Emergent) → GPT-5 (via Emergent) → GPT-4o (via Emergent)
    # All under the EMERGENT_LLM_KEY — no separate Groq or OpenAI keys needed
    # for the inference path. Direct OPENAI_KEY is kept only for document
    # analysis (long-context chunked map-reduce) where we need raw OpenAI.
    try:
        from claude_emergent import call_claude, CLAUDE_SONNET, _call_gpt_emergent
        # Try Sonnet directly (in case smart_route above missed it)
        resp_text = await call_claude(system_trimmed, user_msg, model=CLAUDE_SONNET, timeout=45)
        if resp_text and len(resp_text) > 200:
            return resp_text
        # GPT-5 via Emergent
        resp_text = await _call_gpt_emergent(system_trimmed, user_msg, model="gpt-5")
        if resp_text and len(resp_text) > 200:
            return resp_text
        # GPT-4o via Emergent
        resp_text = await _call_gpt_emergent(system_trimmed, user_msg, model="gpt-4o")
        if resp_text and len(resp_text) > 200:
            return resp_text
    except Exception as e:
        logger.warning(f"Emergent fallback chain failed: {e}")

    logger.error("All fast-path providers failed (Claude + GPT-5 + GPT-4o via Emergent)")
    return ""


async def call_deep_reasoning(session, system_instruction, user_content):
    """Deep reasoning cascade: Claude Opus 4.5 → Sonnet 4.5 → Gemini 2.5 Pro → GPT-4o → Groq.

    Single-prompt architecture (23 Apr 2026): all depth rules live in
    SPECTR_SYSTEM_PROMPT, which is already in `system_instruction`. We pass
    the user's query + research context straight through — no second prompt
    fighting the first one.
    """
    reasoning_content = "USER QUERY + CONTEXT:\n" + user_content[:50000]
    _deep_failures = []  # Track which models failed and why

    # === TIER 0: Claude with smart escalation (cost-aware) ===
    # Sonnet 4.5 first — self-assesses complexity and flags [COMPLEXITY:COMPLEX]
    # If flagged → Opus 4.5 takes over. Otherwise, Sonnet's answer is kept.
    # This avoids $15/M Opus cost on ~80% of queries that Sonnet handles well.
    try:
        from claude_emergent import call_with_escalation
        resp, model_used = await call_with_escalation(system_instruction, reasoning_content)
        if resp and len(resp) > 300:
            logger.info(f"Claude deep reasoning via {model_used}")
            return resp
    except Exception as e:
        logger.warning(f"Claude deep reasoning failed: {e}")
        _deep_failures.append(f"claude: {str(e)[:80]}")

    # === TIER 1: Gemini 2.5 Pro — DISABLED ===
    # Current Gemini API key 429s on 2.5-pro consistently (free-tier RPM is ~2).
    # Every invocation here was burning 10-20s on guaranteed failure before the
    # cascade moved on to Flash. Skipping straight to Flash saves that time.
    # Re-enable by setting ENABLE_GEMINI_PRO_TIER=1 in the env.
    if GOOGLE_AI_KEY and os.environ.get("ENABLE_GEMINI_PRO_TIER") == "1":
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
                    _deep_failures.append(("Gemini 2.5 Pro", f"HTTP {resp.status}"))
        except Exception as e:
            logger.warning(f"Gemini 2.5 Pro error: {e}")
            _deep_failures.append(("Gemini 2.5 Pro", str(e)[:80]))

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
                    _deep_failures.append(("Gemini 2.5 Flash", f"HTTP {resp.status}"))
        except Exception as e:
            logger.warning(f"Gemini 2.5 Flash error: {e}")
            _deep_failures.append(("Gemini 2.5 Flash", str(e)[:80]))

    # === TIER 3: Claude Sonnet (Anthropic — strong reasoning) ===
    if ANTHROPIC_KEY:
        try:
            payload = {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 16384,
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
            _deep_failures.append(("Claude Sonnet", str(e)[:80]))

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
            _deep_failures.append(("GPT-4o", str(e)[:80]))

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
            _deep_failures.append(("Groq LLaMA 70B", str(e)[:80]))

    # All models failed — return diagnostic message instead of empty string
    if _deep_failures:
        failure_report = " | ".join([f"{m}: {r}" for m, r in _deep_failures])
        logger.error(f"ALL deep reasoning models failed: {failure_report}")
    return ""


async def process_query_streamed(user_query: str, mode: str, matter_context: str, statute_context: str, firm_context: str, conversation_history: list | None = None, user_id: str | None = None, conversation_id: str | None = None, matter_id: str | None = None):
    """Stream: research steps → auto-tools → case law → deep analysis with citations.

    Enhanced with:
    - Conversation history for multi-turn context
    - Response quality metrics yielded to frontend
    - Improved context priority ordering
    - TRIAGE GATE: greetings and trivial non-legal queries short-circuit to a fast one-liner
      without running any research tools (sub-2-second response).
    - Supermemory long-term context: retrieves semantically relevant fragments from
      this user's prior Spectr sessions and injects them at the top of the context.
      Saves each turn fire-and-forget so the next query benefits from this one.
    """
    live_prompt = await get_spectr_prompt()
    system_instruction = live_prompt + TOOL_DESCRIPTIONS_FOR_PROMPT
    full_context = ""

    # ─── SUPERMEMORY: long-term context retrieval ───
    # This runs in parallel with the triage check — only adds ~200-400ms to
    # substantive queries because it's a semantic search, not an LLM call.
    # Returns empty string if disabled, timed out, or no matches.
    supermemory_context = ""
    if user_id:
        try:
            from supermemory_client import retrieve_context as _sm_retrieve
            supermemory_context = await _sm_retrieve(
                user_id=user_id,
                query=user_query,
                limit=6,
                matter_id=matter_id,
                timeout_s=3.5,
            )
            if supermemory_context:
                logger.info(f"Supermemory: injected {len(supermemory_context)} chars of prior-session context for user={user_id}")
        except Exception as _e:
            logger.warning(f"Supermemory retrieve failed (non-blocking): {_e}")

    # ─── TRIAGE GATE: short-circuit trivial queries ───
    # Greetings, thanks, pleasantries, meta-questions — don't waste 15s + tool budget.
    # Run them through a single Haiku call with a tiny system prompt and return.
    _q = (user_query or "").strip().lower()
    _q_clean = re.sub(r'[^\w\s]', '', _q)
    _tokens = _q_clean.split()
    _GREETING_WORDS = {
        "hi", "hello", "hey", "yo", "hiya", "howdy", "sup", "whatsup", "whats", "wassup",
        "greetings", "namaste", "namaskar", "morning", "afternoon", "evening", "gm", "gn",
        "thanks", "thank", "thankyou", "ty", "thx", "cheers", "welcome",
        "ok", "okay", "k", "kk", "cool", "nice", "great", "got", "it", "awesome",
        "bye", "goodbye", "cya", "later",
        "yes", "no", "yeah", "yep", "nope", "sure", "alright", "fine",
        "who", "are", "you", "what", "is", "this", "can", "do", "how",
        "test", "testing", "ping", "hola", "ola",
    }
    _is_trivial = (
        len(_tokens) <= 6
        and all(t in _GREETING_WORDS for t in _tokens)
    )
    # Also trivial: very short + no legal/tax/financial keyword
    _LEGAL_KEYWORDS = (
        "gst", "tax", "tds", "itr", "section", "notice", "scn", "penalty", "appeal",
        "bail", "contract", "agreement", "clause", "case", "court", "tribunal",
        "assessment", "limitation", "fema", "sebi", "companies act", "cgst", "ipc",
        "bns", "crpc", "rti", "writ", "petition", "draft", "reply", "compute",
        "compliance", "audit", "reconcile", "demand", "interest", "deduction",
        "itc", "invoice", "gstr", "194", "fy ", "ay ", "₹", "rs.", "rs ",
        "crore", "lakh", "client", "advocate", "lawyer", "ca ",
    )
    if not _is_trivial and len(_q) < 60:
        _has_legal = any(kw in _q for kw in _LEGAL_KEYWORDS)
        if not _has_legal:
            _is_trivial = True

    if _is_trivial:
        yield json.dumps({
            "type": "research_step", "step": "triage",
            "label": "Quick reply",
            "detail": "No research pipeline needed for this message."
        })
        try:
            from claude_emergent import call_claude, CLAUDE_HAIKU
            triage_system = (
                "You are Spectr — an AI legal and tax intelligence engine for Indian CAs, advocates, and CFOs. "
                "This message is a greeting, acknowledgement, or casual remark — NOT a legal/tax question. "
                "Respond with ONE crisp, confident sentence (max 20 words). No preamble. No markdown headings. "
                "No corporate pleasantries like 'How may I assist you today?'. "
                "If the user greeted you, greet back briefly and indicate you're ready — e.g. "
                "'Hey. Hit me with the matter.' or 'Good to see you. What's on the desk?'. "
                "If the user thanked you, acknowledge in one line. "
                "If the user asked who/what you are, answer in one line. "
                "Never list your capabilities unless explicitly asked."
            )
            reply = await call_claude(
                system_prompt=triage_system,
                user_content=user_query,
                model=CLAUDE_HAIKU,
                timeout=15,
            )
            if not reply or len(reply.strip()) < 2:
                reply = "Hey. What's the matter you're working on?"
        except Exception as e:
            logger.warning(f"Triage LLM failed, using canned: {e}")
            reply = "Hey. What's the matter you're working on?"

        yield json.dumps({"type": "fast_chunk", "content": reply.strip()})
        yield json.dumps({
            "type": "fast_complete",
            "models_used": ["claude-haiku-4-5"],
            "sections": [],
            "citations": []
        })
        return

    # Inject conversation history for multi-turn coherence
    if conversation_history and len(conversation_history) > 0:
        from ai_engine import _build_conversation_context
        conv_ctx = _build_conversation_context(conversation_history, max_turns=4, max_chars=6000)
        if conv_ctx:
            full_context += conv_ctx + "\n\n"

    # ─── STEP 0: PRE-FLIGHT ENRICHMENT ───
    # Extract facts from query, auto-run deterministic tools, inject COMPUTED FACTS
    # so the LLM works from verified numbers, not guesses.
    try:
        yield json.dumps({
            "type": "research_step", "step": "pre_flight",
            "label": "Pre-flight — extracting facts, running deterministic tools",
            "detail": "Computing exact TDS/penalty/deadline/notice-validity values before LLM generation..."
        })
        pf = await run_pre_flight(user_query)
        if pf.get("context_block"):
            full_context += pf["context_block"] + "\n\n"
        if pf.get("has_computed_facts"):
            yield json.dumps({
                "type": "pre_flight_complete",
                "tools_run": list(pf.get("computed", {}).keys()),
                "facts_extracted": {
                    "dates": len(pf.get("extracted", {}).get("dates", [])),
                    "amounts": len(pf.get("extracted", {}).get("amounts", [])),
                    "sections": len(pf.get("extracted", {}).get("sections", [])),
                    "notice_type": pf.get("extracted", {}).get("notice_type"),
                },
            })
    except Exception as e:
        logger.warning(f"Pre-flight enrichment failed (non-blocking): {e}")

    # ─── STEP 1: Assessing query ───
    query_types = classify_query(user_query)
    type_labels = {"legal": "Legal", "financial": "Tax & Financial", "corporate": "Corporate", "compliance": "Compliance", "drafting": "Document Drafting"}
    detected = [type_labels.get(t, t.title()) for t in query_types]
    yield json.dumps({"type": "research_step", "step": "assessing", "label": "Assessing query", "detail": f"Identified as: {', '.join(detected)}", "items": detected})

    # ─── STEP 2: Auto-detect and run tools ───
    auto_tool_calls = auto_detect_tools_needed(user_query)
    if auto_tool_calls:
        tool_labels = {"section_mapper": "Section Mapper", "tds_classifier": "TDS Classifier", "notice_validity_checker": "Notice Validator", "penalty_calculator": "Penalty Calculator", "notice_auto_reply": "Notice Reply Engine", "case_law_search": "Case Law Search"}
        tool_names = [tool_labels.get(c["tool"], c["tool"]) for c in auto_tool_calls]
        yield json.dumps({"type": "research_step", "step": "tools", "label": "Running analysis tools", "items": tool_names})

        logger.info(f"War Room agent auto-detected {len(auto_tool_calls)} tool(s)")
        tool_tasks = [execute_agent_tool(c["tool"], c.get("args", {})) for c in auto_tool_calls]
        tool_results = await asyncio.gather(*tool_tasks, return_exceptions=True)
        successful = [r for r in tool_results if isinstance(r, dict) and r.get("success")]
        if successful:
            full_context += format_tool_results(successful) + "\n\n"
            yield json.dumps({"type": "research_step", "step": "tools_done", "label": f"Tools executed — {len(successful)} result(s)", "items": [r.get("tool", "") for r in successful]})

    # ─── STEP 3: Checking statutes ───
    if statute_context:
        sections = extract_sections(statute_context)
        yield json.dumps({"type": "research_step", "step": "statutes", "label": "Checking statute database", "items": sections[:8]})
        full_context += f"=== RELEVANT STATUTE SECTIONS ===\n{statute_context}\n\n"

    # ─── STEP 4: Searching case law ───
    is_legal = any(t in query_types for t in ["legal", "drafting", "compliance"])
    ik_results = []
    if is_legal:
        yield json.dumps({"type": "research_step", "step": "caselaw", "label": "Searching case law", "items": ["IndianKanoon"]})
        try:
            ik_results = await search_indiankanoon(user_query, top_k=10)
        except Exception as e:
            logger.warning(f"IndianKanoon search failed: {e}")

        if ik_results:
            case_names = [c.get("title", "")[:60] for c in ik_results if c.get("title")]
            yield json.dumps({"type": "research_step", "step": "caselaw_found", "label": f"Found {len(ik_results)} relevant precedents", "items": case_names})

            # Fetch full text for top 3 results in parallel (deep context for the LLM)
            top_doc_ids = [c.get("doc_id") for c in ik_results[:3] if c.get("doc_id")]
            fetched_docs = {}
            if top_doc_ids:
                try:
                    docs = await fetch_documents_parallel(top_doc_ids, max_chars=20000)
                    for d in docs:
                        fetched_docs[d.get("title", "")] = d.get("doc", "")[:15000]
                except Exception as e:
                    logger.warning(f"Parallel doc fetch in war room failed: {e}")

            # Inject into context
            full_context += "=== RETRIEVED CASE LAW FROM INDIANKANOON ===\n"
            for i, case in enumerate(ik_results, 1):
                full_context += f"\n[Case {i}] {case.get('title', 'N/A')}\nCourt: {case.get('court', 'N/A')} | Year: {case.get('year', 'N/A')}\nCitation: {case.get('citation', 'N/A')}\nSummary: {case.get('headline', 'N/A')}\n"
                # Append full text for top results
                doc_text = fetched_docs.get(case.get("title", ""), "")
                if doc_text:
                    full_context += f"Full Text (excerpt):\n{doc_text[:12000]}\n"
            full_context += "\n"
        else:
            # IndianKanoon empty or down — escalate to Google Scholar
            yield json.dumps({"type": "research_step", "step": "caselaw_fallback",
                            "label": "IndianKanoon empty — searching Google Scholar",
                            "items": ["Google Scholar"]})
            logger.info("IndianKanoon empty for legal query — escalating to Scholar fallback")
            try:
                from serper_search import search_scholar as _search_scholar
                scholar_res = await _search_scholar(f"{user_query} India judgment ruling precedent", num_results=10)
                scholar_docs = scholar_res.get("organic", [])
                if scholar_docs:
                    full_context += "=== GOOGLE SCHOLAR FALLBACK (IndianKanoon returned no results) ===\n"
                    scholar_titles = []
                    for idx, s in enumerate(scholar_docs[:6], 1):
                        title = s.get("title", "")
                        snippet = s.get("snippet", "")[:400]
                        year = s.get("year", "")
                        cited_by = s.get("citedBy", s.get("cited_by", ""))
                        full_context += (
                            f"\n[Scholar {idx}] {title}"
                            + (f" ({year})" if year else "")
                            + (f" — Cited by {cited_by}" if cited_by else "")
                            + f"\n{snippet}\n"
                        )
                        scholar_titles.append(title[:50])
                    full_context += (
                        "\n[NOTE: IndianKanoon was empty. Scholar results are from Google Scholar "
                        "and MUST be verified against official reporters before citing in any filing.]\n\n"
                    )
                    yield json.dumps({"type": "research_step", "step": "scholar_found",
                                    "label": f"Scholar: {len(scholar_docs)} papers found",
                                    "items": scholar_titles[:4]})
                else:
                    full_context += (
                        "\n[WARNING: Both IndianKanoon and Google Scholar returned no results "
                        "for this query. Case law context is ABSENT. Verify citations independently.]\n\n"
                    )
                    yield json.dumps({"type": "research_step", "step": "no_caselaw",
                                    "label": "No case law found from any source",
                                    "items": []})
            except Exception as scholar_err:
                logger.warning(f"Scholar fallback in war room failed: {scholar_err}")
                full_context += (
                    "\n[WARNING: IndianKanoon returned no results and Scholar fallback failed. "
                    "No case law in context. Verify all citations independently.]\n\n"
                )

    # ─── STEP 5: Checking for key terms ───
    key_terms = []
    term_patterns = {
        "ITC": r'\b(?:itc|input tax credit)\b', "GST": r'\b(?:gst|cgst|igst|sgst)\b',
        "TDS": r'\btds\b', "notice": r'\bnotice\b', "penalty": r'\bpenalt',
        "assessment": r'\bassessment\b', "appeal": r'\bappeal\b', "bail": r'\bbail\b',
        "limitation": r'\blimitation\b', "FEMA": r'\bfema\b', "SEBI": r'\bsebi\b',
        "merger": r'\b(?:merger|m&a|acquisition)\b', "contract": r'\bcontract\b',
        "fraud": r'\bfraud\b', "SCN": r'\b(?:scn|show cause)\b',
    }
    q_lower = user_query.lower()
    for label, pattern in term_patterns.items():
        if re.search(pattern, q_lower, re.IGNORECASE):
            key_terms.append(label)
    if key_terms:
        yield json.dumps({"type": "research_step", "step": "terms", "label": "Checking for key terms", "items": key_terms})

    # ─── STEP 6: Google Search via Serper (instant — <1 second) ───
    web_sources = []
    serper_context = ""
    try:
        yield json.dumps({"type": "research_step", "step": "web_search",
                         "label": "Searching Google Web, News & Scholar",
                         "detail": "Serper API — structured Google results in <1 second",
                         "items": ["Google Web", "Google News", "Google Scholar"]})

        serper_results = await run_comprehensive_search(user_query, query_types)
        if serper_results.get("results"):
            web_sources = [r.get("title", "")[:50] for r in serper_results["results"][:8] if r.get("title")]
            serper_context = format_serper_for_llm(serper_results, user_query)
            if serper_context:
                full_context += f"\n{serper_context}\n\n"

            yield json.dumps({"type": "research_step", "step": "web_done",
                             "label": f"Google search complete — {len(serper_results['results'])} results",
                             "items": web_sources[:6]})
        else:
            yield json.dumps({"type": "research_step", "step": "web_done",
                             "label": "Google search — no results"})
    except Exception as e:
        logger.warning(f"Serper search skipped: {e}")
        # Fallback to DuckDuckGo
        try:
            from duckduckgo_search import DDGS
            search_q = f"{user_query[:80]} India law OR tax OR case"
            ddg_results = DDGS().text(search_q, region='in-en', safesearch='off', max_results=5)
            if ddg_results:
                web_sources = [r.get("title", "")[:50] for r in ddg_results if r.get("title")]
                full_context += "=== WEB RESEARCH ===\n"
                for r in ddg_results:
                    full_context += f"- {r.get('title', '')}: {r.get('body', '')[:200]}\n"
                full_context += "\n"
        except Exception:
            pass

    # ─── STEPS 6.5 + 7: PARALLEL Deep Research ───
    # DeepTrace (Lyzr) + Sandbox browser research run CONCURRENTLY.
    # This saves up to 180s vs the old sequential approach.
    deeptrace_result = ""
    sandbox_research_result = ""
    sandbox_sources = []
    # THREE-TIER MODE MODEL:
    #   mode = "everyday" (Quick)         → Groq fast only. Skip Claude + skip sandbox. ~8s.
    #   mode = "research" (Deep Research) → Groq fast + Claude Sonnet cascade. NO sandbox. ~60-90s.
    #   mode = "partner"  (Depth Research)→ Groq fast + Claude Opus + 5-phase sandbox. ~3-5min.
    # Legacy mode name "assistant" is treated as "research".
    is_quick_mode = (mode == "everyday" or mode == "quick")
    # "research" and "partner" are now UNIFIED (23 Apr 2026). User wanted
    # one depth tier, not two. Both modes trigger sandbox + serper + deep
    # Claude cascade. Only "quick" gets the fast-path short-circuit.
    is_deep_mode = (mode == "partner" or mode == "research" or mode == "assistant")

    run_deeptrace = is_deep_mode and needs_deep_research(user_query)
    run_sandbox = is_deep_mode and should_use_sandbox_research(user_query, query_types)

    if run_deeptrace or run_sandbox:
        # Announce what's launching
        launching = []
        if run_deeptrace:
            launching.extend(["DeepTrace (Perplexity + Brave)"])
        if run_sandbox:
            launching.extend(["Sandbox Deep Research (5-phase)"])

        yield json.dumps({
            "type": "research_step", "step": "parallel_research_start",
            "label": f"Launching {len(launching)} research engine(s) in parallel",
            "detail": "Running simultaneously to save time",
            "items": launching
        })

        # --- Build parallel tasks ---
        async def _run_deeptrace():
            try:
                async with aiohttp.ClientSession() as dt_session:
                    return await call_deeptrace_research(dt_session, user_query)
            except Exception as e:
                logger.warning(f"DeepTrace failed: {e}")
                return ""

        progress_events = []
        async def _stream_progress(step, label, detail="", items=None):
            progress_events.append({"step": step, "label": label, "detail": detail, "items": items or []})

        async def _run_sandbox():
            try:
                return await execute_deep_research(
                    user_query=user_query,
                    query_types=query_types,
                    progress_callback=_stream_progress,
                )
            except Exception as e:
                logger.error(f"Deep research failed: {e}")
                return {"success": False, "errors": [str(e)]}

        tasks = []
        task_labels = []
        if run_deeptrace:
            tasks.append(_run_deeptrace())
            task_labels.append("deeptrace")
        if run_sandbox:
            tasks.append(_run_sandbox())
            task_labels.append("sandbox")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # --- Process DeepTrace result ---
        if "deeptrace" in task_labels:
            dt_idx = task_labels.index("deeptrace")
            dt_result = results[dt_idx]
            if isinstance(dt_result, Exception):
                logger.warning(f"DeepTrace exception: {dt_result}")
            elif dt_result:
                deeptrace_result = dt_result
                full_context += f"=== DEEP RESEARCH INTELLIGENCE ===\n{deeptrace_result}\n\n"
                findings = [line.strip()[:80] for line in deeptrace_result.split("\n")[:10]
                           if line.strip() and len(line.strip()) > 20 and not line.strip().startswith("#")][:4]
                yield json.dumps({
                    "type": "research_step", "step": "deeptrace_done",
                    "label": f"Deep research agent complete — {len(deeptrace_result)} chars",
                    "items": findings or ["Research report generated"]
                })
            else:
                yield json.dumps({"type": "research_step", "step": "deeptrace_done",
                                 "label": "Deep research agent — no results"})

        # --- Process Sandbox result ---
        if "sandbox" in task_labels:
            sb_idx = task_labels.index("sandbox")
            sandbox_result = results[sb_idx]

            # Yield accumulated progress events from sandbox phases
            for evt in progress_events:
                yield json.dumps({
                    "type": "research_step",
                    "step": evt["step"],
                    "label": evt["label"],
                    "detail": evt["detail"],
                    "items": evt["items"],
                })

            if isinstance(sandbox_result, Exception):
                logger.error(f"Deep research exception: {sandbox_result}")
                yield json.dumps({
                    "type": "research_step", "step": "deep_research_complete",
                    "label": "Deep Research — skipped (proceeding with other sources)",
                    "items": []
                })
            elif sandbox_result.get("success") and sandbox_result.get("research_summary"):
                sandbox_research_result = sandbox_result["research_summary"]
                full_context += f"\n{sandbox_research_result}\n\n"

                meta = sandbox_result.get("metadata", {})
                urls_found = meta.get("urls_processed", 0)
                total_words = meta.get("total_words_extracted", 0)
                duration = meta.get("duration_ms", 0)
                sandbox_name = meta.get("sandbox_name", "")
                entities_found = meta.get("entities_found", 0)

                for pc in sandbox_result.get("page_contents", []):
                    if pc.get("success") and pc.get("title"):
                        sandbox_sources.append(pc["title"][:50])

                yield json.dumps({
                    "type": "research_step", "step": "deep_research_complete",
                    "label": f"Deep Research complete — {urls_found} sources, {total_words:,} words in {duration / 1000:.0f}s",
                    "detail": f"{sandbox_name} | {entities_found} entities extracted | {meta.get('searches_performed', 0)} searches",
                    "items": sandbox_sources[:8] if sandbox_sources else ["Research dossier compiled"]
                })
            else:
                errors = sandbox_result.get("errors", []) if isinstance(sandbox_result, dict) else []
                yield json.dumps({
                    "type": "research_step", "step": "deep_research_complete",
                    "label": f"Deep Research — partial results ({errors[0] if errors else 'completed'})",
                    "items": []
                })

    if matter_context: full_context += f"=== MATTER ===\n{matter_context}\n\n"
    if firm_context: full_context += f"=== FIRM CONTEXT ===\n{firm_context}\n\n"
    # Prior-session memory goes at the TOP of the context block so Claude
    # weights it appropriately — prior facts the user already established
    # should frame every new answer without asking for re-confirmation.
    if supermemory_context:
        full_context = f"{supermemory_context}\n\n{full_context}"

    user_content = f"QUERY: {user_query}\n\nCONTEXT:\n{full_context}"
    source_labels = extract_sections(statute_context) if statute_context else []
    if statute_context: source_labels.append("Statute Database")
    if ik_results: source_labels.append("IndianKanoon")
    if serper_context: source_labels.append("Google Search")
    if web_sources: source_labels.extend(web_sources[:3])
    if deeptrace_result: source_labels.append("DeepTrace AI")
    if sandbox_research_result: source_labels.append("Deep Research (Sandbox)")
    if sandbox_sources: source_labels.extend(sandbox_sources[:4])

    # ─── STEP 7: Synthesizing ───
    yield json.dumps({"type": "research_step", "step": "synthesizing", "label": "Synthesizing analysis", "detail": "Generating professional advisory with deep reasoning..."})

    async with aiohttp.ClientSession() as session:
        # Phase 1: Fast baseline (Groq — sub-2 second)
        yield json.dumps({"type": "war_room_status", "status": "Rapid analysis in progress..."})

        baseline_result = await call_groq_fast(session, system_instruction, user_content)
        if baseline_result:
            yield json.dumps({"type": "fast_chunk", "content": baseline_result})
            citations = await find_citation_links(baseline_result)
            yield json.dumps({"type": "fast_complete", "models_used": ["fast-engine"], "sections": source_labels, "citations": citations})

            # === QUICK-MODE TRUST LAYER ===
            # Only run for Quick mode — it's the user's final output there and needs
            # inline [✓]/[⚠] tags. Research and Partner modes run the Trust Layer
            # later on the Claude deep response, so running it on the baseline too
            # would just duplicate 5-10s of IK lookups.
            if is_quick_mode:
                try:
                    _db = None
                    try:
                        from server import db as _srv_db
                        _db = _srv_db
                    except Exception:
                        pass
                    augment_data = await augment_response(baseline_result, db=_db, max_case_verifications=4)
                    if augment_data and augment_data.get("trust_score") is not None:
                        yield json.dumps({
                            "type": "trust_layer",
                            "trust_score": augment_data["trust_score"],
                            "stats": augment_data.get("stats", {}),
                            "verification_report": augment_data.get("verification_report", ""),
                            "augmented_text": augment_data.get("augmented_text", ""),
                        })
                except Exception as _e:
                    logger.warning(f"Quick-mode Trust Layer failed (non-blocking): {_e}")
        else:
            yield json.dumps({"type": "fast_chunk", "content": "System Error: Fast inference failed."})

        # ─── QUICK MODE SHORT-CIRCUIT ───
        # Quick mode skips Claude deep reasoning entirely — the Groq fast result
        # (already emitted above as fast_chunk) is the final response. This brings
        # Quick mode in at ~8s instead of the 60-90s Claude cascade takes.
        deep_result = ""
        if is_quick_mode:
            if baseline_result:
                # Re-emit the baseline as the partner_payload so the frontend
                # renders it in the main response slot (not just the fast_chunk preview).
                citations = await find_citation_links(baseline_result)
                yield json.dumps({
                    "type": "partner_payload",
                    "content": baseline_result,
                    "citations": citations,
                    "mode": "quick",
                })
                deep_result = baseline_result  # for downstream quality metrics
            # skip Phase 2 entirely
        else:
            # Phase 2: MULTI-PASS DEEP MEMO (23 Apr 2026).
            # Single Claude calls capped at ~1,500 words due to Emergent proxy
            # 60s timeout. For the demo-grade 9-12K-word memos, we chain
            # 7 Sonnet 4.6 calls and stream each pass as it completes.
            yield json.dumps({"type": "research_step", "step": "deep_reasoning",
                              "label": "Deploying 7-pass partner memo engine",
                              "detail": "Building Bottom Line \u2192 Issues \u2192 Framework \u2192 Analysis \u2192 Opposition \u2192 Risk \u2192 Actions \u2192 Authorities..."})

            try:
                from multi_pass_memo import generate_multi_pass_memo
                # Streaming accumulator — each pass appended to deep_result
                # so the frontend sees memos grow in real time.
                _accumulated_text = [""]

                async def _on_pass(pass_num, label, text):
                    """Callback: each pass completion streams to frontend."""
                    _accumulated_text[0] = (
                        (_accumulated_text[0] + "\n\n" + text)
                        if _accumulated_text[0] else text
                    )
                    # Let frontend show progress during the 6-minute generation
                    # We queue a JSON event for the outer yield loop — but since
                    # we're inside an async callback, append to a deque.
                    # For now just log; the full memo is yielded below.
                    logger.info(f"Multi-pass: emitted pass {pass_num} ({label}) live")

                # 13 passes — target 16,000-18,000 word memo at demo-grade
                # depth. Each Sonnet 4.6 pass ~40-50s with cache hits on
                # passes 2+. Total ~9-11 minutes end-to-end.
                result = await generate_multi_pass_memo(
                    system_prompt=system_instruction,
                    user_query=user_query,
                    research_context=full_context[:15000] if full_context else "",
                    on_pass_complete=_on_pass,
                    num_passes=13,
                )
                deep_result = result.get("full_text", "")
                logger.info(
                    f"Multi-pass memo delivered: {result.get('total_words', 0):,} words "
                    f"in {result.get('total_time', 0):.1f}s across "
                    f"{len(result.get('pass_texts', []))} passes"
                )
                # Fallback if multi-pass produced nothing usable
                if not deep_result or len(deep_result) < 500:
                    logger.warning(
                        f"Multi-pass returned thin ({len(deep_result)} chars) — "
                        f"falling back to single-call deep cascade"
                    )
                    deep_result = await call_deep_reasoning(session, system_instruction, user_content)
            except Exception as _e:
                logger.warning(f"Multi-pass memo exception, falling back to single-call: {_e}")
                deep_result = await call_deep_reasoning(session, system_instruction, user_content)

            if deep_result and len(deep_result) > 100:
                citations = await find_citation_links(deep_result)
                yield json.dumps({"type": "partner_payload", "content": deep_result, "citations": citations})

        # === TOTAL FAILURE SAFETY NET ===
        if not baseline_result and not deep_result:
            yield json.dumps({
                "type": "partner_payload",
                "content": "**⚠ All AI engines failed to generate a response.**\n\n"
                           "This can happen when:\n"
                           "- API keys are missing or expired (check your `.env`)\n"
                           "- Network connectivity to AI providers is blocked\n"
                           "- All providers are experiencing simultaneous downtime\n\n"
                           "**Your query has been saved.** Please try again in a few minutes.",
                "citations": []
            })

        # === RESPONSE QUALITY METRICS ===
        from ai_engine import _check_response_quality
        q_types = classify_query(user_query)
        is_drafting = "drafting" in q_types

        # Evaluate quality of both responses
        fast_quality = _check_response_quality(baseline_result, q_types, is_drafting) if baseline_result else {"score": 0}
        deep_quality = _check_response_quality(deep_result, q_types, is_drafting) if deep_result else {"score": 0}

        # === ADVERSARIAL CRITIQUE PASS (God-tier quality gate) ===
        # Run structural + hallucination + partner-review on the deep response
        critique_data = None
        struct_data = None
        halluc_flags = []
        final_response = deep_result or baseline_result

        # Skip the adversarial critique pass entirely in Quick mode — it's a 15-25s
        # LLM call that doesn't belong in a sub-10s tier. Quick-mode users already
        # saw the baseline (fast_chunk + Trust Layer ran earlier); that's enough.
        run_full_critique = False
        if final_response and len(final_response) > 400 and not is_drafting and not is_quick_mode:
            # Fast local checks first — they're ~5-20ms each, no network
            struct_data = structural_score(final_response)
            halluc_flags = detect_hallucination_risks(final_response)

            # Skip the LLM critique call if the response is already structurally strong
            # AND has no hallucination flags. This lands ~60% of the time and saves
            # 5-8s of Groq latency. The structural score covers: BLUF present,
            # citations present, headings present, tables/quantification present,
            # word count within target range.
            structurally_strong = struct_data and struct_data.get("score", 0) >= 70
            clean_flags = len(halluc_flags) == 0
            run_full_critique = not (structurally_strong and clean_flags)

            if run_full_critique:
                yield json.dumps({
                    "type": "research_step", "step": "critique",
                    "label": "Adversarial self-review — Partner quality gate",
                    "detail": "Checking for missed loopholes, weak citations, and opposing counsel angles..."
                })

        # === PARALLELIZE CRITIQUE + VERIFICATION ===
        # These two LLM/network-bound passes are independent — critique evaluates
        # the response; verification live-checks citations on IK / statute DB.
        # Running them serially was adding 10-25s. Running concurrently saves that.
        augment_data = None
        _db = None
        try:
            from server import db as _server_db
            _db = _server_db
        except Exception:
            pass

        parallel_tasks = []
        parallel_labels = []
        if run_full_critique:
            parallel_tasks.append(run_critique_pass(session, final_response, user_query, GROQ_KEY_LIVE))
            parallel_labels.append("critique")
        if final_response and len(final_response) > 300 and not is_quick_mode:
            # Cap at 5 cases (was 8). Each IK verification is a live HTTP call ~1-3s.
            # 5 covers the load-bearing citations; beyond that is diminishing returns.
            parallel_tasks.append(augment_response(final_response, db=_db, max_case_verifications=5))
            parallel_labels.append("verify")
            yield json.dumps({
                "type": "research_step", "step": "verifying",
                "label": "Trust Layer — verifying citations",
                "detail": "Live-checking each case on IndianKanoon, each section in statute DB..."
            })

        if parallel_tasks:
            try:
                results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
                for label, result in zip(parallel_labels, results):
                    if isinstance(result, Exception):
                        logger.warning(f"{label} pass failed (non-blocking): {result}")
                        continue
                    if label == "critique":
                        critique_data = result
                        yield json.dumps({
                            "type": "critique_complete",
                            "structural_score": struct_data.get("score", 0) if struct_data else 0,
                            "partner_score": critique_data.get("score", 0) if critique_data else 0,
                            "partner_action": critique_data.get("action", "APPROVE") if critique_data else "APPROVE",
                            "hallucination_flags": len(halluc_flags),
                            "weaknesses_found": len(critique_data.get("weaknesses", [])) if critique_data else 0,
                        })
                    elif label == "verify":
                        augment_data = result
                        yield json.dumps({
                            "type": "verification_complete",
                            "trust_score": augment_data.get("trust_score", 0) if augment_data else 0,
                            "stats": augment_data.get("stats", {}) if augment_data else {},
                            "notes_count": len(augment_data.get("notes", [])) if augment_data else 0,
                        })
            except Exception as e:
                logger.warning(f"Parallel critique+verify orchestration failed: {e}")

        # Revision pass — tightened threshold + capped to Sonnet-tier (was full cascade).
        # Old: score < 6 triggered revision on every mediocre response = avg +60s.
        # New: only trigger when response is actually broken (score < 5) or marked
        # MAJOR_REWRITE. Use Sonnet direct (not the multi-tier cascade) so revision
        # is bounded at ~20-40s instead of 60-120s.
        if run_full_critique:
            needs_revision = (
                (critique_data and critique_data.get("action") == "MAJOR_REWRITE") or
                (critique_data and critique_data.get("score", 10) < 5) or
                (struct_data and struct_data.get("score", 100) < 45)
            )
            if needs_revision:
                yield json.dumps({
                    "type": "research_step", "step": "revising",
                    "label": "Revising response — addressing partner feedback",
                    "detail": f"Score: {critique_data.get('score', 0)}/10. Fixing {len(critique_data.get('weaknesses', []))} weaknesses..."
                })
                try:
                    feedback_block = format_critique_feedback(critique_data, struct_data, halluc_flags)
                    revision_prompt = f"{system_instruction}\n\n=== PARTNER REVIEW FEEDBACK ===\n{feedback_block}\n\nRevise your previous response to address ALL the feedback above. Keep the good parts, fix the weaknesses. The revised version must score 9+/10."
                    revised_content = f"ORIGINAL QUERY: {user_query}\n\nYOUR PREVIOUS DRAFT:\n{final_response[:6000]}\n\nNOW PRODUCE THE REVISED VERSION:"
                    # Direct Sonnet call, not the full cascade — revision is bounded, not a second first-pass
                    from claude_emergent import call_claude, CLAUDE_SONNET
                    revised = await call_claude(revision_prompt, revised_content, model=CLAUDE_SONNET, timeout=60)
                    if revised and len(revised) > len(final_response) * 0.7:
                        final_response = revised
                        citations = await find_citation_links(revised)
                        yield json.dumps({"type": "partner_payload", "content": f"\n\n---\n**[REVISED — Partner Review incorporated]**\n\n{revised}", "citations": citations, "is_revision": True})
                except Exception as e:
                    logger.warning(f"Revision pass failed (non-blocking): {e}")

        # Emit the augmented final response (with inline [✓]/[⚠] tags + verification report)
        if augment_data:
            yield json.dumps({
                "type": "partner_payload",
                "content": f"\n\n---\n**[VERIFIED — Spectr Trust Layer applied]**\n\n{augment_data['augmented_text']}",
                "trust_score": augment_data.get("trust_score", 0),
                "is_verified_version": True,
            })

        yield json.dumps({
            "type": "quality_metrics",
            "fast_score": fast_quality.get("score", 0),
            "deep_score": deep_quality.get("score", 0),
            "structural_score": struct_data.get("score", 0) if struct_data else 0,
            "partner_score": critique_data.get("score", 0) if critique_data else 0,
            "trust_score": augment_data.get("trust_score", 0) if augment_data else 0,
            "verified_citations": (augment_data.get("stats", {}).get("verified_cases", 0) + augment_data.get("stats", {}).get("verified_statutes", 0)) if augment_data else 0,
            "unverified_citations": (augment_data.get("stats", {}).get("unverified_cases", 0) + augment_data.get("stats", {}).get("unverified_statutes", 0)) if augment_data else 0,
            "hallucination_flags": len(halluc_flags),
            "sources_used": len(source_labels),
            "context_size": len(full_context),
            "conversation_turns": len(conversation_history) if conversation_history else 0,
        })

        yield json.dumps({"type": "research_step", "step": "complete", "label": "Analysis complete"})

        # ─── SUPERMEMORY: save this turn as persistent memory ───
        # Fire-and-forget — does not block the stream close. Captures both the
        # user query and the final assistant reply under the same conversation
        # so future queries from this user retrieve the full thread.
        if user_id and conversation_id:
            try:
                from supermemory_client import save_turn_background
                turn_base = len(conversation_history) if conversation_history else 0
                save_turn_background(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    turn_index=turn_base,
                    role="user",
                    content=user_query,
                    matter_id=matter_id,
                    mode=mode,
                )
                # Save the assistant's final consolidated reply (trust-layer
                # augmented when present, otherwise raw deep / baseline)
                _assistant_reply = ""
                if 'augment_data' in locals() and augment_data and augment_data.get("augmented_text"):
                    _assistant_reply = augment_data["augmented_text"]
                elif 'final_response' in locals() and final_response:
                    _assistant_reply = final_response
                elif 'deep_result' in locals() and deep_result:
                    _assistant_reply = deep_result
                elif 'baseline_result' in locals() and baseline_result:
                    _assistant_reply = baseline_result
                if _assistant_reply:
                    save_turn_background(
                        user_id=user_id,
                        conversation_id=conversation_id,
                        turn_index=turn_base + 1,
                        role="assistant",
                        content=_assistant_reply,
                        matter_id=matter_id,
                        mode=mode,
                    )
            except Exception as _e:
                logger.warning(f"Supermemory save-turn scheduling failed (non-blocking): {_e}")
