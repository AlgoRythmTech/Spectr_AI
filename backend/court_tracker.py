"""
Court Date Tracker
Scrapes eCourts / NJDG for case status and hearing dates.
Stores tracked cases in MongoDB for recurring checks.
"""
import os
import json
import aiohttp
import logging
import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

# Lazy-init MongoDB client — avoid module-import-time network calls that can hang
_client = None
_db = None
_tracked_cases_col = None


def _get_col():
    """Return the tracked_cases collection lazily. Uses the same connection string as server."""
    global _client, _db, _tracked_cases_col
    if _tracked_cases_col is None:
        mongo_uri = os.getenv("MONGO_URL", os.getenv("MONGO_URI", "mongodb://localhost:27017"))
        _client = AsyncIOMotorClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
        )
        _db = _client["associate_db"]
        _tracked_cases_col = _db["tracked_cases"]
    return _tracked_cases_col


# Backward-compat shim — existing code uses `tracked_cases_col` as module attribute
class _LazyColl:
    def __getattr__(self, name):
        return getattr(_get_col(), name)

tracked_cases_col = _LazyColl()

async def search_ecourts(case_number: str = None, party_name: str = None, court: str = "supreme_court") -> list:
    """
    Search for case details. Uses NJDG public data or Google as fallback.
    """
    results = []
    
    # Strategy 1: NJDG API
    try:
        search_query = case_number or party_name
        njdg_url = f"https://njdg.ecourts.gov.in/njdgnew/index.php"
        
        async with aiohttp.ClientSession() as session:
            # Use Google search as reliable fallback
            google_query = f"site:ecourts.gov.in {search_query} next hearing date"
            async with session.get(
                f"https://www.google.com/search?q={aiohttp.helpers.quote(google_query, safe='')}",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    for g in soup.select(".g")[:5]:
                        title = g.select_one("h3")
                        snippet = g.select_one(".VwiC3b")
                        link = g.select_one("a")
                        if title:
                            results.append({
                                "title": title.get_text(),
                                "snippet": snippet.get_text() if snippet else "",
                                "url": link["href"] if link else "",
                                "source": "eCourts"
                            })
    except Exception as e:
        logger.error(f"eCourts search error: {e}")

    # Strategy 2: IndianKanoon for decided cases
    try:
        search_query = case_number or party_name
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://indiankanoon.org/search/?formInput={aiohttp.helpers.quote(search_query, safe='')}",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    for result_div in soup.select(".result")[:3]:
                        title_el = result_div.select_one(".result_title a")
                        if title_el:
                            results.append({
                                "title": title_el.get_text().strip(),
                                "url": f"https://indiankanoon.org{title_el['href']}",
                                "snippet": result_div.get_text()[:200],
                                "source": "IndianKanoon"
                            })
    except Exception as e:
        logger.error(f"IndianKanoon search error: {e}")

    return results

async def track_case(user_id: str, case_number: str, court: str, party_name: str, matter_id: str = None) -> dict:
    """Add a case to the tracking list."""
    import uuid
    
    track_id = f"trk_{uuid.uuid4().hex[:12]}"
    
    # Initial search for current status
    search_results = await search_ecourts(case_number=case_number, party_name=party_name, court=court)
    
    case_doc = {
        "track_id": track_id,
        "user_id": user_id,
        "case_number": case_number,
        "court": court,
        "party_name": party_name,
        "matter_id": matter_id,
        "status": "tracking",
        "next_hearing": None,
        "last_checked": datetime.now(timezone.utc).isoformat(),
        "search_results": search_results[:3],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await tracked_cases_col.insert_one(case_doc)
    case_doc.pop("_id", None)
    
    return case_doc

async def get_tracked_cases(user_id: str) -> list:
    """Get all tracked cases for a user."""
    cursor = tracked_cases_col.find({"user_id": user_id})
    cases = []
    async for doc in cursor:
        doc.pop("_id", None)
        cases.append(doc)
    return cases

async def remove_tracked_case(track_id: str, user_id: str) -> bool:
    """Remove a case from tracking."""
    result = await tracked_cases_col.delete_one({"track_id": track_id, "user_id": user_id})
    return result.deleted_count > 0

async def refresh_case(track_id: str) -> dict:
    """Re-check a tracked case for updated hearing info."""
    case_doc = await tracked_cases_col.find_one({"track_id": track_id})
    if not case_doc:
        return {"error": "Case not found"}
        
    updated_results = await search_ecourts(
        case_number=case_doc["case_number"],
        party_name=case_doc["party_name"],
        court=case_doc["court"]
    )
    
    await tracked_cases_col.update_one(
        {"track_id": track_id},
        {"$set": {
            "search_results": updated_results[:3],
            "last_checked": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    case_doc.pop("_id", None)
    case_doc["search_results"] = updated_results[:3]
    case_doc["last_checked"] = datetime.now(timezone.utc).isoformat()
    
    return case_doc
