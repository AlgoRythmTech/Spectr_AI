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
                    
    # Get Firm Context from Library (Agentic Memory)
    library_items = await db.library_items.find({"user_id": user["user_id"]}).to_list(15)
    firm_context = ""
    if library_items:
        firm_context = "Apply the following internal firm templates, principles, and precedents strictly if relevant:\n\n"
        for idx, item in enumerate(library_items):
            firm_context += f"--- Precedent {idx+1}: {item.get('title', '')} ({item.get('item_type', '')}) ---\n"
            firm_context += f"{item.get('content', '')}\n\n"
    
    # PII Anonymization (pre-LLM redaction)
    sanitized_query = req.query
    pii_report = None
    if req.anonymize_pii:
        pii_result = anonymize_text(req.query, redact_level="standard")
        sanitized_query = pii_result["anonymized_text"]
        if pii_result["redactions_count"] > 0:
            pii_report = pii_result
            logger.info(f"PII Guard: Redacted {pii_result['redactions_count']} items from query")

    result = await process_query(
        user_query=sanitized_query,
        mode=req.mode,
        matter_context=matter_context,
        statute_context=statute_context,
        firm_context=firm_context
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
