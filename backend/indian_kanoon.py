import aiohttp
import os
import logging
import re

logger = logging.getLogger(__name__)

INDIANKANOON_API_URL = "https://api.indiankanoon.org"
INDIANKANOON_API_KEY = os.environ.get("INDIANKANOON_API_KEY", "")


async def search_indiankanoon(query: str, top_k: int = 5) -> list:
    """Search IndianKanoon for relevant judgments."""
    if not INDIANKANOON_API_KEY:
        logger.warning("IndianKanoon API key not set")
        return []
    
    try:
        headers = {"Authorization": f"Token {INDIANKANOON_API_KEY}"}
        params = {"pagenum": 0}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{INDIANKANOON_API_URL}/search/",
                headers=headers,
                data={"formInput": query, "pagenum": 0},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    logger.error(f"IndianKanoon search failed: {resp.status}")
                    return []
                data = await resp.json()
        
        docs = data.get("docs", [])[:top_k]
        results = []
        for doc in docs:
            title = doc.get("title", "")
            court_info = extract_court_info(title)
            results.append({
                "doc_id": doc.get("tid", ""),
                "title": title,
                "headline": strip_html(doc.get("headline", "")),
                "court": court_info.get("court", ""),
                "year": court_info.get("year", ""),
                "citation": doc.get("citation", title),
                "docsource": doc.get("docsource", ""),
            })
        return results
    except Exception as e:
        logger.error(f"IndianKanoon search error: {e}")
        return []


async def fetch_document(doc_id: str) -> dict:
    """Fetch full document from IndianKanoon."""
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
        return {
            "title": data.get("title", ""),
            "doc": strip_html(data.get("doc", ""))[:8000],
            "citation": data.get("citation", ""),
        }
    except Exception as e:
        logger.error(f"IndianKanoon doc fetch error: {e}")
        return {}


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
    """Remove HTML tags from text."""
    return re.sub(r'<[^>]+>', '', text).strip()
