import os
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import asyncio
import aiohttp

logger = logging.getLogger("office_engine")
office_router = APIRouter()

GROQ_KEY_LIVE = os.environ.get("GROQ_KEY", "")

class WordRedlineRequest(BaseModel):
    draft_text: str
    instruction: str

class WordCommentRequest(BaseModel):
    document_text: str
    playbook_type: str

class ExcelReconcileRequest(BaseModel):
    rows: list

# 1. MS Word Native Redline Route
@office_router.post("/word/redline")
async def draft_word_redline(req: WordRedlineRequest):
    """Takes existing text + an instruction and outputs the replacement text natively."""
    system_instruction = """You are a Big 4 Senior Attorney processing a redline request.
You are directly modifying a Microsoft Word document via an API.
Given the original text and the user's editing instruction, you MUST output ONLY the final rewritten text.
Do NOT include preamble, do NOT say 'Here is the rewrite', do NOT use markdown symbols if you are just replacing pure text.
Just output the raw, highly polished professional replacement text. Avoid formatting characters that break MS Word injection.
"""
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"INSTRUCTION: {req.instruction}\n\nORIGINAL TEXT TO REPLACE:\n{req.draft_text}"}
        ],
        "temperature": 0.1,
        "max_tokens": 2048
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ_KEY_LIVE}", "Content-Type": "application/json"}, json=payload, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    new_text = data["choices"][0]["message"]["content"].strip()
                    # Strip any accidental LLM chatty behavior
                    if new_text.startswith("Here is the"):
                        new_text = new_text.split(":\n", 1)[-1]
                    return {"success": True, "replacement_text": new_text}
                else:
                    raise HTTPException(status_code=resp.status, detail="AI Inference failed")
        except Exception as e:
            logger.error(f"Redline error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# 2. MS Word Playbook Annotation Route
@office_router.post("/word/comment")
async def playbook_scan(req: WordCommentRequest):
    """Scans document text against a selected firm Playbook and returns targeted deviations."""
    
    playbook = ""
    if req.playbook_type == "standard":
        playbook = "Standard Vendor Agreement Playbook: Liability MUST exclude gross negligence. Jurisdiction MUST be India. Payment terms MUST be at least 45 days."
    elif req.playbook_type == "nda":
        playbook = "Mutual NDA Playbook: Term must not exceed 3 years. Residuals clauses are STRICTLY PROHIBITED."
    else:
        playbook = "Generic Corporate Playbook: Neutral pro-business terms."

    system_instruction = f"""You are a top-tier Risk Management Attorney executing a Playbook Scan via MS Word API.
Here is the strict firm playbook you must enforce:
{playbook}

Analyze the provided document text. If you find clauses that violate the playbook, extract the EXACT phrase from the text, and write a margin comment explaining the risk.
Output your findings STRICTLY as a JSON array of objects. Example:
[
  {{"searchPhrase": "exact broken text from document", "comment": "⚠️ PLAYBOOK DEVIATION: Reason..."}}
]
If there are no deviations, output an empty array [].
DO NOT output anything other than pure JSON.
"""

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"DOCUMENT TEXT:\n{req.document_text[:8000]}"}
        ],
        "temperature": 0.05,
        "response_format": {"type": "json_object"},
        "max_tokens": 2048
    }
    # Note: Llama via Groq supports response_format JSON if hinted. We'll wrap prompt to force a dict.
    payload["messages"][0]["content"] += "\nReturn output inside a dict: {\"deviations\": [...]}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ_KEY_LIVE}", "Content-Type": "application/json"}, json=payload, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    import json
                    parsed = json.loads(content)
                    deviations = parsed.get("deviations", [])
                    return {"success": True, "deviations": deviations}
                else:
                    raise HTTPException(status_code=resp.status, detail="AI Playbook failed")
        except Exception as e:
            logger.error(f"Playbook scan error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# 3. MS Excel GSTR Recon / Forensic Route
@office_router.post("/excel/reconcile")
async def excel_reconcile(req: ExcelReconcileRequest):
    """Ingests row data from Excel, detects discrepancies, and returns cell formatting commands."""
    
    # We use our deterministic math engine concept here.
    # We'll calculate anomalies in Python rather than risking LLM hallucination.
    
    results = []
    for index, row in enumerate(req.rows):
        # Expected row format [GSTIN, Invoice, ITRAmount, 2BAmount]
        if len(row) >= 4:
            gstin = str(row[0])
            try:
                claimed = float(str(row[2]).replace(',', ''))
                available = float(str(row[3]).replace(',', ''))
                
                if available == 0 and claimed > 0:
                    results.append({
                        "rowIndex": index, 
                        "status": "DANGER", 
                        "flag": "❌ Sec 16(2)(c) Violation: Supplier not filed",
                        "color": "#FEE2E2" # Light Red
                    })
                elif claimed > available:
                    results.append({
                        "rowIndex": index, 
                        "status": "WARNING", 
                        "flag": f"⚠️ Rule 36(4) Risk: Claimed {claimed} vs Avlbl {available}",
                        "color": "#FEF3C7" # Light Yellow
                    })
                else:
                    results.append({
                        "rowIndex": index, 
                        "status": "SAFE", 
                        "flag": "✅ Reconciled",
                        "color": "#DCFCE7" # Light Green
                    })
            except ValueError:
                # Header row or garbage data
                pass
                
    return {"success": True, "results": results}
