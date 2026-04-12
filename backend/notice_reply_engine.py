"""
Notice Auto-Reply Engine — The Killer Feature.
Upload a tax notice PDF → System reads it → Extracts notice type, section, demand →
Auto-drafts a structured 10-point legal reply with case law citations.

This is what CAs will pay Rs 10,000/month for. No competitor does this.
"""
import os
import re
import logging
import aiohttp
from datetime import datetime
from typing import Optional
from practice_tools import check_notice_validity

logger = logging.getLogger(__name__)

GOOGLE_AI_KEY = os.environ.get("GOOGLE_AI_KEY", "")
GROQ_KEY = os.environ.get("GROQ_KEY", "")


# Regex patterns to extract structured data from Indian tax notices
NOTICE_PATTERNS = {
    "gstin": r'GSTIN[:\s]*(\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z\d]{2})',
    "din": r'DIN[:\s]*([A-Z0-9]{15,20})',
    "section_73": r'[Ss]ection\s*73',
    "section_74": r'[Ss]ection\s*74',
    "section_143": r'[Ss]ection\s*143\s*\(\s*2\s*\)',
    "section_148": r'[Ss]ection\s*148[A]?',
    "section_147": r'[Ss]ection\s*147',
    "section_271": r'[Ss]ection\s*271',
    "section_270A": r'[Ss]ection\s*270\s*A',
    "drc_01": r'DRC[\s-]*01',
    "drc_01a": r'DRC[\s-]*01[Aa]',
    "asmt_10": r'ASMT[\s-]*10',
    "demand_amount": r'(?:demand|tax\s+payable|amount\s+payable|total\s+demand|tax\s+due)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
    "financial_year": r'(?:F\.?Y\.?|financial\s+year|FY)[:\s]*(\d{4}[\s-]+\d{2,4})',
    "assessment_year": r'(?:A\.?Y\.?|assessment\s+year|AY)[:\s]*(\d{4}[\s-]+\d{2,4})',
    "date_of_notice": r'(?:Date|Dated)[:\s]*(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4})',
    "reply_deadline": r'(?:within|before|latest\s+by|on\s+or\s+before)[:\s]*(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4})',
    "penalty_amount": r'(?:penalty|fine)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
    "interest_amount": r'(?:interest)[:\s]*(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d{1,2})?)',
}


def extract_notice_metadata(text: str) -> dict:
    """Extract structured data from notice text using regex patterns."""
    metadata = {}

    for key, pattern in NOTICE_PATTERNS.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            if key in ("demand_amount", "penalty_amount", "interest_amount"):
                # Clean amount strings
                amounts = [float(m.replace(",", "")) for m in matches if m.replace(",", "").replace(".", "").isdigit()]
                if amounts:
                    metadata[key] = max(amounts)  # Take the largest (usually the total demand)
            elif key in ("section_73", "section_74", "section_143", "section_148", "section_147",
                         "section_271", "section_270A", "drc_01", "drc_01a", "asmt_10"):
                metadata[key] = True
            else:
                metadata[key] = matches[0] if len(matches) == 1 else matches

    # Determine notice type
    notice_type = "Unknown"
    if metadata.get("section_74"):
        notice_type = "GST SCN (Section 74 — Fraud/Suppression)"
    elif metadata.get("section_73"):
        notice_type = "GST SCN (Section 73 — Non-fraud)"
    elif metadata.get("drc_01") or metadata.get("drc_01a"):
        notice_type = "GST DRC-01/DRC-01A (ITC Mismatch)"
    elif metadata.get("asmt_10"):
        notice_type = "GST ASMT-10 (Scrutiny)"
    elif metadata.get("section_148"):
        notice_type = "Income Tax Reassessment (Section 148/148A)"
    elif metadata.get("section_143"):
        notice_type = "Income Tax Scrutiny (Section 143(2))"
    elif metadata.get("section_271") or metadata.get("section_270A"):
        notice_type = "Income Tax Penalty"
    elif metadata.get("section_147"):
        notice_type = "Income Tax Reassessment (Section 147)"

    metadata["notice_type"] = notice_type
    return metadata


REPLY_SYSTEM_PROMPT = """You are a Senior Tax Counsel with 30 years of practice before the ITAT, High Courts, and Supreme Court of India. You are drafting a FORMAL LEGAL REPLY to a tax notice on behalf of a client.

CRITICAL RULES:
1. The reply must be in FORMAL LEGAL LANGUAGE suitable for filing before a quasi-judicial authority.
2. EVERY defense point must cite the EXACT section, sub-section, proviso, rule, or case law.
3. Structure the reply with numbered paragraphs (Para 1, Para 2, etc.) — this is Indian legal drafting standard.
4. Include proper cause title format at the top.
5. Include a prayer clause at the end.
6. For GST notices: ALWAYS check S.73 vs S.74 classification first. ALWAYS calculate S.74(5) pre-adjudication option.
7. For IT notices: ALWAYS check limitation, DIN compliance, and natural justice.
8. Cite at LEAST 5 relevant Supreme Court / High Court / ITAT precedents. Use REAL cases only.
9. Include a Section 74(5) / settlement computation if applicable.
10. End with: "It is therefore most respectfully prayed that the Honourable Authority may be pleased to..."

FORMATTING:
- Use proper legal paragraph numbering: 1., 2., 3., etc.
- Use "It is respectfully submitted that..." for each defense point
- Bold the section numbers and case names
- Include the standard objection: "The above reply is without prejudice to the assessee's right to raise additional grounds."
"""


async def generate_notice_reply(notice_text: str, client_name: str = "",
                                 additional_context: str = "") -> dict:
    """
    The crown jewel: Upload a notice, get a structured legal reply.
    Returns: extracted metadata + auto-drafted reply + validity check.
    """
    # Step 1: Extract metadata from notice
    metadata = extract_notice_metadata(notice_text)
    logger.info(f"Notice metadata extracted: {metadata.get('notice_type', 'Unknown')}")

    # Step 2: Check notice validity automatically
    validity = {}
    notice_date = ""
    if metadata.get("date_of_notice"):
        raw_date = metadata["date_of_notice"]
        if isinstance(raw_date, list):
            raw_date = raw_date[0]
        # Try to parse the date
        for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y"]:
            try:
                parsed = datetime.strptime(raw_date, fmt)
                notice_date = parsed.strftime("%Y-%m-%d")
                break
            except ValueError:
                continue

    if notice_date:
        notice_type_for_check = ""
        if metadata.get("section_74"):
            notice_type_for_check = "74"
        elif metadata.get("section_73"):
            notice_type_for_check = "73"
        elif metadata.get("section_148"):
            notice_type_for_check = "148"
        elif metadata.get("section_143"):
            notice_type_for_check = "143(2)"

        if notice_type_for_check:
            fy = metadata.get("financial_year", "")
            ay = metadata.get("assessment_year", "")
            if isinstance(fy, list): fy = fy[0]
            if isinstance(ay, list): ay = ay[0]

            validity = check_notice_validity(
                notice_type=notice_type_for_check,
                notice_date=notice_date,
                financial_year=fy,
                assessment_year=ay,
                has_din=bool(metadata.get("din")),
                is_fraud_alleged=bool(metadata.get("section_74")),
            )

    # Step 3: Build the reply generation prompt
    demand_str = f"Rs {metadata.get('demand_amount', 0):,.2f}" if metadata.get('demand_amount') else "Not specified"

    validity_context = ""
    if validity and validity.get("challenge_grounds"):
        validity_context = "\n\nAUTO-DETECTED VALIDITY ISSUES:\n"
        for challenge in validity["challenge_grounds"]:
            validity_context += f"- {challenge['ground']}: {challenge['legal_basis']} ({challenge['severity']})\n"

    reply_prompt = f"""DRAFT A FORMAL LEGAL REPLY to the following tax notice.

NOTICE TYPE: {metadata.get('notice_type', 'Tax Notice')}
NOTICE DATE: {notice_date or 'Not extracted'}
DEMAND AMOUNT: {demand_str}
FINANCIAL YEAR: {metadata.get('financial_year', 'Not specified')}
ASSESSMENT YEAR: {metadata.get('assessment_year', 'Not specified')}
GSTIN: {metadata.get('gstin', 'Not specified')}
DIN: {metadata.get('din', 'Not found — POTENTIAL VALIDITY ISSUE')}
CLIENT: {client_name or '[Client Name]'}
{validity_context}

FULL NOTICE TEXT:
{notice_text[:30000]}

{f"ADDITIONAL CLIENT INSTRUCTIONS: {additional_context}" if additional_context else ""}

DRAFT THE COMPLETE REPLY NOW. Include:
1. Proper cause title and reference
2. Preliminary objections (limitation, jurisdiction, DIN, natural justice)
3. Substantive defense on merits (minimum 10 numbered paragraphs)
4. At least 5 case law citations (REAL cases only)
5. Financial computation (if applicable)
6. Prayer clause
"""

    # Step 4: Generate reply via best available model
    reply_text = ""

    if GOOGLE_AI_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GOOGLE_AI_KEY}"
            payload = {
                "system_instruction": {"parts": [{"text": REPLY_SYSTEM_PROMPT}]},
                "contents": [{"role": "user", "parts": [{"text": reply_prompt}]}],
                "tools": [{"googleSearch": {}}],
                "generationConfig": {"temperature": 0.05, "maxOutputTokens": 16384}
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, headers={"Content-Type": "application/json"},
                    json=payload, timeout=aiohttp.ClientTimeout(total=120)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        candidate = data.get("candidates", [{}])[0]
                        parts = candidate.get("content", {}).get("parts", [])
                        reply_text = "\n".join([p.get("text", "") for p in parts if "text" in p])

                        # Extract grounding URLs
                        grounding = candidate.get("groundingMetadata", {})
                        web_chunks = grounding.get("groundingChunks", [])
                        if web_chunks:
                            urls = list(set(c.get("web", {}).get("uri", "") for c in web_chunks if c.get("web", {}).get("uri")))
                            if urls:
                                reply_text += "\n\n---\n**Case Law Sources Verified via Live Search:**\n"
                                for u in urls[:10]:
                                    reply_text += f"- {u}\n"
        except Exception as e:
            logger.error(f"Gemini reply generation error: {e}")

    # Fallback: Groq
    if not reply_text and GROQ_KEY:
        try:
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": REPLY_SYSTEM_PROMPT},
                    {"role": "user", "content": reply_prompt[:25000]}
                ],
                "temperature": 0.05,
                "max_tokens": 8192
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                    json=payload, timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        reply_text = data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Groq reply generation error: {e}")

    if not reply_text:
        reply_text = "Error: Could not generate reply. Please check API keys."

    return {
        "notice_metadata": metadata,
        "notice_type": metadata.get("notice_type", "Unknown"),
        "demand_amount": metadata.get("demand_amount", 0),
        "financial_year": metadata.get("financial_year", ""),
        "assessment_year": metadata.get("assessment_year", ""),
        "validity_check": validity,
        "is_notice_valid": validity.get("overall_validity", "Not checked"),
        "auto_reply": reply_text,
        "reply_ready": bool(reply_text and "Error" not in reply_text[:20]),
        "export_hint": "Use the DOCX export button to generate a formatted Word document ready for filing.",
    }
