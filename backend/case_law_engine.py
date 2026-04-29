import os
import aiohttp
import json
import logging
from bs4 import BeautifulSoup
import urllib.parse
from indian_kanoon import search_indiankanoon

logger = logging.getLogger(__name__)

async def find_case_law(scenario: str, limit: int = 10) -> list:
    """
    1. Uses AI to convert the scenario into advanced IndianKanoon boolean search queries.
    2. Scrapes the results.
    3. Uses AI to score and rank relevance to the original scenario.
    """
    groq_key = os.environ.get("GROQ_KEY", "")
    
    # Step 1: AI Query Generation
    system_prompt = """You are an expert Indian litigator. 
Your job is to read a factual scenario and generate 3 highly specific boolean search queries for IndianKanoon to find analogous judgments.
Focus on exact legal phrases, maxims, statute sections, and unique factual keywords.
Return ONLY a JSON array of 3 strings. Example: ["\"specific performance\" AND \"readiness and willingness\" AND \"section 16\"", "\"...\""]"""

    queries = []
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": scenario}
                ],
                "response_format": {"type": "json_object"}
            }
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result_json = json.loads(data["choices"][0]["message"]["content"])
                    queries = result_json.get("queries", list(result_json.values())[0])
    except Exception as e:
        logger.error(f"Error generating queries: {e}")
        # Fallback simple query
        queries = [scenario[:100]]

    # Step 2: Search IndianKanoon using the API
    all_results = []
    seen_ids = set()

    for q in queries:
        try:
            results = await search_indiankanoon(q, top_k=5)
            for r in results:
                if isinstance(r, dict) and r.get('doc_id') not in seen_ids:
                    seen_ids.add(r.get('doc_id'))
                    r['url'] = f"https://indiankanoon.org/doc/{r.get('doc_id', '')}/"
                    r['snippet'] = r.get('headline', '')
                    all_results.append(r)
        except Exception as e:
             logger.error(f"Kanoon search error for query {q}: {e}")

    if not all_results:
        return []

    # Step 3: AI Relevance Ranking & Formatting
    rank_prompt = """You are a Senior Advocate evaluating case law.
Rate each judgment's relevance to the original scenario from 0 to 100.
Also generate a 1-sentence 'Targeted Holding' explaining WHY it is relevant.
Input Format:
Original Scenario: [text]
Cases:
[index] Title: [title]
Snippet: [snippet]
---
Return JSON array: [{"index": int, "score": int, "holding": "..."}]
"""
    
    cases_text = "\n".join([f"[{i}] Title: {r.get('title', '')}\nSnippet: {r.get('snippet', '')}" for i, r in enumerate(all_results)])
    
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": rank_prompt},
                    {"role": "user", "content": f"Original Scenario: {scenario}\n\nCases:\n{cases_text}"}
                ],
                "response_format": {"type": "json_object"}
            }
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json=payload
            ) as resp:
                 if resp.status == 200:
                    data = await resp.json()
                    ranks_json = json.loads(data["choices"][0]["message"]["content"])
                    ranks_list = ranks_json.get("rankings", list(ranks_json.values())[0])
                    
                    # Merge ranks into results
                    for rank_data in ranks_list:
                        idx = rank_data.get("index")
                        if 0 <= idx < len(all_results):
                            all_results[idx]["relevance_score"] = rank_data.get("score", 50)
                            all_results[idx]["holding"] = rank_data.get("holding", "")
    except Exception as e:
        logger.error(f"Ranking error: {e}")
        for r in all_results:
             r["relevance_score"] = 50
             r["holding"] = r.get("snippet", "")[:100] + "..."

    # Sort by relevance and return top
    all_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    return all_results[:limit]
