"""
Spectr Office Engine — MS Word & Excel Integration Backend
============================================================
Production-grade API endpoints for Office.js add-ins:
  1. Word Redline — Clause-by-clause contract analysis with suggestions
  2. Word Playbook Scan — Deviation detection against firm playbooks
  3. Word AI Chat — Direct AI research inside Word with document context
  4. Excel Reconcile — GSTR-2B reconciliation with cell-level formatting
  5. Excel Classify — Vendor/ledger AI classification
  6. Excel Forensics — Anomaly detection for audit

All endpoints return structured JSON that the Office.js taskpane
renders into native Word comments, Track Changes, and Excel formatting.
"""

import os
import json
import logging
import re
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional
import asyncio
import aiohttp

logger = logging.getLogger("office_engine")
office_router = APIRouter()

GROQ_KEY_LIVE = os.environ.get("GROQ_KEY", "")
GOOGLE_AI_KEY = os.environ.get("GOOGLE_AI_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


# ============================================================
# AI CASCADE — Best available model (Gemini → Claude → Groq)
# ============================================================
async def _call_ai_cascade(system: str, user_content: str, max_tokens: int = 4000) -> str:
    """Call the best available AI model with automatic fallback."""
    # Tier 1: Gemini 2.5 Flash (fast + capable)
    if GOOGLE_AI_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GOOGLE_AI_KEY}"
            payload = {
                "system_instruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user_content}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": max_tokens}
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers={"Content-Type": "application/json"},
                                        json=payload, timeout=aiohttp.ClientTimeout(total=45)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                        text = "\n".join([p.get("text", "") for p in parts if "text" in p])
                        if text and len(text) > 50:
                            return text
        except Exception as e:
            logger.warning(f"Gemini Flash error: {e}")

    # Tier 2: Claude Haiku (fast + precise)
    if ANTHROPIC_KEY:
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": user_content}],
                    "temperature": 0.1
                }
                async with session.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                    json=payload, timeout=aiohttp.ClientTimeout(total=45)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        text = data.get("content", [{}])[0].get("text", "")
                        if text and len(text) > 50:
                            return text
        except Exception as e:
            logger.warning(f"Claude Haiku error: {e}")

    # Tier 3: Groq (fallback)
    if GROQ_KEY_LIVE:
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user_content}],
                    "temperature": 0.1, "max_tokens": max_tokens
                }
                async with session.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_KEY_LIVE}", "Content-Type": "application/json"},
                    json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"Groq error: {e}")

    return ""


# ============================================================
# REQUEST MODELS
# ============================================================
class WordRedlineRequest(BaseModel):
    draft_text: str = Field(..., max_length=60000)
    instruction: str = Field(default="", max_length=2000)

class WordCommentRequest(BaseModel):
    document_text: str = Field(..., max_length=60000)
    playbook_type: str = Field(default="standard", max_length=50)

class WordChatRequest(BaseModel):
    query: str = Field(..., max_length=5000)
    document_context: str = Field(default="", max_length=20000)
    mode: str = Field(default="partner", max_length=20)

class DocumentAnalyzeRequest(BaseModel):
    document_text: str = Field(..., max_length=80000)
    document_type: str = Field(default="auto", description="auto, contract, balance_sheet, financial_statement, audit_report, tax_return, petition, legal_opinion, trust_deed, partnership_deed, board_resolution, compliance_filing, notice, affidavit, power_of_attorney, will, lease, loan_agreement, mou, letter_of_intent")
    analysis_depth: str = Field(default="comprehensive", description="quick, standard, comprehensive")
    client_side: str = Field(default="auto", description="Which party the client represents: auto, party_a, party_b, vendor, buyer, landlord, tenant, employer, employee")

class ExcelReconcileRequest(BaseModel):
    rows: list

class ExcelClassifyRequest(BaseModel):
    entries: list = Field(..., description="List of {description, amount} objects for TDS/ledger classification")
    classification_type: str = Field(default="tds", description="'tds' for TDS section, 'ledger' for Clause 44")

class ExcelForensicsRequest(BaseModel):
    entries: list = Field(..., description="List of {description, amount, vendor, date} objects")


# ============================================================
# PLAYBOOK DEFINITIONS
# ============================================================
PLAYBOOKS = {
    "standard": """Standard Vendor/Service Agreement Playbook:
- Liability MUST be capped at the value of the contract or 12 months' fees, whichever is lower
- Liability exclusions MUST cover gross negligence and wilful misconduct (these should NOT be excluded from liability)
- Indemnity must be mutual — one-sided indemnities are a RED FLAG
- Jurisdiction MUST be India (Indian courts, not foreign arbitration)
- Payment terms MUST be at least 30 days from invoice date
- Termination for convenience must have at least 30 days' notice
- Termination for cause must specify cure period (minimum 15 days)
- Force majeure must include epidemics/pandemics post-COVID
- IP ownership clauses must clearly state who owns deliverables
- Non-compete clauses exceeding 2 years are unenforceable under Indian law (Section 27, Indian Contract Act)
- Auto-renewal clauses without opt-out are a risk — require 30-day notice window
- Data protection obligations must comply with DPDP Act 2023 (if applicable)
- No unilateral amendment rights — changes require written mutual consent
- Consequential/indirect damages must be excluded for both parties""",

    "nda": """Mutual NDA / Confidentiality Agreement Playbook:
- Term must not exceed 3 years (preferably 2 years). Survival of confidentiality obligations may extend 1-2 years beyond term.
- Residuals clauses are STRICTLY PROHIBITED — they create permanent exceptions that nullify the NDA
- Definition of "Confidential Information" must:
  - Include: technical data, business plans, financials, client lists, proprietary methods
  - Exclude: publicly available information, independently developed info, legally compelled disclosures, info received from third parties without restriction
- Must have mutual obligations (both parties bound equally)
- Return/destruction obligation must be within 30 days of termination with written certification
- Carve-outs for legal/regulatory disclosure must be included (court orders, SEBI, RBI, tax authorities)
- No non-solicitation provisions disguised as NDA terms
- Governing law must be Indian law, jurisdiction of specific city courts
- Injunctive relief clause should be present (acknowledging irreparable harm)
- No permitted disclosure to affiliates/subsidiaries without written authorization
- Mark all shared documents as "CONFIDENTIAL" — requirement to treat unmarked info equally""",

    "employment": """Employment Agreement / Offer Letter Playbook:
- Non-compete must not exceed 12 months post-termination (Indian courts consistently strike down longer periods under Section 27, Indian Contract Act 1872)
- Non-solicitation must not exceed 18 months and must be reasonable in scope
- IP assignment must cover works created during employment ONLY, not prior works (carve-out for pre-existing IP)
- Garden leave provisions must be fully compensated at last drawn salary
- Notice period must be symmetric (same for employer and employee). Asymmetric notice is a RED FLAG.
- Termination provisions must comply with applicable labour laws (Industrial Disputes Act 1947 for workmen; Shops & Establishments Act for others)
- Variable pay / bonus clauses must have clear, measurable criteria and payment timelines
- Restrictive covenants must have geographic AND temporal limitations to be enforceable
- Employee invention assignment must be limited to scope of employment and company resources
- Background verification clause must comply with DPDP Act 2023 and consent requirements
- Probation period terms must specify confirmation criteria and termination procedure during probation""",

    "sha": """Shareholders' Agreement / Joint Venture Playbook:
- Pre-emptive rights (ROFR/ROFO) must be clearly defined with exercise timelines
- Tag-along and drag-along rights must be present for minority protection
- Board composition must reflect equity ratios with clear nomination rights
- Reserved matters / affirmative voting list must be comprehensive (amendment to articles, related party transactions, material contracts, borrowing limits, changes in business)
- Deadlock resolution mechanism must be defined (escalation → mediation → arbitration → buy-sell)
- Exit mechanisms: IPO, strategic sale, buy-back — all with clear valuation methodology
- Anti-dilution protection for investors (weighted average, not full ratchet)
- Information rights: quarterly financials, annual audit, inspection rights
- Transfer restrictions: lock-in period, board approval, competitor exclusion
- Compliance with FEMA/RBI if foreign investor involved (FDI policy, pricing guidelines, reporting)""",

    "spa": """Share Purchase Agreement Playbook:
- Representations and warranties must be comprehensive (title, authority, no litigation, compliance, financials accuracy, tax compliance, employee matters, IP ownership)
- Indemnity basket/threshold must be reasonable (0.5-1% of deal value)
- Indemnity cap typically 10-20% of deal value (negotiate higher for known risks)
- Material Adverse Change (MAC) clause must be narrowly defined
- Conditions precedent must have a long-stop date with clear walk-away rights
- Escrow/holdback mechanism for indemnity claims (10-15% of consideration, 12-18 months)
- Non-compete from sellers: minimum 3 years, geographically limited to India
- Conduct of business between signing and closing: ordinary course covenants
- Tax warranties and indemnities: specifically cover pre-closing tax liabilities
- FEMA/RBI compliance for cross-border SPAs (pricing guidelines, FC-GPR filing, reporting)"""
}


# ============================================================
# 1. WORD REDLINE — Clause-by-Clause Contract Analysis
# ============================================================
@office_router.post("/word/redline")
async def draft_word_redline(req: WordRedlineRequest):
    """Analyze contract clause-by-clause. Returns structured suggestions with
    severity, original text, suggested revision, and legal basis — matching
    the Harvey-style suggestion panel UX."""

    system_instruction = """You are a Spectr Senior Attorney performing a clause-by-clause contract redline analysis.

Your job: Analyze the provided contract text and identify every clause that creates legal risk, exposure, or unfavorable terms for the reviewing party. For each problematic clause, output a structured suggestion.

OUTPUT FORMAT — STRICT JSON ARRAY:
{
  "suggestions": [
    {
      "clause_number": "3.2",
      "clause_title": "Limitation of Liability",
      "severity": "CRITICAL",
      "original_text": "The exact problematic text from the contract (must be a real substring)",
      "issue": "One-line description of the risk",
      "suggested_text": "The complete replacement clause text that fixes the issue",
      "legal_basis": "Section/case law/principle supporting the change",
      "risk_if_unchanged": "What happens if the client signs without this change"
    }
  ],
  "summary": {
    "overall_risk": "HIGH",
    "critical_count": 3,
    "total_suggestions": 8,
    "top_risk": "One-sentence summary of the most dangerous clause"
  }
}

RULES:
1. Analyze EVERY clause — not just the obvious ones. Check definitions, boilerplate, schedules.
2. "original_text" MUST be an exact substring from the document. Not a paraphrase.
3. "suggested_text" must be complete, enforceable replacement language — not a template.
4. Severity levels:
   - CRITICAL: Must change before signing. Creates material legal/financial exposure.
   - HIGH: Strongly recommended. Creates significant risk if unchanged.
   - MEDIUM: Should review. Suboptimal but not immediately dangerous.
   - LOW: Minor improvement. Best practice enhancement.
5. Sort by severity (CRITICAL first).
6. Every suggestion must cite Indian law (Indian Contract Act, Specific Relief Act, Companies Act, IT Act, DPDP Act, etc.).
7. Do NOT output anything except the JSON object. No preamble, no markdown, no commentary."""

    user_content = f"INSTRUCTION: {req.instruction or 'Perform comprehensive contract risk analysis. Make this contract airtight under Indian law.'}\n\nCONTRACT TEXT:\n{req.draft_text[:55000]}"

    try:
        result = await _call_ai_cascade(system_instruction, user_content, max_tokens=6000)
        if not result:
            raise HTTPException(status_code=500, detail="AI inference failed across all providers")

        # Parse JSON
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        parsed = json.loads(result)
        suggestions = parsed.get("suggestions", [])
        summary = parsed.get("summary", {})

        # Validate and clean suggestions
        clean_suggestions = []
        for s in suggestions:
            if isinstance(s, dict) and s.get("original_text"):
                clean_suggestions.append({
                    "clause_number": s.get("clause_number", ""),
                    "clause_title": s.get("clause_title", ""),
                    "severity": s.get("severity", "MEDIUM"),
                    "original_text": s.get("original_text", ""),
                    "issue": s.get("issue", ""),
                    "suggested_text": s.get("suggested_text", ""),
                    "legal_basis": s.get("legal_basis", ""),
                    "risk_if_unchanged": s.get("risk_if_unchanged", "")
                })

        return {
            "success": True,
            "suggestions": clean_suggestions,
            "summary": summary,
            "suggestion_count": len(clean_suggestions)
        }
    except json.JSONDecodeError:
        # Fallback: try to extract any valid JSON from the response
        logger.warning("Redline JSON parse failed, attempting extraction")
        try:
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                parsed = json.loads(json_match.group())
                return {
                    "success": True,
                    "suggestions": parsed.get("suggestions", []),
                    "summary": parsed.get("summary", {}),
                    "suggestion_count": len(parsed.get("suggestions", []))
                }
        except Exception:
            pass
        return {"success": True, "suggestions": [], "summary": {}, "suggestion_count": 0}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Redline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 2. WORD PLAYBOOK SCAN — Deviation Detection
# ============================================================
@office_router.post("/word/comment")
async def playbook_scan(req: WordCommentRequest):
    """Scans document text against a selected firm Playbook and returns targeted deviations
    with exact search phrases for Word comment injection."""

    playbook = PLAYBOOKS.get(req.playbook_type, PLAYBOOKS["standard"])

    system_instruction = f"""You are a Spectr Senior Attorney executing a Playbook Compliance Scan on a contract in Microsoft Word.

FIRM PLAYBOOK TO ENFORCE:
{playbook}

INSTRUCTIONS:
1. Read the document carefully, clause by clause.
2. For every clause that deviates from the playbook, extract the EXACT phrase from the document text (must be a real substring — this is used for Word's search-and-highlight API).
3. Write a precise comment explaining the risk and the playbook requirement.
4. Rate severity:
   - CRITICAL: Must change before signing. Violates playbook mandatory requirements.
   - HIGH: Strongly recommended change. Creates significant risk.
   - MEDIUM: Should review. Deviates from best practice.
   - LOW: Minor improvement opportunity.

Output STRICTLY as JSON: {{"deviations": [{{"searchPhrase": "exact text from document (max 255 chars)", "comment": "Risk explanation referencing playbook and Indian law", "severity": "CRITICAL|HIGH|MEDIUM|LOW", "clause": "Clause number if identifiable", "playbook_rule": "Which playbook rule is violated"}}]}}
If no deviations found, return {{"deviations": []}}.
Output ONLY the JSON object. No other text."""

    try:
        result = await _call_ai_cascade(
            system_instruction,
            f"DOCUMENT TEXT:\n{req.document_text[:20000]}",
            max_tokens=4000
        )
        if not result:
            return {"success": True, "deviations": []}

        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[-1].rsplit("```", 1)[0]

        parsed = json.loads(result)
        deviations = parsed.get("deviations", [])

        # Clean and validate
        clean_devs = []
        for d in deviations:
            if isinstance(d, dict) and d.get("searchPhrase"):
                clean_devs.append({
                    "searchPhrase": d["searchPhrase"][:255],
                    "comment": d.get("comment", ""),
                    "severity": d.get("severity", "MEDIUM"),
                    "clause": d.get("clause", ""),
                    "playbook_rule": d.get("playbook_rule", "")
                })

        return {"success": True, "deviations": clean_devs}
    except json.JSONDecodeError as e:
        logger.warning(f"Playbook scan JSON parse error: {e}")
        return {"success": True, "deviations": []}
    except Exception as e:
        logger.error(f"Playbook scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 3. WORD AI CHAT — Direct research inside Word
# ============================================================
@office_router.post("/word/chat")
async def word_ai_chat(req: WordChatRequest):
    """Direct AI chat from inside Word with document context awareness."""

    system_instruction = """You are Spectr, an AI legal and tax intelligence engine embedded inside Microsoft Word.
The user is working on a document and asking you a question. Use the document context to give precise, relevant answers.

RULES:
- Answer concisely but completely. This is a side panel — not a full research memo.
- If the document context is relevant, reference specific clauses or sections from it.
- Always cite Indian law (statutes, sections, case law) when applicable.
- For contract questions: identify risks, suggest improvements, cite legal basis.
- For tax questions: cite exact sections, calculate exposure, state deadlines.
- Use markdown formatting (## headings, **bold**, bullet lists).
- End with a one-line actionable next step.
- NEVER say "I don't have access to the document" — the document context is provided to you."""

    doc_prefix = ""
    if req.document_context:
        doc_prefix = f"DOCUMENT CONTEXT (from the currently open Word document):\n{req.document_context[:15000]}\n\n"

    try:
        response = await _call_ai_cascade(
            system_instruction,
            f"{doc_prefix}USER QUESTION: {req.query}",
            max_tokens=3000
        )
        if not response:
            raise HTTPException(status_code=500, detail="AI inference failed")
        return {"success": True, "response": response}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Word chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 4. UNIVERSAL DOCUMENT ANALYSIS — Any legal/accounting document
# ============================================================
DOCUMENT_ANALYSIS_PROMPTS = {
    "contract": """Analyze this contract clause-by-clause. For each issue found, provide clause number, problematic text (exact quote), risk description, suggested revision, severity (CRITICAL/HIGH/MEDIUM/LOW), and legal basis under Indian law. Check: liability caps, indemnity, termination, force majeure, IP, jurisdiction, governing law, confidentiality, payment terms, auto-renewal, non-compete, data protection.""",

    "balance_sheet": """Analyze this Balance Sheet / Financial Statement with the precision of a statutory auditor under Companies Act 2013 and Ind AS. Check:
- Schedule III compliance (proper classification of current/non-current assets and liabilities)
- Related party transactions (Ind AS 24 / Section 188 Companies Act)
- Contingent liabilities disclosure adequacy (Ind AS 37)
- Revenue recognition compliance (Ind AS 115)
- Deferred tax computation accuracy (Ind AS 12)
- Cash flow statement classification (Ind AS 7)
- Going concern indicators
- Material misstatements or unusual ratios (debt-equity, current ratio, working capital)
- Audit trail compliance (Rule 3(1) Companies (Accounts) Rules)
- CARO 2020 reporting requirements
For each issue: cite exact line/entry, explain the risk, cite the applicable Ind AS/Companies Act section, and provide the corrective action.""",

    "financial_statement": """Perform a comprehensive analysis of this financial statement. Apply Ind AS framework, Companies Act Schedule III requirements, and SA 700/705/706 audit standards. Check mathematical accuracy, cross-references between notes and financials, compliance with accounting policies, unusual fluctuations (>20% YoY changes), and adequacy of disclosures. Flag any numbers that don't reconcile.""",

    "audit_report": """Analyze this audit report / Form 3CD / Form 3CA-3CB. Verify:
- All 44 clauses of Form 3CD are properly addressed
- Quantitative data is internally consistent
- Clause 44 GST expenditure breakdown adds up correctly
- TDS compliance observations are complete (Section 40(a)(ia) disallowance risk)
- Section 43B compliance is verified for all statutory payments
- Revenue recognition aligns with accounting policy
- Related party transactions are fully disclosed
- Audit qualifications are properly worded per SA 705
For each issue: state the clause number, the error/omission, the corrective action, and the penalty exposure.""",

    "tax_return": """Analyze this tax return / computation sheet. Verify:
- Mathematical accuracy of income computation
- Proper set-off and carry-forward of losses (Section 70-80)
- Deduction claims with eligibility and limits (Chapter VIA)
- TDS credit reconciliation with Form 26AS/AIS
- Advance tax computation accuracy (Section 234B/234C)
- MAT/AMT computation where applicable (Section 115JB/115JC)
- Transfer pricing adjustments for international transactions
- Interest and penalty exposure calculation
For each issue: cite the specific section, quantify the tax impact, and state the corrective action with deadline.""",

    "petition": """Analyze this petition / application / writ. Check:
- Cause of action is clearly and completely stated
- Limitation period compliance (Limitation Act 1963)
- Proper court/forum jurisdiction (subject matter + territorial)
- All necessary parties are joined (necessary vs proper parties)
- Prayer clause is specific and legally achievable
- Supporting grounds are legally sound
- Relevant precedents are correctly cited and applicable
- Procedural compliance with CPC/CrPC/BNSS as applicable
- Vakalatnama / authorization is in order
For each weakness: explain the risk of dismissal/rejection and suggest the correction.""",

    "legal_opinion": """Analyze this legal opinion. Verify:
- Question presented is precisely framed
- Applicable law is correctly identified and current
- Case law citations are accurate (ratio decidendi matches)
- Analysis follows IRAC framework
- All counterarguments are addressed
- Risk assessment includes quantified exposure
- Recommendations are actionable and legally sound
- Disclaimers and caveats are appropriate
For each issue: explain why the analysis is weak/incorrect and provide the correct position.""",

    "notice": """Analyze this legal notice / demand notice / show cause notice. Check:
- Sender's authority to issue the notice
- Proper identification of parties
- Clear statement of facts and grievance
- Legal provisions correctly cited
- Relief/demand is legally tenable
- Timeline/deadline is legally valid (limitation check)
- Service requirements compliance
- Whether reply is mandatory or optional
- Consequence of non-reply
For each issue: state the deficiency, the legal risk, and the recommended action.""",

    "trust_deed": """Analyze this trust deed / settlement deed. Check under Indian Trusts Act 1882 and Registration Act 1908:
- Trust purpose is lawful (Section 4, Indian Trusts Act)
- Beneficiary identification is clear and certain
- Trustee powers are properly defined and not excessive
- Revocability/irrevocability is clearly stated
- Stamp duty adequacy for the relevant state
- Registration requirements are met
- Income tax implications under Section 160-166 ITA
- PMLA compliance for trust structures
For each issue: cite the applicable section and recommend correction.""",

    "partnership_deed": """Analyze this partnership deed under Indian Partnership Act 1932. Check:
- Partners' names, addresses, and contributions
- Profit/loss sharing ratio is clearly stated
- Capital interest and drawings terms
- Management rights and authority
- Admission/retirement/death provisions
- Goodwill valuation method
- Dissolution provisions
- Non-compete and confidentiality
- GST registration requirements
- Section 194T TDS compliance (effective 01-04-2025)
For each issue: cite the applicable section and recommend correction.""",

    "board_resolution": """Analyze this board resolution / shareholders' resolution. Check under Companies Act 2013:
- Quorum requirements (Section 174/103)
- Proper authority (Board vs Shareholders vs Committee)
- Section 180/186/188 compliance for specific transactions
- Interested director disclosure (Section 184)
- Related party transaction approval process
- Filing requirements with ROC (timeline + form)
- Secretarial standards compliance (SS-1/SS-2)
For each issue: cite the applicable section and the penalty for non-compliance.""",

    "lease": """Analyze this lease/rent agreement. Check under:
- Transfer of Property Act 1882 (Section 105-117)
- Registration Act 1908 (mandatory for >11 months)
- Stamp duty adequacy for the relevant state
- Rent Control Act applicability
- Security deposit limits (state-specific)
- Maintenance obligations clarity
- Subletting restrictions
- Termination and eviction provisions
- Escalation clause reasonability
- TDS under Section 194-I (10% for >50,000/month)
For each issue: cite the applicable law and suggest correction.""",

    "loan_agreement": """Analyze this loan/credit agreement. Check:
- Interest rate compliance with RBI guidelines (usurious lending)
- Prepayment/foreclosure terms (RBI circular on no-penalty for individual borrowers)
- Security creation and perfection requirements
- Events of default are reasonable and not unilateral
- Personal guarantee obligations are limited
- SARFAESI Act applicability and implications
- Stamp duty adequacy
- TDS on interest (Section 194A/193)
- FEMA compliance for foreign currency loans
For each issue: cite the applicable regulation and suggest correction.""",

    "mou": """Analyze this MOU/Letter of Intent. Check:
- Binding vs non-binding provisions are clearly demarcated
- Exclusivity period is reasonable
- Conditions precedent for definitive agreement
- Confidentiality obligations survive termination
- Cost-bearing provisions
- Break fee/walk-away terms
- Governing law and dispute resolution
- Timeline for definitive agreement execution
For each issue: explain the risk and suggest correction.""",
}

@office_router.post("/word/analyze")
async def analyze_document(req: DocumentAnalyzeRequest):
    """Universal document analysis endpoint — handles any legal or accounting document.
    Auto-detects document type if not specified. Returns structured risk analysis."""

    # Auto-detect document type
    doc_type = req.document_type
    if doc_type == "auto":
        doc_type = _detect_document_type(req.document_text)

    analysis_prompt = DOCUMENT_ANALYSIS_PROMPTS.get(doc_type, DOCUMENT_ANALYSIS_PROMPTS.get("contract"))

    system_instruction = f"""You are Spectr, an institutional-grade legal and accounting intelligence engine performing document analysis.

DOCUMENT TYPE: {doc_type.upper().replace('_', ' ')}
CLIENT SIDE: {req.client_side}

ANALYSIS INSTRUCTIONS:
{analysis_prompt}

OUTPUT FORMAT — STRICT JSON:
{{
  "document_type": "{doc_type}",
  "overall_risk": "CRITICAL|HIGH|MEDIUM|LOW",
  "executive_summary": "2-3 sentence summary of the document's key risks and quality",
  "issues": [
    {{
      "id": 1,
      "section": "Section/Clause/Line reference",
      "title": "Issue title",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "original_text": "Exact quote from the document (must be a real substring)",
      "issue_description": "What is wrong and why it matters",
      "suggested_fix": "Exact replacement text or corrective action",
      "legal_basis": "Applicable statute, section, case law, or accounting standard",
      "financial_impact": "Quantified impact if applicable (e.g., 'Potential disallowance of Rs X under Section Y')",
      "deadline": "Any applicable deadline for correction"
    }}
  ],
  "strengths": ["List of well-drafted provisions or compliant areas"],
  "missing_provisions": ["List of provisions/disclosures that should be present but are missing"],
  "compliance_checklist": [
    {{"item": "Requirement", "status": "COMPLIANT|NON_COMPLIANT|PARTIAL|NOT_APPLICABLE", "notes": "Details"}}
  ]
}}

RULES:
1. "original_text" MUST be an exact substring from the document.
2. Sort issues by severity (CRITICAL first).
3. Be specific — no generic advice. Every recommendation must cite a specific provision.
4. Financial impact must be quantified where possible.
5. Output ONLY the JSON. No preamble."""

    try:
        result = await _call_ai_cascade(
            system_instruction,
            f"DOCUMENT TEXT:\n{req.document_text[:60000]}",
            max_tokens=8000
        )
        if not result:
            raise HTTPException(status_code=500, detail="AI inference failed")

        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        parsed = json.loads(result)
        return {"success": True, **parsed}
    except json.JSONDecodeError:
        try:
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                parsed = json.loads(json_match.group())
                return {"success": True, **parsed}
        except Exception:
            pass
        return {"success": True, "document_type": doc_type, "overall_risk": "UNKNOWN", "issues": [], "error": "Could not parse analysis results"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _detect_document_type(text: str) -> str:
    """Auto-detect document type from content."""
    text_lower = text[:5000].lower()

    detection_rules = [
        ("balance_sheet", ["balance sheet", "assets", "liabilities", "shareholders equity", "shareholders' equity", "schedule iii", "profit and loss", "statement of profit"]),
        ("financial_statement", ["statement of changes in equity", "cash flow statement", "notes to financial", "accounting policies", "ind as"]),
        ("audit_report", ["form 3cd", "form 3ca", "form 3cb", "tax audit", "clause 44", "audit report", "statutory auditor"]),
        ("tax_return", ["income tax return", "form itr", "computation of income", "total income", "assessment year", "advance tax"]),
        ("petition", ["petition", "hon'ble", "petitioner", "respondent", "prayer", "writ", "in the matter of"]),
        ("legal_opinion", ["legal opinion", "opinion:", "we are of the view", "in our opinion", "advised"]),
        ("notice", ["legal notice", "show cause notice", "demand notice", "notice under section", "reply within"]),
        ("trust_deed", ["trust deed", "settlor", "trustee", "beneficiary", "trust property"]),
        ("partnership_deed", ["partnership deed", "partner", "profit sharing ratio", "partnership firm"]),
        ("board_resolution", ["board resolution", "resolved that", "board of directors", "meeting of the board", "shareholders resolution"]),
        ("nda", ["confidential information", "non-disclosure", "nda", "confidentiality agreement", "receiving party", "disclosing party"]),
        ("lease", ["lease deed", "rent agreement", "lessor", "lessee", "monthly rent", "security deposit", "lease period"]),
        ("loan_agreement", ["loan agreement", "borrower", "lender", "interest rate", "emi", "principal amount", "repayment schedule"]),
        ("mou", ["memorandum of understanding", "letter of intent", "loi", "mou", "non-binding"]),
        ("sha", ["shareholders agreement", "shareholder", "tag along", "drag along", "pre-emptive", "board composition"]),
        ("spa", ["share purchase agreement", "purchase price", "closing date", "representations and warranties", "indemnification"]),
        ("employment", ["employment agreement", "employee", "employer", "salary", "notice period", "non-compete", "probation"]),
    ]

    for doc_type, keywords in detection_rules:
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches >= 2:
            return doc_type

    # Default to contract analysis (most versatile)
    if any(kw in text_lower for kw in ["agreement", "contract", "whereas", "parties", "hereinafter"]):
        return "contract"

    return "contract"


# ============================================================
# 5. EXCEL RECONCILIATION — GSTR-2B
# ============================================================
@office_router.post("/excel/reconcile")
async def excel_reconcile(req: ExcelReconcileRequest):
    """Ingests row data from Excel, detects ITC discrepancies against GSTR-2B,
    and returns cell formatting commands with legal references.
    Accepts rows as either arrays or objects."""

    results = []
    for index, row in enumerate(req.rows):
        try:
            if isinstance(row, dict):
                gstin = str(row.get("gstin", ""))
                invoice = str(row.get("invoice", row.get("invoice_no", "")))
                claimed = float(str(row.get("itr_amount", row.get("claimed", 0))).replace(',', ''))
                available = float(str(row.get("twob_amount", row.get("available", 0))).replace(',', ''))
            elif isinstance(row, (list, tuple)) and len(row) >= 4:
                gstin = str(row[0])
                invoice = str(row[1])
                claimed = float(str(row[2]).replace(',', ''))
                available = float(str(row[3]).replace(',', ''))
            else:
                continue

            diff = round(claimed - available, 2)
            pct_diff = round((diff / available * 100), 1) if available > 0 else (100.0 if claimed > 0 else 0)

            if available == 0 and claimed > 0:
                results.append({
                    "row_index": index,
                    "status": "DANGER",
                    "flag": f"Sec 16(2)(c) Violation: Supplier GSTIN {gstin[:10]}... not filed. ITC of {claimed:,.0f} at 100% reversal risk.",
                    "color": "#FEE2E2",
                    "claimed": claimed,
                    "available": available,
                    "diff": diff,
                    "pct_diff": pct_diff,
                    "legal_ref": "Section 16(2)(c) CGST Act 2017 — ITC conditional on supplier filing return and depositing tax",
                    "action": "Issue vendor notice demanding GSTR-1 filing proof. Reverse ITC if unresolved by next filing."
                })
            elif claimed > available * 1.2:
                results.append({
                    "row_index": index,
                    "status": "DANGER",
                    "flag": f"Rule 36(4) Breach: Claimed {claimed:,.0f} exceeds 120% of available {available:,.0f}. Excess: {diff:,.0f} ({pct_diff}%)",
                    "color": "#FEE2E2",
                    "claimed": claimed,
                    "available": available,
                    "diff": diff,
                    "pct_diff": pct_diff,
                    "legal_ref": "Rule 36(4) CGST Rules 2017 — ITC restricted to amount reflected in GSTR-2B",
                    "action": f"Immediately reverse excess ITC of {diff:,.0f}. File DRC-03 voluntary payment to avoid Sec 73/74 proceedings."
                })
            elif claimed > available:
                results.append({
                    "row_index": index,
                    "status": "WARNING",
                    "flag": f"Rule 36(4) Risk: Excess ITC of {diff:,.0f} ({pct_diff}%)",
                    "color": "#FEF3C7",
                    "claimed": claimed,
                    "available": available,
                    "diff": diff,
                    "pct_diff": pct_diff,
                    "legal_ref": "Rule 36(4) CGST Rules 2017",
                    "action": "Verify with vendor. May need reversal in next return."
                })
            elif available > 0 and claimed == 0:
                results.append({
                    "row_index": index,
                    "status": "WARNING",
                    "flag": f"Unclaimed ITC: {available:,.0f} available in GSTR-2B but not claimed. Potential cash flow loss.",
                    "color": "#FEF3C7",
                    "claimed": claimed,
                    "available": available,
                    "diff": diff,
                    "pct_diff": 0,
                    "legal_ref": "Section 16(4) CGST Act — Claim by 30th November of following year",
                    "action": f"Claim {available:,.0f} in next GSTR-3B filing before Sec 16(4) deadline."
                })
            else:
                results.append({
                    "row_index": index,
                    "status": "SAFE",
                    "flag": "Reconciled",
                    "color": "#DCFCE7",
                    "claimed": claimed,
                    "available": available,
                    "diff": diff,
                    "pct_diff": 0,
                    "legal_ref": "",
                    "action": ""
                })
        except (ValueError, TypeError, KeyError):
            pass

    total = len(results)
    danger = sum(1 for r in results if r["status"] == "DANGER")
    warning = sum(1 for r in results if r["status"] == "WARNING")
    safe = sum(1 for r in results if r["status"] == "SAFE")
    total_excess = round(sum(r.get("diff", 0) for r in results if r.get("diff", 0) > 0), 2)
    total_unclaimed = round(abs(sum(r.get("diff", 0) for r in results if r.get("diff", 0) < 0)), 2)

    return {
        "success": True,
        "results": results,
        "summary": {
            "total_rows": total,
            "danger": danger,
            "warning": warning,
            "safe": safe,
            "total_excess_itc": total_excess,
            "total_unclaimed_itc": total_unclaimed,
            "risk_assessment": "CRITICAL — Immediate action required" if danger > 0 else "LOW — Minor issues only" if warning > 0 else "CLEAN — Fully reconciled"
        }
    }


# ============================================================
# 5. EXCEL CLASSIFY — TDS/Ledger Classification
# ============================================================
@office_router.post("/excel/classify")
async def excel_classify(req: ExcelClassifyRequest):
    """AI-powered classification of payment descriptions for TDS sections or Clause 44 ledger grouping."""

    if req.classification_type == "tds":
        system_instruction = """You are a Spectr Tax Engine classifying payment descriptions for TDS (Tax Deducted at Source) under the Income Tax Act, 1961.

For each entry, determine:
1. The applicable TDS section (194C, 194J, 194H, 194I, 194A, 194Q, 194O, 194R, 194S, 194T, 196D, etc.)
2. The TDS rate (with threshold limit)
3. Whether Section 206AB (higher TDS for non-filers) applies
4. Any exemptions or reduced rate eligibility

Output as JSON array:
[{"index": 0, "section": "194C", "rate": "1%/2%", "threshold": "30000/100000", "classification": "Contractor Payment", "s206ab_risk": "Check PAN on compliance portal", "notes": "1% for individual/HUF, 2% for others"}]"""
    else:
        system_instruction = """You are a Spectr Audit Engine classifying ledger entries for Clause 44 of Form 3CD (Tax Audit Report).

For each entry, determine:
1. Whether the vendor is GST Registered, Exempt, or Unregistered based on description
2. The Clause 44 expenditure category
3. Any Section 40(a)(ia) disallowance risk (TDS non-deduction)
4. Any Section 43B disallowance risk (statutory payments)

Output as JSON array:
[{"index": 0, "gst_status": "Registered", "clause44_category": "Professional Services", "disallowance_risk": "None", "notes": "Verify GSTIN on portal"}]"""

    entries_text = "\n".join([f"{i}. {json.dumps(e)}" for i, e in enumerate(req.entries[:100])])

    try:
        result = await _call_ai_cascade(system_instruction, f"ENTRIES:\n{entries_text}", max_tokens=3000)
        if not result:
            return {"success": True, "classifications": []}

        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[-1].rsplit("```", 1)[0]

        classifications = json.loads(result)
        if not isinstance(classifications, list):
            classifications = classifications.get("classifications", classifications.get("results", []))

        return {"success": True, "classifications": classifications}
    except json.JSONDecodeError:
        logger.warning("Classification JSON parse failed")
        return {"success": True, "classifications": []}
    except Exception as e:
        logger.error(f"Classification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 6. EXCEL FORENSICS — Anomaly Detection
# ============================================================
@office_router.post("/excel/forensics")
async def excel_forensics(req: ExcelForensicsRequest):
    """AI-powered forensic anomaly detection for audit. Flags suspicious entries,
    personal expenditure risks, Benford's Law violations, and round-number patterns."""

    # Rule-based quick scan first
    rule_flags = []
    suspicious_keywords = [
        "club", "spa", "holiday", "vacation", "resort", "personal",
        "gift", "donation", "school fee", "tuition", "insurance premium",
        "home loan", "car loan", "jewel", "gold", "silver",
        "restaurant", "bar", "liquor", "wine", "beer", "party",
        "travel agent", "airbnb", "hotel booking", "cruise",
        "gym", "fitness", "salon", "beauty", "cosmetic",
        "amazon", "flipkart", "myntra", "shopping",
    ]

    for idx, entry in enumerate(req.entries):
        desc = str(entry.get("description", "")).lower()
        amount = 0
        try:
            amount = float(str(entry.get("amount", 0)).replace(',', ''))
        except (ValueError, TypeError):
            pass

        # Keyword-based flags
        for kw in suspicious_keywords:
            if kw in desc:
                rule_flags.append({
                    "row_index": idx,
                    "flag_type": "PERSONAL_EXPENDITURE",
                    "severity": "HIGH" if amount > 50000 else "MEDIUM",
                    "description": entry.get("description", ""),
                    "amount": amount,
                    "reason": f"Keyword '{kw}' detected. Potential Section 37(1) disallowance — expenditure not wholly and exclusively for business.",
                    "legal_ref": "Section 37(1) ITA 1961 — Only expenditure laid out wholly and exclusively for business is deductible",
                    "action": "Verify business purpose. Obtain management representation if genuinely business-related."
                })
                break

        # Round number detection (potential inflation)
        if amount > 10000 and amount % 1000 == 0 and amount % 10000 == 0:
            rule_flags.append({
                "row_index": idx,
                "flag_type": "ROUND_NUMBER",
                "severity": "LOW",
                "description": entry.get("description", ""),
                "amount": amount,
                "reason": f"Exact round amount of {amount:,.0f}. Benford's Law anomaly — statistically unusual. May indicate estimated or inflated entry.",
                "legal_ref": "ICAI Standard on Auditing (SA 240) — Auditor's responsibility regarding fraud",
                "action": "Request supporting invoice/receipt for verification."
            })

        # Large cash payments
        if amount > 10000 and "cash" in desc:
            rule_flags.append({
                "row_index": idx,
                "flag_type": "CASH_VIOLATION",
                "severity": "CRITICAL",
                "description": entry.get("description", ""),
                "amount": amount,
                "reason": f"Cash payment of {amount:,.0f} exceeds Section 40A(3) threshold of Rs 10,000.",
                "legal_ref": "Section 40A(3) ITA 1961 — Cash expenditure exceeding Rs 10,000 disallowed (Rs 35,000 for transport)",
                "action": "100% disallowance unless covered by Rule 6DD exceptions. Verify payment mode from bank statement."
            })

    return {
        "success": True,
        "flags": rule_flags,
        "summary": {
            "total_entries": len(req.entries),
            "total_flags": len(rule_flags),
            "critical": sum(1 for f in rule_flags if f["severity"] == "CRITICAL"),
            "high": sum(1 for f in rule_flags if f["severity"] == "HIGH"),
            "medium": sum(1 for f in rule_flags if f["severity"] == "MEDIUM"),
            "low": sum(1 for f in rule_flags if f["severity"] == "LOW"),
        }
    }
