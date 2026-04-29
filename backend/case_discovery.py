"""
Case Discovery Engine — Multi-angle semantic case retrieval.

The problem: Claude does semantic retrieval from training memory. Our keyword IK search
loses to Claude for "find cases in X context" queries because IK just matches words.

The fix: Generate MULTIPLE search angles for the same legal issue, hit every source
(IK + Serper + Scholar) in parallel, fetch full judgment text, and ground the LLM
in actual case reasoning — not just headlines.

Architecture:
  Query → issue extraction → N semantic angles → parallel source hits → dedupe →
  court hierarchy ranking → full text fetch (top 5) → ratio summary → LLM context

This beats Claude because:
- Claude has HEADNOTES from training (summary, not judgment text)
- We have FULL JUDGMENT TEXT fetched live (actual ratio, actual reasoning)
- Claude's cutoff is fixed; we have 2025-2026 cases
- Every case we return has a clickable URL — Claude can't give that
"""
import re
import os
import json
import asyncio
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger("case_discovery")

IK_API_KEY = os.environ.get("INDIANKANOON_API_KEY", "")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")

# ==================== ISSUE EXTRACTION ====================

# Map common legal contexts → search angle templates
# Each angle is a different way of finding the same legal principle
_CONTEXT_ANGLE_MAP = {
    # GST ITC
    r'(?i)itc.*(?:denied|disallowed|reversed|mismatch).*supplier.*(?:not\s+paid|defaulted|fake)': [
        "ITC denied buyer penalty supplier default India judgment",
        "Section 16(2)(c) CGST supplier paid ITC",
        "bona fide purchaser ITC GST buyer cannot be penalized",
        "GSTR-2A mismatch ITC denial judgment India",
        "D.Y. Beathel Bharti Airtel ITC supplier default",
    ],
    r'(?i)itc.*(?:16\(4\)|time\s+limit|deadline|november)': [
        "Section 16(4) CGST Act time limit ITC extension",
        "belated GSTR-3B ITC availment India judgment",
        "Finance Act 2022 Section 16(4) November 30 deadline",
    ],
    r'(?i)rule\s+36\s*\(\s*4\s*\)': [
        "Rule 36(4) CGST ITC GSTR-2B restriction India",
        "provisional credit 20% 10% 5% Rule 36(4) amendment",
        "January 2022 Rule 36(4) abolished judgment",
    ],

    # Reassessment
    r'(?i)reassessment.*(?:change\s+of\s+opinion|tangible\s+material|new\s+material)': [
        "Section 147 148 change of opinion Kelvinator",
        "tangible material reopening assessment India",
        "live link material escaped income reassessment",
    ],
    r'(?i)(?:148A|ashish\s+agarwal|old\s+regime.*reassessment)': [
        "Section 148A procedural Ashish Agarwal reassessment",
        "Union of India Ashish Agarwal 2022 Supreme Court",
        "Section 148 new regime TOLA extension judgment",
    ],

    # GST SCN
    r'(?i)(?:section\s+73|s\.73).*(?:pre.*consultation|rule\s+142)': [
        "Rule 142(1A) pre-consultation GST Section 73 mandatory",
        "DGGI DGST pre-SCN consultation India judgment",
    ],
    r'(?i)(?:section\s+74|s\.74).*(?:fraud|suppression|willful)': [
        "Section 74 CGST fraud suppression burden of proof",
        "Bhagwati Steel Cast Section 74 GST Bombay High Court",
        "invocation Section 74 demand for fraud proof",
    ],

    # DIN
    r'(?i)(?:din|document\s+identification).*(?:notice|missing|absent)': [
        "DIN document identification number notice void ab initio",
        "CBIC Circular 128/47/2019 DIN GST",
        "CBDT Circular 19/2019 DIN notice invalid",
        "Brandix India Apparel DIN GST notice",
    ],

    # TDS
    r'(?i)(?:40\(a\)\(ia\)|disallowance|tds.*default)': [
        "Section 40(a)(ia) disallowance proviso payee tax paid",
        "30% disallowance TDS deducted not deposited",
        "Form 26A certificate Section 201 defaulter",
    ],
    r'(?i)(?:195|fts|royalty|tds.*non\s*resident)': [
        "Section 195 TDS non-resident royalty fees for technical services",
        "GE India Technology 2010 TDS Section 195",
        "Explanation 5 6 Section 9 Finance Act 2020 royalty",
    ],

    # Transfer Pricing
    r'(?i)(?:transfer\s+pricing|alp|arm.?s?\s*length|tp\s+adjustment)': [
        "transfer pricing ALP arm length India ITAT",
        "comparables selection most appropriate method 92C",
        "range concept arithmetic mean transfer pricing",
        "safe harbour rules Section 92C Rule 10TD India",
    ],

    # Criminal
    r'(?i)(?:bail|anticipatory|482\s+crpc|quashing|fir)': [
        "anticipatory bail Section 438 CrPC 482 grounds",
        "FIR quashing inherent powers 482 Bhajan Lal",
        "Section 482 CrPC Section 528 BNSS quashing India",
    ],

    # FEMA
    r'(?i)(?:fema|fdi|odi|ecb|lrs)': [
        "FEMA compounding Section 13 India judgment",
        "LRS $250000 capital account FEMA compliance",
        "FCGPR ODI late filing FEMA penalty",
    ],

    # Companies Act
    r'(?i)(?:section\s+188|related\s+party|rpt|arms.?\s+length.*company)': [
        "Section 188 related party transaction Companies Act",
        "arm's length ordinary course of business RPT",
        "Section 177 audit committee RPT approval",
    ],

    # Corporate — IBC
    r'(?i)(?:cirp|ibc|insolvency|section\s+(?:7|9|10))': [
        "Section 7 IBC financial creditor CIRP limitation",
        "Section 9 IBC operational creditor pre-existing dispute",
        "Section 10A IBC COVID bar insolvency India",
    ],

    # Capital gains
    r'(?i)(?:capital\s+gain|ltcg|stcg|indexation|54|54F|54EC)': [
        "LTCG indexation 112A 12.5% Finance Act 2024",
        "Section 54 54F capital gains exemption residential property",
        "Section 50 depreciable asset capital gain",
    ],
}


def extract_semantic_angles(query: str) -> list[str]:
    """Generate 3-5 semantic search queries from the legal issue.

    Uses context patterns + extracted sections + extracted parties to build
    multiple search angles that approach the same issue from different angles.
    """
    angles = []
    q_lower = query.lower()

    # Match context patterns
    for pattern, template_angles in _CONTEXT_ANGLE_MAP.items():
        if re.search(pattern, q_lower):
            angles.extend(template_angles)

    # Extract section references and add angles
    section_pattern = re.compile(
        r'(?:Section|Sec\.|u/s)\s*(\d+[A-Z]*(?:\([a-z0-9]+\))*)',
        re.IGNORECASE
    )
    sections = list(set(m.group(1) for m in section_pattern.finditer(query)))
    for sec in sections[:3]:
        angles.append(f"Section {sec} interpretation India judgment")
        angles.append(f"Section {sec} latest Supreme Court High Court")

    # If no specific angles matched, use raw query with legal boilerplate
    if not angles:
        # Extract key terms (nouns, not function words)
        stop = {"the", "a", "an", "is", "are", "was", "were", "of", "for", "to", "in", "on", "at", "by", "with", "from", "as", "and", "or", "but", "if", "then", "when", "which", "that", "this", "these", "those", "my", "your", "his", "her", "our", "their", "client", "case", "what", "how", "why", "can", "would", "should"}
        words = [w for w in re.findall(r'\b[a-zA-Z]+\b', query) if len(w) > 3 and w.lower() not in stop]
        key_terms = " ".join(words[:6])
        angles.append(f"{key_terms} India judgment")
        angles.append(f"{key_terms} case law India Supreme Court")
        angles.append(f"{key_terms} ruling precedent")

    # Dedupe while preserving order
    seen = set()
    unique_angles = []
    for a in angles:
        if a.lower() not in seen:
            seen.add(a.lower())
            unique_angles.append(a)

    return unique_angles[:6]  # Cap at 6 angles to avoid over-searching


# ==================== COURT HIERARCHY RANKING ====================

_COURT_RANK = {
    "supreme court": 100,
    "sci": 100,
    "high court": 80,
    "bombay hc": 80, "delhi hc": 80, "madras hc": 80, "calcutta hc": 80, "allahabad hc": 80,
    "nclat": 70,
    "nclt": 60,
    "itat": 55,
    "cestat": 55,
    "tribunal": 40,
    "cit(a)": 30,
    "authority": 25,
}


def _court_rank(title: str, docsource: str = "") -> int:
    """Assign priority rank to a case based on court."""
    combined = f"{title} {docsource}".lower()
    for keyword, rank in _COURT_RANK.items():
        if keyword in combined:
            return rank
    return 10  # Unknown court — low rank


def _extract_year(title: str) -> int:
    """Extract year from case title for recency weighting."""
    m = re.search(r'\b(19\d{2}|20\d{2})\b', title)
    if m:
        return int(m.group(1))
    return 0


# ==================== PARALLEL SEARCH ====================

async def _search_ik(session: aiohttp.ClientSession, query: str, top_k: int = 5) -> list[dict]:
    """Single IK search — return structured results."""
    if not IK_API_KEY:
        return []
    try:
        async with session.post(
            "https://api.indiankanoon.org/search/",
            headers={"Authorization": f"Token {IK_API_KEY}"},
            data={"formInput": query, "pagenum": 0},
            timeout=aiohttp.ClientTimeout(total=6),
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            docs = data.get("docs", [])
            results = []
            for d in docs[:top_k]:
                title_raw = d.get("title", "")
                title = re.sub(r'<[^>]+>', '', title_raw)
                results.append({
                    "source": "ik",
                    "title": title,
                    "doc_id": d.get("tid", ""),
                    "url": f"https://indiankanoon.org/doc/{d.get('tid', '')}/",
                    "headline": d.get("headline", "")[:400],
                    "docsource": d.get("docsource", ""),
                    "year": _extract_year(title),
                    "court_rank": _court_rank(title, d.get("docsource", "")),
                })
            return results
    except Exception as e:
        logger.warning(f"IK search failed for '{query}': {e}")
        return []


async def _search_serper_scholar(session: aiohttp.ClientSession, query: str) -> list[dict]:
    """Serper Scholar search — academic/authoritative results."""
    if not SERPER_API_KEY:
        return []
    try:
        async with session.post(
            "https://google.serper.dev/scholar",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": 5, "gl": "in"},
            timeout=aiohttp.ClientTimeout(total=6),
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            organic = data.get("organic", [])
            results = []
            for o in organic[:5]:
                title = o.get("title", "")
                results.append({
                    "source": "scholar",
                    "title": title,
                    "url": o.get("link", ""),
                    "headline": o.get("snippet", "")[:400],
                    "year": _extract_year(title + " " + o.get("snippet", "")),
                    "court_rank": _court_rank(title),
                })
            return results
    except Exception as e:
        logger.warning(f"Serper Scholar failed for '{query}': {e}")
        return []


async def _search_serper_web(session: aiohttp.ClientSession, query: str) -> list[dict]:
    """Serper web search restricted to authoritative legal domains."""
    if not SERPER_API_KEY:
        return []
    try:
        # Add site filter for authoritative sources
        legal_sites = "site:indiankanoon.org OR site:scconline.com OR site:livelaw.in OR site:barandbench.com OR site:main.sci.gov.in OR site:taxmann.com OR site:itatonline.org"
        full_query = f"{query} {legal_sites}"
        async with session.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": full_query, "num": 5, "gl": "in"},
            timeout=aiohttp.ClientTimeout(total=6),
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            organic = data.get("organic", [])
            results = []
            for o in organic[:5]:
                title = o.get("title", "")
                link = o.get("link", "")
                results.append({
                    "source": "serper_web",
                    "title": title,
                    "url": link,
                    "headline": o.get("snippet", "")[:400],
                    "year": _extract_year(title + " " + o.get("snippet", "")),
                    "court_rank": _court_rank(title),
                    "domain": link,
                })
            return results
    except Exception as e:
        logger.warning(f"Serper web failed for '{query}': {e}")
        return []


async def _fetch_ik_full_text(session: aiohttp.ClientSession, doc_id: str, max_chars: int = 6000) -> str:
    """Fetch full judgment text from IK."""
    if not IK_API_KEY or not doc_id:
        return ""
    try:
        async with session.post(
            f"https://api.indiankanoon.org/doc/{doc_id}/",
            headers={"Authorization": f"Token {IK_API_KEY}"},
            data={"maxcites": 0, "maxcitedby": 0},
            timeout=aiohttp.ClientTimeout(total=8),
        ) as resp:
            if resp.status != 200:
                return ""
            data = await resp.json()
            doc_text = data.get("doc", "")
            # Strip HTML
            clean = re.sub(r'<[^>]+>', '', doc_text)
            # Collapse whitespace
            clean = re.sub(r'\s+', ' ', clean).strip()
            return clean[:max_chars]
    except Exception as e:
        logger.warning(f"IK fetch doc {doc_id} failed: {e}")
        return ""


# ==================== DEDUPE + RANK ====================

def _dedupe_cases(all_results: list[dict]) -> list[dict]:
    """Deduplicate results by normalized title. Keep the one with highest court rank."""
    by_key = {}
    for r in all_results:
        # Normalize title: lowercase, strip parties, keep core names
        title = r.get("title", "").lower()
        # Extract first 2 substantive words from each party
        parties = re.split(r'\s+v\.?\s+|\s+vs\.?\s+|\s+versus\s+', title)
        if len(parties) >= 2:
            p1 = " ".join(re.findall(r'\b[a-z]+\b', parties[0])[:3])
            p2 = " ".join(re.findall(r'\b[a-z]+\b', parties[1])[:3])
            key = f"{p1}|{p2}"
        else:
            key = " ".join(re.findall(r'\b[a-z]+\b', title)[:5])

        existing = by_key.get(key)
        if not existing or r.get("court_rank", 0) > existing.get("court_rank", 0):
            by_key[key] = r
    return list(by_key.values())


def _rank_cases(cases: list[dict]) -> list[dict]:
    """Rank by court hierarchy + recency."""
    return sorted(cases, key=lambda c: (
        -c.get("court_rank", 0),      # Higher court first
        -c.get("year", 0),            # Recent first (within same court)
        c.get("title", ""),
    ))


# ==================== LLM-BASED CASE NAME GENERATION ====================

# Prompt for LLM: generate IK SEARCH QUERIES (not case names — those hallucinate)
# The LLM is reliable at extracting legal concepts; it's unreliable at naming specific cases.
# By having it generate search queries, we leverage its reasoning without trusting its memory.
_SEARCH_QUERY_PROMPT = """You are an Indian legal research expert. Given a legal issue, generate 6-8 DIVERSE search queries to find relevant cases on IndianKanoon and Google.

Output ONLY a JSON array. No markdown. No explanation. Format:
[
  {"query": "search term 1", "angle": "what angle this covers"},
  {"query": "search term 2", "angle": "different angle"},
  ...
]

RULES:
- Each query should be 4-10 words that capture a DIFFERENT legal angle/principle
- Mix specific legal terms with plain language
- Include at least one query with a section reference if applicable
- Include at least one query aimed at adversarial/opposing cases (what department argues)
- Include at least one query for recent 2024-2026 developments
- DO NOT output case names — just search queries
- Think: what would an expert type into a legal search engine?

Example (for GST ITC mismatch issue):
[
  {"query": "Section 16(2)(c) supplier paid tax ITC buyer", "angle": "Core statutory question"},
  {"query": "ITC bona fide purchaser supplier default", "angle": "Pro-assessee angle"},
  {"query": "fake supplier GST ITC buyer liability", "angle": "Specific to fake supplier"},
  {"query": "GSTR-2A GSTR-2B reconciliation ITC denial", "angle": "Reconciliation angle"},
  {"query": "supplier GSTIN cancelled ITC recipient", "angle": "Cancellation angle"},
  {"query": "ITC denial High Court 2024 2025 judgment", "angle": "Recent developments"},
  {"query": "Section 16 CGST input credit revenue appeal won", "angle": "Adversarial — when department won"}
]"""


# Legacy recall prompt — kept for when we need case names specifically (rare)
_CASE_RECALL_PROMPT = """You are an Indian legal expert. Given a legal issue, list ONLY case names you are 100% certain exist.

Output a JSON array. No markdown. Format:
[{"case": "Exact Case Name v. Exact Respondent Name", "court": "SC|HC", "relevance": "one line"}]

STRICT RULES:
- Only cases where you KNOW the exact party names from training
- If unsure, DO NOT include — hallucinated cases are worse than no cases
- 3-6 cases maximum
- Must be recognizable landmark cases
- Return [] if you can't name real ones with confidence"""


async def _llm_generate_queries(session: aiohttp.ClientSession, user_query: str, groq_key: str) -> list[dict]:
    """Ask LLM to generate DIVERSE search queries (NOT case names — those hallucinate).

    The LLM is excellent at identifying legal angles. It's terrible at naming specific cases.
    This approach extracts the legal REASONING without depending on memorized case names.
    """
    if not groq_key:
        return []

    try:
        async with session.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": _SEARCH_QUERY_PROMPT},
                    {"role": "user", "content": f"Legal issue: {user_query[:700]}"},
                ],
                "temperature": 0.4,  # Slight creativity for diverse angles
                "max_tokens": 700,
                "response_format": {"type": "json_object"},
            },
            timeout=aiohttp.ClientTimeout(total=7),
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            content = data["choices"][0]["message"]["content"]
            try:
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    return parsed
                for key in ("queries", "searches", "results", "data"):
                    if key in parsed and isinstance(parsed[key], list):
                        return parsed[key]
            except json.JSONDecodeError:
                m = re.search(r'\[\s*\{.*?\}\s*\]', content, re.DOTALL)
                if m:
                    try:
                        return json.loads(m.group(0))
                    except json.JSONDecodeError:
                        pass
            return []
    except Exception as e:
        logger.warning(f"LLM query generation failed: {e}")
        return []


async def _llm_recall_cases(session: aiohttp.ClientSession, user_query: str, groq_key: str) -> list[dict]:
    """Ask a fast LLM to recall relevant cases from training memory.

    This is the key insight: LLMs like Claude/Groq have VAST case law knowledge baked in.
    We just need to extract it in a structured form, then VERIFY each suggestion live.
    """
    if not groq_key:
        return []

    try:
        async with session.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": _CASE_RECALL_PROMPT},
                    {"role": "user", "content": f"Legal issue: {user_query[:600]}"},
                ],
                "temperature": 0.3,
                "max_tokens": 900,
                "response_format": {"type": "json_object"},
            },
            timeout=aiohttp.ClientTimeout(total=8),
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            content = data["choices"][0]["message"]["content"]
            # Try to parse as JSON array — may be wrapped in object
            try:
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    return parsed
                # Sometimes wrapped: {"cases": [...]}
                for key in ("cases", "results", "data"):
                    if key in parsed and isinstance(parsed[key], list):
                        return parsed[key]
            except json.JSONDecodeError:
                # Try to extract JSON array via regex
                m = re.search(r'\[\s*\{.*?\}\s*\]', content, re.DOTALL)
                if m:
                    try:
                        return json.loads(m.group(0))
                    except json.JSONDecodeError:
                        pass
            return []
    except Exception as e:
        logger.warning(f"LLM case recall failed: {e}")
        return []


async def _verify_case_on_ik_strict(session: aiohttp.ClientSession, case_name: str) -> Optional[dict]:
    """Verify case exists on IK and return the top match with doc_id for full-text fetch."""
    if not IK_API_KEY:
        return None
    try:
        async with session.post(
            "https://api.indiankanoon.org/search/",
            headers={"Authorization": f"Token {IK_API_KEY}"},
            data={"formInput": f'"{case_name}"', "pagenum": 0},
            timeout=aiohttp.ClientTimeout(total=5),
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            docs = data.get("docs", [])

            # Parse the case name into party names
            parts = case_name.lower().split(" v. ") if " v. " in case_name.lower() else case_name.lower().split(" vs ")
            if len(parts) != 2:
                return None
            p1_words = [w for w in parts[0].strip().split() if len(w) > 2][:3]
            p2_words = [w for w in parts[1].strip().split() if len(w) > 2][:3]

            for doc in docs[:10]:
                title_raw = doc.get("title", "")
                title = re.sub(r'<[^>]+>', '', title_raw).lower()
                if any(w in title for w in p1_words) and any(w in title for w in p2_words):
                    return {
                        "source": "ik",
                        "title": re.sub(r'<[^>]+>', '', title_raw),
                        "doc_id": doc.get("tid", ""),
                        "url": f"https://indiankanoon.org/doc/{doc.get('tid', '')}/",
                        "headline": doc.get("headline", "")[:400],
                        "docsource": doc.get("docsource", ""),
                        "year": _extract_year(title_raw),
                        "court_rank": _court_rank(title_raw, doc.get("docsource", "")),
                    }
        return None
    except Exception as e:
        logger.warning(f"IK strict verify failed for '{case_name}': {e}")
        return None


# ==================== MAIN ENTRY ====================

async def discover_cases(user_query: str, max_angles: int = 5, fetch_top_n: int = 4, groq_key: str = "") -> dict:
    """Multi-angle case discovery — THE thing Claude's keyword search loses at.

    Architecture:
      1. LLM RECALL: Ask Groq to name relevant cases from training memory
      2. LIVE VERIFY: Check each LLM-suggested case on IK + fetch full text
      3. RECENT SEARCH: Parallel Serper search for POST-cutoff cases
      4. Dedupe + rank by court hierarchy + recency
      5. Return combined verified cases with full text for LLM grounding

    Returns:
      {"angles_searched", "llm_suggested", "verified_count", "cases", "context_block"}
    """
    if not groq_key:
        groq_key = os.environ.get("GROQ_KEY", "")

    # Hardcoded angle patterns (fast fallback)
    keyword_angles = extract_semantic_angles(user_query)[:max_angles]

    llm_suggested_queries = []
    all_verified = []
    angle_results = []
    llm_suggested_cases = []
    llm_suggested_case_raw = []

    async with aiohttp.ClientSession() as session:
        # Run THREE things in parallel:
        # 1. LLM generates diverse search QUERIES (reliable)
        # 2. LLM names specific cases (less reliable, but we verify)
        # 3. Keyword-based angles from hardcoded patterns (backup)
        query_gen_task = _llm_generate_queries(session, user_query, groq_key)
        case_recall_task = _llm_recall_cases(session, user_query, groq_key)

        # Hardcoded angle searches in parallel
        angle_tasks = []
        for angle in keyword_angles:
            angle_tasks.append(_search_ik(session, angle, top_k=3))

        # Gather phase 1
        results = await asyncio.gather(query_gen_task, case_recall_task, *angle_tasks, return_exceptions=True)
        llm_queries_raw = results[0] if isinstance(results[0], list) else []
        llm_cases_raw = results[1] if isinstance(results[1], list) else []
        angle_results_raw = [r for r in results[2:] if isinstance(r, list)]

        for rl in angle_results_raw:
            angle_results.extend(rl)

        # Phase 2: Search using the LLM-generated QUERIES (the reliable part)
        if llm_queries_raw:
            query_search_tasks = []
            for qobj in llm_queries_raw[:8]:
                q_str = qobj.get("query", "") if isinstance(qobj, dict) else str(qobj)
                if q_str and len(q_str) > 4:
                    llm_suggested_queries.append(qobj)
                    query_search_tasks.append(_search_ik(session, q_str, top_k=3))
                    query_search_tasks.append(_search_serper_web(session, q_str))

            if query_search_tasks:
                qs_results = await asyncio.gather(*query_search_tasks, return_exceptions=True)
                for rl in qs_results:
                    if isinstance(rl, list):
                        angle_results.extend(rl)

        # Phase 3: Verify any specific cases the LLM named (strict verification)
        if llm_cases_raw:
            llm_suggested_case_raw = llm_cases_raw
            verify_tasks = []
            for suggestion in llm_cases_raw[:6]:
                case_name = suggestion.get("case", "") if isinstance(suggestion, dict) else str(suggestion)
                if case_name:
                    verify_tasks.append(_verify_case_on_ik_strict(session, case_name))

            verified = await asyncio.gather(*verify_tasks, return_exceptions=True)
            for suggestion, result in zip(llm_cases_raw[:6], verified):
                if isinstance(result, Exception) or not result:
                    # Hallucinated case — skip
                    continue
                if isinstance(suggestion, dict):
                    result["llm_relevance_note"] = suggestion.get("relevance", "")
                    result["llm_suggested"] = True
                all_verified.append(result)
                llm_suggested_cases.append(suggestion)

        # Combine all results
        all_results = all_verified + angle_results
        unique = _dedupe_cases(all_results)
        ranked = _rank_cases(unique)

        # Fetch full text for top N unique IK results (prioritize LLM-verified ones)
        top_cases = ranked[:fetch_top_n]
        fetch_tasks = []
        for c in top_cases:
            if c.get("source") == "ik" and c.get("doc_id"):
                fetch_tasks.append(_fetch_ik_full_text(session, c["doc_id"], max_chars=5000))
            else:
                fetch_tasks.append(asyncio.sleep(0, result=""))

        full_texts = await asyncio.gather(*fetch_tasks, return_exceptions=True)
        for c, ft in zip(top_cases, full_texts):
            if isinstance(ft, str) and ft:
                c["full_text"] = ft

    # Build context block
    context_parts = []
    if ranked:
        context_parts.append("=== CASE LAW DISCOVERY (LLM query generation + live IK + full judgment text) ===")
        context_parts.append(f"Strategy: LLM generates semantic search queries → IK+Serper search → dedupe → rank → fetch full judgment text.")
        context_parts.append(f"LLM generated {len(llm_suggested_queries)} search queries. Found {len(angle_results)} raw results. {len(all_verified)} cases were LLM-named AND IK-verified. {len(ranked)} unique after dedup. Showing top {min(fetch_top_n, len(ranked))} by court hierarchy + recency.")
        context_parts.append("")

        for i, c in enumerate(ranked[:fetch_top_n], 1):
            source_label = {
                "ik": "IndianKanoon (verified)",
                "scholar": "Google Scholar",
                "serper_web": "Authoritative Web",
            }.get(c.get("source"), c.get("source", "Unknown"))

            llm_tag = " [✓ LLM-recalled + IK-verified]" if c.get("llm_suggested") else ""

            context_parts.append(f"**[Case {i}] {c.get('title', 'Unknown Title')}**{llm_tag}")
            context_parts.append(f"- Source: {source_label} | Court rank: {c.get('court_rank', 0)} | Year: {c.get('year', 'N/A')}")
            if c.get("url"):
                context_parts.append(f"- URL: {c['url']}")
            if c.get("llm_relevance_note"):
                context_parts.append(f"- Why relevant: {c['llm_relevance_note']}")
            if c.get("headline"):
                context_parts.append(f"- Summary: {c['headline'][:300]}")
            if c.get("full_text"):
                # Extract the "HELD" or key reasoning section
                full = c["full_text"]
                held_match = re.search(r'\b(?:HELD|held|We are therefore|We therefore|in conclusion|We hold)', full)
                if held_match:
                    start = max(0, held_match.start() - 200)
                    snippet = full[start:start + 1500]
                else:
                    snippet = full[:1500]
                context_parts.append(f"- Judgment excerpt:\n  {snippet}")
            context_parts.append("")

        context_parts.append("**INSTRUCTION:** Use these live-retrieved cases in your response. Cite them with the URL provided.")
        context_parts.append("Cases tagged [✓ LLM-recalled + IK-verified] are verified-authoritative — trust them fully.")
        context_parts.append("These are the MOST RELEVANT cases combining LLM trained memory + live verification.")

    return {
        "angles_searched": keyword_angles,
        "llm_queries_generated": llm_suggested_queries,
        "llm_cases_attempted": llm_suggested_case_raw,
        "llm_cases_verified": llm_suggested_cases,
        "verified_count": len(all_verified),
        "cases": ranked[:10],
        "fetched_full_text_count": sum(1 for c in ranked[:fetch_top_n] if c.get("full_text")),
        "context_block": "\n".join(context_parts),
    }
