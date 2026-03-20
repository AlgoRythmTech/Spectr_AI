import aiohttp
import os
import logging

logger = logging.getLogger(__name__)

INSTAFINANCIALS_API_URL = "https://api.instafinancials.com"
INSTAFINANCIALS_API_KEY = os.environ.get("INSTAFINANCIALS_API_KEY", "")


async def search_company(query: str) -> list:
    """Search for company by name or CIN."""
    if not INSTAFINANCIALS_API_KEY:
        logger.warning("InstaFinancials API key not set")
        return []
    
    try:
        headers = {"Authorization": f"Bearer {INSTAFINANCIALS_API_KEY}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{INSTAFINANCIALS_API_URL}/GetCIN",
                headers=headers,
                params={"search": query},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    logger.error(f"InstaFinancials search failed: {resp.status}")
                    return []
                data = await resp.json()
        return data if isinstance(data, list) else data.get("results", [])
    except Exception as e:
        logger.error(f"InstaFinancials search error: {e}")
        return []


async def get_company_data(cin: str) -> dict:
    """Fetch detailed company data by CIN."""
    if not INSTAFINANCIALS_API_KEY:
        return {}
    
    try:
        headers = {"Authorization": f"Bearer {INSTAFINANCIALS_API_KEY}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{INSTAFINANCIALS_API_URL}/CompanyMasterData",
                headers=headers,
                params={"cin": cin},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    return {}
                return await resp.json()
    except Exception as e:
        logger.error(f"InstaFinancials company data error: {e}")
        return {}
