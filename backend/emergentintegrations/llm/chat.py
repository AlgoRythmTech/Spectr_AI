import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent.parent / '.env')

class UserMessage:
    def __init__(self, text: str):
        self.text = text

class LlmChat:
    def __init__(self, api_key: str, session_id: str, system_message: str):
        self.api_key = api_key
        self.session_id = session_id
        self.system_message = system_message
        self.provider = "anthropic"
        self.model = "claude-3-5-sonnet-20241022"
    
    def with_model(self, provider: str, model: str):
        self.provider = provider
        self.model = model
        return self

    async def send_message(self, message: UserMessage) -> str:
        import aiohttp
        
        anthropic_key = os.environ.get('ANTHROPIC_KEY', '')
        openai_key = os.environ.get('OPENAI_KEY', '')
        emergent_key = self.api_key
        
        # Priority: Anthropic (Claude) > OpenAI (GPT-4o) > Emergent proxy
        attempts = []
        
        # 1. Direct Anthropic API (Claude) - BEST for Indian legal
        if anthropic_key:
            attempts.append({
                "type": "anthropic",
                "url": "https://api.anthropic.com/v1/messages",
                "key": anthropic_key,
                "model": "claude-3-5-sonnet-20241022",
                "name": "Claude 3.5 Sonnet (Direct)"
            })
        
        # 2. OpenAI API (GPT-4o) - Fallback
        if openai_key:
            attempts.append({
                "type": "openai",
                "url": "https://api.openai.com/v1/chat/completions",
                "key": openai_key,
                "model": "gpt-4o",
                "name": "GPT-4o (OpenAI)"
            })
        
        # 3. Emergent proxy - Last resort
        if emergent_key:
            attempts.append({
                "type": "openai",
                "url": "https://api.emergent.sh/v1/chat/completions",
                "key": emergent_key,
                "model": "claude-3-5-sonnet-20241022",
                "name": "Emergent Proxy"
            })
        
        last_error = None
        for attempt in attempts:
            try:
                if attempt["type"] == "anthropic":
                    result = await self._call_anthropic(attempt, message)
                else:
                    result = await self._call_openai(attempt, message)
                
                if result:
                    return result
            except Exception as e:
                last_error = f"{attempt['name']}: {str(e)}"
        
        return f"Error: All LLM providers failed. Last error: {last_error}"

    async def _call_anthropic(self, attempt: dict, message: UserMessage) -> str:
        """Call Anthropic's native Messages API directly."""
        import aiohttp
        
        headers = {
            "x-api-key": attempt["key"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": attempt["model"],
            "max_tokens": 4096,
            "temperature": 0.3,
            "system": self.system_message,
            "messages": [
                {"role": "user", "content": message.text}
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(attempt["url"], json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Anthropic returns content as a list of content blocks
                    content_blocks = data.get("content", [])
                    return "".join(block.get("text", "") for block in content_blocks)
                else:
                    error_text = await resp.text()
                    raise Exception(f"Anthropic {resp.status}: {error_text[:300]}")

    async def _call_openai(self, attempt: dict, message: UserMessage) -> str:
        """Call OpenAI-compatible API (OpenAI, Emergent, etc.)."""
        import aiohttp
        
        headers = {
            "Authorization": f"Bearer {attempt['key']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": attempt["model"],
            "messages": [
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": message.text}
            ],
            "max_tokens": 4096,
            "temperature": 0.3
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(attempt["url"], json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error_text = await resp.text()
                    raise Exception(f"{attempt['name']} {resp.status}: {error_text[:300]}")
