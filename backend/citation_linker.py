import re
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
import logging

logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URL", os.getenv("MONGO_URI", "mongodb://localhost:27017"))
client = AsyncIOMotorClient(MONGO_URI)
db = client["associate_db"]
statute_collection = db["master_statutes"]

async def find_citation_links(text: str):
    """
    Scans AI response text for section references and case law,
    and returns a list of citation objects.
    """
    citations = []
    
    # 1. Look for Statute Sections
    # Examples: Section 73 of the CGST Act, Section 138 of the Negotiable Instruments Act, Sec. 14 of IBC, Section 270A of the Income Tax Act
    statute_pattern = re.compile(r'(?:Section|Sec\.|u/s)\s*([0-9a-zA-Z]+)(?:\s*of(?:\s*the)?\s*)?([A-Za-z\s]+?(?:Act|Code))', re.IGNORECASE)
    
    matches = statute_pattern.finditer(text)
    seen_statutes = set()
    
    for match in matches:
        section = match.group(1).strip()
        act_name_raw = match.group(2).strip()
        
        # Simple normalization map to handle variations
        act_mapping = {
            'cgst': 'Central Goods and Services Tax Act, 2017',
            'central goods': 'Central Goods and Services Tax Act, 2017',
            'income tax': 'Income-tax Act, 1961',
            'ita': 'Income-tax Act, 1961',
            'companies': 'Companies Act, 2013',
            'negotiable': 'Negotiable Instruments Act, 1881',
            'ibc': 'Insolvency and Bankruptcy Code, 2016',
            'insolvency': 'Insolvency and Bankruptcy Code, 2016',
            'bns': 'Bharatiya Nyaya Sanhita, 2023',
            'bnss': 'Bharatiya Nagarik Suraksha Sanhita, 2023',
            'arbitration': 'Arbitration and Conciliation Act, 1996',
            'contract': 'Indian Contract Act, 1872',
            'limitation': 'Limitation Act, 1963',
            'sebi': 'Securities and Exchange Board of India Act, 1992',
            'pmla': 'Prevention of Money Laundering Act, 2002',
            'fema': 'Foreign Exchange Management Act, 1999',
            'rera': 'Real Estate (Regulation and Development) Act, 2016',
            'consumer protection': 'Consumer Protection Act, 2019'
        }
        
        normalized_act = None
        for key, value in act_mapping.items():
            if key in act_name_raw.lower():
                normalized_act = value
                break
                
        if normalized_act:
            key = f"{section}_{normalized_act}"
            if key not in seen_statutes:
                seen_statutes.add(key)
                
                # Check DB for text preview
                try:
                    statute_doc = await statute_collection.find_one({
                        "act": normalized_act,
                        "section": {'$regex': f'^{section}$', '$options': 'i'}
                    })
                    
                    if statute_doc:
                        citations.append({
                            "type": "statute",
                            "match_text": match.group(0),
                            "section": section,
                            "act": normalized_act,
                            "text_preview": statute_doc.get("text", "Text unavailable")[:800] + "...",
                            "is_verified": True
                        })
                    else:
                         citations.append({
                            "type": "statute",
                            "match_text": match.group(0),
                            "section": section,
                            "act": act_name_raw,
                            "is_verified": False
                        })
                except Exception as e:
                    logger.error(f"Error finding statute citation: {e}")
                    
    # 2. Look for Case Law (Basic v. / vs. pattern)
    # E.g., Kesavananda Bharati v. State of Kerala, Tata Consultancy Services vs State of A.P
    case_pattern = re.compile(r'([A-Z][A-Za-z\.\-\'\d\s]+)\s+(?:v\.|vs\.|versus)\s+([A-Z][A-Za-z\.\-\'\d\s]+)', re.IGNORECASE)

    seen_cases = set()
    case_verification_tasks = []

    for match in case_pattern.finditer(text):
        party1 = match.group(1).strip()
        party2 = match.group(2).strip()

        # Exclude common false positives
        if len(party1) < 3 or len(party2) < 3 or "section" in party1.lower() or "section" in party2.lower():
            continue

        case_name = f"{party1} v. {party2}"
        if case_name not in seen_cases:
            seen_cases.add(case_name)
            case_verification_tasks.append((match.group(0), case_name))

    # Verify cases against IndianKanoon in parallel
    if case_verification_tasks:
        ik_key = os.environ.get("INDIANKANOON_API_KEY", "")
        for match_text, case_name in case_verification_tasks:
            query_str = case_name.replace(" ", "+")
            kanoon_url = f"https://indiankanoon.org/search/?formInput={query_str}"
            is_verified = False
            court = ""
            year = ""

            if ik_key:
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as ik_session:
                        async with ik_session.post(
                            "https://api.indiankanoon.org/search/",
                            headers={"Authorization": f"Token {ik_key}"},
                            data={"formInput": case_name, "pagenum": 0},
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                docs = data.get("docs", [])
                                if docs:
                                    top = docs[0]
                                    top_title = top.get("title", "").lower()
                                    # Check if any word from each party name appears in results
                                    p1_words = [w.lower() for w in party1.split() if len(w) > 2]
                                    p2_words = [w.lower() for w in party2.split() if len(w) > 2]
                                    p1_match = any(w in top_title for w in p1_words[:3])
                                    p2_match = any(w in top_title for w in p2_words[:3])
                                    is_verified = p1_match and p2_match
                                    if is_verified:
                                        # Extract court/year from the verified result
                                        import re as _re
                                        yr = _re.search(r'\b(19|20)\d{2}\b', top.get("title", ""))
                                        year = yr.group() if yr else ""
                                        t = top.get("title", "").lower()
                                        if "supreme court" in t:
                                            court = "Supreme Court of India"
                                        elif "high court" in t:
                                            court = "High Court"
                                        elif "itat" in t:
                                            court = "ITAT"
                                        elif "cestat" in t:
                                            court = "CESTAT"
                except Exception as e:
                    logger.warning(f"Case verification failed for {case_name}: {e}")

            citation_entry = {
                "type": "caselaw",
                "match_text": match_text,
                "case_name": case_name,
                "link": kanoon_url,
                "is_verified": is_verified,
            }
            if court:
                citation_entry["court"] = court
            if year:
                citation_entry["year"] = year
            if not is_verified:
                citation_entry["verification_note"] = "Could not verify on IndianKanoon — confirm independently"
            citations.append(citation_entry)

    return citations
