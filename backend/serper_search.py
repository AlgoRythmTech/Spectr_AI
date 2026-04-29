"""
Serper Search Engine — Lightning-fast Google Search API integration.

Used for EVERY query in Quick mode and as initial intelligence in Deep Research.
Serper returns structured Google results in <1 second — no browser needed.

Endpoints:
  1. Google Search (web) — standard search results with snippets
  2. Google News — latest news articles
  3. Google Scholar — academic papers, court judgments, legal journals

Architecture:
  Quick mode: Serper only → instant results → feed to AI
  Deep mode: Serper first (breadth) → Blaxel sandbox (depth) → cross-reference
"""

import os
import json
import asyncio
import logging
import aiohttp
from typing import Optional

logger = logging.getLogger("serper_search")

SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
SERPER_BASE_URL = "https://google.serper.dev"


# ─── Core Search Functions ───

async def search_google(
    query: str,
    num_results: int = 10,
    country: str = "in",
    language: str = "en",
    session: aiohttp.ClientSession = None,
) -> dict:
    """Google web search via Serper. Returns structured results in <500ms."""
    if not SERPER_API_KEY:
        logger.warning("SERPER_API_KEY not set — skipping Google search")
        return {"results": [], "error": "API key not configured"}

    _own_session = session is None
    if _own_session:
        session = aiohttp.ClientSession()
    try:
        async with session.post(
            f"{SERPER_BASE_URL}/search",
            headers={
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "q": query,
                "gl": country,
                "hl": language,
                "num": num_results,
                "autocorrect": True,
            },
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                logger.error(f"Serper search failed: HTTP {resp.status}")
                return {"results": [], "error": f"HTTP {resp.status}"}

            data = await resp.json()

            results = []
            for item in data.get("organic", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "position": item.get("position", 0),
                    "date": item.get("date", ""),
                    "source": "google",
                })

            kg = data.get("knowledgeGraph", {})
            knowledge = None
            if kg:
                knowledge = {
                    "title": kg.get("title", ""),
                    "type": kg.get("type", ""),
                    "description": kg.get("description", ""),
                    "attributes": kg.get("attributes", {}),
                }

            answer_box = data.get("answerBox", {})
            featured = None
            if answer_box:
                featured = {
                    "title": answer_box.get("title", ""),
                    "answer": answer_box.get("answer", answer_box.get("snippet", "")),
                    "url": answer_box.get("link", ""),
                }

            paa = [
                {"question": item.get("question", ""), "snippet": item.get("snippet", "")}
                for item in data.get("peopleAlsoAsk", [])[:4]
            ]

            return {
                "results": results,
                "knowledge_graph": knowledge,
                "featured_snippet": featured,
                "people_also_ask": paa,
                "search_info": data.get("searchParameters", {}),
            }

    except asyncio.TimeoutError:
        logger.error("Serper search timed out")
        return {"results": [], "error": "Search timed out"}
    except Exception as e:
        logger.error(f"Serper search error: {e}")
        return {"results": [], "error": str(e)}
    finally:
        if _own_session:
            await session.close()


async def search_news(
    query: str,
    num_results: int = 10,
    country: str = "in",
    language: str = "en",
    time_period: str = "",  # "h" = hour, "d" = day, "w" = week, "m" = month, "y" = year
    session: aiohttp.ClientSession = None,
) -> dict:
    """Google News search via Serper. Returns latest news articles."""
    if not SERPER_API_KEY:
        return {"results": [], "error": "API key not configured"}

    _own_session = session is None
    if _own_session:
        session = aiohttp.ClientSession()
    try:
        payload = {
            "q": query,
            "gl": country,
            "hl": language,
            "num": num_results,
        }
        if time_period:
            payload["tbs"] = f"qdr:{time_period}"

        async with session.post(
            f"{SERPER_BASE_URL}/news",
            headers={
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return {"results": [], "error": f"HTTP {resp.status}"}

            data = await resp.json()
            results = []
            for item in data.get("news", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "date": item.get("date", ""),
                    "source_name": item.get("source", ""),
                    "source": "google_news",
                })

            return {"results": results}

    except Exception as e:
        logger.error(f"Serper news search error: {e}")
        return {"results": [], "error": str(e)}
    finally:
        if _own_session:
            await session.close()


async def search_scholar(
    query: str,
    num_results: int = 10,
    session: aiohttp.ClientSession = None,
) -> dict:
    """Google Scholar search via Serper. Returns academic/legal papers."""
    if not SERPER_API_KEY:
        return {"results": [], "error": "API key not configured"}

    _own_session = session is None
    if _own_session:
        session = aiohttp.ClientSession()
    try:
        async with session.post(
            f"{SERPER_BASE_URL}/scholar",
            headers={
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "q": query,
                "num": num_results,
            },
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return {"results": [], "error": f"HTTP {resp.status}"}

            data = await resp.json()
            results = []
            for item in data.get("organic", []):
                cited_by_raw = item.get("citedBy", 0)
                cited_by = cited_by_raw.get("total", 0) if isinstance(cited_by_raw, dict) else (cited_by_raw if isinstance(cited_by_raw, int) else 0)
                pub_info = item.get("publication_info", {})
                authors = pub_info.get("summary", "") if isinstance(pub_info, dict) else str(pub_info)
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "year": item.get("year", ""),
                    "cited_by": cited_by,
                    "authors": authors,
                    "source": "google_scholar",
                })

            return {"results": results}

    except Exception as e:
        logger.error(f"Serper scholar search error: {e}")
        return {"results": [], "error": str(e)}
    finally:
        if _own_session:
            await session.close()


# ─── Multi-Search for Research ───

async def run_comprehensive_search(
    user_query: str,
    query_types: list[str],
    include_news: bool = True,
    include_scholar: bool = True,
) -> dict:
    """
    Run parallel searches across Google Web + News + Scholar.
    Returns combined, deduplicated results in <1.5 seconds.
    """
    queries = _build_serper_queries(user_query, query_types)

    # Fire all searches in parallel using a SINGLE shared session (1 TCP pool, not 5)
    async with aiohttp.ClientSession() as shared_session:
        tasks = []
        for q in queries[:3]:
            tasks.append(search_google(q, num_results=10, session=shared_session))
        if include_news:
            news_query = f"{user_query} India"
            tasks.append(search_news(news_query, num_results=5, time_period="m", session=shared_session))
        if include_scholar and any(t in query_types for t in ["legal", "taxation", "financial"]):
            tasks.append(search_scholar(f"{user_query} India law", num_results=5, session=shared_session))

        results_list = await asyncio.gather(*tasks, return_exceptions=True)

    # Combine and deduplicate
    all_results = []
    seen_urls = set()
    knowledge_graph = None
    featured_snippet = None
    people_also_ask = []

    for result in results_list:
        if isinstance(result, Exception):
            logger.warning(f"Search task failed: {result}")
            continue
        if not isinstance(result, dict):
            continue

        for r in result.get("results", []):
            url = r.get("url", "")
            normalized = _normalize_url(url)
            if normalized and normalized not in seen_urls:
                seen_urls.add(normalized)
                all_results.append(r)

        if not knowledge_graph and result.get("knowledge_graph"):
            knowledge_graph = result["knowledge_graph"]
        if not featured_snippet and result.get("featured_snippet"):
            featured_snippet = result["featured_snippet"]
        if result.get("people_also_ask"):
            people_also_ask.extend(result["people_also_ask"])

    return {
        "results": all_results,
        "knowledge_graph": knowledge_graph,
        "featured_snippet": featured_snippet,
        "people_also_ask": people_also_ask[:6],
        "total_results": len(all_results),
        "queries_used": queries[:3],
    }


def format_serper_for_llm(search_data: dict, user_query: str) -> str:
    """Format Serper search results into structured context for AI consumption."""
    parts = []
    results = search_data.get("results", [])
    if not results:
        return ""

    parts.append("=== GOOGLE SEARCH INTELLIGENCE ===")
    parts.append(f"Query: {user_query}")
    parts.append(f"Sources found: {len(results)}")
    parts.append("")

    # Featured snippet (highest priority)
    featured = search_data.get("featured_snippet")
    if featured:
        parts.append(f">>> FEATURED ANSWER: {featured.get('answer', '')}")
        parts.append(f"    Source: {featured.get('url', '')}")
        parts.append("")

    # Knowledge graph
    kg = search_data.get("knowledge_graph")
    if kg:
        parts.append(f">>> KNOWLEDGE PANEL: {kg.get('title', '')} ({kg.get('type', '')})")
        if kg.get("description"):
            parts.append(f"    {kg['description']}")
        for key, val in (kg.get("attributes", {}) or {}).items():
            parts.append(f"    {key}: {val}")
        parts.append("")

    # Web results
    web_results = [r for r in results if r.get("source") == "google"]
    if web_results:
        parts.append(f"── Web Results ({len(web_results)}) ──")
        for idx, r in enumerate(web_results[:10], 1):
            parts.append(f"  {idx}. {r.get('title', 'No title')}")
            parts.append(f"     {r.get('url', '')}")
            if r.get("date"):
                parts.append(f"     Date: {r['date']}")
            if r.get("snippet"):
                parts.append(f"     → {r['snippet'][:300]}")
        parts.append("")

    # News results
    news_results = [r for r in results if r.get("source") == "google_news"]
    if news_results:
        parts.append(f"── Latest News ({len(news_results)}) ──")
        for idx, r in enumerate(news_results[:5], 1):
            parts.append(f"  {idx}. {r.get('title', '')}")
            parts.append(f"     {r.get('url', '')}")
            if r.get("date"):
                parts.append(f"     Published: {r['date']}")
            if r.get("source_name"):
                parts.append(f"     Source: {r['source_name']}")
            if r.get("snippet"):
                parts.append(f"     → {r['snippet'][:200]}")
        parts.append("")

    # Scholar results
    scholar_results = [r for r in results if r.get("source") == "google_scholar"]
    if scholar_results:
        parts.append(f"── Academic/Legal Papers ({len(scholar_results)}) ──")
        for idx, r in enumerate(scholar_results[:5], 1):
            parts.append(f"  {idx}. {r.get('title', '')}")
            parts.append(f"     {r.get('url', '')}")
            if r.get("year"):
                parts.append(f"     Year: {r['year']}")
            if r.get("cited_by"):
                parts.append(f"     Cited by: {r['cited_by']}")
            if r.get("authors"):
                parts.append(f"     {r['authors']}")
        parts.append("")

    # People also ask
    paa = search_data.get("people_also_ask", [])
    if paa:
        parts.append("── Related Questions ──")
        for q in paa[:4]:
            parts.append(f"  Q: {q.get('question', '')}")
            if q.get("snippet"):
                parts.append(f"     {q['snippet'][:200]}")
        parts.append("")

    return "\n".join(parts)


# ─── Helpers ───

def _build_serper_queries(user_query: str, query_types: list[str]) -> list[str]:
    """Build targeted search queries for Serper based on query type."""
    queries = [user_query]

    if "legal" in query_types or "drafting" in query_types:
        queries.append(f"{user_query} Indian law judgment case law")
    if "taxation" in query_types or "financial" in query_types:
        queries.append(f"{user_query} India income tax GST notification circular")
    if "compliance" in query_types or "corporate" in query_types:
        queries.append(f"{user_query} India compliance regulation MCA SEBI RBI")

    return queries[:3]


def _normalize_url(url: str) -> str:
    """Normalize URL for deduplication."""
    if not url:
        return ""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return (parsed.hostname or "").replace("www.", "") + parsed.path.rstrip("/")
    except Exception:
        return url.lower()
