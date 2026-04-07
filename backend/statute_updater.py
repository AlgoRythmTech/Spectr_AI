"""
Statute Auto-Updater
Nightly cron job that checks for new circulars, notifications, and amendments
from CBDT, CBIC, MCA, RBI and updates the statute DB.
"""
import os
import json
import aiohttp
import logging
import hashlib
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URI)
db = client["associate_db"]
updates_col = db["regulatory_updates"]
statutes_col = db["master_statutes"]

# RSS/Web sources for Indian regulatory updates
SOURCES = [
    {
        "id": "cbic",
        "name": "CBIC (GST/Customs)",
        "url": "https://www.cbic.gov.in/htdocs-cbec/gst/notifications-circulars",
        "type": "scrape",
        "category": "GST"
    },
    {
        "id": "cbdt",
        "name": "CBDT (Income Tax)",
        "url": "https://incometaxindia.gov.in/Pages/communications/notifications.aspx",
        "type": "scrape",
        "category": "Income Tax"
    },
    {
        "id": "mca",
        "name": "MCA (Companies Act)",
        "url": "https://www.mca.gov.in/content/mca/global/en/acts-rules/efile/notifications.html",
        "type": "scrape",
        "category": "Companies Act"
    },
    {
        "id": "rbi",
        "name": "RBI (Banking/FEMA)",
        "url": "https://www.rbi.org.in/Scripts/NotificationUser.aspx",
        "type": "scrape",
        "category": "FEMA/Banking"
    },
    {
        "id": "pib",
        "name": "PIB (Press Information Bureau)",
        "url": "https://pib.gov.in/allRel.aspx",
        "type": "scrape",
        "category": "General"
    },
    {
        "id": "gazette",
        "name": "eGazette of India",
        "url": "https://egazette.gov.in/",
        "type": "scrape",
        "category": "All"
    }
]

async def check_for_updates() -> list:
    """
    Check all configured sources for new regulatory updates.
    Returns list of new updates found.
    """
    new_updates = []
    
    for source in SOURCES:
        try:
            items = await _scrape_source(source)
            for item in items:
                # Generate unique hash to avoid duplicates
                content_hash = hashlib.md5(
                    f"{item['title']}{item.get('date', '')}".encode()
                ).hexdigest()
                
                # Check if we already have this update
                existing = await updates_col.find_one({"content_hash": content_hash})
                if not existing:
                    update_doc = {
                        "content_hash": content_hash,
                        "source_id": source["id"],
                        "source_name": source["name"],
                        "category": source["category"],
                        "title": item["title"],
                        "url": item.get("url", ""),
                        "date": item.get("date", ""),
                        "snippet": item.get("snippet", ""),
                        "full_text": item.get("full_text", ""),
                        "impact_analysis": None,
                        "status": "new",
                        "discovered_at": datetime.now(timezone.utc).isoformat()
                    }
                    await updates_col.insert_one(update_doc)
                    update_doc.pop("_id", None)
                    new_updates.append(update_doc)
                    
        except Exception as e:
            logger.error(f"Error checking source {source['id']}: {e}")
            continue
    
    logger.info(f"Found {len(new_updates)} new regulatory updates across {len(SOURCES)} sources")
    return new_updates

async def _scrape_source(source: dict) -> list:
    """Scrape a regulatory source for new items."""
    items = []
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                source["url"],
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    
                    # Generic extraction: find links with regulatory keywords
                    for link in soup.find_all("a", href=True)[:50]:
                        title = link.get_text(strip=True)
                        href = link["href"]
                        
                        # Filter for regulatory content
                        keywords = ["notification", "circular", "order", "amendment", 
                                   "gazette", "regulation", "rule", "press release",
                                   "corrigendum", "instruction"]
                        if any(kw in title.lower() for kw in keywords) and len(title) > 15:
                            # Make absolute URL
                            if not href.startswith("http"):
                                from urllib.parse import urljoin
                                href = urljoin(source["url"], href)
                            
                            items.append({
                                "title": title[:300],
                                "url": href,
                                "snippet": title[:200],
                                "date": datetime.now().strftime("%Y-%m-%d")
                            })
                            
    except Exception as e:
        logger.error(f"Scrape error for {source['id']}: {e}")
    
    return items[:10]  # Cap at 10 per source

async def generate_impact_analysis(update_id: str) -> dict:
    """
    Use AI to analyze the impact of a regulatory update on existing clients/matters.
    """
    GROQ_KEY = os.environ.get("GROQ_KEY", "")
    
    update = await updates_col.find_one({"content_hash": update_id})
    if not update:
        return {"error": "Update not found"}
    
    prompt = f"""You are a senior Indian regulatory analyst. Analyze the following new regulatory update.

Title: {update['title']}
Source: {update['source_name']}
Category: {update['category']}
Date: {update.get('date', 'Unknown')}
Content: {update.get('full_text', update.get('snippet', 'No content available'))}

Provide:
1. SUMMARY: What this update does in 2-3 sentences
2. WHO IS AFFECTED: Which types of businesses/individuals are impacted
3. KEY CHANGES: Specific changes to compliance requirements, deadlines, or procedures
4. ACTION REQUIRED: What professionals need to do in response
5. EFFECTIVE DATE: When does this take effect
6. RELATED PROVISIONS: Which sections of which Acts are affected

Write in professional prose without markdown headers."""

    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": "You are a senior Indian regulatory affairs analyst."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 2000
            }
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    analysis = data["choices"][0]["message"]["content"]
                    
                    await updates_col.update_one(
                        {"content_hash": update_id},
                        {"$set": {"impact_analysis": analysis, "status": "analyzed"}}
                    )
                    
                    return {"analysis": analysis}
                    
    except Exception as e:
        logger.error(f"Impact analysis error: {e}")
        return {"error": str(e)}

async def get_recent_updates(category: str = None, limit: int = 20) -> list:
    """Get recent regulatory updates, optionally filtered by category."""
    query = {}
    if category:
        query["category"] = category
    
    cursor = updates_col.find(query).sort("discovered_at", -1).limit(limit)
    updates = []
    async for doc in cursor:
        doc.pop("_id", None)
        updates.append(doc)
    return updates

async def update_statute_from_notification(notification_text: str, act_name: str, section_number: str) -> dict:
    """
    Update a specific statute section based on a notification/amendment.
    """
    existing = await statutes_col.find_one({
        "act_name": {"$regex": act_name, "$options": "i"},
        "section_number": section_number
    })
    
    if existing:
        # Append amendment history
        amendments = existing.get("amendments", [])
        amendments.append({
            "date": datetime.now(timezone.utc).isoformat(),
            "notification": notification_text[:500],
            "previous_text": existing.get("text", "")
        })
        
        await statutes_col.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "amendments": amendments,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }}
        )
        return {"status": "updated", "section": section_number, "act": act_name}
    
    return {"status": "not_found", "section": section_number, "act": act_name}
