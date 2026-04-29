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
        self.model = "claude-sonnet-4-6"  # updated 23 Apr 2026 to Sonnet 4.6
    
    def with_model(self, provider: str, model: str):
        self.provider = provider
        self.model = model
        return self

    async def send_message(self, message: UserMessage) -> str:
        import aiohttp
        
        anthropic_key = os.environ.get('ANTHROPIC_KEY', '')
        openai_key = os.environ.get('OPENAI_KEY', '')
        emergent_key = self.api_key
        
        # Priority: Emergent proxy (PRIMARY — user paid for this key and it
        # proxies both Claude and OpenAI) > Anthropic direct > OpenAI direct.
        # Previous ordering made GPT-4o the de-facto primary because the
        # Emergent URL was broken — fixed now.
        attempts = []

        # 1. Anthropic direct — only if user has a separate Anthropic key set.
        # Most deployments won't — Emergent covers Claude.
        if anthropic_key:
            attempts.append({
                "type": "anthropic",
                "url": "https://api.anthropic.com/v1/messages",
                "key": anthropic_key,
                "model": self.model if self.provider == "anthropic" else "claude-sonnet-4-6",
                "name": "Anthropic Direct"
            })
        
        # 2. Emergent proxy — THE PRIMARY path. Proxies Claude + OpenAI.
        # Verified URL: integrations.emergentagent.com/llm/v1/chat/completions
        if emergent_key:
            attempts.append({
                "type": "openai",
                "url": "https://integrations.emergentagent.com/llm/v1/chat/completions",
                "key": emergent_key,
                "model": self.model,
                "name": "Emergent Proxy"
            })

        # 3. OpenAI direct — last-resort safety net if Emergent is down.
        if openai_key:
            attempts.append({
                "type": "openai",
                "url": "https://api.openai.com/v1/chat/completions",
                "key": openai_key,
                "model": "gpt-4o",
                "name": "GPT-4o (OpenAI Direct)"
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
            # Extended output beta — unlocks up to 128K output tokens.
            # Without this, Anthropic 400s on any max_tokens > 8192.
            # Prompt caching saves 90% cost on the 130K system prompt.
            "anthropic-beta": "prompt-caching-2024-07-31,output-128k-2025-02-19",
            "content-type": "application/json"
        }
        payload = {
            "model": attempt["model"],
            "max_tokens": 16384,
            "temperature": 0.3,
            "system": [
                {
                    "type": "text",
                    "text": self.system_message,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
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
        """Call OpenAI-compatible API (OpenAI, Emergent, etc.).

        When calling Emergent with a Claude model, we use the Anthropic-style
        system-as-list-of-blocks format with cache_control set. Emergent
        passes this through to Anthropic, triggering their 5-minute prompt
        cache. Subsequent calls with the same system prompt (multi-pass
        chaining, Vault skills, workflows) cost 10% of uncached input.
        """
        import aiohttp

        headers = {
            "Authorization": f"Bearer {attempt['key']}",
            "Content-Type": "application/json"
        }

        is_emergent_proxy = "integrations.emergentagent.com" in attempt.get("url", "")
        is_claude_model = "claude" in (attempt.get("model") or "").lower()

        if is_emergent_proxy and is_claude_model:
            # Emergent + Claude: use cached system block for 90% input savings
            payload = {
                "model": attempt["model"],
                "messages": [
                    {"role": "system", "content": [
                        {"type": "text", "text": self.system_message,
                         "cache_control": {"type": "ephemeral"}}
                    ]},
                    {"role": "user", "content": message.text}
                ],
                "max_tokens": 16384,
                "temperature": 0.3
            }
        else:
            # Plain OpenAI / non-Claude path — string system
            payload = {
                "model": attempt["model"],
                "messages": [
                    {"role": "system", "content": self.system_message},
                    {"role": "user", "content": message.text}
                ],
                "max_tokens": 16384,
                "temperature": 0.3
            }

        # aiohttp connect-timeout 10s, total 90s so slow proxy responses
        # still land within our call_claude timeout window.
        timeout = aiohttp.ClientTimeout(total=90)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(attempt["url"], json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Log cache metrics when present — shows savings in logs
                    usage = data.get("usage") or {}
                    cache_read = usage.get("cache_read_input_tokens", 0)
                    cache_write = usage.get("cache_creation_input_tokens", 0)
                    if cache_read:
                        import logging as _l
                        _l.getLogger("emergent_proxy").info(
                            f"prompt cache HIT: {cache_read} tokens read at 10% cost"
                        )
                    elif cache_write:
                        import logging as _l
                        _l.getLogger("emergent_proxy").info(
                            f"prompt cache WARM: {cache_write} tokens written (next 5 min reads are 10% cost)"
                        )
                    return data["choices"][0]["message"]["content"]
                else:
                    error_text = await resp.text()
                    raise Exception(f"{attempt['name']} {resp.status}: {error_text[:300]}")
