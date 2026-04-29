"""
Structured Data Extraction Engine — Spectr Grade
Extracts structured, typed fields from legal documents, contracts, notices, and invoices.
Uses AI cascade (Gemini → Claude → GPT-4o → Groq) with JSON schema enforcement.

This is the kind of feature Harvey.ai charges enterprise prices for.
Spectr does it better — tuned for Indian law, Indian statutes, Indian formats.
"""
import os
import json
import re
import logging
import aiohttp
from datetime import datetime, timezone

logger = logging.getLogger("data_extraction")

GOOGLE_AI_KEY = os.environ.get("GOOGLE_AI_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_KEY = os.environ.get("OPENAI_KEY", "")
GROQ_KEY = os.environ.get("GROQ_KEY", "")

# ============================================================
# EXTRACTION SCHEMAS — what we extract from each document type
# ============================================================

EXTRACTION_SCHEMAS = {
    "contract": {
        "description": "Commercial contract, agreement, or MOU",
        "fields": {
            "contract_type": "Type of contract (e.g., Service Agreement, NDA, Joint Venture, Supply, Employment, Lease, Franchise)",
            "parties": "List of parties with their roles (e.g., [{name, role, address, gstin}])",
            "effective_date": "Date the contract takes effect (YYYY-MM-DD)",
            "expiry_date": "End date or term of the contract",
            "auto_renewal": "Whether the contract auto-renews (true/false) and on what terms",
            "governing_law": "Governing law and jurisdiction",
            "dispute_resolution": "Arbitration, mediation, or court — with seat/venue",
            "total_value": "Total contract value in INR (or currency + amount)",
            "payment_terms": "Payment schedule, due dates, milestones",
            "liability_cap": "Maximum aggregate liability, if capped",
            "indemnity_provisions": "Who indemnifies whom, for what, and any caps",
            "termination_clauses": "How either party can terminate — for cause, for convenience, notice period",
            "ip_ownership": "Who owns intellectual property created under the contract",
            "confidentiality_term": "Duration of confidentiality obligations post-termination",
            "non_compete": "Non-compete/non-solicitation restrictions with scope, geography, duration",
            "force_majeure": "Whether force majeure is included and what events it covers",
            "key_obligations": "List of key obligations for each party",
            "penalty_provisions": "Liquidated damages, late fees, or other penalties",
            "stamp_duty_state": "State under which stamp duty is applicable",
            "risk_flags": "List of risk issues found (one-sided clauses, missing protections, etc.)"
        }
    },
    "tax_notice": {
        "description": "Income Tax or GST notice from a tax authority",
        "fields": {
            "notice_type": "Type (Show Cause, Demand, Assessment, Scrutiny, Best Judgment, etc.)",
            "section": "Section under which notice is issued (e.g., 73, 74, 143(2), 148, 148A)",
            "issuing_authority": "Name and designation of the issuing officer",
            "authority_jurisdiction": "Jurisdiction — commissionerate, range, circle",
            "din_number": "Document Identification Number (DIN), if present",
            "notice_date": "Date of the notice (YYYY-MM-DD)",
            "reply_due_date": "Last date for reply/compliance",
            "taxpayer_name": "Name of the taxpayer/assessee",
            "taxpayer_pan": "PAN of the taxpayer",
            "taxpayer_gstin": "GSTIN, if applicable",
            "assessment_year": "Assessment year (e.g., 2023-24)",
            "financial_year": "Financial year",
            "tax_demanded": "Principal tax demand amount in INR",
            "interest_demanded": "Interest amount demanded",
            "penalty_demanded": "Penalty amount demanded",
            "total_demand": "Total demand (tax + interest + penalty)",
            "issues_raised": "List of issues/charges raised in the notice",
            "documents_requested": "List of documents requested for production",
            "hearing_date": "Personal hearing date, if scheduled",
            "limitation_expiry": "Date by which the notice must have been issued (limitation check)",
            "procedural_defects": "Any procedural defects found (missing DIN, no opportunity of hearing, etc.)",
            "risk_level": "Overall risk level: LOW, MEDIUM, HIGH, CRITICAL"
        }
    },
    "invoice": {
        "description": "Tax invoice, proforma invoice, or bill of supply",
        "fields": {
            "invoice_type": "Tax Invoice, Bill of Supply, Credit Note, Debit Note, Proforma",
            "invoice_number": "Invoice/document number",
            "invoice_date": "Date of invoice (YYYY-MM-DD)",
            "supplier_name": "Supplier/seller name",
            "supplier_gstin": "Supplier GSTIN",
            "supplier_address": "Supplier address with state",
            "recipient_name": "Buyer/recipient name",
            "recipient_gstin": "Recipient GSTIN",
            "recipient_address": "Recipient address with state",
            "place_of_supply": "Place of supply (state code + name)",
            "supply_type": "Interstate or Intrastate",
            "hsn_sac_codes": "List of HSN/SAC codes used",
            "line_items": "List of items [{description, hsn_sac, qty, unit_price, taxable_value, cgst_rate, sgst_rate, igst_rate, cess_rate}]",
            "taxable_value": "Total taxable value",
            "cgst_amount": "Total CGST amount",
            "sgst_amount": "Total SGST amount",
            "igst_amount": "Total IGST amount",
            "cess_amount": "Total cess amount",
            "total_tax": "Total tax amount",
            "grand_total": "Grand total (taxable + tax)",
            "reverse_charge": "Whether reverse charge applies (true/false)",
            "e_way_bill": "E-way bill number if present",
            "irn": "Invoice Reference Number (e-invoice IRN) if present",
            "itc_eligibility": "Whether ITC is claimable on this invoice and any restrictions",
            "compliance_issues": "Any compliance issues found (missing fields, wrong rates, etc.)"
        }
    },
    "court_order": {
        "description": "Court order, tribunal order, or judicial decision",
        "fields": {
            "court_name": "Name of the court/tribunal",
            "bench": "Bench composition (judge names)",
            "case_number": "Case/appeal/petition number",
            "case_title": "Full case title (Petitioner vs Respondent)",
            "order_date": "Date of the order (YYYY-MM-DD)",
            "order_type": "Interim, Final, Stay, Remand, Dismissal, etc.",
            "petitioner": "Petitioner/appellant name and details",
            "respondent": "Respondent name and details",
            "statutes_involved": "List of statutes and sections involved",
            "issues_framed": "Legal issues/questions framed by the court",
            "findings": "Key findings of the court on each issue",
            "ratio_decidendi": "The core legal principle established",
            "relief_granted": "What relief was granted or denied",
            "directions_given": "Specific directions issued by the court",
            "next_date": "Next hearing date, if any",
            "appeal_deadline": "Last date to file appeal against this order",
            "costs_awarded": "Whether costs were awarded and how much",
            "precedent_value": "Whether this creates a binding precedent and at what level"
        }
    },
    "legal_document": {
        "description": "General legal document — power of attorney, affidavit, will, trust deed, etc.",
        "fields": {
            "document_type": "Type of document",
            "execution_date": "Date of execution",
            "parties": "List of parties with roles",
            "subject_matter": "What the document deals with",
            "key_terms": "Key terms, conditions, or declarations",
            "operative_clauses": "The main operative parts of the document",
            "stamp_duty": "Whether stamp duty has been paid and on what value",
            "registration": "Whether the document requires/has registration",
            "witnesses": "Names of witnesses, if any",
            "notarization": "Whether notarized",
            "governing_law": "Applicable law",
            "risk_flags": "Any issues or risks identified"
        }
    }
}


EXTRACTION_PROMPT_TEMPLATE = """You are Spectr's Structured Data Extraction Engine — the most precise legal document parser for Indian law.

TASK: Extract ALL structured data fields from this document. Return a valid JSON object matching the schema exactly.

RULES:
1. Extract EXACTLY what the document says — do not infer, assume, or hallucinate.
2. If a field is not present in the document, set it to null — do NOT make up values.
3. For dates, use YYYY-MM-DD format. For amounts, use numbers without currency symbols.
4. For lists (like parties, line items, issues), return proper JSON arrays.
5. For risk_flags / compliance_issues / procedural_defects — actually analyze the document and flag real issues.
6. Be precise with section numbers — "Section 73" is different from "Section 74".
7. If the document references Indian law, use Indian legal terminology.

DOCUMENT TYPE: {doc_type}

SCHEMA (fields to extract):
{schema_json}

DOCUMENT TEXT:
{document_text}

Return ONLY a valid JSON object with the extracted fields. No markdown, no explanation, just the JSON.
"""


async def extract_structured_data(document_text: str, doc_type: str = "auto") -> dict:
    """Extract structured data from a document using AI.

    Args:
        document_text: The full text of the document
        doc_type: One of: contract, tax_notice, invoice, court_order, legal_document, auto

    Returns:
        dict with: extracted_data, doc_type, confidence, extraction_time
    """
    start_time = datetime.now(timezone.utc)

    # Auto-detect document type if not specified
    if doc_type == "auto":
        doc_type = _detect_document_type(document_text)

    schema = EXTRACTION_SCHEMAS.get(doc_type, EXTRACTION_SCHEMAS["legal_document"])

    prompt = EXTRACTION_PROMPT_TEMPLATE.format(
        doc_type=schema["description"],
        schema_json=json.dumps(schema["fields"], indent=2),
        document_text=document_text[:80000]  # Limit to ~80K chars
    )

    # Run through AI cascade
    result = await _extract_with_cascade(prompt)

    extraction_time = (datetime.now(timezone.utc) - start_time).total_seconds()

    if result:
        return {
            "success": True,
            "doc_type": doc_type,
            "doc_type_label": schema["description"],
            "extracted_data": result,
            "field_count": sum(1 for v in result.values() if v is not None),
            "total_fields": len(schema["fields"]),
            "extraction_time_seconds": round(extraction_time, 2),
        }

    return {
        "success": False,
        "doc_type": doc_type,
        "error": "Extraction failed across all AI models",
        "extraction_time_seconds": round(extraction_time, 2),
    }


async def batch_extract(documents: list, doc_type: str = "auto") -> list:
    """Extract structured data from multiple documents in parallel.

    Args:
        documents: List of {id, text, doc_type?} dicts
        doc_type: Default doc type if not specified per document

    Returns:
        List of extraction results with document IDs
    """
    import asyncio

    async def extract_one(doc):
        dt = doc.get("doc_type", doc_type)
        result = await extract_structured_data(doc["text"], dt)
        result["document_id"] = doc.get("id", "unknown")
        return result

    results = await asyncio.gather(*[extract_one(d) for d in documents], return_exceptions=True)

    processed = []
    for r in results:
        if isinstance(r, Exception):
            processed.append({"success": False, "error": str(r)})
        else:
            processed.append(r)
    return processed


def _detect_document_type(text: str) -> str:
    """Auto-detect the document type from content."""
    text_lower = text[:5000].lower()

    # Tax notice indicators
    notice_signals = [
        "show cause notice", "demand notice", "assessment order",
        "section 73", "section 74", "section 143", "section 148",
        "cgst act", "igst act", "income tax act", "penalty proceedings",
        "assessing officer", "commissioner", "adjudicating authority",
        "din:", "din number", "notice u/s", "notice under section"
    ]
    if sum(1 for s in notice_signals if s in text_lower) >= 3:
        return "tax_notice"

    # Invoice indicators
    invoice_signals = [
        "tax invoice", "invoice no", "invoice number", "bill of supply",
        "gstin", "hsn", "sac", "cgst", "sgst", "igst",
        "taxable value", "grand total", "place of supply",
        "credit note", "debit note"
    ]
    if sum(1 for s in invoice_signals if s in text_lower) >= 3:
        return "invoice"

    # Court order indicators
    court_signals = [
        "in the court of", "in the high court", "supreme court",
        "tribunal", "nclt", "itat", "appeal", "writ petition",
        "order dated", "the bench", "disposed of", "dismissed",
        "ratio decidendi", "allowed", "remanded"
    ]
    if sum(1 for s in court_signals if s in text_lower) >= 3:
        return "court_order"

    # Contract indicators
    contract_signals = [
        "agreement", "contract", "between", "party of the first part",
        "whereas", "now therefore", "mutual", "hereinafter",
        "indemnity", "termination", "governing law", "arbitration",
        "confidentiality", "non-compete", "force majeure",
        "executed on", "witness whereof"
    ]
    if sum(1 for s in contract_signals if s in text_lower) >= 3:
        return "contract"

    return "legal_document"


async def _extract_with_cascade(prompt: str) -> dict:
    """Run extraction through AI cascade. Returns parsed JSON dict or None."""

    # Tier 1: Gemini 2.5 Flash (fast, JSON mode)
    if GOOGLE_AI_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GOOGLE_AI_KEY}"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.05,
                    "maxOutputTokens": 16384,
                    "responseMimeType": "application/json"
                }
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload,
                                        timeout=aiohttp.ClientTimeout(total=90)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                        text = "".join([p.get("text", "") for p in parts if "text" in p])
                        result = _parse_json_safely(text)
                        if result:
                            logger.info(f"Extraction: Gemini Flash returned {len(result)} fields")
                            return result
        except Exception as e:
            logger.warning(f"Gemini extraction error: {e}")

    # Tier 2: Claude Sonnet
    if ANTHROPIC_KEY:
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 16384,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.05,
                }
                async with session.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": ANTHROPIC_KEY,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json=payload, timeout=aiohttp.ClientTimeout(total=90)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        text = "\n".join([b["text"] for b in data.get("content", []) if b.get("type") == "text"])
                        result = _parse_json_safely(text)
                        if result:
                            logger.info(f"Extraction: Claude returned {len(result)} fields")
                            return result
        except Exception as e:
            logger.warning(f"Claude extraction error: {e}")

    # Tier 3: GPT-4o (with JSON mode)
    if OPENAI_KEY:
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.05,
                    "max_tokens": 16384,
                    "response_format": {"type": "json_object"}
                }
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
                    json=payload, timeout=aiohttp.ClientTimeout(total=90)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        text = data["choices"][0]["message"]["content"]
                        result = _parse_json_safely(text)
                        if result:
                            logger.info(f"Extraction: GPT-4o returned {len(result)} fields")
                            return result
        except Exception as e:
            logger.warning(f"GPT-4o extraction error: {e}")

    # Tier 4: Groq LLaMA
    if GROQ_KEY:
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.05,
                    "max_tokens": 8000,
                    "response_format": {"type": "json_object"}
                }
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                    json=payload, timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        text = data["choices"][0]["message"]["content"]
                        result = _parse_json_safely(text)
                        if result:
                            logger.info(f"Extraction: Groq returned {len(result)} fields")
                            return result
        except Exception as e:
            logger.warning(f"Groq extraction error: {e}")

    return None


def _parse_json_safely(text: str) -> dict:
    """Parse JSON from AI response, handling markdown wrapping and minor issues."""
    if not text:
        return None

    text = text.strip()

    # Remove markdown code block wrapping
    if text.startswith("```"):
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        text = text.strip()

    # Direct parse
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in text
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    return None
