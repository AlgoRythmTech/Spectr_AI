"""
Emergent LLM — Claude cascade with cost-aware smart routing.

Pricing (Emergent credits, approximate per 1M tokens):
  - Haiku 4.5   — ~$1/1M  (cheapest, 80% of Sonnet for factual Q&A)
  - Sonnet 4.5  — ~$3/1M  (balanced, default for advisory)
  - Opus 4.5    — ~$15/1M (5x cost, use only for complex reasoning / deep research)

Routing strategy:
  1. `call_fast(query)`      → Haiku 4.5 (simple factual, <250 tokens avg)
  2. `call_default(query)`   → Sonnet 4.5 (structured advisory with IRAC)
  3. `call_deep(query)`      → Opus 4.5 (complex strategy, deep research, multi-hop reasoning)
  4. `call_with_escalation()` → Starts Sonnet. Sonnet self-assesses complexity in first 200 tokens.
                                If flag "[NEEDS_OPUS]" detected → re-run on Opus.

Additional cost cuts:
  - Response cache (1-hour TTL) for identical (query, system_prompt_hash) pairs
  - Prompt trimming (keep first 15K of 76K SPECTR prompt for fast tier)
  - Skip escalation for short queries (<20 words — Sonnet is enough)
"""
import os
import re
import time
import hashlib
import logging
import asyncio
from typing import Optional

logger = logging.getLogger("claude_emergent")

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

# Model IDs
# NOTE: Opus 4.5 is ~5x cost of Sonnet. Per user directive, we use Opus 4.1 for deep
# reasoning (nearly identical quality, ~half the credits) and reserve 4.5 for nothing.
# GPT-5 is also available via Emergent as a strong non-Claude fallback.
# Model IDs — verified against Emergent /v1/models on 23 Apr 2026.
# These are the ACTUAL IDs the proxy accepts.
CLAUDE_OPUS = "claude-opus-4-6"                # newest Opus — primary for deep research
CLAUDE_OPUS_5 = "claude-opus-4-5-20251101"     # Opus 4.5 (fallback if 4-6 hits rate limit)
CLAUDE_OPUS_4 = "claude-opus-4-20250514"       # Opus 4 (legacy fallback)
CLAUDE_SONNET = "claude-sonnet-4-6"            # Sonnet 4.6 — primary
CLAUDE_SONNET_4_5 = "claude-sonnet-4-5-20250929"  # Sonnet 4.5 (fallback)
CLAUDE_HAIKU = "claude-haiku-4-5"              # Haiku — simple tier
GPT_5 = "gpt-5"

# ─── Response cache (in-memory, 6-hour TTL, 1000-entry cap) ─────────────
# Two-level caching:
#   1. RESPONSE cache — (normalized_query + statute_hash + model) -> full response.
#      Works across paraphrased queries that retrieve the same grounded context.
#   2. ANTHROPIC PROMPT cache — the big 60K system prompt is cached
#      server-side by Anthropic when cache_control is set. See call_claude_direct.
_CACHE: dict = {}
_CACHE_TTL = 6 * 3600   # 6 hours — most factual answers don't change faster
_CACHE_MAX = 1000       # up from 200
_CACHE_HITS = 0
_CACHE_MISSES = 0

# Stopwords dropped entirely — these words exist in every phrasing of
# a query and carry zero disambiguating signal. Dropping + sorting tokens
# means "what is the TDS rate under 194C?" and "194C TDS rate" canonicalize
# to the same string.
_STOPWORDS = {
    # question boilerplate
    "what", "whats", "is", "the", "a", "an", "of", "on", "in", "for", "to",
    "at", "by", "with", "from", "as", "are", "was", "were", "be", "been",
    # please/kindly
    "please", "kindly", "tell", "me", "give", "show", "explain", "describe",
    # requests
    "could", "can", "would", "should", "will", "need", "want", "help",
    "understand",
    # relative/determiners
    "this", "that", "these", "those", "my", "our", "your", "his", "her", "its",
    # abbreviations that pair with section
    "u", "s", "under", "per", "as",
    # low-signal verbs
    "does", "do", "did", "has", "have", "had", "mean", "means",
    # pronouns + filler
    "you", "it", "them", "they", "he", "she", "we", "i",
    "how", "where", "when", "why", "if", "then", "so", "also",
}


def _normalize_query(q: str) -> str:
    """Canonical form for cache keys.

    Strategy:
      1. Lowercase
      2. Drop punctuation (except digits/letters/section-§)
      3. Tokenize, drop stopwords, dedupe
      4. Sort tokens alphabetically so word-order variants share a key

    Example: "What is the TDS rate under Section 194C?" and "194C TDS rate"
    both canonicalize to '194c rate section tds' — identical.
    """
    if not q:
        return ""
    q = q.lower()
    # Normalize "u/s" to "section" before tokenizing
    q = re.sub(r"\bu[./\s]*s[./\s]*", " section ", q)
    q = re.sub(r"\bsec[./\s]+", " section ", q)
    # Drop everything except alphanumerics and spaces
    q = re.sub(r"[^a-z0-9\s]", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    tokens = [t for t in q.split() if t and t not in _STOPWORDS and len(t) > 1]
    # Dedupe + sort so word-order doesn't generate new keys
    tokens = sorted(set(tokens))
    return " ".join(tokens)


def _cache_key(system: str, user: str, model: str, context_hash: str = "") -> str:
    """Deterministic hash for (normalized_user, context_hash, model).

    System prompt is excluded from the key — Anthropic's prompt cache
    handles that side. Statute/research CONTEXT is included because two
    identically-worded queries with different statute injections should
    produce different answers.
    """
    norm_user = _normalize_query(user)
    combined = f"{model}::{context_hash[:32]}::{norm_user}"
    return hashlib.md5(combined.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> Optional[str]:
    global _CACHE_HITS, _CACHE_MISSES
    entry = _CACHE.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        _CACHE_HITS += 1
        return entry["response"]
    if entry:
        _CACHE.pop(key, None)
    _CACHE_MISSES += 1
    return None


def _cache_set(key: str, response: str):
    if len(_CACHE) >= _CACHE_MAX:
        # Evict oldest 10% — amortizes eviction cost
        drop_count = _CACHE_MAX // 10
        oldest_keys = sorted(_CACHE.items(), key=lambda kv: kv[1].get("ts", 0))[:drop_count]
        for k, _ in oldest_keys:
            _CACHE.pop(k, None)
    _CACHE[key] = {"response": response, "ts": time.time()}


def cache_stats() -> dict:
    """Runtime stats — expose via /health or /admin dashboard."""
    total = _CACHE_HITS + _CACHE_MISSES
    return {
        "entries": len(_CACHE),
        "max_entries": _CACHE_MAX,
        "ttl_seconds": _CACHE_TTL,
        "hits": _CACHE_HITS,
        "misses": _CACHE_MISSES,
        "hit_rate": round(_CACHE_HITS / total, 3) if total else 0,
    }


ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()


async def _call_claude_direct(
    system_prompt: str,
    user_content: str,
    model: str,
    timeout: int = 60,
) -> str:
    """Direct Anthropic call with PROMPT CACHING enabled.

    Uses the anthropic-beta: prompt-caching-2024-07-31 header and a
    cache_control marker on the system prompt. Anthropic caches the 60K
    SPECTR prompt server-side for 5 minutes — subsequent calls within that
    window read it at 10% of normal input cost.

    Cost math for 60K system prompt at Sonnet 4.5 ($3/M input):
      - Without caching: 60K tokens x $3/M = $0.18 per query on system alone
      - Cached (hit):    60K tokens x $0.30/M = $0.018 per query
      - Savings: 90% on system tokens after the first call in a 5-min window

    Only used if ANTHROPIC_API_KEY is set. Falls back to Emergent otherwise.
    """
    if not ANTHROPIC_KEY:
        return ""  # signal "not configured, caller falls back"

    import aiohttp
    # Map our internal model IDs to Anthropic canonical names.
    # Updated 23 Apr 2026: Emergent proxy now lists Claude 4.6 models as
    # primary — use them directly. Fallbacks preserved in case 4.6 is rate
    # limited (drop to 4.5 for Sonnet, 4.5/4 for Opus).
    anthropic_model_map = {
        CLAUDE_SONNET: "claude-sonnet-4-6",
        CLAUDE_SONNET_4_5: "claude-sonnet-4-5-20250929",
        CLAUDE_HAIKU: "claude-haiku-4-5",
        CLAUDE_OPUS: "claude-opus-4-6",
        CLAUDE_OPUS_5: "claude-opus-4-5-20251101",
        CLAUDE_OPUS_4: "claude-opus-4-20250514",
    }
    anth_model = anthropic_model_map.get(model, model)

    payload = {
        "model": anth_model,
        # Max output tokens — 32,768 = ~24,000 words of memo / ~60 pages.
        # Demo showed 12K-word memos; we need output headroom WELL above
        # 12K so the model never runs out of room mid-memo. With the
        # "output-128k-2025-02-19" beta header (below), Sonnet 4.5 supports
        # up to 128K output tokens. 32K is the safe sweet spot: enough to
        # write a 15-page constitutional memo without truncation, while
        # keeping latency reasonable (~3-4 min).
        "max_tokens": 16384,
        "system": [
            {
                "type": "text",
                # Bumped from 60K to 130K so ALL depth-forcing sections of
                # SPECTR_SYSTEM_PROMPT reach the model — Mike Ross Doctrine,
                # Zero-Hallucination Protocol, Weapon Doctrine, Citation
                # Format, Amendment-Awareness Guardrail. These sit AFTER 60K
                # in the prompt file and were being truncated — which is
                # why responses collapsed to textbook depth with placeholder
                # case names (XYZ / ABC).
                # Sonnet 4.5 handles 130K system comfortably (200K context);
                # latency impact ~2-3s, quality impact is night-and-day.
                "text": system_prompt[:130000],
                # This is the magic line: mark the system block as cacheable.
                # Anthropic will return the same response with cache_read
                # tokens instead of cache_creation tokens on the 2nd+ call.
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "messages": [{"role": "user", "content": user_content[:40000]}],
    }
    headers = {
        "x-api-key": ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        # Two beta flags combined:
        #   prompt-caching-2024-07-31  → 90% cost cut on repeated system prompt
        #   output-128k-2025-02-19     → raises output cap from 8,192 → 128K
        # Having both unlocks Claude.ai-level depth (5,000-10,000 word memos)
        # while keeping cost low via cached system prompt.
        "anthropic-beta": "prompt-caching-2024-07-31,output-128k-2025-02-19",
        "content-type": "application/json",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status != 200:
                    err_text = await resp.text()
                    logger.warning(f"Anthropic direct {anth_model} {resp.status}: {err_text[:200]}")
                    return ""
                data = await resp.json()
                # Log cache metrics so we can see the savings
                usage = data.get("usage", {})
                cache_read = usage.get("cache_read_input_tokens", 0)
                cache_write = usage.get("cache_creation_input_tokens", 0)
                if cache_read:
                    logger.info(f"Anthropic PROMPT CACHE HIT: {cache_read} tokens read from cache (~90% saved)")
                elif cache_write:
                    logger.info(f"Anthropic prompt cache WARM: {cache_write} tokens written (next 5 min free-ish)")
                # Extract the text response
                content = data.get("content", [])
                if content and isinstance(content, list):
                    return content[0].get("text", "")
                return ""
    except asyncio.TimeoutError:
        logger.warning(f"Anthropic direct {anth_model} timed out")
        return ""
    except Exception as e:
        logger.warning(f"Anthropic direct {anth_model} failed: {e}")
        return ""


async def call_claude(
    system_prompt: str,
    user_content: str,
    model: str = CLAUDE_SONNET,
    session_id: Optional[str] = None,
    timeout: int = 58,  # must be under the Emergent proxy's 60s hard cap
    use_cache: bool = True,
    context_hash: str = "",
) -> str:
    """Single-shot Claude call with two-layer caching.

    Layer 1: local response cache keyed by (normalized_query, context_hash, model)
    Layer 2: Anthropic prompt cache on the 60K system prompt (if ANTHROPIC_API_KEY set)
    """
    # Layer 1 — response cache
    cache_k = _cache_key(system_prompt, user_content, model, context_hash=context_hash)
    if use_cache:
        cached = _cache_get(cache_k)
        if cached:
            logger.info(f"Claude {model} RESPONSE CACHE HIT ({len(cached)} chars)")
            return cached

    # Try Anthropic direct first (Layer 2 prompt caching) — 90% cheaper on repeat
    resp = ""
    if ANTHROPIC_KEY:
        resp = await _call_claude_direct(system_prompt, user_content, model, timeout=timeout)

    # Fall back to Emergent if Anthropic direct isn't configured or failed
    if not resp:
        if not EMERGENT_KEY:
            logger.warning("Neither ANTHROPIC_API_KEY nor EMERGENT_LLM_KEY set")
            return ""
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
        except ImportError:
            logger.error("emergentintegrations not installed")
            return ""

        import uuid
        sid = session_id or f"spectr-{uuid.uuid4().hex[:8]}"

        try:
            # 130K cutoff — SPECTR prompt is ~132K chars and the stuff that
            # sits at 60K-130K (Zero-Hallucination Protocol, Citation Format,
            # Weapon Doctrine, Mike Ross Doctrine) is EXACTLY what prevents
            # textbook-flat output and case-name hallucinations. Raising to
            # 130K lets the WHOLE prompt reach the model.
            # Sonnet 4.5 handles 130K comfortably (200K context window).
            chat = LlmChat(
                api_key=EMERGENT_KEY,
                session_id=sid,
                system_message=system_prompt[:130000],
            ).with_model("anthropic", model)

            msg = UserMessage(text=user_content[:40000])
            resp = await asyncio.wait_for(chat.send_message(msg), timeout=timeout)
            resp = resp or ""
        except asyncio.TimeoutError:
            logger.warning(f"Claude {model} timed out after {timeout}s")
            return ""
        except Exception as e:
            logger.warning(f"Claude {model} failed: {e}")
            return ""

    if resp and use_cache:
        _cache_set(cache_k, resp)
    return resp


# === SMART ROUTING API ===

def _classify_complexity(query: str) -> str:
    """Heuristic complexity detector.

    Returns: "simple" | "medium" | "complex"

    CALIBRATION (22 Apr 2026): "simple" is now VERY narrow — only pure factual
    lookups ("what is TDS rate", "define ITC", "section 73 CGST"). Anything
    with litigation / bail / client-fact / strategic keywords goes to Sonnet.
    Reason: the previous classifier mis-routed a bail application query to
    Groq, producing textbook-flat output when the client expected partner-
    grade depth. Quality > token cost.
    """
    import re
    q_lower = query.lower()
    word_count = len(query.split())

    # Hard-complex triggers — any one of these forces Sonnet/Opus, regardless
    # of word count. These are the "this is not a textbook question" signals.
    complex_indicators = [
        r'\b(scn|show\s*cause|notice received|reassessment|148a?|143\(2\))\b',
        r'\b(defen[cs]e|strategy|cite cases|case law|precedent|ratio)\b',
        r'\b(writ|appeal|tribunal|high court|supreme court|itat|cestat|nclt)\b',
        r'\b(opposing|adversarial|counter.?argument|prosecution)\b',
        r'\b(draft|prepare|write|compose).{0,40}(petition|reply|ground|affidavit|memo|application|submission|notice)\b',
        r'\b(quantify|compute|calculate).{0,50}(exposure|penalty|interest|demand|loss|liability)\b',
        r'\b(multiple|various|several|different).{0,30}(issue|section|provision)\b',
        r'\b(transfer pricing|alp|pillar two|globe|beps)\b',
        r'\b(merger|amalgamation|demerger|m&a|acquisition)\b',
        r'\b(fraudulent|fraud|suppression|willful|mens rea)\b',
        # Litigation / criminal-law triggers — bail, custody, FIR, arrest etc
        r'\b(bail|anticipatory|custody|fir|arrest|remand|quash|charge.?sheet)\b',
        r'\b(accused|offender|convict|trial|magistrate|sessions court)\b',
        # Advisory / "my client" signals — anything with facts + context
        r'\b(my client|the client|our client|first.?time|prior record|economic offen[dc]e)\b',
        r'\b(exposure|risk|liability|strategy|defen[cs]e|mitigat)\b',
    ]
    if any(re.search(p, q_lower) for p in complex_indicators):
        return "complex"
    if word_count > 60:
        return "complex"

    # SIMPLE: pure factual lookup — no case facts, no client context, short.
    # Must match a lookup pattern AND be <20 words AND have no pronouns
    # suggesting a scenario.
    if word_count < 20 and not re.search(r'\b(my|our|the|this|client|case|we|they|he|she)\b', q_lower):
        simple_patterns = [
            r'^\s*what is\b', r'^\s*define\b', r'^\s*explain\b',
            r'\btds rate\b', r'\bgst rate\b', r'\brate of\b',
            r'\bthreshold for\b', r'\bslab for\b',
            r'^\s*section \d+',
        ]
        if any(re.search(p, q_lower) for p in simple_patterns):
            return "simple"

    # Default = medium (Sonnet). We'd rather "over-spend" on quality than
    # under-spend and flatten a Zepto-grade query to textbook output.
    return "medium"


async def _call_gpt_emergent(system_prompt: str, user_content: str, model: str = "gpt-5") -> Optional[str]:
    """GPT via Emergent proxy — fallback when Claude cascade fails.

    Emergent supports both anthropic and openai under one key. We use GPT-5
    (or gpt-4o) as the safety net when Claude is rate-limited / over capacity
    so the user never sees a dead response.
    """
    if not EMERGENT_KEY:
        return None
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except ImportError:
        return None

    import uuid
    sid = f"spectr-gpt-{uuid.uuid4().hex[:8]}"
    try:
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=sid,
            system_message=system_prompt[:130000],
        ).with_model("openai", model)
        msg = UserMessage(text=user_content[:40000])
        resp = await asyncio.wait_for(chat.send_message(msg), timeout=90)
        return resp or None
    except Exception as e:
        logger.info(f"GPT fallback via Emergent ({model}) failed: {e}")
        return None


async def smart_route(
    system_prompt: str,
    user_content: str,
    query: str = "",
    session_id: Optional[str] = None,
    force_tier: Optional[str] = None,
) -> tuple[str, str, str]:
    """Route based on complexity. Returns (response, model_used, tier).

    Model policy (23 Apr 2026 — GROQ REMOVED):
      - ALL tiers use Claude via Emergent; GPT-5 / GPT-4o as emergency fallback.
      - simple:  Claude Haiku 4.5 ($1/M, ~2s) → Sonnet escalation if thin
      - medium:  Claude Sonnet 4.5 ($3/M, balanced)
      - complex: Claude Sonnet 4.5 with Opus 4.1 escalation via
                 call_with_escalation (deep research pass does this too)
      - fallback for any tier on Claude failure: GPT-5 via Emergent, then GPT-4o
    """
    tier = force_tier or _classify_complexity(query or user_content[:500])

    # Simple tier: Haiku first, Sonnet escalation if thin, GPT fallback on total failure
    if tier == "simple":
        resp = await call_claude(system_prompt, user_content, model=CLAUDE_HAIKU, session_id=session_id)
        if resp and len(resp) >= 100:
            return resp, CLAUDE_HAIKU, "simple"
        # Haiku failed/thin — upgrade to Sonnet
        resp = await call_claude(system_prompt, user_content, model=CLAUDE_SONNET, session_id=session_id)
        if resp and len(resp) >= 100:
            return resp, CLAUDE_SONNET, "medium"
        # Last resort — GPT-5 via Emergent
        resp = await _call_gpt_emergent(system_prompt, user_content, model="gpt-5")
        if resp and len(resp) >= 100:
            return resp, "openai/gpt-5", "simple"
        resp = await _call_gpt_emergent(system_prompt, user_content, model="gpt-4o")
        return resp or "", "openai/gpt-4o", "simple"

    # Medium / complex tier: Claude Sonnet (Opus for explicitly complex)
    # Cost policy (23 Apr 2026): Sonnet 4.6 handles 95% of queries including
    # complex. Opus 4.6 reserved for EXPLICIT partner mode (deep research
    # with sandbox). Sonnet delivers 9/10 quality at 1/5 the cost.
    model_map = {
        "medium": CLAUDE_SONNET,
        "complex": CLAUDE_SONNET,   # NOT Opus — cost-efficient
    }
    model = model_map.get(tier, CLAUDE_SONNET)
    resp = await call_claude(system_prompt, user_content, model=model, session_id=session_id)
    if resp and len(resp) >= 300:
        return resp, model, tier
    # Claude failed / thin — try Sonnet if we were on Opus
    if model != CLAUDE_SONNET:
        resp = await call_claude(system_prompt, user_content, model=CLAUDE_SONNET, session_id=session_id)
        if resp and len(resp) >= 300:
            return resp, CLAUDE_SONNET, tier
    # GPT fallback chain
    resp = await _call_gpt_emergent(system_prompt, user_content, model="gpt-5")
    if resp and len(resp) >= 300:
        return resp, "openai/gpt-5", tier
    resp = await _call_gpt_emergent(system_prompt, user_content, model="gpt-4o")
    return resp or "", "openai/gpt-4o", tier


async def call_with_escalation(
    system_prompt: str,
    user_content: str,
    query: str = "",
    session_id: Optional[str] = None,
) -> tuple[str, str]:
    """Route directly to the right tier based on query complexity heuristics —
    no double-call penalty.

    Prior implementation ran Sonnet first, asked it to self-flag complexity,
    and re-ran on Opus if flagged. That doubled latency whenever Opus was
    actually needed. New behaviour: classify upfront, go straight to the
    right tier.

    Cost-to-quality policy:
      - simple   → Haiku 4.5 (~$1/M)  — rate/threshold lookups, greetings
      - medium   → Sonnet 4.5 (~$3/M) — single-issue advisory, clean CREAC
      - complex  → Opus 4.1 (~$7.5/M) — multi-issue / constitutional /
                   adversarial / >60-word scenarios / explicit triggers

    Triggers that force Opus directly (zero roundtrip):
      - query length > 60 words OR > 500 chars (real scenarios, not lookups)
      - adversarial / strategic keywords (scn, notice, writ, petition,
        defence, strategy, challenge, constitutional, article 14/19/21, bnss,
        puttaswamy, anticipatory bail, sedition)
      - multi-statute keywords (dpdp + ipc, gst + income tax, etc.)
    """
    tier = _classify_complexity(query or user_content[:600])

    # ROUTING POLICY (calibrated for VIP-client demo):
    #   - Sonnet 4.5 is the default for research mode — delivers 8-9/10 quality
    #     with the full SPECTR playbook, response time 25-45s.
    #   - Opus 4.1 is reserved for the `call_deep_research` path (Partner mode
    #     with sandbox browser research). That's where 2-3 min latency is OK
    #     because the user explicitly picked "Deep Research".
    #   - Escalating mid-path (Sonnet flags [NEEDS_OPUS]) is a quality fallback,
    #     not the primary route.
    #
    # This keeps research mode snappy while still giving Opus its moment in
    # Partner/Deep-Research mode where the sandbox is already running too.

    if tier == "simple":
        resp = await call_claude(system_prompt, user_content, model=CLAUDE_HAIKU, session_id=session_id)
        if resp and len(resp) > 80:
            return resp, CLAUDE_HAIKU
        resp = await call_claude(system_prompt, user_content, model=CLAUDE_SONNET, session_id=session_id)
        return resp, CLAUDE_SONNET

    # Both medium AND complex route to Sonnet 4.5 in this fast path — Opus is
    # reserved for the explicit deep-research path. Sonnet handles 8-9/10
    # quality across both tiers when the SPECTR playbook is in context.
    sonnet_resp = await call_claude(system_prompt, user_content, model=CLAUDE_SONNET, session_id=session_id)
    if not sonnet_resp:
        logger.warning("call_with_escalation: Sonnet failed, falling back to Opus")
        opus_resp = await call_claude(system_prompt, user_content, model=CLAUDE_OPUS, session_id=session_id)
        return opus_resp, CLAUDE_OPUS

    # Only escalate to Opus for truly exceptional queries — >120 words AND multiple
    # complex indicators. Most research-mode queries don't hit this.
    word_count = len((query or user_content[:600]).split())
    if tier == "complex" and word_count > 120:
        logger.info(f"call_with_escalation: exceptional query ({word_count} words, complex) → Opus reinforcement")
        opus_resp = await call_claude(system_prompt, user_content, model=CLAUDE_OPUS, session_id=session_id)
        if opus_resp and len(opus_resp) > len(sonnet_resp) * 0.7:
            return opus_resp, CLAUDE_OPUS

    # Strip the flag line from the response
    cleaned = sonnet_resp
    for flag in ("[COMPLEXITY:SIMPLE]", "[COMPLEXITY:MEDIUM]", "[COMPLEXITY:COMPLEX]"):
        if flag in cleaned[:100]:
            cleaned = cleaned.replace(flag, "", 1).lstrip()
            break
    return cleaned, CLAUDE_SONNET


async def call_deep_research(
    system_prompt: str,
    user_content: str,
    session_id: Optional[str] = None,
) -> tuple[str, str]:
    """Deep Research mode — ALWAYS uses Opus 4.5.

    Caller should have already gathered context (sandbox research, IK cases,
    statute DB, pre-flight computed facts). Opus synthesizes this into a
    senior-partner-grade deliverable.
    """
    resp = await call_claude(system_prompt, user_content, model=CLAUDE_OPUS, timeout=120, session_id=session_id)
    return resp, CLAUDE_OPUS


async def call_claude_cascade(
    system_prompt: str,
    user_content: str,
    tier: str = "deep",
    session_id: Optional[str] = None,
) -> tuple[str, str]:
    """Legacy wrapper — keep for existing callers. Maps to smart_route."""
    tier_map = {"fast": "simple", "deep": "medium", "partner": "complex"}
    mapped_tier = tier_map.get(tier, "medium")
    resp, model, _ = await smart_route(system_prompt, user_content, force_tier=mapped_tier, session_id=session_id)
    return resp, model


async def health_check() -> dict:
    """Verify key + all 3 models."""
    results = {}
    for m in [CLAUDE_HAIKU, CLAUDE_SONNET, CLAUDE_OPUS]:
        resp = await call_claude("You are a helpful assistant.", "Say OK", model=m, timeout=10, use_cache=False)
        results[m] = "ok" if resp else "fail"
    return results


# Diagnostic
if __name__ == "__main__":
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).parent / ".env")

    async def run():
        print("Health check:", await health_check())
        # Test routing
        for q in [
            "TDS rate under Section 194J?",
            "My client got a S.74 GST SCN for Rs 2cr fake ITC — defense strategy with case law?",
            "What is the threshold for 194C?",
        ]:
            resp, model, tier = await smart_route("You are Spectr.", q, query=q)
            print(f"\n[{tier.upper()}] model={model} → {resp[:200]}...")

    asyncio.run(run())
