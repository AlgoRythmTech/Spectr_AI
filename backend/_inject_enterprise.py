import os
import re

file_path = r"c:\Users\aasri\Associate_Research\backend\server.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

if "from statute_updater import" not in content:
    new_imports = """
from statute_updater import check_for_updates, get_recent_updates
from enhanced_export import generate_memo_export, generate_court_document, generate_tax_notice_reply
from email_ingestion import generate_ingest_address
from document_parser import parse_document_structure
"""
    
    new_routes = """

@api_router.get("/regulatory/updates")
async def get_regulatory_updates_route(category: str = None, request: Request = None, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    updates = await get_recent_updates(category=category)
    return {"updates": updates}

@api_router.post("/regulatory/force-check")
async def check_regulatory_updates_route(request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    new_updates = await check_for_updates()
    return {"new_updates_found": len(new_updates), "updates": new_updates}

@api_router.post("/export/enhanced")
async def enhanced_export_route(request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    data = await request.json()
    doc_type = data.get("doc_type", "memo")
    content = data.get("content", "")
    
    if doc_type == "court":
        doc_bytes = generate_court_document(
            content=content,
            court_type=data.get("court_type", "high_court"),
            case_number=data.get("case_number", ""),
            petitioner=data.get("petitioner", ""),
            respondent=data.get("respondent", ""),
            document_type=data.get("document_type", "PETITION")
        )
        filename = "Court_Filing.docx"
    elif doc_type == "tax_reply":
        doc_bytes = generate_tax_notice_reply(
            notice_details=data.get("notice_details", {}),
            reply_content=content
        )
        filename = "Notice_Reply.docx"
    else:
        doc_bytes = generate_memo_export(content, title=data.get("title", "Legal Memorandum"))
        filename = "Legal_Memo.docx"
        
    return Response(
        content=doc_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@api_router.get("/matters/{matter_id}/ingest-email")
async def get_ingest_email_route(matter_id: str, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    email = await generate_ingest_address(matter_id, user["user_id"])
    return {"ingestion_email": email}

"""

    content = content.replace("from auth import ", new_imports + "from auth import ")
    content = content.replace("# ==================== MOUNT ROUTER ====================", new_routes + "# ==================== MOUNT ROUTER ====================")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Routes injected")
else:
    print("Routes already present")
