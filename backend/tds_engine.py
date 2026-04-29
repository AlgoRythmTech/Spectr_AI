"""
TDS/TCS Compliance Engine -- Complete Indian withholding tax system.
Covers: All TDS sections, rate master, calculators, Form 26Q/24Q/27Q
generation, deposit tracking, 26AS reconciliation, and TCS rates.
All financial calculations use Decimal for precision.
"""
import logging
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)

# =====================================================================
# CONSTANTS
# =====================================================================

ZERO = Decimal("0")
ONE_PERCENT = Decimal("0.01")
TWO_PERCENT = Decimal("0.02")
FIVE_PERCENT = Decimal("0.05")
TEN_PERCENT = Decimal("0.10")
TWENTY_PERCENT = Decimal("0.20")
THIRTY_PERCENT = Decimal("0.30")

PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
BSR_CODE_REGEX = re.compile(r"^\d{7}$")
TAN_REGEX = re.compile(r"^[A-Z]{4}\d{5}[A-Z]$")

# Interest rates for late deduction / deposit (per month)
INTEREST_LATE_DEDUCTION = Decimal("0.01")   # 1% p.m. under Section 201(1A)(i)
INTEREST_LATE_DEPOSIT = Decimal("0.015")    # 1.5% p.m. under Section 201(1A)(ii)

# Section 206AA -- higher rate when PAN not available
NO_PAN_RATE = Decimal("0.20")

# =====================================================================
# ENUMS
# =====================================================================


class PayeeType(Enum):
    INDIVIDUAL = "individual"
    HUF = "huf"
    COMPANY = "company"
    FIRM = "firm"
    AOP = "aop"
    LLP = "llp"
    TRUST = "trust"
    OTHER = "other"


class ResidencyStatus(Enum):
    RESIDENT = "resident"
    NON_RESIDENT = "non_resident"
    NOT_ORDINARILY_RESIDENT = "not_ordinarily_resident"


class Quarter(Enum):
    Q1 = "Q1"  # Apr-Jun
    Q2 = "Q2"  # Jul-Sep
    Q3 = "Q3"  # Oct-Dec
    Q4 = "Q4"  # Jan-Mar


# =====================================================================
# TDS RATE MASTER -- All sections with rates, thresholds, descriptions
# =====================================================================

TDS_RATE_MASTER = {
    "192": {
        "description": "Salary",
        "rate_individual": None,  # Slab-based
        "rate_others": None,
        "threshold": ZERO,
        "threshold_type": "per_annum",
        "notes": "TDS on salary computed at average rate of income tax on estimated income",
        "is_slab_based": True,
    },
    "193": {
        "description": "Interest on securities",
        "rate_individual": TEN_PERCENT,
        "rate_others": TEN_PERCENT,
        "threshold": Decimal("10000"),
        "threshold_type": "per_annum",
        "notes": "Debentures, govt securities (not 8% Savings Bonds for resident individuals)",
    },
    "194": {
        "description": "Dividends",
        "rate_individual": TEN_PERCENT,
        "rate_others": TEN_PERCENT,
        "threshold": Decimal("5000"),
        "threshold_type": "per_annum",
        "notes": "Dividend by Indian company to resident shareholders",
    },
    "194A": {
        "description": "Interest other than on securities",
        "rate_individual": TEN_PERCENT,
        "rate_others": TEN_PERCENT,
        "threshold": Decimal("40000"),   # 50000 for senior citizens
        "threshold_senior": Decimal("50000"),
        "threshold_type": "per_annum",
        "notes": "FD interest, recurring deposit interest from banks/co-ops/post office",
    },
    "194B": {
        "description": "Winnings from lottery, crossword puzzle",
        "rate_individual": THIRTY_PERCENT,
        "rate_others": THIRTY_PERCENT,
        "threshold": Decimal("10000"),
        "threshold_type": "per_transaction",
        "notes": "Includes online gaming winnings",
    },
    "194BB": {
        "description": "Winnings from horse race",
        "rate_individual": THIRTY_PERCENT,
        "rate_others": THIRTY_PERCENT,
        "threshold": Decimal("10000"),
        "threshold_type": "per_annum",
        "notes": "Aggregate winnings during the FY",
    },
    "194C": {
        "description": "Payment to contractor/sub-contractor",
        "rate_individual": ONE_PERCENT,
        "rate_others": TWO_PERCENT,
        "threshold": Decimal("30000"),
        "threshold_aggregate": Decimal("100000"),
        "threshold_type": "single_and_aggregate",
        "notes": "1% for individual/HUF, 2% for others. Single payment >30K or aggregate >1L in FY",
    },
    "194D": {
        "description": "Insurance commission",
        "rate_individual": FIVE_PERCENT,
        "rate_others": TEN_PERCENT,
        "threshold": Decimal("15000"),
        "threshold_type": "per_annum",
        "notes": "Commission/remuneration for procuring insurance business",
    },
    "194DA": {
        "description": "Life insurance policy maturity proceeds",
        "rate_individual": FIVE_PERCENT,
        "rate_others": FIVE_PERCENT,
        "threshold": Decimal("100000"),
        "threshold_type": "per_annum",
        "notes": "On income component only (not entire sum assured)",
    },
    "194E": {
        "description": "Payment to non-resident sportsmen or sports association",
        "rate_individual": TWENTY_PERCENT,
        "rate_others": TWENTY_PERCENT,
        "threshold": ZERO,
        "threshold_type": "per_transaction",
        "notes": "No threshold. Applies to NRI sportsmen, entertainers, sports associations",
    },
    "194EE": {
        "description": "Payment in respect of NSS deposits",
        "rate_individual": TEN_PERCENT,
        "rate_others": TEN_PERCENT,
        "threshold": Decimal("2500"),
        "threshold_type": "per_annum",
        "notes": "National Savings Scheme withdrawal",
    },
    "194F": {
        "description": "Repurchase of units by MF or UTI",
        "rate_individual": TWENTY_PERCENT,
        "rate_others": TWENTY_PERCENT,
        "threshold": ZERO,
        "threshold_type": "per_transaction",
        "notes": "Repurchase of units from unit holder",
    },
    "194G": {
        "description": "Commission on sale of lottery tickets",
        "rate_individual": FIVE_PERCENT,
        "rate_others": FIVE_PERCENT,
        "threshold": Decimal("15000"),
        "threshold_type": "per_annum",
        "notes": "Stocking, distributing, purchasing, selling lottery tickets",
    },
    "194H": {
        "description": "Commission or brokerage",
        "rate_individual": FIVE_PERCENT,
        "rate_others": FIVE_PERCENT,
        "threshold": Decimal("15000"),
        "threshold_type": "per_annum",
        "notes": "Excludes insurance commission (covered under 194D)",
    },
    "194I_PM": {
        "description": "Rent -- Plant and machinery",
        "rate_individual": TWO_PERCENT,
        "rate_others": TWO_PERCENT,
        "threshold": Decimal("240000"),
        "threshold_type": "per_annum",
        "notes": "Rent on plant, machinery, equipment",
    },
    "194I_LBF": {
        "description": "Rent -- Land, building, furniture, fittings",
        "rate_individual": TEN_PERCENT,
        "rate_others": TEN_PERCENT,
        "threshold": Decimal("240000"),
        "threshold_type": "per_annum",
        "notes": "Rent on land, building, furniture, fittings",
    },
    "194IA": {
        "description": "Transfer of immovable property (other than agricultural land)",
        "rate_individual": ONE_PERCENT,
        "rate_others": ONE_PERCENT,
        "threshold": Decimal("5000000"),
        "threshold_type": "per_transaction",
        "notes": "Buyer to deduct TDS. Consideration >= 50 lakhs",
    },
    "194IB": {
        "description": "Rent by individual/HUF not liable to audit",
        "rate_individual": FIVE_PERCENT,
        "rate_others": FIVE_PERCENT,
        "threshold": Decimal("50000"),
        "threshold_type": "per_month",
        "notes": "Individual/HUF paying rent > 50K/month, not covered under 194I",
    },
    "194IC": {
        "description": "Payment under Joint Development Agreement",
        "rate_individual": TEN_PERCENT,
        "rate_others": TEN_PERCENT,
        "threshold": ZERO,
        "threshold_type": "per_transaction",
        "notes": "Consideration (not in kind) under specified agreement for land/building development",
    },
    "194J_TECH": {
        "description": "Fees for technical services / royalty (call centre included)",
        "rate_individual": TWO_PERCENT,
        "rate_others": TWO_PERCENT,
        "threshold": Decimal("30000"),
        "threshold_type": "per_annum",
        "notes": "Technical services, royalty, call centre. 2% rate",
    },
    "194J_PROF": {
        "description": "Professional fees / director fees / non-compete fees",
        "rate_individual": TEN_PERCENT,
        "rate_others": TEN_PERCENT,
        "threshold": Decimal("30000"),
        "threshold_type": "per_annum",
        "notes": "Professional services, director sitting fees, non-compete consideration. 10% rate",
    },
    "194K": {
        "description": "Income from units of mutual fund",
        "rate_individual": TEN_PERCENT,
        "rate_others": TEN_PERCENT,
        "threshold": Decimal("5000"),
        "threshold_type": "per_annum",
        "notes": "Dividend/income from MF, UTI units to resident",
    },
    "194LA": {
        "description": "Compensation on compulsory acquisition of immovable property",
        "rate_individual": TEN_PERCENT,
        "rate_others": TEN_PERCENT,
        "threshold": Decimal("250000"),
        "threshold_type": "per_annum",
        "notes": "Enhanced compensation allowed. Threshold 2.5 lakhs",
    },
    "194LB": {
        "description": "Income from infrastructure debt fund (NR)",
        "rate_individual": FIVE_PERCENT,
        "rate_others": FIVE_PERCENT,
        "threshold": ZERO,
        "threshold_type": "per_transaction",
        "notes": "Interest payable to non-resident from infra debt fund",
    },
    "194LC": {
        "description": "Income from specified bonds/GDR (NR)",
        "rate_individual": FIVE_PERCENT,
        "rate_others": FIVE_PERCENT,
        "threshold": ZERO,
        "threshold_type": "per_transaction",
        "notes": "Interest on foreign currency bonds, GDRs to non-residents",
    },
    "194LD": {
        "description": "Interest on certain bonds and govt securities (FPI)",
        "rate_individual": FIVE_PERCENT,
        "rate_others": FIVE_PERCENT,
        "threshold": ZERO,
        "threshold_type": "per_transaction",
        "notes": "Interest to FPIs/QFIs on govt securities, rupee-denominated bonds",
    },
    "194M": {
        "description": "Commission/contractual payment by individual/HUF",
        "rate_individual": FIVE_PERCENT,
        "rate_others": FIVE_PERCENT,
        "threshold": Decimal("5000000"),
        "threshold_type": "per_annum",
        "notes": "Individual/HUF (not auditable) paying commission/brokerage/contractual to resident",
    },
    "194N": {
        "description": "Cash withdrawal from bank",
        "rate_individual": TWO_PERCENT,
        "rate_others": TWO_PERCENT,
        "threshold": Decimal("10000000"),
        "threshold_type": "per_annum",
        "rate_non_filer": FIVE_PERCENT,
        "threshold_non_filer": Decimal("2000000"),
        "notes": "2% on cash > 1Cr (filers), 5% on cash > 20L (non-filers)",
    },
    "194O": {
        "description": "Payment by e-commerce operator to participant",
        "rate_individual": ONE_PERCENT,
        "rate_others": ONE_PERCENT,
        "threshold": Decimal("500000"),
        "threshold_type": "per_annum",
        "notes": "E-commerce operator to deduct 1% from payment to e-commerce participant",
    },
    "194P": {
        "description": "TDS on senior citizen (75+) -- specified bank",
        "rate_individual": None,
        "rate_others": None,
        "threshold": ZERO,
        "threshold_type": "per_annum",
        "is_slab_based": True,
        "notes": "Specified bank to compute and deduct TDS for senior citizens 75+ with pension/interest income only",
    },
    "194Q": {
        "description": "Purchase of goods",
        "rate_individual": Decimal("0.001"),
        "rate_others": Decimal("0.001"),
        "threshold": Decimal("5000000"),
        "threshold_type": "per_annum",
        "notes": "Buyer (turnover > 10Cr) to deduct 0.1% on purchase > 50L from resident seller",
    },
    "194R": {
        "description": "Business perquisites/benefits",
        "rate_individual": TEN_PERCENT,
        "rate_others": TEN_PERCENT,
        "threshold": Decimal("20000"),
        "threshold_type": "per_annum",
        "notes": "Perquisite/benefit arising from business or profession",
    },
    "194S": {
        "description": "Payment for transfer of virtual digital assets",
        "rate_individual": ONE_PERCENT,
        "rate_others": ONE_PERCENT,
        "threshold": Decimal("50000"),
        "threshold_type": "per_annum",
        "threshold_specified": Decimal("10000"),
        "notes": "50K for specified persons, 10K for others. Crypto/NFT transactions",
    },
}


# =====================================================================
# TCS RATE MASTER -- Section 206C
# =====================================================================

TCS_RATE_MASTER = {
    "206C_SCRAP": {
        "description": "Sale of scrap",
        "rate": ONE_PERCENT,
        "threshold": ZERO,
        "notes": "Scrap means waste/scrap from manufacture/mechanical working of materials",
    },
    "206C_TENDU": {
        "description": "Sale of tendu leaves",
        "rate": FIVE_PERCENT,
        "threshold": ZERO,
        "notes": "Tendu leaves used for bidi manufacturing",
    },
    "206C_TIMBER": {
        "description": "Sale of timber obtained by forest lease",
        "rate": Decimal("0.025"),
        "threshold": ZERO,
        "notes": "Timber obtained under forest lease",
    },
    "206C_FOREST": {
        "description": "Sale of any other forest produce (not timber/tendu)",
        "rate": Decimal("0.025"),
        "threshold": ZERO,
        "notes": "Forest produce other than timber and tendu leaves",
    },
    "206C_MINERALS": {
        "description": "Sale of minerals (coal, iron ore, etc.)",
        "rate": ONE_PERCENT,
        "threshold": ZERO,
        "notes": "Coal, lignite, iron ore, and other minerals",
    },
    "206C_MOTOR_VEHICLE": {
        "description": "Sale of motor vehicle exceeding 10 lakhs",
        "rate": ONE_PERCENT,
        "threshold": Decimal("1000000"),
        "notes": "Motor vehicle value exceeding 10 lakhs",
    },
    "206C_PARKING_LOT": {
        "description": "Toll plaza / parking lot",
        "rate": TWO_PERCENT,
        "threshold": ZERO,
        "notes": "Toll plaza, mining, quarrying lease/licence/contract",
    },
    "206C_OVERSEAS_REMITTANCE": {
        "description": "Foreign remittance under LRS",
        "rate": FIVE_PERCENT,
        "threshold": Decimal("700000"),
        "notes": "5% on remittance > 7L under LRS (0.5% for education loan). 20% above 7L for non-education/medical",
        "rate_education_loan": Decimal("0.005"),
        "rate_above_threshold_general": TWENTY_PERCENT,
    },
    "206C_FOREIGN_TOUR": {
        "description": "Foreign tour package",
        "rate": FIVE_PERCENT,
        "threshold": ZERO,
        "notes": "TCS on sale of overseas tour package by tour operator",
        "rate_above_7l": TWENTY_PERCENT,
    },
    "206C_SALE_OF_GOODS": {
        "description": "Sale of goods (residual)",
        "rate": Decimal("0.001"),
        "threshold": Decimal("5000000"),
        "notes": "Seller (turnover > 10Cr) to collect 0.1% on sale > 50L",
    },
}


# =====================================================================
# INCOME TAX SLAB RATES (AY 2025-26, New Regime)
# =====================================================================

INCOME_TAX_SLABS_NEW_REGIME = [
    (Decimal("0"),       Decimal("300000"),   ZERO),
    (Decimal("300000"),  Decimal("700000"),   FIVE_PERCENT),
    (Decimal("700000"),  Decimal("1000000"),  TEN_PERCENT),
    (Decimal("1000000"), Decimal("1200000"),  Decimal("0.15")),
    (Decimal("1200000"), Decimal("1500000"),  TWENTY_PERCENT),
    (Decimal("1500000"), Decimal("99999999999"), THIRTY_PERCENT),
]

INCOME_TAX_SLABS_OLD_REGIME = [
    (Decimal("0"),       Decimal("250000"),   ZERO),
    (Decimal("250000"),  Decimal("500000"),   FIVE_PERCENT),
    (Decimal("500000"),  Decimal("1000000"),  TWENTY_PERCENT),
    (Decimal("1000000"), Decimal("99999999999"), THIRTY_PERCENT),
]

STANDARD_DEDUCTION_SALARY = Decimal("75000")   # New regime from FY 2024-25
REBATE_THRESHOLD_NEW_REGIME = Decimal("700000")  # u/s 87A
REBATE_AMOUNT_NEW_REGIME = Decimal("25000")

CESS_RATE = Decimal("0.04")  # 4% Health & Education Cess

# DTAA rates for common countries (for 27Q)
DTAA_RATES = {
    "US": {"interest": TEN_PERCENT, "dividend": Decimal("0.15"), "royalty": TEN_PERCENT, "fts": TEN_PERCENT},
    "UK": {"interest": TEN_PERCENT, "dividend": TEN_PERCENT, "royalty": TEN_PERCENT, "fts": TEN_PERCENT},
    "Singapore": {"interest": TEN_PERCENT, "dividend": TEN_PERCENT, "royalty": TEN_PERCENT, "fts": TEN_PERCENT},
    "UAE": {"interest": Decimal("0.125"), "dividend": TEN_PERCENT, "royalty": TEN_PERCENT, "fts": TEN_PERCENT},
    "Mauritius": {"interest": Decimal("0.075"), "dividend": FIVE_PERCENT, "royalty": Decimal("0.15"), "fts": TEN_PERCENT},
    "Germany": {"interest": TEN_PERCENT, "dividend": TEN_PERCENT, "royalty": TEN_PERCENT, "fts": TEN_PERCENT},
    "Japan": {"interest": TEN_PERCENT, "dividend": TEN_PERCENT, "royalty": TEN_PERCENT, "fts": TEN_PERCENT},
    "Canada": {"interest": Decimal("0.15"), "dividend": Decimal("0.15"), "royalty": TEN_PERCENT, "fts": Decimal("0.15")},
    "Australia": {"interest": Decimal("0.15"), "dividend": Decimal("0.15"), "royalty": TEN_PERCENT, "fts": TEN_PERCENT},
    "Netherlands": {"interest": TEN_PERCENT, "dividend": TEN_PERCENT, "royalty": TEN_PERCENT, "fts": TEN_PERCENT},
    "France": {"interest": TEN_PERCENT, "dividend": TEN_PERCENT, "royalty": TEN_PERCENT, "fts": TEN_PERCENT},
    "China": {"interest": TEN_PERCENT, "dividend": TEN_PERCENT, "royalty": TEN_PERCENT, "fts": TEN_PERCENT},
}


# =====================================================================
# VALIDATION HELPERS
# =====================================================================

def validate_pan(pan: str) -> dict:
    """Validate PAN format and extract entity type."""
    if not pan or not isinstance(pan, str):
        return {"valid": False, "error": "PAN is required"}
    pan = pan.upper().strip()
    if not PAN_REGEX.match(pan):
        return {"valid": False, "error": f"Invalid PAN format: {pan}. Expected: AAAAA9999A"}
    fourth_char = pan[3]
    entity_map = {
        "P": "Individual", "C": "Company", "H": "HUF", "F": "Firm",
        "A": "AOP/BOI", "T": "Trust", "B": "BOI", "L": "Local Authority",
        "J": "Artificial Juridical Person", "G": "Government",
    }
    entity_type = entity_map.get(fourth_char, "Unknown")
    return {"valid": True, "pan": pan, "entity_type": entity_type}


def validate_tan(tan: str) -> dict:
    """Validate TAN format."""
    if not tan or not isinstance(tan, str):
        return {"valid": False, "error": "TAN is required"}
    tan = tan.upper().strip()
    if not TAN_REGEX.match(tan):
        return {"valid": False, "error": f"Invalid TAN format: {tan}. Expected: AAAA99999A"}
    return {"valid": True, "tan": tan}


def validate_bsr_code(bsr: str) -> dict:
    """Validate BSR code (7-digit bank branch code)."""
    if not bsr or not isinstance(bsr, str):
        return {"valid": False, "error": "BSR code is required"}
    bsr = bsr.strip()
    if not BSR_CODE_REGEX.match(bsr):
        return {"valid": False, "error": f"Invalid BSR code: {bsr}. Must be 7 digits"}
    return {"valid": True, "bsr_code": bsr}


def _to_decimal(value) -> Decimal:
    """Safely convert to Decimal."""
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"Cannot convert {value!r} to Decimal")


def _round_tds(amount: Decimal) -> Decimal:
    """Round TDS to nearest rupee (no paise in TDS)."""
    return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _get_financial_year(d: date) -> str:
    """Return FY string like '2024-25' for a given date."""
    if d.month >= 4:
        return f"{d.year}-{str(d.year + 1)[-2:]}"
    return f"{d.year - 1}-{str(d.year)[-2:]}"


def _get_quarter(d: date) -> Quarter:
    """Return the quarter for a given date in Indian FY."""
    if d.month in (4, 5, 6):
        return Quarter.Q1
    elif d.month in (7, 8, 9):
        return Quarter.Q2
    elif d.month in (10, 11, 12):
        return Quarter.Q3
    else:
        return Quarter.Q4


# =====================================================================
# TDS CALCULATOR
# =====================================================================

def calculate_tds(
    section: str,
    payment_amount,
    payee_pan: str = "",
    payee_type: str = "individual",
    is_resident: bool = True,
    has_lower_deduction_cert: bool = False,
    certificate_rate=None,
    is_senior_citizen: bool = False,
    aggregate_paid_in_fy=None,
    is_non_filer_206ab: bool = False,
) -> dict:
    """
    Calculate TDS for a given payment.

    Args:
        section: TDS section code (e.g., '194C', '194J_PROF')
        payment_amount: Amount of payment (before TDS)
        payee_pan: PAN of the payee
        payee_type: 'individual', 'company', 'firm', 'huf', etc.
        is_resident: Whether the payee is an Indian resident
        has_lower_deduction_cert: Whether payee has Section 197 certificate
        certificate_rate: Rate specified in lower deduction certificate
        is_senior_citizen: For 194A higher threshold
        aggregate_paid_in_fy: Total amount already paid to this payee in the FY
        is_non_filer_206ab: Whether payee is a non-filer under Section 206AB

    Returns:
        dict with keys: section, payment_amount, tds_rate, tds_amount,
        effective_rate, threshold, threshold_exceeded, rate_basis, warnings
    """
    payment_amount = _to_decimal(payment_amount)
    warnings = []

    # Validate section
    if section not in TDS_RATE_MASTER:
        return {
            "error": f"Unknown TDS section: {section}",
            "valid_sections": sorted(TDS_RATE_MASTER.keys()),
        }

    section_info = TDS_RATE_MASTER[section]

    # Slab-based sections (192, 194P) -- cannot compute here
    if section_info.get("is_slab_based"):
        return {
            "error": f"Section {section} is slab-based. Use calculate_salary_tds() for Section 192.",
            "section": section,
            "description": section_info["description"],
        }

    # Validate PAN
    pan_result = validate_pan(payee_pan) if payee_pan else {"valid": False}
    has_valid_pan = pan_result.get("valid", False)
    if not has_valid_pan and payee_pan:
        warnings.append(f"Invalid PAN format: {payee_pan}")

    # Determine base rate
    payee_type_lower = payee_type.lower()
    is_individual_type = payee_type_lower in ("individual", "huf")

    if is_individual_type:
        base_rate = section_info["rate_individual"]
    else:
        base_rate = section_info["rate_others"]

    if base_rate is None:
        return {"error": f"Rate not defined for section {section} / payee type {payee_type}"}

    # Check threshold
    threshold = section_info["threshold"]
    threshold_type = section_info["threshold_type"]
    threshold_exceeded = True

    # Special threshold for senior citizen under 194A
    if section == "194A" and is_senior_citizen:
        threshold = section_info.get("threshold_senior", threshold)

    if threshold > ZERO:
        if threshold_type == "per_annum":
            check_amount = (aggregate_paid_in_fy or ZERO) + payment_amount
            if check_amount <= threshold:
                threshold_exceeded = False
        elif threshold_type == "per_month":
            if payment_amount <= threshold:
                threshold_exceeded = False
        elif threshold_type == "per_transaction":
            if payment_amount < threshold:
                threshold_exceeded = False
        elif threshold_type == "single_and_aggregate":
            single_threshold = threshold
            aggregate_threshold = section_info.get("threshold_aggregate", threshold)
            agg_amount = (aggregate_paid_in_fy or ZERO) + payment_amount
            if payment_amount < single_threshold and agg_amount < aggregate_threshold:
                threshold_exceeded = False

    # Determine effective rate
    effective_rate = base_rate
    rate_basis = f"Section {section} base rate"

    # Section 206AA: No PAN -> 20% or section rate, whichever is higher
    if not has_valid_pan:
        if NO_PAN_RATE > effective_rate:
            effective_rate = NO_PAN_RATE
            rate_basis = "Section 206AA (no PAN) -- 20%"
        warnings.append("No valid PAN: Section 206AA higher rate may apply")

    # Section 206AB: Non-filer -> twice the rate or 5%, whichever higher
    if is_non_filer_206ab and has_valid_pan:
        rate_206ab = max(base_rate * 2, FIVE_PERCENT)
        if rate_206ab > effective_rate:
            effective_rate = rate_206ab
            rate_basis = f"Section 206AB (non-filer) -- {rate_206ab * 100}%"
        warnings.append(f"Non-filer under Section 206AB: rate {rate_206ab * 100}%")

    # Lower deduction certificate (Section 197)
    if has_lower_deduction_cert and certificate_rate is not None:
        cert_rate = _to_decimal(certificate_rate)
        if cert_rate < effective_rate:
            effective_rate = cert_rate
            rate_basis = f"Section 197 certificate -- {cert_rate * 100}%"
            warnings = [w for w in warnings if "206AA" not in w and "206AB" not in w]
            warnings.append(f"Lower deduction certificate applied: {cert_rate * 100}%")

    # Compute TDS amount
    if threshold_exceeded:
        tds_amount = _round_tds(payment_amount * effective_rate)
    else:
        tds_amount = ZERO
        rate_basis = f"Below threshold ({threshold}). No TDS."

    return {
        "section": section,
        "description": section_info["description"],
        "payment_amount": str(payment_amount),
        "tds_rate": str(effective_rate),
        "tds_amount": str(tds_amount),
        "net_payment": str(payment_amount - tds_amount),
        "effective_rate_percent": str(effective_rate * 100),
        "threshold": str(threshold),
        "threshold_exceeded": threshold_exceeded,
        "rate_basis": rate_basis,
        "payee_type": payee_type,
        "has_valid_pan": has_valid_pan,
        "warnings": warnings,
    }


# =====================================================================
# SALARY TDS CALCULATOR (Section 192)
# =====================================================================

def calculate_salary_tds(
    gross_salary,
    hra_exempt=None,
    lta_exempt=None,
    standard_deduction=None,
    chapter_vi_a_deductions=None,
    regime: str = "new",
    employer_pf_contribution=None,
    professional_tax=None,
    other_income=None,
    tds_already_deducted=None,
    months_remaining: int = 12,
) -> dict:
    """
    Compute TDS on salary under Section 192.

    Args:
        gross_salary: Total gross salary for the FY
        hra_exempt: HRA exemption (old regime only)
        lta_exempt: LTA exemption (old regime only)
        standard_deduction: Override standard deduction (default 75000 new, 50000 old)
        chapter_vi_a_deductions: Dict of deductions {section: amount} (old regime only)
        regime: 'new' or 'old'
        employer_pf_contribution: Employer's PF contribution (for NPS u/s 80CCD(2))
        professional_tax: Professional tax paid
        other_income: Other income declared by employee (Form 12BB)
        tds_already_deducted: TDS already deducted in prior months
        months_remaining: Months remaining in FY for per-month TDS

    Returns:
        dict with full computation including per-month TDS
    """
    gross = _to_decimal(gross_salary)
    warnings = []

    # Build income computation
    computation = {
        "gross_salary": gross,
        "regime": regime,
    }

    net_taxable = gross

    # Exemptions (only in old regime)
    total_exemptions = ZERO
    if regime == "old":
        if hra_exempt:
            hra = _to_decimal(hra_exempt)
            total_exemptions += hra
            computation["hra_exemption"] = hra
        if lta_exempt:
            lta = _to_decimal(lta_exempt)
            total_exemptions += lta
            computation["lta_exemption"] = lta

    computation["total_exemptions"] = total_exemptions
    net_taxable -= total_exemptions

    # Standard deduction
    if standard_deduction is not None:
        std_ded = _to_decimal(standard_deduction)
    else:
        std_ded = STANDARD_DEDUCTION_SALARY if regime == "new" else Decimal("50000")
    computation["standard_deduction"] = std_ded
    net_taxable -= std_ded

    # Professional tax
    if professional_tax:
        pt = _to_decimal(professional_tax)
        computation["professional_tax"] = pt
        net_taxable -= pt

    # Employer PF (80CCD(2) -- available in both regimes)
    if employer_pf_contribution:
        epf = _to_decimal(employer_pf_contribution)
        computation["employer_pf_80ccd2"] = epf
        net_taxable -= epf

    # Chapter VI-A deductions (old regime only)
    total_vi_a = ZERO
    if regime == "old" and chapter_vi_a_deductions:
        vi_a_details = {}
        for sec, amt in chapter_vi_a_deductions.items():
            dec_amt = _to_decimal(amt)
            vi_a_details[sec] = dec_amt
            total_vi_a += dec_amt
        computation["chapter_vi_a"] = {k: str(v) for k, v in vi_a_details.items()}
    computation["total_vi_a_deductions"] = total_vi_a
    net_taxable -= total_vi_a

    # Other income
    if other_income:
        oi = _to_decimal(other_income)
        computation["other_income"] = oi
        net_taxable += oi

    if net_taxable < ZERO:
        net_taxable = ZERO
    computation["net_taxable_income"] = net_taxable

    # Tax computation
    slabs = INCOME_TAX_SLABS_NEW_REGIME if regime == "new" else INCOME_TAX_SLABS_OLD_REGIME

    tax = ZERO
    slab_breakup = []
    remaining = net_taxable
    for lower, upper, rate in slabs:
        if remaining <= ZERO:
            break
        slab_income = min(remaining, upper - lower)
        slab_tax = slab_income * rate
        slab_breakup.append({
            "range": f"{lower} - {upper}",
            "rate": str(rate * 100) + "%",
            "income_in_slab": str(slab_income),
            "tax": str(_round_tds(slab_tax)),
        })
        tax += slab_tax
        remaining -= slab_income

    computation["slab_breakup"] = slab_breakup
    computation["tax_before_rebate"] = str(_round_tds(tax))

    # Section 87A Rebate (new regime: taxable <= 7L, rebate up to 25K)
    rebate = ZERO
    if regime == "new" and net_taxable <= REBATE_THRESHOLD_NEW_REGIME:
        rebate = min(tax, REBATE_AMOUNT_NEW_REGIME)
    elif regime == "old" and net_taxable <= Decimal("500000"):
        rebate = min(tax, Decimal("12500"))
    tax -= rebate
    if tax < ZERO:
        tax = ZERO
    computation["rebate_87a"] = str(rebate)
    computation["tax_after_rebate"] = str(_round_tds(tax))

    # Surcharge
    surcharge = ZERO
    if net_taxable > Decimal("50000000"):
        surcharge = tax * Decimal("0.37")
    elif net_taxable > Decimal("20000000"):
        surcharge = tax * Decimal("0.25")
    elif net_taxable > Decimal("10000000"):
        surcharge = tax * Decimal("0.15")
    elif net_taxable > Decimal("5000000"):
        surcharge = tax * Decimal("0.10")
    computation["surcharge"] = str(_round_tds(surcharge))
    tax += surcharge

    # Cess
    cess = tax * CESS_RATE
    computation["cess_4_percent"] = str(_round_tds(cess))
    total_tax = _round_tds(tax + cess)
    computation["total_tax_liability"] = str(total_tax)

    # TDS already deducted
    tds_done = _to_decimal(tds_already_deducted) if tds_already_deducted else ZERO
    computation["tds_already_deducted"] = str(tds_done)
    remaining_tax = total_tax - tds_done
    if remaining_tax < ZERO:
        remaining_tax = ZERO
        warnings.append("TDS already deducted exceeds total tax liability -- refund scenario")
    computation["remaining_tax_for_fy"] = str(remaining_tax)

    # Per-month TDS
    if months_remaining > 0:
        per_month = _round_tds(remaining_tax / Decimal(str(months_remaining)))
    else:
        per_month = remaining_tax
    computation["tds_per_month"] = str(per_month)
    computation["months_remaining"] = months_remaining
    computation["warnings"] = warnings

    return computation


# =====================================================================
# FORM 26Q GENERATOR (Quarterly non-salary TDS return)
# =====================================================================

def generate_form_26q(
    deductor_tan: str,
    deductor_name: str,
    deductor_pan: str,
    financial_year: str,
    quarter: str,
    deductee_records: list,
    challan_details: list,
    responsible_person: dict = None,
) -> dict:
    """
    Generate Form 26Q (Non-salary quarterly TDS return) data.

    Args:
        deductor_tan: TAN of deductor
        deductor_name: Name of deductor
        deductor_pan: PAN of deductor
        financial_year: e.g., '2024-25'
        quarter: 'Q1', 'Q2', 'Q3', or 'Q4'
        deductee_records: List of dicts with keys:
            pan, name, section, payment_amount, tds_deducted, tds_deposited,
            date_of_payment, date_of_deduction, challan_ref
        challan_details: List of dicts with keys:
            bsr_code, challan_serial, date_of_deposit, amount,
            surcharge, cess, interest, fee_234e, total
        responsible_person: Dict with name, designation, pan, address

    Returns:
        dict with form data, validation errors, and summary
    """
    errors = []
    warnings = []

    # Validate TAN
    tan_result = validate_tan(deductor_tan)
    if not tan_result["valid"]:
        errors.append(tan_result["error"])

    # Validate deductor PAN
    pan_result = validate_pan(deductor_pan)
    if not pan_result["valid"]:
        errors.append(f"Deductor PAN invalid: {pan_result['error']}")

    # Validate quarter
    valid_quarters = {"Q1", "Q2", "Q3", "Q4"}
    if quarter not in valid_quarters:
        errors.append(f"Invalid quarter: {quarter}. Must be one of {valid_quarters}")

    # Validate and process deductee records
    processed_deductees = []
    total_tds_deducted = ZERO
    total_tds_deposited = ZERO
    total_payment = ZERO
    section_wise = {}

    for idx, rec in enumerate(deductee_records):
        rec_errors = []
        rec_num = idx + 1

        # Validate deductee PAN
        d_pan = rec.get("pan", "")
        d_pan_result = validate_pan(d_pan)
        if not d_pan_result["valid"]:
            rec_errors.append(f"Record {rec_num}: Invalid deductee PAN '{d_pan}'")

        # Validate section
        section = rec.get("section", "")
        if section not in TDS_RATE_MASTER:
            rec_errors.append(f"Record {rec_num}: Unknown section '{section}'")

        # Parse amounts
        try:
            payment = _to_decimal(rec.get("payment_amount", 0))
            tds_ded = _to_decimal(rec.get("tds_deducted", 0))
            tds_dep = _to_decimal(rec.get("tds_deposited", 0))
        except ValueError as e:
            rec_errors.append(f"Record {rec_num}: Invalid amount -- {e}")
            errors.extend(rec_errors)
            continue

        if tds_dep < tds_ded:
            warnings.append(
                f"Record {rec_num} ({d_pan}): TDS deposited ({tds_dep}) < deducted ({tds_ded}). "
                f"Shortfall: {tds_ded - tds_dep}"
            )

        total_tds_deducted += tds_ded
        total_tds_deposited += tds_dep
        total_payment += payment

        # Section-wise summary
        if section not in section_wise:
            section_wise[section] = {"count": 0, "payment": ZERO, "tds": ZERO}
        section_wise[section]["count"] += 1
        section_wise[section]["payment"] += payment
        section_wise[section]["tds"] += tds_ded

        processed_deductees.append({
            "sl_no": rec_num,
            "pan": d_pan.upper().strip() if d_pan else "PANNOTAVBL",
            "name": rec.get("name", ""),
            "section": section,
            "date_of_payment": rec.get("date_of_payment", ""),
            "date_of_deduction": rec.get("date_of_deduction", ""),
            "payment_amount": str(payment),
            "tds_deducted": str(tds_ded),
            "tds_deposited": str(tds_dep),
            "challan_ref": rec.get("challan_ref", ""),
            "errors": rec_errors,
        })

        errors.extend(rec_errors)

    # Validate challans
    processed_challans = []
    total_challan_amount = ZERO
    for idx, ch in enumerate(challan_details):
        ch_errors = []
        ch_num = idx + 1

        bsr = ch.get("bsr_code", "")
        bsr_result = validate_bsr_code(bsr)
        if not bsr_result["valid"]:
            ch_errors.append(f"Challan {ch_num}: {bsr_result['error']}")

        try:
            ch_amount = _to_decimal(ch.get("amount", 0))
            ch_total = _to_decimal(ch.get("total", ch.get("amount", 0)))
        except ValueError as e:
            ch_errors.append(f"Challan {ch_num}: Invalid amount -- {e}")
            errors.extend(ch_errors)
            continue

        total_challan_amount += ch_total

        processed_challans.append({
            "sl_no": ch_num,
            "bsr_code": bsr,
            "challan_serial": ch.get("challan_serial", ""),
            "date_of_deposit": ch.get("date_of_deposit", ""),
            "tds_amount": str(ch_amount),
            "surcharge": str(_to_decimal(ch.get("surcharge", 0))),
            "cess": str(_to_decimal(ch.get("cess", 0))),
            "interest": str(_to_decimal(ch.get("interest", 0))),
            "fee_234e": str(_to_decimal(ch.get("fee_234e", 0))),
            "total": str(ch_total),
            "errors": ch_errors,
        })
        errors.extend(ch_errors)

    # Cross-check: total deposited vs challan total
    if total_tds_deposited != total_challan_amount:
        warnings.append(
            f"Mismatch: Total TDS deposited in records ({total_tds_deposited}) "
            f"!= Total challan amount ({total_challan_amount})"
        )

    shortfall = total_tds_deducted - total_tds_deposited
    if shortfall > ZERO:
        warnings.append(f"TDS shortfall (deducted but not deposited): {shortfall}")

    # Section-wise summary with string amounts
    section_summary = {}
    for sec, data in section_wise.items():
        desc = TDS_RATE_MASTER.get(sec, {}).get("description", sec)
        section_summary[sec] = {
            "description": desc,
            "count": data["count"],
            "total_payment": str(data["payment"]),
            "total_tds": str(data["tds"]),
        }

    return {
        "form": "26Q",
        "form_type": "Non-salary TDS quarterly return",
        "deductor": {
            "tan": deductor_tan.upper().strip() if deductor_tan else "",
            "name": deductor_name,
            "pan": deductor_pan.upper().strip() if deductor_pan else "",
        },
        "financial_year": financial_year,
        "quarter": quarter,
        "responsible_person": responsible_person or {},
        "deductee_count": len(processed_deductees),
        "deductees": processed_deductees,
        "challans": processed_challans,
        "summary": {
            "total_payment": str(total_payment),
            "total_tds_deducted": str(total_tds_deducted),
            "total_tds_deposited": str(total_tds_deposited),
            "shortfall": str(shortfall) if shortfall > ZERO else "0",
            "total_challan_amount": str(total_challan_amount),
        },
        "section_wise_summary": section_summary,
        "validation_errors": errors,
        "warnings": warnings,
        "is_valid": len(errors) == 0,
    }


# =====================================================================
# FORM 24Q GENERATOR (Salary TDS quarterly return)
# =====================================================================

def generate_form_24q(
    deductor_tan: str,
    deductor_name: str,
    deductor_pan: str,
    financial_year: str,
    quarter: str,
    employee_records: list,
    challan_details: list,
    is_q4: bool = False,
) -> dict:
    """
    Generate Form 24Q (Salary TDS quarterly return) data.

    Args:
        deductor_tan: TAN of employer
        deductor_name: Name of employer
        deductor_pan: PAN of employer
        financial_year: e.g., '2024-25'
        quarter: 'Q1'-'Q4'
        employee_records: List of dicts -- each employee's quarterly data:
            pan, name, designation, gross_salary_quarter, tds_deducted_quarter,
            date_of_payment, date_of_deduction, challan_ref,
            (For Q4 Annexure II) full_year_salary_breakup: dict with fields like
            basic, hra, special_allowance, lta, other_allowances,
            value_of_perquisites, profit_in_lieu_salary, hra_exempt,
            lta_exempt, standard_deduction, professional_tax,
            chapter_vi_a (dict), regime
        challan_details: Same structure as 26Q
        is_q4: If True, generates Annexure II (employee-wise full-year breakup)

    Returns:
        dict with form data, Annexure I/II, validation errors, summary
    """
    errors = []
    warnings = []

    tan_result = validate_tan(deductor_tan)
    if not tan_result["valid"]:
        errors.append(tan_result["error"])

    # Annexure I: Quarter-wise deduction details (all quarters)
    annexure_i = []
    total_salary = ZERO
    total_tds = ZERO

    for idx, emp in enumerate(employee_records):
        rec_num = idx + 1
        d_pan = emp.get("pan", "")
        pan_check = validate_pan(d_pan)
        if not pan_check["valid"]:
            errors.append(f"Employee {rec_num}: Invalid PAN '{d_pan}'")

        try:
            salary_q = _to_decimal(emp.get("gross_salary_quarter", 0))
            tds_q = _to_decimal(emp.get("tds_deducted_quarter", 0))
        except ValueError as e:
            errors.append(f"Employee {rec_num}: Invalid amount -- {e}")
            continue

        total_salary += salary_q
        total_tds += tds_q

        annexure_i.append({
            "sl_no": rec_num,
            "pan": d_pan.upper().strip() if d_pan else "",
            "name": emp.get("name", ""),
            "designation": emp.get("designation", ""),
            "section": "192",
            "gross_salary_quarter": str(salary_q),
            "tds_deducted_quarter": str(tds_q),
            "date_of_payment": emp.get("date_of_payment", ""),
            "date_of_deduction": emp.get("date_of_deduction", ""),
            "challan_ref": emp.get("challan_ref", ""),
        })

    # Annexure II: Full-year salary breakup (only Q4)
    annexure_ii = []
    if is_q4 or quarter == "Q4":
        for idx, emp in enumerate(employee_records):
            breakup = emp.get("full_year_salary_breakup", {})
            if not breakup:
                warnings.append(f"Employee {idx+1} ({emp.get('name', '')}): No full-year breakup for Annexure II")
                continue

            # Compute using salary TDS calculator
            gross = _to_decimal(breakup.get("gross_salary", emp.get("gross_salary_quarter", 0)) or 0)
            computation = calculate_salary_tds(
                gross_salary=gross,
                hra_exempt=breakup.get("hra_exempt"),
                lta_exempt=breakup.get("lta_exempt"),
                standard_deduction=breakup.get("standard_deduction"),
                chapter_vi_a_deductions=breakup.get("chapter_vi_a"),
                regime=breakup.get("regime", "new"),
                employer_pf_contribution=breakup.get("employer_pf"),
                professional_tax=breakup.get("professional_tax"),
                other_income=breakup.get("other_income"),
                tds_already_deducted=breakup.get("tds_already_deducted"),
                months_remaining=0,
            )

            annexure_ii.append({
                "sl_no": idx + 1,
                "pan": emp.get("pan", "").upper().strip(),
                "name": emp.get("name", ""),
                "salary_breakup": {
                    "basic": str(_to_decimal(breakup.get("basic", 0) or 0)),
                    "hra": str(_to_decimal(breakup.get("hra", 0) or 0)),
                    "special_allowance": str(_to_decimal(breakup.get("special_allowance", 0) or 0)),
                    "lta": str(_to_decimal(breakup.get("lta", 0) or 0)),
                    "other_allowances": str(_to_decimal(breakup.get("other_allowances", 0) or 0)),
                    "perquisites": str(_to_decimal(breakup.get("value_of_perquisites", 0) or 0)),
                    "profit_in_lieu": str(_to_decimal(breakup.get("profit_in_lieu_salary", 0) or 0)),
                    "gross_salary": str(gross),
                },
                "computation": computation,
            })

    # Process challans (same as 26Q)
    processed_challans = []
    total_challan = ZERO
    for idx, ch in enumerate(challan_details):
        bsr = ch.get("bsr_code", "")
        bsr_result = validate_bsr_code(bsr)
        if not bsr_result["valid"]:
            errors.append(f"Challan {idx+1}: {bsr_result['error']}")

        try:
            ch_total = _to_decimal(ch.get("total", ch.get("amount", 0)))
        except ValueError:
            errors.append(f"Challan {idx+1}: Invalid amount")
            continue

        total_challan += ch_total
        processed_challans.append({
            "sl_no": idx + 1,
            "bsr_code": bsr,
            "challan_serial": ch.get("challan_serial", ""),
            "date_of_deposit": ch.get("date_of_deposit", ""),
            "total": str(ch_total),
        })

    return {
        "form": "24Q",
        "form_type": "Salary TDS quarterly return",
        "deductor": {
            "tan": deductor_tan.upper().strip() if deductor_tan else "",
            "name": deductor_name,
            "pan": deductor_pan.upper().strip() if deductor_pan else "",
        },
        "financial_year": financial_year,
        "quarter": quarter,
        "employee_count": len(annexure_i),
        "annexure_i": annexure_i,
        "annexure_ii": annexure_ii if annexure_ii else None,
        "challans": processed_challans,
        "summary": {
            "total_salary_paid": str(total_salary),
            "total_tds_deducted": str(total_tds),
            "total_challan_deposited": str(total_challan),
        },
        "validation_errors": errors,
        "warnings": warnings,
        "is_valid": len(errors) == 0,
    }


# =====================================================================
# FORM 27Q GENERATOR (NRI / foreign payment TDS return)
# =====================================================================

def generate_form_27q(
    deductor_tan: str,
    deductor_name: str,
    deductor_pan: str,
    financial_year: str,
    quarter: str,
    deductee_records: list,
    challan_details: list,
) -> dict:
    """
    Generate Form 27Q (TDS on payments to non-residents).

    Args:
        deductee_records: List of dicts with additional NRI-specific fields:
            pan, name, section, payment_amount, tds_deducted, tds_deposited,
            date_of_payment, date_of_deduction, challan_ref,
            country_of_residence, dtaa_applicable (bool),
            dtaa_rate (optional), trc_available (bool),
            form_10f_submitted (bool), nature_of_payment ('interest', 'dividend', 'royalty', 'fts')

    Returns:
        dict with form data, DTAA analysis, validation errors, summary
    """
    errors = []
    warnings = []

    tan_result = validate_tan(deductor_tan)
    if not tan_result["valid"]:
        errors.append(tan_result["error"])

    processed_deductees = []
    total_payment = ZERO
    total_tds = ZERO

    for idx, rec in enumerate(deductee_records):
        rec_num = idx + 1
        d_pan = rec.get("pan", "")
        country = rec.get("country_of_residence", "")
        dtaa_applicable = rec.get("dtaa_applicable", False)
        trc_available = rec.get("trc_available", False)
        form_10f = rec.get("form_10f_submitted", False)
        nature = rec.get("nature_of_payment", "")
        section = rec.get("section", "")

        try:
            payment = _to_decimal(rec.get("payment_amount", 0))
            tds_ded = _to_decimal(rec.get("tds_deducted", 0))
        except ValueError as e:
            errors.append(f"Record {rec_num}: Invalid amount -- {e}")
            continue

        total_payment += payment
        total_tds += tds_ded

        # DTAA analysis
        dtaa_info = None
        if dtaa_applicable and country in DTAA_RATES:
            dtaa_country_rates = DTAA_RATES[country]
            dtaa_rate_for_nature = dtaa_country_rates.get(nature)
            it_act_rate = None
            if section in TDS_RATE_MASTER:
                it_act_rate = TDS_RATE_MASTER[section].get("rate_individual")

            if dtaa_rate_for_nature is not None and it_act_rate is not None:
                beneficial_rate = min(dtaa_rate_for_nature, it_act_rate)
                dtaa_info = {
                    "country": country,
                    "it_act_rate": str(it_act_rate * 100) + "%",
                    "dtaa_rate": str(dtaa_rate_for_nature * 100) + "%",
                    "beneficial_rate": str(beneficial_rate * 100) + "%",
                    "applied": "DTAA" if beneficial_rate == dtaa_rate_for_nature else "IT Act",
                }
            elif dtaa_rate_for_nature is not None:
                dtaa_info = {
                    "country": country,
                    "dtaa_rate": str(dtaa_rate_for_nature * 100) + "%",
                    "note": "IT Act rate not found for comparison",
                }

            if not trc_available:
                warnings.append(
                    f"Record {rec_num} ({d_pan}): DTAA benefit claimed for {country} "
                    f"but Tax Residency Certificate (TRC) is NOT available"
                )
            if not form_10f:
                warnings.append(
                    f"Record {rec_num} ({d_pan}): Form 10F not submitted. "
                    f"Required for DTAA benefit with {country}"
                )
        elif dtaa_applicable and country and country not in DTAA_RATES:
            warnings.append(
                f"Record {rec_num}: DTAA claimed for '{country}' but "
                f"country not in rate master. Verify DTAA rate manually."
            )

        processed_deductees.append({
            "sl_no": rec_num,
            "pan": d_pan.upper().strip() if d_pan else "",
            "name": rec.get("name", ""),
            "section": section,
            "country_of_residence": country,
            "nature_of_payment": nature,
            "payment_amount": str(payment),
            "tds_deducted": str(tds_ded),
            "dtaa_analysis": dtaa_info,
            "trc_available": trc_available,
            "form_10f_submitted": form_10f,
            "date_of_payment": rec.get("date_of_payment", ""),
            "date_of_deduction": rec.get("date_of_deduction", ""),
            "challan_ref": rec.get("challan_ref", ""),
        })

    # Process challans
    processed_challans = []
    total_challan = ZERO
    for idx, ch in enumerate(challan_details):
        bsr = ch.get("bsr_code", "")
        bsr_result = validate_bsr_code(bsr)
        if not bsr_result["valid"]:
            errors.append(f"Challan {idx+1}: {bsr_result['error']}")
        try:
            ch_total = _to_decimal(ch.get("total", ch.get("amount", 0)))
        except ValueError:
            errors.append(f"Challan {idx+1}: Invalid amount")
            continue
        total_challan += ch_total
        processed_challans.append({
            "sl_no": idx + 1,
            "bsr_code": bsr,
            "challan_serial": ch.get("challan_serial", ""),
            "date_of_deposit": ch.get("date_of_deposit", ""),
            "total": str(ch_total),
        })

    return {
        "form": "27Q",
        "form_type": "TDS on payments to non-residents (quarterly)",
        "deductor": {
            "tan": deductor_tan.upper().strip() if deductor_tan else "",
            "name": deductor_name,
            "pan": deductor_pan.upper().strip() if deductor_pan else "",
        },
        "financial_year": financial_year,
        "quarter": quarter,
        "deductee_count": len(processed_deductees),
        "deductees": processed_deductees,
        "challans": processed_challans,
        "summary": {
            "total_payment": str(total_payment),
            "total_tds_deducted": str(total_tds),
            "total_challan_deposited": str(total_challan),
        },
        "validation_errors": errors,
        "warnings": warnings,
        "is_valid": len(errors) == 0,
    }


# =====================================================================
# TDS DEPOSIT TRACKER
# =====================================================================

def get_tds_deposit_due_date(deduction_month: int, deduction_year: int) -> date:
    """
    Return the due date for TDS deposit.
    General rule: 7th of the month following the month of deduction.
    Exception: For March, due date is 30th April.
    """
    if deduction_month == 3:
        return date(deduction_year, 4, 30)

    if deduction_month == 12:
        return date(deduction_year + 1, 1, 7)
    else:
        return date(deduction_year, deduction_month + 1, 7)


def get_quarterly_return_due_dates(financial_year: str) -> dict:
    """
    Return due dates for all TDS quarterly return filings.

    Args:
        financial_year: e.g., '2024-25'

    Returns:
        dict with quarter -> due date mapping
    """
    parts = financial_year.split("-")
    start_year = int(parts[0])

    return {
        "Q1": {
            "period": f"Apr {start_year} - Jun {start_year}",
            "due_date": date(start_year, 7, 31).isoformat(),
            "form_24q": date(start_year, 7, 31).isoformat(),
            "form_26q": date(start_year, 7, 31).isoformat(),
            "form_27q": date(start_year, 7, 31).isoformat(),
        },
        "Q2": {
            "period": f"Jul {start_year} - Sep {start_year}",
            "due_date": date(start_year, 10, 31).isoformat(),
            "form_24q": date(start_year, 10, 31).isoformat(),
            "form_26q": date(start_year, 10, 31).isoformat(),
            "form_27q": date(start_year, 10, 31).isoformat(),
        },
        "Q3": {
            "period": f"Oct {start_year} - Dec {start_year}",
            "due_date": date(start_year + 1, 1, 31).isoformat(),
            "form_24q": date(start_year + 1, 1, 31).isoformat(),
            "form_26q": date(start_year + 1, 1, 31).isoformat(),
            "form_27q": date(start_year + 1, 1, 31).isoformat(),
        },
        "Q4": {
            "period": f"Jan {start_year + 1} - Mar {start_year + 1}",
            "due_date": date(start_year + 1, 5, 31).isoformat(),
            "form_24q": date(start_year + 1, 5, 31).isoformat(),
            "form_26q": date(start_year + 1, 5, 31).isoformat(),
            "form_27q": date(start_year + 1, 5, 31).isoformat(),
        },
    }


def calculate_interest_on_late_deposit(
    tds_amount,
    date_of_deduction: date,
    date_of_deposit: date,
    was_deducted_late: bool = False,
    date_payment_made: date = None,
) -> dict:
    """
    Calculate interest under Section 201(1A) for late TDS deposit.

    Two types of interest:
    (i) 1% per month -- from date of deductibility to date of actual deduction
        (when TDS not deducted at all or deducted late)
    (ii) 1.5% per month -- from date of deduction to date of deposit
        (when TDS deducted but deposited late)

    Part of a month counts as a full month.

    Args:
        tds_amount: Amount of TDS
        date_of_deduction: Date TDS was actually deducted
        date_of_deposit: Date TDS was deposited to government
        was_deducted_late: Whether TDS was deducted late
        date_payment_made: Date payment was made to payee (for late deduction calc)

    Returns:
        dict with interest breakdown
    """
    tds = _to_decimal(tds_amount)
    due_date = get_tds_deposit_due_date(date_of_deduction.month, date_of_deduction.year)

    result = {
        "tds_amount": str(tds),
        "date_of_deduction": date_of_deduction.isoformat(),
        "date_of_deposit": date_of_deposit.isoformat(),
        "deposit_due_date": due_date.isoformat(),
        "interest_201_1a_i": "0",
        "interest_201_1a_ii": "0",
        "total_interest": "0",
        "months_late_deduction": 0,
        "months_late_deposit": 0,
        "is_deposit_late": date_of_deposit > due_date,
    }

    total_interest = ZERO

    # Interest for late deduction (Section 201(1A)(i)) -- 1% per month
    if was_deducted_late and date_payment_made:
        months_late_ded = _count_months(date_payment_made, date_of_deduction)
        interest_i = _round_tds(tds * INTEREST_LATE_DEDUCTION * Decimal(str(months_late_ded)))
        result["interest_201_1a_i"] = str(interest_i)
        result["months_late_deduction"] = months_late_ded
        total_interest += interest_i

    # Interest for late deposit (Section 201(1A)(ii)) -- 1.5% per month
    if date_of_deposit > due_date:
        months_late_dep = _count_months(date_of_deduction, date_of_deposit)
        interest_ii = _round_tds(tds * INTEREST_LATE_DEPOSIT * Decimal(str(months_late_dep)))
        result["interest_201_1a_ii"] = str(interest_ii)
        result["months_late_deposit"] = months_late_dep
        total_interest += interest_ii

    result["total_interest"] = str(total_interest)
    return result


def _count_months(from_date: date, to_date: date) -> int:
    """Count months between two dates (part month = full month)."""
    if to_date <= from_date:
        return 0
    months = (to_date.year - from_date.year) * 12 + (to_date.month - from_date.month)
    if to_date.day > from_date.day:
        months += 1
    return max(months, 1)


def track_tds_deposits(
    deposit_records: list,
    financial_year: str = None,
) -> dict:
    """
    Track TDS deposit status and generate Challan 281 summary.

    Args:
        deposit_records: List of dicts with keys:
            section, deduction_date, deposit_date, tds_amount,
            bsr_code, challan_serial, bank_name,
            was_deducted_late (optional), payment_date (optional)

    Returns:
        Summary with timely/late deposits, interest computations
    """
    results = []
    total_tds = ZERO
    total_interest = ZERO
    timely_count = 0
    late_count = 0

    for rec in deposit_records:
        try:
            tds_amt = _to_decimal(rec.get("tds_amount", 0))
            ded_date = _parse_date(rec.get("deduction_date"))
            dep_date = _parse_date(rec.get("deposit_date"))
        except (ValueError, TypeError) as e:
            results.append({"error": str(e), "record": rec})
            continue

        total_tds += tds_amt
        due = get_tds_deposit_due_date(ded_date.month, ded_date.year)

        interest_result = calculate_interest_on_late_deposit(
            tds_amount=tds_amt,
            date_of_deduction=ded_date,
            date_of_deposit=dep_date,
            was_deducted_late=rec.get("was_deducted_late", False),
            date_payment_made=_parse_date(rec.get("payment_date")) if rec.get("payment_date") else None,
        )

        is_late = dep_date > due
        if is_late:
            late_count += 1
        else:
            timely_count += 1

        int_amount = _to_decimal(interest_result["total_interest"])
        total_interest += int_amount

        results.append({
            "section": rec.get("section", ""),
            "tds_amount": str(tds_amt),
            "deduction_date": ded_date.isoformat(),
            "deposit_date": dep_date.isoformat(),
            "due_date": due.isoformat(),
            "is_late": is_late,
            "days_late": (dep_date - due).days if is_late else 0,
            "interest": interest_result,
            "challan_281": {
                "bsr_code": rec.get("bsr_code", ""),
                "challan_serial": rec.get("challan_serial", ""),
                "bank_name": rec.get("bank_name", ""),
            },
        })

    return {
        "financial_year": financial_year or "",
        "total_deposits": len(results),
        "timely_deposits": timely_count,
        "late_deposits": late_count,
        "total_tds_amount": str(total_tds),
        "total_interest_payable": str(total_interest),
        "deposit_details": results,
    }


def _parse_date(value) -> date:
    """Parse a date from string or date object."""
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Cannot parse date: {value}")
    raise TypeError(f"Expected date or string, got {type(value)}")


# =====================================================================
# 26AS vs BOOKS RECONCILIATION
# =====================================================================

def reconcile_26as_with_books(
    traces_data: list,
    books_data: list,
    tolerance=None,
) -> dict:
    """
    Reconcile 26AS (TRACES download) with books TDS data.

    Args:
        traces_data: List of dicts from 26AS / TRACES:
            deductor_tan, deductor_name, section, transaction_date,
            amount_paid, tds_deducted, quarter
        books_data: List of dicts from accounting books:
            deductor_tan, deductor_name, section, transaction_date,
            amount_paid, tds_deducted, quarter, invoice_ref (optional)
        tolerance: Amount tolerance for matching (default 1 rupee)

    Returns:
        Reconciliation report with matched, unmatched, mismatched entries
    """
    if tolerance is None:
        tolerance = Decimal("1")
    else:
        tolerance = _to_decimal(tolerance)

    # Normalize data
    traces_entries = _normalize_recon_entries(traces_data, source="26AS")
    books_entries = _normalize_recon_entries(books_data, source="Books")

    matched = []
    mismatched = []
    in_26as_not_books = []
    in_books_not_26as = []

    # Build lookup keys: (deductor_tan, section, quarter) -> list of entries
    traces_lookup = {}
    for entry in traces_entries:
        key = (entry["deductor_tan"], entry["section"], entry["quarter"])
        if key not in traces_lookup:
            traces_lookup[key] = []
        traces_lookup[key].append(entry)

    books_lookup = {}
    for entry in books_entries:
        key = (entry["deductor_tan"], entry["section"], entry["quarter"])
        if key not in books_lookup:
            books_lookup[key] = []
        books_lookup[key].append(entry)

    # Track matched indices to avoid double-matching
    traces_matched = set()
    books_matched = set()

    # Pass 1: Exact match on (TAN, section, quarter, amount)
    for b_idx, b_entry in enumerate(books_entries):
        if b_idx in books_matched:
            continue
        b_key = (b_entry["deductor_tan"], b_entry["section"], b_entry["quarter"])
        candidates = traces_lookup.get(b_key, [])

        for t_entry in candidates:
            t_idx = t_entry["_index"]
            if t_idx in traces_matched:
                continue

            amount_diff = abs(t_entry["tds_deducted"] - b_entry["tds_deducted"])
            payment_diff = abs(t_entry["amount_paid"] - b_entry["amount_paid"])

            if amount_diff <= tolerance and payment_diff <= tolerance:
                matched.append({
                    "traces_entry": _entry_to_dict(t_entry),
                    "books_entry": _entry_to_dict(b_entry),
                    "status": "EXACT_MATCH",
                    "tds_difference": str(amount_diff),
                    "payment_difference": str(payment_diff),
                })
                traces_matched.add(t_idx)
                books_matched.add(b_idx)
                break

    # Pass 2: Approximate match (TAN, section, quarter match, but amount differs)
    for b_idx, b_entry in enumerate(books_entries):
        if b_idx in books_matched:
            continue
        b_key = (b_entry["deductor_tan"], b_entry["section"], b_entry["quarter"])
        candidates = traces_lookup.get(b_key, [])

        for t_entry in candidates:
            t_idx = t_entry["_index"]
            if t_idx in traces_matched:
                continue

            tds_diff = t_entry["tds_deducted"] - b_entry["tds_deducted"]
            payment_diff = t_entry["amount_paid"] - b_entry["amount_paid"]

            # Match on TAN + section + quarter but amounts differ
            mismatched.append({
                "traces_entry": _entry_to_dict(t_entry),
                "books_entry": _entry_to_dict(b_entry),
                "status": "AMOUNT_MISMATCH",
                "tds_difference": str(tds_diff),
                "payment_difference": str(payment_diff),
                "action_required": _recon_action(tds_diff),
            })
            traces_matched.add(t_idx)
            books_matched.add(b_idx)
            break

    # Unmatched entries
    for t_idx, t_entry in enumerate(traces_entries):
        if t_idx not in traces_matched:
            in_26as_not_books.append({
                "entry": _entry_to_dict(t_entry),
                "status": "IN_26AS_NOT_IN_BOOKS",
                "action_required": (
                    "Verify if payment was received. If yes, book the entry. "
                    "If TDS credit is genuine, record in books for ITR claim."
                ),
            })

    for b_idx, b_entry in enumerate(books_entries):
        if b_idx not in books_matched:
            in_books_not_26as.append({
                "entry": _entry_to_dict(b_entry),
                "status": "IN_BOOKS_NOT_IN_26AS",
                "action_required": (
                    "Follow up with deductor to file/revise TDS return. "
                    "TDS credit will not be available until reflected in 26AS."
                ),
            })

    # Summary
    total_traces_tds = sum(e["tds_deducted"] for e in traces_entries)
    total_books_tds = sum(e["tds_deducted"] for e in books_entries)
    net_difference = total_traces_tds - total_books_tds

    return {
        "reconciliation_summary": {
            "total_traces_entries": len(traces_entries),
            "total_books_entries": len(books_entries),
            "matched": len(matched),
            "mismatched": len(mismatched),
            "in_26as_not_in_books": len(in_26as_not_books),
            "in_books_not_in_26as": len(in_books_not_26as),
            "total_tds_as_per_26as": str(total_traces_tds),
            "total_tds_as_per_books": str(total_books_tds),
            "net_difference": str(net_difference),
            "reconciliation_status": "RECONCILED" if (
                len(mismatched) == 0 and
                len(in_26as_not_books) == 0 and
                len(in_books_not_26as) == 0
            ) else "DISCREPANCIES_FOUND",
        },
        "matched_entries": matched,
        "mismatched_entries": mismatched,
        "in_26as_not_in_books": in_26as_not_books,
        "in_books_not_in_26as": in_books_not_26as,
        "action_items": _generate_recon_action_items(
            mismatched, in_26as_not_books, in_books_not_26as
        ),
    }


def _normalize_recon_entries(entries: list, source: str) -> list:
    """Normalize reconciliation entries from either 26AS or books."""
    normalized = []
    for idx, e in enumerate(entries):
        try:
            tan = (e.get("deductor_tan") or "").upper().strip()
            section = (e.get("section") or "").strip()
            quarter = (e.get("quarter") or "").strip()
            amount_paid = _to_decimal(e.get("amount_paid", 0))
            tds_deducted = _to_decimal(e.get("tds_deducted", 0))
        except (ValueError, TypeError):
            logger.warning(f"Skipping invalid {source} entry at index {idx}: {e}")
            continue

        normalized.append({
            "_index": idx,
            "_source": source,
            "deductor_tan": tan,
            "deductor_name": e.get("deductor_name", ""),
            "section": section,
            "quarter": quarter,
            "transaction_date": e.get("transaction_date", ""),
            "amount_paid": amount_paid,
            "tds_deducted": tds_deducted,
            "invoice_ref": e.get("invoice_ref", ""),
        })
    return normalized


def _entry_to_dict(entry: dict) -> dict:
    """Convert internal entry to output dict (stringify Decimals)."""
    return {
        "deductor_tan": entry["deductor_tan"],
        "deductor_name": entry["deductor_name"],
        "section": entry["section"],
        "quarter": entry["quarter"],
        "transaction_date": entry["transaction_date"],
        "amount_paid": str(entry["amount_paid"]),
        "tds_deducted": str(entry["tds_deducted"]),
        "invoice_ref": entry.get("invoice_ref", ""),
    }


def _recon_action(tds_diff: Decimal) -> str:
    """Generate action item text based on TDS difference."""
    if tds_diff > ZERO:
        return (
            f"26AS shows higher TDS by {tds_diff}. "
            "Verify with deductor. If correct, update books to claim additional credit."
        )
    elif tds_diff < ZERO:
        return (
            f"Books show higher TDS by {abs(tds_diff)}. "
            "Follow up with deductor to correct TDS return. "
            "Excess TDS in books will not be allowed as credit."
        )
    return "Amounts match."


def _generate_recon_action_items(mismatched, in_26as_not_books, in_books_not_26as) -> list:
    """Generate prioritized action items from reconciliation discrepancies."""
    actions = []

    # Priority 1: Entries in books but not in 26AS (deductor hasn't filed)
    if in_books_not_26as:
        total_stuck = sum(
            _to_decimal(e["entry"]["tds_deducted"]) for e in in_books_not_26as
        )
        actions.append({
            "priority": "HIGH",
            "category": "Missing from 26AS",
            "count": len(in_books_not_26as),
            "total_tds_at_risk": str(total_stuck),
            "action": (
                "Contact deductors to file/revise their TDS returns. "
                "TDS credit cannot be claimed in ITR without 26AS reflection. "
                "If unresolved, file grievance on TRACES portal."
            ),
            "deductors_to_follow_up": list(set(
                e["entry"]["deductor_tan"] for e in in_books_not_26as
            )),
        })

    # Priority 2: Amount mismatches
    if mismatched:
        total_diff = sum(
            abs(_to_decimal(e["tds_difference"])) for e in mismatched
        )
        actions.append({
            "priority": "MEDIUM",
            "category": "Amount Mismatches",
            "count": len(mismatched),
            "total_difference": str(total_diff),
            "action": (
                "Verify each mismatch with the deductor. "
                "If 26AS is correct, update books. "
                "If books are correct, request deductor to file revised return."
            ),
        })

    # Priority 3: In 26AS but not in books (unexpected TDS credit)
    if in_26as_not_books:
        total_extra = sum(
            _to_decimal(e["entry"]["tds_deducted"]) for e in in_26as_not_books
        )
        actions.append({
            "priority": "LOW",
            "category": "Extra in 26AS",
            "count": len(in_26as_not_books),
            "total_extra_tds": str(total_extra),
            "action": (
                "Verify if these relate to actual transactions. "
                "If legitimate, book the income and TDS. "
                "Additional TDS credit can be claimed in ITR."
            ),
        })

    return actions


# =====================================================================
# TCS CALCULATOR
# =====================================================================

def calculate_tcs(
    tcs_section: str,
    sale_amount,
    buyer_pan: str = "",
    is_non_filer: bool = False,
    aggregate_in_fy=None,
) -> dict:
    """
    Calculate TCS under Section 206C.

    Args:
        tcs_section: TCS section code (e.g., '206C_SCRAP', '206C_MOTOR_VEHICLE')
        sale_amount: Sale consideration
        buyer_pan: PAN of the buyer
        is_non_filer: Whether buyer has not filed returns
        aggregate_in_fy: Aggregate amount collected from this buyer in FY

    Returns:
        dict with TCS computation
    """
    sale = _to_decimal(sale_amount)
    warnings = []

    if tcs_section not in TCS_RATE_MASTER:
        return {
            "error": f"Unknown TCS section: {tcs_section}",
            "valid_sections": sorted(TCS_RATE_MASTER.keys()),
        }

    section_info = TCS_RATE_MASTER[tcs_section]
    threshold = section_info["threshold"]
    base_rate = section_info["rate"]

    # Check threshold
    threshold_exceeded = True
    if threshold > ZERO:
        check_amount = (aggregate_in_fy or ZERO) + sale
        if check_amount <= threshold:
            threshold_exceeded = False

    # Determine effective rate
    effective_rate = base_rate
    rate_basis = f"Section {tcs_section} base rate"

    # No PAN: higher of 5% or twice the rate (Section 206CC)
    pan_result = validate_pan(buyer_pan) if buyer_pan else {"valid": False}
    if not pan_result.get("valid", False):
        higher_rate = max(FIVE_PERCENT, base_rate * 2)
        if higher_rate > effective_rate:
            effective_rate = higher_rate
            rate_basis = f"Section 206CC (no PAN) -- {higher_rate * 100}%"
        warnings.append("No valid PAN: Section 206CC higher rate applies")

    # Non-filer: higher of 5% or twice the rate (Section 206CCA)
    if is_non_filer and pan_result.get("valid", False):
        non_filer_rate = max(FIVE_PERCENT, base_rate * 2)
        if non_filer_rate > effective_rate:
            effective_rate = non_filer_rate
            rate_basis = f"Section 206CCA (non-filer) -- {non_filer_rate * 100}%"
        warnings.append(f"Non-filer under Section 206CCA: rate {non_filer_rate * 100}%")

    # Compute TCS
    if threshold_exceeded:
        # TCS on amount exceeding threshold
        if threshold > ZERO:
            taxable_amount = (aggregate_in_fy or ZERO) + sale - threshold
            if taxable_amount < ZERO:
                taxable_amount = ZERO
            tcs_amount = _round_tds(taxable_amount * effective_rate)
        else:
            tcs_amount = _round_tds(sale * effective_rate)
    else:
        tcs_amount = ZERO
        rate_basis = f"Below threshold ({threshold}). No TCS."

    return {
        "section": tcs_section,
        "description": section_info["description"],
        "sale_amount": str(sale),
        "tcs_rate": str(effective_rate),
        "tcs_amount": str(tcs_amount),
        "amount_collectible": str(sale + tcs_amount),
        "effective_rate_percent": str(effective_rate * 100),
        "threshold": str(threshold),
        "threshold_exceeded": threshold_exceeded,
        "rate_basis": rate_basis,
        "warnings": warnings,
    }


# =====================================================================
# UTILITY: FEE UNDER SECTION 234E (Late filing of TDS return)
# =====================================================================

def calculate_234e_fee(
    quarter: str,
    financial_year: str,
    actual_filing_date: date,
    total_tds_amount=None,
) -> dict:
    """
    Calculate fee under Section 234E for late filing of TDS return.
    Fee = Rs. 200 per day of delay, capped at total TDS amount.

    Args:
        quarter: 'Q1', 'Q2', 'Q3', 'Q4'
        financial_year: e.g., '2024-25'
        actual_filing_date: Actual date of filing
        total_tds_amount: Total TDS in the return (cap for fee)

    Returns:
        dict with fee computation
    """
    due_dates = get_quarterly_return_due_dates(financial_year)
    if quarter not in due_dates:
        return {"error": f"Invalid quarter: {quarter}"}

    due_date_str = due_dates[quarter]["due_date"]
    due_date = date.fromisoformat(due_date_str)

    if actual_filing_date <= due_date:
        return {
            "quarter": quarter,
            "financial_year": financial_year,
            "due_date": due_date.isoformat(),
            "filing_date": actual_filing_date.isoformat(),
            "days_late": 0,
            "fee_234e": "0",
            "is_late": False,
        }

    days_late = (actual_filing_date - due_date).days
    raw_fee = Decimal(str(days_late)) * Decimal("200")

    # Cap at total TDS amount
    if total_tds_amount is not None:
        tds = _to_decimal(total_tds_amount)
        fee = min(raw_fee, tds)
    else:
        fee = raw_fee

    return {
        "quarter": quarter,
        "financial_year": financial_year,
        "due_date": due_date.isoformat(),
        "filing_date": actual_filing_date.isoformat(),
        "days_late": days_late,
        "fee_per_day": "200",
        "raw_fee": str(raw_fee),
        "fee_234e": str(_round_tds(fee)),
        "is_late": True,
        "capped_at_tds": total_tds_amount is not None and raw_fee > _to_decimal(total_tds_amount),
    }


# =====================================================================
# COMPREHENSIVE TDS SECTION LOOKUP
# =====================================================================

def lookup_tds_section(section: str = None, keyword: str = None) -> list:
    """
    Look up TDS/TCS sections by code or keyword.

    Args:
        section: Exact section code (e.g., '194C')
        keyword: Keyword to search in descriptions (e.g., 'rent', 'contractor')

    Returns:
        List of matching sections with full details
    """
    results = []

    all_sections = {**TDS_RATE_MASTER, **TCS_RATE_MASTER}

    for code, info in all_sections.items():
        match = False
        if section and code == section:
            match = True
        elif keyword:
            kw = keyword.lower()
            if (kw in info["description"].lower() or
                    kw in info.get("notes", "").lower() or
                    kw in code.lower()):
                match = True
        elif not section and not keyword:
            match = True

        if match:
            entry = {
                "section": code,
                "description": info["description"],
                "notes": info.get("notes", ""),
                "threshold": str(info.get("threshold", ZERO)),
            }

            if "rate" in info:
                entry["rate"] = str(info["rate"] * 100) + "%"
            else:
                if info.get("rate_individual") is not None:
                    entry["rate_individual"] = str(info["rate_individual"] * 100) + "%"
                if info.get("rate_others") is not None:
                    entry["rate_others"] = str(info["rate_others"] * 100) + "%"
                if info.get("is_slab_based"):
                    entry["rate_type"] = "Slab-based"

            results.append(entry)

    return results


# =====================================================================
# BULK TDS COMPUTATION
# =====================================================================

def compute_bulk_tds(records: list) -> dict:
    """
    Compute TDS for multiple payment records at once.

    Args:
        records: List of dicts, each with keys matching calculate_tds params:
            section, payment_amount, payee_pan, payee_type, is_resident,
            has_lower_deduction_cert, certificate_rate

    Returns:
        dict with individual results and grand totals
    """
    results = []
    total_payment = ZERO
    total_tds = ZERO
    error_count = 0

    for idx, rec in enumerate(records):
        result = calculate_tds(
            section=rec.get("section", ""),
            payment_amount=rec.get("payment_amount", 0),
            payee_pan=rec.get("payee_pan", ""),
            payee_type=rec.get("payee_type", "individual"),
            is_resident=rec.get("is_resident", True),
            has_lower_deduction_cert=rec.get("has_lower_deduction_cert", False),
            certificate_rate=rec.get("certificate_rate"),
            is_senior_citizen=rec.get("is_senior_citizen", False),
            aggregate_paid_in_fy=rec.get("aggregate_paid_in_fy"),
            is_non_filer_206ab=rec.get("is_non_filer_206ab", False),
        )

        result["record_index"] = idx + 1
        result["payee_name"] = rec.get("payee_name", "")
        results.append(result)

        if "error" not in result:
            total_payment += _to_decimal(result["payment_amount"])
            total_tds += _to_decimal(result["tds_amount"])
        else:
            error_count += 1

    return {
        "total_records": len(records),
        "successful": len(records) - error_count,
        "errors": error_count,
        "total_payment": str(total_payment),
        "total_tds": str(total_tds),
        "results": results,
    }


# =====================================================================
# DTAA RATE LOOKUP
# =====================================================================

def get_dtaa_rate(country: str, nature_of_payment: str) -> dict:
    """
    Get DTAA rate for a specific country and payment nature.

    Args:
        country: Country name (e.g., 'US', 'UK', 'Singapore')
        nature_of_payment: 'interest', 'dividend', 'royalty', 'fts'

    Returns:
        dict with DTAA rate and comparison with IT Act rate
    """
    if country not in DTAA_RATES:
        return {
            "error": f"Country '{country}' not in DTAA master. Available: {sorted(DTAA_RATES.keys())}",
            "note": "Verify DTAA rate from the actual treaty text for unlisted countries.",
        }

    country_rates = DTAA_RATES[country]
    if nature_of_payment not in country_rates:
        return {
            "error": f"Payment nature '{nature_of_payment}' not found for {country}",
            "available_natures": list(country_rates.keys()),
        }

    dtaa_rate = country_rates[nature_of_payment]

    return {
        "country": country,
        "nature_of_payment": nature_of_payment,
        "dtaa_rate": str(dtaa_rate * 100) + "%",
        "dtaa_rate_decimal": str(dtaa_rate),
        "note": "Beneficial rate (lower of DTAA vs IT Act) applies if payee furnishes TRC and Form 10F.",
        "requirements": [
            "Tax Residency Certificate (TRC) from country of residence",
            "Form 10F (self-declaration with prescribed particulars)",
            "No PE (Permanent Establishment) in India for reduced rate",
        ],
    }
