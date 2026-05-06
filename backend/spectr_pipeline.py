"""
spectr_pipeline.py — the 4-stage cascade per the Spectr operating brief.

Classifier (GPT-4o-mini, <2s)
  -> Retrieval (MongoDB, <200ms)
  -> Drafter   (ft:SyntaxAI or GPT-4.1, 15-25s)
  -> Critic    (GPT-4o-mini, 3-5s)
  -> Optional ONE rewrite if critic flags must_fix

Total target: 25-40s per query with the 8-section output contract from brief §3.

Why no multi-pass for normal queries:
  The earlier 13-pass system produced 14K words in 6 min. Spec is 30-50s
  max, quality over word count. This pipeline ships 2,000-4,000 word
  partner-grade memos in 30s by putting the depth into the SYSTEM PROMPT
  + RETRIEVED CHUNKS rather than chaining LLM calls.
"""
import os
import re
import json
import time
import hashlib
import asyncio
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger("spectr_pipeline")

OPENAI_KEY = os.environ.get("OPENAI_KEY", "")
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# Emergent universal-key proxy. ONE key fronts GPT-5/4.1/4o + Claude Sonnet 4.5/4.6
# at bulk pricing. We route everything except the GPT-5.5 top tier through here
# so the demo budget doesn't blow up on direct-OpenAI per-call rates.
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
EMERGENT_URL = "https://integrations.emergentagent.com/llm/v1/chat/completions"

# NVIDIA NIM — primary surface after Emergent budget exhaustion.
# Hosts Qwen3-Next-80B-Thinking (MoE A3B = 3B active, fast + reasoning),
# Mistral-Nemotron, Phi-4. OpenAI-compatible.
NVIDIA_NIM_KEY = os.environ.get("NVIDIA_NIM_KEY", "")
NVIDIA_NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# Groq — fastest LPU inference on the planet. We use it ONLY for the cheap
# "is this trivial chitchat or a real legal question?" gate. ~400ms, free
# under quota, leaves the premium budget for the actual memo generation.
GROQ_KEY = os.environ.get("GROQ_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Parallel.ai — deep web research API. LLM-optimized excerpts with citations.
# Gives us research depth that Serper (snippet-only) can't match.
PARALLEL_KEY = os.environ.get("PARALLEL_WEB_KEY", "")
PARALLEL_URL = "https://api.parallel.ai/v1/search"
GROQ_INTENT_MODEL = "llama-3.1-8b-instant"        # ~200ms intent gate (T/L)
GROQ_ORCHESTRATOR_MODEL = "llama-3.3-70b-versatile"  # ~700ms full classifier + routing

# z.ai (Zhipu GLM) — extra budget tier. Off by default (account balance 429s)
# but the driver auto-falls through to OpenAI/Emergent on failure so it's safe
# to leave in the routing chain.
ZAI_KEY = os.environ.get("ZAI_API_KEY", "")
ZAI_URL = "https://api.z.ai/api/paas/v4/chat/completions"
ZAI_MODEL_BUDGET = "glm-4.5"
ZAI_MODEL_DEEP = "glm-4.6"

# ─────────────────────────────────────────────────────────────────────
# MODEL ROUTING — PEAK REASONING ONLY. Two drafters, nothing else.
# ─────────────────────────────────────────────────────────────────────
# Tier            | Model                            | Surface | Why
# ─────────────────┼──────────────────────────────────┼─────────┼──────────────
# Drafter (only)  | gpt-5.5                          | direct  | Mandatory, effort=medium
# Drafter (FB)    | mistral-large-3-675b (NIM)       | NIM     | 5.6s, non-thinking, fast failover
# Classifier      | gpt-5.5                          | direct  | Same model, fast intent
# Critic          | gpt-5.5                          | direct  | Same model, light pass
# DEMO LOCK — Rohan Bagai meeting: GPT-5.5 mandatory. NO Llama, NO Claude
# (Emergent budget exhausted), NO gpt-4o-mini, NO Sonnet. Top reasoning or nothing.
MODEL_CLASSIFIER     = "gpt-5.5"
MODEL_CRITIC         = "gpt-5.5"
MODEL_DRAFTER_SIMPLE = "gpt-5.5"
MODEL_DRAFTER_MEDIUM = "mistralai/mistral-large-3-675b-instruct-2512"  # NIM fallback — 675B Mistral, non-thinking, ~5s
MODEL_DRAFTER_DEEP   = "gpt-5.5"
MODEL_DRAFTER_TOP    = "gpt-5.5"                             # mandatory default
MODEL_DRAFTER_OPUS   = "mistralai/mistral-large-3-675b-instruct-2512"  # alias for legacy refs

# Models that MUST be called direct OpenAI (Emergent doesn't have them)
DIRECT_OPENAI_ONLY = {"gpt-5.5", "gpt-5", "gpt-5-mini"}

# Models that use the new max_completion_tokens param instead of max_tokens
GPT5_FAMILY = {"gpt-5", "gpt-5-mini", "gpt-5.5", "gpt-5.5-turbo"}

# z.ai health is tested once per process to avoid burning an HTTP call per
# classifier hit when the account is in 429-loop. Flip to None to force re-probe.
_ZAI_HEALTHY: Optional[bool] = None

# Web research cache — Parallel.ai + Serper results keyed by md5(query+domain).
# 15-minute TTL means a user iterating on the same matter pays the 2-3s web
# round-trip once, not on every refinement query.
_WEB_CACHE: dict[str, dict] = {}
_WEB_CACHE_TTL = 900  # 15 minutes


async def _kickoff_background_check(user_query: str):
    """Fire a sandbox-driven deep research task for entity/person background check.

    Returns an asyncio.Task that resolves to a formatted findings block (str)
    or '' if sandbox unavailable. The orchestrator awaits with a 90s cap.

    The findings block is shaped as a ready-to-paste section labelled
    'BACKGROUND CHECK FINDINGS' covering: court history (IndianKanoon),
    company filings (MCA where applicable), regulatory actions (SEBI/RBI/ED),
    media coverage, and any litigation timelines surfaced.
    """
    try:
        from sandbox_research import execute_deep_research
    except Exception as e:
        logger.debug(f"[bg_check] sandbox_research import failed: {e}")
        return None

    async def _run():
        try:
            t0 = time.time()
            # Heuristic query_types for due-diligence — push browser to all
            # the relevant Indian record sources.
            query_types = ["legal", "litigation", "corporate", "regulatory"]
            result = await execute_deep_research(user_query, query_types)
            elapsed = time.time() - t0
            logger.info(f"[bg_check] deep research returned in {elapsed:.1f}s")
            if not result:
                return ""
            # Format the dossier
            return _format_bg_check_block(result, user_query, elapsed)
        except Exception as e:
            logger.warning(f"[bg_check] non-blocking error: {e}")
            return ""

    return asyncio.create_task(_run())


def _format_bg_check_block(result: dict, user_query: str, elapsed_s: float) -> str:
    """Render execute_deep_research output as the BACKGROUND CHECK section."""
    parts = ["**BACKGROUND CHECK — LIVE SANDBOX FINDINGS**"]
    parts.append(
        f"_Investigation completed in {elapsed_s:.0f}s using a sandboxed headless "
        f"browser running across IndianKanoon, MCA21, court filings, regulatory "
        f"databases, and live news sources. Every link below was retrieved seconds ago._"
    )
    parts.append("")

    # Pull from result structure (depends on what execute_deep_research returns)
    # The function returns a dict with searchResults, pageContents, entities, etc.
    sr = result.get("searchResults", []) or []
    pc = result.get("pageContents", []) or []
    entities = result.get("entities", {}) or {}
    timeline = result.get("timeline", []) or []
    opposing = result.get("opposingFindings", []) or []

    # Identified entities
    if entities:
        named = entities.get("entity_names") or entities.get("companies") or []
        people = entities.get("people") or entities.get("persons") or []
        cases = entities.get("case_names") or entities.get("cases") or []
        if named or people:
            parts.append(f"**Subjects identified.** {', '.join((named + people)[:8])}")
        if cases:
            parts.append(f"**Cases surfaced.** {len(cases)} matter{'s' if len(cases) != 1 else ''} matching the subject — top hits: {', '.join(cases[:5])}")
        parts.append("")

    # Litigation history
    litigation_pages = [p for p in pc if isinstance(p, dict) and any(
        s in (p.get("url", "") or "").lower()
        for s in ["indiankanoon", "courtnic", "courtindia", "ecourts", "judis"]
    )]
    if litigation_pages:
        parts.append("**Litigation history.**")
        for p in litigation_pages[:8]:
            title = (p.get("title") or "")[:120]
            url = p.get("url", "")
            snippet = (p.get("text") or p.get("excerpt") or "")[:280].replace("\n", " ")
            if title and url:
                parts.append(f"- [{title}]({url}) — {snippet}…")
        parts.append("")

    # Corporate filings
    corp_pages = [p for p in pc if isinstance(p, dict) and any(
        s in (p.get("url", "") or "").lower()
        for s in ["mca.gov", "zaubacorp", "tofler", "instafinancials"]
    )]
    if corp_pages:
        parts.append("**Corporate filings (MCA21 / corporate registries).**")
        for p in corp_pages[:5]:
            title = (p.get("title") or "")[:120]
            url = p.get("url", "")
            snippet = (p.get("text") or "")[:240].replace("\n", " ")
            if title and url:
                parts.append(f"- [{title}]({url}) — {snippet}…")
        parts.append("")

    # Regulatory actions
    reg_pages = [p for p in pc if isinstance(p, dict) and any(
        s in (p.get("url", "") or "").lower()
        for s in ["sebi.gov", "rbi.org", "irdai.gov", "enforcement", "ed.gov", "incometax"]
    )]
    if reg_pages:
        parts.append("**Regulatory actions (SEBI / RBI / ED / IT Department).**")
        for p in reg_pages[:5]:
            title = (p.get("title") or "")[:120]
            url = p.get("url", "")
            snippet = (p.get("text") or "")[:240].replace("\n", " ")
            if title and url:
                parts.append(f"- [{title}]({url}) — {snippet}…")
        parts.append("")

    # Media coverage
    media_pages = [p for p in pc if isinstance(p, dict) and any(
        s in (p.get("url", "") or "").lower()
        for s in ["livelaw", "barandbench", "moneycontrol", "economictimes", "business-standard", "livemint", "thehindu"]
    )]
    if media_pages:
        parts.append("**Media coverage.**")
        for p in media_pages[:5]:
            title = (p.get("title") or "")[:120]
            url = p.get("url", "")
            snippet = (p.get("text") or "")[:240].replace("\n", " ")
            if title and url:
                parts.append(f"- [{title}]({url}) — {snippet}…")
        parts.append("")

    # Timeline if surfaced
    if timeline:
        parts.append("**Chronological timeline of public events.**")
        for evt in timeline[:12]:
            if isinstance(evt, dict):
                date = evt.get("date", "—")
                what = evt.get("event") or evt.get("description") or evt.get("text", "")
                parts.append(f"- {date} — {what[:200]}")
        parts.append("")

    # Counter-findings (if user is on one side, the other side's case)
    if opposing:
        parts.append("**Counter-findings (the other side's narrative).**")
        for f in opposing[:5]:
            if isinstance(f, dict):
                t = (f.get("title") or "")[:120]
                u = f.get("url", "")
                parts.append(f"- [{t}]({u})")
            else:
                parts.append(f"- {str(f)[:200]}")
        parts.append("")

    # Source-count footer
    parts.append(
        f"_{len(sr)} searches executed • {len(pc)} pages extracted • "
        f"{len(litigation_pages)} litigation hits • {len(corp_pages)} corporate filings • "
        f"{len(reg_pages)} regulatory mentions • {len(media_pages)} media references_"
    )

    return "\n".join(parts)


async def _probe_zai() -> bool:
    """One-shot health probe so we don't keep hitting a dead z.ai balance."""
    global _ZAI_HEALTHY
    if _ZAI_HEALTHY is not None:
        return _ZAI_HEALTHY
    if not ZAI_KEY:
        _ZAI_HEALTHY = False
        return False
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as s:
            async with s.post(
                ZAI_URL,
                headers={"Authorization": f"Bearer {ZAI_KEY}", "Content-Type": "application/json"},
                json={"model": ZAI_MODEL_BUDGET, "messages": [{"role": "user", "content": "ok"}], "max_tokens": 3},
            ) as r:
                _ZAI_HEALTHY = r.status == 200
                if not _ZAI_HEALTHY:
                    logger.info(f"[spectr_pipeline] z.ai probe failed: HTTP {r.status} — will stay on OpenAI this process")
                else:
                    logger.info("[spectr_pipeline] z.ai healthy — budget queries will route through GLM")
                return _ZAI_HEALTHY
    except Exception as e:
        logger.info(f"[spectr_pipeline] z.ai probe error: {e} — OpenAI only")
        _ZAI_HEALTHY = False
        return False


# ============================================================================
# STAGE 0 — CLASSIFIER
# ============================================================================

CLASSIFIER_PROMPT = """You are the orchestrator for an Indian legal/tax research platform. You read the user's query and decide:
  1. What kind of question this is (domain, task, complexity)
  2. What to retrieve from the statute/case corpus
  3. WHICH MODEL should draft the answer

You emit EXACTLY this JSON schema (no prose, no markdown fences — raw JSON object):

{
  "domain": "direct_tax"|"indirect_tax"|"corporate_law"|"ipr"|"criminal"|"civil_procedure"|"constitutional"|"labour"|"sebi_fema"|"ibc"|"family"|"property"|"fintech"|"other",
  "task": "lookup"|"drafting"|"research_memo"|"opinion"|"computation"|"compliance_check"|"case_strategy"|"summarisation",
  "complexity": 1|2|3|4|5,
  "needs_case_law": true|false,
  "needs_computation": true|false,
  "jurisdictional_state": "<state name or null>",
  "retrieval_queries": ["<q1>", "<q2>", "..."],
  "recommended_model": "gpt-5.5",
  "escalate_to_claude": true|false
}

CLASSIFICATION RULES:
- domain: single best-fit tag.
- task: single best-fit tag.
- complexity: 1=rate/threshold lookup, 2=single-section explanation, 3=single-issue advisory, 4=multi-section scenario or SCN reply, 5=novel multi-statute / constitutional / cross-border / high-stakes.
- retrieval_queries: 3-8 specific search strings for a statute/case RAG layer. Expand synonyms. Example: for "TDS on rent", emit ["Section 194I Income-tax Act TDS rent", "Section 194IB TDS individual HUF rent", "TDS rates plant machinery land building 2024-25"].
- escalate_to_claude: true ONLY when the query needs the "best partner-grade reasoning" — multi-statute synthesis, novel questions, high-stakes constitutional matters, or user explicitly asked for "deep analysis" / "depth research" / "partner-grade".

MODEL RECOMMENDATION RULES — GPT-5.5 MANDATORY:

The user mandate (Rohan Bagai meeting) is locked: GPT-5.5 Pro is the ONLY drafter. No Sonnet, no Opus, no Llama, no 4o-mini. If GPT-5.5 errors, the runtime silently retries on Qwen3-Thinking via NVIDIA NIM — but you, the classifier, only ever recommend "gpt-5.5".

- "gpt-5.5" → ALWAYS. Tax, GST, case law, constitutional, drafting, computation — everything goes here at peak reasoning effort.

Emit ONLY the JSON object. No code fences. No commentary."""


async def _classify_via_groq(query: str, recent_history: Optional[list] = None) -> Optional[dict]:
    """Groq llama-3.3-70b orchestrator. Returns full classification dict or None on failure.

    ~700ms, free under Groq quota. Replaces the gpt-4o-mini classifier as the
    primary orchestrator — Groq picks the downstream drafter (Claude / GPT-5.5
    / GPT-4.1) based on its analysis of the query's complexity and task.
    """
    if not GROQ_KEY:
        return None

    user_content = query
    if recent_history:
        last_two = recent_history[-4:]
        hist_lines = []
        for h in last_two:
            role = h.get("role", "user")
            text = (h.get("content") or "")[:500]
            hist_lines.append(f"[{role}] {text}")
        if hist_lines:
            user_content = "RECENT CONTEXT:\n" + "\n".join(hist_lines) + f"\n\nCURRENT QUERY:\n{query}"

    payload = {
        "model": GROQ_ORCHESTRATOR_MODEL,
        "messages": [
            {"role": "system", "content": CLASSIFIER_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0,
        "max_tokens": 600,
        "response_format": {"type": "json_object"},
    }
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
            async with s.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                json=payload,
            ) as r:
                if r.status != 200:
                    err = await r.text()
                    logger.info(f"[orchestrator] groq HTTP {r.status}: {err[:160]}")
                    return None
                data = await r.json()
                text = data["choices"][0]["message"]["content"]
                try:
                    result = json.loads(text)
                except Exception:
                    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
                    result = json.loads(text)
                usage = data.get("usage", {})
                result["_usage"] = {
                    "model": GROQ_ORCHESTRATOR_MODEL,
                    "in_tokens": usage.get("prompt_tokens", 0),
                    "out_tokens": usage.get("completion_tokens", 0),
                }
                return result
    except Exception as e:
        logger.info(f"[orchestrator] groq exception: {e}")
        return None


async def classify_query(query: str, recent_history: list[dict] | None = None) -> dict:
    """Stage 0 — gpt-5.5 classifier ONLY. No Groq, no fallback to lesser models.

    DEMO LOCK: Rohan Bagai meeting requires only top-tier models in entire stack.
    Falls back to deterministic regex only if gpt-5.5 itself is unreachable.
    """
    url, key, surface = _route_for_model(MODEL_CLASSIFIER)
    if not key:
        return _fallback_classification(query)

    # Include last 2 turns if provided (spec §2 Stage 0)
    user_content = query
    if recent_history:
        last_two = recent_history[-4:]  # 2 user + 2 assistant
        hist_lines = []
        for h in last_two:
            role = h.get("role", "user")
            text = (h.get("content") or "")[:500]
            hist_lines.append(f"[{role}] {text}")
        if hist_lines:
            user_content = "RECENT CONTEXT:\n" + "\n".join(hist_lines) + f"\n\nCURRENT QUERY:\n{query}"

    # gpt-5.5 uses max_completion_tokens (not max_tokens) and no temperature.
    # Larger budget so reasoning tokens don't starve the JSON output.
    is_gpt5_classifier = MODEL_CLASSIFIER in GPT5_FAMILY
    payload = {
        "model": MODEL_CLASSIFIER,
        "messages": [
            {"role": "system", "content": CLASSIFIER_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "response_format": {"type": "json_object"},
    }
    if is_gpt5_classifier:
        payload["max_completion_tokens"] = 8000
        payload["reasoning_effort"] = "low"  # classification is decision-tree, not deep reasoning
    else:
        payload["temperature"] = 0
        payload["max_tokens"] = 400
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    logger.warning(f"Classifier {surface} HTTP {resp.status}: {err[:200]}")
                    # If Emergent failed, try direct OpenAI once before regex
                    if surface == "emergent" and OPENAI_KEY:
                        async with session.post(OPENAI_URL,
                            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
                            json=payload) as r2:
                            if r2.status == 200:
                                data = await r2.json()
                                surface = "openai-direct"
                            else:
                                return _fallback_classification(query)
                    else:
                        return _fallback_classification(query)
                else:
                    data = await resp.json()
                text = data["choices"][0]["message"]["content"]
                try:
                    result = json.loads(text)
                except Exception:
                    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
                    result = json.loads(text)
                usage = data.get("usage", {})
                result["_usage"] = {
                    "model": MODEL_CLASSIFIER,
                    "surface": surface,
                    "in_tokens": usage.get("prompt_tokens", 0),
                    "out_tokens": usage.get("completion_tokens", 0),
                }
                return result
    except Exception as e:
        logger.warning(f"Classifier failed: {e}")
        return _fallback_classification(query)


def _fallback_classification(query: str) -> dict:
    """Regex fallback when classifier LLM is unreachable."""
    q = (query or "").lower()
    complexity = 2
    if len(q.split()) > 60 or any(w in q for w in ["scn", "notice", "draft", "writ", "petition", "bail", "constitutional"]):
        complexity = 4
    domain = "other"
    if any(w in q for w in ["gst", "cgst", "itc", "gstr", "scn"]):
        domain = "indirect_tax"
    elif any(w in q for w in ["income tax", "tds", "section 194", "itr", "assessment"]):
        domain = "direct_tax"
    elif any(w in q for w in ["bns", "bnss", "fir", "bail", "criminal", "cheating", "murder"]):
        domain = "criminal"
    elif any(w in q for w in ["ibc", "cirp", "insolvency", "liquidation", "nclt"]):
        domain = "ibc"
    elif any(w in q for w in ["companies act", "director", "agm", "board resolution", "mca"]):
        domain = "corporate_law"
    elif any(w in q for w in ["payment aggregator", "upi", "dpdp", "data protection", "fintech", "ppi", "digital lending", "account aggregator", "tokenization", "crypto", "vda", "rbi licence", "pa licence", "pa-o", "pa-p", "pa-cb", "consent manager", "data fiduciary", "data principal", "npci", "fldg", "dlg", "lsp", "lending service", "digital loan", "virtual digital asset", "fiu-ind", "kyc refresh", "escrow account", "payment gateway", "bbpou", "prepaid instrument", "wallet", "personal data", "privacy", "consent architecture", "cross-border payment", "sahamati", "aadhaar", "e-kyc"]):
        domain = "fintech"
    return {
        "domain": domain,
        "task": "research_memo" if complexity >= 4 else "opinion",
        "complexity": complexity,
        "needs_case_law": complexity >= 3,
        "needs_computation": any(w in q for w in ["compute", "calculate", "rate", "exposure"]),
        "jurisdictional_state": None,
        "retrieval_queries": [query],
        "escalate_to_claude": complexity >= 5,
        "_usage": {"model": "fallback-regex", "in_tokens": 0, "out_tokens": 0},
    }


# ============================================================================
# STAGE 1 — RETRIEVAL (no LLM)
# ============================================================================

async def retrieve_chunks(queries: list[str], k: int = 12, domain: Optional[str] = None) -> list[dict]:
    """Stage 1 — hit the Spectr legal corpus.

    Returns chunks with stable citation strings:
      {
        "chunk_id": "stat_74_cgst",            # stable ID for [Corpus §N] citations
        "text":     "<chunk body>",
        "citation": "Section 74 of the CGST Act, 2017",
        "source":   "statute_db" | "case_law" | "notification",
        "score":    float,
      }

    Uses the existing get_statute_context from server.py (MongoDB/Firestore with
    3-pass retrieval: exact section, act-keyword, topic). For the spec's k=12
    goal we combine results across all queries and dedupe.
    """
    try:
        from server import get_statute_context
    except Exception:
        return []

    # PARALLEL corpus calls — was serial 6×3s=18s, now max(6 queries) ≈ 2-3s.
    # Cap at top 4 queries (classifier emits 3-8, top 4 give >95% recall).
    async def _safe_ctx(q: str) -> str:
        try:
            return await get_statute_context(q) or ""
        except Exception as e:
            logger.debug(f"retrieve for '{q}' failed: {e}")
            return ""

    top_queries = queries[:4]
    contexts = await asyncio.gather(*(_safe_ctx(q) for q in top_queries))

    seen_keys = set()
    chunks: list[dict] = []
    for ctx in contexts:
        if not ctx:
            continue
        # get_statute_context returns "[DB RECORD] Section X of Act — title\n<text>"
        for block in ctx.split("[DB RECORD]"):
            block = block.strip()
            if not block:
                continue
            lines = block.split("\n", 1)
            header = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ""

            # SCRAMBLE GUARD — detect bodies that are TOC bleed from the
            # next section (audit found 22/2905 entries like §26 IT Act
            # whose body is just the §28+ table-of-contents). Skip them
            # silently — drafter falls back to training knowledge for
            # those specific sections.
            if _is_scrambled_body(body):
                logger.debug(f"[retrieve] skipping scrambled chunk: {header[:60]}")
                continue

            m = re.match(r"Section\s+(\S+)\s+of\s+(.+?)\s+[—-]\s+(.*)", header)
            if m:
                sec, act, title = m.group(1), m.group(2), m.group(3)
                chunk_id = f"{_slug(act)}_sec_{sec}"
                citation = f"Section {sec} of the {act}"
            else:
                chunk_id = f"chunk_{hashlib.md5(header.encode()).hexdigest()[:8]}"
                citation = header[:80]
            if chunk_id in seen_keys:
                continue
            seen_keys.add(chunk_id)
            chunks.append({
                "chunk_id": chunk_id,
                "text": body[:1500],  # tighter per-chunk cap (was 3000) for TPM headroom
                "citation": citation,
                "source": "statute_db",
                "score": 1.0,
            })
            if len(chunks) >= k:
                break
        if len(chunks) >= k:
            break
    return chunks[:k]


_TOC_BLEED_RE = re.compile(
    r"(?:[A-Z][a-z][^\n]{5,80}\s*\n)?(\s*\d+[A-Z]?\.\s+[A-Z][^\n]{3,80}\s*\n){3,}"
)
_PROSE_LEAD_RE = re.compile(
    r"^[\(\[]\d|^Notwithstanding|^Subject to|^Where\b|^Any \b|^The \b|^In this|^Save as|^If \b"
)


def _is_scrambled_body(body: str) -> bool:
    """Detect TOC-bleed scrambling in a statute chunk body.

    True if body STARTS with a 'NN. Title' table-of-contents block (3+ lines)
    rather than statute prose. Audit shows 22/2905 corpus entries fail this
    test — typically §26 IT Act whose body is the Chapter IV-D TOC.
    """
    if len(body) < 100:
        return False
    first_500 = body[:500]
    m = _TOC_BLEED_RE.search(first_500)
    if not m:
        return False
    before_toc = first_500[:m.start()].strip()
    if _PROSE_LEAD_RE.search(before_toc):
        return False
    return True


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:24]


def format_chunks_for_prompt(chunks: list[dict]) -> str:
    """Render chunks for the drafter's <CORPUS> tag."""
    if not chunks:
        return "(no chunks retrieved — drafter must flag un-grounded statements)"
    lines = []
    for c in chunks:
        lines.append(
            f"[§{c['chunk_id']}] {c['citation']}\n{c['text']}\n"
        )
    return "\n".join(lines)


# ============================================================================
# STAGE 2 — DRAFTER
# ============================================================================

DRAFTER_PROMPT_CORE = """You are Spectr — research and filing artifacts for Indian advocates, CAs, CSs, in-house counsel. Reader's time costs ₹15-50K/hr.

HARD OUTPUT RULES (apply to the very first token):
1. Never narrate process. Forbidden openers (any variation): "Okay, let's…", "Let me…", "First I need…", "Looking at the corpus…", "From the corpus…", "The user is asking…", "I'll tackle…", "Wait…", "Sure, here's…", "Got it", "Understood".
2. The corpus is your source — it never appears in the output. Mislabelled chunk? Skip it silently, use training. Never write "the corpus shows…" / "based on the provided corpus…".
3. First sentence = the direct answer / the leading case + dispositive ratio (8-12 words) / a verb-led recommended action. No restatement of the question.
4. Never expose raw [§...] tags, "[Unverified by corpus]", or token-budget scaffolding. Read as a senior partner's signed opinion.

FIND THINGS VANILLA CLAUDE WOULD NEVER SURFACE — this is the differentiator:
  • The procedural defect that makes the Department's whole notice void (jurisdictional AO post Notification 18/2022; SCN missing DIN; §74 invoked without fraud particulars; faceless scheme bypassed; pre-deposit waiver overlooked; limitation already expired by 4 days).
  • The recent (2024-2025) HC/ITAT decision that updates the position the textbook still has wrong — name it, give the bench, quote 1-2 lines from the operative paragraph.
  • The state/bench-specific overlay (Maharashtra stamp duty differs from Karnataka; Bombay HC numbered grounds vs Delhi HC para-grouped; NCLT vs NCLAT format differences; specific officer designations like "Joint Director (Investigation)" not just "the AO").
  • The interlocking compliance the question doesn't ask but matters (DPDP Section 16 cross-border + RBI Master Direction on Outsourcing of IT Services 10.04.2023 + Storage of Payment Data Direction 06.04.2018 — answer the user's question, then note all three apply in parallel).
  • The litigation-strategy angle (which forum first, what relief sequence, which proviso to invoke, what evidence to lock in early, what NOT to admit in writing).
  • The drafting tell that signals Indian-trained counsel (correct form numbers, correct bench-specific addressing, correct "respondent No. 1" syntax, correct "Honourable" capitalisation, ₹ in lakh/crore notation, dates DD.MM.YYYY).
  • The computation the user didn't ask for but needs — interest u/s 220(2) at 1% per month, late fee u/s 234E, penalty exposure u/s 271/272 — quantified on their actual numbers.
  • The "what could shift this" closer — pending SLPs, recent referral to a larger bench, expected legislative amendment, market-practice that diverges from technical position.

EIGHT CAPABILITIES — every substantive response shows these (compressed):
  1. CURRENT-DAY STATUTE: BNS/BNSS/BSA from 01.07.2024 (cite "BNS §103 (formerly IPC §302)"). GST 2.0 from 22.09.2025. Finance Act 2025: §87A rebate ₹60K / ₹12L threshold, std-ded ₹75K, slabs 0-4-8-12-16-20-24L, §112A LTCG 12.5%/₹1.25L, §111A STCG 20%, §80CCD(2) NPS 14%. Labour Codes from 21.11.2025. §148A regime FA 2021, §149 limitation 3yr/10yr. Repealed law never appears as current.
  2. CORPUS-GROUNDED: every statute cite tied to retrieved <CORPUS> chunk via [Corpus §<id>]. Training-only positions: prefix "[unverified by corpus]".
  3. CASE LAW + INDIAN KANOON LINKS: in the precedent table — `https://indiankanoon.org/search/?formInput=<keywords>`. Real cases only; if unsure, state the principle without a citation.
  4. FILING-READY ARTIFACT: not "you should file" — produce the draft paragraphs (blockquoted) / computation table / chronological calendar with form numbers (DRC-01/06/07, APL-01, DIR-12, AOC-2, Form 26Q/27Q/15CA/CB, 10-IEA).
  5. PROCEDURAL ARITHMETIC: limitation periods on the actual dates. Math on the page, not the partner's head.
  6. THE DISPOSITIVE POINT, NOT BURIED: jurisdictional flaw / procedural defect / wrong-section invocation surfaced inline (e.g., JAO §148A void post-Notification 18/2022; §74 with no fraud particulars collapses to §73).
  7. CROSS-DOC REASONING + VAULT HOOK: end with "Upload [specific docs] to your Spectr Vault — I'll cross-check limitation arithmetic, flag DIN/approval issues, identify procedural defects."
  8. INDIAN PRACTICE REGISTER: SCN replies = formal-respectful; writs = constitutional-persuasive; opinions = measured-decisive; board resolutions = procedural-minimalist. State + bench overlays where relevant.

PRE-SUBMISSION CHECK: does the draft contain current statute, corpus-tagged cites, IndianKanoon-linked precedent table, filing-ready artifact, date arithmetic, the tactical point that wins, Vault hook? Add what's missing.

ANSWER WHAT WAS ASKED. Nothing more. Nothing less.
  • User asked for case laws on X → list the cases, court by court, with the leading authority called out by name in the FIRST line. No "issue framing" of their own question.
  • User asked to draft a reply → give the draft. The legal analysis is supporting; the draft is the deliverable.
  • User asked for computation → show the math. Lead with the number, walk through how you got there.
  • User asked a strategic question → name the play. Identify the dispositive variable. Resolve it on the facts.
  • User asked a definitional question → the definition, the exception, the recent amendment that changed it, in three sentences. No padding.

ULTRA-LONG MANDATE — there is no upper limit on response length. Depth wins. The reader is paying for exhaustive partner-grade research, not summary. Use as many tokens as the question warrants. Default minimums:
  • Pure rate / threshold lookup: 200-400 words (still cite the section, the recent amendment, the related sections)
  • Single-issue advisory: 1200-2000 words (statutory analysis, judicial position with bench-by-bench grouping, computation if applicable, procedural exposure, drafting flag)
  • Multi-issue / SCN / writ / opinion: 2500-4500 words (every sub-issue gets a full paragraph block, every angle covered, every relevant case named with its dispositive ratio)
  • Cross-statutory / constitutional / due diligence / FinTech-DPDP / M&A: 4000-7000+ words. Don't compress. The deeper the better.

When a question carries sub-issues (a/b/c/d structure), EACH sub-issue gets its own multi-paragraph treatment — never a single sentence per. Cover the statutory position, the judicial gloss, the contrarian view, the recent development, the procedural angle, the tactical angle, and the practical recommendation for EACH sub-issue.

NEVER stop short to "be concise". Concise is what vanilla Claude does. You exhaust the question. If you can think of one more relevant case, name it. One more proviso, surface it. One more procedural risk, flag it. One more drafting consideration, add it. The output reads like a senior partner has spent 4-6 hours and is delivering the comprehensive note — not a chatbot summary.

VOICE — senior partner, not textbook:
  • Short declarative sentences. Contractions OK. "We" for our side; name counterparty ("the Department", "the AO", "the OP", "the Tribunal").
  • Banned: "it is humbly submitted", "it would not be inappropriate", "in our considered opinion", "in light of the above", "having said that", "needless to say", "as per", "the user is asking", "the real question is", "the fork is".
  • Calibrate plainly: "it's settled" / "Bombay says yes, Madras says no, we bet on yes because…" / "untested post-amendment". Never "it depends" without naming on-what.
  • Lead with the answer.

DON'T (vanilla LLM tells): opens by restating the question; generic "Issue Framing / Governing Law" template; hedges ("may", "could potentially", "subject to applicable laws"); cites Vodafone/McDowell without the recent update; "Let me know if you need…"; "consult a tax professional" disclaimers.

DO (Spectr): first sentence = the answer / leading case + ratio. Flows as continuous prose. Reads like a senior counsel's signed opinion or a Tribunal order: dense, decisive, navigable.

NO formulaic ## section headings ("## Issue Framing", "## Governing Law", "## Conclusion") — those are vanilla-LLM template tells. BUT for ultra-long responses (2000+ words) covering multiple sub-issues, you MAY use ITALICIZED LEAD-IN PHRASES at paragraph starts to anchor the reader, e.g.:
   *On the limitation question.* The SCN dated 02.01.2025 …
   *Turning to cross-border data transfer.* §16 DPDP Act read with …
   *On the RBI Outsourcing Direction overlap.* …
   *Tactical recommendation.* …
These are inline pivots, not ## headers — they let a 5000-word response stay scannable while still flowing as one continuous opinion.

Recent (2023+) HC/ITAT/CESTAT cited with bench + 1-2 line ratio. Procedural defect / limitation expiry surfaced inline. Exact form + deadline + filing authority as inline sentences. Artifacts (precedent table, draft block, computation table, timeline, Vault hook) bottom-loaded with brief lead-in lines.

DELIVERABLE MANDATE — every substantive response (not a one-line lookup) closes with ≥2 of these artifacts. Bottom-loaded. Brief lead-in line, no ## headings.

ARTIFACT 1 — PRECEDENT CITATION TABLE (case-law / opinion / strategy)
| Case | Court / Year | Ratio (≤ 18 words) | IndianKanoon |
|---|---|---|---|
| *Hexaware Technologies v. ACIT* (2024) 464 ITR 430 | Bombay HC, 2024 | Post-Notification 18/2022, only FAO can issue §148A notices; JAO-issued void. | [verify](https://indiankanoon.org/search/?formInput=Hexaware+Technologies+ACIT) |

URL pattern: `https://indiankanoon.org/search/?formInput=<URL-encoded keywords>`. Real cases only.

ARTIFACT 2 — FILING-READY DRAFT TEXT (drafting / SCN reply / writ / opinion-with-action). Lead-in: "Operative paragraphs the partner can paste:" then blockquoted draft in Indian legal register — DD.MM.YYYY dates, ₹ lakh/crore notation, DIN refs, statutory provisos.

ARTIFACT 3 — COMPUTATION TABLE (tax / accounting / quantum). Lead-in: "Computation:"
| Component | Formula | Substitution | ₹ |
|---|---|---|---:|
| TDS §194J | Sum × 10% | 5,00,000 × 10% | 50,000 |
| Interest §201(1A) | TDS × 1% × months | 50,000 × 1% × 14 | 7,000 |
| **Total** | | | **57,000** |

ARTIFACT 4 — LITIGATION/COMPLIANCE TIMELINE (procedural). Lead-in: "Calendar:"
| Date | Event | Form | Authority | Days from Notice |
|---|---|---|---|---:|
| 02.01.2025 | SCN under §74 | DRC-01 | Proper Officer | 0 |
| 01.02.2025 | Reply due | DRC-06 | Proper Officer | +30 |
| ~01.04.2025 | Order under §74(9) | DRC-07 | Proper Officer | +90 |

ARTIFACT 5 — VAULT HOOK (always). Closing line:
> **Vault check:** Upload [specific docs for this matter] to your Spectr Vault — I'll cross-check limitation arithmetic, flag DIN/approval issues, identify procedural defects against the live record.

SELECTION:
- Case-law/jurisprudence → Artifact 1 mandatory + 5. Add 2 if pleading implied.
- Drafting → Artifact 2 mandatory. Add 4 if procedural.
- Computation → Artifact 3 mandatory.
- SCN/notice/litigation strategy → 1 + 2 + 4.
- Pure rate lookup → no artifacts; 2-3 sentence answer.

HALLUCINATION RULE — non-negotiable. Indian case names are formulaic and easy to invent; vanilla LLMs hallucinate them constantly. You don't.
  • Not 100% sure the citation exists? State the principle without a citation. Write "[case verification needed]" or "the principle, drawn from a line of HC decisions, is…".
  • Better one real case than five plausible inventions. Don't pad case lists.
  • Specific high-stakes domains have curated case authority loaded via the domain extension below — use those when the query intersects.

INDIAN LAW FRESHNESS CARD (FY 2025-26 / AY 2026-27) — wins over training memory:
- BNS/BNSS/BSA from 01.07.2024. Post-01.07.2024 offences ALWAYS in new codes; format "BNS §X (formerly IPC §Y)". Citing IPC/CrPC/IEA for a 2025 matter is the single biggest stale-LLM tell.
- 4 LABOUR CODES from 21.11.2025 (Wages 2019, IR 2020, Social Security 2020, OSH 2020) — replace 29 old laws (PoW 1936, ID 1947, Factories 1948, EPF 1952, Gratuity 1972, Bonus 1965). §2(y) wage definition: inclusive (cash+DA+retaining) + exclusionary (HRA/conveyance/bonus/OT/PF/NPS) + 50% proviso (excess added back).
- GST 2.0 from 22.09.2025: old 5/12/18/28% → 5% merit + 18% standard + 40% sin/luxury. Cement 28→18, insurance 18→exempt, small cars 28→18. Time of supply §12 CGST governs rate.
- DIRECT TAX FA 2025: §87A rebate ₹60K / ≤ ₹12L (NOT ₹25K/₹7L); std-ded ₹75K; §115BAC new regime DEFAULT, opt-out Form 10-IEA; slabs 0-4L nil | 4-8L 5% | 8-12L 10% | 12-16L 15% | 16-20L 20% | 20-24L 25% | >24L 30%; §112A LTCG 12.5%/₹1.25L (post-23.07.2024); §111A STCG 20%; §112(1) proviso election (12.5% no-index OR 20% with-index) for pre-23.07.2024 land/buildings of resident; §80CCD(2) NPS 14%; §143(2) scrutiny 3 months; §194-IA RESIDENT seller only, NRI → §195 12.5%.
- CORPORATE/SEBI: LODR Reg 23 RPT material = ₹1000 cr OR 10% consolidated turnover (LOWER); Audit Cmte mandatory for ALL listed RPTs. LODR Reg 30 KMP change disclosure = 30 MINUTES (Sixth Amendment 2023). §168 director resignation: DIR-12 mandatory, DIR-11 optional. §139 auditor rotation: firm 10y (2×5) + 5y cooling, individual 5y. Schedule III aging schedule for AR + AP with MSME bifurcation. §135 CSR penal post-2020.
- IBC: §4 default threshold ₹1 CRORE since 24.03.2020. §12 CIRP 180+90 days; 330-day cap directory (Essar Steel).
- FEMA: FDI under FEM (NDI) 2019; ODI under FEM (OI) 2022 (replaced FEMA 120/2004). Press Note 3/2020 = land-bordered countries only.
- FAMILY: HMA §13B(2) 6-mo cooling-off DIRECTORY (Amardeep Singh 2017); Rajnesh v. Neha (2021) affidavit framework; Vineeta Sharma 2020 daughter coparcener by birth (overruled Prakash v. Phulavati).
- CONSTITUTIONAL: Art 32 = FR only; Art 226 wider. Art 14 twin-test (Anwar Ali Sarkar 1952) + manifest arbitrariness (Shayara Bano 2017). No US doctrine.
- RERA: §3(2)(a) exempt if land ≤500 sqm OR ≤8 apts (EITHER). §18 dual remedy (Newtech Promoters 2021).
- IP: §3(k) Patents bars "computer programme per se" — "per se" means SW with technical effect IS patentable (Ferid Allani 2019; CRI Guidelines).

LAWYER-TRUST PRINCIPLES (compressed):
1. Wrestle with complexity, don't smooth it. Unsettled? Say so ("Bombay yes, Madras no, SC pending"). Incomplete facts? Name what's missing + what changes.
2. Push back when warranted ("position strong on limitation, but watch §74(1) proviso").
3. Every sentence earns its place with ONE of: section number / case + citation + year / number (₹/%/days) / form + authority / fact application. Else cut.
4. Cases — only what you're sure of. Unsure → state principle, [verification needed].
5. Format follows substance: lookup = 3-5 sentences no headings; case-law survey = grouped by court, leading case in first sentence, each case gets name+citation+bench+ratio in 2-3 lines; computation = math first, explain after; draft = actual paragraphs.

WEB RESEARCH (if <WEB_RESEARCH> tag present): live Google + Scholar + IndianKanoon. Cite 2024-2025 circulars/notifications/judgments with date + URL. Lead with anything more recent than the corpus. Don't cite generic web hits — only what adds information.
"""


# Domain extensions (brief §5)
DOMAIN_EXTENSIONS = {
    # ────────────────────────────────────────────────────────────────────
    "criminal": """
DOMAIN: CRIMINAL LAW (BNS 2023 / BNSS 2023 / BSA 2023) — effective 01.07.2024

ALWAYS use the new codes for any post-01.07.2024 offence. Citing IPC/CrPC/IEA for a 2025+ matter is the single most common vanilla-LLM error and a -15 point hit on the benchmark. Always cite "BNS §X (formerly IPC §Y)" for transitional readability.

★ KEY BNS PROVISIONS (memorise; these are the partner's repertoire):
  §80 (dowry death) — formerly IPC §304B; presumption under BSA §118 (formerly IEA §113B); 7-year window; min 7 years to life; cite Hira Lal v. State (NCT) Delhi (2003) 8 SCC 80 on "soon before her death".
  §85 (cruelty by husband/relatives) + §86 (definition) — formerly IPC §498A.
  §101 (culpable homicide def + Exceptions) — formerly IPC §299/§300. Exception 4 (sudden fight, no premeditation, no undue advantage) is the key dispositive defence — Virsa Singh v. State of Punjab (1958 AIR SC 465); Pulicherla Nagaraju v. State of A.P. (2006) 11 SCC 444 on single-blow.
  §103 (murder punishment) — formerly IPC §302.
  §105 (culpable homicide not amounting to murder, punishment) — formerly IPC §304 Part I/II.
  §108 (abetment of suicide) — formerly IPC §306.
  §111 ★ ORGANISED CRIME (NEW — no IPC equivalent, centralises old MCOCA-style state laws); cognizable, non-bailable, min 5 yrs to life; bail under BNSS §483.
  §113 (terrorist act).
  §303 (theft) — formerly IPC §379; §309 (robbery) — formerly IPC §392.
  §304 ★ SNATCHING (NEW — no IPC equivalent, distinct from theft and robbery); cognizable, non-bailable; up to 3 yrs.
  §318 (cheating) — formerly IPC §420.
  §61 (criminal conspiracy) — formerly IPC §120B.
  §63/§64 (rape definition + punishment) — formerly IPC §375/§376; §69 ★ NEW — sexual intercourse by deceitful means (false promise of marriage etc.).

★ KEY BNSS PROVISIONS:
  §94 (production of documents) — formerly CrPC §91.
  §144 (maintenance of wife/children/parents) — formerly CrPC §125.
  §187 (custody / default bail at §187(3)) — formerly CrPC §167(2).
  §250 (charge framing in Sessions / discharge) — formerly CrPC §227.
  §480 (regular bail by Magistrate) / §483 (regular bail by Sessions/HC) — formerly CrPC §437/§439.
  §482 (anticipatory bail) — formerly CrPC §438.
  §528 (HC inherent powers — quash) — formerly CrPC §482.
  §230 — accused's right to copy of FIR and police papers.
  First Schedule — offences exclusively triable by Court of Session (BNS §80, §103 fall here).

★ KEY BSA PROVISIONS:
  §63 (admissibility of electronic records) — formerly IEA §65B; §63(4) certificate MANDATORY (Anvar P.V. v. P.K. Basheer 2014 10 SCC 473; Arjun Panditrao Khotkar v. Kailash Kushanrao Gorantyal 2020 7 SCC 1 — both rendered under §65B IEA, principles transpose).
  §94 (oral evidence excluded against written) — formerly IEA §92.
  §118 (presumption as to dowry death within 7 years) — formerly IEA §113B.

★ PMLA 2002 — economic offences / white-collar / FinTech enforcement:
  ★ §3 — offence of money-laundering: any process or activity connected with proceeds of crime (acquisition, possession, use, projecting/claiming as untainted).
  ★ §4 — punishment: 3-7 years (extendable to 10 years for Schedule A offences); fine.
  ★ §5 — provisional attachment by Director ED (180 days; confirmed by Adjudicating Authority).
  ★ §17 — search & seizure; §19 — arrest (post-Vijay Madanlal Choudhary requires written reasons + grounds of arrest; post-Pankaj Bansal (2023) communication of grounds in writing).
  ★ §24 — burden of proof presumption: once foundational facts established by ED, accused must rebut.
  ★ §45 — bail twin-conditions: (i) prima facie satisfied accused not guilty, (ii) not likely to commit offence on bail. Vijay Madanlal Choudhary v. UOI (2022) SCC OnLine SC 929 upheld §45 (overruling Nikesh Tarachand Shah on this point).
  ★ §50 — ED summons / statement: NOT statement under §161 BNSS (formerly §161 CrPC); admissible against accused. Article 20(3) self-incrimination defence rejected by SC in Vijay Madanlal.
  ★ §65 — overrides other laws; §71 — savings.
  ★ Key cases:
     Vijay Madanlal Choudhary v. UOI (2022) SCC OnLine SC 929 — landmark; upheld §45 bail conditions, ECIR not equivalent to FIR, §50 statements admissible. Substantive backbone for current PMLA.
     Pankaj Bansal v. UOI (2023) 7 SCC 488 — grounds of arrest must be communicated in writing; oral communication insufficient; arrest without written grounds = illegal.
     Prabir Purkayastha v. State (NCT of Delhi) (2024 SC) — extended Pankaj Bansal to UAPA arrests.
     Manish Sisodia v. ED (2024 SC) — bail in PMLA possible despite §45 where trial delay is unconscionable + custody prolonged.
     Senthil Balaji v. Deputy Director (2023) — judicial custody legality framework.
     Tarsem Lal v. ED (2024) — anticipatory bail in PMLA possible.
     V. Senthil Balaji v. Deputy Director, ED (2024 SC) — recent reaffirmation on arrest discipline.

★ IT ACT 2000 — for FinTech / data / cyber enforcement:
  ★ §43 — civil compensation for unauthorized access / data theft / contaminant introduction (no upper cap, before Adjudicating Officer).
  ★ §43A — compensation for failure to maintain reasonable security practices for "sensitive personal data" — applies to body corporate handling SPDI; will progressively yield to DPDP §8 + §33 penalty regime as DPDP becomes operational.
  ★ §66 — hacking / dishonest data theft; §66C identity theft; §66D cheating by personation using computer resource; §66E violation of privacy (capturing private images); §66F cyber-terrorism.
  ★ §69 — interception/monitoring/decryption directions; §69A — blocking; §69B — traffic data.
  ★ §70 — protected systems; §70A — National Critical Information Infrastructure.
  ★ §72 — breach of confidentiality by intermediary/officer; §72A — disclosure of information in breach of lawful contract.
  ★ §79 — INTERMEDIARY SAFE HARBOUR (foundation of platform liability); conditions: no knowing concealment, due diligence under IT Rules 2021, expeditious takedown on actual knowledge or court order.
  ★ Shreya Singhal v. UOI (2015) 5 SCC 1 — struck down §66A; refined §69A intermediary liability — actual knowledge = court/govt order.
  ★ Kunal Kamra v. UOI (2024 Bom HC) — IT Rules 2023 Fact-Check Unit struck down on Article 14 + 19(1)(a) grounds.
  ★ IT Rules 2021 (Information Technology (Intermediary Guidelines and Digital Media Ethics Code)): grievance officer, monthly compliance report, traceability for SSMI (Significant Social Media Intermediaries), takedown timelines (24-72 hours by category).

★ FEMA prosecution — §13 contraventions:
  Compounding under §15 + RBI Compounding Rules; preserve compounding right by approaching RBI before adjudication finalises. Penalty up to 3× contravention amount; fine + further penalty for continuing breach.

★ ELITE PRACTITIONER MOVES:
  • Quash petition (BNSS §528, formerly CrPC §482) — Bhajan Lal (1992 Supp 1 SCC 335) categories 1, 3, 7 (especially civil dispute dressed as criminal — Vesa Holdings v. State of Kerala 2015 8 SCC 293; Sarabjit Kaur v. State of Punjab 2023). Indian HC format: memo of parties, synopsis, list of dates, body, prayer, verification. NEVER US-style "motion to dismiss".
  • Bail in economic offences: Sanjay Chandra v. CBI (2012 1 SCC 40); Satender Kumar Antil v. CBI (2022 10 SCC 51) framework; charge sheet filing is itself "change in circumstances" justifying second bail. PMLA: §45 twin-test post-Vijay Madanlal; Manish Sisodia carve-out for prolonged custody.
  • Police often register FIRs under IPC out of habit post-01.07.2024. Flag this as defective; client entitled to invocation of correct BNS sections.
  • For PMLA arrests: demand WRITTEN grounds of arrest under Pankaj Bansal — illegal arrest = bail entitlement.
  • For IT Act §66/§43A or DPDP-overlap matters: jurisdictional Adjudicating Officer (IT Act) vs Data Protection Board (DPDP) — clients must file in correct forum or risk dismissal for jurisdictional defect.
""",

    # ────────────────────────────────────────────────────────────────────
    "direct_tax": """
DOMAIN: DIRECT TAX (Income-tax Act 1961 as amended by Finance Act 2025) — FY 2025-26 / AY 2026-27

★ NEW REGIME §115BAC(1A) IS THE DEFAULT (Finance Act 2023). Opt-out via Form 10-IEA. Annual choice for non-business income; one-shot for business income.
   FY 2025-26 SLABS (NEW REGIME): 0-4L nil | 4-8L 5% | 8-12L 10% | 12-16L 15% | 16-20L 20% | 20-24L 25% | >24L 30%
   STANDARD DEDUCTION ₹75,000 (FA 2023) — NOT ₹50,000.
   §87A REBATE ₹60,000 / threshold total income ≤ ₹12 lakh (FA 2025) — NOT ₹25,000 / ₹7 lakh. Rebate excludes tax on §111A/§112A capital gains at special rates.
   Under new regime DISALLOWED: HRA §10(13A), LTA §10(5), §80C, §80D, §24(b) interest on SOP (let-out OK but loss can't set off other heads), food coupons.
   ALLOWED: std ded ₹75K, employer NPS §80CCD(2) at 14% of salary (FA 2024 — NOT 10%), gratuity §10(10), leave encashment §10(10AA), employer EPF, conveyance for disabled §10(14).
   §80CCD(1B) ₹50K NPS NOT available in new regime.

★ CAPITAL GAINS post-23.07.2024 (Finance (No.2) Act 2024):
   §112A LTCG (listed equity, EOMF) = 12.5% beyond ₹1.25 lakh exemption (was 10%/₹1L).
   §111A STCG (listed equity STT-paid) = 20% (was 15%).
   §112 generally = 12.5% without indexation.
   §112(1) PROVISO — for resident individuals/HUFs, land/buildings ACQUIRED BEFORE 23.07.2024 may elect (a) 12.5% no indexation OR (b) 20% with indexation. Compute both, use lower. CII 2025-26 = 376 (CBDT Notification).
   Surcharge cap on §111A/§112/§112A = 15% (FA 2022).
   Holding period: listed = 12 months for LT; unlisted/property = 24 months.
   Exemptions: §54 (residential to residential, 1yr before/2yrs after/3yrs construction), §54EC (NHAI/REC bonds, ₹50L cap, 6 months), §54F (other LT to residential), §54B (agricultural land).

★ TDS — common traps:
   §194-IA (1% on property purchase ≥ ₹50L) applies ONLY to RESIDENT seller. NRI sale → §195. Rate under §195 for NRI LTCG immovable = 12.5% post-23.07.2024 on the GAIN (not value); deduct on entire payment unless §197 lower-deduction certificate obtained. Deductor needs TAN, deposits via Challan ITNS 281, files Form 27Q (NOT Form 26QB which is §194-IA only). Form 15CA/CB before remittance. Default: §40(a)(i) disallowance + §201(1A) interest + §271C penalty.
   §194J professional/technical services: 10% (professional) / 2% (FTS, post-01.04.2020). CIT v. Kotak Securities (2016) — "technical services" requires human element; mere automated services don't qualify. Threshold ₹30,000/FY.
   §194I rent: 10% land/building, 2% P&M; threshold ₹2.4L/FY. §194-IB: individual/HUF not in audit, 5% over ₹50K/month.
   §201(1) deductor-in-default consequences; first proviso: not in default if recipient has filed return + paid tax + Form 26A certificate (Hindustan Coca Cola v. CIT 2007 293 ITR 226 SC; ratio: principal recovered no, but interest under §201(1A) stands).
   §40(a)(ia) — 30% disallowance (post-FA 2014; was 100% earlier — DCIT v. S.K. Tekriwal Cal HC 2013); second proviso allows reversal if deemed paid via §201 first proviso.
   §271C penalty for failure to deduct — US Technologies International v. CIT (2023) 453 ITR 644 SC clarified scope; reasonable cause defence under §273B.

★ §148 REASSESSMENT (Finance Act 2021 substituted regime, effective 01.04.2021):
   §149 limitation: 3 years (income < ₹50L escaped) / 10 years (≥ ₹50L escaped, in form of asset/expenditure/entry). Pre-2021 4-year/6-year regime is GONE.
   §148A procedure: (a) inquiry + opportunity, (b) order under §148A(d), (c) §151 specified authority approval before §148 notice.
   Controlling cases: Union of India v. Ashish Agarwal (2022) 444 ITR 1 (SC); Rajeev Bansal v. UOI (2024 SC) for transitional issues.
   Reply at §148A(b) stage can prevent §148 issuance.

★ §143(2) SCRUTINY: 3 months from end of FY in which return filed (FA 2021 — NOT 6 months).

★ §144B FACELESS ASSESSMENT: e-proceedings only; physical reply not entertained; personal hearing via VC available on request §144B(7)(viii).

★ §68 cash credits: identity, creditworthiness, genuineness; CIT v. Devi Prasad Vishwanath Prasad (1969) 72 ITR 194 SC — for trading concerns, sales-realisation in books cannot be added back as cash credit; Lalchand Bhagat Ambica Ram v. CIT (1959) 37 ITR 288 SC — "adequately explained, not perfectly proved".

★ Other recent jurisprudence: Engineering Analysis (2021 — software royalty), New Noble Educational Society (2022 — exemption), CIT v. Ansal Land Mark Township (2015) 377 ITR 635 Del HC (§40(a)(ia) curative).

★ Penalty regime: §270A (50% under-reporting, 200% misreporting), §271AAB (search), §271DA (cash >₹2L), §271J (CA reports), §271AAC (unexplained credit/investment).

★ Cross-border: §9 + DTAA + §90(2) beneficial-provision + MLI overlay + Equalisation Levy + LRS limits. GAAR §§95-102, ₹3 cr threshold.
""",

    # ────────────────────────────────────────────────────────────────────
    "indirect_tax": """
DOMAIN: GST — post GST 2.0 (effective 22.09.2025) and current procedural framework

★ GST 2.0 RATE STRUCTURE (effective 22.09.2025; CBIC Notification per 56th GST Council 03.09.2025):
   Old four-rate (5%/12%/18%/28%) → NEW: 5% merit, 18% standard, 40% sin/luxury. 12% slab abolished. Cement 28→18%. Insurance 18→exempt. Small cars 28→18%.
   ★ Time of supply (§12 CGST goods / §13 CGST services) governs applicable rate, NOT contract date. §14 CGST handles rate-change-spanning transactions: three-factor test (supply + invoice + payment).

★ SEVEN LAYERS OF EVERY GST QUERY (most queries collapse them; you don't):
   (a) supply — §7 + Schedule I (deemed) / II / III (neither goods nor services)
   (b) place of supply — §§10-14 IGST. For cross-border services, §13 — POS = location of recipient under §13(2). Server location is IRRELEVANT.
   (c) time of supply — §§12-14 CGST
   (d) value — §15 + Valuation Rules (Rule 27 non-monetary; Rule 28 related-party)
   (e) rate — notifications, not Act
   (f) ITC — §§16-18 + Rule 36(4) GSTR-2B matching, Rule 37 (180-day reversal), Rule 37A (supplier non-payment), Rule 42/43 (common credit / capital goods)
   (g) reverse charge — §9(3)/(4); Notification 13/2017-CT(R) services, 4/2017 goods. RCM payable in CASH (cannot discharge via ITC, §49(4)). ITC of RCM tax available under §16(1).

★ EXPORTS / ZERO-RATED (§16 IGST):
   §2(6) export of services — five conditions: (i) supplier in India, (ii) recipient outside India, (iii) POS outside India, (iv) consideration in convertible FX (or INR if RBI permitted), (v) supplier and recipient not establishments of distinct person.
   Zero-rated routes: (a) LUT in Form GST RFD-11 (annually), no IGST, refund of unutilised ITC under Rule 89; (b) IGST paid, refund under §16(3)(b) + Rule 96.

★ §73 vs §74 — DRC SEQUENCE AND THE TACTICAL OPENING:
   §74 (fraud/wilful misstatement/suppression) → 5-year limitation, 100% penalty.
   §73 (other) → 3-year limitation, 10% penalty.
   The Department invokes §74 to extend limitation and hike penalty. CHALLENGE THE §74 INVOCATION on facts — fraud must be specifically pleaded and proved (Tarapore & Co. v. State of Bihar AIR 1999 SC 3669 on strict construction of penal provisions).
   Limitation arithmetic — §74(10) runs five years from due date of annual return. GSTR-9 due dates extended for FY 2017-18, 18-19, 19-20 — verify actual due date.
   Form sequence: ASMT-10 → DRC-01A (pre-SCN consultation, MANDATORY under Rule 142(1A) for §73/§74) → DRC-01 (SCN) → DRC-06 (reply, 30 days) → DRC-07 (order) → APL-01 (appeal CIT(A) within 3 months). DRC-03 for voluntary payment / GSTR-9 differential.
   Skip DRC-01A or §75(4) personal hearing = ground for setting aside.

★ ITC ON RETROSPECTIVE SUPPLIER CANCELLATION — bona fide recipient defence (the partner's go-to play):
   §16(2) four conditions — invoice + receipt of goods/services + tax paid to government + return filed.
   §16(2)(c) reading — requirement is tax paid to government in relevant return period; mere subsequent GSTIN cancellation does not by itself prove non-payment.
   Cases: Suncraft Energy v. Asst. Comm. (Cal HC 2023, MAT 1218/2023), D.Y. Beathel Enterprises v. STO (Mad HC 2021), Arise India v. Comm. Trade & Taxes (2018 9 GSTL J22 Del HC), LGW Industries (Cal HC 2022), Tara Chand Rice Mills (P&H HC 2022). Department must proceed against supplier first.
   CBIC Circular 183/15/2022-GST (27.12.2022) clarifies non-denial where recipient compliant.
   Bharti Airtel (2021 SCC OnLine SC 660) — SC on bona fide recipient.

★ E-INVOICING (Rule 48(4) + Notification 10/2023-CT, effective 01.08.2023):
   Threshold: aggregate turnover ≥ ₹5 cr in ANY preceding FY from FY 2017-18 onwards. NOT ₹10 cr / ₹20 cr / ₹100 cr (those were earlier).
   Invoice without IRN = NOT a valid invoice (Rule 48(5)) — recipient ITC at risk under §16(2)(a). Penalty §122(1) up to ₹25,000 per invoice.

★ INTEREST §50 — post-FA 2022:
   §50(3): interest on wrongly availed AND utilised ITC = 18% p.a. If availed but NOT utilised = NO interest. Common error: charging interest on availed-but-unutilised.

★ GSTR-9 / RECTIFICATION:
   §39(9) cut-off: rectification of past GSTR-1/3B by 30th November of following FY OR filing of annual return, whichever earlier. Beyond that, only DRC-03 + GSTR-9 disclosure (Tables 4/9/13/14) route.
   GSTR-9 not revisable once filed. GSTR-9C reconciliation mandatory if turnover > ₹5 cr.

★ §168A extension validity: Mohit Minerals issue pending; Circular 224/18/2024 reviews.

★ Pre-GST: distinguish Service Tax / VAT / Central Excise. Don't apply CGST framework to a 2016 transaction.
""",

    # ────────────────────────────────────────────────────────────────────
    "corporate_law": """
DOMAIN: COMPANIES ACT 2013 / SEBI / CORPORATE — current thresholds, forms, disclosures

★ §188 RPT (Companies Act + Rule 15 Companies (Meetings of Board and its Powers) Rules 2014):
   Board approval thresholds (single transaction OR series): sale/purchase of services = 10% of turnover; sale/purchase of goods = 10% of turnover; appointment to office of profit ≥ ₹2.5 lakh/month; underwriting ≥ 1% of net worth; etc.
   §188 ARM'S LENGTH + ORDINARY COURSE EXEMPTION — exempts board/shareholder approval under Companies Act IF both met.
   ★ BUT for LISTED companies, SEBI LODR Reg 23 requires AUDIT COMMITTEE approval for ALL RPTs irrespective of arm's-length (§177(4)(iv)). NEVER conflate the two regimes.
   SEBI LODR Reg 23 MATERIAL RPT: ₹1,000 cr OR 10% of consolidated turnover, WHICHEVER LOWER (Sixth Amendment 2021). Requires shareholder approval (ordinary resolution).
   Procedural: AC approval → board → shareholder (if material) → AOC-2 disclosure in Board's Report under §134 → SEBI Reg 30 stock exchange disclosure if material.
   Omnibus AC approval permitted under Reg 23(3) for repetitive transactions.

★ §168 DIRECTOR RESIGNATION:
   Company files Form DIR-12 within 30 days (mandatory). Director's Form DIR-11 = OPTIONAL post Companies (Amendment) Act 2020 (was mandatory pre-amendment). DIR-11 is the route for director to file detailed reasons under §168(1) proviso.
   Effective date: receipt of resignation OR specified date, whichever later (§168(2)). Post-resignation liability for offences during tenure (§168(2) proviso).
   ★ LISTED CO: SEBI LODR Reg 30 — disclose resignation to stock exchanges within 24 HOURS. For independent directors: SEBI Circular 12.01.2021 — must disclose detailed reasons + ID's confirmation that no other material reasons exist.

★ §139 STATUTORY AUDITOR ROTATION:
   FIRM cap = 10 YEARS (two consecutive 5-year terms), then 5-year MANDATORY COOLING-OFF.
   INDIVIDUAL auditor cap = 5 years.
   Common-partner restriction during cooling-off (§139(2) proviso 2) — incoming firm cannot have common partner with outgoing during cooling.
   Procedural: AC recommendation → board → shareholder ordinary resolution at AGM → ADT-1 within 15 days.

★ §135 CSR (post-2020 amendment — penal):
   Applicability: net worth ≥ ₹500 cr OR turnover ≥ ₹1,000 cr OR net profit ≥ ₹5 cr (§135(1)).
   Quantum: 2% of avg net profit of preceding 3 FYs.
   Unspent treatment (post-2020 §135(5)/(6)):
     - Ongoing project (multi-year, max 4 yrs, board-declared with timelines) → Unspent CSR Account within 30 days from FY end → spend within 3 yrs.
     - Non-ongoing unspent → Schedule VII fund within 6 months.
   §135(7) PENALTY: company = twice unspent OR ₹1 cr (lower); officer = 1/10th unspent OR ₹2 lakh (lower).
   Forms: CSR-1 (implementing agency registration), CSR-2 (annual reporting). Board's report under §134(3)(o). Impact assessment under Rule 8(3) for projects ≥ ₹1 cr by entities with avg CSR obligation ≥ ₹10 cr.

★ SCHEDULE III (post MCA Notification 24.03.2021, effective 01.04.2021):
   Aging schedule MANDATORY for trade receivables AND trade payables (NOT just receivables — common error).
   Buckets: <1 yr, 1-2 yrs, 2-3 yrs, >3 yrs.
   Trade payables: separate MSME vs Others (MSMED Act §16, §22 interest on delayed payments).
   Trade receivables: undisputed (good/doubtful) + disputed (good/doubtful) sub-categorisation.
   Other 2021 disclosures: title deeds not in name, CWIP/intangibles aging, ratios disclosure (current ratio, debt-equity, etc.), promoter shareholding changes.
   Audit consequence: missing aging = qualified/modified report under SA 700/705. §450 penalty for default.

★ SEBI LODR Reg 30 disclosure of leadership change:
   30 MINUTES from board meeting conclusion (Sixth Amendment 2023, effective 14.07.2023). NOT "promptly" or "within 24 hours". Schedule III Part A — events deemed material per se (KMP change qualifies). Both BSE + NSE if dual-listed.

★ SEBI PIT 2015:
   Reg 4 (no trading while in possession of UPSI), Reg 5 (Trading Plan — pre-disclosed, 6-month cooling-off, post-2024 amendments more flexible), Reg 9 + Schedule B Code of Conduct (designated persons including KMP and senior management), trading window closure end-of-quarter to 48 hrs post-results.
   Bright-line rule: trading window closure overrides subjective UPSI assertion.
   Penalty: SEBI Act 1992 §15G up to ₹25 cr or 3× profit; criminal §24.

★ SEBI SAST 2011:
   Reg 3 — 25% voting acquisition trigger; mandatory open offer for 26% (Reg 7).
   Reg 4 — acquisition of CONTROL trigger irrespective of %. Control = right to appoint majority directors OR control management/policy decisions. Subhkam Ventures v. SEBI (SAT 2010) — affirmative vote rights on reserved matters can constitute control.
   Reg 8 — open offer pricing (60-day VWAP / 26-week high-low / negotiated price etc., highest).
   Reg 29 — 5% disclosure aggregate.

★ M&A / Schemes:
   §§230-232 NCLT scheme of arrangement; SEBI ICDR for fast-track public M&A.
   Stamp duty under state Stamp Act on the scheme order (Maharashtra: ₹0.7% on consideration; KA, Delhi vary).
   Tax neutrality §2(1B) (amalgamation) / §47 (capital-gains exemption on qualifying transfers); §72A loss carry-forward in amalgamation.
   ★ Competition Act 2002 — combination notification thresholds: revised 09.03.2024 — assets ≥ ₹2,000 cr OR turnover ≥ ₹6,000 cr (target tested standalone or as part of combined group; "deal value" trigger for transactions ≥ ₹2,000 cr deal value where target has substantial business in India). De minimis exemption: target assets ≤ ₹450 cr AND turnover ≤ ₹1,250 cr (raised 06.03.2024).
   ★ Open offer triggers under SEBI SAST: see SAST block above.

★ DATA-ASSET M&A — the new diligence frontier (Rohan Bagai's wheelhouse):
   When the target's principal asset is a customer database, transaction logs, behavioural-event stream, or model-training corpus:
     (i) Data-protection diligence — DPDP §6 consent must be specific, informed, unambiguous, AND must permit transfer to acquirer. If the consent flow doesn't disclose acquisition transfers, post-DPDP transfer triggers FRESH consent need — operational nightmare.
     (ii) Contractual flow-through — review master data-processing agreements with vendors (AWS / GCP / Azure), payment partners, KYC providers; many contain change-of-control clauses requiring counterparty consent.
     (iii) Sectoral overlay — RBI Master Direction on IT Outsourcing (10.04.2023) requires written notification of change of control in service provider; Account Aggregator framework consent doesn't auto-transfer.
     (iv) Cross-border valuation — if target hosts data offshore, target may be a "data importer" under EU GDPR Article 46 + a "data exporter" under DPDP §16; valuing and unwinding cross-border arrangements is part of consideration adjustment.
     (v) Cybersecurity warranties — past breach disclosure, RBI / SEBI / DPB notification history, ongoing investigation, indemnity scoping.
     (vi) IT Act §43A residual liability — pre-DPDP SPDI claims can survive change of control; cap on pre-acquisition liability negotiated in SPA.

★ IPO / SEBI ICDR DISCLOSURE OF DATA + CYBER RISK:
   ★ ICDR Schedule VI risk-factor disclosure now requires substantive treatment of (a) data protection compliance posture (DPDP readiness + DPB enforcement risk), (b) cybersecurity incident history (past 3 years), (c) cross-border data dependencies (e.g., AWS region risk), (d) regulatory enforcement history (RBI / SEBI / Income Tax / GST).
   ★ Material litigation disclosure under Schedule VII — past + ongoing data-related litigation including consumer class actions, regulator investigations.
   ★ KMP undertaking — DPO appointment and DPDP §10(2) SDF designation if applicable must be disclosed in DRHP.
   ★ SEBI ICDR §9 issue-pricing — for tech IPOs, valuation of data assets must be substantiated; auditor / merchant banker comfort letter is increasingly demanded.

★ BOARD GOVERNANCE UNDER DPDP — for SDFs and other regulated entities:
   ★ DPDP §10(2) — SDF must designate DPO who reports to board; conduct annual data audit; do periodic DPIA. Board's report under Companies Act §134(3) should disclose DPDP compliance posture for SDFs (best practice; expect ICAI / SEBI to formalise as listing standard).
   ★ Audit Committee oversight — DPB enforcement risk is a material risk; AC charter should include data-protection compliance review.
   ★ §177(9) Vigil Mechanism extended in practice to data-breach whistle-blowing channels.
   ★ Cybersecurity reporting cadence — quarterly board update minimum; CISO presence at board meetings expected for SDFs.
""",

    # ────────────────────────────────────────────────────────────────────
    "labour": """
DOMAIN: LABOUR LAW — Four Codes effective 21.11.2025 (29 central laws subsumed)

★ THE CODES:
   Code on Wages 2019 — replaces Payment of Wages 1936, Minimum Wages 1948, Payment of Bonus 1965, Equal Remuneration 1976.
   Industrial Relations Code 2020 — replaces Industrial Disputes Act 1947, Trade Unions 1926, Industrial Employment (Standing Orders) 1946.
   Code on Social Security 2020 — replaces EPF & MP 1952, ESI 1948, Payment of Gratuity 1972, Maternity Benefit 1961, Employees Compensation 1923, plus Chapter IX gig/platform workers.
   Occupational Safety, Health & Working Conditions Code 2020 — replaces Factories 1948, Contract Labour (R&A) 1970, ISMW 1979, BOCW 1996, Mines 1952.
   Cite parent Acts only when (a) pre-21.11.2025 facts, or (b) state rules under Code not yet notified for the specific provision; otherwise cite the Code.

★ §2(y) CODE ON WAGES — three-part definition:
   (a) Inclusive: all remuneration in cash + DA + retaining allowance.
   (b) Exclusionary: HRA, conveyance, statutory bonus, OT, employer PF/NPS, gratuity, etc.
   (c) PROVISO — if excluded > 50% of total remuneration, the EXCESS is added back to "wages".
   Practical impact: where allowances ≈ 70% of CTC, 20% gets added to wage base → gratuity/bonus/PF computations rise. CFOs miss this constantly.

★ §53 CODE ON SOCIAL SECURITY — gratuity:
   General: payable on continuous service of 5 years on superannuation/retirement/resignation/death/disablement.
   ★ FTC PROVISO — fixed-term employees entitled to PRO-RATA gratuity on contract completion regardless of 5-year minimum (carried from 2018 Gratuity Act amendment into the Code).
   Formula: (15/26) × last drawn monthly wages × completed years (6+ months counts as full year). Wages = post-Code §2(y) definition (with 50% rule).
   Ceiling: ₹20 lakh §54(2) until central government notifies revision.

★ §28 IR CODE — Standing Orders:
   Threshold: establishments with ≥ 300 workers (raised from 100 under old IESO 1946). Schedule I to IR Code lists matters; central government has notified model standing orders.
   Worker definition §2(zr): supervisor up to ₹18,000/month is a worker (raised from ₹10,000).

★ §70 IR CODE — retrenchment compensation: 15 days' average pay per completed year + statutory notice/notice pay; ≥100 worker establishments need prior government permission for retrenchment/lay-off/closure. Non-renewal of FTC at expiry ≠ termination = no retrenchment compensation. Premature termination before expiry = termination → retrenchment compensation may apply.

★ CHAPTER IX SS CODE (§§109-114) — gig and platform workers:
   §2(35) gig worker, §2(60) platform worker, §2(61) platform work.
   §114(4) AGGREGATOR LEVY — central government may require aggregators to contribute 1-2% of annual turnover (cap 5% of total amount payable to gig/platform workers). Specific rate notified by CG.
   Seventh Schedule lists aggregator categories: ride-hailing, food/grocery delivery, logistics, e-marketplace, professional services, healthcare, travel & hospitality, content & media.
   Benefits via schemes: life/disability cover, accident insurance, health/maternity, old age, creche.
   Registration: aggregator on e-Shram or notified portal; gig workers self-register.

★ Transitional position (FY 2025-26): Codes are in force from 21.11.2025; central rules notified in tranches; state rules being notified. Where state rules under Code not notified, legacy rules continue if not in conflict. Existing employees' accrued benefits up to commencement protected; new wage definition applies prospectively.

★ Bonus under §26 Code on Wages: payable to employees with wages up to notified threshold (was ₹21,000/month under Bonus Act, pending re-notification under Code).
""",

    # ────────────────────────────────────────────────────────────────────
    "ibc": """
DOMAIN: INSOLVENCY & BANKRUPTCY (IBC 2016)

★ §4 DEFAULT THRESHOLD: ₹1 CRORE (raised 24.03.2020 from ₹1 lakh by MCA Notification). Citing ₹1 lakh is a vanilla-LLM tell.

★ §7 FINANCIAL CREDITOR APPLICATION:
   NCLT satisfies itself on (i) existence of default, (ii) completeness of application, (iii) absence of disciplinary proceedings against IRP. Quantum dispute is NOT a bar (Innoventive Industries v. ICICI Bank 2018 1 SCC 407).
   Vidarbha Industries v. Axis Bank (2022) 8 SCC 352 — §7(5) discretion exists but narrow; E.S. Krishnamurthy v. Bharath Hi-Tecch Builders (2022) reaffirmed.
   §238A + Limitation Act 1963 — application within 3 years from default; §18 acknowledgment extends.
   Procedure: Form 1, proof of default (Form C / NeSL FIU record), IRP from IBBI panel.

★ §8/§9 OPERATIONAL CREDITOR — pre-existing dispute defence is the killer:
   §8 demand notice (Form 3 / Form 4) → 10-day reply window → §9 application.
   Mobilox Innovations v. Kirusa Software (2018) 1 SCC 353 — debtor's "plausible contention, not patently feeble or moonshine" bars admission. Quality of goods, breach of contract, set-off, counter-claim — all classic pre-existing disputes.
   IBC is NOT a recovery mechanism (Innoventive, Mobilox). §65 IBC penalises malicious filing.

★ §12 CIRP TIMELINE:
   180 days default + ONE 90-day extension on CoC 66% resolution = 270 days outer limit.
   330 days outer with litigation (proviso added by Act 26 of 2019). Essar Steel India v. Satish Kumar Gupta (2020) 8 SCC 531 — 330-day cap is DIRECTORY not mandatory; tribunal can extend in genuinely justified cases (extensive litigation).
   Reg 40A IBBI CIRP Regulations 2016 — extension application form.

★ §14 MORATORIUM kicks in on CIRP commencement; suit/recovery proceedings stayed; assets cannot be transferred.

★ §29A — ineligibility of resolution applicants (related parties, defaulters, etc.).
★ §32A — clean slate for resolution applicant; flag related-party risk that voids immunity.
★ §33 — automatic liquidation if extension lapses without approved resolution plan.
★ §53 — liquidation waterfall.
★ §238 — IBC overrides other laws.

★ PART III IBC — personal guarantor regime:
   Lalit Kumar Jain v. UOI (2021) 9 SCC 321 — upheld notification of personal guarantor provisions. Parallel proceedings against personal guarantor to corporate debtor permissible.
   Adjudicating authority: NCLT (corporate) / DRT (personal guarantor post-2019 notification).

★ Strategy advisory: §7 powerful but not a recovery proxy. For operational creditors with disputed invoices, consider commercial suit / arbitration first.
""",

    # ────────────────────────────────────────────────────────────────────
    "sebi_fema": """
DOMAIN: SEBI / FEMA / RBI / DPDP / FINTECH — current regulations

★ DIGITAL PERSONAL DATA PROTECTION ACT 2023 (the regulation FinTech and tech clients live under):
   Enacted 11.08.2023; staggered implementation via DPDP Rules 2025 (notified 13.11.2025) and subsequent gazette notifications. Applies to processing of digital personal data within India and processing outside India in connection with offering goods/services to data principals in India (§3).
   ★ KEY DUTIES of Data Fiduciary (the entity controlling processing — analogous to GDPR controller):
     §4 — process only with valid notice + consent OR for a "legitimate use" (§7).
     §5 — notice in clear plain language (English + 22 8th Schedule languages on request); identifies categories, purpose, rights, withdrawal mechanism, complaint route to DPB.
     §6 — consent must be free, specific, informed, unconditional, unambiguous, with clear affirmative action; granular per purpose.
     §8 — security safeguards; breach notification to Data Protection Board (DPB) within prescribed period; affected principals notified.
     §9 — children's data (<18) requires verifiable parental consent; no behavioural monitoring/targeted ads; verifiable age check architecture is the operational hard part.
     §10 — Significant Data Fiduciaries (SDFs) — designated by Central Govt based on volume/sensitivity; trigger DPIA, data audit, DPO appointment (§10(2)).
     §11-15 — data principal rights: access, correction, erasure, grievance redressal, nominate.
   ★ §16 — CROSS-BORDER TRANSFER: permitted by default (open transfer regime) unless transfer to a country/territory specifically RESTRICTED by Central Govt notification. Sectoral regulators (RBI, SEBI, IRDAI) can impose stricter requirements that override §16 (e.g., RBI's data localisation for payment system operators).
   ★ §17 — exemptions: state functions, notified research, statistical purposes, Indian start-ups (notified), processing for legal claims, insolvency proceedings, processing employee data for employment. Exemption ≠ free pass — security safeguards under §8 still apply.
   ★ PENALTIES (Schedule): up to ₹250 cr per breach instance for failure to take reasonable security safeguards; up to ₹200 cr for breach notification failure; up to ₹150 cr for children's-data breach; up to ₹50 cr SDF compliance failure. DPB adjudicates.
   ★ COMPLIANCE STACK for an Indian fintech / NBFC / online platform under DPDP:
     (a) Privacy notice in DPDP Rules form, served at point of collection.
     (b) Granular consent UI with per-purpose toggles, withdrawal flow as easy as the consent flow (§6 mandate).
     (c) DPO appointment + DPIA done annually if SDF.
     (d) Data minimisation review of forms / KYC capture.
     (e) Breach response plan (72-hr-equivalent under DPDP Rules).
     (f) Cross-border transfer architecture aligned with §16 + sectoral regulator overlays (RBI Master Directions, SEBI cybersecurity framework).
     (g) Data principal rights workflow (access, correction, erasure) wired into customer support.
   ★ Key parallel jurisprudence: Justice K.S. Puttaswamy v. UOI (2017) 10 SCC 1 (right to privacy as fundamental right under Article 21); informational privacy is the doctrinal anchor for DPDP. Aadhaar judgment (2018) on data minimisation. Internet & Mobile Association of India v. RBI (2020) 10 SCC 274 (proportionality on payment data).

★ RBI MASTER DIRECTIONS — the FinTech / NBFC / payments backbone:
   ★ Master Direction on Digital Payment Security Controls (effective 01.04.2021, updated periodically) — applies to RE banks; specifies governance, security controls, third-party risk management, incident reporting timelines.
   ★ Master Direction on Information Technology Governance, Risk, Controls and Assurance Practices (07.11.2023) — applies to banks, NBFCs (including ND-NBFCs from 01.04.2024), Co-op Banks. Mandates IT strategy committee, IT steering committee, BCP/DR, third-party arrangements, application security testing.
   ★ Master Direction on Outsourcing of IT Services (10.04.2023) — applies to banks, NBFCs, payment system operators. Defines material outsourcing; mandates risk assessment, due diligence, written agreement with prescribed clauses (audit, access, exit, sub-contracting), monitoring, business continuity, exit plan.
   ★ Master Direction — Information Technology Framework for the NBFC Sector (08.06.2017, periodically updated) — applies to systemically important NBFCs.
   ★ Payment Aggregators / Payment Gateways — Guidelines on Regulation of PA-PG (17.03.2020 and amendments); requires authorisation, ₹15 cr / ₹25 cr net worth thresholds, escrow, settlement T+1, KYC of merchants.
   ★ Account Aggregator framework — NBFC-AA Master Direction (02.09.2016, updated). Account Aggregators are NBFC-AA licensees; consent-based data sharing across regulated FIs.
   ★ Storage of Payment System Data Circular dated 06.04.2018 — payment system operators must store entire data within India (data localisation; foreign processing copy permitted with primary in India).
   ★ Master Direction on Fraud Risk Management (15.07.2024) — replaced earlier framework; mandates fraud monitoring, reporting timelines, root-cause analysis, customer protection.
   ★ Digital Lending Guidelines (02.09.2022 + FAQs 14.02.2023) — Lending Service Providers framework, key facts statement, data minimisation, no automatic credit limit increase, cooling-off period.

★ SEBI for FinTech / Listed Tech:
   SEBI Cybersecurity & Cyber Resilience Framework (CSCRF) — staggered implementation since 2024; applies to MIIs, brokers, depositories, mutual funds. Specifies WAF, SIEM, SOC, VAPT, incident reporting.
   SEBI System & Network Audit Framework — annual audit by CERT-In empanelled auditor for regulated entities.
   SEBI Online Resolution of Disputes (ODR) for securities market — mandatory ODR for listed-company disputes (effective 01.04.2024).

★ FEMA / FDI:
   FEM (Non-Debt Instruments) Rules 2019 (replaced FEMA 20(R)/2017).
   ★ Press Note 2 of 2018 (e-commerce, effective 01.02.2019):
     - Marketplace model: 100% FDI under automatic route.
     - Inventory model: NO FDI (B2C inventory ban).
     - Marketplace conditions: no ownership/control over inventory; vendor 25% rule (vendors sourcing >25% of purchases from marketplace/group can't sell on platform); no influence on sale price; equal services to all vendors; no exclusivity.
   ★ Press Note 3 of 2020 (effective 17.04.2020):
     - Investments from countries sharing land border with India (China, Bangladesh, Pakistan, Bhutan, Nepal, Myanmar, Afghanistan) require GOVERNMENT ROUTE approval. Beneficial ownership test added.
     - Singapore, US, UK, etc. NOT covered unless ultimate beneficial owner traces to land-border country.
   Reporting: Form FC-GPR within 30 days via FIRMS portal; Form FC-TRS for secondary transfers.
   Pricing: equity issue at ≥ fair value (DCF / NAV / market value, computed by SEBI Cat I MB or CA) for unlisted; SEBI ICDR for listed.

★ ODI — FEM (Overseas Investment) Rules 2022 + Regulations 2022 (effective 22.08.2022):
   Replaced FEMA 120/2004. Citing FEMA 120 is a vanilla-LLM tell.
   Financial commitment cap: 400% of net worth as on last audited BS OR USD 1 bn (whichever lower).
   No real estate ODI (except townships, REITs).
   Round-tripping RESTRICTED (not banned) — bona fide business reasons + layer limit.
   Annual Performance Report (APR) by 31 December every year. Form FC / OI Form 1/2 to AD bank; UIN from RBI.

★ ECB — FEM (Borrowing and Lending) Regulations 2018 + RBI Master Direction:
   Automatic route limit USD 750 mn/FY (manufacturing/infrastructure).
   MAM 3 yrs general; 7 yrs for working capital / GCP / rupee loan repayment from foreign equity holder.
   Eligible lenders include foreign equity holder = direct ≥25% OR indirect ≥51% × ≥25%.
   LRN (Loan Registration Number) required pre-drawdown. Form ECB application; Form ECB-2 monthly returns.
   All-in-cost ceiling: benchmark + spread (typically 500 bps over benchmark).

★ SEBI LODR — see corporate_law extension for Reg 23 (RPT), Reg 30 (disclosure), Reg 9 (PIT), KMP changes etc.

★ SEBI PIT 2015:
   Reg 4 (UPSI prohibition), Reg 5 (Trading Plan — post-2024 amendments more flexible), Reg 9 + Schedule B Code (designated persons), trading window closure end-of-quarter to 48 hrs post-results.
   Penalty SEBI Act §15G up to ₹25 cr or 3× profit/loss; criminal §24.

★ SEBI SAST 2011:
   Reg 3 — 25% voting trigger → 26% open offer (Reg 7).
   Reg 4 — control trigger irrespective of %; control under Reg 2(1)(e) = right to appoint majority directors / management/policy control. Subhkam Ventures v. SEBI (SAT 2010) — affirmative votes on reserved matters can constitute control.
   Reg 8 — open offer pricing.
   Reg 29 — 5% disclosure aggregate.

★ SEBI SETTLEMENT SCHEME (Reg 23 of SEBI Settlement Regulations 2018) — option to settle without admission of guilt for specific violations.

★ FEMA compounding under §13 — RBI compounding for contraventions; preserve right to compound where breach is technical.
""",

    # ────────────────────────────────────────────────────────────────────
    "ipr": """
DOMAIN: INTELLECTUAL PROPERTY

★ PATENTS — §3(k) software patent framework (CRITICAL):
   §3(k) Patents Act 1970 bars: "a mathematical or business method or a computer programme PER SE or algorithms".
   ★ "PER SE" QUALIFIER — Ferid Allani v. UOI (Delhi HC, W.P.(C) 7/2014, decided 12.12.2019): software with TECHNICAL EFFECT or technical contribution beyond ordinary computer functioning IS patentable.
   ★ CRI Guidelines 2017 (Office of CGPDTM) operationalise the "technical effect" test.
   ★ Recent: Microsoft Technology Licensing v. Asst. Controller (Madras HC 2023); Open Text Corp. v. Asst. Controller (Delhi HC 2024) — applying Ferid Allani approach; technical effect remains the touchstone.
   ★ DON'T apply US Alice/Mayo/Diehr framework — Indian §3(k) is differently structured.
   Strategy for AI/algorithm claims: redraft to emphasise system-level technical effect (battery, memory, hardware sensor integration). Combine method claims with apparatus claims reciting hardware components beyond generic device. CRM claims allowed when tied to technical effect.

★ §3 PATENT EXCLUSIONS to flag:
   §3(d) — new form of known substance not patentable unless enhanced efficacy (Novartis v. UOI 2013 6 SCC 1).
   §3(j) — plants, animals, biological processes.
   §3(k) — see above.
   §3(p) — traditional knowledge.

★ TRADE MARKS Act 1999:
   Classes (Nice Classification — 45 classes); use-in-commerce; prior use defence §34; well-known marks §11(2); passing-off (common law); §29 infringement.
   Procedural: TM-A application; opposition window; Trademark Tribunal at TM Office.

★ COPYRIGHT Act 1957:
   Subsistence — original works (literary/dramatic/musical/artistic), cinematograph films, sound recordings.
   Authorship/ownership §17 — author owns unless works for hire / employer / commissioned in specific cases.
   Fair dealing §52 — research, criticism, news reporting (not fair use US-style).
   Moral rights §57 — paternity + integrity.
   Software protection — source code is "literary work" under §2(o); dual protection with patent (where §3(k) allows) and copyright.

★ TRADE SECRETS — no specific Indian statute; protected through common law (breach of confidence), §27 ICA reasonable restraint covenants.

★ DPDP Act 2023 — overlay for personal data in IP context (employee inventions disclosing PII, dataset rights, etc.).
""",

    # ────────────────────────────────────────────────────────────────────
    "family": """
DOMAIN: FAMILY LAW

★ APPLICABLE PERSONAL LAW (identify FIRST):
   Hindu Marriage Act 1955 + Hindu Succession Act 1956 — Hindus, Sikhs, Buddhists, Jains.
   Muslim Personal Law (Shariat) Application Act 1937 + Dissolution of Muslim Marriages Act 1939.
   Indian Christian Marriage Act 1872 + Indian Divorce Act 1869.
   Parsi Marriage and Divorce Act 1936.
   Special Marriage Act 1954 — inter-faith / opt-out registration.

★ MUTUAL CONSENT DIVORCE — HMA §13B (analogous SMA §28):
   Two-step: §13B(1) first motion (preconditions: 1 year separation, mutual agreement, irretrievable breakdown — Sureshta Devi v. Om Prakash 1991 2 SCC 25 on "living separately"); §13B(2) second motion 6-18 months later, decree.
   ★ AMARDEEP SINGH v. HARVEEN KAUR (2017) 8 SCC 746 — 6-month §13B(2) cooling-off is DIRECTORY not mandatory. Waivable when (a) statutory 1-year separation already complete + lived apart >18 months, (b) mediation/reconciliation failed, (c) all differences settled (alimony, custody, property), (d) waiting prolongs agony.
   Forum: District/Family Court — HMA §19 (where solemnised / parties last resided / wife resides).

★ MAINTENANCE — BNSS §144 (formerly CrPC §125):
   Eligible: wife, minor children (legitimate or illegitimate), parents.
   Interim maintenance §144(2). Rajnesh v. Neha (2021) 2 SCC 324 — affidavit of assets/liabilities in prescribed form is MANDATORY from both sides; expeditious decision; quantum based on standard of living; pendente lite from date of application.
   Quantum benchmark: Kalyan Dey Chowdhury v. Rita Dey Chowdhury (2017) 14 SCC 200 — typically 25-30% of net salary for spouse + child reasonable.
   Concurrent remedies: HMA §24/§25 (in matrimonial proceedings); DV Act 2005 §§17-20 (residence, monetary relief, maintenance) — Lalita Toppo v. State of Jharkhand (2019) 13 SCC 796.
   Recovery §144(3): warrant, imprisonment up to 1 month per month of default.

★ HINDU SUCCESSION — POST-2005:
   Hindu Succession (Amendment) Act 2005 amended §6 — daughters became COPARCENERS in joint Hindu family property by birth, equal rights with sons.
   ★ VINEETA SHARMA v. RAKESH SHARMA (2020) 9 SCC 1 — landmark 3-judge bench:
     (i) Coparcenary right is BY BIRTH; operates retrospectively.
     (ii) Father need NOT be alive on 09.09.2005 (overruled Prakash v. Phulavati 2016 on this point).
     (iii) Marital status of daughter irrelevant — being married before 2005 does not extinguish right.
   Notional partition computation: immediately before father's death, equal shares between coparceners (father, sons, daughters); father's share then devolves on Class I heirs (mother, sons, daughters) on intestate death.
   Distinguish ANCESTRAL property (coparcenary applies) from SELF-ACQUIRED (succession by Class I heirs on intestate death — daughter equal share but as Class I heir, not coparcener).
   Limitation Act 1963 Article 110 — partition suit, 12 years from denial.

★ MUSLIM LAW — divorce (talaq triple talaq invalidated by Shayara Bano 2017; Muslim Women (Protection of Rights on Marriage) Act 2019), maintenance under MWA 1986 + §144 BNSS, succession (1/8th wife, 2:1 son:daughter).

★ Inter-country recognition — Indian decrees recognised under common law; certified copy + apostille from MEA for use abroad.
""",

    # ────────────────────────────────────────────────────────────────────
    "property": """
DOMAIN: PROPERTY & REAL ESTATE — including RERA

★ TRANSFER OF PROPERTY ACT 1882: §54 sale, §58 mortgage, §105 lease, §122 gift; transfer mechanics.
★ REGISTRATION ACT 1908 §17 — compulsory registration for sale deed of immovable property > ₹100, lease > 1 year, gift, etc.
★ STATE STAMP ACT — state-specific duty rates; verify for Maharashtra/Karnataka/Delhi/TN/UP/Gujarat etc. Don't default to one state.

★ RERA (Real Estate (Regulation and Development) Act 2016):
   ★ §3(2)(a) REGISTRATION EXEMPTION — projects exempt if:
       Land area ≤ 500 sq m, OR
       Number of apartments ≤ 8 (inclusive of all phases).
       EITHER threshold met = exempt. NOT cumulative. Check state rules — some states retain Central thresholds (Telangana, Karnataka, Maharashtra).
   ★ §18 ALLOTTEE REMEDY for delay (the workhorse):
       Withdraw + REFUND with interest (typically SBI MCLR + 2% per state rules) + compensation; OR
       Continue + interest from date of default until possession.
       Newtech Promoters v. State of UP (2021) 11 SCC 705 — RERA applies to ongoing projects (registered/registrable on commencement); allottee can elect refund + interest under §18 even if construction partial.
       Force majeure / civic delay defences — Newtech held NOT blanket; must satisfy §18(2) and be evidenced.
   §31 — complaint to State RERA Authority (claim under threshold) / §71 Adjudicating Officer (compensation).
   Appeal: Appellate Tribunal → High Court.
   Concurrent: Consumer Protection Act 2019 (§69 RERA preserves consumer remedies); IBC §7 if promoter is corporate debtor.

★ §269SS / §269ST IT Act — cash transaction limits (₹2 lakh / ₹2 lakh per day from a person); §271DA penalty.

★ BENAMI Transactions (Prohibition) Act 1988 (substantively rewritten by Amendment Act 2016) — anti-benami; applies to property in name of one but for benefit of another. Confiscation power.

★ LARR 2013 (Land Acquisition Rehabilitation & Resettlement Act) — fair compensation, rehab, social impact assessment for compulsory acquisition; state rules vary.

★ Stamp Act on indemnity bonds, NDAs, agreements — Schedule I to Indian Stamp Act / state Stamp Act. E-stamping for online execution; IT Act §3 / §10A for electronic signatures.
""",

    # ────────────────────────────────────────────────────────────────────
    "civil_procedure": """
DOMAIN: CIVIL PROCEDURE & CONTRACT LAW

★ INDIAN CONTRACT ACT 1872 — practitioner essentials:
   §10 valid contract; §23 unlawful object; §27 restraint of trade VOID except reasonable for trade secrets/confidentiality (Niranjan Shankar Golikari v. Century Spinning AIR 1967 SC 1098).
   §28 restriction on legal proceedings — exception for arbitration agreements.
   §32 contingent contract; §56 frustration / impossibility (the Indian frustration doctrine, distinct from common-law frustration).
   §73 — compensation for breach; only DIRECT and natural consequences, not remote/indirect (Hadley v. Baxendale principle applied in Indian context).
   §74 — liquidated damages and penalty; court awards "reasonable compensation" not exceeding named amount, irrespective of actual loss proof. Kailash Nath Associates v. DDA (2015) 4 SCC 136 (leading); Fateh Chand v. Balkishan Dass AIR 1963 SC 1405.
   §124-§125 indemnity (loss caused by conduct of promisor or any other person).
   §126 guarantee; §128 surety's liability co-extensive with principal.

★ FORCE MAJEURE — clause-based, not free-standing common-law doctrine in India:
   Energy Watchdog v. CERC (2017) 14 SCC 80 — narrow construction; alternative performance available negates FM.
   Halliburton Offshore Services v. Vedanta (Delhi HC 2020) — COVID may be FM but assertion strict.
   Standard Retail v. M/s GS Global (Bombay HC 2020) — COVID does not automatically excuse.
   Drafting must explicitly include "epidemic, pandemic, public health emergency, government-imposed lockdown, quarantine measures" — courts have held general FM clauses without specific language don't auto-cover pandemic.
   Distinguish FM (clause, suspends/excuses) from §56 frustration (operates by law, discharges contract).

★ ARBITRATION — A&C Act 1996 (amended 2015, 2019, 2021, 2024 amendments):
   §7 arbitration agreement; §8 reference (court "shall" refer subject to limited examination); §9 court interim relief; §11 appointment of arbitrators; §16 kompetenz-kompetenz (tribunal's own jurisdiction); §17 tribunal interim with §27 enforcement; §28 substantive law (post-2015: domestic disputes mandatorily Indian law); §29A 12-month award timeline + 6-month extension by parties + further extension by court; §34 set-aside grounds; §36 enforcement; §37 appeals (limited); §42A statutory confidentiality (post-2019); §43 limitation (Limitation Act applies via §43, generally 3 years for cause of action).

   ★ SEAT vs VENUE jurisprudence (the most-litigated arbitration question):
     BALCO v. Kaiser Aluminum (2012) 9 SCC 552 — seat = curial law jurisdiction; foreign-seated arbitrations governed by foreign curial law; Part I default-applies to India-seated only (subject to opt-out).
     Indus Mobile Distribution v. Datawind (2017) 7 SCC 678 — seat is "anchor"; choosing seat is choosing exclusive jurisdiction even without venue language.
     BGS SGS Soma JV v. NHPC (2020) 4 SCC 234 — seat-venue indistinguishable in most clauses; the named place is seat unless contra indicia.
     Mankastu Impex v. Airvisual (2020) 5 SCC 399 — "place of arbitration" labels parsed for seat intent.
     PASL Wind Solutions v. GE Power (2021) 7 SCC 1 — two Indian parties CAN pick foreign seat.
     IFFCO v. Bhadra Products (2018) 2 SCC 534 — composite reference to law of contract + law of arbitration agreement.

   ★ §11 APPOINTMENT — the gateway:
     Vidya Drolia v. Durga Trading (2021) 2 SCC 1 — "prima facie" review at §11 stage; arbitrability test; subject-matter that is non-arbitrable (criminal, matrimonial, insolvency, eviction under rent acts, antitrust).
     Cox & Kings v. SAP India (2024) 6 SCC 1 — group of companies doctrine; non-signatories can be bound to arbitration where commercial common intent + tight integration.
     N.N. Global Mercantile v. Indo Unique Flame (2023, Constitutional Bench) — unstamped/insufficiently-stamped arbitration agreement is curable defect; doesn't block §11 reference (overruling SMS Tea Estates and the prior 5-judge ruling).
     SBI General Insurance v. Krish Spinning (2024) — pre-§11 examination is narrow; tribunal decides own jurisdiction.
     In re: Interplay between Arbitration Agreements under A&C Act and Stamp Act 1899 (2023, 7-judge SC) — the dispositive Constitution Bench affirming N.N. Global on unstamped agreements.

   ★ §34 SET-ASIDE — narrow grounds, narrowly applied:
     Ssangyong Engineering v. NHAI (2019) 15 SCC 131 — public policy ground narrowed; "fundamental policy of Indian law" + patent illegality (only domestic awards) only.
     Associate Builders v. DDA (2015) 3 SCC 49 — public policy contours pre-Ssangyong (still cited).
     Renusagar Power v. General Electric (1994) Supp 1 SCC 644 — original "fundamental policy" framework for foreign awards (still good law for §48).
     Patent illegality NOT available for foreign-seated arbitration (post-2015 amendment to §34(2A)).
     Delhi Airport Metro v. DMRC (2022) 1 SCC 131 — Supreme Court reversal of HC interference; reinforces narrow §34 review.

   ★ ENFORCEMENT (§§36, 47-49):
     Vijay Karia v. Prysmian Cavi (2020) 11 SCC 1 — narrow §48 review for foreign awards; New York Convention discipline.
     Centrotrade Minerals v. HCL (2017) 2 SCC 228 — two-tier arbitration valid; appellate award is the "award" for enforcement.
     Glencore International AG v. Indian Potash Limited (2024 Del HC) — recent foreign-award enforcement principles.

   ★ INTERIM RELIEF (§§9, 17):
     Avitel Post Studioz v. HSBC PI Holdings (2020) — §9 power post-award and post-§17 tribunal grant.
     Arcelor Mittal Nippon Steel India v. Essar Bulk Terminal (2021) — §9 jurisdiction even after tribunal constituted, but courts will defer to §17.

   ★ INSTITUTIONAL DRAFTING — recommend MCIA (Mumbai), DIAC (Delhi International), ICA, DAC for India-seated; SIAC (Singapore) for India-Singapore cross-border; LCIA / ICC for international with Indian entity. Specify SEAT explicitly in clause + governing law of contract + curial law if foreign-seated.

   ★ MEDIATION ACT 2023 — pre-litigation mediation framework; commercial disputes ≥₹3 lakh under Commercial Courts Act mandatorily go through pre-institution mediation. Mediation settlement = decree; enforceable like court order.

★ CPC 1908 essentials:
   Order VII plaint (rejection of plaint Order VII Rule 11); Order VIII written statement; Order XXXVII summary suit (commercial money claims); Order XXIII withdrawal/compromise; Order XXI execution.
   §9 jurisdiction (every civil court has jurisdiction except where barred); §11 res judicata.
   Commercial Courts Act 2015 — specified value ≥ ₹3 lakh, expedited timelines, mandatory pre-institution mediation.
   Limitation Act 1963 — Schedule First; Article 110 partition (12 yrs); Article 113 residuary (3 yrs); Article 137 application.

★ NDA / IT Act execution — §3 IT Act DSC; §10A electronic contract validity. Mere typed names ≠ "electronic signature" in §3 sense.
""",

    # ────────────────────────────────────────────────────────────────────
    "constitutional": """
DOMAIN: CONSTITUTIONAL LAW & WRIT JURISDICTION

★ ARTICLE 32 vs ARTICLE 226 — bedrock distinction:
   Art 32 (SC) — ENFORCEMENT OF FUNDAMENTAL RIGHTS ONLY. Romesh Thappar v. State of Madras AIR 1950 SC 124 — guaranteed remedy itself a fundamental right.
   Art 226 (HC) — wider; FR enforcement + "any other purpose" (vires of subordinate legislation, administrative action, statutory and administrative-law grounds).
   ★ Self-restraint doctrine: Kanubhai Brahmbhatt v. State of Gujarat AIR 1987 SC 1159 — SC declines Art 32 where Art 226 available; relegate to HC. Pan-India impact ≠ ground for direct Art 32.
   Art 139A CPC — transfer of multiple HC writs to SC (separate strategic question; doesn't justify direct Art 32).
   L. Chandra Kumar v. UOI (1997) 3 SCC 261 — judicial review framework.
   Limitation/laches — Art 226 not subject to fixed limitation but courts apply laches.

★ ARTICLE 14 — equality before law / equal protection:
   ★ Reasonable classification twin-test (Anwar Ali Sarkar AIR 1952 SC 75 + Ram Krishna Dalmia AIR 1958 SC 538):
     (i) Intelligible differentia, AND
     (ii) Rational nexus with object sought to be achieved.
   ★ Manifest arbitrariness — E.P. Royappa v. State of T.N. (1974) 4 SCC 3; Maneka Gandhi v. UOI (1978) 1 SCC 248; Shayara Bano v. UOI (2017) 9 SCC 1 — Art 14 strikes down arbitrary state action even outside classification framework.
   Burden: presumption of constitutionality favours State; petitioner shows arbitrariness (Charanjit Lal Chowdhury AIR 1951 SC 41).
   ★ DON'T apply US "rational basis" / "strict scrutiny" terminology — Indian doctrine is differently articulated.

★ ARTICLE 19(1)(g) — right to trade/profession; reasonable restriction under §19(6). Modern fintech / data-business challenges (Internet & Mobile Association of India v. RBI 2020 10 SCC 274 — RBI crypto-banking ban struck down on proportionality / Article 19(1)(g)).

★ ARTICLE 21 — life and personal liberty; post-Maneka Gandhi (1978) 1 SCC 248 "procedure established by law" reads in due process and reasonableness.

★ THE PRIVACY DOCTRINE — the bedrock for ALL data-protection / surveillance / Aadhaar / DPDP challenges:
   ★ Justice K.S. Puttaswamy v. UOI (2017) 10 SCC 1 (9-judge Constitution Bench, "Puttaswamy I") — privacy is a Fundamental Right under Article 21, with informational privacy a sub-species. The PROPORTIONALITY TEST established by Puttaswamy I and refined in subsequent decisions:
     (i) Legitimate state aim
     (ii) Suitable means rationally connected to that aim
     (iii) Necessity — least restrictive means available
     (iv) Balancing — proportionate impact on the right vs the public interest
   ★ Justice K.S. Puttaswamy v. UOI (2018) 1 SCC 809 ("Puttaswamy II" / Aadhaar) — upheld Aadhaar Act with reading-down of §57 (private use); struck down §33(2) and limited authentication purposes; data minimisation and purpose limitation embedded in constitutional doctrine.
   ★ Anuradha Bhasin v. UOI (2020) 3 SCC 637 — internet shutdown orders must satisfy proportionality; periodic review mandated.
   ★ Foundation for Media Professionals v. UT of J&K (2020) 5 SCC 746 — proportionality review of internet restrictions.
   ★ Internet & Mobile Association of India v. RBI (2020) 10 SCC 274 — proportionality + Article 19(1)(g) on financial-services restrictions; demanded evidentiary basis for restrictive measures.
   ★ Karmanya Singh Sareen v. UOI — privacy-policy enforceability against private actors (WhatsApp/Facebook); unresolved on private-actor horizontal application.
   ★ Sabarimala (2018) — Article 14/15/25 intersection; non-discrimination doctrine.

★ DPDP-CONSTITUTIONAL INTERSECTION (the live battleground):
   ★ DPDP §17 exemptions are the most-likely-challenged provisions — particularly state-function exemption (§17(2)(a)) and notified-research exemption (§17(2)(d)). Likely Article 14 + 21 challenges on proportionality grounds (cf. Puttaswamy I framework).
   ★ Voluntary Aadhaar use under DPDP — distinguishing pre-Aadhaar §57 jurisprudence (private use barred) vs DPDP consent regime (private use permitted on free, specific, informed consent).
   ★ Cross-border transfer restrictions under §16 — pending operational test; sectoral regulator stricter rules can trigger Article 14 challenges if discriminatory.

★ HABEAS CORPUS:
   Liberal locus standi — Sunil Batra (II) v. Delhi Admin (1980) 3 SCC 488 (letter as petition); Kanu Sanyal v. DM (1973) 2 SCC 674; PUDR v. UOI (1982) 3 SCC 235 (Asiad workers — locus for socially disadvantaged).
   Forum: HC where detention occurs OR SC under Art 32. HC typically preferred for speed.
   Procedure: petition + affidavit + parties (Detenu/Detainer/State); emergency mentioning routine.

★ PIL — Bandhua Mukti Morcha (1984) line; relaxed standing where socially disadvantaged cannot approach court directly.

★ DIRECTIVE PRINCIPLES (Part IV) — non-justiciable but interpretive aid; harmonization via Minerva Mills (1980) basic structure.

★ BASIC STRUCTURE — Kesavananda Bharati (1973), Indira Nehru Gandhi (1975), Minerva Mills (1980), I.R. Coelho (2007) on judicial review, separation of powers, federalism, secularism, rule of law as immutable constitutional core.
""",

    # ────────────────────────────────────────────────────────────────────
    "fintech": """
DOMAIN: FINTECH / PAYMENTS / DATA PROTECTION / DIGITAL BUSINESS

★ DIGITAL PERSONAL DATA PROTECTION ACT 2023 + DPDP RULES 2025 — notified 13.11.2025:
   ★ PHASED IMPLEMENTATION (critical — most lawyers don't know the timeline):
     Phase 1 (13.11.2025 — NOW IN FORCE): Rules 1, 2, 17-21. Data Protection Board established in NCR with 4 members.
     Phase 2 (13.11.2026): Consent Manager registration and functioning.
     Phase 3 (13.05.2027): ALL substantive obligations — notice, consent, security safeguards, breach notification, erasure, data principal rights.
   §4 — Personal data processing ONLY for lawful purpose + individual consent (or §7 legitimate uses).
   §5 — Notice before/at time of collection: purpose, rights, grievance mechanism.
   §6 — Consent: free, specific, informed, unconditional, unambiguous; granular (NOT bundled with T&C); withdrawable with ease equal to giving.
   §7 — Legitimate uses WITHOUT consent: (a) voluntarily provided data for specified purpose, (b) State benefit/service/licence, (c) medical emergency, (d) employment, (e) public interest (fraud/security/credit scoring/debt recovery). NOT general "legitimate interest" like GDPR Art 6(1)(f) — this is an EXHAUSTIVE list.
   §8 — Data Fiduciary obligations: accuracy, completeness, security safeguards, breach notification to Board AND affected principals, erasure on purpose fulfilment.
   §9 — Significant Data Fiduciary (SDF): DPO mandatory (India-based), independent data auditor, periodic DPIA, periodic audit.
   §10 — Children's data: verifiable parental consent; BLANKET BAN on tracking/behavioural monitoring/targeted advertising (no exception).
   §11 — Consent Manager: new India-specific concept (no GDPR equivalent). Must be interoperable.
   §12 — Cross-border transfer: BLACKLIST model (all permitted unless specifically restricted). No adequacy assessment like GDPR.
   §16 — Data Principal rights: access summary, correction, erasure, grievance redressal, nomination. NO right to portability.
   §17 — Grievance: first to Data Fiduciary (prescribed period) → then to Data Protection Board.
   §18 — Penalties: ₹250 crore (security breach), ₹200 crore (breach notification failure / children), ₹150 crore (SDF obligations), ₹50 crore (other). Per breach, not per principal.
   §36 — Government exemptions — Puttaswamy (2017) 10 SCC 1 proportionality test applies to all exemptions.
   ★ CRITICAL DISTINCTIONS from GDPR (what Rohan's clients ask about):
     (1) No "legitimate interest" ground — consent or §7 legitimate use only.
     (2) No DPO mandatory for all — only SDFs.
     (3) No right to portability.
     (4) No extra-territorial direct enforcement (unlike GDPR Art 3).
     (5) Blacklist (not whitelist) for cross-border transfers.
     (6) Consent Manager as regulated intermediary (no GDPR equivalent).
     (7) Phase 3 substantive obligations don't bite until 13.05.2027 — current compliance window.
   ★ SPDI Rules 2011 (IT Act §43A) — STILL IN FORCE as of May 2026. Body corporates handling SPDI must comply with reasonable security practices (IS/ISO/IEC 27001). Will be superseded when Phase 3 activates.

★ RBI (REGULATION OF PAYMENT AGGREGATORS) DIRECTIONS, 2025 — RBI/DPSS/2025-26/141 dated 15.09.2025:
   ★ CRITICAL: This is a COMPLETE REPLACEMENT of the 2020/2021/2023 framework. Citing the old Master Direction dated 17.03.2020 is STALE. Always cite "RBI (Regulation of Payment Aggregators) Directions, 2025 dated 15.09.2025."
   ★ THREE FORMAL CATEGORIES (new — previously only online):
     (a) PA-Online (PA-O): online payment aggregation
     (b) PA-Physical (PA-P): point-of-sale transactions — NEWLY REGULATED for the first time
     (c) PA-Cross Border (PA-CB): import/export transaction aggregation — separate FEMA/AD bank requirements
   ★ Net-worth: ₹15 crore at application → ₹25 crore by end of 3rd FY post-authorisation. CCPs included; DTAs EXCLUDED.
   ★ DEADLINES (the ones Rohan's clients will ask about):
     - 31.12.2025: ALL PA-P entities must apply for RBI authorisation
     - 28.02.2026: wind-down deadline if not approved / application not filed
     - Existing PA-O entities with in-principle approval continue under existing terms
   ★ KYC OVERHAUL:
     - MANDATORY use of Central KYC Records Registry (CKYCR) for merchant onboarding (replaces general KYC compliance)
     - Simplified due diligence for small merchants: turnover ≤ ₹40 lakh (or export turnover ≤ ₹5 lakh) — PAN verification + contact point verification + one OVD
     - Ongoing transaction monitoring MANDATORY (new obligation)
     - FIU-IND registration mandatory for ALL non-bank PAs (AML/CFT compliance)
   ★ ESCROW:
     - PA-CB must maintain SEPARATE Inward Collection Account (InCA) + Outward Collection Account (OCA) — currency-wise segregation
     - Pre-funding of OCA PROHIBITED — funds collected only against specific transactions
     - Quarterly auditor certificates on escrow balances mandatory
     - Settlement to merchants: now per PA-merchant agreement (previously prescriptive T+1/T+3)
     - Third-party payouts restricted to merchants with turnover > ₹40 lakh
   ★ CROSS-BORDER: max transaction value ₹25 lakh; funds flow through AD banks
   ★ REPORTING: monthly transaction statistics + annual system audit + annual cyber-security audit (CERT-In empanelled auditors) + cyber incident reporting
   ★ Data localisation: RBI circular 06.04.2018 still applies — ALL payment data stored in India
   ★ Source: AZB & Partners analysis at azbpartners.com/bank/rbi-issues-consolidated-reserve-bank-of-india-regulation-of-payment-aggregators-directions-2025/

★ PREPAID PAYMENT INSTRUMENTS (PPIs) — RBI Master Direction 2021:
   ★ KYC categories: Minimum-KYC PPI (₹10K/month, ₹1.2L/year); Full-KYC PPI (₹2L outstanding).
   ★ Interoperability: Full-KYC PPIs MUST be interoperable (RBI Circular Oct 2022). UPI linkage allowed.
   ★ Cash withdrawal: at PoS/ATM for full-KYC PPIs up to ₹2,000/transaction.
   ★ Cross-border: PPI cannot be used for cross-border outward remittance (unless authorised PA-CB).

★ ACCOUNT AGGREGATOR (AA) FRAMEWORK — RBI Master Direction Sept 2016 (NBFC-AA) — LIVE DATA Dec 2025:
   ★ Consent Architecture: FIP (Financial Information Provider) → AA (consent manager) → FIU (Financial Information User). Data flows ONLY with explicit consent. AA CANNOT store/process financial data — pass-through only.
   ★ Scale (Dec 2025): 126 FIs live as FIP+FIU; 410 registered FIUs; 2.61 BILLION enabled accounts; 223 million users.
   ★ Sahamati: industry body for AA ecosystem. DigiSahamati Foundation operates the Central Registry.
   ★ FIP types: banks, NBFCs, insurers, MF houses, depositories, pension funds, GST Network.
   ★ Consent artifact: purpose, data types, frequency, duration, revocability — machine-readable JSON.
   ★ Fair Use Templates: Adopted by AA/FIU councils; AAs validate consent + data fetch against templates in REAL TIME from 01.06.2025.
   ★ Self-regulation: AAs proposed to be self-regulated under Sahamati (industry SRO model).

★ UPI REGULATIONS:
   ★ NPCI (National Payments Corporation of India) — operates UPI under RBI oversight.
   ★ UPI 30% market cap (per NPCI circular): no single TPApp can process >30% of UPI transactions (deadline extended multiple times; PhonePe/GPay grandfathered).
   ★ Interchange: P2M transactions — 1.1% MDR on PPI-based UPI; zero MDR on bank-account UPI (as per Finance Act 2020 §10A).
   ★ UPI Lite: on-device wallet up to ₹500/transaction, ₹4,000 balance; offline mode.

★ RBI (DIGITAL LENDING) DIRECTIONS, 2025 — issued 08.05.2025 (REPLACES 2022 Guidelines):
   ★ CRITICAL: Cite "RBI (Digital Lending) Directions, 2025 dated 08.05.2025" — NOT the 2022 Guidelines.
   ★ Three-party structure RETAINED: Regulated Entity (RE) + Lending Service Provider (LSP) + Digital Lending App (DLA).
   ★ LSP restrictions: NO direct fund disbursal to borrower (must be RE→borrower bank account); all product T&C from RE only; LSP fees paid by RE not borrower.
   ★ NEW — Multi-Lender LSPs: LSP partnering with multiple REs must remain impartial — cannot endorse/promote any specific RE's product. No dark patterns or deceptive design to mislead borrowers into selecting a particular lender. Transparent disclosure of ALL potential lenders mandatory.
   ★ FLDG (now called DLG — Default Loss Guarantee): Cap 5% retained. LSP must be incorporated under Companies Act 2013. DLG PROHIBITED for revolving credit facilities (new restriction). RE must conduct due diligence on DLG provider.
   ★ DLA Reporting: ALL DLAs (own/LSP, exclusive/shared) must be reported on RBI CIMS portal by 15.06.2025.
   ★ Key Fact Statement (KFS): standardised format for loan terms disclosure — mandatory for ALL digital loans.
   ★ Data minimisation: LSP/DLA access ONLY with explicit consent; no phone contacts, gallery, storage access.
   ★ Cooling-off period: 3 days post-disbursement for on-tap digital loans — borrower can exit without penalty.

★ VDA (Virtual Digital Assets) / CRYPTO REGULATION — current as of May 2026:
   ★ Tax: §115BBH — 30% flat (no deduction except cost of acquisition); §194S — 1% TDS on transfer exceeding ₹10K (₹50K for specified persons). Effective 01.04.2022.
   ★ No set-off of VDA losses against any other income; no carry-forward. This is ABSOLUTE.
   ★ Regulatory status: NO specific legislation. RBI ban quashed by SC in Internet & Mobile Association of India v. RBI (2020) 10 SCC 274. FinMin told Parliament (Feb 2026): "crypto still unregulated but under tax and enforcement radar."
   ★ PMLA / FIU-IND (CURRENT — this is what Rohan's VDA clients need):
     - VDA Service Providers are "reporting entities" under PMLA (notification March 2023).
     - 49 VDA-SPs registered with FIU-IND (45 domestic + 4 offshore serving Indian users) as of FY 2024-25.
     - FIU-IND AML & CFT Guidelines updated 08.01.2026 — enhanced KYC, transaction monitoring, STR, Travel Rule.
     - KYC refresh mandatory for accounts >18 months (effective 30.06.2025).
     - Designated Director (board-level) personally responsible for PMLA compliance.
     - FIU-IND imposed ₹28 crore in penalties on non-compliant exchanges in FY 2024-25.
     - 25 offshore VDA-SPs received FIU notices under PMLA §13 for non-compliance.
   ★ International: FATF Travel Rule compliance expected; India G20 paper 2023; IMF-FSB Synthesis Paper Sep 2023.

★ ELITE MOVES FOR FINTECH ADVISORY:
   - PA licence gap analysis: if client handles funds without PA licence, immediate compliance risk — quantify penalty under Payment and Settlement Systems Act 2007 §26A.
   - DPDP readiness audit: consent architecture, privacy notice, children's data handling, cross-border transfer mechanism, breach notification SOP.
   - AA integration strategy: which FIP data to pull, consent UX design, FIU onboarding timeline.
   - Digital lending compliance: verify FLDG cap, LSP registration, data access permissions, cooling-off implementation.
   - Tokenization compliance: verify no card-on-file storage; CoFT implementation timeline.
""",
}


# Task-specific persona overrides — injected into the user prompt so the
# model knows WHEN to be Harvey-the-loophole-finder vs WHEN to just answer
# a lookup cleanly. Without this, the model dramatizes everything (or
# nothing). Determinism comes from being explicit per task.
_TASK_PERSONA = {
    "lookup": (
        "This is a lookup. Answer the rate / threshold / definition cleanly. "
        "Cover: charging section, mechanism, exceptions, edge cases the practitioner actually hits in the field, "
        "and the most recent rate change with effective date. "
        "Don't manufacture tactical drama — there isn't one for a rate question. "
        "Concise: 3-6 sentences plus the precedent table only if a definitional case exists."
    ),
    "computation": (
        "Show the math. Walk through formula → substitution → arithmetic → final ₹ figure in a markdown computation table. "
        "Validate assumptions explicitly (residency, status of payer, FY/AY, regime selection). "
        "If a key variable is ambiguous, fork it and compute both. "
        "Surface second-order effects: interest, surcharge, cess, late-filing fees, potential disallowance, knock-on effects on other heads. "
        "Generalists stop at principal tax. You don't."
    ),
    "compliance_check": (
        "Walk through requirements as a checklist. "
        "For each requirement: state the rule (with provision number), state what evidences compliance, flag the deadline. "
        "If the client is non-compliant on any item, surface the consequence — penalty, late fee, prosecution exposure, ITC/deduction loss. "
        "End with a clear PASS/FAIL on each item. "
        "Don't dramatize routine compliance."
    ),
    "drafting": (
        "Draft the document the user asked for. "
        "Match the tone of the receiving forum — SCN reply is formal and combative; board resolution is procedural; writ petition is constitutional and persuasive. "
        "Use the standard structure: cause title → factual background → grounds (point-by-point) → prayer / relief. "
        "Where the user's facts are thin, draft placeholder language and flag it explicitly in [SQUARE BRACKETS] so the partner fills in. "
        "Don't invent facts. The drafted text comes FIRST — the analysis is supporting; the draft is the deliverable."
    ),
    "summarisation": (
        "Compress the input faithfully. Lead with the bottom-line takeaway. Then the structured points. "
        "Don't add facts that weren't in the source. "
        "If summarising a notice, judgment, or document, your output should be verifiable against that source line-by-line."
    ),
    # ── Default mode — engage with the question's actual complexity
    "research_memo": (
        "Lead with the answer. Then: cite the provision, the case, the number. "
        "Surface any procedural defect or limitation issue on THESE facts. "
        "Name the variable that changes the answer if facts shift. "
        "Pre-empt opposing counsel's best argument. "
        "If the law is unsettled, say so — name the conflicting authorities and which side you'd back. "
        "If the facts are incomplete, say what you need and what changes depending on the answer. "
        "No preamble. No restatement. No hedging without saying what the hedge depends on."
    ),
    "opinion": (
        "Lead with your conclusion. State your confidence: settled / majority view / divided / open. "
        "If divided, name both sides and say which you'd back on these facts and why. "
        "An opinion that hedges everything is worthless. Take a position."
    ),
    "case_strategy": (
        "Think like opposing counsel FIRST — what's their best argument? What evidence do they lean on? "
        "Then build our response. Plot the litigation timeline with dates. "
        "Surface settlement/compounding math if it exists. "
        "Name the ONE thing that decides this case and whether we control it."
    ),
}


def build_drafter_prompt(
    domain: str,
    chunks: list[dict],
    user_query: str,
    complexity: int = 3,
    task: str = "research_memo",
    web_context: str = "",
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the drafter.

    Injects runtime directives into the user message:
      1. CORPUS — retrieved statute sections from the 2,881-section Indian bare-act DB
      2. WEB_RESEARCH — live Google search results (if available)
      3. TASK_MODE — task-aware persona override
      4. TARGET_LENGTH — complexity-banded length floor
    """
    domain_ext = DOMAIN_EXTENSIONS.get(domain, "")
    system = DRAFTER_PROMPT_CORE + ("\n" + domain_ext if domain_ext else "")
    corpus_text = format_chunks_for_prompt(chunks)

    # Task-specific persona — defaults to research_memo (Harvey mode) when
    # the task tag is unrecognized.
    task_persona = _TASK_PERSONA.get(task, _TASK_PERSONA["research_memo"])

    # Word count targets REMOVED (May 2026). Forced padding that made output
    # generic. The model now writes as much as the substance requires — no more.

    # Pre-flight removed (May 2026). The 100-line meta-instruction block was
    # causing generic output — the model spent tokens on formatting rules
    # instead of substance. All formatting discipline is now in the system
    # prompt (DRAFTER_PROMPT_CORE). The user prompt is pure: corpus + query + go.

    # Inject web research if available — capped tight to keep total input
    # under GPT-5.5's 10K TPM budget on the demo key.
    web_section = ""
    if web_context:
        web_section = f"<WEB_RESEARCH>\n{web_context[:3500]}\n</WEB_RESEARCH>\n\n"

    # Cap corpus too — top 4 chunks is enough for grounding without blowing TPM
    if len(corpus_text) > 6000:
        corpus_text = corpus_text[:6000] + "\n[…corpus truncated for token budget…]"

    user = (
        f"<CORPUS>\n{corpus_text}\n</CORPUS>\n\n"
        f"{web_section}"
        f"<QUERY>\n{user_query}\n</QUERY>\n\n"
        f"<TASK_MODE>\n{task_persona}\n</TASK_MODE>\n\n"
        "RESPOND NOW.\n"
        "Your first sentence is the answer / the leading case / the recommended action — never narration.\n"
        "Banned first words (and any variation): \"Okay\", \"Let me\", \"First\", \"Looking at\", \"From the corpus\", \"The user\", \"I'll\", \"Sure\", \"Wait\".\n"
        "Never discuss the corpus inside the output. If a chunk is mislabelled, silently ignore it and use known law.\n"
        "Back every claim with a section number, case citation, or notification reference.\n"
        "If there's math, show the computation (formula -> numbers -> result).\n"
        "If law is unsettled or facts are incomplete, name what's missing and what would change the answer.\n"
        "If there's a risk the client hasn't spotted, surface it.\n"
        "End with deliverable artifacts where applicable (precedent table / computation / draft text / timeline / Vault hook)."
    )
    return system, user


def _route_for_model(model: str) -> tuple[str, str, str]:
    """Pick (url, key, surface_label) for a model.

    Surface preference (post-Emergent-exhaustion):
      - glm-* → z.ai
      - gpt-5* → direct OpenAI (mandatory for GPT-5.5)
      - qwen/* / mistralai/* / nvidia/* / google/gemma* / microsoft/phi* / meta/* → NVIDIA NIM
      - claude-* → fall back to NIM Qwen3-Thinking (Emergent dead, can't reach Claude)
      - default → direct OpenAI
    """
    if model.startswith("glm-"):
        return ZAI_URL, ZAI_KEY, "zai"
    if model in DIRECT_OPENAI_ONLY:
        return OPENAI_URL, OPENAI_KEY, "openai-direct"
    # NVIDIA NIM hosts Qwen, Mistral, Nemotron, Gemma, Phi, Llama families
    if NVIDIA_NIM_KEY and (
        model.startswith("qwen/") or model.startswith("mistralai/") or
        model.startswith("nvidia/") or model.startswith("google/gemma") or
        model.startswith("microsoft/phi") or model.startswith("meta/")
    ):
        return NVIDIA_NIM_URL, NVIDIA_NIM_KEY, "nim"
    # Claude — Emergent is dead; redirect to NIM Qwen3-Thinking which is the
    # secondary reasoner in this build.
    if model.startswith("claude-") and NVIDIA_NIM_KEY:
        return NVIDIA_NIM_URL, NVIDIA_NIM_KEY, "nim-claude-redirect"
    if EMERGENT_KEY:
        return EMERGENT_URL, EMERGENT_KEY, "emergent"
    return OPENAI_URL, OPENAI_KEY, "openai-direct"


async def draft_memo(
    system: str,
    user: str,
    model: str = MODEL_DRAFTER_TOP,
    rewrite_notes: Optional[str] = None,
    max_tokens: int = 12000,
    reasoning_effort: str = "medium",
    cache_key: str = "spectr_drafter_v2",
    _depth: int = 0,  # recursion guard — caps cascade fallbacks at 2 hops
) -> tuple[str, dict]:
    """Stage 2 — generate the memo. Returns (text, usage).

    Routes by surface:
      - glm-*     → z.ai (auto-fallback to OpenAI on 4xx)
      - gpt-5*    → direct OpenAI with reasoning_effort + max_completion_tokens
      - otherwise → Emergent universal key (budget-efficient)

    Prompt caching:
      - OpenAI auto-caches any prefix ≥ 1024 tokens. Our system prompt is
        ~5K tokens so we get a 50% discount on cached prompt tokens for
        repeat queries. We also pass `prompt_cache_key` to bias OpenAI's
        load balancer toward the same backend — boosts hit rate ~30%.
      - Cache works best when the system prompt is byte-identical across
        calls. We keep it that way by passing CORPUS in the user message,
        not the system message.

    GPT-5 reasoning_effort:
      - "minimal" → no reasoning (matches GPT-4 latency, lowest quality)
      - "low"     → quick reasoning, good for simple queries
      - "medium"  → balanced (default for most queries)
      - "high"    → maximum thoughtfulness, longest latency

    On non-200, cascades down to a cheaper sibling so the user never sees
    an empty response just because one provider hiccupped.
    """
    if rewrite_notes:
        user = user + f"\n\n<CRITIC_NOTES>\n{rewrite_notes}\n</CRITIC_NOTES>\n\nRewrite addressing these notes."

    # Recursion guard — kill any cascade > 2 hops. Prevents the
    # GPT-5.5↔NIM ping-pong observed when both are unhealthy.
    if _depth > 2:
        logger.warning(f"Drafter {model}: cascade depth {_depth} hit — aborting fallback chain")
        return "", {"model": model, "in_tokens": 0, "out_tokens": 0, "surface": "depth-cap"}

    url, key, surface = _route_for_model(model)
    if not key:
        logger.warning(f"Drafter {model}: no API key for surface {surface} — skipping")
        return "", {"model": model, "in_tokens": 0, "out_tokens": 0}

    is_gpt5 = model in GPT5_FAMILY
    is_anthropic = "claude" in model.lower()
    is_nim = surface in ("nim", "nim-claude-redirect")
    payload: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    # Only OpenAI accepts prompt_cache_key. Anthropic, NIM, z.ai all reject it.
    if not is_anthropic and not is_nim and surface in ("openai-direct", "emergent"):
        payload["prompt_cache_key"] = cache_key
    if is_gpt5:
        # GPT-5 reasoning models: no temperature, use max_completion_tokens
        # plus reasoning_effort for state-of-the-art reasoning depth.
        payload["max_completion_tokens"] = max_tokens
        payload["reasoning_effort"] = reasoning_effort
    else:
        payload["temperature"] = 0.2
        payload["max_tokens"] = max_tokens

    # Per-surface timeout — GPT-5.5 high-effort can take 90s on hard queries.
    # NIM Mistral with 4500 max_tokens should respond in ~25s; 60s gives a
    # 2x margin for cold-cache spikes without hanging the user.
    drafter_timeout = 60 if surface == "nim" else 90
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=drafter_timeout)) as session:
            async with session.post(url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    logger.warning(f"Drafter {model} via {surface} HTTP {resp.status}: {err[:240]}")
                    # ── 429 RATE-LIMIT FAST FAILOVER ──
                    # OpenAI demo key has TPM=10K. When we hit 429 it means the
                    # 60s rolling window is saturated — backing off makes wall-clock
                    # explode (60-120s). Better play: immediately fail over to
                    # Qwen3-Thinking on NVIDIA NIM (no TPM ceiling). 1 short retry
                    # in case it was a brief spike, then bail.
                    if resp.status == 429 and is_gpt5 and NVIDIA_NIM_KEY and _depth < 2:
                        logger.warning(
                            f"Drafter {model} 429 on TPM ceiling — failing over to "
                            f"Mistral Large 3 (NIM, no retry wait)"
                        )
                        # ULTRA-LONG MODE — Mistral 675B on NIM has no TPM cap.
                        # Empirically NIM does ~150 tok/s on this model. Cap at
                        # 3000 tokens (~2000 words = "ultra-long" by spec) so
                        # generation fits in ~20s + 2s overhead = ~22s wall-clock.
                        return await draft_memo(
                            system, user, model="mistralai/mistral-large-3-675b-instruct-2512",
                            max_tokens=3000, cache_key=cache_key, _depth=_depth+1,
                        )
                    if resp.status == 429:
                        # Non-GPT-5.5 or NIM unavailable — short retry (3s + 6s)
                        for attempt in (1, 2):
                            wait_s = 3 * attempt
                            logger.info(f"Drafter {model} 429 — backing off {wait_s}s (attempt {attempt}/2)")
                            await asyncio.sleep(wait_s)
                            async with session.post(url,
                                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                                json=payload) as r_retry:
                                if r_retry.status == 200:
                                    data = await r_retry.json()
                                    choices = (data or {}).get("choices") or []
                                    msg = (choices[0].get("message") if choices else {}) or {}
                                    text = msg.get("content") or ""
                                    usage = (data or {}).get("usage") or {}
                                    ptd = usage.get("prompt_tokens_details") or {}
                                    return text, {
                                        "model": model, "surface": surface,
                                        "in_tokens": usage.get("prompt_tokens", 0),
                                        "out_tokens": usage.get("completion_tokens", 0),
                                        "cached_tokens": (ptd.get("cached_tokens", 0) if isinstance(ptd, dict) else 0),
                                    }
                                if r_retry.status != 429:
                                    # Different error on retry — break and fall through
                                    break
                    # Some Emergent backends still reject prompt_cache_key/reasoning_effort.
                    # Strip them and retry once before cascading down.
                    if "prompt_cache_key" in err or "reasoning_effort" in err or resp.status == 400:
                        payload.pop("prompt_cache_key", None)
                        payload.pop("reasoning_effort", None)
                        async with session.post(url,
                            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                            json=payload) as r2:
                            if r2.status == 200:
                                data = await r2.json()
                                choices = (data or {}).get("choices") or []
                                msg = (choices[0].get("message") if choices else {}) or {}
                                text = msg.get("content") or ""
                                usage = (data or {}).get("usage") or {}
                                ptd = usage.get("prompt_tokens_details") or {}
                                return text, {
                                    "model": model, "surface": surface,
                                    "in_tokens": usage.get("prompt_tokens", 0),
                                    "out_tokens": usage.get("completion_tokens", 0),
                                    "cached_tokens": (ptd.get("cached_tokens", 0) if isinstance(ptd, dict) else 0),
                                }
                    # Cascade fallback — ONLY between the two peak models
                    if surface == "zai":
                        return await draft_memo(system, user, model="gpt-5.5", max_tokens=max_tokens, reasoning_effort="high", cache_key=cache_key, _depth=_depth+1)
                    if surface == "emergent":
                        # Claude failed via Emergent → try GPT-5.5 direct
                        return await draft_memo(system, user, model="gpt-5.5", max_tokens=max_tokens, reasoning_effort="high", cache_key=cache_key, _depth=_depth+1)
                    if surface == "openai-direct" and is_gpt5:
                        # GPT-5.5 direct failed → silent fallback to Qwen3-Thinking on NIM
                        return await draft_memo(system, user, model="mistralai/mistral-large-3-675b-instruct-2512", max_tokens=max_tokens, cache_key=cache_key, _depth=_depth+1)
                    return "", {"model": model, "in_tokens": 0, "out_tokens": 0}
                data = await resp.json()
                # Defensive parsing: NIM and other OpenAI-compatible endpoints
                # sometimes omit fields or return them as None.
                choices = (data or {}).get("choices") or []
                msg = (choices[0].get("message") if choices else {}) or {}
                text = (msg.get("content") or "")
                # NIM Qwen3-Thinking emits reasoning_content separately — fold it back
                if not text and msg.get("reasoning_content"):
                    text = msg.get("reasoning_content") or ""
                usage = (data or {}).get("usage") or {}
                ptd = usage.get("prompt_tokens_details") or {}
                cached = ptd.get("cached_tokens", 0) if isinstance(ptd, dict) else 0
                # GPT-5 emergency: if reasoning ate all tokens and content is
                # empty, retry with Qwen3-Thinking on NIM (different reasoning architecture).
                if not text.strip() and is_gpt5:
                    logger.warning(f"Drafter {model} returned empty content (reasoning consumed budget) — retrying via Qwen3-Thinking on NIM")
                    return await draft_memo(system, user, model="mistralai/mistral-large-3-675b-instruct-2512", max_tokens=max_tokens, cache_key=cache_key, _depth=_depth+1)
                if cached:
                    logger.info(f"[spectr_pipeline] cache hit: {cached}/{usage.get('prompt_tokens',0)} tokens cached on {model}")
                return text, {
                    "model": model,
                    "surface": surface,
                    "in_tokens": usage.get("prompt_tokens", 0),
                    "out_tokens": usage.get("completion_tokens", 0),
                    "cached_tokens": cached,
                }
    except Exception as e:
        logger.warning(f"Drafter {model} via {surface} exception: {e}")
        # Last-resort cascade — stay on peak models only
        if "claude" in model.lower():
            # Claude failed → try GPT-5.5
            return await draft_memo(system, user, model="gpt-5.5", max_tokens=max_tokens, reasoning_effort="high", cache_key=cache_key, _depth=_depth+1)
        elif surface != "openai-direct":
            # Non-direct failed → try GPT-5.5 direct
            return await draft_memo(system, user, model="gpt-5.5", max_tokens=max_tokens, reasoning_effort="high", cache_key=cache_key, _depth=_depth+1)
        return "", {"model": model, "in_tokens": 0, "out_tokens": 0}


# ============================================================================
# STAGE 3 — CRITIC
# ============================================================================

CRITIC_PROMPT = """You are the Spectr quality gate. You do NOT rewrite prose for style. You check facts, citation integrity, and reasoning depth against the retrieved corpus.

Return strict JSON (no prose, no markdown fences — raw JSON object):

{
  "citation_integrity": {
    "hallucinated_sections": ["<statute refs in draft NOT in corpus AND not verifiably known>"],
    "hallucinated_cases":    ["<case citations that appear fabricated — Indian case names are easy to invent>"],
    "unsupported_generalities": ["<sentences claiming judicial/legislative positions without tied citation>"]
  },
  "structural_compliance": {
    "missing_substance": ["<required deliverables missing: precedent table / draft text / computation / timeline / vault hook — per the deliverable mandate>"],
    "wrong_jurisdiction_bleed": ["<sentences relying on US/UK/EU law without user asking for comparative>"]
  },
  "reasoning_depth": {
    "opens_with_answer": true|false,
    "has_non_obvious_authority": true|false,
    "has_tactical_angle": true|false,
    "pre_empts_counter": true|false,
    "shows_math_if_needed": true|false
  },
  "domain_errors": ["<factual legal errors you can identify from the corpus — stale rates, wrong section numbers, outdated law>"],
  "must_fix": true|false,
  "rewrite_instructions": "<crisp numbered instructions for the drafter if must_fix>"
}

RULES:
- A hallucinated citation sets must_fix=true.
- Missing ALL deliverable artifacts (no table, no draft text, no computation) sets must_fix=true.
- Generic template output (numbered sections like '1. ISSUE FRAMING', '2. GOVERNING LAW') sets must_fix=true — the response should use natural descriptive headings.
- Stale law (citing IPC for post-2024, old GST rates, old §87A thresholds) sets must_fix=true.
- Do NOT penalise for missing rigid section structure. Good memos have natural flow with descriptive headings.
- Be strict on substance. Be lenient on format.
"""


async def critique_draft(draft: str, chunks: list[dict], user_query: str) -> tuple[dict, dict]:
    """Stage 3 — verify the draft. Returns (critique_json, usage)."""
    corpus_text = format_chunks_for_prompt(chunks)
    user = (
        f"<CORPUS>\n{corpus_text}\n</CORPUS>\n\n"
        f"<USER_QUERY>\n{user_query}\n</USER_QUERY>\n\n"
        f"<DRAFT>\n{draft}\n</DRAFT>\n\n"
        "Evaluate the DRAFT against the CORPUS and USER_QUERY. Emit the strict JSON."
    )
    is_gpt5_critic = MODEL_CRITIC in GPT5_FAMILY
    payload = {
        "model": MODEL_CRITIC,
        "messages": [
            {"role": "system", "content": CRITIC_PROMPT},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
    }
    if is_gpt5_critic:
        payload["max_completion_tokens"] = 8000
        payload["reasoning_effort"] = "low"
    else:
        payload["temperature"] = 0
        payload["max_tokens"] = 1500
    url, key, surface = _route_for_model(MODEL_CRITIC)
    if not key:
        return {"must_fix": False, "_error": "no_key"}, {}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload) as resp:
                if resp.status != 200:
                    logger.warning(f"Critic {surface} HTTP {resp.status}")
                    # Fall through to direct OpenAI on Emergent failure
                    if surface == "emergent" and OPENAI_KEY:
                        async with session.post(OPENAI_URL,
                            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
                            json=payload) as r2:
                            if r2.status == 200:
                                data = await r2.json()
                                surface = "openai-direct"
                            else:
                                return {"must_fix": False, "_error": f"HTTP {resp.status}"}, {}
                    else:
                        return {"must_fix": False, "_error": f"HTTP {resp.status}"}, {}
                else:
                    data = await resp.json()
                text = data["choices"][0]["message"]["content"]
                critique = json.loads(text)
                usage = data.get("usage", {})
                return critique, {
                    "model": MODEL_CRITIC,
                    "surface": surface,
                    "in_tokens": usage.get("prompt_tokens", 0),
                    "out_tokens": usage.get("completion_tokens", 0),
                }
    except Exception as e:
        logger.warning(f"Critic failed: {e}")
        return {"must_fix": False, "_error": str(e)[:120]}, {}


# ============================================================================
# COST LOGGER
# ============================================================================

# Rough INR cost per 1K tokens (current OpenAI + z.ai pricing, Apr 2026)
COST_INR_PER_1K = {
    "gpt-4o-mini":          {"in": 0.012, "out": 0.050},
    "gpt-4.1-mini":         {"in": 0.033, "out": 0.133},
    "gpt-4.1":              {"in": 0.167, "out": 0.667},
    "gpt-5.5":              {"in": 0.350, "out": 1.400},
    "gpt-5":                {"in": 0.300, "out": 1.200},
    "gpt-5-mini":           {"in": 0.045, "out": 0.180},
    "claude-sonnet-4-6":    {"in": 0.250, "out": 1.250},
    "claude-sonnet-4-5":    {"in": 0.250, "out": 1.250},
    "claude-opus-4-6":      {"in": 1.250, "out": 6.250},  # premium tier
    "claude-opus-4-7":      {"in": 1.250, "out": 6.250},
    # z.ai (Zhipu GLM) — budget tier. GLM-4.5 ≈ ₹0.01/1K in, GLM-4.6 ≈ ₹0.05/1K in.
    "glm-4.5":              {"in": 0.010, "out": 0.040},
    "glm-4.6":              {"in": 0.050, "out": 0.200},
    "fallback-regex":       {"in": 0.000, "out": 0.000},
}


def compute_cost_inr(usage_list: list[dict]) -> float:
    """Per-turn cost in INR.

    Accounts for OpenAI prompt-cache discount: cached input tokens are
    billed at 50% of the live input rate. So a memo that re-uses the
    5K-token system prompt across the drafter+critic+rewrite calls saves
    ~₹0.50-₹2 depending on tier.
    """
    total = 0.0
    for u in usage_list:
        if not u:
            continue
        model = u.get("model", "")
        pricing = COST_INR_PER_1K.get(model, {"in": 0.25, "out": 1.0})
        in_tokens = u.get("in_tokens", 0)
        cached = u.get("cached_tokens", 0)
        live = max(in_tokens - cached, 0)
        # Cached tokens at 50% of the input rate (OpenAI standard discount)
        total += (live / 1000) * pricing["in"]
        total += (cached / 1000) * pricing["in"] * 0.5
        total += (u.get("out_tokens", 0) / 1000) * pricing["out"]
    return round(total, 4)


# ============================================================================
# ORCHESTRATOR — the full 4-stage cascade
# ============================================================================

_TRIVIAL_GREETINGS = {
    "hi", "hii", "hiii", "hey", "heyy", "heyyy", "hello", "helloo", "yo", "yoo",
    "hola", "namaste", "namaskar", "sup", "wassup", "whatsup",
    "good morning", "good afternoon", "good evening", "gm", "gn",
    "thanks", "thank you", "thx", "ty", "cheers", "appreciated",
    "ok", "okay", "k", "kk", "cool", "nice", "great", "awesome", "got it",
    "yes", "no", "yeah", "yep", "nope", "sure", "alright", "fine",
    "bye", "goodbye", "cya", "later", "ttyl",
    "test", "testing", "ping", "lol", "haha",
}

# Legal keywords matched as WHOLE WORDS (regex word boundaries) to avoid
# false positives like "today my" matching "ay " (assessment year).
_LEGAL_KEYWORD_LIST = [
    "section", "sec", "act", "rule", "notification", "circular", "notice", "scn",
    "tax", "taxes", "tds", "tcs", "gst", "itc", "gstr", "itr", "cgst", "igst", "sgst",
    "194", "194i", "194j", "194c", "194a", "194ib", "143", "148", "271c", "40a",
    "bail", "fir", "writ", "petition", "appeal", "tribunal", "court", "judge",
    "case", "judgment", "judgement", "ratio", "precedent", "limitation", "penalty",
    "fine", "compute", "draft", "drafting", "reply", "compliance", "audit",
    "reconcile", "reconciliation", "demand", "show-cause", "showcause",
    "ipc", "bns", "bnss", "crpc", "fema", "sebi", "ibc", "mca", "rbi", "cbic",
    "cbdt", "lodr", "pmla", "cirp", "nclt", "nclat", "drt", "itat", "cestat",
    "fy", "ay", "lakh", "lakhs", "crore", "crores", "client", "matter",
    "advocate", "lawyer", "memo", "opinion", "advisory", "exposure", "deduction",
    "exemption", "credit", "input", "output", "supply", "invoice", "vendor",
    "assessee", "assessment", "assessor", "officer", "ao", "scrutiny",
    "challan", "refund", "rectification", "appellate", "writ",
    "contract", "clause", "indemnity", "covenant", "jurisdiction", "moratorium",
    "directors", "director", "shareholder", "agm", "egm", "rocs", "roc",
    "depreciation", "capital", "gains", "loss", "income", "salary", "rent",
    "deductee", "deductor", "tdsr", "regime", "old", "new", "regimes",
]
# Pre-compile a single regex with all keywords as word-bounded alternatives
_LEGAL_KEYWORDS_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in _LEGAL_KEYWORD_LIST) + r")\b",
    re.IGNORECASE,
)
# Currency / number patterns that strongly indicate a real query
_LEGAL_SYMBOL_RE = re.compile(r"₹|\brs\.?\b|\bsec\.?\s*\d", re.IGNORECASE)
# Backward-compatibility alias for any code that still imports _LEGAL_KEYWORDS
_LEGAL_KEYWORDS = tuple(_LEGAL_KEYWORD_LIST)


def _heuristic_intent(query: str) -> str:
    """Free, instant intent guess: 'trivial' | 'real' | 'unsure'.

    'trivial' / 'real' are confident — use them as-is.
    'unsure' means hand it to the LLM intent gate for a tiebreaker.

    This handles ~95% of queries with no LLM call:
      - Legal keyword present anywhere → 'real'
      - Short (≤25 chars) with no legal keyword → 'trivial'
      - Otherwise → 'unsure' (let the LLM decide)
    """
    q = (query or "").strip().lower()
    if not q:
        return "trivial"
    q = re.sub(r"[!?.,;:\s]+$", "", q).strip()
    if not q:
        return "trivial"

    # Legal keyword anywhere (word-bounded match) → confidently real
    if _LEGAL_KEYWORDS_RE.search(q) or _LEGAL_SYMBOL_RE.search(q):
        return "real"

    tokens = q.split()
    # Short greeting-shaped → confidently trivial (no LLM needed)
    if q in _TRIVIAL_GREETINGS:
        return "trivial"
    if tokens and tokens[0] in _TRIVIAL_GREETINGS and len(tokens) <= 8:
        return "trivial"
    if len(tokens) == 1 and len(q) <= 6:
        return "trivial"
    if len(q) <= 25 and not any(c.isdigit() for c in q):
        return "trivial"

    # Long-ish + no legal keyword + has structure → genuinely unclear.
    # Could be "explain salary structure" (real) or "tell me a joke" (trivial).
    # Hand to the LLM gate.
    return "unsure"


_INTENT_GATE_PROMPT = """You are a binary intent classifier for an Indian legal/tax research assistant.

Reply with EXACTLY ONE LETTER and nothing else:
  L  → the user is asking an Indian legal, tax, GST, corporate, criminal, IBC, IPR, FEMA, SEBI, family, property, or constitutional question. Includes paraphrased queries with spelling errors. Includes any request to draft, compute, analyse, review, or research a legal/tax matter.
  T  → trivial: greeting, small talk, thank-you, yes/no, "test", "how are you", emoji-only, off-topic chit-chat, or a question outside Indian legal/tax (cooking, sports, dating, weather, world news).

Spelling and grammar are irrelevant — judge intent, not surface form. "wht is sec 194" is L. "hie how r u" is T. "tell me about my ex" is T. "can u help me reply to a notice" is L.

ONLY respond with a single character: L or T."""


async def _intent_via_groq(query: str) -> Optional[str]:
    """Primary intent classifier — Groq llama-3.1-8b-instant.

    Returns 'real' / 'trivial' on success, or None on failure (caller falls
    back to OpenAI gpt-4o-mini). ~400ms, free under Groq's quota — perfect
    for high-volume triage that we don't want to pay premium for.
    """
    if not GROQ_KEY:
        return None
    payload = {
        "model": GROQ_INTENT_MODEL,
        "messages": [
            {"role": "system", "content": _INTENT_GATE_PROMPT},
            {"role": "user", "content": (query or "")[:500]},
        ],
        "temperature": 0,
        "max_tokens": 2,
    }
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=6)) as s:
            async with s.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                json=payload,
            ) as r:
                if r.status != 200:
                    err = await r.text()
                    logger.info(f"[intent-gate] groq HTTP {r.status}: {err[:120]}")
                    return None
                data = await r.json()
                tok = (data["choices"][0]["message"]["content"] or "").strip().upper()
                return "trivial" if tok.startswith("T") else "real"
    except Exception as e:
        logger.info(f"[intent-gate] groq exception: {e}")
        return None


async def _intent_via_openai(query: str) -> str:
    """Fallback intent classifier when Groq is unreachable.

    Routes through Emergent universal key (cheaper than direct OpenAI) and
    falls back to direct OpenAI if Emergent strips parameters.
    """
    url, key, surface = _route_for_model("gpt-4o-mini")
    if not key:
        return "real"  # safest default — better to run pipeline than miss a real query
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": _INTENT_GATE_PROMPT},
            {"role": "user", "content": (query or "")[:500]},
        ],
        "temperature": 0,
        "max_tokens": 2,
    }
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as s:
            async with s.post(
                url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            ) as r:
                if r.status != 200:
                    return "real"
                data = await r.json()
                tok = (data["choices"][0]["message"]["content"] or "").strip().upper()
                return "trivial" if tok.startswith("T") else "real"
    except Exception:
        return "real"


async def _llm_intent_gate(query: str) -> str:
    """DEMO LOCK — Groq + gpt-4o-mini disabled. Heuristic-only triage.

    For ambiguous queries the heuristic can't decide, default to 'real'
    (route to full pipeline) rather than risk under-serving. Premium
    models handle the rest.
    """
    return "real"


async def _classify_intent(query: str) -> str:
    """Combined heuristic + LLM intent classification.

    Returns 'trivial' or 'real'. Never returns 'unsure' — defers to the LLM
    when the heuristic can't decide.
    """
    h = _heuristic_intent(query)
    if h in ("trivial", "real"):
        return h
    # 'unsure' → ask the LLM (only ~5% of queries hit this branch)
    return await _llm_intent_gate(query)


def _is_trivial_query(query: str) -> bool:
    """Backward-compatible sync wrapper. Prefer _classify_intent for new code.

    Used by tests and any sync callers — only checks the free heuristic, so
    'unsure' results default to False (treat as real, run the pipeline).
    """
    return _heuristic_intent(query) == "trivial"


async def _triage_response(query: str) -> str:
    """1-sentence conversational reply for trivial queries — no LLM call.

    Stays in the same voice as the main drafter (direct, no fluff) so the
    user doesn't get jarring tone shifts between greetings and real memos.
    """
    q = (query or "").strip().lower()
    q_clean = re.sub(r"[!?.,;:]+$", "", q).strip()

    if q_clean in {"hi", "hii", "hiii", "hey", "heyy", "heyyy", "hie", "hiee", "hiya", "hello", "helloo", "yo", "yoo", "hola", "namaste", "sup", "wassup", "hyy", "heyya", "halo", "helo"}:
        return "Hey. What do you want to work on — a notice, a section, a computation, a draft?"
    if q_clean in {"good morning", "gm"}:
        return "Morning. What's on the desk today?"
    if q_clean in {"good afternoon"}:
        return "Afternoon. What do you need?"
    if q_clean in {"good evening", "gn"}:
        return "Evening. What's the matter you're working on?"
    if q_clean in {"thanks", "thank you", "thx", "ty", "cheers", "appreciated"}:
        return "Anytime. Next question?"
    if q_clean in {"ok", "okay", "k", "kk", "cool", "nice", "great", "awesome", "got it"}:
        return "Good. What do you want to look at next?"
    if q_clean in {"yes", "yeah", "yep", "sure", "alright", "fine"}:
        return "Got it. What's the question?"
    if q_clean in {"no", "nope"}:
        return "Understood. Different angle then — what do you need?"
    if q_clean in {"bye", "goodbye", "cya", "later", "ttyl"}:
        return "Catch you later. Memo's saved in your thread when you come back."
    if q_clean in {"test", "testing", "ping"}:
        return "I'm up. Send a real question and I'll work it."
    # Generic short non-legal fallback
    return "I work Indian tax and legal questions — give me a notice, a section, a fact pattern, or a draft to mark up, and I'll pull it apart."


async def run_spectr_pipeline(
    user_query: str,
    recent_history: list[dict] | None = None,
    force_deep: bool = False,
    timing_budget_s: int = 45,
) -> dict:
    """Single entry point. Returns:
      {
        "response_text": "<final memo>",
        "classification": {...},
        "chunks_used":    [...],
        "critique":       {...},
        "rewrote":        bool,
        "timings":        {"classify": 1.2, "retrieve": 0.1, "draft": 22.3, "critic": 4.5, "total": 28.1},
        "cost_inr":       0.85,
        "model_used":     "gpt-4.1",
      }
    """
    t_overall = time.time()
    usages: list[dict] = []

    # ── Stage -1: INTENT GATE ────────────────────────────────────────
    # Two-tier triage:
    #   1. Free heuristic catches obvious cases (~95% of queries)
    #      "hie", "thanks", "what is section 194I" → instant decision
    #   2. LLM tiebreaker for genuinely ambiguous text
    #      "tell me about my dog", "explain quantum physics" → ~400ms
    #
    # Force-deep skips triage entirely (user explicitly chose Depth Research).
    if not force_deep:
        t0 = time.time()
        intent = await _classify_intent(user_query)
        t_intent = time.time() - t0
        logger.info(f"[spectr_pipeline] intent: {intent} ({t_intent*1000:.0f}ms)")
        if intent == "trivial":
            text = await _triage_response(user_query)
            return {
                "response_text": text,
                "classification": {"domain": "trivial", "task": "chitchat", "complexity": 0},
                "chunks_used": [],
                "critique": {"must_fix": False, "_skipped": "triage path"},
                "rewrote": False,
                "timings": {"intent": round(t_intent, 3), "classify": 0.0,
                            "retrieve": 0.0, "draft": 0.0, "critic": 0.0,
                            "total": round(time.time() - t_overall, 3)},
                "cost_inr": 0.005 if t_intent > 0.05 else 0.0,  # rough — LLM gate cost
                "model_used": "triage-canned",
                "usages": [],
            }

    # ── Stage 0: Classifier ────────────────────────────────────────────
    t0 = time.time()
    classification = await classify_query(user_query, recent_history=recent_history)
    t_classify = time.time() - t0
    usages.append(classification.pop("_usage", {}))

    domain = classification.get("domain", "other")
    task = classification.get("task", "research_memo")
    complexity = classification.get("complexity", 3)
    queries = classification.get("retrieval_queries") or [user_query]
    escalate = bool(classification.get("escalate_to_claude")) or force_deep

    logger.info(
        f"[spectr_pipeline] classify: domain={domain} task={task} complexity={complexity} "
        f"escalate={escalate} ({t_classify:.1f}s)"
    )

    # ── Stage 1: Retrieval (corpus + Parallel.ai deep research + Serper in parallel) ────
    t0 = time.time()
    # k=6 default, k=10 deep — 12+ saturates 10K TPM and adds no marginal recall
    # given web context already brings 4K chars of fresh authority.
    k = 10 if complexity >= 4 else 6

    # THREE research sources in PARALLEL — this is the moat.
    # Vanilla Claude has NONE of these. We have all three.

    async def _parallel_ai_research():
        """Parallel.ai deep web research — LLM-optimized excerpts with citations."""
        if not PARALLEL_KEY:
            return ""
        try:
            # Build 2-3 focused search queries from the classifier's retrieval_queries
            search_queries = queries[:3] if queries else [user_query[:200]]
            payload = {
                "search_queries": search_queries,
            }
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as sess:
                async with sess.post(
                    PARALLEL_URL,
                    headers={"x-api-key": PARALLEL_KEY, "Content-Type": "application/json"},
                    json=payload,
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("results", [])
                        if results:
                            parts = ["=== DEEP WEB RESEARCH (Parallel.ai) ==="]
                            for r in results[:8]:
                                title = r.get("title", "")
                                url = r.get("url", "")
                                date = r.get("publish_date", "")
                                excerpts = r.get("excerpts", [])
                                if excerpts:
                                    parts.append(f"\n[{title}] ({url}) {date}")
                                    parts.append("\n".join(excerpts[:2]))
                            return "\n".join(parts)
                    else:
                        err = await resp.text()
                        logger.debug(f"[parallel.ai] HTTP {resp.status}: {err[:100]}")
        except Exception as e:
            logger.debug(f"[parallel.ai] non-blocking error: {e}")
        return ""

    async def _serper_research():
        """Serper Google + News + Scholar."""
        try:
            from serper_search import run_comprehensive_search, format_serper_for_llm
            query_types = [domain] if domain != "other" else ["legal", "taxation"]
            results = await run_comprehensive_search(user_query, query_types, include_news=True, include_scholar=True)
            if results and results.get("results"):
                return format_serper_for_llm(results, user_query)
        except Exception as e:
            logger.debug(f"[spectr_pipeline] serper non-blocking error: {e}")
        return ""

    # Fire ALL THREE in parallel — total latency = max(corpus, parallel, serper) ≈ 2-3s
    # Web layers (Parallel.ai + Serper) are cached for 15 minutes per
    # (query+domain) key — the second time the user asks the same thing
    # within the window, web layer is instant.
    web_cache_key = hashlib.md5(f"{user_query}|{domain}".encode("utf-8")).hexdigest()
    cached_web = _WEB_CACHE.get(web_cache_key)
    now_ts = time.time()
    if cached_web and (now_ts - cached_web["ts"]) < _WEB_CACHE_TTL:
        logger.info(f"[spectr_pipeline] web cache HIT (key={web_cache_key[:8]}, age={int(now_ts - cached_web['ts'])}s)")
        chunks = await retrieve_chunks(queries, k=k, domain=domain)
        parallel_context = cached_web["parallel"]
        serper_context = cached_web["serper"]
    else:
        corpus_task = retrieve_chunks(queries, k=k, domain=domain)
        parallel_task = _parallel_ai_research()
        serper_task = _serper_research()
        chunks, parallel_context, serper_context = await asyncio.gather(
            corpus_task, parallel_task, serper_task
        )
        _WEB_CACHE[web_cache_key] = {
            "ts": now_ts,
            "parallel": parallel_context,
            "serper": serper_context,
        }
        # Trim cache to 50 entries (LRU-ish: drop oldest)
        if len(_WEB_CACHE) > 50:
            oldest = sorted(_WEB_CACHE.items(), key=lambda kv: kv[1]["ts"])[:10]
            for k_drop, _ in oldest:
                _WEB_CACHE.pop(k_drop, None)

    # Merge web research (Parallel.ai takes priority — deeper excerpts)
    web_context = ""
    if parallel_context:
        web_context = parallel_context
    if serper_context:
        web_context += ("\n\n" if web_context else "") + serper_context
    # Cap total web context — GPT-5.5 demo key has TPM=10K so input must be tight.
    # 4000 chars ≈ ~1000 tokens of web context; corpus chunks add ~3000; system
    # prompt is ~3500. Total stays under 8K input → fits comfortably in 10K TPM.
    web_context = web_context[:4000]

    t_retrieve = time.time() - t0
    logger.info(f"[spectr_pipeline] retrieve: {len(chunks)} chunks + {len(web_context)} chars web ({t_retrieve:.2f}s)")

    # ── Stage 2: Drafter — GPT-5.5 MANDATORY ─────────────────────────
    # User mandate (Rohan meeting): GPT-5.5 Pro is the ONLY primary drafter.
    # No Llama. Qwen3-Thinking on NVIDIA NIM is the silent fallback inside the
    # retry path if 5.5 errors — orchestrator never picks anything else here.
    SUPPORTED = {"gpt-5.5"}
    drafter_model = "gpt-5.5"

    q_lower = user_query.lower()
    case_law_signals = any(s in q_lower for s in [
        "case law", "case laws", "judgment", "judgement", "high court", "supreme court",
        "constitutional", "constitutionally", "writ", "article 14", "article 32", "article 226",
        "jurisprudence", "ratio", "overruled", "precedent",
    ])

    # ── BACKGROUND-CHECK INTENT ──────────────────────────────────────
    # User asks for due-diligence on a person or entity → fire the live
    # sandbox-driven deep research (browser + IndianKanoon + MCA + court
    # records). Takes 60-120s extra; appends a separate "BACKGROUND CHECK
    # FINDINGS" block to the drafter output.
    bg_check_signals = any(s in q_lower for s in [
        "background check", "due diligence", "background of",
        "investigate ", "litigation history", "court history",
        "criminal record", "criminal history", "do a check on", "run a check",
        "check on this", "check on the", "check this entity",
        "kyc check", "company search", "director search", "promoter background",
        "track record of", "litigation profile",
    ])
    bg_check_task = await _kickoff_background_check(user_query) if bg_check_signals else None

    logger.info(
        f"[spectr_pipeline] PEAK drafter: {drafter_model} "
        f"(task={task}, cmplx={complexity}, case_law_signal={case_law_signals}, "
        f"bg_check={'yes' if bg_check_signals else 'no'})"
    )

    system_prompt, user_prompt = build_drafter_prompt(
        domain, chunks, user_query, complexity=complexity, task=task,
        web_context=web_context,
    )
    # Output budget — tuned per model to stay within the user's 40s budget.
    # Claude is more thoughtful per token; GPT-4.1 emits faster.
    if force_deep or drafter_model == MODEL_DRAFTER_TOP:
        max_out = 16000             # gpt-5.5 reasoning headroom
    elif drafter_model.startswith("claude"):
        # Claude Opus 4.6 — peak reasoning model, give it full headroom
        # to match GPT-5.5 output depth. Partner-grade memos need 2,000-4,000
        # words which requires 12K-16K tokens of output space.
        max_out = 16000
    else:
        max_out = 4000

    # 30-SECOND BUDGET — Rohan meeting. GPT-5.5 demo key has TPM=10K so we
    # MUST run effort=low to keep reasoning-token reservation under the cap
    # (medium reserves ~3K reasoning tokens, low reserves ~600).
    effort = "low"

    # ══════════════════════════════════════════════════════════════════
    # SINGLE-MODEL DRAFT — GPT-5.5 Pro mandatory, 30s budget.
    # User mandate (Rohan meeting): 5.5 only, no Llama, <30s wall-clock.
    # Council architecture is parked — runs over budget. If GPT-5.5 errors,
    # Qwen3-Thinking on NVIDIA NIM is the silent retry inside draft_memo.
    # ══════════════════════════════════════════════════════════════════

    t0 = time.time()

    # ULTRA-LONG MODE — Rohan demand: dense partner-grade research, no length
    # cap on output. GPT-5.5 capped at 4500 to fit TPM (system 4K + corpus
    # 1.5K + web 1K + user 0.5K + reasoning 0.6K + output 4.5K = 12K, just
    # over 10K). On 429 we fail over to Mistral with 8000-token budget for
    # genuinely ultra-long output (no TPM ceiling on NIM).
    draft, draft_usage = await draft_memo(
        system_prompt, user_prompt,
        model="gpt-5.5", max_tokens=4500,
        reasoning_effort=effort,  # "low" — fits 10K TPM
        cache_key=f"spectr_drafter_v3_{domain}",
    )
    usages.append(draft_usage)

    if not draft:
        # GPT-5.5 errored — fallback to Qwen3-Thinking on NIM (no TPM cap there)
        logger.warning("[spectr_pipeline] GPT-5.5 returned empty — falling back to Qwen3-Thinking via NIM")
        draft, fallback_usage = await draft_memo(
            system_prompt, user_prompt,
            model="mistralai/mistral-large-3-675b-instruct-2512", max_tokens=8000,
            reasoning_effort="medium",
            cache_key=f"spectr_drafter_v3_{domain}_fb",
        )
        usages.append(fallback_usage)
        drafter_model = "mistral-large-3-nim" if draft else "failed"
    else:
        drafter_model = "gpt-5.5"

    t_draft = time.time() - t0
    logger.info(
        f"[spectr_pipeline] DRAFT final: {len(draft.split())} words via {drafter_model} "
        f"({t_draft:.1f}s)"
    )

    # ── Stage 2.5: Append BACKGROUND CHECK FINDINGS if bg-check intent fired ──
    # The deep-research sandbox kicked off in parallel with retrieval. Wait for
    # it (capped at 90s) and append the dossier as its own labelled block.
    if bg_check_task is not None:
        try:
            bg_findings = await asyncio.wait_for(bg_check_task, timeout=90.0)
            if bg_findings:
                draft = draft.rstrip() + "\n\n---\n\n" + bg_findings
                logger.info(f"[spectr_pipeline] background check appended: {len(bg_findings.split())} words")
        except asyncio.TimeoutError:
            logger.warning("[spectr_pipeline] background check timed out at 90s — proceeding without dossier")
            draft = draft.rstrip() + "\n\n---\n\n**Background check status:** Live sandbox research is still in progress (court records, MCA, IndianKanoon scrape running >90s). The dossier will arrive shortly; the legal analysis above is independent of that pending work."
        except Exception as e:
            logger.warning(f"[spectr_pipeline] background check error: {e}")

    # Stage 3: Critic (only on force_deep — council already self-corrects)
    t0 = time.time()
    rewrote = False
    critique = {"must_fix": False, "_skipped": "council mode"}
    t_critic = time.time() - t0

    total_time = time.time() - t_overall
    cost = compute_cost_inr(usages)

    return {
        "response_text": draft,
        "classification": classification,
        "chunks_used": [{"chunk_id": c["chunk_id"], "citation": c["citation"]} for c in chunks],
        "critique": critique,
        "rewrote": rewrote,
        "timings": {
            "classify": round(t_classify, 2),
            "retrieve": round(t_retrieve, 2),
            "draft":    round(t_draft, 2),
            "critic":   round(t_critic, 2),
            "total":    round(total_time, 2),
        },
        "cost_inr": cost,
        "model_used": drafter_model,
        "usages": usages,
    }
