"""
Response Augmenter — Inline verification, math checking, and trust annotation.

After a response is generated, this module:
1. Inline-annotates every case citation with [✓ Verified on IK] or [⚠ Unverified]
2. Inline-annotates every statute citation with [✓ Statute DB] or [⚠ Training]
3. Verifies arithmetic in tax/interest/penalty computations
4. Injects a "Verification Report" summary at the end of the response
5. Flags stale amendment-vulnerable citations

This is what actually makes lawyers trust the output — they can see, for every
single claim, whether it was independently verified or not.
"""
import re
import os
import json
import asyncio
import logging
from typing import Optional
import aiohttp

logger = logging.getLogger("response_augmenter")

IK_API_KEY = os.environ.get("INDIANKANOON_API_KEY", "")


# ==================== STATUTE CITATION VERIFICATION ====================

_STATUTE_PATTERN = re.compile(
    r'(Section|Sec\.|u/s|under\s+Section)\s*(\d+[A-Za-z]*(?:\([a-z0-9ivxIVX]+\))*(?:\([a-z0-9ivxIVX]+\))*)'
    r'(?:\s+of\s+(?:the\s+)?([A-Za-z,&\-\s]+?(?:Act|Code|Rules|Regulations)(?:,\s*\d{4})?))?',
    re.IGNORECASE
)

_ACT_CANONICAL = {
    "cgst": "Central Goods and Services Tax Act, 2017",
    "central goods": "Central Goods and Services Tax Act, 2017",
    "gst act": "Central Goods and Services Tax Act, 2017",
    "igst": "Integrated Goods and Services Tax Act, 2017",
    "income tax": "Income-tax Act, 1961",
    "income-tax": "Income-tax Act, 1961",
    "ita": "Income-tax Act, 1961",
    "it act": "Income-tax Act, 1961",
    "companies": "Companies Act, 2013",
    "negotiable": "Negotiable Instruments Act, 1881",
    "ibc": "Insolvency and Bankruptcy Code, 2016",
    "insolvency": "Insolvency and Bankruptcy Code, 2016",
    "bns": "Bharatiya Nyaya Sanhita, 2023",
    "bnss": "Bharatiya Nagarik Suraksha Sanhita, 2023",
    "bsa": "Bharatiya Sakshya Adhiniyam, 2023",
    "ipc": "Indian Penal Code, 1860",
    "crpc": "Code of Criminal Procedure, 1973",
    "iea": "Indian Evidence Act, 1872",
    "arbitration": "Arbitration and Conciliation Act, 1996",
    "contract act": "Indian Contract Act, 1872",
    "limitation": "Limitation Act, 1963",
    "sebi": "Securities and Exchange Board of India Act, 1992",
    "pmla": "Prevention of Money Laundering Act, 2002",
    "fema": "Foreign Exchange Management Act, 1999",
    "rera": "Real Estate (Regulation and Development) Act, 2016",
    "consumer": "Consumer Protection Act, 2019",
    "finance act": "Finance Act",
    "benami": "Prohibition of Benami Property Transactions Act, 1988",
    "black money": "Black Money (Undisclosed Foreign Income and Assets) Act, 2015",
    "fcra": "Foreign Contribution (Regulation) Act, 2010",
    "customs": "Customs Act, 1962",
}


def _canonicalize_act(act_raw: str) -> Optional[str]:
    """Map user-facing act name → canonical DB name."""
    if not act_raw:
        return None
    lower = act_raw.lower().strip()
    for key, canonical in _ACT_CANONICAL.items():
        if key in lower:
            return canonical
    return None


# ==================== CASE CITATION VERIFICATION ====================

_CASE_PATTERN = re.compile(
    r'\b([A-Z][A-Za-z\.\-\'&\s]{2,60}?)\s+(?:v\.|vs\.?|versus)\s+'
    r'([A-Z][A-Za-z\.\-\'&\s\d]{2,60}?)(?:[,\s]+(?:\((\d{4})\)|\[(\d{4})\])?)',
    re.UNICODE
)

# Cases with known amendment warnings — always annotate these
_AMENDMENT_WARNINGS = {
    r'smifs\s+securities': '[⚠ Post-FY2021 goodwill excluded from S.32 depreciation]',
    r'vodafone\s+international': '[⚠ Retrospectively overridden by Finance Act 2012/2021]',
    r'larsen\s+(?:&|and)\s+toubro.*?\b2014\b': '[⚠ Pre-GST — cite S.7 CGST for barter]',
    r'ge\s+india\s+technology': '[⚠ Finance Act 2020 expanded royalty definition]',
    r'kelvinator\s+of\s+india': '[✓ Still good law — S.147 reopening "change of opinion"]',
    r'ashish\s+agarwal': '[✓ Still good law — S.148A procedural mandate]',
    r'checkmate\s+(?:services|fiscal)': '[✓ Binding — PF/ESI employer contribution permanent disallowance]',
}


async def _verify_case_on_ik(session: aiohttp.ClientSession, case_name: str) -> dict:
    """Live IndianKanoon verification of a case citation.

    Scans top 10 results (not just top 1) because IK relevance ranking is not perfect.
    Accepts if ANY top-10 result matches both party names.
    """
    if not IK_API_KEY:
        return {"verified": False, "reason": "No IK API key", "source": "ik"}

    # Use quoted party names for better precision
    parts = case_name.lower().split(" v. ") if " v. " in case_name.lower() else case_name.lower().split(" vs ")
    if len(parts) != 2:
        return {"verified": False, "reason": "Parse error", "source": "ik"}
    p1, p2 = parts[0].strip(), parts[1].strip()

    # Query with each party name quoted (IK supports + AND, quotes for phrases)
    # First try: exact-phrase search for the primary party
    try_queries = [
        f'"{p1}"',  # Just primary party — usually unique enough
        case_name,   # Full case name
    ]

    p1_words = [w for w in p1.split() if len(w) > 2][:4]
    p2_words = [w for w in p2.split() if len(w) > 2][:4]

    try:
        for q in try_queries:
            async with session.post(
                "https://api.indiankanoon.org/search/",
                headers={"Authorization": f"Token {IK_API_KEY}"},
                data={"formInput": q, "pagenum": 0},
                timeout=aiohttp.ClientTimeout(total=6),
            ) as resp:
                if resp.status != 200:
                    continue
                data = await resp.json()
                docs = data.get("docs", [])
                if not docs:
                    continue

                # Scan TOP 10 results (not just #1), because IK relevance isn't perfect
                for doc in docs[:10]:
                    title_raw = doc.get("title", "")
                    # Strip <b> tags and lowercase
                    title = re.sub(r'<[^>]+>', '', title_raw).lower()

                    # Both party names must have fuzzy hits IN THIS result
                    p1_hit = any(w in title for w in p1_words)
                    p2_hit = any(w in title for w in p2_words)

                    if p1_hit and p2_hit:
                        yr = re.search(r'\b(19|20)\d{2}\b', title_raw)
                        # Court detection from title/docsource
                        docsource = (doc.get("docsource") or "").lower()
                        combined_ct = f"{title} {docsource}"
                        if "supreme court" in combined_ct:
                            court = "SC"
                        elif "high court" in combined_ct:
                            court = "HC"
                        elif "itat" in combined_ct or "income tax appellate" in combined_ct:
                            court = "ITAT"
                        elif "cestat" in combined_ct:
                            court = "CESTAT"
                        elif "nclt" in combined_ct or "nclat" in combined_ct:
                            court = "NCLT"
                        else:
                            court = ""
                        return {
                            "verified": True,
                            "doc_id": doc.get("tid", ""),
                            "court": court,
                            "year": yr.group() if yr else "",
                            "url": f"https://indiankanoon.org/doc/{doc.get('tid', '')}/",
                            "source": "ik",
                            "matched_title": title_raw[:100],
                        }

        return {"verified": False, "reason": "No top-10 match on IK", "source": "ik"}
    except Exception as e:
        return {"verified": False, "reason": f"Exception: {type(e).__name__}", "source": "ik"}


# Authoritative legal sources — a hit on these means the case is real
_AUTHORITATIVE_LEGAL_DOMAINS = [
    "indiankanoon.org", "scconline.com", "manupatra.com", "casemine.com",
    "livelaw.in", "barandbench.com", "latestlaws.com", "legitquest.com",
    "main.sci.gov.in", "judgments.ecourts.gov.in", "itat.gov.in", "cestat.gov.in",
    "nclt.gov.in", "nclat.gov.in", "itatonline.org", "taxmann.com",
    "taxguru.in", "taxscan.in", "legalcrystal.com",
]


async def _verify_case_via_web(session: aiohttp.ClientSession, case_name: str) -> dict:
    """Fallback: search Serper (Google) and DuckDuckGo to check if case exists.

    Returns verified=True only if we find the case on at least one authoritative legal domain.
    """
    parts = case_name.lower().split(" v. ") if " v. " in case_name.lower() else case_name.lower().split(" vs ")
    if len(parts) != 2:
        return {"verified": False, "reason": "Parse error", "source": "web"}
    p1_words = [w for w in parts[0].strip().split() if len(w) > 2][:3]
    p2_words = [w for w in parts[1].strip().split() if len(w) > 2][:3]

    # Try Serper first (more reliable, Google results)
    serper_key = os.environ.get("SERPER_API_KEY", "")
    if serper_key:
        try:
            search_query = f'"{case_name}" India judgment'
            async with session.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
                json={"q": search_query, "num": 10, "gl": "in"},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    organic = data.get("organic", [])
                    for result in organic[:10]:
                        link = (result.get("link") or "").lower()
                        title = (result.get("title") or "").lower()
                        snippet = (result.get("snippet") or "").lower()
                        combined = f"{title} {snippet}"

                        # Authoritative source check
                        is_authoritative = any(dom in link for dom in _AUTHORITATIVE_LEGAL_DOMAINS)
                        # Fuzzy match both party names in title+snippet
                        p1_hit = any(w in combined for w in p1_words)
                        p2_hit = any(w in combined for w in p2_words)

                        if is_authoritative and p1_hit and p2_hit:
                            # Which court?
                            court = ""
                            if "supreme court" in combined or "sci.gov.in" in link:
                                court = "SC"
                            elif "high court" in combined:
                                court = "HC"
                            elif "itat" in combined:
                                court = "ITAT"
                            elif "cestat" in combined:
                                court = "CESTAT"

                            # Which domain?
                            matched_domain = next((dom for dom in _AUTHORITATIVE_LEGAL_DOMAINS if dom in link), "")

                            yr = re.search(r'\b(19|20)\d{2}\b', combined)
                            return {
                                "verified": True,
                                "court": court,
                                "year": yr.group() if yr else "",
                                "url": result.get("link", ""),
                                "source": "serper",
                                "matched_domain": matched_domain,
                            }
                    return {"verified": False, "reason": "No authoritative hit on Serper", "source": "serper"}
        except Exception as e:
            logger.warning(f"Serper case verification failed: {e}")

    # Fallback to DuckDuckGo HTML (no key required)
    # Stricter check: parse actual result <a> links and their snippets — not just HTML substring match
    try:
        from urllib.parse import quote_plus, urlparse
        query = f'"{case_name}" India judgment'
        ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        async with session.get(ddg_url, timeout=aiohttp.ClientTimeout(total=5), headers={"User-Agent": "Mozilla/5.0"}) as resp:
            if resp.status == 200:
                html = await resp.text()
                # Extract individual result blocks — each result has a link + title
                # DDG HTML format: <a class="result__a" href="...">Title</a> then <a class="result__snippet">snippet
                result_pattern = re.compile(
                    r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>.*?<a[^>]*class="result__snippet"[^>]*>([^<]+)',
                    re.DOTALL | re.IGNORECASE
                )
                for m in result_pattern.finditer(html):
                    link = m.group(1)
                    title = m.group(2).lower()
                    snippet = m.group(3).lower()
                    combined = f"{title} {snippet}"

                    # Extract actual domain from link (DDG wraps urls in redirect)
                    # DDG redirect format: //duckduckgo.com/l/?uddg=<encoded-url>
                    import urllib.parse as _up
                    actual_url = link
                    if "uddg=" in link:
                        m2 = re.search(r'uddg=([^&]+)', link)
                        if m2:
                            actual_url = _up.unquote(m2.group(1))
                    try:
                        domain = urlparse(actual_url).netloc.lower().replace("www.", "")
                    except Exception:
                        domain = ""

                    # Must be on authoritative domain AND both parties must appear in title/snippet of THIS result
                    is_authoritative = any(dom in domain for dom in _AUTHORITATIVE_LEGAL_DOMAINS)
                    p1_hit = any(w in combined for w in p1_words)
                    p2_hit = any(w in combined for w in p2_words)

                    if is_authoritative and p1_hit and p2_hit:
                        court = "SC" if "supreme court" in combined else "HC" if "high court" in combined else ""
                        yr = re.search(r'\b(19|20)\d{2}\b', combined)
                        return {
                            "verified": True,
                            "court": court,
                            "year": yr.group() if yr else "",
                            "url": actual_url,
                            "source": "duckduckgo",
                            "matched_domain": domain,
                        }
                return {"verified": False, "reason": "No authoritative result on DDG", "source": "duckduckgo"}
    except Exception as e:
        logger.warning(f"DDG case verification failed: {e}")

    return {"verified": False, "reason": "All verification sources exhausted", "source": "all"}


async def _verify_case_cascade(session: aiohttp.ClientSession, case_name: str) -> dict:
    """Cascade verification: IndianKanoon → Serper → DuckDuckGo.

    This gives us the highest possible coverage. Unreported/recent cases that IK missed
    often show up on SCC Online/LiveLaw/Taxmann via Google.
    """
    # 1. Try IndianKanoon first (most authoritative for Indian case law)
    ik_result = await _verify_case_on_ik(session, case_name)
    if ik_result.get("verified"):
        return ik_result

    # 2. Fallback to Serper/DDG web search
    web_result = await _verify_case_via_web(session, case_name)
    if web_result.get("verified"):
        # Preserve info about where it was found
        web_result["fallback_note"] = "Not on IK but found via web on authoritative source"
        return web_result

    # 3. Nothing found — genuinely unverified
    return {
        "verified": False,
        "reason": f"IK: {ik_result.get('reason', 'no')}; Web: {web_result.get('reason', 'no')}",
        "source": "cascade_failed",
    }


async def _verify_statute_in_db(section: str, act_canonical: str, db) -> bool:
    """Check if the section exists in MongoDB statute DB."""
    if db is None or not act_canonical:
        return False
    try:
        doc = await db.master_statutes.find_one({
            "act": act_canonical,
            "section": {"$regex": f"^{re.escape(section)}$", "$options": "i"},
        })
        return doc is not None
    except Exception as e:
        logger.warning(f"Statute DB check failed: {e}")
        return False


async def _verify_statute_on_web(session: aiohttp.ClientSession, section: str, act: str) -> dict:
    """Fallback: search Serper for the statute section on authoritative sources."""
    serper_key = os.environ.get("SERPER_API_KEY", "")
    if not serper_key:
        return {"verified": False, "reason": "No Serper key"}

    try:
        query = f'"Section {section}" "{act}" India'
        async with session.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
            json={"q": query, "num": 5, "gl": "in"},
            timeout=aiohttp.ClientTimeout(total=5),
        ) as resp:
            if resp.status != 200:
                return {"verified": False, "reason": f"Serper status {resp.status}"}
            data = await resp.json()
            organic = data.get("organic", [])
            # Consider verified if a gov/authoritative source returns the section
            auth_gov_domains = [
                "indiacode.nic.in", "incometaxindia.gov.in", "cbic-gst.gov.in",
                "mca.gov.in", "rbi.org.in", "sebi.gov.in", "egazette.nic.in",
                "indiankanoon.org", "taxmann.com", "cleartax.in", "taxguru.in",
            ]
            for result in organic[:5]:
                link = (result.get("link") or "").lower()
                title = (result.get("title") or "").lower()
                snippet = (result.get("snippet") or "").lower()

                # Must mention the section AND be on authoritative domain
                if any(dom in link for dom in auth_gov_domains):
                    if str(section).lower() in f"{title} {snippet}":
                        matched_domain = next((dom for dom in auth_gov_domains if dom in link), "")
                        return {
                            "verified": True,
                            "url": result.get("link", ""),
                            "source": "serper",
                            "matched_domain": matched_domain,
                        }
            return {"verified": False, "reason": "No authoritative hit"}
    except Exception as e:
        return {"verified": False, "reason": f"Exception: {type(e).__name__}"}


async def _verify_statute_cascade(session: aiohttp.ClientSession, section: str, act_canonical: str, act_raw: str, db) -> dict:
    """Cascade: MongoDB → Serper (authoritative domains) → unverified."""
    # 1. MongoDB first (fastest, most authoritative when available)
    if await _verify_statute_in_db(section, act_canonical, db):
        return {"verified": True, "source": "db"}

    # 2. Web search fallback
    web_act = act_canonical or act_raw
    if web_act:
        web_result = await _verify_statute_on_web(session, section, web_act)
        if web_result.get("verified"):
            return web_result

    return {"verified": False, "reason": "Not in DB, not on authoritative web sources"}


# ==================== MATH VERIFICATION ====================

_INR_AMOUNT = re.compile(r'(?:₹|Rs\.?|INR|rupees?)\s*([\d,]+(?:\.\d+)?)\s*(crore|lakh|lac|thousand|cr|L)?', re.IGNORECASE)
_PERCENTAGE = re.compile(r'(\d+(?:\.\d+)?)\s*%')


def _normalize_inr(amount_str: str, unit: str = "") -> float:
    """Convert ₹ amount string to absolute rupees."""
    try:
        num = float(amount_str.replace(",", ""))
    except ValueError:
        return 0
    unit_lower = (unit or "").lower().strip()
    if unit_lower in ("crore", "cr"):
        return num * 10_000_000
    elif unit_lower in ("lakh", "lac", "l"):
        return num * 100_000
    elif unit_lower == "thousand":
        return num * 1_000
    return num


def extract_monetary_claims(response: str) -> list[dict]:
    """Extract all ₹ amounts from a response for auditing."""
    claims = []
    for m in _INR_AMOUNT.finditer(response):
        amount_str = m.group(1)
        unit = m.group(2) or ""
        absolute = _normalize_inr(amount_str, unit)
        claims.append({
            "raw": m.group(0),
            "absolute_rupees": absolute,
            "position": m.start(),
        })
    return claims


def _verify_arithmetic_sum(response: str) -> list[dict]:
    """Check if sums stated in the response are mathematically correct.

    Looks for patterns like:
      '₹X + ₹Y + ₹Z = ₹T'
      '₹X * 18% = ₹Y'
    """
    flags = []

    # Pattern: a + b = c (handles ₹ or Rs)
    _INR = r'(?:₹|Rs\.?|INR)'
    sum_pattern = re.compile(
        rf'{_INR}\s*([\d,]+(?:\.\d+)?)\s*(?:\+\s*{_INR}?\s*([\d,]+(?:\.\d+)?)\s*){{1,4}}=\s*{_INR}\s*([\d,]+(?:\.\d+)?)'
    )
    for m in sum_pattern.finditer(response):
        # Extract all numbers in this equation
        eq_text = m.group(0)
        numbers = re.findall(r'[\d,]+(?:\.\d+)?', eq_text)
        if len(numbers) < 3:
            continue
        try:
            nums = [float(n.replace(",", "")) for n in numbers]
            operands = nums[:-1]
            stated_total = nums[-1]
            actual_total = sum(operands)
            if abs(actual_total - stated_total) > max(1, stated_total * 0.01):  # >1% off
                flags.append({
                    "type": "arithmetic_error",
                    "equation": eq_text,
                    "stated_total": stated_total,
                    "actual_total": actual_total,
                    "error": abs(actual_total - stated_total),
                })
        except Exception:
            pass

    # Pattern: A * B% = C (handles ₹ or Rs)
    pct_pattern = re.compile(
        rf'{_INR}\s*([\d,]+(?:\.\d+)?)\s*(?:\*|×|x)\s*(\d+(?:\.\d+)?)\s*%\s*=\s*{_INR}\s*([\d,]+(?:\.\d+)?)'
    )
    for m in pct_pattern.finditer(response):
        try:
            base = float(m.group(1).replace(",", ""))
            pct = float(m.group(2))
            stated = float(m.group(3).replace(",", ""))
            actual = base * pct / 100
            if abs(actual - stated) > max(1, stated * 0.01):
                flags.append({
                    "type": "percentage_error",
                    "equation": m.group(0),
                    "stated": stated,
                    "actual": actual,
                })
        except Exception:
            pass

    return flags


# ==================== INLINE ANNOTATION ====================

async def augment_response(response: str, db=None, max_case_verifications: int = 10) -> dict:
    """Post-process a response with inline verification annotations.

    Returns dict:
      - augmented_text: response with inline [✓]/[⚠] tags next to each citation
      - stats: { verified_cases, unverified_cases, verified_statutes, unverified_statutes, math_errors }
      - trust_score: 0-100 overall confidence
      - verification_report: markdown block summarizing verification
    """
    if not response or len(response) < 100:
        return {
            "augmented_text": response,
            "stats": {},
            "trust_score": 0,
            "verification_report": "",
        }

    augmented = response
    stats = {
        "verified_cases": 0, "unverified_cases": 0,
        "verified_statutes": 0, "unverified_statutes": 0,
        "amendment_warnings": 0, "math_errors": 0,
    }
    verification_notes = []

    # ========== 1. STATUTE ANNOTATION (with cascade: DB → Serper) ==========
    statute_matches = list(_STATUTE_PATTERN.finditer(response))
    async with aiohttp.ClientSession() as session:
        # Run all statute verifications in parallel (DB + web cascade)
        statute_tasks = []
        for match in statute_matches:
            section = match.group(2).strip()
            act_raw = (match.group(3) or "").strip()
            canonical = _canonicalize_act(act_raw)
            statute_tasks.append((match, section, act_raw, canonical))

        if statute_tasks:
            results = await asyncio.gather(
                *[_verify_statute_cascade(session, section, canonical, act_raw, db)
                  for _, section, act_raw, canonical in statute_tasks],
                return_exceptions=True,
            )
        else:
            results = []

    # Process in reverse order so indices don't shift
    for (match, section, act_raw, canonical), verify_result in reversed(list(zip(statute_tasks, results))):
        if isinstance(verify_result, Exception):
            verify_result = {"verified": False, "reason": "exception"}

        if not canonical and not verify_result.get("verified"):
            # Can't identify the Act and couldn't find on web — skip
            continue

        if verify_result.get("verified"):
            source = verify_result.get("source", "db")
            if source == "db":
                tag = " `[✓ DB]`"
            elif source == "serper":
                matched_domain = verify_result.get("matched_domain", "web")
                short_dom = matched_domain.replace(".com", "").replace(".org", "").replace(".in", "").replace(".gov", "")[:12]
                tag = f" `[✓ Gov: {short_dom}]`"
            else:
                tag = " `[✓ Verified]`"
            stats["verified_statutes"] += 1
        else:
            tag = " `[⚠ Verify]`"
            stats["unverified_statutes"] += 1
            verification_notes.append(f"Section {section} of {canonical or act_raw} — not found in DB or on authoritative web sources")

        # Insert tag right after the match
        end = match.end()
        after = augmented[end:end+15]
        if not after.startswith(" `["):
            augmented = augmented[:end] + tag + augmented[end:]

    # ========== 2. CASE ANNOTATION ==========
    case_matches = list(_CASE_PATTERN.finditer(response))[:max_case_verifications]
    async with aiohttp.ClientSession() as session:
        verification_tasks = []
        for match in case_matches:
            p1 = match.group(1).strip()
            p2 = match.group(2).strip()
            # Filter out false positives
            if len(p1) < 3 or len(p2) < 3:
                continue
            if any(bad in (p1 + p2).lower() for bad in ["section", "clause", "rule", "article"]):
                continue
            case_name = f"{p1} v. {p2}"
            verification_tasks.append((match, case_name))

        # Parallel verification using CASCADE: IK → Serper → DDG
        results = await asyncio.gather(
            *[_verify_case_cascade(session, cn) for _, cn in verification_tasks],
            return_exceptions=True,
        )

    # Build annotation plan (reversed order for stable indices)
    annotations = []
    for (match, case_name), verify_result in zip(verification_tasks, results):
        if isinstance(verify_result, Exception):
            verify_result = {"verified": False, "reason": "exception", "source": "error"}

        if verify_result.get("verified"):
            court = verify_result.get("court", "")
            source = verify_result.get("source", "ik")
            # Show which source verified it (so lawyer knows the provenance)
            if source == "ik":
                tag = f" `[✓ IK {court}]`" if court else " `[✓ IK]`"
            elif source == "serper":
                matched_domain = verify_result.get("matched_domain", "web")
                # Short domain name for tag
                short_dom = matched_domain.replace(".com", "").replace(".org", "").replace(".in", "").replace(".gov", "")[:12]
                tag = f" `[✓ Web: {short_dom}]`"
            elif source == "duckduckgo":
                tag = " `[✓ Web]`"
            else:
                tag = f" `[✓ {court}]`" if court else " `[✓]`"
            stats["verified_cases"] += 1
        else:
            tag = " `[⚠ Unverified]`"
            stats["unverified_cases"] += 1
            reason = verify_result.get("reason", "unknown")
            verification_notes.append(f"Case '{case_name}' — NOT found on IK, Serper, or DDG ({reason}). Confirm independently before filing.")

        # Check for amendment warnings
        case_lower = case_name.lower()
        for pattern, warning in _AMENDMENT_WARNINGS.items():
            if re.search(pattern, case_lower):
                tag += f" {warning}"
                stats["amendment_warnings"] += 1
                verification_notes.append(f"{case_name} — {warning}")
                break

        annotations.append((match.end(), tag))

    # Apply annotations in reverse
    for pos, tag in sorted(annotations, key=lambda x: -x[0]):
        after = augmented[pos:pos+15]
        if not after.startswith(" `["):
            augmented = augmented[:pos] + tag + augmented[pos:]

    # ========== 3. MATH VERIFICATION ==========
    math_flags = _verify_arithmetic_sum(response)
    stats["math_errors"] = len(math_flags)
    for flag in math_flags:
        verification_notes.append(
            f"Arithmetic error: '{flag['equation']}' — stated {flag.get('stated', flag.get('stated_total'))}, actual {flag.get('actual', flag.get('actual_total'))}"
        )

    # ========== 4. TRUST SCORE ==========
    total_claims = (
        stats["verified_cases"] + stats["unverified_cases"] +
        stats["verified_statutes"] + stats["unverified_statutes"]
    )
    if total_claims == 0:
        trust_score = 50  # Neutral — no verifiable claims
    else:
        verified = stats["verified_cases"] + stats["verified_statutes"]
        unverified = stats["unverified_cases"] + stats["unverified_statutes"]
        trust_score = int((verified / total_claims) * 100)
        # Penalize math errors heavily
        trust_score -= stats["math_errors"] * 10
        # Penalize amendment warnings (uncertainty)
        trust_score -= stats["amendment_warnings"] * 5
        trust_score = max(0, min(100, trust_score))

    # ========== 5. VERIFICATION REPORT ==========
    # No emoji — typography discipline bans them and they render literal on
    # some clients. Keep the Trust Layer footer clean and professional.
    report_lines = ["\n\n## Verification Report (Spectr Trust Layer)\n"]
    report_lines.append(f"**Trust Score: {trust_score}/100**")
    report_lines.append("")
    report_lines.append(f"| Check | Verified | Unverified |")
    report_lines.append(f"|---|---|---|")
    report_lines.append(f"| Case Citations | {stats['verified_cases']} | {stats['unverified_cases']} |")
    report_lines.append(f"| Statute Citations | {stats['verified_statutes']} | {stats['unverified_statutes']} |")
    report_lines.append(f"| Amendment Warnings | {stats['amendment_warnings']} | - |")
    report_lines.append(f"| Arithmetic Errors | - | {stats['math_errors']} |")
    report_lines.append("")

    if verification_notes:
        report_lines.append("**Verification Flags:**")
        for note in verification_notes[:8]:
            report_lines.append(f"- {note}")
        report_lines.append("")

    report_lines.append(f"**Legend:** `[✓ IK]` = verified on IndianKanoon live API | `[✓ DB]` = verified in MongoDB statute DB | `[⚠ Unverified]` = not independently verified — confirm before filing")

    verification_report = "\n".join(report_lines)

    return {
        "augmented_text": augmented + verification_report,
        "stats": stats,
        "trust_score": trust_score,
        "verification_report": verification_report,
        "notes": verification_notes,
    }


# ==================== PRE-RESPONSE DETERMINISTIC CALCULATOR ====================

def compute_tax_exposure(
    demand: float,
    notice_date_str: str,
    due_date_str: str,
    penalty_type: str = "under_reporting",
    rate: float = 18.0,  # GST S.50 default
) -> dict:
    """Deterministic computation of full tax + interest + penalty exposure.

    No LLM math — pure arithmetic we can trust.
    """
    from datetime import datetime as _dt
    try:
        notice = _dt.strptime(notice_date_str, "%Y-%m-%d")
        due = _dt.strptime(due_date_str, "%Y-%m-%d")
        days_elapsed = max(0, (notice - due).days)
        months_elapsed = days_elapsed / 30.0
    except Exception:
        days_elapsed = 0
        months_elapsed = 0

    # Interest (simple — per month as per S.50 GST / S.234B IT)
    interest = round(demand * (rate / 100) * months_elapsed / 12, 2)

    # Penalty scenarios
    penalty_map = {
        "under_reporting": 0.50,     # S.270A(7) - 50% of tax
        "misreporting": 2.00,         # S.270A(9) - 200%
        "s271_1_c_min": 1.00,         # S.271(1)(c) - 100% of tax
        "s271_1_c_max": 3.00,         # S.271(1)(c) - 300%
        "s122_gst": 0.10,             # S.122 GST - 10% of tax, min Rs 10k
        "s271c_tds": 1.00,            # S.271C TDS - equal to amount not deducted
    }
    penalty_factor = penalty_map.get(penalty_type, 0.50)
    penalty = round(demand * penalty_factor, 2)
    if penalty_type == "s122_gst":
        penalty = max(penalty, 10_000)

    total_exposure = round(demand + interest + penalty, 2)

    return {
        "principal_tax": demand,
        "interest": interest,
        "penalty": penalty,
        "total_exposure": total_exposure,
        "days_elapsed": days_elapsed,
        "months_elapsed": round(months_elapsed, 2),
        "rate_used": rate,
        "penalty_basis": penalty_type,
        "formula_breakdown": f"Principal ₹{demand:,.2f} + Interest [₹{demand:,.2f} × {rate}% × {months_elapsed:.1f}/12 months] ₹{interest:,.2f} + Penalty [{int(penalty_factor*100)}% of tax] ₹{penalty:,.2f} = **₹{total_exposure:,.2f}**",
    }
