"""
Agentic Workflow Chain Engine — Spectr Grade
Multi-step workflows where the output of each step feeds into the next.
Now supports ALL 39+ frontend workflow templates dynamically.
Uses the full Spectr AI pipeline (Gemini → Claude → GPT-4o → Groq).
"""
import os
import json
import aiohttp
import logging
import uuid
import re
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

GROQ_KEY = os.environ.get("GROQ_KEY", "")
GOOGLE_AI_KEY = os.environ.get("GOOGLE_AI_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_KEY = os.environ.get("OPENAI_KEY", "")

# ============================================================
# CHAIN TEMPLATES — Named multi-step workflows
# These are pre-built chains with explicit step sequences.
# Any workflow NOT listed here falls through to the dynamic
# single-shot generator (which handles all 39+ frontend templates).
# ============================================================

CHAIN_TEMPLATES = {
    "gst_defense": {
        "name": "GST Defense Strategy",
        "description": "Full defense workflow: Research statute, find precedent, draft reply, calculate penalty exposure.",
        "steps": [
            {"id": "research", "title": "Statutory Research", "prompt": "Research all relevant GST Act provisions, rules, circulars, and notifications related to the following matter. Identify the exact sections involved, the legal position, and any recent amendments. Matter: {input}"},
            {"id": "precedent", "title": "Precedent Analysis", "prompt": "Based on the statutory research below, identify the 5 most relevant tribunal/court decisions that support the taxpayer's position. For each, provide the case name, court, year, and the key ratio decidendi.\n\nStatutory Research:\n{prev_output}"},
            {"id": "draft", "title": "Draft Reply", "prompt": "Using the statutory research and precedent analysis below, draft a professional reply to the GST show cause notice. Use proper legal formatting with numbered paragraphs. Include all relevant section citations and case law references.\n\nResearch:\n{step_research}\n\nPrecedents:\n{prev_output}"},
            {"id": "calculate", "title": "Penalty Computation", "prompt": "Based on the entire analysis below, compute the exact tax, interest under Section 50, and penalty exposure under Section 73/74 of the CGST Act. Show all calculations step by step.\n\nDraft Reply:\n{prev_output}"},
        ]
    },
    "contract_review": {
        "name": "Contract Review Pipeline",
        "description": "Full contract analysis: Extract obligations, identify risks, draft amendments.",
        "steps": [
            {"id": "extract", "title": "Obligation Extraction", "prompt": "Extract every obligation, deadline, condition, and penalty from the following contract. Organize by party.\n\nContract:\n{input}"},
            {"id": "risk", "title": "Risk Assessment", "prompt": "Analyze each extracted obligation for legal risk. Flag clauses that are one-sided, unusually broad, or deviate from standard market terms under Indian law. Rate each as HIGH, MEDIUM, or LOW.\n\nObligations:\n{prev_output}"},
            {"id": "amendments", "title": "Draft Amendments", "prompt": "For each HIGH and MEDIUM risk clause identified, draft a proposed amendment that better protects our client's interests while remaining commercially reasonable.\n\nRisk Assessment:\n{prev_output}"},
        ]
    },
    "litigation_prep": {
        "name": "Litigation Preparation",
        "description": "End-to-end litigation filing: Summarize facts, research law, draft petition, calculate limitation.",
        "steps": [
            {"id": "facts", "title": "Fact Summary", "prompt": "Organize the following facts chronologically. Identify the key dispute, parties involved, relevant dates, and the relief sought.\n\nFacts:\n{input}"},
            {"id": "law", "title": "Legal Research", "prompt": "Based on the fact summary below, identify all applicable statutes, relevant sections, and the legal principles that govern this dispute. Include limitation period analysis.\n\nFact Summary:\n{prev_output}"},
            {"id": "draft", "title": "Draft Petition", "prompt": "Draft a professional petition/complaint based on the facts and legal research below. Include proper cause title, jurisdiction statement, factual allegations in numbered paragraphs, legal grounds, and prayer clause.\n\nFacts:\n{step_facts}\n\nLegal Research:\n{prev_output}"},
            {"id": "limitation", "title": "Limitation Analysis", "prompt": "Calculate the exact limitation period for filing this petition. Identify the starting date, applicable limitation period, any grounds for condonation of delay, and the last date for filing.\n\nPetition:\n{prev_output}"},
        ]
    },
    "tax_audit": {
        "name": "Tax Audit Preparation",
        "description": "Form 3CD preparation: Collect data, verify clauses, draft report.",
        "steps": [
            {"id": "data", "title": "Data Collection", "prompt": "Based on the client information below, identify all data points required for Form 3CD preparation. List each clause and what specific data/documents are needed.\n\nClient Info:\n{input}"},
            {"id": "verify", "title": "Clause Verification", "prompt": "For each Form 3CD clause, verify the data provided against the requirements. Flag any missing information, discrepancies, or areas requiring further investigation.\n\nData:\n{prev_output}"},
            {"id": "draft", "title": "Draft Report", "prompt": "Draft the Form 3CD tax audit report based on the verified data. Use the prescribed format for each clause. Include all mandatory disclosures and qualifications.\n\nVerified Data:\n{prev_output}"},
        ]
    }
}

# In-memory chain store with TTL cleanup
active_chains = {}
_CHAIN_TTL = 3600  # 1 hour — completed/abandoned chains are evicted after this
_CHAIN_MAX = 50  # Max concurrent chains in memory before forced cleanup


# ============================================================
# SPECTR WORKFLOW SYSTEM PROMPT — used for all workflow generation
# ============================================================

WORKFLOW_SYSTEM_PROMPT = """You are Spectr — the most advanced legal and tax document generation engine for Indian CAs, Advocates, and CFOs.

You are generating a FINAL DELIVERABLE DOCUMENT as part of a structured workflow. This document will be:
- Printed and placed in case files
- Filed with courts, tribunals, or tax authorities
- Forwarded to clients, board members, and opposing counsel
- Relied on for decisions involving crores of rupees

DOCUMENT GENERATION RULES:
1. Generate the COMPLETE document — not a template, not an outline, not bullet points. A full, filing-ready document.
2. Use proper legal formatting: numbered paragraphs (1, 1.1, 1.1.1), formal headers, proper salutation and sign-off blocks.
3. Every legal claim must cite a specific section number, rule, circular, or case law.
4. Use precise legal terminology naturally: "void ab initio," "ratio decidendi," "pari materia," "ultra vires."
5. Include jurisdiction-appropriate provisions under Indian law.
6. If a bail application, it should be 5-10 pages. If a notice reply, 3-5 pages. If a computation, show all working.
7. For tax computations: show every step, every rate, every threshold, every date.
8. For legal drafting: include cause title, jurisdiction, factual matrix, legal grounds, prayer clause, verification.
9. NEVER produce a skeleton. NEVER say "insert details here." Use the provided facts to generate the real document.

QUALITY STANDARD:
- A senior partner should be able to sign this document without edits.
- An assessing officer should see depth that makes them reconsider their position.
- A judge should see research that exceeds what most lawyers produce in a week.
- Every citation must be accurate — wrong citations destroy credibility permanently.

CASE LAW ACCURACY:
- State what each case ACTUALLY decided — never stretch a ratio.
- Flag pre-GST cases when citing for GST propositions.
- Note if a section has been amended since the judgment.
- Tag training-data citations: [From training knowledge — verify independently]
"""


def _evict_stale_chains():
    """Remove completed chains older than _CHAIN_TTL and enforce max chain limit."""
    now = datetime.now(timezone.utc)
    to_remove = []
    for cid, chain in active_chains.items():
        created = chain.get("created_at", "")
        try:
            created_dt = datetime.fromisoformat(created)
            age_seconds = (now - created_dt).total_seconds()
            if age_seconds > _CHAIN_TTL:
                to_remove.append(cid)
            elif chain.get("status") == "completed" and age_seconds > 300:
                # Completed chains evicted after 5 min
                to_remove.append(cid)
        except (ValueError, TypeError):
            pass

    for cid in to_remove:
        active_chains.pop(cid, None)

    # Hard cap: if still over limit, evict oldest
    if len(active_chains) > _CHAIN_MAX:
        sorted_chains = sorted(active_chains, key=lambda k: active_chains[k].get("created_at", ""))
        for cid in sorted_chains[:len(active_chains) - _CHAIN_MAX]:
            active_chains.pop(cid, None)

    if to_remove:
        logger.info(f"Chain cleanup: evicted {len(to_remove)} stale chain(s), {len(active_chains)} active")


async def start_chain(chain_type: str, initial_input: str, user_id: str) -> dict:
    """Start a new workflow chain and execute the first step."""
    _evict_stale_chains()

    # Check if this is a named multi-step chain
    if chain_type in CHAIN_TEMPLATES:
        return await _start_named_chain(chain_type, initial_input, user_id)

    # Otherwise: dynamic single-shot generation for all 39+ frontend templates
    return await _start_dynamic_workflow(chain_type, initial_input, user_id)


async def _start_named_chain(chain_type: str, initial_input: str, user_id: str) -> dict:
    """Start a pre-defined multi-step chain."""
    template = CHAIN_TEMPLATES[chain_type]
    chain_id = f"chain_{uuid.uuid4().hex[:12]}"

    chain = {
        "chain_id": chain_id,
        "chain_type": chain_type,
        "name": template["name"],
        "user_id": user_id,
        "steps": template["steps"],
        "current_step": 0,
        "step_outputs": {},
        "initial_input": initial_input,
        "status": "in_progress",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    first_step = template["steps"][0]
    prompt = first_step["prompt"].replace("{input}", initial_input)

    output = await _execute_step_with_spectr_pipeline(prompt)
    chain["step_outputs"][first_step["id"]] = output
    active_chains[chain_id] = chain

    return {
        "chain_id": chain_id,
        "name": template["name"],
        "current_step": 0,
        "total_steps": len(template["steps"]),
        "step_title": first_step["title"],
        "step_output": output,
        "next_step": template["steps"][1]["title"] if len(template["steps"]) > 1 else None,
        "status": "in_progress"
    }


async def _start_dynamic_workflow(chain_type: str, initial_input: str, user_id: str) -> dict:
    """Handle any workflow type dynamically with a 2-step flow:
    Step 1: Generate the complete document
    Step 2: Review, edit, finalize → export DOCX
    """
    chain_id = f"chain_{uuid.uuid4().hex[:12]}"

    # Extract workflow name from the input
    name_match = re.search(r'=== WORKFLOW: (.+?) ===', initial_input)
    workflow_name = name_match.group(1) if name_match else chain_type.replace('_', ' ').title()

    steps = [
        {"id": "generate", "title": f"Generate {workflow_name}", "prompt": ""},
        {"id": "finalize", "title": "Review & Export", "prompt": ""},
    ]

    chain = {
        "chain_id": chain_id,
        "chain_type": chain_type,
        "name": workflow_name,
        "user_id": user_id,
        "steps": steps,
        "current_step": 0,
        "step_outputs": {},
        "initial_input": initial_input,
        "status": "in_progress",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    # Generate the document using the full Spectr pipeline
    generation_prompt = f"""Generate a complete, filing-ready {workflow_name} document based on the following details.

{initial_input}

CRITICAL: This must be a COMPLETE document, not an outline. Include:
- Proper legal formatting with numbered paragraphs
- All relevant statutory citations with section numbers
- Case law references where applicable
- Specific dates, amounts, and details from the provided facts
- Proper cause title / header appropriate for this document type
- Sign-off block and verification where required

Generate the full document now."""

    output = await _execute_step_with_spectr_pipeline(generation_prompt)
    chain["step_outputs"]["generate"] = output
    active_chains[chain_id] = chain

    return {
        "chain_id": chain_id,
        "name": workflow_name,
        "current_step": 0,
        "total_steps": 2,
        "step_title": f"Generate {workflow_name}",
        "step_output": output,
        "next_step": "Review & Export",
        "status": "in_progress"
    }


async def advance_chain(chain_id: str, edited_output: str = None, user_id: str = None) -> dict:
    """Advance to the next step in the chain."""
    if chain_id not in active_chains:
        return {"error": "Chain not found", "status": "error"}

    chain = active_chains[chain_id]

    # Authorization: only the chain owner can advance it
    if user_id and chain.get("user_id") and chain["user_id"] != user_id:
        return {"error": "Not authorized to modify this chain", "status": "error"}
    current_idx = chain["current_step"]
    steps = chain["steps"]

    # Save edited output
    if edited_output:
        current_step_id = steps[current_idx]["id"]
        chain["step_outputs"][current_step_id] = edited_output

    # Move to next step
    next_idx = current_idx + 1
    if next_idx >= len(steps):
        chain["status"] = "completed"
        return {
            "chain_id": chain_id,
            "status": "completed",
            "all_outputs": chain["step_outputs"]
        }

    chain["current_step"] = next_idx
    next_step = steps[next_idx]

    # For dynamic workflows, step 2 is "finalize" — just pass through
    if next_step["id"] == "finalize":
        # The edited output from step 1 becomes the final document
        final_output = edited_output or chain["step_outputs"].get("generate", "")
        chain["step_outputs"]["finalize"] = final_output
        chain["status"] = "completed"
        return {
            "chain_id": chain_id,
            "status": "completed",
            "all_outputs": chain["step_outputs"]
        }

    # For named chains, build prompt with context
    if chain["chain_type"] in CHAIN_TEMPLATES:
        template = CHAIN_TEMPLATES[chain["chain_type"]]
        prompt = next_step["prompt"]
        prev_step_id = steps[next_idx - 1]["id"]
        prompt = prompt.replace("{prev_output}", chain["step_outputs"].get(prev_step_id, ""))
        prompt = prompt.replace("{input}", chain["initial_input"])

        for step_id, step_output in chain["step_outputs"].items():
            prompt = prompt.replace(f"{{step_{step_id}}}", step_output)

        output = await _execute_step_with_spectr_pipeline(prompt)
    else:
        output = edited_output or ""

    chain["step_outputs"][next_step["id"]] = output
    next_next = steps[next_idx + 1]["title"] if next_idx + 1 < len(steps) else None

    return {
        "chain_id": chain_id,
        "current_step": next_idx,
        "total_steps": len(steps),
        "step_title": next_step["title"],
        "step_output": output,
        "next_step": next_next,
        "status": "in_progress"
    }


async def get_chain_status(chain_id: str, user_id: str = None) -> dict:
    """Get the full status of a chain."""
    if chain_id not in active_chains:
        return {"error": "Chain not found"}
    chain = active_chains[chain_id]

    # Authorization: only the chain owner can view it
    if user_id and chain.get("user_id") and chain["user_id"] != user_id:
        return {"error": "Not authorized to view this chain"}
    return {
        "chain_id": chain_id,
        "name": chain["name"],
        "status": chain["status"],
        "current_step": chain["current_step"],
        "total_steps": len(chain["steps"]),
        "steps": [{"id": s["id"], "title": s["title"], "completed": s["id"] in chain["step_outputs"]} for s in chain["steps"]],
        "step_outputs": chain["step_outputs"]
    }


def get_templates() -> list:
    """Return available chain templates."""
    return [
        {"id": k, "name": v["name"], "description": v["description"], "steps": len(v["steps"])}
        for k, v in CHAIN_TEMPLATES.items()
    ]


async def _execute_step_with_spectr_pipeline(prompt: str) -> str:
    """Execute a workflow step using the full Spectr AI cascade.
    Gemini 2.5 Pro → Claude Sonnet → GPT-4o → Groq LLaMA
    Uses a single shared HTTP session across all tiers.
    """
    system = WORKFLOW_SYSTEM_PROMPT

    async with aiohttp.ClientSession() as session:
        # Tier 1: Gemini 2.5 Pro (best for long-form generation)
        if GOOGLE_AI_KEY:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GOOGLE_AI_KEY}"
                payload = {
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.15, "maxOutputTokens": 16000}
                }
                async with session.post(url, headers={"Content-Type": "application/json"},
                                        json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                        text = "\n".join([p.get("text", "") for p in parts if "text" in p])
                        if text and len(text) > 200:
                            logger.info(f"Workflow step: Gemini 2.5 Pro returned {len(text)} chars")
                            return text
                    else:
                        logger.warning(f"Gemini 2.5 Pro failed ({resp.status})")
            except Exception as e:
                logger.warning(f"Gemini 2.5 Pro error: {e}")

        # Tier 2: Claude Sonnet
        if ANTHROPIC_KEY:
            try:
                payload = {
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 8000,
                    "system": system,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.15
                }
                async with session.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": ANTHROPIC_KEY,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json=payload, timeout=aiohttp.ClientTimeout(total=90)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        text = data.get("content", [{}])[0].get("text", "")
                        if text and len(text) > 200:
                            logger.info(f"Workflow step: Claude returned {len(text)} chars")
                            return text
                    else:
                        logger.warning(f"Claude failed ({resp.status})")
            except Exception as e:
                logger.warning(f"Claude error: {e}")

        # Tier 3: GPT-4o
        if OPENAI_KEY:
            try:
                payload = {
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.15,
                    "max_tokens": 8000
                }
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
                    json=payload, timeout=aiohttp.ClientTimeout(total=90)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        text = data["choices"][0]["message"]["content"]
                        if text and len(text) > 200:
                            logger.info(f"Workflow step: GPT-4o returned {len(text)} chars")
                            return text
                    else:
                        logger.warning(f"GPT-4o failed ({resp.status})")
            except Exception as e:
                logger.warning(f"GPT-4o error: {e}")

    # Tier 4: Groq LLaMA (fallback — uses its own session with retries)
    return await _execute_step(prompt)


async def _execute_step(prompt: str) -> str:
    """Execute a single chain step via Groq LLaMA (fast fallback)."""
    if not GROQ_KEY:
        return "Error: No AI API keys configured. Please set GROQ_KEY, GOOGLE_AI_KEY, ANTHROPIC_API_KEY, or OPENAI_KEY."
    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": WORKFLOW_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt[:20000]}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 8000
                }
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                    json=payload, timeout=aiohttp.ClientTimeout(total=90)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"]
                    elif resp.status == 429 or resp.status >= 500:
                        import asyncio
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        err = await resp.text()
                        logger.error(f"Groq error ({resp.status}): {err[:200]}")
                        return f"Error generating document. Please try again."
        except Exception as e:
            if attempt == 2:
                logger.error(f"Workflow step execution error: {e}")
                return f"Error generating document: {str(e)}"
            import asyncio
            await asyncio.sleep(2 ** attempt)
    return "Error: Failed after 3 attempts. Please try again."
