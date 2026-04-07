"""
Contract Playbook Engine
Compares incoming contract drafts against firm-standard playbook templates.
Identifies deviations and suggests firm-approved replacement language.
"""
import os
import json
import aiohttp
import logging

logger = logging.getLogger(__name__)

GROQ_KEY = os.environ.get("GROQ_KEY", "")

COMPARISON_PROMPT = """You are a senior contracts partner at a top-tier Indian law firm.

You have two documents:
1. PLAYBOOK (firm standard): The firm's approved standard terms
2. DRAFT (incoming): The counterparty's draft

Your task:
1. Extract key clauses from BOTH documents (liability, indemnity, termination, payment, IP, non-compete, confidentiality, jurisdiction, force majeure, governing law, warranty, limitation of liability)
2. Compare each clause type between Playbook and Draft
3. For each deviation, classify severity as: CRITICAL (materially disadvantageous), WARNING (non-standard but negotiable), or INFO (minor wording difference)
4. For CRITICAL and WARNING deviations, suggest firm-approved replacement language

Return JSON:
{
  "deviations": [
    {
      "clause_type": "Indemnity",
      "severity": "CRITICAL",
      "playbook_text": "...",
      "draft_text": "...",
      "issue": "One-sentence explanation of the deviation",
      "suggested_fix": "Firm-approved replacement text"
    }
  ],
  "overall_risk": "HIGH|MEDIUM|LOW",
  "summary": "2-3 sentence summary of the overall contract risk"
}"""

async def compare_against_playbook(playbook_text: str, draft_text: str) -> dict:
    """Compare a draft contract against the firm's playbook and identify deviations."""
    
    if not playbook_text or not draft_text:
        return {"error": "Both playbook and draft text are required", "deviations": []}

    # Truncate if needed
    pb = playbook_text[:20000]
    dr = draft_text[:20000]

    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": COMPARISON_PROMPT},
                    {"role": "user", "content": f"PLAYBOOK (Firm Standard):\n\n{pb}\n\n---\n\nDRAFT (Incoming):\n\n{dr}"}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
                "max_tokens": 4000
            }
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = json.loads(data["choices"][0]["message"]["content"])
                    return result
                else:
                    error_text = await resp.text()
                    logger.error(f"Playbook comparison failed: {error_text}")
                    return {"error": f"AI comparison failed: {error_text}", "deviations": []}

    except Exception as e:
        logger.error(f"Playbook comparison error: {e}")
        return {"error": str(e), "deviations": []}
