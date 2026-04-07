import sys

with open(r'c:\Users\aasri\Associate_Research\backend\server.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_routes = '''
from obligation_extractor import extract_obligations
from workflow_chain import start_chain, advance_chain, get_chain_status, get_templates
from court_tracker import track_case, get_tracked_cases, remove_tracked_case, refresh_case, search_ecourts
from playbook_engine import compare_against_playbook
from judgment_summarizer import summarize_judgment

class ObligationRequest(BaseModel):
    document_text: str

@api_router.post("/vault/extract-obligations")
async def extract_obligations_endpoint(req: ObligationRequest, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    result = await extract_obligations(req.document_text)
    return result

class ChainStartRequest(BaseModel):
    chain_type: str
    initial_input: str

class ChainAdvanceRequest(BaseModel):
    chain_id: str
    edited_output: str = None

@api_router.get("/workflows/chain/templates")
async def get_chain_templates(request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    return {"templates": get_templates()}

@api_router.post("/workflows/chain/start")
async def start_chain_endpoint(req: ChainStartRequest, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    result = await start_chain(req.chain_type, req.initial_input, user["user_id"])
    return result

@api_router.post("/workflows/chain/next")
async def advance_chain_endpoint(req: ChainAdvanceRequest, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    result = await advance_chain(req.chain_id, req.edited_output)
    return result

@api_router.get("/workflows/chain/{chain_id}")
async def get_chain_endpoint(chain_id: str, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    result = await get_chain_status(chain_id)
    return result

class CourtTrackRequest(BaseModel):
    case_number: str
    court: str = "supreme_court"
    party_name: str = ""
    matter_id: str = None

@api_router.post("/court/track")
async def track_case_endpoint(req: CourtTrackRequest, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    result = await track_case(user["user_id"], req.case_number, req.court, req.party_name, req.matter_id)
    return result

@api_router.get("/court/upcoming")
async def get_upcoming_cases(request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    cases = await get_tracked_cases(user["user_id"])
    return {"cases": cases}

@api_router.delete("/court/track/{track_id}")
async def remove_case_endpoint(track_id: str, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    success = await remove_tracked_case(track_id, user["user_id"])
    return {"deleted": success}

@api_router.post("/court/refresh/{track_id}")
async def refresh_case_endpoint(track_id: str, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    result = await refresh_case(track_id)
    return result

class PlaybookCompareRequest(BaseModel):
    playbook_text: str
    draft_text: str

@api_router.post("/playbook/compare")
async def playbook_compare_endpoint(req: PlaybookCompareRequest, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    result = await compare_against_playbook(req.playbook_text, req.draft_text)
    return result

class JudgmentSummarizeRequest(BaseModel):
    document_text: str

@api_router.post("/vault/summarize-judgment")
async def summarize_judgment_endpoint(req: JudgmentSummarizeRequest, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    result = await summarize_judgment(req.document_text)
    return result

class WorkspaceInvite(BaseModel):
    matter_id: str
    email: str
    role: str = "editor"

@api_router.post("/matters/{matter_id}/invite")
async def invite_to_matter(matter_id: str, req: WorkspaceInvite, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    member_doc = {
        "matter_id": matter_id,
        "invited_by": user["user_id"],
        "email": req.email,
        "role": req.role,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.workspace_members.insert_one(member_doc)
    return {"message": f"Invitation sent to {req.email}"}

@api_router.get("/matters/{matter_id}/members")
async def get_matter_members(matter_id: str, request: Request, authorization: str = Header(None)):
    user = await get_current_user(request, authorization)
    cursor = db.workspace_members.find({"matter_id": matter_id})
    members = []
    async for doc in cursor:
        doc.pop("_id", None)
        members.append(doc)
    return {"members": members}

'''

content = content.replace('# ==================== MOUNT ROUTER ====================', new_routes + '# ==================== MOUNT ROUTER ====================')

with open(r'c:\Users\aasri\Associate_Research\backend\server.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done - all routes added')
