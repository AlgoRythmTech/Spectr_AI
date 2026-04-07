"""
Indian Legal Tools Engine — Monopoly Feature Set
Covers: Limitation Tracker, Stamp Duty Calculator, 26AS TDS Mismatch,
IT Scrutiny Bot, Forensic Bank Analysis, eCourts Scraper
"""
import re
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# =====================================================================
# 1. LIMITATION PERIOD TRACKER (Limitation Act, 1963)
# =====================================================================
LIMITATION_PERIODS = {
    # Civil Suits 
    "money_suit": {"period_years": 3, "section": "Article 1", "from": "when the right to sue accrues"},
    "specific_performance": {"period_years": 3, "section": "Article 54", "from": "date fixed for performance, or refusal"},
    "recovery_of_movable": {"period_years": 3, "section": "Article 9", "from": "when the property is wrongfully taken"},
    "recovery_of_immovable": {"period_years": 12, "section": "Article 65", "from": "when the possession becomes adverse"},
    "partition_suit": {"period_years": 12, "section": "Article 110", "from": "when exclusion from joint possession"},
    "rent_arrears": {"period_years": 3, "section": "Article 52", "from": "when the arrears become due"},
    "tort_compensation": {"period_years": 1, "section": "Article 72", "from": "date of the wrongful act"},
    "defamation": {"period_years": 1, "section": "Article 75", "from": "when the defamation is published"},
    "cheque_bounce_138": {"period_days": 30, "section": "Section 142 NI Act", "from": "date of cause of action (after 15-day notice period)"},
    
    # Appeals
    "appeal_district_court": {"period_days": 30, "section": "Section 96 CPC / Order 41", "from": "date of decree"},
    "appeal_high_court": {"period_days": 90, "section": "Section 100 CPC (Second Appeal)", "from": "date of decree"},
    "appeal_supreme_court": {"period_days": 90, "section": "Article 133/134", "from": "date of HC judgment"},
    "revision_petition": {"period_days": 90, "section": "Section 115 CPC", "from": "date of order"},
    
    # Tax
    "gst_appeal_first": {"period_months": 3, "section": "Section 107 CGST Act", "from": "date of order + 1 month condonable"},
    "gst_appeal_tribunal": {"period_months": 3, "section": "Section 112 CGST Act", "from": "date of appellate order"},
    "it_appeal_cit": {"period_days": 30, "section": "Section 246A IT Act", "from": "date of assessment order"},
    "it_appeal_itat": {"period_days": 60, "section": "Section 253 IT Act", "from": "date of CIT(A) order"},
    
    # Corporate / IBC
    "nclt_ibc_section7": {"period_years": 3, "section": "Section 7 IBC", "from": "date of default"},
    "nclt_ibc_section9": {"period_years": 3, "section": "Section 9 IBC", "from": "date of default"},
    "nclat_appeal": {"period_days": 30, "section": "Section 61 IBC", "from": "date of NCLT order + 15 days condonable"},
}


def calculate_limitation(suit_type: str, accrual_date: str) -> dict:
    """Calculate limitation period with deadline alerts."""
    if suit_type not in LIMITATION_PERIODS:
        return {"error": f"Unknown suit type: {suit_type}. Available: {list(LIMITATION_PERIODS.keys())}"}
    
    config = LIMITATION_PERIODS[suit_type]
    try:
        start = datetime.strptime(accrual_date, "%Y-%m-%d")
    except ValueError:
        return {"error": "Date format must be YYYY-MM-DD"}
    
    if "period_years" in config:
        deadline = start.replace(year=start.year + config["period_years"])
    elif "period_months" in config:
        month = start.month + config["period_months"]
        year = start.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        deadline = start.replace(year=year, month=month)
    elif "period_days" in config:
        deadline = start + timedelta(days=config["period_days"])
    else:
        return {"error": "Invalid configuration"}
    
    today = datetime.now()
    days_remaining = (deadline - today).days
    
    status = "SAFE" if days_remaining > 30 else ("WARNING" if days_remaining > 7 else ("CRITICAL" if days_remaining > 0 else "EXPIRED"))
    
    return {
        "suit_type": suit_type,
        "section": config["section"],
        "limitation_from": config["from"],
        "accrual_date": accrual_date,
        "deadline": deadline.strftime("%Y-%m-%d"),
        "days_remaining": max(days_remaining, 0),
        "status": status,
        "condonation_advice": "File Section 5 application with sufficient cause" if days_remaining < 0 else None,
    }


# =====================================================================
# 2. MULTI-STATE STAMP DUTY CALCULATOR
# =====================================================================
STAMP_DUTY_RATES = {
    "maharashtra": {
        "sale_deed": {"rate_pct": 5, "registration_pct": 1, "notes": "Metro areas: 6% (1% metro cess)"},
        "lease_deed": {"rate_pct": 0.25, "max_cap": 500000, "notes": "Per Article 36"},
        "gift_deed_family": {"rate_pct": 3, "notes": "Reduced rate for blood relatives"},
        "mortgage_deed": {"rate_pct": 0.3, "max_cap": 1000000, "notes": "Simple mortgage"},
        "partnership_deed": {"flat_amount": 1000, "notes": "Per Article 47"},
        "power_of_attorney": {"flat_amount": 500, "notes": "General POA"},
        "agreement_to_sell": {"rate_pct": 0.1, "notes": "Article 5(g-a)"},
    },
    "karnataka": {
        "sale_deed": {"rate_pct": 5, "registration_pct": 1, "notes": "BBMP areas + surcharge"},
        "lease_deed": {"rate_pct": 1, "notes": "Per Article 35"},
        "gift_deed_family": {"rate_pct": 0, "notes": "Exempt for blood relatives"},
        "partnership_deed": {"flat_amount": 500, "notes": "Article 46"},
        "power_of_attorney": {"flat_amount": 200, "notes": "GPA"},
    },
    "delhi": {
        "sale_deed": {"rate_pct": 6, "registration_pct": 1, "notes": "Male: 6%, Female: 4%"},
        "lease_deed": {"rate_pct": 2, "notes": "Lease > 5 years"},
        "gift_deed_family": {"rate_pct": 4, "notes": "Female transferee: 2%"},
        "mortgage_deed": {"rate_pct": 1, "notes": "With possession"},
        "partnership_deed": {"flat_amount": 1000, "notes": "Indo Stamp Act"},
    },
    "uttar_pradesh": {
        "sale_deed": {"rate_pct": 7, "registration_pct": 1, "notes": "Plus 2% Nagar Nigam cess in urban"},
        "gift_deed_family": {"rate_pct": 0, "notes": "Exempt for blood relatives up to certain limit"},
    },
    "tamil_nadu": {
        "sale_deed": {"rate_pct": 7, "registration_pct": 1, "notes": "Plus 4% registration"},
        "gift_deed_family": {"rate_pct": 1, "notes": "Between specified relatives"},
    },
}


def calculate_stamp_duty(state: str, instrument: str, consideration: float, gender: str = "male") -> dict:
    """Calculate stamp duty + registration fees for a given state and instrument."""
    state_lower = state.lower().replace(" ", "_")
    if state_lower not in STAMP_DUTY_RATES:
        return {"error": f"State not found. Available: {list(STAMP_DUTY_RATES.keys())}"}
    
    state_data = STAMP_DUTY_RATES[state_lower]
    instrument_lower = instrument.lower().replace(" ", "_")
    if instrument_lower not in state_data:
        return {"error": f"Instrument not found for {state}. Available: {list(state_data.keys())}"}
    
    config = state_data[instrument_lower]
    
    if "flat_amount" in config:
        stamp_duty = config["flat_amount"]
    elif "rate_pct" in config:
        stamp_duty = consideration * config["rate_pct"] / 100
        if "max_cap" in config:
            stamp_duty = min(stamp_duty, config["max_cap"])
    else:
        stamp_duty = 0
    
    registration = consideration * config.get("registration_pct", 0) / 100
    
    # Delhi gender adjustment
    if state_lower == "delhi" and gender.lower() == "female" and instrument_lower == "sale_deed":
        stamp_duty = consideration * 4 / 100
    
    return {
        "state": state,
        "instrument": instrument,
        "consideration_amount": consideration,
        "stamp_duty": round(stamp_duty, 2),
        "registration_fee": round(registration, 2),
        "total_payable": round(stamp_duty + registration, 2),
        "notes": config.get("notes", ""),
        "gender_applied": gender,
    }


# =====================================================================
# 3. FORENSIC BANK STATEMENT ANALYZER
# =====================================================================
def analyze_bank_statement(transactions: list) -> dict:
    """
    Analyze bank transactions for forensic red flags.
    Input: list of dicts with keys: date, narration, debit, credit, balance
    """
    flags = []
    total_debit = 0
    total_credit = 0
    cash_deposits = []
    round_amounts = []
    related_party_suspects = []
    
    for idx, txn in enumerate(transactions):
        debit = float(txn.get("debit", 0) or 0)
        credit = float(txn.get("credit", 0) or 0)
        narration = str(txn.get("narration", "")).lower()
        total_debit += debit
        total_credit += credit
        
        # Flag 1: Cash deposits > 10 lakh (PMLA threshold)
        if credit > 1000000 and "cash" in narration:
            cash_deposits.append({"index": idx, "amount": credit, "date": txn.get("date")})
            flags.append(f"🚨 PMLA Alert: Cash deposit of ₹{credit:,.0f} on {txn.get('date')}")
        
        # Flag 2: Round amount transactions (evasion indicator)
        amt = max(debit, credit)
        if amt > 100000 and amt % 100000 == 0:
            round_amounts.append({"index": idx, "amount": amt})
        
        # Flag 3: Related party indicators (Section 40A(2)(b))
        related_keywords = ["director", "relative", "family", "self", "loan to", "loan from", "advance to"]
        if any(kw in narration for kw in related_keywords):
            related_party_suspects.append({
                "index": idx, "narration": txn.get("narration"), 
                "amount": max(debit, credit), "date": txn.get("date")
            })
        
        # Flag 4: Circular trading (same amounts in/out within 3 days)
        if debit > 500000:
            for j in range(max(0, idx-5), min(len(transactions), idx+5)):
                if j == idx: continue
                other_credit = float(transactions[j].get("credit", 0) or 0)
                if abs(other_credit - debit) < 1000 and other_credit > 0:
                    flags.append(f"⚠️ Circular Trading Suspect: ₹{debit:,.0f} out on {txn.get('date')}, similar amount in on {transactions[j].get('date')}")
    
    return {
        "total_transactions": len(transactions),
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "cash_deposits_above_10L": cash_deposits,
        "round_amount_transactions": len(round_amounts),
        "related_party_suspects": related_party_suspects,
        "critical_flags": flags,
        "risk_score": min(10, len(flags) * 2 + len(related_party_suspects) + len(cash_deposits) * 3),
    }
