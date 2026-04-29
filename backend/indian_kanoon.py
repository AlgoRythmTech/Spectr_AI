import aiohttp
import asyncio
import os
import logging
import re

logger = logging.getLogger(__name__)

INDIANKANOON_API_URL = "https://api.indiankanoon.org"
INDIANKANOON_API_KEY = os.environ.get("INDIANKANOON_API_KEY", "")

# Court hierarchy for ranking (higher = more authoritative)
COURT_HIERARCHY = {
    "Supreme Court of India": 100,
    "High Court": 80,
    "NCLAT": 60,
    "NCLT": 55,
    "ITAT": 50,
    "CESTAT": 50,
    "Tribunal": 40,
    "Court": 30,
}


async def _reformulate_query_for_ik(scenario: str) -> str:
    """Turn a natural-language scenario into IK search keywords.

    IK's search is keyword-based, not semantic. Natural sentences like
    'A lawyer is caught practising law without a license' return garbage.
    Feeding it legal section numbers + doctrinal terms works MUCH better.
    Uses Claude Haiku (cheapest) with a tight prompt.
    """
    scenario = (scenario or "").strip()
    if not scenario or len(scenario) < 20:
        return scenario  # already short, pass through

    try:
        from claude_emergent import call_claude, CLAUDE_HAIKU
        reformulation_system = (
            "You are an expert Indian legal researcher. Convert the user's scenario "
            "into a concise IndianKanoon search query. Output ONLY the query — 6 to 15 "
            "words — using Indian legal terms, section numbers, and Act names where "
            "relevant. No quotes, no preamble, no explanation. Just the query.\n\n"
            "Examples:\n"
            "  Scenario: 'A lawyer is caught practising law without a license and has been summoned.'\n"
            "  Query: unauthorised practice of law Section 45 Advocates Act 1961 non-advocate\n\n"
            "  Scenario: 'Client received SCN under GST Section 74 for ₹48 lakh ITC mismatch.'\n"
            "  Query: Section 74 CGST Act show cause notice ITC mismatch fraud suppression\n\n"
            "  Scenario: 'Partner wants anticipatory bail under BNS for cheating case.'\n"
            "  Query: anticipatory bail Section 482 BNSS cheating Section 318 BNS\n"
        )
        reformulated = await call_claude(
            system_prompt=reformulation_system,
            user_content=scenario,
            model=CLAUDE_HAIKU,
            timeout=10,
        )
        reformulated = (reformulated or "").strip().strip('"').strip("'")
        # Sanity: if LLM returned something too long or empty, fall back
        if reformulated and 4 <= len(reformulated.split()) <= 30:
            logger.info(f"IK query reformulation: {scenario[:60]!r} -> {reformulated!r}")
            return reformulated
    except Exception as e:
        logger.warning(f"IK query reformulation failed (using raw scenario): {e}")
    return scenario


async def search_indiankanoon(query: str, top_k: int = 12, court_filter: str = None, reformulate: bool = True) -> list:
    """Search IndianKanoon for relevant judgments.

    Args:
        query: search query or natural-language scenario
        top_k: max results (increased from 5 to 12 for better coverage)
        court_filter: optional — "SC", "HC", "ITAT", "CESTAT", "NCLT" to prefer specific courts
        reformulate: if True, uses LLM to convert natural-language into IK keyword query
    """
    if not INDIANKANOON_API_KEY:
        logger.warning("IndianKanoon API key not set")
        return []

    # Reformulate natural-language queries into keyword search terms
    search_query = query
    if reformulate and len(query) > 40:
        search_query = await _reformulate_query_for_ik(query)

    try:
        headers = {"Authorization": f"Token {INDIANKANOON_API_KEY}"}

        # Build formInput with optional court filter
        form_input = search_query
        if court_filter:
            court_map = {
                "SC": "doctypes: supremecourt",
                "HC": "doctypes: allahabad,bombay,calcutta,delhi,karnataka,madras,kerala,punjab,rajasthan,telangana,gujarathighcourt",
                "ITAT": "doctypes: itat",
                "CESTAT": "doctypes: cestat",
                "NCLT": "doctypes: nclt",
            }
            if court_filter in court_map:
                form_input = f"{search_query} {court_map[court_filter]}"

        # Fetch more results from API, then we filter/rank locally
        fetch_count = min(top_k * 2, 25)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{INDIANKANOON_API_URL}/search/",
                headers=headers,
                data={"formInput": form_input, "pagenum": 0},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    logger.error(f"IndianKanoon search failed: {resp.status}")
                    return []
                data = await resp.json()

        docs = data.get("docs", [])[:fetch_count]
        # Derive query terms for relevance scoring (strip stopwords, lowercase)
        _STOPWORDS = {"a", "an", "the", "is", "are", "was", "were", "of", "in", "on", "at",
                      "for", "to", "from", "by", "and", "or", "but", "with", "that", "this",
                      "be", "has", "have", "had", "not", "no"}
        query_terms = {t.lower().strip(".,;:!?") for t in search_query.split()
                       if len(t) > 2 and t.lower() not in _STOPWORDS}

        results = []
        for idx, doc in enumerate(docs):
            title = doc.get("title", "")
            court_info = extract_court_info(title)
            headline_text = strip_html(doc.get("headline", ""))

            # Relevance score: IK's native order (lower idx = better) + keyword overlap bonus
            searchable = (title + " " + headline_text).lower()
            keyword_hits = sum(1 for t in query_terms if t in searchable)
            relevance_score = (len(docs) - idx) * 10 + keyword_hits * 5

            results.append({
                "doc_id": doc.get("tid", ""),
                "title": title,
                "headline": headline_text,
                "court": court_info.get("court", ""),
                "year": court_info.get("year", ""),
                "citation": doc.get("citation", title),
                "docsource": doc.get("docsource", ""),
                "_court_rank": COURT_HIERARCHY.get(court_info.get("court", ""), 20),
                "_relevance": relevance_score,
            })

        # Rank: RELEVANCE first (IK's native order + keyword overlap), court rank as tiebreaker
        # This fixes the bug where unrelated SC cases beat directly-relevant HC cases.
        results.sort(key=lambda r: (
            -r.get("_relevance", 0),
            -r.get("_court_rank", 0),
            -(int(r.get("year") or "0")),
        ))

        # Strip internal ranking keys, return top_k
        for r in results:
            r.pop("_court_rank", None)
            r.pop("_relevance", None)
        return results[:top_k]

    except Exception as e:
        logger.error(f"IndianKanoon search error: {e}")
        return []


async def fetch_document(doc_id: str, max_chars: int = 25000) -> dict:
    """Fetch full document from IndianKanoon.

    Args:
        doc_id: IndianKanoon document ID
        max_chars: max characters to return (increased from 8000 to 25000 for fuller context)
    """
    if not INDIANKANOON_API_KEY:
        return {}

    try:
        headers = {"Authorization": f"Token {INDIANKANOON_API_KEY}"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{INDIANKANOON_API_URL}/doc/{doc_id}/",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    return {}
                data = await resp.json()

        full_text = strip_html(data.get("doc", ""))
        return {
            "title": data.get("title", ""),
            "doc": full_text[:max_chars],
            "citation": data.get("citation", ""),
            "full_length": len(full_text),
        }
    except Exception as e:
        logger.error(f"IndianKanoon doc fetch error: {e}")
        return {}


async def fetch_documents_parallel(doc_ids: list, max_chars: int = 25000) -> list:
    """Fetch multiple documents in parallel for speed.

    Args:
        doc_ids: list of IndianKanoon document IDs
        max_chars: max characters per document
    """
    if not doc_ids:
        return []

    tasks = [fetch_document(did, max_chars=max_chars) for did in doc_ids[:8]]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    docs = []
    for r in results:
        if isinstance(r, dict) and r.get("title"):
            docs.append(r)
        elif isinstance(r, Exception):
            logger.warning(f"Parallel doc fetch error: {r}")
    return docs


async def search_and_fetch(query: str, top_k: int = 8, fetch_top_n: int = 4,
                           court_filter: str = None, max_chars: int = 20000) -> dict:
    """Combined search + fetch for the top results. One-call convenience function.

    Returns: {"results": [...], "documents": [...]}
    """
    results = await search_indiankanoon(query, top_k=top_k, court_filter=court_filter)
    if not results:
        return {"results": [], "documents": []}

    # Fetch full text for the top N results
    doc_ids = [r["doc_id"] for r in results[:fetch_top_n] if r.get("doc_id")]
    documents = await fetch_documents_parallel(doc_ids, max_chars=max_chars)

    return {"results": results, "documents": documents}


def extract_court_info(title: str) -> dict:
    """Extract court and year from judgment title."""
    court = ""
    year = ""
    
    year_match = re.search(r'\b(19|20)\d{2}\b', title)
    if year_match:
        year = year_match.group()
    
    title_lower = title.lower()
    if "supreme court" in title_lower:
        court = "Supreme Court of India"
    elif "high court" in title_lower:
        court_match = re.search(r'([\w\s]+)\s*high\s*court', title_lower)
        court = f"{court_match.group(1).strip().title()} High Court" if court_match else "High Court"
    elif "nclt" in title_lower:
        court = "NCLT"
    elif "nclat" in title_lower:
        court = "NCLAT"
    elif "itat" in title_lower:
        court = "ITAT"
    elif "cestat" in title_lower:
        court = "CESTAT"
    elif "tribunal" in title_lower:
        court = "Tribunal"
    else:
        court = "Court"
    
    return {"court": court, "year": year}


def strip_html(text: str) -> str:
    """Remove HTML tags AND website chrome/navigation text from IK content.

    IK's /doc/ endpoint sometimes returns the full page HTML which, when
    stripped of tags, leaves nav text like "Skip to main content", "Indian
    Kanoon", "Search", menu labels, and promo copy. We strip those patterns
    so only judgment body makes it into LLM context.
    """
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove known IK website chrome lines (case-insensitive, line-by-line)
    chrome_patterns = [
        r'skip to main content',
        r'indian kanoon\s*-\s*search engine for indian law',
        r'^search indian laws and judgments\s*$',
        r'^search laws, court judgments.*$',
        r'^main navigation\s*$',
        r'^free features\s*$',
        r'^premium\s*$',
        r'^prism ai\s*$',
        r'^ikademy\s*$',
        r'^pricing\s*$',
        r'^login\s*$',
        r'^legal document view\s*$',
        r'^tools for analyzing.*$',
        r'^select the following parts.*$',
        r'^for entire doc:\s*$',
        r'^view how precedents.*$',
        r'^view precedents:\s*$',
        r'^view only precedents:\s*$',
        r'^filter precedents by opinion.*$',
        r'^unlock advanced research.*$',
        r'^integrated with over.*judgments.*$',
        r'^know your kanoon\s*$',
        r'^doc gen hub\s*$',
        r'^counter argument\s*$',
        r'^case predict ai\s*$',
        r'^talk with ik doc\s*$',
        r'^upgrade to premium\s*$',
        r'^document options\s*$',
        r'^\[cites \d+,\s*cited by \d+\]\s*$',
    ]
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned.append(line)
            continue
        is_chrome = False
        for pat in chrome_patterns:
            if re.match(pat, stripped, re.IGNORECASE):
                is_chrome = True
                break
        if not is_chrome:
            cleaned.append(line)
    text = "\n".join(cleaned)
    # Collapse 3+ blank lines to 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
