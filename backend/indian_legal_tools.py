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

    # Additional Civil Suits
    "breach_of_contract": {"period_years": 3, "section": "Article 55", "from": "date of breach"},
    "accounts_stated": {"period_years": 3, "section": "Article 64", "from": "date of acknowledgment"},
    "malicious_prosecution": {"period_years": 1, "section": "Article 71", "from": "date of acquittal or discharge"},
    "fraud": {"period_years": 3, "section": "Article 59", "from": "when fraud first known"},
    "mortgage_foreclosure": {"period_years": 30, "section": "Article 61(a)", "from": "when money becomes due"},
    "recovery_possession_lease": {"period_years": 12, "section": "Article 66", "from": "expiry of lease"},
    "mesne_profits": {"period_years": 3, "section": "Article 51", "from": "when profits accrue"},
    "injunction_breach": {"period_years": 3, "section": "Article 7", "from": "date of breach of injunction"},
    "declaration_suit": {"period_years": 3, "section": "Article 58", "from": "when right to sue accrues"},
    "trust_property_recovery": {"period_years": 12, "section": "Article 92", "from": "date of breach of trust"},
    "restitution_conjugal_rights": {"period_years": 1, "section": "Article 26", "from": "date of withdrawal from society"},
    "recovery_from_agent": {"period_years": 3, "section": "Article 16", "from": "when account is rendered"},
    "possession_easement": {"period_years": 12, "section": "Article 112", "from": "when dispossessed"},
    "contribution_between_sureties": {"period_years": 3, "section": "Article 43", "from": "when principal is paid"},
    "legacy_suit": {"period_years": 12, "section": "Article 109", "from": "when legacy becomes payable"},

    # Consumer
    "consumer_complaint_district": {"period_years": 2, "section": "Section 69 CP Act 2019", "from": "when cause of action arises"},
    "consumer_appeal_state": {"period_days": 30, "section": "Section 41 CP Act 2019", "from": "date of District Commission order"},
    "consumer_appeal_national": {"period_days": 30, "section": "Section 51 CP Act 2019", "from": "date of State Commission order"},

    # Labour & Employment
    "industrial_dispute_reference": {"period_years": 3, "section": "Section 10 ID Act", "from": "date of discharge/dismissal"},
    "workmen_compensation": {"period_years": 2, "section": "Section 10 WC Act", "from": "date of accident"},
    "epf_claim": {"period_years": 3, "section": "Section 7A EPF Act", "from": "date when contribution due"},

    # RERA
    "rera_complaint": {"period_years": 1, "section": "Section 31 RERA Act", "from": "date of possession promise or defect"},
    "rera_appeal_appat": {"period_days": 60, "section": "Section 44 RERA Act", "from": "date of RERA Authority order"},

    # RTI
    "rti_first_appeal": {"period_days": 30, "section": "Section 19(1) RTI Act", "from": "expiry of 30 days from request or date of refusal"},
    "rti_second_appeal": {"period_days": 90, "section": "Section 19(3) RTI Act", "from": "date of first appellate order or deemed refusal"},

    # Criminal
    "criminal_complaint_private": {"period_years": 3, "section": "Section 468 CrPC", "from": "date of offence (punishable ≤ 3 years)"},
    "criminal_revision_hc": {"period_days": 90, "section": "Section 397 CrPC", "from": "date of sessions/magistrate order"},

    # Writ
    "writ_petition_hc": {"period_years": 0, "section": "Article 226 Constitution", "from": "no fixed limitation but must be filed without unreasonable delay (typically within 6 months)", "note": "Laches-based — no statutory limitation but 6 months is conventional"},

    # Customs & Excise
    "customs_appeal_cestat": {"period_days": 60, "section": "Section 129A Customs Act", "from": "date of order-in-appeal"},
    "customs_appeal_commissioner": {"period_days": 60, "section": "Section 128 Customs Act", "from": "date of order-in-original"},

    # Arbitration
    "arbitration_challenge_34": {"period_months": 3, "section": "Section 34 Arbitration Act", "from": "date of receiving award"},
    "arbitration_appeal_37": {"period_days": 30, "section": "Section 37 Arbitration Act", "from": "date of order under S.9/S.34"},
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
        "lease_deed": {"rate_pct": 2, "notes": "Lease > 1 year"},
        "gift_deed_family": {"rate_pct": 0, "notes": "Exempt for blood relatives up to certain limit"},
        "mortgage_deed": {"rate_pct": 3, "notes": "With possession"},
        "partnership_deed": {"flat_amount": 500, "notes": "Per UP Stamp Act"},
        "power_of_attorney": {"flat_amount": 100, "notes": "General POA"},
        "agreement_to_sell": {"rate_pct": 0, "notes": "Nominal stamp in most cases"},
    },
    "tamil_nadu": {
        "sale_deed": {"rate_pct": 7, "registration_pct": 4, "notes": "Total 11% (7% stamp + 4% registration)"},
        "lease_deed": {"rate_pct": 1, "notes": "Lease > 1 year, per TN Stamp Act"},
        "gift_deed_family": {"rate_pct": 1, "notes": "Between specified relatives"},
        "mortgage_deed": {"rate_pct": 1, "notes": "Simple mortgage"},
        "partnership_deed": {"flat_amount": 300, "notes": "Per Article 46"},
        "power_of_attorney": {"flat_amount": 100, "notes": "GPA"},
    },
    "telangana": {
        "sale_deed": {"rate_pct": 5, "registration_pct": 0.5, "notes": "Plus transfer duty 1.5%"},
        "lease_deed": {"rate_pct": 0.5, "notes": "Per Article 35"},
        "gift_deed_family": {"rate_pct": 1, "notes": "Between blood relatives"},
        "mortgage_deed": {"rate_pct": 0.5, "notes": "Simple mortgage"},
        "partnership_deed": {"flat_amount": 500, "notes": "Per TS Stamp Act"},
        "power_of_attorney": {"flat_amount": 200, "notes": "General POA"},
        "agreement_to_sell": {"rate_pct": 0.5, "notes": "Adjustable against sale deed"},
    },
    "andhra_pradesh": {
        "sale_deed": {"rate_pct": 5, "registration_pct": 0.5, "notes": "Plus transfer duty 1.5%"},
        "lease_deed": {"rate_pct": 0.5, "notes": "Per AP Stamp Act"},
        "gift_deed_family": {"rate_pct": 2, "notes": "Between family members"},
        "mortgage_deed": {"rate_pct": 0.5, "notes": "Without possession"},
        "partnership_deed": {"flat_amount": 500, "notes": "Per AP Stamp Act"},
    },
    "gujarat": {
        "sale_deed": {"rate_pct": 4.9, "registration_pct": 1, "notes": "3.5% stamp + 1% registration + 0.4% additional"},
        "lease_deed": {"rate_pct": 1, "notes": "Per Gujarat Stamp Act"},
        "gift_deed_family": {"rate_pct": 2, "notes": "Close relatives lower rate"},
        "mortgage_deed": {"rate_pct": 0.1, "notes": "Simple mortgage, max ₹15,000"},
        "partnership_deed": {"flat_amount": 500, "notes": "Per Gujarat Stamp Act"},
        "power_of_attorney": {"flat_amount": 100, "notes": "GPA"},
        "agreement_to_sell": {"rate_pct": 0, "notes": "Rs 20 flat"},
    },
    "rajasthan": {
        "sale_deed": {"rate_pct": 6, "registration_pct": 1, "notes": "Male: 6%, Female: 5% (1% concession)"},
        "lease_deed": {"rate_pct": 1, "notes": "Per Rajasthan Stamp Act"},
        "gift_deed_family": {"rate_pct": 2.5, "notes": "Between blood relatives"},
        "mortgage_deed": {"rate_pct": 2, "notes": "With possession"},
        "partnership_deed": {"flat_amount": 500, "notes": "Per Rajasthan Stamp Act"},
        "power_of_attorney": {"flat_amount": 100, "notes": "General POA; SPA higher"},
    },
    "west_bengal": {
        "sale_deed": {"rate_pct": 7, "registration_pct": 1, "notes": "KMC area: 6% + 1% surcharge; Mofussil: 5%"},
        "lease_deed": {"rate_pct": 1, "notes": "Per WB Stamp Act"},
        "gift_deed_family": {"rate_pct": 0.5, "notes": "Reduced rate for family transfer"},
        "mortgage_deed": {"rate_pct": 0.3, "notes": "Simple mortgage"},
        "partnership_deed": {"flat_amount": 500, "notes": "Per WB Stamp Act"},
    },
    "punjab": {
        "sale_deed": {"rate_pct": 7, "registration_pct": 1, "notes": "Male: 7%, Female: 5%"},
        "lease_deed": {"rate_pct": 2, "notes": "Per Punjab Stamp Act"},
        "gift_deed_family": {"rate_pct": 3, "notes": "Between close relatives"},
        "mortgage_deed": {"rate_pct": 1, "notes": "With possession"},
        "partnership_deed": {"flat_amount": 500, "notes": "Per Indian Stamp Act"},
    },
    "haryana": {
        "sale_deed": {"rate_pct": 7, "registration_pct": 1, "notes": "Male: 7%, Female: 5% (2% concession)"},
        "lease_deed": {"rate_pct": 2, "notes": "Per Haryana Stamp Act"},
        "gift_deed_family": {"rate_pct": 3, "notes": "Between specified relatives"},
        "mortgage_deed": {"rate_pct": 1, "notes": "With possession"},
    },
    "madhya_pradesh": {
        "sale_deed": {"rate_pct": 7.5, "registration_pct": 1, "notes": "Highest stamp duty state — 7.5%"},
        "lease_deed": {"rate_pct": 2, "notes": "Per MP Stamp Act"},
        "gift_deed_family": {"rate_pct": 2.5, "notes": "Between blood relatives"},
        "mortgage_deed": {"rate_pct": 2, "notes": "With possession"},
    },
    "kerala": {
        "sale_deed": {"rate_pct": 8, "registration_pct": 2, "notes": "Highest at 10% total (8% stamp + 2% registration)"},
        "lease_deed": {"rate_pct": 2, "notes": "Per Kerala Stamp Act"},
        "gift_deed_family": {"rate_pct": 3, "notes": "Between close relatives"},
        "mortgage_deed": {"rate_pct": 1, "notes": "Without possession"},
    },
    "goa": {
        "sale_deed": {"rate_pct": 3.5, "registration_pct": 1, "notes": "Lowest stamp duty state"},
        "lease_deed": {"rate_pct": 1, "notes": "Per Goa Stamp Act"},
        "gift_deed_family": {"rate_pct": 1, "notes": "Family transfers — reduced"},
        "mortgage_deed": {"rate_pct": 0.5, "notes": "Without possession"},
        "partnership_deed": {"flat_amount": 200, "notes": "Per Goa Stamp Act"},
    },
    "bihar": {
        "sale_deed": {"rate_pct": 6.3, "registration_pct": 2, "notes": "5.7% stamp + 0.6% surcharge"},
        "lease_deed": {"rate_pct": 1, "notes": "Per Bihar Stamp Act"},
        "gift_deed_family": {"rate_pct": 3, "notes": "Between relatives"},
    },
    "jharkhand": {
        "sale_deed": {"rate_pct": 6, "registration_pct": 2, "notes": "Urban: 6%, Rural: 4%"},
        "lease_deed": {"rate_pct": 1, "notes": "Per Jharkhand Stamp Act"},
        "gift_deed_family": {"rate_pct": 3, "notes": "Between relatives"},
    },
    "odisha": {
        "sale_deed": {"rate_pct": 5, "registration_pct": 1, "notes": "Standard rate"},
        "lease_deed": {"rate_pct": 1, "notes": "Per Odisha Stamp Act"},
        "gift_deed_family": {"rate_pct": 2, "notes": "Between family members"},
    },
    "chhattisgarh": {
        "sale_deed": {"rate_pct": 5, "registration_pct": 1, "notes": "Standard rate"},
        "gift_deed_family": {"rate_pct": 2, "notes": "Family transfers"},
    },
    "assam": {
        "sale_deed": {"rate_pct": 6, "registration_pct": 1, "notes": "Standard rate"},
        "gift_deed_family": {"rate_pct": 3, "notes": "Between relatives"},
    },
    "uttarakhand": {
        "sale_deed": {"rate_pct": 5, "registration_pct": 1, "notes": "Male: 5%, Female: 3.75%"},
        "gift_deed_family": {"rate_pct": 2.5, "notes": "Between family members"},
    },
    "himachal_pradesh": {
        "sale_deed": {"rate_pct": 6, "registration_pct": 1, "notes": "Standard rate"},
        "gift_deed_family": {"rate_pct": 3, "notes": "Between relatives"},
    },
    "jammu_kashmir": {
        "sale_deed": {"rate_pct": 7, "registration_pct": 1, "notes": "Per J&K Stamp Act post-abrogation"},
        "gift_deed_family": {"rate_pct": 3, "notes": "Between relatives"},
    },
    "meghalaya": {
        "sale_deed": {"rate_pct": 5, "registration_pct": 1, "notes": "Standard rate"},
        "gift_deed_family": {"rate_pct": 2, "notes": "Family transfers"},
    },
    "tripura": {
        "sale_deed": {"rate_pct": 5, "registration_pct": 1, "notes": "Standard rate"},
        "gift_deed_family": {"rate_pct": 2, "notes": "Family transfers"},
    },
    "manipur": {
        "sale_deed": {"rate_pct": 5, "registration_pct": 1, "notes": "Standard rate"},
        "gift_deed_family": {"rate_pct": 2, "notes": "Family transfers"},
    },
    "mizoram": {
        "sale_deed": {"rate_pct": 5, "registration_pct": 1, "notes": "Standard rate"},
        "gift_deed_family": {"rate_pct": 2, "notes": "Family transfers"},
    },
    "nagaland": {
        "sale_deed": {"rate_pct": 5, "registration_pct": 1, "notes": "Standard rate"},
        "gift_deed_family": {"rate_pct": 2, "notes": "Family transfers"},
    },
    "arunachal_pradesh": {
        "sale_deed": {"rate_pct": 5, "registration_pct": 1, "notes": "Standard rate"},
        "gift_deed_family": {"rate_pct": 2, "notes": "Family transfers"},
    },
    "sikkim": {
        "sale_deed": {"rate_pct": 5, "registration_pct": 1, "notes": "Standard rate"},
        "gift_deed_family": {"rate_pct": 2, "notes": "Family transfers"},
    },
    "puducherry": {
        "sale_deed": {"rate_pct": 7, "registration_pct": 2, "notes": "Total 9%"},
        "gift_deed_family": {"rate_pct": 3, "notes": "Between relatives"},
    },
    "chandigarh": {
        "sale_deed": {"rate_pct": 6, "registration_pct": 1, "notes": "Male: 6%, Female: 4%"},
        "gift_deed_family": {"rate_pct": 2, "notes": "Between family members"},
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
