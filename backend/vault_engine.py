import os
import logging
import asyncio
import aiohttp
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json

logger = logging.getLogger("vault_engine")
vault_router = APIRouter()

GROQ_KEY_LIVE = os.environ.get("GROQ_KEY", "")

class VaultAnalysisRequest(BaseModel):
    vault_id: str
    documents: List[dict]  # [{"filename": "Notice.pdf", "content": "..."}]
    analysis_type: str  # "timeline" | "contradictions" | "night_before" | "custom_query"
    custom_prompt: Optional[str] = None

# Global in-memory vault storage for the MVP
# In production, this would be MongoDB or S3 with Vector Embeddings.
_ACTIVE_VAULTS = {}

def get_system_prompt_for_type(analysis_type: str) -> str:
    base_expert = "You are a Big 4 Senior Litigator and Forensic Analyst parsing a Multi-Document Vault.\n"
    base_expert += "CRITICAL DIRECTIVE: You MUST utilize Extended Sequential Thinking before yielding a final output. Begin your response with an `<internal_strategy>` block where you logically map timeline events, flag discrepancies, and correlate files. Only after your strategy block should you output the final Markdown response.\n\n"
    
    if analysis_type == "timeline":
        return f"""{base_expert}
Your objective is to read across ALL provided documents and extract a mathematically perfect Chronological Timeline of Events.
Output strictly in Rich Markdown.
Format:
| Date | Event Description | Source Document | Legal Implication |
|---|---|---|---|
Never hallucinate dates. If a date is ambiguous, say so. Sort chronologically from oldest to newest."""
    
    elif analysis_type == "contradictions":
        return f"""{base_expert}
Your objective is to find CONTRADICTIONS, DISCREPANCIES, and LIES across the documents. 
For example, if Document A (Ledger) says 50,000 but Document B (Affidavit) says 40,000, FLAG IT.
Format your output dynamically using Markdown blocks, using `> Blockquotes` to highlight the exact contradictory statements side by side.
Be extremely aggressive. Find what the opposing counsel is trying to hide and rip their case apart in the `<internal_strategy>` block first."""

    elif analysis_type == "night_before":
        return f"""{base_expert}
You are preparing the "Night Before" Hearing Digest for the Senior Advocate. They have 3 minutes to read this before tribunal proceedings.
Structure your output EXACTLY as:
## 1. THE BLUF (Bottom Line Up Front)
[3 crisp sentences on the crux of the dispute]

## 2. CHRONOLOGY OF FATAL ERRORS
[A bulleted list of 3-5 major procedural or factual errors made by the Department/Opponent]

## 3. MASTER PRECEDENT MATRIX
[The top 3 absolute strongest defenses based on the facts, specifying WHY they apply]

## 4. THE FIRST 3 MINUTES OF ARGUMENT
[A literal script of what the Senior Advocate should say to the bench when building the opening frame]"""

    else:
        return f"{base_expert} Answer the user's specific query by aggressively cross-referencing all provided documents. Cite the specific 'filename' when making claims."


@vault_router.post("/analyze")
async def analyze_vault_stream(req: Request):
    """Streams the deep analysis back to the UI."""
    data = await req.json()
    documents = data.get("documents", [])
    analysis_type = data.get("analysis_type", "timeline")
    custom_prompt = data.get("custom_prompt", "")
    
    if not documents:
        raise HTTPException(status_code=400, detail="Vault is empty.")
    
    # Compile the mega-context
    mega_context = "=== VAULT CONTENTS ===\n\n"
    for idx, doc in enumerate(documents):
        mega_context += f"--- DOCUMENT {idx+1}: {doc.get('filename', 'Unknown')} ---\n"
        mega_context += f"{doc.get('content', '')[:15000]}\n\n" # Hard cap per doc to avoid blowing context if abused
        
    system_prompt = get_system_prompt_for_type(analysis_type)
    
    user_prompt = "Execute the required analysis on the Vault Contents below.\n\n"
    if analysis_type == "custom_query":
        user_prompt = f"USER INSTRUCTION: {custom_prompt}\n\n"
    
    user_prompt += mega_context

    async def stream_generator():
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 6000,
            "stream": True
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                # Initial thought signal
                yield json.dumps({"type": "vault_status", "status": "Compressing Vault context window..."}) + "\n"
                await asyncio.sleep(0.5)
                yield json.dumps({"type": "vault_status", "status": "Executing deep cross-examination..."}) + "\n"
                
                async with session.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ_KEY_LIVE}", "Content-Type": "application/json"}, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status != 200:
                        err = await resp.text()
                        yield json.dumps({"type": "vault_chunk", "content": f"Vault Error: {err}"}) + "\n"
                        return
                    
                    async for chunk in resp.content:
                        if chunk:
                            chunk_str = chunk.decode('utf-8').strip()
                            if chunk_str.startswith('data: ') and chunk_str != 'data: [DONE]':
                                try:
                                    data_json = json.loads(chunk_str[6:])
                                    delta = data_json['choices'][0]['delta'].get('content', '')
                                    if delta:
                                        yield json.dumps({"type": "vault_chunk", "content": delta}) + "\n"
                                except:
                                    pass
                yield json.dumps({"type": "vault_complete"}) + "\n"
            except Exception as e:
                logger.error(f"Vault stream error: {e}")
                yield json.dumps({"type": "vault_chunk", "content": f"\n\n**System Error during Vault Analysis:** {str(e)}"}) + "\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")

