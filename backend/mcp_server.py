"""
MCP (Model Context Protocol) Server — Associate Platform
=========================================================
Provides tool registration for:
  1. MongoDB Statute Lookup — Search verified legal provisions
  2. IndianKanoon Case Law — Search live case law API
  3. GSTIN Validation — Verify vendor GST registration
  4. Compliance Calendar — Get upcoming deadlines
  5. Web Research — Deep search via DuckDuckGo
  6. GSuite (Placeholder) — Google Docs, Sheets, Drive integration

This server exposes tools that Gemma 4 and other models can call
via agentic tool-calling to perform deep, grounded research.

Usage:
  from mcp_server import MCPToolRegistry, execute_tool
  tools = MCPToolRegistry.get_tool_definitions()
  result = await execute_tool("statute_lookup", {"query": "section 73 CGST"})
"""
import asyncio
import os
import re
import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / '.env')
logger = logging.getLogger("mcp_server")

# MongoDB connection (shared with server.py)
_mongo_client = None
_db = None

def get_mcp_db():
    global _mongo_client, _db
    if _db is None:
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        _mongo_client = AsyncIOMotorClient(mongo_url, tls=True, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=10000)
        _db = _mongo_client[os.environ.get("DB_NAME", "associate_db")]
    return _db


class MCPToolRegistry:
    """Registry of all available MCP tools for the Associate platform."""
    
    TOOLS = {
        "statute_lookup": {
            "name": "statute_lookup",
            "description": "Search the verified MongoDB statute database for Indian legal provisions. Returns exact section text, act name, and effective dates. Use this for ANY query involving specific sections, acts, or legal provisions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query — can be a section number (e.g., '73'), act name (e.g., 'CGST'), or legal concept (e.g., 'ITC time limit')"},
                    "act_filter": {"type": "string", "description": "Optional: filter by specific act (e.g., 'CGST', 'Income Tax', 'FEMA')", "default": ""},
                    "max_results": {"type": "integer", "description": "Maximum number of results to return", "default": 10}
                },
                "required": ["query"]
            }
        },
        "case_law_search": {
            "name": "case_law_search",
            "description": "Search IndianKanoon for relevant case law, judgments, and precedents. Returns case titles, courts, citations, and summaries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Legal search query for case law"},
                    "top_k": {"type": "integer", "description": "Number of results", "default": 5}
                },
                "required": ["query"]
            }
        },
        "gstin_validate": {
            "name": "gstin_validate",
            "description": "Validate a GSTIN number and retrieve vendor registration details from the GST portal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "gstin": {"type": "string", "description": "15-character GSTIN to validate"}
                },
                "required": ["gstin"]
            }
        },
        "compliance_deadlines": {
            "name": "compliance_deadlines",
            "description": "Get upcoming compliance deadlines for GST, Income Tax, Company Law, and other regulatory filings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Filter by category: 'gst', 'income_tax', 'company_law', 'all'", "default": "all"},
                    "days_ahead": {"type": "integer", "description": "Number of days to look ahead", "default": 30}
                },
                "required": []
            }
        },
        "web_research": {
            "name": "web_research",
            "description": "Perform deep web research on a legal topic using DuckDuckGo. Returns relevant snippets from legal websites, government portals, and news sources.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Research query"},
                    "region": {"type": "string", "description": "Search region", "default": "in-en"},
                    "max_results": {"type": "integer", "description": "Maximum results", "default": 8}
                },
                "required": ["query"]
            }
        },
        "gsuite_docs_create": {
            "name": "gsuite_docs_create",
            "description": "[PLACEHOLDER] Create a Google Doc with the specified content. Requires GSuite OAuth setup.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Document title"},
                    "content": {"type": "string", "description": "Document content in markdown"},
                    "folder_id": {"type": "string", "description": "Google Drive folder ID", "default": ""}
                },
                "required": ["title", "content"]
            }
        },
        "gsuite_sheets_read": {
            "name": "gsuite_sheets_read",
            "description": "[PLACEHOLDER] Read data from a Google Sheet. Requires GSuite OAuth setup.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {"type": "string", "description": "Google Sheet ID"},
                    "range": {"type": "string", "description": "Cell range (e.g., 'Sheet1!A1:D100')"}
                },
                "required": ["spreadsheet_id", "range"]
            }
        }
    }
    
    @classmethod
    def get_tool_definitions(cls):
        """Return tool definitions in OpenAI function-calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
            }
            for tool in cls.TOOLS.values()
        ]
    
    @classmethod
    def get_gemma_tool_definitions(cls):
        """Return tool definitions in Google AI Studio format for Gemma 4."""
        return [
            {
                "functionDeclarations": [
                    {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["parameters"]
                    }
                    for tool in cls.TOOLS.values()
                    if not tool["name"].startswith("gsuite_")  # Exclude placeholder tools
                ]
            }
        ]


async def execute_tool(tool_name: str, args: dict) -> dict:
    """Execute an MCP tool and return the result."""
    
    if tool_name == "statute_lookup":
        return await _tool_statute_lookup(args)
    elif tool_name == "case_law_search":
        return await _tool_case_law_search(args)
    elif tool_name == "gstin_validate":
        return await _tool_gstin_validate(args)
    elif tool_name == "compliance_deadlines":
        return await _tool_compliance_deadlines(args)
    elif tool_name == "web_research":
        return await _tool_web_research(args)
    elif tool_name.startswith("gsuite_"):
        return {"status": "error", "message": "GSuite integration requires OAuth setup. Configure Google Cloud Console credentials first."}
    else:
        return {"status": "error", "message": f"Unknown tool: {tool_name}"}


async def _tool_statute_lookup(args: dict) -> dict:
    """Search MongoDB for statute provisions."""
    db = get_mcp_db()
    query = args.get("query", "")
    act_filter = args.get("act_filter", "")
    max_results = args.get("max_results", 10)
    
    # Extract section numbers
    section_nums = re.findall(r'\b(\d+[A-Za-z]*(?:\([a-z0-9]+\))*)', query.lower())
    keywords = re.findall(r'\b\w+\b', query.lower())
    search_terms = [kw for kw in keywords if len(kw) > 2][:15]
    search_terms.extend(section_nums)
    search_terms = list(set(search_terms))
    
    if not search_terms:
        return {"status": "no_results", "results": []}
    
    regex_pattern = "|".join(search_terms)
    mongo_filter = {"$or": [
        {"section_text": {"$regex": regex_pattern, "$options": "i"}},
        {"section_title": {"$regex": regex_pattern, "$options": "i"}},
        {"act_name": {"$regex": regex_pattern, "$options": "i"}},
        {"keywords": {"$in": search_terms}},
    ]}
    
    if act_filter:
        mongo_filter["act_name"] = {"$regex": act_filter, "$options": "i"}
    
    try:
        cursor = db.statutes.find(mongo_filter, {"_id": 0}).limit(max_results)
        results = await cursor.to_list(max_results)
        return {
            "status": "success",
            "count": len(results),
            "results": results,
            "source": "MongoDB Statute DB — verified"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _tool_case_law_search(args: dict) -> dict:
    """Search IndianKanoon for case law."""
    try:
        from indian_kanoon import search_indiankanoon
        results = await search_indiankanoon(args.get("query", ""), top_k=args.get("top_k", 5))
        return {
            "status": "success",
            "count": len(results),
            "results": results,
            "source": "IndianKanoon — Live API"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _tool_gstin_validate(args: dict) -> dict:
    """Validate a GSTIN."""
    try:
        from gstin_validator import validate_gstin
        result = validate_gstin(args.get("gstin", ""))
        return {"status": "success", "result": result, "source": "GSTIN Validator"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _tool_compliance_deadlines(args: dict) -> dict:
    """Get upcoming compliance deadlines."""
    try:
        from compliance_calendar import get_upcoming_deadlines
        deadlines = get_upcoming_deadlines(
            category=args.get("category", "all"),
            days_ahead=args.get("days_ahead", 30)
        )
        return {"status": "success", "deadlines": deadlines, "source": "Compliance Calendar"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _tool_web_research(args: dict) -> dict:
    """Deep web research via DuckDuckGo."""
    try:
        from duckduckgo_search import DDGS
        query = args.get("query", "")
        region = args.get("region", "in-en")
        max_results = args.get("max_results", 8)
        
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region=region, safesearch="off", max_results=max_results))
        
        return {
            "status": "success",
            "count": len(results),
            "results": [{"title": r.get("title", ""), "body": r.get("body", ""), "url": r.get("href", "")} for r in results],
            "source": "DuckDuckGo Web Search"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# === SELF-TEST ===
if __name__ == "__main__":
    async def test_tools():
        print("=" * 60)
        print("MCP SERVER — TOOL SELF-TEST")
        print("=" * 60)
        
        # Test statute lookup
        print("\n--- Statute Lookup: 'Section 73 CGST' ---")
        result = await execute_tool("statute_lookup", {"query": "Section 73 CGST"})
        print(f"Status: {result['status']}, Results: {result.get('count', 0)}")
        if result.get("results"):
            for r in result["results"][:2]:
                print(f"  📜 §{r.get('section_number')} of {r.get('act_name')}: {r.get('section_title', '')[:60]}")
        
        # Test web research
        print("\n--- Web Research: 'CBDT Circular 2025 TDS' ---")
        web = await execute_tool("web_research", {"query": "CBDT Circular 2025 TDS rates India"})
        print(f"Status: {web['status']}, Results: {web.get('count', 0)}")
        if web.get("results"):
            for r in web["results"][:3]:
                print(f"  🌐 {r['title'][:60]}")
        
        # Test tool definitions
        print(f"\n--- Tool Registry ---")
        tools = MCPToolRegistry.get_tool_definitions()
        print(f"Registered tools: {len(tools)}")
        for t in tools:
            print(f"  🔧 {t['function']['name']}: {t['function']['description'][:60]}")
        
        print("\n" + "=" * 60)
        print("MCP SELF-TEST COMPLETE")
        print("=" * 60)
    
    asyncio.run(test_tools())
