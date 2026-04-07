import os
import asyncio
import aiohttp
import json
import logging
import re
from citation_linker import find_citation_links
from ai_engine import ASSOCIATE_SYSTEM_PROMPT
from browser_agent import autonomous_deep_research

def extract_sections(text: str) -> list:
    if not text: return []
    return list(set(re.findall(r'Section \d+[A-Z]*', text)))

logger = logging.getLogger("war_room")

from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / '.env')

GROQ_KEY_LIVE = os.environ.get("GROQ_KEY", "")
GOOGLE_AI_KEY = os.environ.get("GOOGLE_AI_KEY", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")
OPENAI_KEY = os.environ.get("OPENAI_KEY", "")
async def call_groq_fast(session, system_instruction, user_content):
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": "Write in highly detailed, flowing professional prose. Start with the direct answer. Use rich Markdown for formatting.\n\n" + user_content[:15000]}
        ],
        "temperature": 0.1,
        "max_tokens": 4096
    }
    try:
        async with session.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ_KEY_LIVE}", "Content-Type": "application/json"}, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Groq fast error: {e}")
    return ""

async def call_gemma4_research(session, system_instruction, user_content):
    payload = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": "You are a Deep Web Grounding Node. You MUST use the Google Search API to aggressively verify if the laws or precedents mentioned in this query have been amended or overruled recently. Cite the URLs you find.\n\n" + user_content[:15000]}]}],
        "tools": [{"googleSearch": {}}],
        "generationConfig": {"temperature": 0.05, "maxOutputTokens": 8192}
    }
    try:
        api_key = os.environ.get("GOOGLE_AI_KEY", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={api_key}"
        async with session.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status == 200:
                data = await resp.json()
                candidate = data.get("candidates", [{}])[0]
                parts = candidate.get("content", {}).get("parts", [])
                text_output = "\n".join([p.get("text", "") for p in parts if "text" in p])
                
                # Extract grounding metadata to physically prove live web search occurred
                grounding_metadata = candidate.get("groundingMetadata", {})
                web_chunks = grounding_metadata.get("groundingChunks", [])
                if web_chunks:
                    urls = []
                    for chunk in web_chunks:
                        web = chunk.get("web", {})
                        if web.get("uri"):
                            urls.append(web.get("uri"))
                    if urls:
                        unique_urls = list(set(urls))
                        text_output += "\n\n### LIVE WEB SEARCH EXECUTED\n"
                        text_output += "The following live URLs were scanned to ground this analysis:\n"
                        for url in unique_urls:
                            text_output += f"- {url}\n"
                            
                return text_output
    except Exception as e:
        logger.error(f"Gemma4 error: {e}")
    return ""

async def call_qwen_statute(session, system_instruction, user_content):
    qwen_instruction = """You are the STATUTORY DEEP-DIVE engine. Your SOLE purpose is exhaustive statutory extraction. For every legal or tax issue in the query:

1. IDENTIFY every applicable statute, section, sub-section, proviso, explanation, and rule. Use EXACT notation (e.g., 'Section 16(2)(c) read with Rule 36(4) of CGST Rules, 2017').
2. For each section, provide: (a) the operative text in your own condensed summary, (b) the threshold/limit if any, (c) the penalty for non-compliance, (d) the relevant CBDT Circular/Notification number if applicable.
3. MAP old section numbers to new ones if the law has been amended (e.g., 'Old IPC 420 → BNS 318').
4. CROSS-REFERENCE intersecting statutes (e.g., if GST ITC is denied, also check Section 43B of IT Act for disallowance impact).
5. Include ALL proviso chains — many defenses are hidden in the second or third proviso.
6. Cite the EXACT limitation period applicable with the article/section that governs it.
7. Output in STRUCTURED MARKDOWN with section-wise breakdown. Use tables where comparing multiple sections.

Do NOT summarize generically. Every claim must have a section number attached. If you are uncertain about a section number, say so explicitly rather than guessing."""
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": qwen_instruction + "\n\n" + user_content[:15000]}
        ],
        "temperature": 0.05,
        "max_tokens": 6000
    }
    try:
        async with session.post("https://api.openai.com/v1/chat/completions", headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}, json=payload, timeout=aiohttp.ClientTimeout(total=45)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Statute Panel (GPT-4o-mini) error: {e}")
    return ""

async def call_nemotron_strategy(session, system_instruction, user_content):
    nemotron_instruction = """You are the STRATEGIC DEFENSE engine. Your sole purpose is to produce a multi-track litigation/advisory strategy that a Senior Partner at a Big 4 firm would present to a Fortune 500 client. For every issue:

1. PRIMARY DEFENSE: The strongest legal argument. Cite the leading Supreme Court / High Court case by name, year, and SCC/ITR citation. Quote the relevant ratio decidendi in 1-2 sentences.
2. SECONDARY DEFENSE: An alternative argument if the primary fails. Different legal basis.
3. PROCEDURAL DEFENSE: Jurisdictional challenges, limitation bars, natural justice violations, non-service of notice, etc.
4. FINANCIAL EXPOSURE MATRIX: Produce a table with columns: Scenario | Tax/Liability | Interest (rate + period) | Penalty | Total Exposure. Show best-case, worst-case, and most-likely amounts.
5. SETTLEMENT STRATEGY: If pre-deposit, VVSV, mediation, or compounding is available, calculate the exact cost.
6. IMMEDIATE ACTION ITEMS: Numbered list of what the professional must do in the next 48 hours, with deadlines.
7. COUNTER-ARGUMENTS: Anticipate and pre-emptively rebut the opposing side's likely arguments.

NO generic advice. NO disclaimers. Every recommendation must be backed by a specific section, rule, or case. Output in rich markdown with tables and bold key terms."""
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": nemotron_instruction + "\n\n" + user_content[:15000]}
        ],
        "temperature": 0.05,
        "max_tokens": 6000
    }
    try:
        async with session.post("https://api.openai.com/v1/chat/completions", headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}, json=payload, timeout=aiohttp.ClientTimeout(total=45)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Strategy Panel (GPT-4o) error: {e}")
    return ""

async def call_gemma_logic(session, system_instruction, user_content):
    gemma_instruction = """You are the JURISPRUDENTIAL LOGIC ENGINE (Gemma 4 Tier). Your purpose is to deconstruct the legal query structurally.
    
1. Trace the legislative intent behind the provisions.
2. Identify the logical gaps or contradictions in the opposing side's potential arguments.
3. Draw analogies from constitutional bench judgments or equivalent complex matters.
4. Output in highly structured markdown. Do NOT use web search. Rely purely on deep zero-shot reasoning.
"""
    payload = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": gemma_instruction + "\n\n" + user_content[:15000]}]}],
        "generationConfig": {"temperature": 0.05, "maxOutputTokens": 8192}
    }
    try:
        api_key = os.environ.get("GOOGLE_AI_KEY", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemma-4-31b-it:generateContent?key={api_key}"
        async with session.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status == 200:
                data = await resp.json()
                candidate = data.get("candidates", [{}])[0]
                parts = candidate.get("content", {}).get("parts", [])
                text_output = "\n".join([p.get("text", "") for p in parts if "text" in p])
                return text_output
    except Exception as e:
        logger.error(f"Gemma 4 Reasoning Panel error: {e}")
    return ""


async def process_query_streamed(user_query: str, mode: str, matter_context: str, statute_context: str, firm_context: str):
    # Setup context
    system_instruction = ASSOCIATE_SYSTEM_PROMPT
    full_context = ""
    if statute_context: full_context += f"=== DB STATUTES ===\n{statute_context}\n\n"
    if matter_context: full_context += f"=== MATTER ===\n{matter_context}\n\n"
    if firm_context: full_context += f"=== FIRM CONTEXT ===\n{firm_context}\n\n"
    
    user_content = f"QUERY: {user_query}\n\nCONTEXT:\n{full_context}"
    source_labels = extract_sections(statute_context) if statute_context else []
    if statute_context: source_labels.append("MongoDB Statute DB")
    
    # Generate chunks
    async with aiohttp.ClientSession() as session:
        yield json.dumps({"type": "war_room_status", "status": "Rapid analysis in progress..."})
        
        baseline_result = await call_groq_fast(session, system_instruction, user_content)
        if baseline_result:
            yield json.dumps({"type": "fast_chunk", "content": baseline_result})
            citations = await find_citation_links(baseline_result)
            yield json.dumps({"type": "fast_complete", "models_used": ["fast-engine"], "sections": source_labels, "citations": citations})
        else:
            yield json.dumps({"type": "fast_chunk", "content": "System Error: Fast inference failed."})
        
        # War Room Phase
        yield json.dumps({"type": "war_room_status", "status": "Deploying deep multi-agent reasoning, including headless Chromium scraper..."})
        
        async def yield_wrapper(status_dict):
            # A tiny callback wrapper to pass to the browser agent
            if "status" in status_dict:
                import json
                try:
                    # We can't actually yield from a non-generator, but we use a list or queue
                    pass # Since we are inside an async generator, we can't easily yield back without queues. 
                         # We'll just append statuses to be yielded.
                except:
                    pass

        # Since yield_wrapper inside asyncio.gather won't yield to the parent generator directly,
        # we will simply let the browser agent log or return its status in the final text.
        gemma_task = asyncio.create_task(call_gemma4_research(session, system_instruction, user_content))
        qwen_task = asyncio.create_task(call_qwen_statute(session, system_instruction, user_content))
        nemotron_task = asyncio.create_task(call_nemotron_strategy(session, system_instruction, user_content))
        gemma_logic_task = asyncio.create_task(call_gemma_logic(session, system_instruction, user_content))
        
        # Dispatch the Autonomous Browser Agent
        browser_task = asyncio.create_task(autonomous_deep_research(user_query, None))
        
        g_res, q_res, n_res, gl_res, b_res = await asyncio.gather(gemma_task, qwen_task, nemotron_task, gemma_logic_task, browser_task, return_exceptions=True)
        
        panels = []
        if isinstance(n_res, str) and len(n_res) > 50: panels.append(f"STRATEGIC ANALYSIS:\n{n_res}\n\n")
        if isinstance(q_res, str) and len(q_res) > 50: panels.append(f"STATUTORY ANALYSIS:\n{q_res}\n\n")
        if isinstance(g_res, str) and len(g_res) > 50: panels.append(f"INDEPTH RESEARCH:\n{g_res}\n\n")
        if isinstance(gl_res, str) and len(gl_res) > 50: panels.append(f"JURISPRUDENTIAL LOGIC (GEMMA):\n{gl_res}\n\n")
        if isinstance(b_res, str) and len(b_res) > 50: panels.append(f"AUTONOMOUS BROWSER SCRAPING RESULTS:\n{b_res}\n\n")
        
        if panels:
            yield json.dumps({"type": "war_room_status", "status": f"System compiling Indepth analysis from {len(panels)} expert panels..."})
            
            synth_prompt = f"""You are the FINAL SYNTHESIS engine. You have received analyses from multiple expert panels. Your job is to merge them into a SINGLE, devastatingly comprehensive legal/tax advisory document that would satisfy a Senior Partner at Veritas Legal.

MINIMUM QUALITY BAR: Your output must match the depth and precision of a Claude Opus 4.6 response. If it is generic, vague, or lacks specific section numbers and case citations, it has FAILED.

CRITICAL RULES:
0. EXCEPTIONAL OVERRIDE: If the user query is a greeting (e.g. "hi") or completely lacks legal/tax substance, IGNORE the mandatory structure entirely. Output ONLY a 1-sentence professional greeting without any headers, stars, or hashes.
1. Do NOT repeat the fast baseline answer already shown.
2. NEVER refer to yourself as AI, engine, model, or system.
3. Every factual claim MUST have a section number or case citation attached.
4. Use RICH MARKDOWN aggressively: `## Headers`, `**bold**`, `> blockquotes`, `| tables |`, numbered lists. No `####` allowed.
5. AUDIT: Silently discard any panel output that contains hallucinated laws, invented case names, or PMLA/FEMA risks for ordinary commercial matters.
6. If panels contradict each other on a legal point, note the conflict and state which position is stronger with reasoning.

MANDATORY OUTPUT STRUCTURE (use these EXACT headers if query is legal):

## I. CORE ISSUE CLASSIFICATION
Identify the precise legal question. Classify under relevant statute and jurisdiction.

## II. COMPLETE STATUTORY FRAMEWORK
List EVERY applicable section, sub-section, proviso, and rule. Use a table format:
| Section | Provision | Applicability | Key Threshold/Limit |

## III. LEADING CASE LAW
For each legal point, cite the leading SC/HC judgment with: Case Name, Year, Citation, and the ratio in 1-2 sentences. Minimum 3 cases.

## IV. QUANTIFIED RISK ASSESSMENT
Produce a financial exposure table:
| Scenario | Principal | Interest | Penalty | Total |
Show best-case, worst-case, and most-likely.

## V. MULTI-TRACK DEFENSE STRATEGY
Primary defense (strongest argument), Secondary defense (alternative basis), Procedural defense (limitation/jurisdiction).

## VI. IMMEDIATE ACTION PROTOCOL
Numbered list of exactly what the professional must do in the next 48 hours.

## VII. CRITICAL WARNINGS
Anything that could go catastrophically wrong if ignored.

EXPERT PANEL OUTPUTS TO SYNTHESIZE:
{chr(10).join(panels)}"""
            
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": synth_prompt[:30000]}
                ],
                "temperature": 0.03, "max_tokens": 8192
            }
            try:
                async with session.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ_KEY_LIVE}", "Content-Type": "application/json"}, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        synth_data = await resp.json()
                        final_text = synth_data["choices"][0]["message"]["content"]
                        citations = await find_citation_links(final_text)
                        yield json.dumps({"type": "partner_payload", "content": final_text, "citations": citations})
            except Exception as e:
                yield json.dumps({"type": "war_room_status", "status": f"Synthesis failed: {e}"})
                
        yield json.dumps({"type": "war_room_status", "status": "Analysis complete."})
