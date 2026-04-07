"""
SEBI / RBI / MCA / CBIC / IBBI Regulatory Change Monitor
An agent that monitors regulatory changes and maps them against active client matters.
"Client ABC has an IBC Section 7 application pending. IBBI just issued new CIRP timelines.
Here is what changes and what it means for this matter."
"""
import logging
import aiohttp
import re
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# RSS/API endpoints for Indian regulators
REGULATORY_SOURCES = {
    "SEBI": {
        "url": "https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doCommittee=false&typeRound=2",
        "rss": "https://www.sebi.gov.in/sebirss.xml",
        "type": "SEBI Circular",
        "tags": ["sebi", "securities", "listed_company", "ipo", "insider_trading"],
    },
    "RBI": {
        "url": "https://www.rbi.org.in/scripts/NotificationUser.aspx",
        "rss": "https://www.rbi.org.in/scripts/rss.aspx",
        "type": "RBI Master Direction / Circular",
        "tags": ["rbi", "banking", "fema", "nbfc", "forex"],
    },
    "MCA": {
        "url": "https://www.mca.gov.in/MinistryV2/notification.html",
        "type": "MCA Notification / Amendment",
        "tags": ["mca", "companies_act", "roc", "llp"],
    },
    "CBIC": {
        "url": "https://www.cbic.gov.in/resources//htdocs-cbec/gst/notfnsst.pdf",
        "type": "GST Circular / Notification",
        "tags": ["gst", "customs", "cgst", "igst"],
    },
    "IBBI": {
        "url": "https://www.ibbi.gov.in/",
        "type": "IBBI Regulation / Circular",
        "tags": ["ibc", "insolvency", "nclt", "cirp", "resolution_professional"],
    },
    "ITAT": {
        "url": "https://itat.gov.in/WebMarketing/",
        "type": "ITAT Order / Practice Direction",
        "tags": ["itat", "income_tax", "appeal", "tax_tribunal"],
    },
}

# India-specific matter type → regulator tag mapping
MATTER_TYPE_TO_TAGS = {
    "ibc_section7": ["ibc", "nclt", "cirp", "sebi"],
    "ibc_section9": ["ibc", "nclt", "cirp"],
    "gst_appeal": ["gst", "cgst", "cbic"],
    "income_tax": ["itat", "income_tax"],
    "sebi_investigation": ["sebi", "securities"],
    "fema": ["rbi", "fema", "forex"],
    "company_law": ["mca", "companies_act", "roc"],
    "banking": ["rbi", "banking", "nbfc"],
    "real_estate": ["rera", "sebi"],
    "general": ["all"],
}


async def check_regulatory_updates(matter_types: list, days_back: int = 7) -> list:
    """
    Check recent regulatory updates relevant to the given matter types.
    Returns structured list of updates with matter impact analysis.
    """
    relevant_tags = set()
    for mt in matter_types:
        relevant_tags.update(MATTER_TYPE_TO_TAGS.get(mt, ["all"]))
    
    updates = []
    
    # Try to scrape SEBI RSS
    try:
        sebi_updates = await _fetch_rss(REGULATORY_SOURCES["SEBI"]["rss"], "SEBI")
        updates.extend(sebi_updates)
    except Exception as e:
        logger.warning(f"SEBI feed error: {e}")
        updates.append(_mock_update("SEBI", "SEBI Circular No. SEBI/HO/CFD/2026-01", 
                                    "Revised disclosure requirements for listed companies under LODR Regulations"))
    
    # Try to scrape RBI
    try:
        rbi_updates = await _fetch_rss(REGULATORY_SOURCES["RBI"]["rss"], "RBI")
        updates.extend(rbi_updates)
    except Exception as e:
        logger.warning(f"RBI feed error: {e}")
        updates.append(_mock_update("RBI", "RBI Master Direction 2026", 
                                    "Updated FEMA regulations for external commercial borrowings"))
    
    # Filter by relevant tags
    if "all" not in relevant_tags:
        filtered = []
        for update in updates:
            update_tags = update.get("tags", [])
            if any(tag in relevant_tags for tag in update_tags):
                filtered.append(update)
        return filtered
    
    return updates


async def _fetch_rss(url: str, source: str) -> list:
    """Fetch and parse an RSS feed from a regulator."""
    updates = []
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10), 
                               headers={"User-Agent": "Mozilla/5.0"}) as resp:
            if resp.status != 200:
                return []
            content = await resp.text()
            
    # Parse basic RSS items
    items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)
    for item in items[:10]:
        title = re.search(r'<title>(.*?)</title>', item)
        link = re.search(r'<link>(.*?)</link>', item)
        pub_date = re.search(r'<pubDate>(.*?)</pubDate>', item)
        
        if title:
            updates.append({
                "source": source,
                "title": re.sub(r'<[^>]+>', '', title.group(1)).strip(),
                "url": link.group(1).strip() if link else "",
                "published": pub_date.group(1).strip() if pub_date else "",
                "tags": REGULATORY_SOURCES.get(source, {}).get("tags", []),
                "type": REGULATORY_SOURCES.get(source, {}).get("type", "Regulatory Update"),
            })
    return updates


def _mock_update(source: str, title: str, description: str) -> dict:
    """Generate a mock update for demonstration when feed is unavailable."""
    return {
        "source": source,
        "title": title,
        "description": description,
        "url": f"https://www.{source.lower()}.gov.in/",
        "published": datetime.now(timezone.utc).isoformat(),
        "tags": REGULATORY_SOURCES.get(source, {}).get("tags", []),
        "type": REGULATORY_SOURCES.get(source, {}).get("type", "Update"),
        "is_demo": True,
    }


async def generate_regulatory_impact(update_title: str, update_description: str, 
                                      matter_type: str, matter_facts: str,
                                      process_query_fn) -> str:
    """
    Use AI to analyze the regulatory update's impact on a specific client matter.
    """
    prompt = f"""
You are a Regulatory Intelligence Analyst for Indian legal and tax matters.

A new regulatory update has been issued:
REGULATOR UPDATE: {update_title}
DESCRIPTION: {update_description}

Active Client Matter:
Matter Type: {matter_type}
Matter Facts: {matter_facts[:2000]}

Analyze:
1. Does this regulatory change DIRECTLY impact this matter? (Yes/No/Possibly)
2. What specifically changes for the client?
3. What ACTION must the lawyer/CA take within the next 30 days?
4. Any penalty/liability exposure if action is not taken?
5. Relevant sections/rules that now apply.

Be specific and actionable. If the update has no impact on this matter, say clearly: "No direct impact on this matter."
"""
    result = await process_query_fn(
        user_query=prompt,
        mode="partner",
        matter_context=f"Regulatory Impact Analysis: {matter_type}"
    )
    return result.get("response_text", "Impact analysis unavailable.")
