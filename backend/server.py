from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form, Request, Response, Header, Query
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
import io
import re
import aiohttp
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from ai_engine import process_query, process_document_analysis, generate_workflow_document, classify_query
from indian_kanoon import search_indiankanoon
from insta_financials import search_company, get_company_data
from document_export import generate_word_document, generate_pdf_bytes
from storage_utils import init_storage, put_object, get_object, generate_storage_path

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

class UserOut(BaseModel):
    user_id: str
    email: str
    name: str
    picture: str = ""
    role: str = "associate"
    firm_name: str = ""
    created_at: str = ""

class MatterCreate(BaseModel):
    name: str
    client_name: str = ""
    matter_type: str = "general"
    description: str = ""

class QueryRequest(BaseModel):
    query: str
    mode: str = "partner"
    matter_id: str = ""
    language: str = "english"

class WorkflowRequest(BaseModel):
    workflow_type: str
    fields: dict
    mode: str = "partner"

class DocumentAnalysisRequest(BaseModel):
    document_id: str
    analysis_type: str = "general"

class ExportRequest(BaseModel):
    content: str
    title: str
    format: str = "docx"
    header_option: str = ""
    watermark: str = ""

class LibraryItemCreate(BaseModel):
    title: str
    content: str
    item_type: str = "template"
    tags: list = []

class AnnotationCreate(BaseModel):
    response_id: str
    text: str

# ==================== AUTH HELPERS ====================

async def get_current_user(request: Request, authorization: str = Header(None)) -> dict:
    session_token = request.cookies.get("session_token")
    if not session_token and authorization:
        session_token = authorization.replace("Bearer ", "")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ==================== AUTH ROUTES ====================

@api_router.get("/")
async def root():
    return {"message": "Associate API — Built by AlgoRythm Group"}

@api_router.post("/auth/session")
async def exchange_session(request: Request):
    body = await request.json()
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    async with aiohttp.ClientSession() as http_session:
        async with http_session.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id},
            timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=401, detail="Invalid session")
            data = await resp.json()
    
    email = data.get("email", "")
    name = data.get("name", "")
    picture = data.get("picture", "")
    session_token = data.get("session_token", "")
    
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one({"email": email}, {"$set": {"name": name, "picture": picture}})
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "role": "associate",
            "firm_name": "",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": datetime(2026, 3, 17, tzinfo=timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    response = Response(content='{"status":"ok"}', media_type="application/json")
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7*24*60*60
    )
    return response

@api_router.get("/auth/me")
async def get_me(request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    return UserOut(**user)

@api_router.post("/auth/logout")
async def logout(request: Request):
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    response = Response(content='{"status":"logged_out"}', media_type="application/json")
    response.delete_cookie("session_token", path="/")
    return response

# ==================== MATTER ROUTES ====================

@api_router.post("/matters")
async def create_matter(matter: MatterCreate, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    matter_id = f"matter_{uuid.uuid4().hex[:12]}"
    doc = {
        "matter_id": matter_id,
        "user_id": user["user_id"],
        "name": matter.name,
        "client_name": matter.client_name,
        "matter_type": matter.matter_type,
        "description": matter.description,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.matters.insert_one(doc)
    return {k: v for k, v in doc.items() if k != "_id"}

@api_router.get("/matters")
async def list_matters(request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    matters = await db.matters.find({"user_id": user["user_id"]}, {"_id": 0}).sort("updated_at", -1).to_list(100)
    return matters

@api_router.get("/matters/{matter_id}")
async def get_matter(matter_id: str, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    matter = await db.matters.find_one({"matter_id": matter_id, "user_id": user["user_id"]}, {"_id": 0})
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")
    return matter

# ==================== ASSISTANT ROUTES ====================

@api_router.post("/assistant/query")
async def assistant_query(req: QueryRequest, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    
    # Get statute context from DB
    statute_context = await get_statute_context(req.query)
    
    # Get matter context if provided
    matter_context = ""
    if req.matter_id:
        matter = await db.matters.find_one({"matter_id": req.matter_id}, {"_id": 0})
        if matter:
            matter_context = f"Matter: {matter.get('name', '')} | Client: {matter.get('client_name', '')} | Type: {matter.get('matter_type', '')}"
            # Get recent conversation history for this matter
            recent = await db.query_history.find(
                {"matter_id": req.matter_id}, {"_id": 0}
            ).sort("created_at", -1).limit(3).to_list(3)
            if recent:
                matter_context += "\n\nRecent conversation context:\n"
                for r in reversed(recent):
                    matter_context += f"Q: {r.get('query', '')[:200]}\nA: {r.get('response_text', '')[:500]}\n\n"
    
    result = await process_query(
        user_query=req.query,
        mode=req.mode,
        matter_context=matter_context,
        statute_context=statute_context
    )
    
    # Save to history
    history_id = f"qh_{uuid.uuid4().hex[:12]}"
    history_doc = {
        "history_id": history_id,
        "user_id": user["user_id"],
        "matter_id": req.matter_id,
        "query": req.query,
        "mode": req.mode,
        "response_text": result["response_text"],
        "sections": result["sections"],
        "query_types": result["query_types"],
        "model_used": result["model_used"],
        "sources": result["sources"],
        "citations_count": result["citations_count"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.query_history.insert_one(history_doc)
    
    # Update matter timestamp
    if req.matter_id:
        await db.matters.update_one(
            {"matter_id": req.matter_id},
            {"$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    return {
        "history_id": history_id,
        "response_text": result["response_text"],
        "sections": result["sections"],
        "query_types": result["query_types"],
        "model_used": result["model_used"],
        "sources": result["sources"],
        "citations_count": result["citations_count"],
    }


async def get_statute_context(query: str) -> str:
    """Search statute DB for relevant sections."""
    query_lower = query.lower()
    keywords = re.findall(r'\b\w+\b', query_lower)
    
    # Search statutes collection
    relevant = []
    search_terms = [kw for kw in keywords if len(kw) > 3][:10]
    
    if search_terms:
        regex_pattern = "|".join(search_terms)
        cursor = db.statutes.find(
            {"$or": [
                {"section_text": {"$regex": regex_pattern, "$options": "i"}},
                {"section_title": {"$regex": regex_pattern, "$options": "i"}},
                {"act_name": {"$regex": regex_pattern, "$options": "i"}},
                {"keywords": {"$in": search_terms}}
            ]},
            {"_id": 0}
        ).limit(10)
        relevant = await cursor.to_list(10)
    
    if not relevant:
        return ""
    
    context_parts = []
    for s in relevant:
        context_parts.append(
            f"Section {s.get('section_number', 'N/A')} of {s.get('act_name', 'N/A')}"
            f" — {s.get('section_title', '')}\n"
            f"{s.get('section_text', '')[:500]}"
        )
    return "\n\n".join(context_parts)

# ==================== VAULT ROUTES ====================

@api_router.post("/vault/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    authorization: str = Header(None)
):
    user = await get_current_user(request, authorization)
    
    file_data = await file.read()
    file_ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "bin"
    
    # Extract text based on file type
    extracted_text = ""
    if file_ext == "pdf":
        extracted_text = extract_pdf_text(file_data)
    elif file_ext in ["doc", "docx"]:
        extracted_text = extract_docx_text(file_data)
    elif file_ext in ["txt", "csv"]:
        extracted_text = file_data.decode("utf-8", errors="ignore")
    elif file_ext in ["xlsx", "xls"]:
        extracted_text = extract_xlsx_text(file_data)
    elif file_ext in ["jpg", "jpeg", "png"]:
        extracted_text = "[Image uploaded - OCR processing available]"
    
    # Classify document type
    doc_type = classify_document(file.filename, extracted_text)
    
    # Upload to storage
    storage_path = generate_storage_path(user["user_id"], file.filename)
    try:
        storage_result = put_object(storage_path, file_data, file.content_type or "application/octet-stream")
    except Exception as e:
        logger.error(f"Storage upload failed: {e}")
        storage_result = {"path": storage_path}
    
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    doc = {
        "doc_id": doc_id,
        "user_id": user["user_id"],
        "filename": file.filename,
        "file_ext": file_ext,
        "content_type": file.content_type,
        "storage_path": storage_result.get("path", storage_path),
        "size": len(file_data),
        "doc_type": doc_type,
        "extracted_text": extracted_text[:50000],
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.documents.insert_one(doc)
    
    return {k: v for k, v in doc.items() if k not in ["_id", "extracted_text"]}

@api_router.get("/vault/documents")
async def list_documents(request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    docs = await db.documents.find(
        {"user_id": user["user_id"], "is_deleted": False},
        {"_id": 0, "extracted_text": 0}
    ).sort("created_at", -1).to_list(100)
    return docs

@api_router.post("/vault/analyze")
async def analyze_document(req: DocumentAnalysisRequest, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    
    doc = await db.documents.find_one(
        {"doc_id": req.document_id, "user_id": user["user_id"]},
        {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    result = await process_document_analysis(
        document_text=doc.get("extracted_text", ""),
        doc_type=doc.get("doc_type", "other"),
        analysis_type=req.analysis_type
    )
    
    # Save analysis
    analysis_id = f"analysis_{uuid.uuid4().hex[:12]}"
    analysis_doc = {
        "analysis_id": analysis_id,
        "doc_id": req.document_id,
        "user_id": user["user_id"],
        "analysis_type": req.analysis_type,
        "response_text": result["response_text"],
        "sections": result["sections"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.document_analyses.insert_one(analysis_doc)
    
    return {
        "analysis_id": analysis_id,
        "response_text": result["response_text"],
        "sections": result["sections"],
        "doc_type": result["doc_type"],
        "analysis_type": result["analysis_type"]
    }

@api_router.post("/vault/ask")
async def vault_ask(request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    body = await request.json()
    question = body.get("question", "")
    doc_ids = body.get("doc_ids", [])
    
    if not question:
        raise HTTPException(status_code=400, detail="Question required")
    
    # Gather document texts
    combined_text = ""
    for did in doc_ids[:20]:
        doc = await db.documents.find_one({"doc_id": did, "user_id": user["user_id"]}, {"_id": 0})
        if doc:
            combined_text += f"\n--- Document: {doc.get('filename', 'N/A')} ---\n{doc.get('extracted_text', '')[:5000]}\n"
    
    if not combined_text:
        combined_text = "No documents selected."
    
    result = await process_document_analysis(
        document_text=combined_text,
        doc_type="bulk",
        analysis_type="general"
    )
    
    return {
        "response_text": result["response_text"],
        "sections": result["sections"],
    }

# ==================== WORKFLOW ROUTES ====================

WORKFLOWS = [
    {"id": "cheque_bounce_notice", "name": "Legal Notice — Section 138 NI Act (Cheque Bounce)", "category": "litigation",
     "fields": [{"name": "sender_name", "label": "Sender Name", "type": "text"},
                {"name": "sender_address", "label": "Sender Address", "type": "textarea"},
                {"name": "receiver_name", "label": "Receiver Name", "type": "text"},
                {"name": "receiver_address", "label": "Receiver Address", "type": "textarea"},
                {"name": "amount", "label": "Cheque Amount (INR)", "type": "text"},
                {"name": "cheque_number", "label": "Cheque Number", "type": "text"},
                {"name": "bank_name", "label": "Bank Name", "type": "text"},
                {"name": "dishonour_date", "label": "Dishonour Date", "type": "date"}]},
    {"id": "general_demand_notice", "name": "Legal Notice — General Demand", "category": "litigation",
     "fields": [{"name": "sender_name", "label": "Sender Name", "type": "text"},
                {"name": "receiver_name", "label": "Receiver Name", "type": "text"},
                {"name": "subject", "label": "Subject Matter", "type": "textarea"},
                {"name": "amount", "label": "Amount/Relief", "type": "text"},
                {"name": "deadline_days", "label": "Deadline (days)", "type": "text"}]},
    {"id": "consumer_complaint", "name": "Consumer Forum Complaint", "category": "litigation",
     "fields": [{"name": "complainant", "label": "Complainant Name & Address", "type": "textarea"},
                {"name": "opposite_party", "label": "Opposite Party Name & Address", "type": "textarea"},
                {"name": "product_service", "label": "Product/Service", "type": "text"},
                {"name": "deficiency", "label": "Deficiency in Service", "type": "textarea"},
                {"name": "relief_sought", "label": "Relief Sought", "type": "textarea"}]},
    {"id": "rti_application", "name": "RTI Application", "category": "litigation",
     "fields": [{"name": "public_authority", "label": "Public Authority", "type": "text"},
                {"name": "information_sought", "label": "Information Sought", "type": "textarea"},
                {"name": "reason", "label": "Supporting Reason", "type": "textarea"}]},
    {"id": "rera_complaint", "name": "RERA Complaint", "category": "litigation",
     "fields": [{"name": "buyer_details", "label": "Buyer Details", "type": "textarea"},
                {"name": "builder_details", "label": "Builder Details", "type": "textarea"},
                {"name": "rera_number", "label": "Project RERA Number", "type": "text"},
                {"name": "deficiency", "label": "Deficiency/Delay Details", "type": "textarea"}]},
    {"id": "bail_application", "name": "Bail Application (Sessions/HC)", "category": "litigation",
     "fields": [{"name": "accused_details", "label": "Accused Details", "type": "textarea"},
                {"name": "fir_details", "label": "FIR Details (No., Date, PS)", "type": "textarea"},
                {"name": "offence", "label": "Offence Charged", "type": "text"},
                {"name": "grounds", "label": "Grounds for Bail", "type": "textarea"}]},
    {"id": "legal_research_memo", "name": "Legal Research Memo", "category": "litigation",
     "fields": [{"name": "legal_issue", "label": "Legal Issue", "type": "textarea"},
                {"name": "jurisdiction", "label": "Jurisdiction", "type": "text"},
                {"name": "key_facts", "label": "Key Facts", "type": "textarea"}]},
    {"id": "writ_petition", "name": "Writ Petition (HC) — Brief", "category": "litigation",
     "fields": [{"name": "violation", "label": "Constitutional/Legal Violation", "type": "textarea"},
                {"name": "authority", "label": "Authority Against", "type": "text"},
                {"name": "relief", "label": "Relief Sought", "type": "textarea"},
                {"name": "facts", "label": "Material Facts", "type": "textarea"}]},
    {"id": "written_statement", "name": "Written Statement / Reply to Plaint", "category": "litigation",
     "fields": [{"name": "case_details", "label": "Case Number & Court", "type": "text"},
                {"name": "plaint_summary", "label": "Plaint Summary / Upload Content", "type": "textarea"},
                {"name": "client_version", "label": "Client's Version of Facts", "type": "textarea"}]},
    {"id": "contract_review", "name": "Contract Review + Risk Report", "category": "litigation",
     "fields": [{"name": "contract_text", "label": "Paste Contract Text or Key Clauses", "type": "textarea"},
                {"name": "party_role", "label": "Your Client is (Party A/B)", "type": "text"}]},
    {"id": "gst_scn_response", "name": "GST SCN Response", "category": "taxation",
     "fields": [{"name": "company_name", "label": "Company Name", "type": "text"},
                {"name": "gstin", "label": "GSTIN", "type": "text"},
                {"name": "scn_number", "label": "SCN Number", "type": "text"},
                {"name": "scn_date", "label": "SCN Date", "type": "date"},
                {"name": "demand_amount", "label": "Demand Amount (INR)", "type": "text"},
                {"name": "issue_type", "label": "Issue Type", "type": "text"}]},
    {"id": "gst_appeal", "name": "GST Appeal — First Appellate Authority", "category": "taxation",
     "fields": [{"name": "order_details", "label": "Order Details", "type": "textarea"},
                {"name": "grounds", "label": "Grounds of Dispute", "type": "textarea"},
                {"name": "amount", "label": "Disputed Amount (INR)", "type": "text"}]},
    {"id": "it_notice_143", "name": "Income Tax Notice Reply — Section 143(1)", "category": "taxation",
     "fields": [{"name": "pan", "label": "PAN", "type": "text"},
                {"name": "assessment_year", "label": "Assessment Year", "type": "text"},
                {"name": "demand_raised", "label": "Demand Raised (INR)", "type": "text"},
                {"name": "nature_of_addition", "label": "Nature of Addition", "type": "textarea"}]},
    {"id": "it_notice_148", "name": "Income Tax Notice Reply — Section 148 (Escaped Assessment)", "category": "taxation",
     "fields": [{"name": "pan", "label": "PAN", "type": "text"},
                {"name": "year", "label": "Assessment Year", "type": "text"},
                {"name": "reasons", "label": "Reasons Given for Reopening", "type": "textarea"}]},
    {"id": "pmla_compliance", "name": "PMLA Compliance Note", "category": "taxation",
     "fields": [{"name": "transaction_details", "label": "Transaction Details", "type": "textarea"},
                {"name": "entity_type", "label": "Entity Type", "type": "text"},
                {"name": "amount", "label": "Amount (INR)", "type": "text"},
                {"name": "cross_border", "label": "Cross-border (Y/N)", "type": "text"}]},
    {"id": "fema_compounding", "name": "FEMA Compounding Application", "category": "taxation",
     "fields": [{"name": "transaction_details", "label": "Transaction Details", "type": "textarea"},
                {"name": "rbi_direction", "label": "RBI Master Direction Reference", "type": "text"},
                {"name": "violation_details", "label": "Violation Details", "type": "textarea"}]},
    {"id": "due_diligence", "name": "Due Diligence Report — Company Acquisition", "category": "taxation",
     "fields": [{"name": "company_name", "label": "Company Name", "type": "text"},
                {"name": "cin", "label": "CIN (if available)", "type": "text"}]},
    {"id": "financial_health", "name": "Financial Health Report", "category": "taxation",
     "fields": [{"name": "company_name", "label": "Company Name", "type": "text"}]},
    {"id": "ibc_section9", "name": "IBC Section 9 — Operational Creditor Application", "category": "taxation",
     "fields": [{"name": "creditor", "label": "Operational Creditor Details", "type": "textarea"},
                {"name": "corporate_debtor", "label": "Corporate Debtor Details", "type": "textarea"},
                {"name": "debt_details", "label": "Debt Details", "type": "textarea"},
                {"name": "demand_notice", "label": "Demand Notice History", "type": "textarea"}]},
    {"id": "director_disqualification", "name": "Director Disqualification Check + Response", "category": "taxation",
     "fields": [{"name": "din", "label": "DIN Number", "type": "text"}]},
]

@api_router.get("/workflows")
async def list_workflows():
    return WORKFLOWS

@api_router.post("/workflows/generate")
async def generate_workflow(req: WorkflowRequest, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    
    workflow = next((w for w in WORKFLOWS if w["id"] == req.workflow_type), None)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    result = await generate_workflow_document(
        workflow_type=workflow["name"],
        fields=req.fields,
        mode=req.mode
    )
    
    # Save to history
    gen_id = f"wf_{uuid.uuid4().hex[:12]}"
    await db.workflow_history.insert_one({
        "gen_id": gen_id,
        "user_id": user["user_id"],
        "workflow_type": req.workflow_type,
        "workflow_name": workflow["name"],
        "fields": req.fields,
        "response_text": result["response_text"],
        "sources": result.get("sources", []),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "gen_id": gen_id,
        "response_text": result["response_text"],
        "workflow_name": workflow["name"],
        "sources": result.get("sources", []),
    }

# ==================== EXPORT ROUTES ====================

@api_router.post("/export/word")
async def export_word(req: ExportRequest, request: Request, authorization: str = Header(None)):
    await get_current_user(request, authorization)
    doc_bytes = generate_word_document(req.title, req.content, header_option=req.header_option)
    return StreamingResponse(
        io.BytesIO(doc_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={req.title.replace(' ', '_')}.docx"}
    )

@api_router.post("/export/pdf")
async def export_pdf(req: ExportRequest, request: Request, authorization: str = Header(None)):
    await get_current_user(request, authorization)
    pdf_bytes = generate_pdf_bytes(req.title, req.content, header_option=req.header_option, watermark=req.watermark)
    if not pdf_bytes:
        raise HTTPException(status_code=500, detail="PDF generation failed")
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={req.title.replace(' ', '_')}.pdf"}
    )

# ==================== HISTORY ROUTES ====================

@api_router.get("/history")
async def get_history(request: Request, authorization: str = Header(None), limit: int = 50):
    user = await get_current_user(request, authorization)
    history = await db.query_history.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return history

@api_router.get("/history/{history_id}")
async def get_history_item(history_id: str, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    item = await db.query_history.find_one(
        {"history_id": history_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not item:
        raise HTTPException(status_code=404, detail="History item not found")
    return item

@api_router.get("/history/matter/{matter_id}")
async def get_matter_history(matter_id: str, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    history = await db.query_history.find(
        {"matter_id": matter_id, "user_id": user["user_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return history

# ==================== LIBRARY ROUTES ====================

@api_router.post("/library")
async def create_library_item(item: LibraryItemCreate, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    item_id = f"lib_{uuid.uuid4().hex[:12]}"
    doc = {
        "item_id": item_id,
        "user_id": user["user_id"],
        "title": item.title,
        "content": item.content,
        "item_type": item.item_type,
        "tags": item.tags,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.library.insert_one(doc)
    return {k: v for k, v in doc.items() if k != "_id"}

@api_router.get("/library")
async def list_library(request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    items = await db.library.find({"user_id": user["user_id"]}, {"_id": 0}).sort("updated_at", -1).to_list(100)
    return items

@api_router.delete("/library/{item_id}")
async def delete_library_item(item_id: str, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    result = await db.library.delete_one({"item_id": item_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "deleted"}

# ==================== SEARCH ROUTES ====================

@api_router.get("/search/cases")
async def search_cases(q: str = Query(...)):
    results = await search_indiankanoon(q, top_k=10)
    return results

@api_router.get("/search/companies")
async def search_companies(q: str = Query(...)):
    results = await search_company(q)
    return results

# ==================== STATUTE DB ROUTES ====================

@api_router.get("/statutes")
async def search_statutes(q: str = Query(""), act: str = Query("")):
    query_filter = {}
    if q:
        query_filter["$or"] = [
            {"section_text": {"$regex": q, "$options": "i"}},
            {"section_title": {"$regex": q, "$options": "i"}},
        ]
    if act:
        query_filter["act_name"] = {"$regex": act, "$options": "i"}
    
    results = await db.statutes.find(query_filter, {"_id": 0}).limit(20).to_list(20)
    return results

# ==================== HELPERS ====================

def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF."""
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        return text.strip()
    except ImportError:
        try:
            from io import BytesIO
            from pdfminer.high_level import extract_text
            return extract_text(BytesIO(pdf_bytes))
        except ImportError:
            return "[PDF text extraction not available - install PyMuPDF or pdfminer]"


def extract_docx_text(docx_bytes: bytes) -> str:
    """Extract text from DOCX."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(docx_bytes))
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        return f"[DOCX extraction error: {e}]"


def extract_xlsx_text(xlsx_bytes: bytes) -> str:
    """Extract text from XLSX."""
    try:
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(xlsx_bytes), read_only=True)
        text = ""
        for sheet in wb.sheetnames:
            ws = wb[sheet]
            text += f"\n--- Sheet: {sheet} ---\n"
            for row in ws.iter_rows(values_only=True):
                text += " | ".join([str(c) if c else "" for c in row]) + "\n"
        return text.strip()
    except Exception as e:
        return f"[XLSX extraction error: {e}]"


def classify_document(filename: str, text: str) -> str:
    """Auto-classify document type."""
    filename_lower = filename.lower()
    text_lower = text[:2000].lower() if text else ""
    
    if any(kw in text_lower for kw in ["agreement", "contract", "whereas", "hereby agree"]):
        return "contract"
    if any(kw in text_lower for kw in ["order", "judgment", "hon'ble", "court"]):
        return "court_order"
    if any(kw in text_lower for kw in ["gst", "cgst", "show cause", "scn"]):
        return "gst_notice"
    if any(kw in text_lower for kw in ["income tax", "143", "148", "assessment"]):
        return "it_notice"
    if any(kw in text_lower for kw in ["balance sheet", "profit", "loss", "revenue"]):
        return "financial_statement"
    if any(kw in text_lower for kw in ["moa", "aoa", "board resolution", "company"]):
        return "corporate_document"
    if any(kw in text_lower for kw in ["sale deed", "property", "conveyance"]):
        return "property_document"
    return "other"


# ==================== STARTUP ====================

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed (non-blocking): {e}")
    
    # Create indexes
    await db.statutes.create_index([("act_name", 1), ("section_number", 1)])
    await db.statutes.create_index([("keywords", 1)])
    await db.query_history.create_index([("user_id", 1), ("created_at", -1)])
    await db.documents.create_index([("user_id", 1), ("created_at", -1)])
    await db.matters.create_index([("user_id", 1)])
    logger.info("Associate API started successfully")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
