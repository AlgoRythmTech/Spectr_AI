"""
Spectr Drive MCP Server — exposes Google Drive/Sheets/Docs as MCP tools.

Supports both transports:
  1. HTTP+JSON-RPC: mounted at /mcp/drive on main FastAPI app
  2. stdio (for Claude Desktop): runnable via `python mcp_drive_server.py --stdio`

Tools exposed:
  - drive_list_folders      — Browse user's Drive
  - drive_create_folder     — Make a new folder
  - drive_upload_file       — Upload Spectr-generated file to Drive
  - drive_download_file     — Get a Drive file back
  - drive_search            — Search Drive by name/query
  - sheets_read             — Read cells from a Google Sheet
  - sheets_write            — Write cells (with formulas)
  - docs_read               — Read a Google Doc as plain text
  - docs_replace_text       — Replace text throughout a Doc
  - generate_and_upload     — Combined: generate via code executor → upload
"""
import os
import json
import logging
from typing import Optional
from fastapi import APIRouter, Request, Response

logger = logging.getLogger("mcp_drive")

MCP_VERSION = "2024-11-05"

MCP_TOOLS = [
    {
        "name": "drive_list_folders",
        "description": "List folders in the user's Google Drive. parent_id='root' for top-level.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "parent_id": {"type": "string", "default": "root"},
                "query": {"type": "string"},
            },
            "required": ["user_id"],
        },
    },
    {
        "name": "drive_create_folder",
        "description": "Create a new folder in Google Drive.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "name": {"type": "string"},
                "parent_id": {"type": "string", "default": "root"},
            },
            "required": ["user_id", "name"],
        },
    },
    {
        "name": "drive_upload_file",
        "description": "Upload a Spectr-generated file (by our file_id) to user's Google Drive. Converts xlsx→Sheets, docx→Docs automatically.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "file_id": {"type": "string"},
                "folder_id": {"type": "string", "default": "root"},
                "convert": {"type": "boolean", "default": True},
            },
            "required": ["user_id", "file_id"],
        },
    },
    {
        "name": "drive_search",
        "description": "Search Drive for files by name. Returns id, name, mimeType, url.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "query": {"type": "string"},
                "mime_type": {"type": "string"},
                "max_results": {"type": "integer", "default": 20},
            },
            "required": ["user_id", "query"],
        },
    },
    {
        "name": "sheets_read",
        "description": "Read cells from a Google Sheet. range_a1 like 'Sheet1!A1:D10'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "sheet_id": {"type": "string"},
                "range_a1": {"type": "string", "default": "A1:ZZ1000"},
            },
            "required": ["user_id", "sheet_id"],
        },
    },
    {
        "name": "sheets_write",
        "description": "Write values to Google Sheet. Values may include formulas. USER_ENTERED interprets '=' prefix as formula.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "sheet_id": {"type": "string"},
                "range_a1": {"type": "string"},
                "values": {"type": "array"},
                "value_input_option": {"type": "string", "default": "USER_ENTERED"},
            },
            "required": ["user_id", "sheet_id", "range_a1", "values"],
        },
    },
    {
        "name": "docs_read",
        "description": "Read a Google Doc and return plain text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "doc_id": {"type": "string"},
            },
            "required": ["user_id", "doc_id"],
        },
    },
    {
        "name": "docs_replace_text",
        "description": "Replace text throughout a Google Doc.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "doc_id": {"type": "string"},
                "find": {"type": "string"},
                "replace": {"type": "string"},
                "match_case": {"type": "boolean", "default": True},
            },
            "required": ["user_id", "doc_id", "find", "replace"],
        },
    },
    {
        "name": "generate_and_upload",
        "description": "Generate a file using Spectr's code executor AND upload to Drive in one call.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "prompt": {"type": "string"},
                "folder_id": {"type": "string", "default": "root"},
                "convert": {"type": "boolean", "default": True},
            },
            "required": ["user_id", "prompt"],
        },
    },
]


async def _tool_drive_list_folders(db, args: dict) -> dict:
    from google_integration import get_valid_access_token, list_folders, get_folder_path
    token = await get_valid_access_token(db, args["user_id"])
    if not token:
        return {"error": "User has not connected Google account"}
    folders = await list_folders(token, parent_id=args.get("parent_id", "root"), query=args.get("query", ""))
    breadcrumb = await get_folder_path(token, args.get("parent_id", "root")) if args.get("parent_id", "root") != "root" else [{"id": "root", "name": "My Drive"}]
    return {"folders": folders, "breadcrumb": breadcrumb}


async def _tool_drive_create_folder(db, args: dict) -> dict:
    from google_integration import get_valid_access_token, create_folder
    token = await get_valid_access_token(db, args["user_id"])
    if not token:
        return {"error": "User has not connected Google account"}
    return await create_folder(token, args["name"], args.get("parent_id", "root"))


async def _tool_drive_upload_file(db, args: dict, files_cache: dict) -> dict:
    from google_integration import get_valid_access_token, upload_file_to_drive
    entry = files_cache.get(args["file_id"])
    if not entry:
        return {"error": f"File {args['file_id']} not found or expired"}
    token = await get_valid_access_token(db, args["user_id"])
    if not token:
        return {"error": "User has not connected Google account"}
    result = await upload_file_to_drive(
        token, entry["name"], entry["content"],
        folder_id=args.get("folder_id", "root") if args.get("folder_id", "root") != "root" else None,
        convert_to_google_format=args.get("convert", True),
    )
    return {
        "drive_file_id": result.get("id"),
        "drive_name": result.get("name"),
        "drive_url": result.get("webViewLink"),
        "mime_type": result.get("mimeType"),
        "converted": result.get("converted"),
    }


async def _tool_drive_search(db, args: dict) -> dict:
    import aiohttp
    from google_integration import get_valid_access_token
    token = await get_valid_access_token(db, args["user_id"])
    if not token:
        return {"error": "User has not connected Google account"}
    q_parts = ["trashed=false", f"name contains '{args['query']}'"]
    if args.get("mime_type"):
        q_parts.append(f"mimeType='{args['mime_type']}'")
    q = " and ".join(q_parts)
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://www.googleapis.com/drive/v3/files",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "q": q,
                "fields": "files(id,name,mimeType,webViewLink,modifiedTime,parents)",
                "pageSize": str(args.get("max_results", 20)),
            },
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                return {"error": f"Drive search failed: {resp.status}"}
            data = await resp.json()
            return {"files": data.get("files", [])}


async def _tool_sheets_read(db, args: dict) -> dict:
    from google_integration import get_valid_access_token, read_sheet_values
    token = await get_valid_access_token(db, args["user_id"])
    if not token:
        return {"error": "User has not connected Google account"}
    values = await read_sheet_values(token, args["sheet_id"], args.get("range_a1", "A1:ZZ1000"))
    return {"values": values, "rows": len(values), "cols": max((len(r) for r in values), default=0)}


async def _tool_sheets_write(db, args: dict) -> dict:
    from google_integration import get_valid_access_token, update_sheet_values
    token = await get_valid_access_token(db, args["user_id"])
    if not token:
        return {"error": "User has not connected Google account"}
    return await update_sheet_values(
        token, args["sheet_id"], args["range_a1"], args["values"],
        value_input_option=args.get("value_input_option", "USER_ENTERED"),
    )


async def _tool_docs_read(db, args: dict) -> dict:
    from google_integration import get_valid_access_token, get_doc, plain_text_from_doc
    token = await get_valid_access_token(db, args["user_id"])
    if not token:
        return {"error": "User has not connected Google account"}
    doc = await get_doc(token, args["doc_id"])
    return {"doc_id": args["doc_id"], "title": doc.get("title", ""), "text": plain_text_from_doc(doc)}


async def _tool_docs_replace_text(db, args: dict) -> dict:
    from google_integration import get_valid_access_token, batch_update_doc
    token = await get_valid_access_token(db, args["user_id"])
    if not token:
        return {"error": "User has not connected Google account"}
    req = {
        "replaceAllText": {
            "containsText": {"text": args["find"], "matchCase": args.get("match_case", True)},
            "replaceText": args["replace"],
        }
    }
    return await batch_update_doc(token, args["doc_id"], [req])


async def _tool_generate_and_upload(db, args: dict) -> dict:
    from code_executor import execute_user_task
    from google_integration import get_valid_access_token, upload_file_to_drive
    import base64 as _b64

    token = await get_valid_access_token(db, args["user_id"])
    if not token:
        return {"error": "User has not connected Google account"}

    result = await execute_user_task(args["prompt"], [], max_iterations=3)
    if result.get("status") != "success" or not result.get("output_files"):
        return {"error": f"Generation failed: {result.get('error', 'no files produced')}"}

    uploaded = []
    for f in result["output_files"]:
        try:
            content = _b64.b64decode(f["content_b64"])
            dr = await upload_file_to_drive(
                token, f["name"], content,
                folder_id=args.get("folder_id", "root") if args.get("folder_id", "root") != "root" else None,
                convert_to_google_format=args.get("convert", True),
            )
            uploaded.append({
                "original_name": f["name"],
                "drive_id": dr.get("id"),
                "drive_name": dr.get("name"),
                "drive_url": dr.get("webViewLink"),
                "converted": dr.get("converted"),
            })
        except Exception as e:
            uploaded.append({"original_name": f["name"], "error": str(e)})
    return {"uploaded": uploaded, "iterations": result.get("iterations")}


async def handle_mcp_request(request_data: dict, db, files_cache: dict) -> Optional[dict]:
    method = request_data.get("method", "")
    params = request_data.get("params", {})
    request_id = request_data.get("id")

    def _resp(result=None, error=None):
        r = {"jsonrpc": "2.0", "id": request_id}
        if error is not None:
            r["error"] = error
        else:
            r["result"] = result
        return r

    try:
        if method == "initialize":
            return _resp({
                "protocolVersion": MCP_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "spectr-drive-mcp", "version": "1.0.0"},
            })
        elif method == "notifications/initialized":
            return None
        elif method == "tools/list":
            return _resp({"tools": MCP_TOOLS})
        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            dispatch = {
                "drive_list_folders": lambda: _tool_drive_list_folders(db, tool_args),
                "drive_create_folder": lambda: _tool_drive_create_folder(db, tool_args),
                "drive_upload_file": lambda: _tool_drive_upload_file(db, tool_args, files_cache),
                "drive_search": lambda: _tool_drive_search(db, tool_args),
                "sheets_read": lambda: _tool_sheets_read(db, tool_args),
                "sheets_write": lambda: _tool_sheets_write(db, tool_args),
                "docs_read": lambda: _tool_docs_read(db, tool_args),
                "docs_replace_text": lambda: _tool_docs_replace_text(db, tool_args),
                "generate_and_upload": lambda: _tool_generate_and_upload(db, tool_args),
            }
            if tool_name not in dispatch:
                return _resp(error={"code": -32601, "message": f"Unknown tool: {tool_name}"})
            result = await dispatch[tool_name]()
            return _resp({
                "content": [{"type": "text", "text": json.dumps(result, default=str, indent=2)}],
                "isError": isinstance(result, dict) and bool(result.get("error")),
            })
        else:
            return _resp(error={"code": -32601, "message": f"Method not found: {method}"})
    except Exception as e:
        logger.exception(f"MCP request failed: {e}")
        return _resp(error={"code": -32000, "message": str(e)})


def create_mcp_router(db_getter, files_cache_getter):
    """Mount at /api/mcp/drive on main FastAPI app."""
    router = APIRouter(prefix="/mcp/drive")

    @router.post("")
    @router.post("/")
    async def rpc(request: Request):
        body = await request.json()
        db = db_getter()
        cache = files_cache_getter()
        if isinstance(body, list):
            results = []
            for r in body:
                resp = await handle_mcp_request(r, db, cache)
                if resp is not None:
                    results.append(resp)
            return results
        else:
            r = await handle_mcp_request(body, db, cache)
            return r if r else Response(status_code=204)

    @router.get("/tools")
    async def list_tools():
        return {"tools": MCP_TOOLS, "protocol_version": MCP_VERSION}

    @router.get("/info")
    async def info():
        return {
            "name": "spectr-drive-mcp",
            "version": "1.0.0",
            "protocol_version": MCP_VERSION,
            "tools_count": len(MCP_TOOLS),
        }

    return router


if __name__ == "__main__":
    import sys
    if "--stdio" in sys.argv:
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        from dotenv import load_dotenv
        from pathlib import Path
        load_dotenv(Path(__file__).parent / '.env')

        mongo_client = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        db = mongo_client["associate_db"]

        async def stdio_loop():
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            loop = asyncio.get_event_loop()
            await loop.connect_read_pipe(lambda: protocol, sys.stdin)
            while True:
                line = await reader.readline()
                if not line:
                    break
                try:
                    req = json.loads(line.decode('utf-8'))
                except json.JSONDecodeError:
                    continue
                resp = await handle_mcp_request(req, db, {})
                if resp is not None:
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()

        asyncio.run(stdio_loop())
    else:
        print("Spectr Drive MCP Server")
        print("Usage: python mcp_drive_server.py --stdio")
        print("Or mount the router: from mcp_drive_server import create_mcp_router")
