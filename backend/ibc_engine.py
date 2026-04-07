"""
IBC / NCLT Intelligence Module
Dedicated workflows for Insolvency and Bankruptcy Code proceedings:
- Section 7 (Financial Creditor) Application Drafting
- Section 9 (Operational Creditor) Application Drafting  
- CIRP Timeline Monitoring
- Section 29A Eligibility Checking
- Resolution Plan Review
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# IBC Timelines per the Code and IBBI Regulations
IBC_TIMELINES = {
    "cirp_total": {
        "days": 330, 
        "description": "Total CIRP period including extensions (Section 12 IBC)",
        "extensions": "Maximum 90 days by NCLT + 30 days per NCLT order + 60 days for ongoing litigation"
    },
    "cirp_initial": {
        "days": 180,
        "description": "Initial CIRP period from insolvency commencement date",
        "section": "Section 12(1) IBC"
    },
    "cirp_extension": {
        "days": 90,
        "description": "Maximum extension of CIRP beyond initial 180 days",
        "section": "Section 12(2) IBC"
    },
    "eoi_minimum": {
        "days": 30,
        "description": "Minimum time for Expression of Interest invitation",
        "section": "Regulation 36A(4) CIRP Regulations"
    },
    "resolution_plan_submission": {
        "days": 30,
        "description": "Time for resolution applicants to submit plans after Request for Resolution Plans",
        "section": "Regulation 39(1) CIRP Regulations"
    },
    "coc_approval": {
        "days": 7,
        "description": "CoC must approve/reject resolution plan within 7 days of receiving IRP recommendation",
        "section": "Regulation 39(3) CIRP Regulations"
    },
    "nclt_admission": {
        "days": 14,
        "description": "NCLT must admit/reject Section 7/9 application within 14 days (targetted)",
        "section": "Section 7(4) / Section 9(5) IBC"
    },
    "public_announcement": {
        "days": 3,
        "description": "IRP must make public announcement within 3 days of appointment",
        "section": "Regulation 6 CIRP Regulations"
    },
    "claims_submission": {
        "days": 14,
        "description": "Creditors must submit claims within 14 days of public announcement",
        "section": "Regulation 12 CIRP Regulations"
    },
    "information_memorandum": {
        "days": 54,
        "description": "Information Memorandum must be prepared within 54 days of CIRP commencement",
        "section": "Regulation 36(1) CIRP Regulations"
    },
}

# Section 29A ineligibility grounds
SECTION_29A_GROUNDS = [
    "Undischarged insolvent",
    "Wilful defaulter under RBI guidelines",
    "NPA for over 1 year (unless fully settled + 1 year elapsed)",
    "Convicted of offence punishable with 2+ years imprisonment",
    "Disqualified as company director under Companies Act",
    "Prohibited by SEBI from accessing capital markets",
    "Person who sold property of corporate debtor in preceding 3 years",
    "Connected person to any of the above (promoters, related parties, directors)",
]

# Pre-defined NCLT Bench jurisdictions
NCLT_BENCHES = {
    "Delhi": ["Delhi NCT", "Haryana", "Punjab", "Himachal Pradesh", "J&K", "Chandigarh"],
    "Mumbai": ["Maharashtra", "Goa"],
    "Kolkata": ["West Bengal", "Bihar", "Jharkhand", "Odisha"],
    "Ahmedabad": ["Gujarat", "Rajasthan"],
    "Chennai": ["Tamil Nadu", "Puducherry"],
    "Bengaluru": ["Karnataka"],
    "Hyderabad": ["Telangana", "Andhra Pradesh"],
    "Allahabad": ["Uttar Pradesh", "Uttarakhand"],
}


def calculate_cirp_milestones(commencement_date: str, bench: str = "Mumbai") -> dict:
    """
    Calculate all CIRP milestone dates from insolvency commencement date.
    """
    try:
        start = datetime.strptime(commencement_date, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Date format must be YYYY-MM-DD"}
    
    today = date.today()
    
    milestones = {}
    for key, config in IBC_TIMELINES.items():
        milestone_date = start + timedelta(days=config["days"])
        days_remaining = (milestone_date - today).days
        milestones[key] = {
            "date": milestone_date.isoformat(),
            "description": config["description"],
            "section": config.get("section", "IBC"),
            "days_from_start": config["days"],
            "days_remaining": days_remaining,
            "status": "EXPIRED" if days_remaining < 0 else ("CRITICAL" if days_remaining <= 7 else ("WARNING" if days_remaining <= 30 else "OK")),
        }
    
    # Summary
    cirp_end = start + timedelta(days=330)
    elapsed = (today - start).days
    cirp_pct = min(100, round(elapsed / 330 * 100, 1))
    
    return {
        "commencement_date": commencement_date,
        "nclt_bench": bench,
        "days_elapsed": elapsed,
        "days_remaining_total_cirp": max(0, (cirp_end - today).days),
        "cirp_progress_pct": cirp_pct,
        "milestones": milestones,
        "critical_alerts": [v for v in milestones.values() if v["status"] in ("CRITICAL", "EXPIRED")],
    }


def check_section_29a_eligibility(applicant_facts: str) -> dict:
    """
    Generate Section 29A checklist for resolution applicant vetting.
    Returns preliminary eligibility assessment (not a legal opinion).
    """
    flags = []
    applicant_lower = applicant_facts.lower()
    
    for ground in SECTION_29A_GROUNDS:
        # Heuristic keyword matches — AI engine should run full analysis
        keywords_map = {
            "Undischarged insolvent": ["insolvent", "bankruptcy"],
            "Wilful defaulter": ["wilful defaulter", "bank default", "rbi list"],
            "NPA": ["npa", "non-performing", "bad loan"],
            "Convicted": ["convicted", "imprisonment", "criminal"],
            "Disqualified as director": ["disqualified director", "din cancelled"],
            "SEBI": ["sebi debarred", "capital market ban"],
        }
        for key, kws in keywords_map.items():
            if key in ground and any(kw in applicant_lower for kw in kws):
                flags.append({
                    "ground": ground,
                    "risk": "HIGH",
                    "note": "Requires detailed legal verification — possible 29A disqualification"
                })
    
    return {
        "applicant_facts_analyzed": True,
        "potential_disqualification_grounds": flags,
        "eligible_prima_facie": len(flags) == 0,
        "caveat": "This is a preliminary AI-assisted check only. A legal opinion under Section 29A requires review of all documents by qualified insolvency counsel.",
        "section": "Section 29A IBC / Regulation 38(1A) CIRP Regulations",
    }


IBC_WORKFLOW_TEMPLATES = {
    "section_7": {
        "title": "Section 7 Application — Financial Creditor",
        "checklist": [
            "Certified copy of credit agreement/loan documentation",
            "Statement of accounts (default date, outstanding amount)",
            "Evidence of default (demand notice, account statement)",
            "Proposed IRP name + IBBI registration number",
            "Board resolution authorizing filing",
            "Form 1 under CIRP Regulations",
            "Annexure to Form 1 (documents listed in Regulation 6(1))",
            "Court fee payment",
        ],
        "section": "Section 7 IBC / Regulation 4 CIRP Regulations",
        "filing_fee": "₹2,000 per application",
        "limitation": "3 years from date of default (may extend with fresh promise/acknowledgement)",
    },
    "section_9": {
        "title": "Section 9 Application — Operational Creditor",
        "checklist": [
            "Demand Notice to Corporate Debtor (Section 8 notice) — served at least 10 days prior",
            "Copy of invoice(s) raising the claim",
            "Affidavit confirming no notice of dispute received",
            "Evidence of delivery of goods/services",
            "Certificate from financial institution (if payment default via banking channels)",
            "Proposed IRP name + IBBI registration number",
            "Form 5 under CIRP Regulations",
            "Court fee payment",
        ],
        "section": "Section 9 IBC / Regulation 6 CIRP Regulations",
        "filing_fee": "₹2,000 per application",
        "limitation": "3 years from date of default",
        "notice_period": "10 days from Section 8 demand notice before filing Section 9",
    },
}
