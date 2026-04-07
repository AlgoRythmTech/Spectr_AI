"""
Judgment Summarizer
Multi-pass extraction for long court orders and judgments.
Produces structured summaries with metadata, holdings, and appeal points.
"""
import os
import json
import aiohttp
import logging

logger = logging.getLogger(__name__)

GROQ_KEY = os.environ.get("GROQ_KEY", "")

async def _call_llm(system_prompt: str, user_content: str) -> str:
    """Helper to call Groq LLM."""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                "temperature": 0.1,
                "max_tokens": 3000
            }
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return f"Error: {await resp.text()}"
    except Exception as e:
        return f"Error: {str(e)}"


async def summarize_judgment(judgment_text: str) -> dict:
    """
    Multi-pass judgment summarization:
    Pass 1: Extract metadata (parties, court, judge, date, case number)
    Pass 2: Extract issues and arguments
    Pass 3: Extract holdings and ratio
    Pass 4: Extract orders, directions, compliance deadlines
    Pass 5: Generate appeal analysis
    """
    text = judgment_text[:40000]  # Truncate for token limits

    # Pass 1: Metadata
    metadata = await _call_llm(
        """Extract the following from this judgment in JSON format:
{
  "case_number": "",
  "court": "",
  "bench": "",
  "date_of_judgment": "",
  "petitioner": "",
  "respondent": "",
  "subject_matter": "",
  "statutes_involved": [],
  "key_sections": []
}""",
        text
    )

    # Pass 2: Issues & Arguments
    issues = await _call_llm(
        """You are a judicial clerk. Extract from this judgment:
1. All issues framed by the court (verbatim if possible)
2. The petitioner/appellant's key arguments (numbered)
3. The respondent's key arguments (numbered)
4. Any amicus curiae or intervenor arguments

Write in flowing professional prose without markdown headers or asterisks. Use numbered paragraphs.""",
        text
    )

    # Pass 3: Holdings & Ratio
    holdings = await _call_llm(
        """You are a senior advocate analyzing this judgment. Extract:
1. The court's holding on each issue framed
2. The ratio decidendi (the principle of law that forms the basis of the decision)
3. Any obiter dicta (observations made by the court that are not binding)
4. How the court distinguished or followed earlier precedents

Write in flowing professional prose without markdown headers or asterisks.""",
        text
    )

    # Pass 4: Orders & Directions
    orders = await _call_llm(
        """Extract from this judgment:
1. The final order/decree (verbatim)
2. Any specific directions given to parties
3. Any compliance deadlines or timelines set
4. Any costs awarded
5. Any liberty reserved to parties

Format as numbered paragraphs. Do not use markdown headers or asterisks.""",
        text
    )

    # Pass 5: Appeal Analysis
    appeal_points = await _call_llm(
        """You are a senior litigator advising on appeal strategy. Based on this judgment:
1. Identify potential grounds for appeal (errors of law, errors of fact, procedural irregularities)
2. Assess the strength of each ground (Strong, Moderate, Weak)
3. Identify the appellate forum (which court the appeal would lie to)
4. Note the limitation period for filing the appeal
5. Suggest any interim relief that should be sought

Write in flowing professional prose. Do not use markdown.""",
        text
    )

    # Quick Brief (2-paragraph summary)
    quick_brief = await _call_llm(
        """Write a 2-paragraph executive summary of this judgment in under 200 words. First paragraph: who, what, when, where. Second paragraph: what was decided and why it matters. Do not use markdown.""",
        text
    )

    return {
        "quick_brief": quick_brief,
        "metadata": metadata,
        "issues_and_arguments": issues,
        "holdings_and_ratio": holdings,
        "orders_and_directions": orders,
        "appeal_analysis": appeal_points,
        "sections": [
            {"title": "Executive Brief", "content": quick_brief},
            {"title": "Issues and Arguments", "content": issues},
            {"title": "Holdings and Ratio", "content": holdings},
            {"title": "Orders and Directions", "content": orders},
            {"title": "Appeal Strategy", "content": appeal_points}
        ]
    }
