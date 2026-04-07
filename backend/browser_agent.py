import asyncio
from playwright.async_api import async_playwright
import bs4
import logging
import json

logger = logging.getLogger(__name__)

class DeepResearchBrowser:
    """An autonomous Puppeteer/Playwright Sub-Agent that navigates the actual web."""
    
    def __init__(self):
        self.browser = None
        self.playwright = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def read_url(self, url: str) -> str:
        """Navigates to URL, waits for network idle, and extracts pure text."""
        try:
            page = await self.browser.new_page()
            # Intercept and block heavy resources to load faster
            await page.route("**/*", lambda route: route.continue_() if route.request.resource_type in ["document", "script", "xhr", "fetch"] else route.abort())
            
            await page.goto(url, wait_until="networkidle", timeout=15000)
            html = await page.content()
            await page.close()
            
            # Use BeautifulSoup to rip out text cleanly
            soup = bs4.BeautifulSoup(html, 'lxml')
            for tag in soup(["script", "style", "nav", "footer", "aside"]):
                tag.decompose()
                
            return soup.get_text(separator=' ', strip=True)[:15000] # Return top 15k chars to avoid blowing context
        except Exception as e:
            logger.error(f"Browser SubAgent failed reading {url}: {e}")
            return f"[Error fetching {url}: Site blocked or timeout]"

async def autonomous_deep_research(query: str, yield_callback=None) -> str:
    """
    1. DDGS to find target URLs based on query
    2. Dispatch Chromium Browser Subagent to physically scrape the content
    3. Return the synthesized text
    """
    if yield_callback:
        yield_callback({"type": "war_room_status", "status": "Browser Sub-Agent dispatched. Booting Chromium headless engine..."})
    
    urls_to_scrape = []
    
    try:
        from duckduckgo_search import DDGS
        results = DDGS().text(query, region='in-en', safesearch='off', max_results=2)
        urls_to_scrape = [r['href'] for r in results if 'href' in r]
    except Exception as e:
        logger.error(f"DDG Search failed in browser agent: {e}")
        
    if not urls_to_scrape:
        return "Autonomous Browser: No viable targets found."
        
    if yield_callback:
        for u in urls_to_scrape:
            yield_callback({"type": "war_room_status", "status": f"Chromium Navigating to: {u}..."})
            
    scraped_content = []
    async with DeepResearchBrowser() as browser:
        for url in urls_to_scrape:
            text = await browser.read_url(url)
            scraped_content.append(f"SOURCE: {url}\n{text}\n")
            
    return "\n".join(scraped_content)
