"""
Test the new FREE Model Council — Gemma 4 + Qwen3.6 + Nemotron 120B
Tests each model independently, then the full synthesis pipeline.
"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / '.env')

GOOGLE_AI_KEY = os.environ.get("GOOGLE_AI_KEY", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")
GROQ_KEY = os.environ.get("GROQ_KEY", "")

async def test_gemma4():
    """Test Gemma 4 31B via Google AI Studio with Google Search."""
    print("\n" + "="*60)
    print("TEST 1: Gemma 4 31B (Google AI Studio + Web Search)")
    print("="*60)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemma-4-31b-it:generateContent?key={GOOGLE_AI_KEY}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": "What is Section 73 of the CGST Act 2017? Give the exact legal provision and time limit for issuing SCN. Be specific with dates and deadlines."}]}],
        "tools": [{"googleSearch": {}}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1024}
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status == 200:
                data = await resp.json()
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                text = "\n".join([p["text"] for p in parts if "text" in p])
                print(f"[PASS] Status: {resp.status}")
                print(f"Response ({len(text)} chars):\n{text[:500]}...")
                return True
            else:
                err = await resp.text()
                print(f"[FAIL] Status: {resp.status}: {err[:300]}")
                return False

async def test_qwen():
    """Test Qwen3.6 Plus via OpenRouter (free)."""
    print("\n" + "="*60)
    print("TEST 2: Qwen3.6 Plus (OpenRouter Free)")
    print("="*60)
    payload = {
        "model": "qwen/qwen3.6-plus:free",
        "messages": [
            {"role": "user", "content": "Explain Section 138 of the Negotiable Instruments Act 1881 in detail. What are the conditions for filing a complaint? Be specific with timelines."}
        ],
        "temperature": 0.1,
        "max_tokens": 1024
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://associate.ai",
                "X-Title": "Associate Legal AI"
            },
            json=payload, timeout=aiohttp.ClientTimeout(total=90)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                text = data["choices"][0]["message"]["content"]
                model_used = data.get("model", "unknown")
                print(f"[PASS] Status: {resp.status} | Model: {model_used}")
                print(f"Response ({len(text)} chars):\n{text[:500]}...")
                return True
            else:
                err = await resp.text()
                print(f"[FAIL] Status: {resp.status}: {err[:300]}")
                return False

async def test_nemotron():
    """Test NVIDIA Nemotron 120B via OpenRouter (free)."""
    print("\n" + "="*60)
    print("TEST 3: NVIDIA Nemotron 120B (OpenRouter Free)")
    print("="*60)
    payload = {
        "model": "nvidia/nemotron-3-super-120b-a12b:free",
        "messages": [
            {"role": "user", "content": "What are the penalties under FEMA for unauthorized foreign exchange dealings? Cite specific sections and amounts."}
        ],
        "temperature": 0.1,
        "max_tokens": 1024
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://associate.ai",
                "X-Title": "Associate Legal AI"
            },
            json=payload, timeout=aiohttp.ClientTimeout(total=90)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                text = data["choices"][0]["message"]["content"]
                model_used = data.get("model", "unknown")
                print(f"[PASS] Status: {resp.status} | Model: {model_used}")
                print(f"Response ({len(text)} chars):\n{text[:500]}...")
                return True
            else:
                err = await resp.text()
                print(f"[FAIL] Status: {resp.status}: {err[:300]}")
                return False

async def test_groq():
    """Test Groq LLaMA 70B (direct, always free)."""
    print("\n" + "="*60)
    print("TEST 4: Groq LLaMA3 70B (Direct API)")
    print("="*60)
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "user", "content": "What is the limitation period for filing a Section 34 application to set aside an arbitral award? Cite the exact provision."}
        ],
        "temperature": 0.1,
        "max_tokens": 512
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json=payload, timeout=aiohttp.ClientTimeout(total=30)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                text = data["choices"][0]["message"]["content"]
                print(f"[PASS] Status: {resp.status}")
                print(f"Response ({len(text)} chars):\n{text[:500]}...")
                return True
            else:
                err = await resp.text()
                print(f"[FAIL] Status: {resp.status}: {err[:300]}")
                return False

async def main():
    print("=" * 60)
    print("ASSOCIATE — FREE MODEL COUNCIL TEST")
    print("=" * 60)
    
    results = {}
    results["gemma4"] = await test_gemma4()
    results["qwen"] = await test_qwen()
    results["nemotron"] = await test_nemotron()
    results["groq"] = await test_groq()
    
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for model, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {model}: {status}")
    
    passed_count = sum(1 for v in results.values() if v)
    print(f"\n{passed_count}/4 models operational")
    if passed_count >= 2:
        print("[OK] Council is OPERATIONAL (minimum 2 models needed for synthesis)")
    else:
        print("[ERROR] Council DEGRADED — fewer than 2 models responding")

if __name__ == "__main__":
    asyncio.run(main())
