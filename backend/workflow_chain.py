"""
Agentic Workflow Chain Engine
Multi-step workflows where the output of each step feeds into the next.
"""
import os
import json
import aiohttp
import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

GROQ_KEY = os.environ.get("GROQ_KEY", "")

# Chain templates
CHAIN_TEMPLATES = {
    "gst_defense": {
        "name": "GST Defense Strategy",
        "description": "Full defense workflow: Research statute, find precedent, draft reply, calculate penalty exposure, export PDF.",
        "steps": [
            {"id": "research", "title": "Statutory Research", "prompt": "Research all relevant GST Act provisions, rules, circulars, and notifications related to the following matter. Identify the exact sections involved, the legal position, and any recent amendments. Matter: {input}"},
            {"id": "precedent", "title": "Precedent Analysis", "prompt": "Based on the statutory research below, identify the 5 most relevant tribunal/court decisions that support the taxpayer's position. For each, provide the case name, court, year, and the key ratio decidendi.\n\nStatutory Research:\n{prev_output}"},
            {"id": "draft", "title": "Draft Reply", "prompt": "Using the statutory research and precedent analysis below, draft a professional reply to the GST show cause notice. Use proper legal formatting with numbered paragraphs. Include all relevant section citations and case law references.\n\nResearch:\n{step_research}\n\nPrecedents:\n{prev_output}"},
            {"id": "calculate", "title": "Penalty Computation", "prompt": "Based on the entire analysis below, compute the exact tax, interest under Section 50, and penalty exposure under Section 73/74 of the CGST Act. Show all calculations step by step with applicable rates and periods.\n\nDraft Reply:\n{prev_output}"},
        ]
    },
    "contract_review": {
        "name": "Contract Review Pipeline",
        "description": "Full contract analysis: Extract obligations, identify risks, compare to standard terms, draft amendments.",
        "steps": [
            {"id": "extract", "title": "Obligation Extraction", "prompt": "Extract every obligation, deadline, condition, and penalty from the following contract. Organize by party.\n\nContract:\n{input}"},
            {"id": "risk", "title": "Risk Assessment", "prompt": "Analyze each extracted obligation for legal risk. Flag clauses that are one-sided, unusually broad, or deviate from standard market terms under Indian law. Rate each risk as HIGH, MEDIUM, or LOW.\n\nObligations:\n{prev_output}"},
            {"id": "amendments", "title": "Draft Amendments", "prompt": "For each HIGH and MEDIUM risk clause identified, draft a proposed amendment that better protects our client's interests while remaining commercially reasonable. Provide the original clause wording and the proposed revision.\n\nRisk Assessment:\n{prev_output}"},
        ]
    },
    "litigation_prep": {
        "name": "Litigation Preparation",
        "description": "End-to-end litigation filing: Summarize facts, research law, draft petition, calculate limitation.",
        "steps": [
            {"id": "facts", "title": "Fact Summary", "prompt": "Organize the following facts chronologically. Identify the key dispute, parties involved, relevant dates, and the relief sought.\n\nFacts:\n{input}"},
            {"id": "law", "title": "Legal Research", "prompt": "Based on the fact summary below, identify all applicable statutes, relevant sections, and the legal principles that govern this dispute. Include limitation period analysis.\n\nFact Summary:\n{prev_output}"},
            {"id": "draft", "title": "Draft Petition", "prompt": "Draft a professional petition/complaint based on the facts and legal research below. Include proper cause title, jurisdiction statement, factual allegations in numbered paragraphs, legal grounds, and prayer clause.\n\nFacts:\n{step_facts}\n\nLegal Research:\n{prev_output}"},
            {"id": "limitation", "title": "Limitation Analysis", "prompt": "Calculate the exact limitation period for filing this petition. Identify the starting date, applicable limitation period under the Limitation Act 1963 or the specific statute, any grounds for condonation of delay, and the last date for filing.\n\nPetition:\n{prev_output}"},
        ]
    },
    "tax_audit": {
        "name": "Tax Audit Preparation",
        "description": "Form 3CD preparation: Collect data, verify clauses, draft report, flag discrepancies.",
        "steps": [
            {"id": "data", "title": "Data Collection", "prompt": "Based on the client information below, identify all data points required for Form 3CD preparation. List each clause of Form 3CD and what specific data/documents are needed.\n\nClient Info:\n{input}"},
            {"id": "verify", "title": "Clause Verification", "prompt": "For each Form 3CD clause, verify the data provided against the requirements. Flag any missing information, discrepancies, or areas requiring further investigation.\n\nData:\n{prev_output}"},
            {"id": "draft", "title": "Draft Report", "prompt": "Draft the Form 3CD tax audit report based on the verified data. Use the prescribed format for each clause. Include all mandatory disclosures and qualifications.\n\nVerified Data:\n{prev_output}"},
        ]
    }
}

# In-memory chain store (in production, use MongoDB)
active_chains = {}

async def start_chain(chain_type: str, initial_input: str, user_id: str) -> dict:
    """Start a new workflow chain and execute the first step."""
    if chain_type not in CHAIN_TEMPLATES:
        return {"error": f"Unknown chain type: {chain_type}"}

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

    # Execute first step
    first_step = template["steps"][0]
    prompt = first_step["prompt"].replace("{input}", initial_input)

    output = await _execute_step(prompt)
    chain["step_outputs"][first_step["id"]] = output

    active_chains[chain_id] = chain

    return {
        "chain_id": chain_id,
        "name": template["name"],
        "current_step": 0,
        "total_steps": len(template["steps"]),
        "step_title": first_step["title"],
        "step_output": output,
        "next_step": template["steps"][1]["title"] if len(template["steps"]) > 1 else None
    }

async def advance_chain(chain_id: str, edited_output: str = None) -> dict:
    """Advance to the next step in the chain."""
    if chain_id not in active_chains:
        return {"error": "Chain not found"}

    chain = active_chains[chain_id]
    template = CHAIN_TEMPLATES[chain["chain_type"]]
    current_idx = chain["current_step"]

    # Save edited output if provided
    if edited_output:
        current_step_id = template["steps"][current_idx]["id"]
        chain["step_outputs"][current_step_id] = edited_output

    # Move to next step
    next_idx = current_idx + 1
    if next_idx >= len(template["steps"]):
        chain["status"] = "completed"
        return {
            "chain_id": chain_id,
            "status": "completed",
            "all_outputs": chain["step_outputs"]
        }

    chain["current_step"] = next_idx
    next_step = template["steps"][next_idx]

    # Build prompt with context from previous steps
    prompt = next_step["prompt"]
    prev_step_id = template["steps"][next_idx - 1]["id"]
    prompt = prompt.replace("{prev_output}", chain["step_outputs"].get(prev_step_id, ""))
    prompt = prompt.replace("{input}", chain["initial_input"])

    # Replace any {step_xxx} references
    for step_id, step_output in chain["step_outputs"].items():
        prompt = prompt.replace(f"{{step_{step_id}}}", step_output)

    output = await _execute_step(prompt)
    chain["step_outputs"][next_step["id"]] = output

    next_next = template["steps"][next_idx + 1]["title"] if next_idx + 1 < len(template["steps"]) else None

    return {
        "chain_id": chain_id,
        "current_step": next_idx,
        "total_steps": len(template["steps"]),
        "step_title": next_step["title"],
        "step_output": output,
        "next_step": next_next,
        "status": "in_progress"
    }

async def get_chain_status(chain_id: str) -> dict:
    """Get the full status of a chain."""
    if chain_id not in active_chains:
        return {"error": "Chain not found"}
    chain = active_chains[chain_id]
    template = CHAIN_TEMPLATES[chain["chain_type"]]
    return {
        "chain_id": chain_id,
        "name": chain["name"],
        "status": chain["status"],
        "current_step": chain["current_step"],
        "total_steps": len(template["steps"]),
        "steps": [{"id": s["id"], "title": s["title"], "completed": s["id"] in chain["step_outputs"]} for s in template["steps"]],
        "step_outputs": chain["step_outputs"]
    }

def get_templates() -> list:
    """Return available chain templates."""
    return [
        {"id": k, "name": v["name"], "description": v["description"], "steps": len(v["steps"])}
        for k, v in CHAIN_TEMPLATES.items()
    ]

async def _execute_step(prompt: str) -> str:
    """Execute a single chain step via Groq."""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": "You are a legal and tax professional working on a multi-step workflow. Produce thorough, precise, and actionable output for the current step. Do not use markdown headers (#) or asterisks for bold (**). Write in flowing professional prose with numbered paragraphs where appropriate."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 4000
            }
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return f"Error executing step: {await resp.text()}"
    except Exception as e:
        return f"Error: {str(e)}"
