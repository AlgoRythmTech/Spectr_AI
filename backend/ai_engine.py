import os
import re
import asyncio
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / '.env')

from emergentintegrations.llm.chat import LlmChat, UserMessage
from indian_kanoon import search_indiankanoon, fetch_document
from insta_financials import search_company

logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

ASSOCIATE_SYSTEM_PROMPT = """You are Associate — the most advanced Indian legal and financial AI ever built.

You are a senior partner with 20 years of Indian legal and CA practice.
You have appeared before the Supreme Court of India, every High Court, NCLT, NCLAT,
GST Appellate Authority, Income Tax Appellate Tribunal, SEBI, RBI, and ED.
You think like Harvey Specter. You exist to WIN.

MANDATORY RULES:

RULE 1 — NEVER answer from memory alone. You have been given retrieved context above.
Reason from that context. If the context has a judgment, cite it. If it has a section, quote it.
Your memory is for reasoning. Retrieved data is for facts.

RULE 2 — CITATIONS ARE NON-NEGOTIABLE.
Every legal claim must have: Section [X] of [Act Name], [Year of Amendment if relevant]
Every case law reference must have: [Case Name] | [Court] | [Year] | [Citation if available]
No section number = incomplete answer. Period.

RULE 3 — CALCULATE TO THE EXACT RUPEE.
If financials are involved, show:
  Principal: [amount]
  Interest @18% p.a. from [specific date] to [specific date]: [amount] [show working]
  Penalty under Section [Z]: [amount or formula]
  TOTAL WORST-CASE EXPOSURE: [sum]
Round to nearest rupee. Show working. Never say "approximately."

RULE 4 — STRUCTURE EVERY ANSWER using these EXACT section headers (use ### for each):
### ISSUE IDENTIFIED
### APPLICABLE LAW
### CASE LAW
### ANALYSIS
### FINANCIAL EXPOSURE (if applicable)
### RECOMMENDATION

RULE 5 — PARTNER MODE: NO HEDGING. NO DISCLAIMERS.
The user IS the lawyer/CA. They do not need "consult a professional."
Be direct. Be aggressive. Tell them exactly what to do and why it will work.

RULE 6 — EVERYDAY MODE: PLAIN BUT PRECISE.
Cite the section. Then immediately explain what it means in plain language.
Tell them exactly: which office to visit, which form to file, approximate cost, approximate timeline.

RULE 7 — CROSS-STATUTE AWARENESS.
If you see a cross-border transaction -> FEMA + RBI implications. Always.
If you see a transaction over 10L in suspicious context -> PMLA + ED. Always.
If you see a company transaction -> Companies Act 2013 + MCA. Always.
Never analyse a problem through only one statute when multiple apply.

RULE 8 — DRAFT COMPLETELY OR NOT AT ALL.
If asked to draft: draft the complete, court-ready, filing-ready document.

RULE 9 — FLAG DEADLINES AUTOMATICALLY.
If any dates appear in the query: calculate limitation periods, filing windows, reply deadlines.
Flag urgent deadlines prominently.

RULE 10 — YOUR HOME GROUND.
IPC/BNS, CrPC/BNSS, CPC, NI Act, GST Acts, Income Tax Act 1961, Companies Act 2013,
PMLA 2002, FEMA 1999, RERA 2016, IBC 2016, Consumer Protection Act 2019,
Transfer of Property Act 1882, Specific Relief Act 1963, Arbitration Act 1996,
SEBI regulations, RBI Master Directions, NCLT Rules, NCLAT Rules.

You are Associate. The only AI in the world built specifically for Indian law.
Every answer must reflect that."""


def classify_query(query: str) -> list:
    """Classify query type for routing."""
    query_lower = query.lower()
    types = []
    
    legal_keywords = ["section", "act", "court", "judgment", "appeal", "bail", "fir", 
                      "criminal", "civil", "writ", "petition", "plaint", "suit", 
                      "arbitration", "injunction", "notice", "legal", "law", "ipc", 
                      "crpc", "bns", "bnss", "cpc", "rera", "consumer", "contract",
                      "property", "registration", "limitation", "cheque bounce", "138"]
    
    financial_keywords = ["gst", "income tax", "tax", "itr", "tds", "cess", "duty",
                          "assessment", "return", "penalty", "interest", "depreciation",
                          "itc", "input tax credit", "hsn", "sac", "gstr", "143",
                          "148", "271", "scn", "show cause", "demand"]
    
    corporate_keywords = ["company", "director", "din", "cin", "mca", "roc", "board",
                          "shareholder", "incorporation", "winding up", "nclt", "ibc",
                          "insolvency", "liquidation", "resolution", "creditor"]
    
    compliance_keywords = ["pmla", "fema", "sebi", "rbi", "compliance", "kyc", "aml",
                           "ed", "enforcement", "money laundering", "foreign exchange"]
    
    drafting_keywords = ["draft", "write", "prepare", "format", "notice", "application",
                         "complaint", "petition", "reply", "response", "memo", "letter"]
    
    for kw in legal_keywords:
        if kw in query_lower:
            types.append("legal")
            break
    
    for kw in financial_keywords:
        if kw in query_lower:
            types.append("financial")
            break
    
    for kw in corporate_keywords:
        if kw in query_lower:
            types.append("corporate")
            break
    
    for kw in compliance_keywords:
        if kw in query_lower:
            types.append("compliance")
            break
    
    for kw in drafting_keywords:
        if kw in query_lower:
            types.append("drafting")
            break
    
    if not types:
        types = ["legal"]
    
    return list(set(types))


def is_complex(query_types: list) -> bool:
    """Determine if query needs Opus (complex) or Sonnet (simple)."""
    if len(query_types) >= 2:
        return True
    if "compliance" in query_types or "corporate" in query_types:
        return True
    return False


def extract_company_name(query: str) -> str:
    """Try to extract company name from query."""
    patterns = [
        r'(?:company|firm|ltd|limited|pvt|private)\s*[:\-]?\s*([A-Z][\w\s&]+)',
        r'([A-Z][\w\s&]+(?:Ltd|Limited|Pvt|Private|Inc|Corp))',
    ]
    for p in patterns:
        m = re.search(p, query, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


async def process_query(user_query: str, mode: str, matter_context: str = "",
                        conversation_history: list = None, statute_context: str = "") -> dict:
    """Main query processing pipeline."""
    
    query_types = classify_query(user_query)
    
    # Parallel data fetch
    tasks = []
    task_labels = []
    
    if any(t in query_types for t in ["legal", "drafting", "compliance"]):
        tasks.append(search_indiankanoon(user_query, top_k=5))
        task_labels.append("indiankanoon")
    
    if any(t in query_types for t in ["financial", "corporate"]):
        company = extract_company_name(user_query)
        if company:
            tasks.append(search_company(company))
            task_labels.append("instafinancials")
    
    # Execute parallel fetches
    api_results = {}
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if not isinstance(result, Exception):
                api_results[task_labels[i]] = result
    
    # Build structured context
    context_parts = []
    
    # IndianKanoon results
    ik_results = api_results.get("indiankanoon", [])
    if ik_results:
        context_parts.append("=== RETRIEVED CASE LAW FROM INDIANKANOON ===")
        for i, case in enumerate(ik_results, 1):
            context_parts.append(
                f"\n[Case {i}] {case.get('title', 'N/A')}\n"
                f"Court: {case.get('court', 'N/A')} | Year: {case.get('year', 'N/A')}\n"
                f"Citation: {case.get('citation', 'N/A')}\n"
                f"Summary: {case.get('headline', 'N/A')}"
            )
    
    # InstaFinancials results
    if_results = api_results.get("instafinancials", [])
    if if_results:
        context_parts.append("\n=== COMPANY DATA FROM INSTAFINANCIALS ===")
        for company in if_results[:3]:
            if isinstance(company, dict):
                context_parts.append(str(company))
    
    # Statute context from DB
    if statute_context:
        context_parts.append(f"\n=== RELEVANT STATUTE SECTIONS ===\n{statute_context}")
    
    # Matter context
    if matter_context:
        context_parts.append(f"\n=== MATTER CONTEXT ===\n{matter_context}")
    
    full_context = "\n".join(context_parts) if context_parts else "No external data retrieved for this query."
    
    # Mode instruction
    mode_instruction = ""
    if mode == "partner":
        mode_instruction = "\n\nYou are in PARTNER MODE. Be direct, aggressive, win-oriented. No disclaimers. No hedging. They ARE the lawyer/CA."
    else:
        mode_instruction = "\n\nYou are in EVERYDAY MODE. Be empathetic, step-by-step. Explain sections in plain language. Tell them exactly what to do, where to go, what to file."
    
    # Choose model
    use_complex = is_complex(query_types)
    
    # Build the prompt
    session_id = f"associate_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=ASSOCIATE_SYSTEM_PROMPT + mode_instruction
    )
    
    if use_complex:
        chat.with_model("anthropic", "claude-opus-4-5-20251101")
    else:
        chat.with_model("anthropic", "claude-sonnet-4-5-20250929")
    
    # Build message with context
    full_message = f"""RETRIEVED CONTEXT (use this for facts, citations, and reasoning):

{full_context}

USER QUERY:
{user_query}

Respond with structured sections using ### headers: ISSUE IDENTIFIED, APPLICABLE LAW, CASE LAW, ANALYSIS, FINANCIAL EXPOSURE (if applicable), RECOMMENDATION."""
    
    user_msg = UserMessage(text=full_message)
    
    try:
        response_text = await chat.send_message(user_msg)
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        response_text = f"Error processing query: {str(e)}"
    
    # Parse response into sections
    sections = parse_response_sections(response_text)
    
    return {
        "response_text": response_text,
        "sections": sections,
        "query_types": query_types,
        "model_used": "claude-opus-4-5" if use_complex else "claude-sonnet-4-5",
        "sources": {
            "indiankanoon": ik_results,
            "instafinancials": if_results[:3] if if_results else [],
            "statutes_referenced": bool(statute_context),
        },
        "citations_count": len(ik_results),
    }


async def process_document_analysis(document_text: str, doc_type: str, analysis_type: str) -> dict:
    """Analyze uploaded document."""
    session_id = f"vault_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=ASSOCIATE_SYSTEM_PROMPT
    )
    chat.with_model("anthropic", "claude-opus-4-5-20251101")
    
    analysis_prompts = {
        "anomaly": "Scan this document for anomalies, missed claims, incorrect calculations, tax risks, and compliance gaps. Flag EVERYTHING.",
        "contract_risk": "Analyze this contract for risks: missing clauses, one-sided provisions, unusual penalties, jurisdiction issues, limitation problems.",
        "timeline": "Extract ALL dates from this document. Calculate limitation periods and flag deadlines. Mark anything under 7 days as URGENT.",
        "obligations": "List every party's obligations from this document in a structured table.",
        "response": "This is a notice/order. Draft a complete, court-ready response to it with proper section citations and legal grounds.",
        "general": "Provide a comprehensive analysis of this document covering: classification, key provisions, risks, obligations, deadlines, and recommendations.",
    }
    
    prompt = analysis_prompts.get(analysis_type, analysis_prompts["general"])
    
    full_message = f"""DOCUMENT TYPE: {doc_type}
ANALYSIS REQUESTED: {analysis_type}

{prompt}

DOCUMENT CONTENT:
{document_text[:15000]}

Respond with structured sections using ### headers."""
    
    user_msg = UserMessage(text=full_message)
    
    try:
        response_text = await chat.send_message(user_msg)
    except Exception as e:
        logger.error(f"Document analysis error: {e}")
        response_text = f"Error analyzing document: {str(e)}"
    
    return {
        "response_text": response_text,
        "sections": parse_response_sections(response_text),
        "analysis_type": analysis_type,
        "doc_type": doc_type,
    }


async def generate_workflow_document(workflow_type: str, fields: dict, mode: str = "partner") -> dict:
    """Generate document from workflow fields."""
    session_id = f"workflow_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    
    # Fetch relevant case law
    search_query = f"{workflow_type} Indian law"
    ik_results = await search_indiankanoon(search_query, top_k=3)
    
    ik_context = ""
    if ik_results:
        ik_context = "RELEVANT CASE LAW:\n"
        for case in ik_results:
            ik_context += f"- {case.get('title', '')} | {case.get('court', '')} | {case.get('year', '')}\n  {case.get('headline', '')}\n"
    
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=ASSOCIATE_SYSTEM_PROMPT
    )
    chat.with_model("anthropic", "claude-opus-4-5-20251101")
    
    mode_text = "PARTNER MODE - Direct, aggressive, win-oriented." if mode == "partner" else "EVERYDAY MODE - Plain language, empathetic."
    
    fields_text = "\n".join([f"  {k}: {v}" for k, v in fields.items()])
    
    full_message = f"""WORKFLOW: {workflow_type}
MODE: {mode_text}

INPUT FIELDS:
{fields_text}

{ik_context}

Generate a COMPLETE, FILING-READY document for this workflow. Not a template. Not a summary.
The full document with every paragraph, every whereas clause, every prayer.
Include proper Indian legal formatting, cause title, paragraph numbering, and signature blocks.
Cite exact sections and relevant case law inline."""
    
    user_msg = UserMessage(text=full_message)
    
    try:
        response_text = await chat.send_message(user_msg)
    except Exception as e:
        logger.error(f"Workflow generation error: {e}")
        response_text = f"Error generating document: {str(e)}"
    
    return {
        "response_text": response_text,
        "workflow_type": workflow_type,
        "sources": ik_results,
    }


def parse_response_sections(text: str) -> list:
    """Parse AI response into structured sections."""
    sections = []
    current_section = None
    current_content = []
    
    for line in text.split("\n"):
        header_match = re.match(r'^###\s*(.+)', line.strip())
        if header_match:
            if current_section:
                sections.append({
                    "title": current_section,
                    "content": "\n".join(current_content).strip()
                })
            current_section = header_match.group(1).strip()
            current_content = []
        else:
            current_content.append(line)
    
    if current_section:
        sections.append({
            "title": current_section,
            "content": "\n".join(current_content).strip()
        })
    
    if not sections and text.strip():
        sections.append({
            "title": "RESPONSE",
            "content": text.strip()
        })
    
    return sections
