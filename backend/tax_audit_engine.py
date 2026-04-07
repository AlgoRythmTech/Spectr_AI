"""
Form 3CD / Tax Audit AI Assistant
The highest-value CA feature: AI reads Tally export + bank statements + contracts
and generates clause-wise Form 3CD observations for the auditor's review.
Worth ₹15,000-25,000/month to CA firms alone.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# All 44 clauses of Form 3CD with their requirements
FORM_3CD_CLAUSES = {
    "1": {"title": "Name and address of the assessee", "category": "identity", "auto_fill": True},
    "2": {"title": "PAN", "category": "identity", "auto_fill": True},
    "3": {"title": "Status (Individual/HUF/Firm/Co.)", "category": "identity", "auto_fill": True},
    "4": {"title": "Previous year ended March 31", "category": "identity", "auto_fill": True},
    "5": {"title": "Assessment year", "category": "identity", "auto_fill": True},
    "6": {"title": "Address of branches (if any)", "category": "structure", "auto_fill": False},
    "7": {"title": "Nature of business/profession", "category": "business", "auto_fill": True},
    "8": {"title": "Relevant applicable accounting standards", "category": "accounting", "auto_fill": False},
    "9": {"title": "Reference to earlier audit reports", "category": "audit_history", "auto_fill": False},
    "10": {"title": "Nature of books and records maintained", "category": "books", "auto_fill": False},
    "11": {"title": "Method of accounting — cash or mercantile", "category": "accounting", "auto_fill": False},
    "12": {"title": "Method of accounting for construction contracts", "category": "accounting", "auto_fill": False},
    "13": {"title": "Method of valuation of closing stock", "category": "stock", "auto_fill": False},
    "14": {"title": "Capital asset converted to stock — fair market value", "category": "stock", "auto_fill": False},
    "15": {"title": "Amounts not credited to P&L — Section 28 income", "category": "income", "auto_fill": False},
    "16": {"title": "Amounts debited to P&L — Section 30-37 analysis", "category": "expenses", "auto_fill": False},
    "17": {"title": "Deductions allowed on actual payment — Section 43B", "category": "expenses", "auto_fill": False},
    "18": {"title": "Amounts deemed as income — Section 41", "category": "income", "auto_fill": False},
    "19": {"title": "Sum paid/payable to related parties — Section 40A(2)(b)", "category": "related_party", "auto_fill": False},
    "20": {"title": "Payments made in cash exceeding ₹10,000 — Section 40A(3)", "category": "payments", "auto_fill": False},
    "21": {"title": "Deductions under Chapter VI-A", "category": "deductions", "auto_fill": False},
    "22": {"title": "CENVAT credit / Input Service Distributor", "category": "gst", "auto_fill": False},
    "23": {"title": "Prior period items debited/credited", "category": "accounting", "auto_fill": False},
    "24": {"title": "Income on which tax is deducted at source — Section 194N", "category": "tds", "auto_fill": False},
    "25": {"title": "Bonus/commission — Section 36(1)(ii)", "category": "expenses", "auto_fill": False},
    "26": {"title": "Interest not deducted — Section 23", "category": "interest", "auto_fill": False},
    "27": {"title": "Loans/deposits/advances — Section 269SS/269T", "category": "loans", "auto_fill": False},
    "28": {"title": "Central/state government dues outstanding", "category": "dues", "auto_fill": False},
    "29": {"title": "Cost audit or company law audit details", "category": "audit", "auto_fill": False},
    "30": {"title": "Assessments completed or in progress during the year", "category": "litigation", "auto_fill": False},
    "31": {"title": "Depreciation under Companies Act vs IT Act", "category": "depreciation", "auto_fill": False},
    "32": {"title": "Deduction for expenditure on scientific research", "category": "deductions", "auto_fill": False},
    "33": {"title": "Deduction under Section 35D/35E", "category": "deductions", "auto_fill": False},
    "34": {"title": "TDS/TCS compliance details", "category": "tds", "auto_fill": False},
    "35": {"title": "Amounts deemed as income from discontinued operations", "category": "income", "auto_fill": False},
    "36": {"title": "Quantitative details of goods (for traders/manufacturers)", "category": "stock", "auto_fill": False},
    "37": {"title": "Details of expenditure incurred in foreign exchange", "category": "forex", "auto_fill": False},
    "38": {"title": "Division between personal and business expenditure", "category": "expenses", "auto_fill": False},
    "39": {"title": "On conversion of inventory to capital asset — Section 45(2A)", "category": "capital", "auto_fill": False},
    "40": {"title": "Capital gains — Sections 45, 47, 47A", "category": "capital", "auto_fill": False},
    "41": {"title": "In case of company — details of share buyback", "category": "capital", "auto_fill": False},
    "42": {"title": "STCG/LTCG on land and building — land component", "category": "capital", "auto_fill": False},
    "43": {"title": "GST — details of ITC claimed/reversed", "category": "gst", "auto_fill": False},
    "44": {"title": "Break-up of total expenditure vis-à-vis GST registered/unregistered suppliers", "category": "gst", "auto_fill": False},
}

AUDIT_PROMPT_TEMPLATE = """
You are a Tax Audit Intelligence Engine generating Form 3CD observations for a Chartered Accountant.

FINANCIAL YEAR: {fy}
ASSESSEE: {assessee_name}
PAN: {pan}
TURNOVER: ₹{turnover_lakhs} Lakhs

INSTRUCTIONS:
For each clause below, analyze the provided financial data and generate:
1. OBSERVATION: What the audit found
2. DISCLOSURE REQUIRED: Yes/No and what exactly
3. RISK FLAG: HIGH/MEDIUM/LOW with reason
4. AUDITOR NOTE: What the CA must manually verify

Focus on high-risk clauses: 19 (Related Party 40A(2)(b)), 20 (Cash payments 40A(3)), 
27 (Section 269SS/269T), 34 (TDS compliance), 43 (GST ITC), 44 (GST supplier classification).

FINANCIAL DATA PROVIDED:
{financial_data}

BANK STATEMENT FORENSIC ANALYSIS:
{forensic_summary}

Generate observations for ALL 44 clauses. Mark AUTO-VERIFIED clauses as such.
For HIGH risk clauses, be extremely specific about disclosure and penalty exposure.
Format each clause as:
CLAUSE [N]: [Title]
Status: AUTO-VERIFIED / REQUIRES ATTENTION / HIGH RISK
Observation: [...]
Disclosure Required: [...]
Auditor Note: [...]
---
"""


def build_audit_prompt(assessee_name: str, pan: str, fy: str, 
                       turnover_lakhs: float, financial_data: str,
                       forensic_summary: str = "") -> str:
    """Build the AI prompt for Form 3CD generation."""
    return AUDIT_PROMPT_TEMPLATE.format(
        fy=fy,
        assessee_name=assessee_name,
        pan=pan,
        turnover_lakhs=turnover_lakhs,
        financial_data=financial_data[:8000],
        forensic_summary=forensic_summary[:2000] if forensic_summary else "Not provided"
    )


def parse_audit_clauses(ai_response: str) -> list:
    """Parse AI response into structured clause-by-clause observations."""
    clauses = []
    current = {}
    
    for line in ai_response.split("\n"):
        line = line.strip()
        if line.startswith("CLAUSE "):
            if current:
                clauses.append(current)
            current = {"clause": line, "status": "INFO", "observation": "", "disclosure": "", "note": ""}
        elif line.startswith("Status:"):
            status_text = line.replace("Status:", "").strip()
            if "HIGH RISK" in status_text:
                current["status"] = "HIGH_RISK"
            elif "REQUIRES ATTENTION" in status_text:
                current["status"] = "ATTENTION"
            else:
                current["status"] = "OK"
        elif line.startswith("Observation:"):
            current["observation"] = line.replace("Observation:", "").strip()
        elif line.startswith("Disclosure Required:"):
            current["disclosure"] = line.replace("Disclosure Required:", "").strip()
        elif line.startswith("Auditor Note:"):
            current["note"] = line.replace("Auditor Note:", "").strip()
    
    if current:
        clauses.append(current)
    
    return clauses
