"""
Obligation & Deadline Extractor
Scans contract/document text and extracts structured obligations, deadlines, and conditions.
"""
import os
import json
import aiohttp
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

GROQ_KEY = os.environ.get("GROQ_KEY", "")

EXTRACTION_PROMPT = """You are an expert contract analyst specializing in Indian commercial law.
Analyze the following document text and extract ALL obligations, deadlines, and conditions.

For each obligation, extract:
1. party: Which party bears the obligation
2. obligation: What must be done (specific action)
3. deadline: When it must be done (exact date if available, or relative like "within 30 days of execution")
4. condition: Any precondition that must be met
5. penalty: Consequence of non-compliance
6. clause_ref: Clause or section reference in the document
7. category: One of [payment, delivery, compliance, reporting, termination, indemnity, confidentiality, other]

Return a JSON object with key "obligations" containing an array of objects.
If no clear deadline exists, set deadline to "ongoing".
Be exhaustive - extract every single obligation, even minor ones."""

async def extract_obligations(document_text: str) -> dict:
    """Extract obligations from document text using AI."""
    if not document_text or not document_text.strip():
        return {"obligations": [], "summary": "No document text provided."}

    # Truncate if too long
    text = document_text[:30000]

    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": EXTRACTION_PROMPT},
                    {"role": "user", "content": f"DOCUMENT TEXT:\n\n{text}"}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1
            }
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = json.loads(data["choices"][0]["message"]["content"])
                    obligations = result.get("obligations", [])

                    # Post-process: calculate days remaining
                    today = datetime.now()
                    for ob in obligations:
                        deadline_str = ob.get("deadline", "ongoing")
                        ob["urgency"] = "normal"
                        ob["days_remaining"] = None

                        if deadline_str and deadline_str != "ongoing":
                            try:
                                # Try to parse various date formats
                                for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d %B %Y", "%B %d, %Y"]:
                                    try:
                                        deadline_date = datetime.strptime(deadline_str, fmt)
                                        days_left = (deadline_date - today).days
                                        ob["days_remaining"] = days_left
                                        if days_left < 0:
                                            ob["urgency"] = "overdue"
                                        elif days_left <= 7:
                                            ob["urgency"] = "critical"
                                        elif days_left <= 30:
                                            ob["urgency"] = "warning"
                                        break
                                    except ValueError:
                                        continue
                            except Exception:
                                pass

                    # Generate summary
                    critical_count = sum(1 for o in obligations if o["urgency"] in ["overdue", "critical"])
                    summary = f"Extracted {len(obligations)} obligations. {critical_count} require immediate attention."

                    return {"obligations": obligations, "summary": summary}
                else:
                    error_text = await resp.text()
                    logger.error(f"Obligation extraction failed: {error_text}")
                    return {"obligations": [], "summary": f"Extraction failed: {error_text}"}

    except Exception as e:
        logger.error(f"Obligation extraction error: {e}")
        return {"obligations": [], "summary": f"Error: {str(e)}"}
