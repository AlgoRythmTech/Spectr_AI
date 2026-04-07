import asyncio
import aiohttp
import os
from dotenv import load_dotenv
from pathlib import Path
import json

load_dotenv(Path(__file__).parent / '.env')

from war_room_engine import call_gemma4_research, call_qwen_statute, call_nemotron_strategy, call_gemma_logic

async def run_live_test():
    system_prompt = "You are a Senior Partner at a Top Tier Law Firm."
    query = """My client received a Show Cause Notice under Section 74 of CGST Act for ITC mismatch in GSTR-2A vs GSTR-3B for FY 2018-19. What is the limitation period, and what are our strongest defenses citing recent High Court and Supreme Court judgments?"""
    
    print("="*60)
    print(f"QUERY: {query}")
    print("="*60)
    
    async with aiohttp.ClientSession() as session:
        print("Dispatching Parallel Models...")
        
        print("  -> Triggering Qwen (Statutory Deep-Dive)...")
        qwen_task = asyncio.create_task(call_qwen_statute(session, system_prompt, query))
        
        print("  -> Triggering Nemotron (Strategic Defense)...")
        nemo_task = asyncio.create_task(call_nemotron_strategy(session, system_prompt, query))
        
        print("  -> Triggering Gemma (Web Grounding)...")
        gemma_task = asyncio.create_task(call_gemma4_research(session, system_prompt, query))
        
        print("  -> Triggering Gemma (Jurisprudential Logic)...")
        gemma_logic_task = asyncio.create_task(call_gemma_logic(session, system_prompt, query))
        
        q_res, n_res, g_res, gl_res = await asyncio.gather(qwen_task, nemo_task, gemma_task, gemma_logic_task)
        
        print("\n\n" + "="*20 + " QWEN (Statute) " + "="*20)
        print(q_res if q_res else "[FAILED]")
        
        print("\n\n" + "="*20 + " NEMOTRON (Strategy) " + "="*20)
        print(n_res if n_res else "[FAILED]")
        
        print("\n\n" + "="*20 + " GEMMA (Web search) " + "="*20)
        print(g_res if g_res else "[FAILED]")

        print("\n\n" + "="*20 + " GEMMA (Logic) " + "="*20)
        print(gl_res if gl_res else "[FAILED]")
        
        panels = []
        if q_res: panels.append(f"STATUTORY:\n{q_res}")
        if n_res: panels.append(f"STRATEGY:\n{n_res}")
        if g_res: panels.append(f"WEB SEARCH:\n{g_res}")
        if gl_res: panels.append(f"JURISPRUDENTIAL LOGIC:\n{gl_res}")
        
        print("\n\n" + "="*20 + " SYNTHESIS PROMPT COMPILATION TEST " + "="*20)
        print(f"Loaded {len(panels)} successful panels.")
        
        # Test the final Synthesis Prompt Generation
        synth_prompt = f"""You are the FINAL SYNTHESIS engine. You have received analyses from multiple expert panels. Your job is to merge them into a SINGLE, devastatingly comprehensive legal/tax advisory document that would satisfy a Senior Partner at Veritas Legal.

MINIMUM QUALITY BAR: Your output must match the depth and precision of a Claude Opus 4.6 response. If it is generic, vague, or lacks specific section numbers and case citations, it has FAILED.

CRITICAL RULES:
1. Do NOT repeat the fast baseline answer already shown.
2. NEVER refer to yourself as AI, engine, model, or system.
3. Every factual claim MUST have a section number or case citation attached.
4. Use RICH MARKDOWN aggressively: `## Headers`, `**bold**`, `> blockquotes`, `| tables |`, numbered lists.
5. AUDIT: Silently discard any panel output that contains hallucinated laws, invented case names, or PMLA/FEMA risks for ordinary commercial matters.
6. If panels contradict each other on a legal point, note the conflict and state which position is stronger with reasoning.

MANDATORY OUTPUT STRUCTURE (use these EXACT headers):

## I. CORE ISSUE CLASSIFICATION
## II. COMPLETE STATUTORY FRAMEWORK
## III. LEADING CASE LAW
## IV. QUANTIFIED RISK ASSESSMENT
## V. MULTI-TRACK DEFENSE STRATEGY
## VI. IMMEDIATE ACTION PROTOCOL
## VII. CRITICAL WARNINGS

EXPERT PANEL OUTPUTS TO SYNTHESIZE:
{chr(10).join(panels)}"""
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": synth_prompt[:30000]}
            ],
            "temperature": 0.03, "max_tokens": 8192
        }
        
        print(f"\nFinal payload assembled. Character count: {len(synth_prompt)}")
        print("\nExecuting Final Llama-3.3-70B Synthesis...")
        
        GROQ_KEY = os.environ.get("GROQ_KEY")
        async with session.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                final_content = data["choices"][0]["message"]["content"]
                with open("test_output.md", "w", encoding="utf-8") as f:
                    f.write("# FINAL SYNTHESIS OUTPUT\n\n")
                    f.write(final_content)
                print("\n\n✅ Final Synthesis written to test_output.md")
            else:
                print(f"Error {resp.status} from Groq: {await resp.text()}")

if __name__ == "__main__":
    asyncio.run(run_live_test())

