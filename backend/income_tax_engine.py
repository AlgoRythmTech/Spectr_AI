"""
Income Tax Computation Engine for Indian Chartered Accountants
==============================================================
Comprehensive engine for FY 2024-25 (AY 2025-26) covering:
- ITR form selection logic
- Tax computation under Old and New (115BAC) regimes
- Schedule HP, CG, BP computations
- Section 80 deductions mapper
- Advance tax calculator with 234B/234C interest
- Cost Inflation Index table
- Depreciation calculator (IT Act rates, WDV method)

All monetary calculations use Decimal for precision.
"""

import logging
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import date, datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — FY 2024-25 (AY 2025-26)
# ---------------------------------------------------------------------------

FY = "2024-25"
AY = "2025-26"

D = Decimal  # shorthand

ZERO = D("0")
ONE = D("1")
HUNDRED = D("100")

# ---- New Regime Slabs (Section 115BAC, post Finance Act 2024) ----
NEW_REGIME_SLABS: List[Tuple[D, D, D]] = [
    (D("0"),       D("300000"),   D("0")),      # 0 - 3L: Nil
    (D("300000"),  D("700000"),   D("5")),       # 3L - 7L: 5%
    (D("700000"),  D("1000000"),  D("10")),      # 7L - 10L: 10%
    (D("1000000"), D("1200000"),  D("15")),      # 10L - 12L: 15%
    (D("1200000"), D("1500000"),  D("20")),      # 12L - 15L: 20%
    (D("1500000"), D("999999999999"), D("30")),   # 15L+: 30%
]

# ---- Old Regime Slabs (Individual / HUF below 60) ----
OLD_REGIME_SLABS_GENERAL: List[Tuple[D, D, D]] = [
    (D("0"),       D("250000"),   D("0")),
    (D("250000"),  D("500000"),   D("5")),
    (D("500000"),  D("1000000"),  D("20")),
    (D("1000000"), D("999999999999"), D("30")),
]

# ---- Old Regime Slabs (Senior Citizen 60-80) ----
OLD_REGIME_SLABS_SENIOR: List[Tuple[D, D, D]] = [
    (D("0"),       D("300000"),   D("0")),
    (D("300000"),  D("500000"),   D("5")),
    (D("500000"),  D("1000000"),  D("20")),
    (D("1000000"), D("999999999999"), D("30")),
]

# ---- Old Regime Slabs (Super Senior Citizen 80+) ----
OLD_REGIME_SLABS_SUPER_SENIOR: List[Tuple[D, D, D]] = [
    (D("0"),       D("500000"),   D("0")),
    (D("500000"),  D("1000000"),  D("20")),
    (D("1000000"), D("999999999999"), D("30")),
]

# ---- Firm / LLP flat rate ----
FIRM_TAX_RATE = D("30")

# ---- Company Tax Rates ----
COMPANY_NORMAL_RATE = D("30")               # Domestic company (turnover > 400Cr)
COMPANY_CONCESSIONAL_RATE = D("25")          # Domestic (turnover <= 400Cr in FY 2022-23)
COMPANY_115BAA_RATE = D("22")               # Section 115BAA
COMPANY_115BAB_RATE = D("15")               # Section 115BAB (new mfg)

# ---- Surcharge Thresholds (Old Regime — Individuals) ----
SURCHARGE_OLD_REGIME: List[Tuple[D, D, D]] = [
    (D("5000000"),   D("10000000"),  D("10")),   # 50L - 1Cr: 10%
    (D("10000000"),  D("20000000"),  D("15")),   # 1Cr - 2Cr: 15%
    (D("20000000"),  D("50000000"),  D("25")),   # 2Cr - 5Cr: 25%
    (D("50000000"),  D("999999999999"), D("37")), # >5Cr: 37%
]

# ---- Surcharge — New Regime (capped at 25%) ----
SURCHARGE_NEW_REGIME: List[Tuple[D, D, D]] = [
    (D("5000000"),   D("10000000"),  D("10")),
    (D("10000000"),  D("20000000"),  D("15")),
    (D("20000000"),  D("999999999999"), D("25")),  # Capped at 25%
]

# ---- Surcharge — Firms ----
SURCHARGE_FIRM: List[Tuple[D, D, D]] = [
    (D("10000000"), D("999999999999"), D("12")),  # >1Cr: 12%
]

# ---- Surcharge — Companies ----
SURCHARGE_COMPANY_NORMAL: List[Tuple[D, D, D]] = [
    (D("10000000"),  D("100000000"), D("7")),     # 1Cr - 10Cr: 7%
    (D("100000000"), D("999999999999"), D("12")),  # >10Cr: 12%
]
SURCHARGE_115BAA = D("10")  # Flat 10% surcharge for 115BAA
SURCHARGE_115BAB = D("10")  # Flat 10% surcharge for 115BAB

# ---- Cess ----
HEALTH_EDUCATION_CESS_RATE = D("4")  # 4% on tax + surcharge

# ---- Rebate u/s 87A ----
REBATE_87A_NEW_REGIME_INCOME_LIMIT = D("700000")
REBATE_87A_NEW_REGIME_MAX = D("25000")
REBATE_87A_OLD_REGIME_INCOME_LIMIT = D("500000")
REBATE_87A_OLD_REGIME_MAX = D("12500")

# ---- Standard Deduction ----
STANDARD_DEDUCTION_OLD_REGIME = D("50000")
STANDARD_DEDUCTION_NEW_REGIME = D("75000")

# ---- Section 80 Deduction Limits ----
DEDUCTION_80C_LIMIT = D("150000")
DEDUCTION_80CCC_LIMIT = D("150000")   # Part of 80C aggregate
DEDUCTION_80CCD1_LIMIT = D("150000")  # Part of 80C aggregate (10% of salary cap)
DEDUCTION_80CCD1B_LIMIT = D("50000")  # Additional NPS
DEDUCTION_80CCD2_LIMIT_PERCENT = D("14")  # 14% of salary (central govt) / 10% others
DEDUCTION_80D_SELF_BELOW60 = D("25000")
DEDUCTION_80D_SELF_SENIOR = D("50000")
DEDUCTION_80D_PARENTS_BELOW60 = D("25000")
DEDUCTION_80D_PARENTS_SENIOR = D("50000")
DEDUCTION_80DD_NORMAL = D("75000")
DEDUCTION_80DD_SEVERE = D("125000")
DEDUCTION_80DDB_BELOW60 = D("40000")
DEDUCTION_80DDB_SENIOR = D("100000")
DEDUCTION_80E_NO_LIMIT = True  # Full interest deductible
DEDUCTION_80EE_LIMIT = D("50000")
DEDUCTION_80EEA_LIMIT = D("150000")
DEDUCTION_80G_LIMITS = {"100_no_limit": D("100"), "50_no_limit": D("50"),
                        "100_with_limit": D("100"), "50_with_limit": D("50")}
DEDUCTION_80GG_LIMIT = D("60000")  # ₹5,000/month
DEDUCTION_80TTA_LIMIT = D("10000")
DEDUCTION_80TTB_LIMIT = D("50000")  # Senior citizens
DEDUCTION_80U_NORMAL = D("75000")
DEDUCTION_80U_SEVERE = D("125000")

# ---- Section 24(b) Interest on House Property ----
SEC_24B_SELF_OCCUPIED_LIMIT = D("200000")
SEC_24B_LET_OUT_LIMIT = None  # No limit for let-out property

# ---- House Property ----
HP_STANDARD_DEDUCTION_RATE = D("30")  # 30% of NAV

# ---- Capital Gains ----
STCG_111A_RATE = D("15")        # Listed equity via STT
LTCG_112A_RATE = D("10")        # Listed equity above exemption
LTCG_112A_EXEMPTION = D("100000")  # ₹1 lakh exemption
LTCG_112_RATE = D("20")         # With indexation (others)

# Holding periods for LTCG classification (in months)
HOLDING_PERIOD_EQUITY = 12       # Listed shares, equity MF
HOLDING_PERIOD_IMMOVABLE = 24    # Land, building
HOLDING_PERIOD_UNLISTED = 24     # Unlisted shares
HOLDING_PERIOD_OTHERS = 36       # Debt MF, gold, others

# ---- Presumptive Taxation ----
PRESUMPTIVE_44AD_CASH_RATE = D("8")
PRESUMPTIVE_44AD_DIGITAL_RATE = D("6")
PRESUMPTIVE_44AD_TURNOVER_LIMIT = D("30000000")    # 3 Cr (if digital > 95%)
PRESUMPTIVE_44AD_TURNOVER_LIMIT_OLD = D("20000000")  # 2 Cr (otherwise)
PRESUMPTIVE_44ADA_RATE = D("50")
PRESUMPTIVE_44ADA_GROSS_LIMIT = D("7500000")  # 75 lakhs
PRESUMPTIVE_44AE_PER_HEAVY = D("7500")   # per month per heavy goods vehicle
PRESUMPTIVE_44AE_PER_OTHER = D("7500")   # per month per other vehicle

# ---- Advance Tax Due Dates ----
ADVANCE_TAX_SCHEDULE: List[Tuple[str, D]] = [
    ("2024-06-15", D("15")),   # 15% by June 15
    ("2024-09-15", D("45")),   # 45% by Sep 15
    ("2024-12-15", D("75")),   # 75% by Dec 15
    ("2025-03-15", D("100")),  # 100% by Mar 15
]

# Interest rates for 234B and 234C
INTEREST_234B_RATE = D("1")  # 1% per month
INTEREST_234C_RATE = D("1")  # 1% per month

# ---- Depreciation Rates (IT Act) ----
DEPRECIATION_RATES: Dict[str, Dict[str, D]] = {
    "building_residential": {"rate": D("5"), "description": "Buildings — residential"},
    "building_non_residential": {"rate": D("10"), "description": "Buildings — non-residential"},
    "building_temp_structure": {"rate": D("40"), "description": "Temporary erections / wooden structure"},
    "furniture_fittings": {"rate": D("10"), "description": "Furniture and fittings"},
    "plant_machinery_general": {"rate": D("15"), "description": "Plant and Machinery — general"},
    "plant_machinery_motor_car": {"rate": D("15"), "description": "Motor cars (other than used for hire)"},
    "plant_machinery_motor_lorry": {"rate": D("30"), "description": "Motor lorries / buses for hire"},
    "computers_software": {"rate": D("40"), "description": "Computers and computer software"},
    "intangible_assets": {"rate": D("25"), "description": "Intangible assets (patents, copyrights, trademarks, licences, franchises, know-how)"},
    "energy_saving_devices": {"rate": D("40"), "description": "Energy saving devices"},
    "air_pollution_control": {"rate": D("40"), "description": "Air/water pollution control equipment"},
    "books_annual_publications": {"rate": D("40"), "description": "Books — annual publications"},
    "books_others": {"rate": D("15"), "description": "Books — other than annual publications"},
}

ADDITIONAL_DEPRECIATION_RATE = D("20")  # Section 32(1)(iia) — new plant/machinery in manufacturing

# ---- Cost Inflation Index Table (Base Year 2001-02 = 100) ----
COST_INFLATION_INDEX: Dict[str, int] = {
    "2001-02": 100,
    "2002-03": 105,
    "2003-04": 109,
    "2004-05": 113,
    "2005-06": 117,
    "2006-07": 122,
    "2007-08": 129,
    "2008-09": 137,
    "2009-10": 148,
    "2010-11": 167,
    "2011-12": 184,
    "2012-13": 200,
    "2013-14": 220,
    "2014-15": 240,
    "2015-16": 254,
    "2016-17": 264,
    "2017-18": 272,
    "2018-19": 280,
    "2019-20": 289,
    "2020-21": 301,
    "2021-22": 317,
    "2022-23": 331,
    "2023-24": 348,
    "2024-25": 363,
}


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class AssesseeType(str, Enum):
    INDIVIDUAL = "individual"
    HUF = "huf"
    FIRM = "firm"
    LLP = "llp"
    COMPANY = "company"
    TRUST = "trust"


class TaxRegime(str, Enum):
    OLD = "old"
    NEW = "new"


class AgeBracket(str, Enum):
    GENERAL = "general"        # Below 60
    SENIOR = "senior"          # 60-80
    SUPER_SENIOR = "super_senior"  # 80+


class IncomeSource(str, Enum):
    SALARY = "salary"
    HOUSE_PROPERTY = "house_property"
    BUSINESS = "business"
    CAPITAL_GAINS = "capital_gains"
    OTHER_SOURCES = "other_sources"


class PropertyType(str, Enum):
    SELF_OCCUPIED = "self_occupied"
    LET_OUT = "let_out"
    DEEMED_LET_OUT = "deemed_let_out"


class AssetType(str, Enum):
    LISTED_EQUITY = "listed_equity"         # Listed shares, equity MF (STT paid)
    UNLISTED_SHARES = "unlisted_shares"
    IMMOVABLE_PROPERTY = "immovable_property"
    DEBT_MUTUAL_FUND = "debt_mutual_fund"
    GOLD = "gold"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class HousePropertyInput:
    """Input for Schedule HP computation."""
    property_type: PropertyType
    gross_annual_value: D = ZERO           # GAV — for let-out / deemed let-out
    rent_received: D = ZERO
    municipal_taxes_paid: D = ZERO
    interest_on_borrowed_capital: D = ZERO  # Section 24(b)
    pre_construction_interest: D = ZERO     # 1/5th allowed per year for 5 years
    unrealised_rent: D = ZERO
    fair_rent: D = ZERO                    # Municipal valuation / fair rent
    standard_rent: D = ZERO


@dataclass
class CapitalGainInput:
    """Input for Schedule CG computation."""
    asset_type: AssetType
    sale_consideration: D = ZERO
    cost_of_acquisition: D = ZERO
    cost_of_improvement: D = ZERO
    transfer_expenses: D = ZERO
    year_of_acquisition: str = ""          # e.g., "2015-16"
    year_of_transfer: str = FY
    sale_date: Optional[date] = None
    purchase_date: Optional[date] = None
    is_stt_paid: bool = False              # STT paid on sale
    exemption_54: D = ZERO                 # Section 54/54F/54EC
    exemption_section: str = ""            # Which section claimed


@dataclass
class BusinessIncomeInput:
    """Input for Schedule BP computation."""
    is_presumptive: bool = False
    presumptive_section: str = ""          # "44AD", "44ADA", "44AE"
    gross_turnover: D = ZERO
    cash_turnover: D = ZERO                # For 44AD split
    digital_turnover: D = ZERO             # For 44AD split
    gross_receipts_profession: D = ZERO    # For 44ADA
    number_of_heavy_vehicles: int = 0      # For 44AE
    number_of_other_vehicles: int = 0      # For 44AE
    months_owned: int = 12                 # For 44AE proration
    net_profit_as_per_books: D = ZERO      # For non-presumptive
    depreciation_as_per_books: D = ZERO
    depreciation_as_per_it: D = ZERO
    disallowances: Dict[str, D] = field(default_factory=dict)  # Section-wise add-backs
    exempt_income_debited: D = ZERO
    income_not_credited: D = ZERO


@dataclass
class Section80Deductions:
    """All Chapter VI-A deductions with amounts claimed."""
    sec_80c: D = ZERO          # Life insurance, PPF, ELSS, NSC, etc.
    sec_80ccc: D = ZERO        # Pension fund contribution
    sec_80ccd_1: D = ZERO      # Employee NPS contribution
    sec_80ccd_1b: D = ZERO     # Additional NPS (₹50,000)
    sec_80ccd_2: D = ZERO      # Employer NPS contribution
    sec_80d_self: D = ZERO     # Mediclaim — self/family
    sec_80d_parents: D = ZERO  # Mediclaim — parents
    sec_80d_preventive: D = ZERO  # Preventive health check-up (within 80D limit)
    is_self_senior: bool = False
    is_parents_senior: bool = False
    sec_80dd: D = ZERO         # Disabled dependent
    is_severe_disability_dd: bool = False
    sec_80ddb: D = ZERO        # Medical treatment of specified diseases
    is_senior_ddb: bool = False
    sec_80e: D = ZERO          # Education loan interest (full deduction)
    sec_80ee: D = ZERO         # Interest on housing loan (first-time buyer)
    sec_80eea: D = ZERO        # Interest on housing loan (affordable housing)
    sec_80g: D = ZERO          # Donations (computed amount after limits)
    sec_80gg: D = ZERO         # Rent paid (no HRA)
    sec_80tta: D = ZERO        # Savings account interest
    sec_80ttb: D = ZERO        # Interest income for senior citizens
    sec_80u: D = ZERO          # Person with disability
    is_severe_disability_u: bool = False


@dataclass
class AdvanceTaxPayment:
    """Record of an advance tax installment paid."""
    date_paid: date
    amount: D


@dataclass
class TDSEntry:
    """TDS credit entry."""
    deductor_tan: str = ""
    amount: D = ZERO
    section: str = ""           # 192, 194A, etc.
    quarter: str = ""           # Q1, Q2, Q3, Q4


@dataclass
class DepreciationAsset:
    """Single asset block for depreciation calculation."""
    asset_category: str              # Key from DEPRECIATION_RATES
    opening_wdv: D = ZERO
    additions_first_half: D = ZERO   # Additions before October 1
    additions_second_half: D = ZERO  # Additions on/after October 1
    sale_proceeds: D = ZERO
    is_new_manufacturing_asset: bool = False  # Eligible for additional depreciation
    description: str = ""


@dataclass
class TaxResult:
    """Complete tax computation result."""
    regime: TaxRegime
    gross_total_income: D = ZERO
    total_deductions: D = ZERO
    taxable_income: D = ZERO
    tax_on_normal_income: D = ZERO
    tax_on_special_income: D = ZERO      # STCG 111A, LTCG 112A, etc.
    total_tax_before_rebate: D = ZERO
    rebate_87a: D = ZERO
    tax_after_rebate: D = ZERO
    surcharge: D = ZERO
    cess: D = ZERO
    total_tax_liability: D = ZERO
    relief_89: D = ZERO
    net_tax_payable: D = ZERO
    breakdown: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def _to_decimal(value: Any) -> D:
    """Safely convert a value to Decimal."""
    if isinstance(value, D):
        return value
    if value is None:
        return ZERO
    try:
        return D(str(value))
    except (InvalidOperation, ValueError):
        logger.warning("Could not convert %s to Decimal, using 0", value)
        return ZERO


def _round_to_nearest_ten(amount: D) -> D:
    """Round taxable income down to nearest ₹10 as per IT Act."""
    return (amount / D("10")).to_integral_value(rounding=ROUND_HALF_UP) * D("10")


def _round_currency(amount: D) -> D:
    """Round to nearest rupee."""
    return amount.quantize(D("1"), rounding=ROUND_HALF_UP)


def _compute_slab_tax(taxable_income: D, slabs: List[Tuple[D, D, D]]) -> D:
    """
    Compute tax on normal income using progressive slab rates.
    Each slab: (lower_limit, upper_limit, rate_percent)
    """
    if taxable_income <= ZERO:
        return ZERO

    tax = ZERO
    remaining = taxable_income

    for lower, upper, rate in slabs:
        if remaining <= ZERO:
            break
        slab_amount = min(remaining, upper - lower)
        if slab_amount > ZERO:
            tax += slab_amount * rate / HUNDRED
        remaining -= slab_amount

    return _round_currency(tax)


def _compute_surcharge(
    tax_amount: D,
    total_income: D,
    surcharge_table: List[Tuple[D, D, D]]
) -> D:
    """
    Compute surcharge based on total income and surcharge slab table.
    Applies marginal relief where applicable.
    """
    if tax_amount <= ZERO or total_income <= ZERO:
        return ZERO

    surcharge = ZERO
    for lower, upper, rate in surcharge_table:
        if lower < total_income <= upper or (total_income > upper and upper >= D("999999999999")):
            if total_income > lower:
                surcharge = tax_amount * rate / HUNDRED
                # Marginal relief: surcharge should not exceed the additional income
                # beyond the threshold
                excess_income = total_income - lower
                tax_at_lower = _compute_slab_tax(lower, OLD_REGIME_SLABS_GENERAL)
                marginal_limit = excess_income
                if surcharge > marginal_limit:
                    surcharge = marginal_limit
                break

    return _round_currency(surcharge)


def _compute_surcharge_for_regime(
    tax_amount: D,
    total_income: D,
    regime: TaxRegime,
    assessee_type: AssesseeType
) -> D:
    """Select appropriate surcharge table and compute."""
    if assessee_type == AssesseeType.COMPANY:
        return _round_currency(tax_amount * SURCHARGE_115BAA / HUNDRED)
    elif assessee_type in (AssesseeType.FIRM, AssesseeType.LLP):
        return _compute_surcharge(tax_amount, total_income, SURCHARGE_FIRM)
    elif regime == TaxRegime.NEW:
        return _compute_surcharge(tax_amount, total_income, SURCHARGE_NEW_REGIME)
    else:
        return _compute_surcharge(tax_amount, total_income, SURCHARGE_OLD_REGIME)


def _compute_cess(tax_plus_surcharge: D) -> D:
    """Health and Education Cess = 4% on (tax + surcharge)."""
    return _round_currency(tax_plus_surcharge * HEALTH_EDUCATION_CESS_RATE / HUNDRED)


def get_indexed_cost(
    cost: D,
    year_of_acquisition: str,
    year_of_transfer: str = FY
) -> D:
    """
    Compute indexed cost of acquisition using CII.
    Indexed Cost = Cost * (CII of transfer year / CII of acquisition year)
    """
    cii_transfer = COST_INFLATION_INDEX.get(year_of_transfer)
    cii_acquisition = COST_INFLATION_INDEX.get(year_of_acquisition)

    if cii_transfer is None:
        raise ValueError(f"CII not available for transfer year {year_of_transfer}")
    if cii_acquisition is None:
        raise ValueError(f"CII not available for acquisition year {year_of_acquisition}")
    if cii_acquisition == 0:
        raise ValueError("CII for acquisition year cannot be zero")

    indexed = cost * D(str(cii_transfer)) / D(str(cii_acquisition))
    return _round_currency(indexed)


def get_cii(year: str) -> int:
    """Return Cost Inflation Index for a given financial year."""
    cii = COST_INFLATION_INDEX.get(year)
    if cii is None:
        raise ValueError(
            f"CII not available for year {year}. "
            f"Available years: {min(COST_INFLATION_INDEX.keys())} to {max(COST_INFLATION_INDEX.keys())}"
        )
    return cii


# ---------------------------------------------------------------------------
# 1. ITR Form Selector
# ---------------------------------------------------------------------------

def select_itr_form(
    assessee_type: str,
    income_sources: List[str],
    turnover: D = ZERO,
    total_income: D = ZERO,
    has_foreign_income: bool = False,
    has_foreign_assets: bool = False,
    is_director: bool = False,
    unlisted_shares: bool = False,
    is_presumptive: bool = False,
    presumptive_section: str = "",
    number_of_house_properties: int = 0,
    has_brought_forward_losses: bool = False,
    has_agricultural_income_above_5000: bool = False,
    is_religious_trust: bool = False,
    is_political_party: bool = False,
    is_research_institution: bool = False,
) -> Dict[str, Any]:
    """
    Determine the appropriate ITR form based on assessee profile.

    Returns:
        Dict with keys: form, reasons, schedules_needed, eligibility_notes
    """
    try:
        a_type = AssesseeType(assessee_type.lower())
    except ValueError:
        return {
            "form": None,
            "error": f"Invalid assessee type: {assessee_type}. "
                     f"Valid types: {[t.value for t in AssesseeType]}"
        }

    sources = [s.lower() for s in income_sources]
    reasons = []
    schedules = []

    # ------- Trust / Section 11 / 12 / Political Party / Research -------
    if a_type == AssesseeType.TRUST or is_religious_trust or is_political_party or is_research_institution:
        reasons.append("Assessee is a trust / institution / political party — ITR-7 mandatory")
        schedules.extend(["Schedule AI (Accumulation of Income)", "Schedule VC (Voluntary Contributions)",
                          "Schedule I (Income)", "Schedule J (Investments)", "Schedule K (Land/Building)"])
        return {
            "form": "ITR-7",
            "reasons": reasons,
            "schedules_needed": schedules,
            "eligibility_notes": "Mandatory for trusts u/s 139(4A), political parties u/s 139(4B), "
                                 "institutions u/s 139(4C/4D)"
        }

    # ------- Company -------
    if a_type == AssesseeType.COMPANY:
        reasons.append("Companies must file ITR-6 (not claiming exemption u/s 11)")
        schedules.extend(["Schedule BP", "Schedule HP", "Schedule CG", "Schedule OS",
                          "Schedule OA (Other Adjustments)", "Schedule DPM (Depreciation)",
                          "Schedule DOA", "Schedule ESR", "Schedule CYLA", "Schedule MAT"])
        if has_foreign_income or has_foreign_assets:
            schedules.extend(["Schedule FA (Foreign Assets)", "Schedule FSI (Foreign Source Income)",
                              "Schedule TR (Tax Relief)"])
        return {
            "form": "ITR-6",
            "reasons": reasons,
            "schedules_needed": schedules,
            "eligibility_notes": "All companies (other than those claiming exemption u/s 11)"
        }

    # ------- Firm / LLP -------
    if a_type in (AssesseeType.FIRM, AssesseeType.LLP):
        reasons.append(f"{a_type.value.upper()} must file ITR-5")
        schedules.extend(["Schedule BP", "Schedule HP", "Schedule CG", "Schedule OS",
                          "Schedule DPM (Depreciation)", "Schedule Partners",
                          "Schedule CYLA", "Schedule BFLA"])
        if has_foreign_income or has_foreign_assets:
            schedules.extend(["Schedule FA", "Schedule FSI", "Schedule TR"])
        return {
            "form": "ITR-5",
            "reasons": reasons,
            "schedules_needed": schedules,
            "eligibility_notes": "Mandatory for firms, LLPs, AOPs, BOIs"
        }

    # ------- Individual / HUF — determine ITR-1 / ITR-2 / ITR-3 / ITR-4 -------

    has_salary = "salary" in sources
    has_hp = "house_property" in sources
    has_business = "business" in sources
    has_cg = "capital_gains" in sources
    has_other = "other_sources" in sources

    # ----- ITR-3: Business income (non-presumptive) -----
    if has_business and not is_presumptive:
        reasons.append("Business/profession income (non-presumptive) requires ITR-3")
        schedules.extend(["Schedule S (Salary)", "Schedule HP", "Schedule BP",
                          "Schedule CG", "Schedule OS", "Schedule DPM",
                          "Schedule CYLA", "Schedule BFLA", "Schedule VIA"])
        if has_foreign_income or has_foreign_assets:
            schedules.extend(["Schedule FA", "Schedule FSI", "Schedule TR"])
            reasons.append("Foreign income/assets require additional schedules")
        return {
            "form": "ITR-3",
            "reasons": reasons,
            "schedules_needed": schedules,
            "eligibility_notes": "For individuals/HUFs with business/profession income (non-presumptive)"
        }

    # ----- ITR-4: Presumptive income -----
    if is_presumptive and presumptive_section in ("44AD", "44ADA", "44AE"):
        # ITR-4 has restrictions
        disqualifiers = []
        if has_cg:
            disqualifiers.append("Capital gains income present — cannot use ITR-4")
        if has_foreign_income:
            disqualifiers.append("Foreign income present — cannot use ITR-4")
        if has_foreign_assets:
            disqualifiers.append("Foreign assets present — cannot use ITR-4")
        if is_director:
            disqualifiers.append("Director in a company — cannot use ITR-4")
        if unlisted_shares:
            disqualifiers.append("Holds unlisted equity shares — cannot use ITR-4")
        if number_of_house_properties > 1:
            disqualifiers.append("More than one house property — cannot use ITR-4")
        if total_income > D("5000000"):
            disqualifiers.append("Total income exceeds ₹50 lakhs — cannot use ITR-4")

        if disqualifiers:
            reasons.extend(disqualifiers)
            reasons.append("Falling back to ITR-3 due to ITR-4 disqualifications")
            schedules.extend(["Schedule S", "Schedule HP", "Schedule BP",
                              "Schedule CG", "Schedule OS", "Schedule DPM",
                              "Schedule CYLA", "Schedule BFLA", "Schedule VIA"])
            return {
                "form": "ITR-3",
                "reasons": reasons,
                "schedules_needed": schedules,
                "eligibility_notes": "ITR-4 not eligible; ITR-3 required"
            }

        reasons.append(f"Presumptive income u/s {presumptive_section} — ITR-4 eligible")
        schedules.extend(["Schedule BP (Presumptive)", "Schedule VIA"])
        if has_salary:
            schedules.append("Schedule S (Salary)")
        if has_hp:
            schedules.append("Schedule HP (One property only)")
        return {
            "form": "ITR-4",
            "reasons": reasons,
            "schedules_needed": schedules,
            "eligibility_notes": (
                f"For individuals/HUFs/firms with presumptive income u/s {presumptive_section}. "
                f"Income must not exceed ₹50L. No capital gains, foreign income/assets."
            )
        }

    # ----- ITR-2: Capital gains / foreign income / director / multiple HP -----
    itr2_triggers = []
    if has_cg:
        itr2_triggers.append("Capital gains income present")
    if has_foreign_income:
        itr2_triggers.append("Foreign source income")
    if has_foreign_assets:
        itr2_triggers.append("Foreign assets/accounts to be reported in Schedule FA")
    if is_director:
        itr2_triggers.append("Director in a company during the year")
    if unlisted_shares:
        itr2_triggers.append("Holds unlisted equity shares at any time during the year")
    if number_of_house_properties > 1:
        itr2_triggers.append("More than one house property")
    if total_income > D("5000000") and not has_business:
        itr2_triggers.append("Total income exceeds ₹50 lakhs (requires asset-liability schedule)")
    if has_agricultural_income_above_5000:
        itr2_triggers.append("Agricultural income exceeding ₹5,000")
    if has_brought_forward_losses:
        itr2_triggers.append("Brought forward losses to be carried forward")

    if itr2_triggers:
        reasons.extend(itr2_triggers)
        reasons.append("ITR-2 is required")
        schedules.extend(["Schedule S", "Schedule HP", "Schedule CG", "Schedule OS",
                          "Schedule CYLA", "Schedule BFLA", "Schedule VIA"])
        if has_foreign_income or has_foreign_assets:
            schedules.extend(["Schedule FA", "Schedule FSI", "Schedule TR"])
        if total_income > D("5000000"):
            schedules.append("Schedule AL (Asset and Liability)")
        return {
            "form": "ITR-2",
            "reasons": reasons,
            "schedules_needed": list(set(schedules)),
            "eligibility_notes": "For individuals/HUFs without business income but with CG/foreign/director status"
        }

    # ----- ITR-1 (Sahaj): Simplest form -----
    itr1_eligible = True
    itr1_blockers = []

    if a_type == AssesseeType.HUF:
        itr1_eligible = False
        itr1_blockers.append("HUF cannot file ITR-1")

    if total_income > D("5000000"):
        itr1_eligible = False
        itr1_blockers.append("Total income exceeds ₹50 lakhs")

    if number_of_house_properties > 1:
        itr1_eligible = False
        itr1_blockers.append("More than 1 house property")

    if has_business:
        itr1_eligible = False
        itr1_blockers.append("Business income present")

    allowed_sources_itr1 = {"salary", "house_property", "other_sources"}
    extra_sources = set(sources) - allowed_sources_itr1
    if extra_sources:
        itr1_eligible = False
        itr1_blockers.append(f"Income sources not allowed in ITR-1: {extra_sources}")

    if has_agricultural_income_above_5000:
        itr1_eligible = False
        itr1_blockers.append("Agricultural income exceeds ₹5,000")

    if itr1_eligible:
        reasons.append("Eligible for ITR-1 (Sahaj) — simplest form")
        reasons.append("Salary + one house property + other sources, income ≤ ₹50L")
        schedules_itr1 = []
        if has_salary:
            schedules_itr1.append("Part B — TI (Salary details)")
        if has_hp:
            schedules_itr1.append("Part B — TI (House property)")
        schedules_itr1.append("Part C — Deductions under Chapter VI-A")
        schedules_itr1.append("Part D — Tax Computation")
        schedules_itr1.append("Schedule TDS")
        return {
            "form": "ITR-1",
            "reasons": reasons,
            "schedules_needed": schedules_itr1,
            "eligibility_notes": "Resident individual with salary + 1 HP + other sources, total income ≤ ₹50L"
        }
    else:
        reasons.extend(itr1_blockers)
        reasons.append("Not eligible for ITR-1; ITR-2 recommended")
        schedules.extend(["Schedule S", "Schedule HP", "Schedule OS",
                          "Schedule CYLA", "Schedule VIA"])
        return {
            "form": "ITR-2",
            "reasons": reasons,
            "schedules_needed": schedules,
            "eligibility_notes": "Individual/HUF not eligible for ITR-1 and no business income"
        }


# ---------------------------------------------------------------------------
# 2. Tax Computation Engine
# ---------------------------------------------------------------------------

def compute_tax(
    assessee_type: str,
    regime: str,
    gross_total_income: D,
    salary_income: D = ZERO,
    hp_income: D = ZERO,
    business_income: D = ZERO,
    stcg_111a: D = ZERO,           # STCG on listed equity (taxed at 15%)
    stcg_normal: D = ZERO,         # STCG on other assets (normal slab rates)
    ltcg_112a: D = ZERO,           # LTCG on listed equity (10% above ₹1L)
    ltcg_112: D = ZERO,            # LTCG on other assets (20% with indexation)
    other_income: D = ZERO,
    deductions: Optional[Section80Deductions] = None,
    age_bracket: str = "general",
    tds_total: D = ZERO,
    advance_tax_paid: D = ZERO,
    self_assessment_tax: D = ZERO,
    relief_89: D = ZERO,
    company_section: str = "",     # "115BAA" or "115BAB" for companies
) -> TaxResult:
    """
    Compute total tax liability for FY 2024-25.

    Handles individuals, HUFs, firms, LLPs, and companies.
    For individuals/HUFs: computes under the specified regime (old/new).
    Applies surcharge and cess automatically.
    """
    try:
        a_type = AssesseeType(assessee_type.lower())
    except ValueError:
        raise ValueError(f"Invalid assessee type: {assessee_type}")

    try:
        tax_regime = TaxRegime(regime.lower())
    except ValueError:
        raise ValueError(f"Invalid regime: {regime}. Use 'old' or 'new'")

    try:
        age = AgeBracket(age_bracket.lower())
    except ValueError:
        age = AgeBracket.GENERAL

    result = TaxResult(regime=tax_regime)
    breakdown = {}

    # ---- Step 1: Compute Gross Total Income ----
    normal_income = salary_income + hp_income + business_income + stcg_normal + other_income
    special_rate_income = stcg_111a + ltcg_112a + ltcg_112

    result.gross_total_income = normal_income + special_rate_income
    breakdown["income_heads"] = {
        "salary": str(salary_income),
        "house_property": str(hp_income),
        "business_profession": str(business_income),
        "stcg_normal_rates": str(stcg_normal),
        "stcg_111a": str(stcg_111a),
        "ltcg_112a": str(ltcg_112a),
        "ltcg_112": str(ltcg_112),
        "other_sources": str(other_income),
        "gross_total_income": str(result.gross_total_income),
    }

    # ---- Step 2: Apply Deductions ----
    total_deductions = ZERO

    if tax_regime == TaxRegime.NEW:
        # New regime: only 80CCD(2) (employer NPS) allowed
        if deductions and deductions.sec_80ccd_2 > ZERO:
            total_deductions = deductions.sec_80ccd_2
            breakdown["deductions"] = {
                "regime_note": "New regime — only Section 80CCD(2) allowed",
                "sec_80ccd_2": str(deductions.sec_80ccd_2),
                "total_deductions": str(total_deductions),
            }
        else:
            breakdown["deductions"] = {
                "regime_note": "New regime — no Chapter VI-A deductions (except 80CCD(2))",
                "total_deductions": "0",
            }
    elif tax_regime == TaxRegime.OLD and deductions:
        total_deductions = _compute_section80_deductions(deductions)
        breakdown["deductions"] = _section80_breakdown(deductions, total_deductions)

    result.total_deductions = total_deductions

    # ---- Step 3: Taxable Income ----
    taxable_normal = max(ZERO, normal_income - total_deductions)
    taxable_normal = _round_to_nearest_ten(taxable_normal)
    result.taxable_income = taxable_normal + special_rate_income

    breakdown["taxable_income"] = {
        "normal_income_after_deductions": str(taxable_normal),
        "special_rate_income": str(special_rate_income),
        "total_taxable_income": str(result.taxable_income),
    }

    # ---- Step 4: Compute Tax ----
    if a_type == AssesseeType.COMPANY:
        tax_normal = _compute_company_tax(taxable_normal, company_section)
        breakdown["company_section"] = company_section or "Normal rates"
    elif a_type in (AssesseeType.FIRM, AssesseeType.LLP):
        tax_normal = _round_currency(taxable_normal * FIRM_TAX_RATE / HUNDRED)
    elif tax_regime == TaxRegime.NEW:
        tax_normal = _compute_slab_tax(taxable_normal, NEW_REGIME_SLABS)
    else:
        slabs = _get_old_regime_slabs(age)
        tax_normal = _compute_slab_tax(taxable_normal, slabs)

    result.tax_on_normal_income = tax_normal

    # ---- Step 5: Tax on Special Rate Income ----
    tax_special = ZERO
    special_breakdown = {}

    if stcg_111a > ZERO:
        tax_stcg_111a = _round_currency(stcg_111a * STCG_111A_RATE / HUNDRED)
        tax_special += tax_stcg_111a
        special_breakdown["stcg_111a_tax"] = str(tax_stcg_111a)

    if ltcg_112a > ZERO:
        taxable_ltcg_112a = max(ZERO, ltcg_112a - LTCG_112A_EXEMPTION)
        tax_ltcg_112a = _round_currency(taxable_ltcg_112a * LTCG_112A_RATE / HUNDRED)
        tax_special += tax_ltcg_112a
        special_breakdown["ltcg_112a_exempt"] = str(min(ltcg_112a, LTCG_112A_EXEMPTION))
        special_breakdown["ltcg_112a_taxable"] = str(taxable_ltcg_112a)
        special_breakdown["ltcg_112a_tax"] = str(tax_ltcg_112a)

    if ltcg_112 > ZERO:
        tax_ltcg_112 = _round_currency(ltcg_112 * LTCG_112_RATE / HUNDRED)
        tax_special += tax_ltcg_112
        special_breakdown["ltcg_112_tax"] = str(tax_ltcg_112)

    result.tax_on_special_income = tax_special
    if special_breakdown:
        breakdown["special_rate_tax"] = special_breakdown

    # ---- Step 6: Total Tax Before Rebate ----
    total_tax = tax_normal + tax_special
    result.total_tax_before_rebate = total_tax

    # ---- Step 7: Rebate u/s 87A ----
    rebate = ZERO
    if a_type in (AssesseeType.INDIVIDUAL,) and a_type not in (AssesseeType.COMPANY, AssesseeType.FIRM, AssesseeType.LLP):
        if tax_regime == TaxRegime.NEW and result.taxable_income <= REBATE_87A_NEW_REGIME_INCOME_LIMIT:
            rebate = min(total_tax, REBATE_87A_NEW_REGIME_MAX)
            breakdown["rebate_87a"] = {
                "eligible": True,
                "income_limit": str(REBATE_87A_NEW_REGIME_INCOME_LIMIT),
                "rebate_amount": str(rebate),
            }
        elif tax_regime == TaxRegime.OLD and result.taxable_income <= REBATE_87A_OLD_REGIME_INCOME_LIMIT:
            rebate = min(total_tax, REBATE_87A_OLD_REGIME_MAX)
            breakdown["rebate_87a"] = {
                "eligible": True,
                "income_limit": str(REBATE_87A_OLD_REGIME_INCOME_LIMIT),
                "rebate_amount": str(rebate),
            }
        else:
            breakdown["rebate_87a"] = {"eligible": False, "reason": "Income exceeds limit"}

    result.rebate_87a = rebate
    tax_after_rebate = max(ZERO, total_tax - rebate)
    result.tax_after_rebate = tax_after_rebate

    # ---- Step 8: Surcharge ----
    surcharge = ZERO
    if a_type == AssesseeType.COMPANY:
        if company_section == "115BAA":
            surcharge = _round_currency(tax_after_rebate * SURCHARGE_115BAA / HUNDRED)
        elif company_section == "115BAB":
            surcharge = _round_currency(tax_after_rebate * SURCHARGE_115BAB / HUNDRED)
        else:
            surcharge = _compute_surcharge(tax_after_rebate, result.taxable_income, SURCHARGE_COMPANY_NORMAL)
    elif a_type in (AssesseeType.FIRM, AssesseeType.LLP):
        surcharge = _compute_surcharge(tax_after_rebate, result.taxable_income, SURCHARGE_FIRM)
    else:
        surcharge = _compute_surcharge_for_regime(
            tax_after_rebate, result.taxable_income, tax_regime, a_type
        )

    result.surcharge = surcharge
    breakdown["surcharge"] = str(surcharge)

    # ---- Step 9: Cess ----
    cess = _compute_cess(tax_after_rebate + surcharge)
    result.cess = cess
    breakdown["cess"] = str(cess)

    # ---- Step 10: Total Tax Liability ----
    total_liability = tax_after_rebate + surcharge + cess
    result.total_tax_liability = _round_currency(total_liability)

    # ---- Step 11: Relief u/s 89 ----
    result.relief_89 = relief_89

    # ---- Step 12: Net Tax Payable ----
    net_payable = total_liability - relief_89 - tds_total - advance_tax_paid - self_assessment_tax
    result.net_tax_payable = _round_currency(max(ZERO, net_payable))

    breakdown["credits"] = {
        "tds": str(tds_total),
        "advance_tax": str(advance_tax_paid),
        "self_assessment_tax": str(self_assessment_tax),
        "relief_89": str(relief_89),
        "net_tax_payable": str(result.net_tax_payable),
        "refund_due": str(_round_currency(abs(net_payable))) if net_payable < ZERO else "0",
    }

    result.breakdown = breakdown
    return result


def compare_regimes(
    assessee_type: str = "individual",
    salary_income: D = ZERO,
    hp_income: D = ZERO,
    business_income: D = ZERO,
    stcg_111a: D = ZERO,
    stcg_normal: D = ZERO,
    ltcg_112a: D = ZERO,
    ltcg_112: D = ZERO,
    other_income: D = ZERO,
    deductions: Optional[Section80Deductions] = None,
    age_bracket: str = "general",
    tds_total: D = ZERO,
    advance_tax_paid: D = ZERO,
) -> Dict[str, Any]:
    """
    Compare tax liability under both Old and New regimes.
    Returns both computations and a recommendation.
    """
    gti = salary_income + hp_income + business_income + stcg_111a + stcg_normal + ltcg_112a + ltcg_112 + other_income

    old_result = compute_tax(
        assessee_type=assessee_type, regime="old",
        gross_total_income=gti,
        salary_income=salary_income, hp_income=hp_income,
        business_income=business_income, stcg_111a=stcg_111a,
        stcg_normal=stcg_normal, ltcg_112a=ltcg_112a,
        ltcg_112=ltcg_112, other_income=other_income,
        deductions=deductions, age_bracket=age_bracket,
        tds_total=tds_total, advance_tax_paid=advance_tax_paid,
    )

    new_result = compute_tax(
        assessee_type=assessee_type, regime="new",
        gross_total_income=gti,
        salary_income=salary_income, hp_income=hp_income,
        business_income=business_income, stcg_111a=stcg_111a,
        stcg_normal=stcg_normal, ltcg_112a=ltcg_112a,
        ltcg_112=ltcg_112, other_income=other_income,
        deductions=deductions, age_bracket=age_bracket,
        tds_total=tds_total, advance_tax_paid=advance_tax_paid,
    )

    old_total = old_result.total_tax_liability
    new_total = new_result.total_tax_liability
    savings = abs(old_total - new_total)

    if new_total < old_total:
        recommended = "new"
        recommendation_text = (
            f"New Regime is beneficial. Tax saving: Rs. {savings:,.0f}. "
            f"Old Regime: Rs. {old_total:,.0f} | New Regime: Rs. {new_total:,.0f}"
        )
    elif old_total < new_total:
        recommended = "old"
        recommendation_text = (
            f"Old Regime is beneficial. Tax saving: Rs. {savings:,.0f}. "
            f"Old Regime: Rs. {old_total:,.0f} | New Regime: Rs. {new_total:,.0f}"
        )
    else:
        recommended = "new"  # Default to new if same
        recommendation_text = (
            f"Both regimes result in same tax: Rs. {old_total:,.0f}. "
            f"New Regime recommended as default."
        )

    return {
        "old_regime": {
            "total_tax_liability": str(old_total),
            "taxable_income": str(old_result.taxable_income),
            "deductions_claimed": str(old_result.total_deductions),
            "breakdown": old_result.breakdown,
        },
        "new_regime": {
            "total_tax_liability": str(new_total),
            "taxable_income": str(new_result.taxable_income),
            "deductions_claimed": str(new_result.total_deductions),
            "breakdown": new_result.breakdown,
        },
        "recommended_regime": recommended,
        "tax_savings": str(savings),
        "recommendation": recommendation_text,
    }


def _get_old_regime_slabs(age: AgeBracket) -> List[Tuple[D, D, D]]:
    """Return the appropriate old regime slab based on age bracket."""
    if age == AgeBracket.SUPER_SENIOR:
        return OLD_REGIME_SLABS_SUPER_SENIOR
    elif age == AgeBracket.SENIOR:
        return OLD_REGIME_SLABS_SENIOR
    else:
        return OLD_REGIME_SLABS_GENERAL


def _compute_company_tax(taxable_income: D, section: str) -> D:
    """Compute company tax based on applicable section."""
    if section == "115BAA":
        return _round_currency(taxable_income * COMPANY_115BAA_RATE / HUNDRED)
    elif section == "115BAB":
        return _round_currency(taxable_income * COMPANY_115BAB_RATE / HUNDRED)
    else:
        return _round_currency(taxable_income * COMPANY_NORMAL_RATE / HUNDRED)


# ---------------------------------------------------------------------------
# Section 80 Deduction Computation
# ---------------------------------------------------------------------------

def _compute_section80_deductions(ded: Section80Deductions) -> D:
    """
    Compute total eligible deductions under Chapter VI-A (Old Regime).
    Applies individual section limits and aggregate limits.
    """
    total = ZERO

    # ---- 80C + 80CCC + 80CCD(1) — Aggregate limit ₹1.5L ----
    sec80c_aggregate = min(
        ded.sec_80c + ded.sec_80ccc + ded.sec_80ccd_1,
        DEDUCTION_80C_LIMIT
    )
    total += sec80c_aggregate

    # ---- 80CCD(1B) — Additional NPS ₹50,000 ----
    total += min(ded.sec_80ccd_1b, DEDUCTION_80CCD1B_LIMIT)

    # ---- 80CCD(2) — Employer NPS (allowed in both regimes) ----
    total += ded.sec_80ccd_2  # Limited to 14% of salary (validation outside)

    # ---- 80D — Mediclaim ----
    self_limit = DEDUCTION_80D_SELF_SENIOR if ded.is_self_senior else DEDUCTION_80D_SELF_BELOW60
    parents_limit = DEDUCTION_80D_PARENTS_SENIOR if ded.is_parents_senior else DEDUCTION_80D_PARENTS_BELOW60

    total += min(ded.sec_80d_self + ded.sec_80d_preventive, self_limit)
    total += min(ded.sec_80d_parents, parents_limit)

    # ---- 80DD — Disabled dependent ----
    if ded.sec_80dd > ZERO:
        dd_limit = DEDUCTION_80DD_SEVERE if ded.is_severe_disability_dd else DEDUCTION_80DD_NORMAL
        total += min(ded.sec_80dd, dd_limit)

    # ---- 80DDB — Medical treatment ----
    if ded.sec_80ddb > ZERO:
        ddb_limit = DEDUCTION_80DDB_SENIOR if ded.is_senior_ddb else DEDUCTION_80DDB_BELOW60
        total += min(ded.sec_80ddb, ddb_limit)

    # ---- 80E — Education loan interest (no limit) ----
    total += ded.sec_80e

    # ---- 80EE — Housing loan interest (first-time buyer) ----
    total += min(ded.sec_80ee, DEDUCTION_80EE_LIMIT)

    # ---- 80EEA — Affordable housing interest ----
    total += min(ded.sec_80eea, DEDUCTION_80EEA_LIMIT)

    # ---- 80G — Donations (pre-computed eligible amount) ----
    total += ded.sec_80g

    # ---- 80GG — Rent paid (no HRA) ----
    total += min(ded.sec_80gg, DEDUCTION_80GG_LIMIT)

    # ---- 80TTA / 80TTB (mutually exclusive) ----
    if ded.sec_80ttb > ZERO:
        total += min(ded.sec_80ttb, DEDUCTION_80TTB_LIMIT)
    elif ded.sec_80tta > ZERO:
        total += min(ded.sec_80tta, DEDUCTION_80TTA_LIMIT)

    # ---- 80U — Person with disability ----
    if ded.sec_80u > ZERO:
        u_limit = DEDUCTION_80U_SEVERE if ded.is_severe_disability_u else DEDUCTION_80U_NORMAL
        total += min(ded.sec_80u, u_limit)

    return total


def _section80_breakdown(ded: Section80Deductions, total: D) -> Dict[str, str]:
    """Generate detailed breakdown of Section 80 deductions."""
    breakdown = {}
    sec80c_agg = min(ded.sec_80c + ded.sec_80ccc + ded.sec_80ccd_1, DEDUCTION_80C_LIMIT)
    breakdown["80C_80CCC_80CCD1_aggregate"] = str(sec80c_agg)
    if ded.sec_80c > ZERO:
        breakdown["80C_claimed"] = str(ded.sec_80c)
    if ded.sec_80ccc > ZERO:
        breakdown["80CCC_claimed"] = str(ded.sec_80ccc)
    if ded.sec_80ccd_1 > ZERO:
        breakdown["80CCD(1)_claimed"] = str(ded.sec_80ccd_1)
    if ded.sec_80ccd_1b > ZERO:
        breakdown["80CCD(1B)_NPS_additional"] = str(min(ded.sec_80ccd_1b, DEDUCTION_80CCD1B_LIMIT))
    if ded.sec_80ccd_2 > ZERO:
        breakdown["80CCD(2)_employer_NPS"] = str(ded.sec_80ccd_2)
    if ded.sec_80d_self > ZERO or ded.sec_80d_parents > ZERO:
        self_limit = DEDUCTION_80D_SELF_SENIOR if ded.is_self_senior else DEDUCTION_80D_SELF_BELOW60
        parents_limit = DEDUCTION_80D_PARENTS_SENIOR if ded.is_parents_senior else DEDUCTION_80D_PARENTS_BELOW60
        breakdown["80D_self_family"] = str(min(ded.sec_80d_self + ded.sec_80d_preventive, self_limit))
        breakdown["80D_parents"] = str(min(ded.sec_80d_parents, parents_limit))
    if ded.sec_80dd > ZERO:
        breakdown["80DD"] = str(min(ded.sec_80dd,
                                    DEDUCTION_80DD_SEVERE if ded.is_severe_disability_dd else DEDUCTION_80DD_NORMAL))
    if ded.sec_80ddb > ZERO:
        breakdown["80DDB"] = str(min(ded.sec_80ddb,
                                     DEDUCTION_80DDB_SENIOR if ded.is_senior_ddb else DEDUCTION_80DDB_BELOW60))
    if ded.sec_80e > ZERO:
        breakdown["80E_education_loan"] = str(ded.sec_80e)
    if ded.sec_80ee > ZERO:
        breakdown["80EE"] = str(min(ded.sec_80ee, DEDUCTION_80EE_LIMIT))
    if ded.sec_80eea > ZERO:
        breakdown["80EEA"] = str(min(ded.sec_80eea, DEDUCTION_80EEA_LIMIT))
    if ded.sec_80g > ZERO:
        breakdown["80G_donations"] = str(ded.sec_80g)
    if ded.sec_80gg > ZERO:
        breakdown["80GG_rent"] = str(min(ded.sec_80gg, DEDUCTION_80GG_LIMIT))
    if ded.sec_80tta > ZERO:
        breakdown["80TTA"] = str(min(ded.sec_80tta, DEDUCTION_80TTA_LIMIT))
    if ded.sec_80ttb > ZERO:
        breakdown["80TTB"] = str(min(ded.sec_80ttb, DEDUCTION_80TTB_LIMIT))
    if ded.sec_80u > ZERO:
        breakdown["80U"] = str(min(ded.sec_80u,
                                   DEDUCTION_80U_SEVERE if ded.is_severe_disability_u else DEDUCTION_80U_NORMAL))
    breakdown["total_deductions"] = str(total)
    return breakdown


def get_section80_deductions_reference() -> List[Dict[str, Any]]:
    """
    Return a comprehensive reference of all Section 80 deductions
    with limits, eligibility, and documentation requirements.
    """
    return [
        {
            "section": "80C",
            "description": "Life insurance, PPF, ELSS, NSC, Sukanya Samriddhi, tuition fees, home loan principal",
            "limit": "Rs. 1,50,000 (aggregate with 80CCC + 80CCD(1))",
            "eligible": "Individual / HUF",
            "documents": ["Premium receipts", "PPF passbook", "ELSS statement", "NSC certificate",
                          "Tuition fee receipts", "Home loan principal certificate"],
            "new_regime": False,
        },
        {
            "section": "80CCC",
            "description": "Contribution to pension fund of LIC or other insurer",
            "limit": "Rs. 1,50,000 (part of 80C aggregate)",
            "eligible": "Individual",
            "documents": ["Pension fund contribution receipt"],
            "new_regime": False,
        },
        {
            "section": "80CCD(1)",
            "description": "Employee contribution to NPS",
            "limit": "10% of salary (14% for central govt), part of 80C aggregate",
            "eligible": "Individual (salaried or self-employed)",
            "documents": ["NPS contribution statement (CRA)"],
            "new_regime": False,
        },
        {
            "section": "80CCD(1B)",
            "description": "Additional NPS contribution",
            "limit": "Rs. 50,000 (over and above 80C limit)",
            "eligible": "Individual",
            "documents": ["NPS Tier-I contribution statement"],
            "new_regime": False,
        },
        {
            "section": "80CCD(2)",
            "description": "Employer contribution to NPS",
            "limit": "14% of salary (central govt) / 10% of salary (others)",
            "eligible": "Individual (salaried)",
            "documents": ["Form 16 / employer NPS certificate"],
            "new_regime": True,  # Allowed in new regime
        },
        {
            "section": "80D",
            "description": "Health insurance premium (mediclaim)",
            "limit": "Self/family: Rs. 25,000 (Rs. 50,000 if senior). Parents: Rs. 25,000 (Rs. 50,000 if senior). "
                     "Preventive health check-up: Rs. 5,000 within overall limit",
            "eligible": "Individual / HUF",
            "documents": ["Mediclaim premium receipt", "Health check-up bills"],
            "new_regime": False,
        },
        {
            "section": "80DD",
            "description": "Medical treatment of disabled dependent",
            "limit": "Rs. 75,000 (normal) / Rs. 1,25,000 (severe — 80%+ disability)",
            "eligible": "Resident Individual / HUF",
            "documents": ["Medical certificate from govt hospital", "Form 10-IA"],
            "new_regime": False,
        },
        {
            "section": "80DDB",
            "description": "Medical treatment of specified diseases (cancer, neurological, AIDS, etc.)",
            "limit": "Rs. 40,000 (Rs. 1,00,000 for senior citizens)",
            "eligible": "Resident Individual / HUF",
            "documents": ["Prescription from specialist", "Form 10-I"],
            "new_regime": False,
        },
        {
            "section": "80E",
            "description": "Interest on education loan (higher education)",
            "limit": "No limit — full interest deductible for 8 years from repayment start",
            "eligible": "Individual only",
            "documents": ["Interest certificate from bank/NBFC"],
            "new_regime": False,
        },
        {
            "section": "80EE",
            "description": "Interest on housing loan — first-time home buyer (loan sanctioned FY 2016-17)",
            "limit": "Rs. 50,000 (over and above Section 24(b)). Conditions: loan <= 35L, property value <= 50L",
            "eligible": "Individual",
            "documents": ["Home loan interest certificate", "Property registration"],
            "new_regime": False,
        },
        {
            "section": "80EEA",
            "description": "Interest on affordable housing loan (loan sanctioned Apr 2019 - Mar 2022)",
            "limit": "Rs. 1,50,000 (stamp value <= 45L)",
            "eligible": "Individual (no other residential property on sanction date)",
            "documents": ["Home loan interest certificate", "Stamp duty valuation"],
            "new_regime": False,
        },
        {
            "section": "80G",
            "description": "Donations to specified funds/charitable institutions",
            "limit": "100% or 50% deduction, with or without qualifying limit (10% of adjusted GTI)",
            "eligible": "All assessees",
            "documents": ["Donation receipt with 80G registration number", "Form 10BE"],
            "new_regime": False,
        },
        {
            "section": "80GG",
            "description": "Rent paid — for those not receiving HRA",
            "limit": "Least of: Rs. 5,000/month, 25% of total income, or (rent paid - 10% of total income)",
            "eligible": "Individual (not receiving HRA, no owned residential property in same city)",
            "documents": ["Rent receipts", "Rental agreement", "Form 10BA declaration"],
            "new_regime": False,
        },
        {
            "section": "80TTA",
            "description": "Interest on savings bank account",
            "limit": "Rs. 10,000",
            "eligible": "Individual / HUF (not senior citizen)",
            "documents": ["Bank passbook / statement showing interest"],
            "new_regime": False,
        },
        {
            "section": "80TTB",
            "description": "Interest income — deposits (savings, FD, RD, post office) for senior citizens",
            "limit": "Rs. 50,000",
            "eligible": "Resident senior citizen (60+)",
            "documents": ["Interest certificates from banks/post office"],
            "new_regime": False,
        },
        {
            "section": "80U",
            "description": "Person with disability (self)",
            "limit": "Rs. 75,000 (normal) / Rs. 1,25,000 (severe — 80%+ disability)",
            "eligible": "Resident Individual",
            "documents": ["Disability certificate from medical authority", "Form 10-IA"],
            "new_regime": False,
        },
    ]


# ---------------------------------------------------------------------------
# 3. Schedule Computations
# ---------------------------------------------------------------------------

# ---- Schedule HP (House Property) ----

def compute_house_property_income(properties: List[HousePropertyInput]) -> Dict[str, Any]:
    """
    Compute income/loss from house property for all properties.
    Handles self-occupied, let-out, and deemed let-out properties.

    Key rules:
    - Self-occupied: GAV = Nil, interest deduction capped at ₹2L
    - Let-out: GAV = higher of actual rent or expected rent
    - Standard deduction: 30% of NAV
    - Loss from HP can be set off against other heads up to ₹2L
    """
    results = []
    total_hp_income = ZERO
    self_occupied_count = 0

    for i, prop in enumerate(properties):
        prop_result = {}
        prop_result["property_number"] = i + 1
        prop_result["property_type"] = prop.property_type.value

        if prop.property_type == PropertyType.SELF_OCCUPIED:
            self_occupied_count += 1
            if self_occupied_count > 2:
                # From AY 2020-21, max 2 self-occupied properties
                prop_result["note"] = ("Only 2 properties can be treated as self-occupied. "
                                       "This property will be deemed let-out.")
                # Treat as deemed let-out
                nav = _compute_nav_let_out(prop)
                standard_ded = _round_currency(nav * HP_STANDARD_DEDUCTION_RATE / HUNDRED)
                interest = prop.interest_on_borrowed_capital + prop.pre_construction_interest
                hp_income = nav - standard_ded - interest
            else:
                # Self-occupied: GAV = Nil
                nav = ZERO
                standard_ded = ZERO
                interest = min(
                    prop.interest_on_borrowed_capital + prop.pre_construction_interest,
                    SEC_24B_SELF_OCCUPIED_LIMIT
                )
                hp_income = ZERO - interest  # Will be negative (loss)

            prop_result["gross_annual_value"] = "0 (Self-occupied)"
            prop_result["net_annual_value"] = str(nav)
            prop_result["standard_deduction_30pct"] = str(standard_ded)
            prop_result["interest_on_borrowed_capital"] = str(interest)
            if prop.pre_construction_interest > ZERO:
                prop_result["pre_construction_interest_included"] = str(prop.pre_construction_interest)
                prop_result["pre_construction_note"] = "1/5th of pre-construction interest allowed for 5 years"
            prop_result["income_from_property"] = str(hp_income)

        elif prop.property_type in (PropertyType.LET_OUT, PropertyType.DEEMED_LET_OUT):
            nav = _compute_nav_let_out(prop)
            standard_ded = _round_currency(nav * HP_STANDARD_DEDUCTION_RATE / HUNDRED)
            interest = prop.interest_on_borrowed_capital + prop.pre_construction_interest
            hp_income = nav - standard_ded - interest

            prop_result["gross_annual_value"] = str(prop.gross_annual_value)
            prop_result["rent_received"] = str(prop.rent_received)
            prop_result["fair_rent"] = str(prop.fair_rent)
            prop_result["municipal_taxes"] = str(prop.municipal_taxes_paid)
            prop_result["net_annual_value"] = str(nav)
            prop_result["standard_deduction_30pct"] = str(standard_ded)
            prop_result["interest_on_borrowed_capital"] = str(interest)
            prop_result["income_from_property"] = str(hp_income)

        results.append(prop_result)
        total_hp_income += hp_income

    # Loss from house property set-off limit
    loss_setoff_limit = D("-200000")
    carried_forward_loss = ZERO
    if total_hp_income < loss_setoff_limit:
        carried_forward_loss = total_hp_income - loss_setoff_limit
        total_hp_income_for_gti = loss_setoff_limit
    else:
        total_hp_income_for_gti = total_hp_income

    return {
        "properties": results,
        "total_hp_income": str(total_hp_income),
        "hp_income_for_gti": str(total_hp_income_for_gti),
        "loss_carried_forward": str(carried_forward_loss),
        "loss_setoff_note": (
            "Loss from house property can be set off against other income up to Rs. 2,00,000. "
            "Balance loss carried forward for 8 assessment years."
        ) if carried_forward_loss < ZERO else "",
    }


def _compute_nav_let_out(prop: HousePropertyInput) -> D:
    """
    Compute Net Annual Value for let-out / deemed let-out property.
    GAV = higher of (actual rent received, fair rent/standard rent — whichever is higher)
    NAV = GAV - Municipal taxes - Unrealised rent
    """
    # Expected rent = higher of fair rent and standard rent (but not exceeding municipal value)
    expected_rent = max(prop.fair_rent, prop.standard_rent)
    # GAV = higher of actual rent and expected rent
    gav = max(prop.rent_received, expected_rent)
    if prop.gross_annual_value > ZERO:
        gav = max(gav, prop.gross_annual_value)
    # NAV = GAV - Municipal taxes paid - Unrealised rent
    nav = max(ZERO, gav - prop.municipal_taxes_paid - prop.unrealised_rent)
    return nav


# ---- Schedule CG (Capital Gains) ----

def compute_capital_gains(transactions: List[CapitalGainInput]) -> Dict[str, Any]:
    """
    Compute capital gains for multiple asset sale transactions.
    Classifies as STCG/LTCG, applies indexation, computes tax.
    """
    stcg_111a_total = ZERO   # Listed equity with STT
    stcg_normal_total = ZERO  # Other short-term
    ltcg_112a_total = ZERO   # Listed equity with STT
    ltcg_112_total = ZERO    # Other long-term (with indexation)
    transaction_details = []

    for i, txn in enumerate(transactions):
        detail = {"transaction": i + 1, "asset_type": txn.asset_type.value}

        # Determine holding period
        is_long_term = _is_long_term(txn)
        detail["classification"] = "Long-term" if is_long_term else "Short-term"
        detail["sale_consideration"] = str(txn.sale_consideration)
        detail["cost_of_acquisition"] = str(txn.cost_of_acquisition)

        if is_long_term and txn.asset_type not in (AssetType.LISTED_EQUITY,):
            # Apply indexation for non-equity LTCG
            try:
                indexed_cost = get_indexed_cost(
                    txn.cost_of_acquisition, txn.year_of_acquisition, txn.year_of_transfer
                )
                indexed_improvement = ZERO
                if txn.cost_of_improvement > ZERO:
                    indexed_improvement = get_indexed_cost(
                        txn.cost_of_improvement, txn.year_of_acquisition, txn.year_of_transfer
                    )
                detail["indexed_cost_of_acquisition"] = str(indexed_cost)
                detail["indexed_cost_of_improvement"] = str(indexed_improvement)
                total_cost = indexed_cost + indexed_improvement + txn.transfer_expenses
            except ValueError as e:
                detail["indexation_error"] = str(e)
                total_cost = txn.cost_of_acquisition + txn.cost_of_improvement + txn.transfer_expenses
        else:
            total_cost = txn.cost_of_acquisition + txn.cost_of_improvement + txn.transfer_expenses

        detail["transfer_expenses"] = str(txn.transfer_expenses)
        gain = txn.sale_consideration - total_cost
        detail["capital_gain_before_exemption"] = str(gain)

        # Apply exemptions
        if txn.exemption_54 > ZERO:
            detail["exemption_section"] = txn.exemption_section
            detail["exemption_amount"] = str(txn.exemption_54)
            gain = max(ZERO, gain - txn.exemption_54)

        detail["taxable_capital_gain"] = str(gain)

        # Classify for tax computation
        if is_long_term:
            if txn.asset_type == AssetType.LISTED_EQUITY and txn.is_stt_paid:
                detail["tax_section"] = "Section 112A (10% above Rs. 1L exemption)"
                ltcg_112a_total += gain
            else:
                detail["tax_section"] = "Section 112 (20% with indexation)"
                ltcg_112_total += gain
        else:
            if txn.asset_type == AssetType.LISTED_EQUITY and txn.is_stt_paid:
                detail["tax_section"] = "Section 111A (15%)"
                stcg_111a_total += gain
            else:
                detail["tax_section"] = "Normal slab rates"
                stcg_normal_total += gain

        transaction_details.append(detail)

    return {
        "transactions": transaction_details,
        "summary": {
            "stcg_111a": str(stcg_111a_total),
            "stcg_normal": str(stcg_normal_total),
            "ltcg_112a": str(ltcg_112a_total),
            "ltcg_112": str(ltcg_112_total),
            "total_stcg": str(stcg_111a_total + stcg_normal_total),
            "total_ltcg": str(ltcg_112a_total + ltcg_112_total),
            "total_capital_gains": str(stcg_111a_total + stcg_normal_total + ltcg_112a_total + ltcg_112_total),
        },
        "tax_rates_applicable": {
            "stcg_111a": "15% (listed equity with STT)",
            "stcg_normal": "As per applicable slab rates",
            "ltcg_112a": "10% above Rs. 1,00,000 exemption (listed equity with STT)",
            "ltcg_112": "20% with indexation benefit (other assets)",
        },
    }


def _is_long_term(txn: CapitalGainInput) -> bool:
    """
    Determine if capital gain is long-term based on holding period.
    Uses actual dates if available, otherwise uses financial years.
    """
    if txn.purchase_date and txn.sale_date:
        holding_days = (txn.sale_date - txn.purchase_date).days
        holding_months = holding_days / 30.44  # Average days per month

        threshold_months = {
            AssetType.LISTED_EQUITY: HOLDING_PERIOD_EQUITY,
            AssetType.IMMOVABLE_PROPERTY: HOLDING_PERIOD_IMMOVABLE,
            AssetType.UNLISTED_SHARES: HOLDING_PERIOD_UNLISTED,
            AssetType.DEBT_MUTUAL_FUND: HOLDING_PERIOD_OTHERS,
            AssetType.GOLD: HOLDING_PERIOD_OTHERS,
            AssetType.OTHER: HOLDING_PERIOD_OTHERS,
        }.get(txn.asset_type, HOLDING_PERIOD_OTHERS)

        return holding_months > threshold_months

    # Fallback: compare financial years (rough estimation)
    if txn.year_of_acquisition and txn.year_of_transfer:
        try:
            acq_start_year = int(txn.year_of_acquisition.split("-")[0])
            tfr_start_year = int(txn.year_of_transfer.split("-")[0])
            year_diff = tfr_start_year - acq_start_year

            if txn.asset_type == AssetType.LISTED_EQUITY:
                return year_diff >= 1
            elif txn.asset_type in (AssetType.IMMOVABLE_PROPERTY, AssetType.UNLISTED_SHARES):
                return year_diff >= 2
            else:
                return year_diff >= 3
        except (ValueError, IndexError):
            pass

    return False  # Default to short-term if cannot determine


def get_holding_period_reference() -> Dict[str, str]:
    """Return holding period thresholds for all asset types."""
    return {
        "Listed equity shares / equity MF (STT paid)": f"{HOLDING_PERIOD_EQUITY} months",
        "Unlisted shares": f"{HOLDING_PERIOD_UNLISTED} months",
        "Immovable property (land/building)": f"{HOLDING_PERIOD_IMMOVABLE} months",
        "Debt mutual funds": f"{HOLDING_PERIOD_OTHERS} months",
        "Gold / gold ETF / sovereign gold bonds": f"{HOLDING_PERIOD_OTHERS} months",
        "Other assets": f"{HOLDING_PERIOD_OTHERS} months",
    }


# ---- Schedule BP (Business Profits) ----

def compute_business_income(inputs: BusinessIncomeInput) -> Dict[str, Any]:
    """
    Compute income from business/profession.
    Handles presumptive taxation (44AD, 44ADA, 44AE) and regular computation.
    """
    if inputs.is_presumptive:
        return _compute_presumptive_income(inputs)
    else:
        return _compute_regular_business_income(inputs)


def _compute_presumptive_income(inputs: BusinessIncomeInput) -> Dict[str, Any]:
    """Compute presumptive income under Section 44AD / 44ADA / 44AE."""
    result = {"section": inputs.presumptive_section, "type": "presumptive"}

    if inputs.presumptive_section == "44AD":
        # Section 44AD: 8% of cash turnover + 6% of digital turnover
        cash_income = _round_currency(inputs.cash_turnover * PRESUMPTIVE_44AD_CASH_RATE / HUNDRED)
        digital_income = _round_currency(inputs.digital_turnover * PRESUMPTIVE_44AD_DIGITAL_RATE / HUNDRED)
        total_turnover = inputs.cash_turnover + inputs.digital_turnover

        # Determine applicable turnover limit
        digital_ratio = ZERO
        if total_turnover > ZERO:
            digital_ratio = inputs.digital_turnover * HUNDRED / total_turnover

        if digital_ratio > D("95"):
            limit = PRESUMPTIVE_44AD_TURNOVER_LIMIT
            limit_note = "Rs. 3 Cr (digital receipts > 95% of turnover)"
        else:
            limit = PRESUMPTIVE_44AD_TURNOVER_LIMIT_OLD
            limit_note = "Rs. 2 Cr (digital receipts <= 95% of turnover)"

        presumptive_income = cash_income + digital_income

        result.update({
            "gross_turnover": str(total_turnover),
            "cash_turnover": str(inputs.cash_turnover),
            "digital_turnover": str(inputs.digital_turnover),
            "digital_percentage": str(_round_currency(digital_ratio)),
            "turnover_limit": str(limit),
            "turnover_limit_note": limit_note,
            "income_at_8pct_cash": str(cash_income),
            "income_at_6pct_digital": str(digital_income),
            "presumptive_income": str(presumptive_income),
            "eligible": total_turnover <= limit,
        })

        if total_turnover > limit:
            result["warning"] = (
                f"Turnover Rs. {total_turnover:,.0f} exceeds limit of {limit_note}. "
                f"Section 44AD not available. Must maintain books u/s 44AA and get audit u/s 44AB."
            )

    elif inputs.presumptive_section == "44ADA":
        # Section 44ADA: 50% of gross receipts for professionals
        presumptive_income = _round_currency(
            inputs.gross_receipts_profession * PRESUMPTIVE_44ADA_RATE / HUNDRED
        )

        result.update({
            "gross_receipts": str(inputs.gross_receipts_profession),
            "presumptive_rate": "50%",
            "presumptive_income": str(presumptive_income),
            "receipts_limit": str(PRESUMPTIVE_44ADA_GROSS_LIMIT),
            "eligible": inputs.gross_receipts_profession <= PRESUMPTIVE_44ADA_GROSS_LIMIT,
        })

        if inputs.gross_receipts_profession > PRESUMPTIVE_44ADA_GROSS_LIMIT:
            result["warning"] = (
                f"Gross receipts Rs. {inputs.gross_receipts_profession:,.0f} exceed Rs. 75L limit. "
                f"Section 44ADA not available."
            )

    elif inputs.presumptive_section == "44AE":
        # Section 44AE: per vehicle per month
        heavy_income = (D(str(inputs.number_of_heavy_vehicles))
                        * PRESUMPTIVE_44AE_PER_HEAVY
                        * D(str(inputs.months_owned)))
        other_income = (D(str(inputs.number_of_other_vehicles))
                        * PRESUMPTIVE_44AE_PER_OTHER
                        * D(str(inputs.months_owned)))
        presumptive_income = heavy_income + other_income

        result.update({
            "heavy_goods_vehicles": inputs.number_of_heavy_vehicles,
            "other_vehicles": inputs.number_of_other_vehicles,
            "months_owned": inputs.months_owned,
            "income_per_heavy_vehicle_per_month": str(PRESUMPTIVE_44AE_PER_HEAVY),
            "income_per_other_vehicle_per_month": str(PRESUMPTIVE_44AE_PER_OTHER),
            "total_heavy_vehicle_income": str(heavy_income),
            "total_other_vehicle_income": str(other_income),
            "presumptive_income": str(presumptive_income),
            "eligible": (inputs.number_of_heavy_vehicles + inputs.number_of_other_vehicles) <= 10,
        })

        total_vehicles = inputs.number_of_heavy_vehicles + inputs.number_of_other_vehicles
        if total_vehicles > 10:
            result["warning"] = (
                f"Total vehicles ({total_vehicles}) exceed limit of 10. "
                f"Section 44AE not available."
            )

    return result


def _compute_regular_business_income(inputs: BusinessIncomeInput) -> Dict[str, Any]:
    """
    Compute business income under regular provisions.
    Net profit as per books + add-backs - allowed deductions.
    """
    result = {"type": "regular"}

    net_profit = inputs.net_profit_as_per_books

    # Add-backs (disallowances)
    total_addbacks = ZERO
    addback_details = {}

    # Standard disallowances
    common_disallowances = {
        "40a_ia_tds_default": "Section 40(a)(ia) — TDS not deducted/deposited on specified payments",
        "40a_i_tds_non_resident": "Section 40(a)(i) — TDS not deducted on payments to non-residents",
        "40a_3_cash_above_10k": "Section 40A(3) — Cash payment exceeding Rs. 10,000 to a single person in a day",
        "43b_statutory_dues": "Section 43B — Statutory dues (PF, ESI, GST) not paid before due date of return",
        "40b_partner_remuneration": "Section 40(b) — Partner remuneration exceeding allowed limits",
        "37_1_personal_expenses": "Section 37(1) — Personal or non-business expenditure",
        "40_a_v_head_office_expenses": "Section 40(a)(v) — Head office expenses of non-resident",
        "36_1_xii_bad_debts": "Section 36(1)(vii) — Bad debts not written off in books",
    }

    for key, description in common_disallowances.items():
        amount = inputs.disallowances.get(key, ZERO)
        if amount > ZERO:
            total_addbacks += amount
            addback_details[key] = {"description": description, "amount": str(amount)}

    # Any additional custom disallowances
    for key, amount in inputs.disallowances.items():
        if key not in common_disallowances and amount > ZERO:
            total_addbacks += amount
            addback_details[key] = {"description": f"Disallowance — {key}", "amount": str(amount)}

    # Depreciation adjustment
    depreciation_addback = inputs.depreciation_as_per_books  # Add back book depreciation
    depreciation_allowed = inputs.depreciation_as_per_it      # Deduct IT depreciation
    depreciation_difference = depreciation_addback - depreciation_allowed

    # Income not credited to P&L
    income_not_credited = inputs.income_not_credited

    # Exempt income debited to P&L (add back)
    exempt_debited = inputs.exempt_income_debited

    # Compute taxable business income
    business_income = (
        net_profit
        + total_addbacks
        + depreciation_addback
        - depreciation_allowed
        + income_not_credited
        + exempt_debited
    )

    result.update({
        "net_profit_as_per_books": str(net_profit),
        "add_backs": addback_details,
        "total_add_backs": str(total_addbacks),
        "depreciation_as_per_books": str(depreciation_addback),
        "depreciation_as_per_it_act": str(depreciation_allowed),
        "depreciation_difference": str(depreciation_difference),
        "income_not_credited_to_pl": str(income_not_credited),
        "exempt_income_debited_to_pl": str(exempt_debited),
        "taxable_business_income": str(business_income),
    })

    return result


# ---------------------------------------------------------------------------
# 4. Advance Tax Calculator
# ---------------------------------------------------------------------------

def compute_advance_tax(
    total_tax_liability: D,
    tds_credits: List[TDSEntry] = None,
    advance_payments: List[AdvanceTaxPayment] = None,
    is_senior_no_business: bool = False,
) -> Dict[str, Any]:
    """
    Compute advance tax installments, and interest u/s 234B and 234C.

    Rules:
    - Senior citizens (60+) without business income are exempt from advance tax
    - Advance tax not required if total tax liability < Rs. 10,000
    - Interest u/s 234B: 1% per month on shortfall (if paid < 90% of assessed tax)
    - Interest u/s 234C: 1% per month on deferment of each installment
    """
    if tds_credits is None:
        tds_credits = []
    if advance_payments is None:
        advance_payments = []

    total_tds = sum(t.amount for t in tds_credits)
    net_tax_after_tds = max(ZERO, total_tax_liability - total_tds)

    result = {
        "total_tax_liability": str(total_tax_liability),
        "total_tds_credits": str(total_tds),
        "net_tax_after_tds": str(net_tax_after_tds),
    }

    # Check exemptions
    if is_senior_no_business:
        result["advance_tax_required"] = False
        result["reason"] = "Senior citizen (60+) without business income — exempt from advance tax u/s 207"
        return result

    if net_tax_after_tds < D("10000"):
        result["advance_tax_required"] = False
        result["reason"] = "Net tax liability < Rs. 10,000 — advance tax not required u/s 208"
        return result

    result["advance_tax_required"] = True

    # Compute required installments
    installments = []
    for due_date_str, cum_percent in ADVANCE_TAX_SCHEDULE:
        required_amount = _round_currency(net_tax_after_tds * cum_percent / HUNDRED)
        installment_amount = required_amount
        if installments:
            installment_amount = required_amount - D(installments[-1]["cumulative_required"])
        installments.append({
            "due_date": due_date_str,
            "cumulative_percent": str(cum_percent),
            "cumulative_required": str(required_amount),
            "installment_amount": str(installment_amount),
        })

    result["installment_schedule"] = installments

    # Compute actual payments against due dates
    total_advance_paid = sum(p.amount for p in advance_payments)
    result["total_advance_tax_paid"] = str(total_advance_paid)

    # ---- Interest u/s 234C (Deferment) ----
    interest_234c = _compute_234c_interest(net_tax_after_tds, advance_payments)
    result["interest_234c"] = interest_234c

    # ---- Interest u/s 234B (Default) ----
    interest_234b = _compute_234b_interest(net_tax_after_tds, total_advance_paid)
    result["interest_234b"] = interest_234b

    return result


def _compute_234c_interest(assessed_tax: D, payments: List[AdvanceTaxPayment]) -> Dict[str, Any]:
    """
    Compute interest u/s 234C for deferment of advance tax installments.
    1% per month (simple) for 3 months on shortfall in each quarter.
    """
    if assessed_tax <= ZERO:
        return {"total_interest": "0", "details": []}

    # Sort payments by date
    sorted_payments = sorted(payments, key=lambda p: p.date_paid)

    # Due dates and cumulative percentages
    due_dates = [
        (date(2024, 6, 15), D("15")),
        (date(2024, 9, 15), D("45")),
        (date(2024, 12, 15), D("75")),
        (date(2025, 3, 15), D("100")),
    ]

    total_interest = ZERO
    details = []
    cumulative_paid = ZERO

    for due_date, cum_pct in due_dates:
        required = _round_currency(assessed_tax * cum_pct / HUNDRED)

        # Sum payments up to this due date
        for payment in sorted_payments:
            if payment.date_paid <= due_date and payment.amount > ZERO:
                cumulative_paid += payment.amount
                # Mark as counted (avoid double counting)
                payment.amount = ZERO

        shortfall = max(ZERO, required - cumulative_paid)

        if shortfall > ZERO:
            # 1% per month for 3 months
            months = 3
            interest = _round_currency(shortfall * INTEREST_234C_RATE / HUNDRED * D(str(months)))
            total_interest += interest
            details.append({
                "due_date": due_date.isoformat(),
                "required": str(required),
                "paid_by_date": str(cumulative_paid),
                "shortfall": str(shortfall),
                "interest_months": months,
                "interest_amount": str(interest),
            })
        else:
            details.append({
                "due_date": due_date.isoformat(),
                "required": str(required),
                "paid_by_date": str(cumulative_paid),
                "shortfall": "0",
                "interest_amount": "0",
            })

    return {"total_interest": str(total_interest), "details": details}


def _compute_234b_interest(assessed_tax: D, total_advance_paid: D) -> Dict[str, Any]:
    """
    Compute interest u/s 234B for default in payment of advance tax.
    Applicable when advance tax paid < 90% of assessed tax.
    1% per month from April of AY to date of determination/payment.
    """
    if assessed_tax <= ZERO:
        return {"applicable": False, "interest": "0"}

    threshold = _round_currency(assessed_tax * D("90") / HUNDRED)

    if total_advance_paid >= threshold:
        return {
            "applicable": False,
            "assessed_tax": str(assessed_tax),
            "advance_tax_paid": str(total_advance_paid),
            "ninety_percent_threshold": str(threshold),
            "interest": "0",
            "note": "Advance tax paid >= 90% of assessed tax. No 234B interest.",
        }

    shortfall = assessed_tax - total_advance_paid

    # Interest from April 1 of AY to date of determination
    # Assume determination by July 31 (due date of return) = 4 months
    months = 4  # Apr, May, Jun, Jul (typical)
    interest = _round_currency(shortfall * INTEREST_234B_RATE / HUNDRED * D(str(months)))

    return {
        "applicable": True,
        "assessed_tax": str(assessed_tax),
        "advance_tax_paid": str(total_advance_paid),
        "ninety_percent_threshold": str(threshold),
        "shortfall": str(shortfall),
        "interest_months": months,
        "interest_rate": "1% per month",
        "interest": str(interest),
        "note": (
            f"Advance tax paid (Rs. {total_advance_paid:,.0f}) is less than 90% of "
            f"assessed tax (Rs. {threshold:,.0f}). Interest u/s 234B applicable on "
            f"shortfall of Rs. {shortfall:,.0f}."
        ),
    }


# ---------------------------------------------------------------------------
# 5. Cost Inflation Index — Exposed via function
# ---------------------------------------------------------------------------

def get_cii_table() -> Dict[str, int]:
    """Return the full Cost Inflation Index table from 2001-02 onwards."""
    return dict(COST_INFLATION_INDEX)


def compute_indexed_cost_of_acquisition(
    cost: D,
    year_of_acquisition: str,
    year_of_transfer: str = FY,
    cost_of_improvement: D = ZERO,
    year_of_improvement: str = "",
) -> Dict[str, Any]:
    """
    Compute indexed cost of acquisition and improvement.

    Returns detailed computation with CII values used.
    """
    result = {
        "original_cost": str(cost),
        "year_of_acquisition": year_of_acquisition,
        "year_of_transfer": year_of_transfer,
    }

    try:
        cii_transfer = get_cii(year_of_transfer)
        cii_acquisition = get_cii(year_of_acquisition)

        indexed_cost = _round_currency(cost * D(str(cii_transfer)) / D(str(cii_acquisition)))

        result.update({
            "cii_acquisition_year": cii_acquisition,
            "cii_transfer_year": cii_transfer,
            "indexed_cost_of_acquisition": str(indexed_cost),
            "formula": f"({cost} x {cii_transfer}) / {cii_acquisition} = {indexed_cost}",
        })

        if cost_of_improvement > ZERO and year_of_improvement:
            cii_improvement = get_cii(year_of_improvement)
            indexed_improvement = _round_currency(
                cost_of_improvement * D(str(cii_transfer)) / D(str(cii_improvement))
            )
            result.update({
                "cost_of_improvement": str(cost_of_improvement),
                "year_of_improvement": year_of_improvement,
                "cii_improvement_year": cii_improvement,
                "indexed_cost_of_improvement": str(indexed_improvement),
                "total_indexed_cost": str(indexed_cost + indexed_improvement),
            })
        else:
            result["total_indexed_cost"] = str(indexed_cost)

    except ValueError as e:
        result["error"] = str(e)

    return result


# ---------------------------------------------------------------------------
# 6. Depreciation Calculator
# ---------------------------------------------------------------------------

def compute_depreciation(
    assets: List[DepreciationAsset],
    assessment_year: str = AY,
) -> Dict[str, Any]:
    """
    Compute depreciation under Income Tax Act using WDV (Written Down Value) method.

    Rules:
    - Normal depreciation at prescribed rates
    - Additional depreciation u/s 32(1)(iia) at 20% for new P&M in manufacturing
    - Assets acquired in 2nd half (Oct-Mar): 50% depreciation for first year
    - Sale proceeds deducted from block; if block becomes negative, treated as STCG
    """
    block_results = []
    total_depreciation = ZERO
    total_additional_dep = ZERO
    stcg_on_blocks = ZERO

    for asset in assets:
        block = _compute_block_depreciation(asset)
        block_results.append(block)
        total_depreciation += _to_decimal(block.get("normal_depreciation", "0"))
        total_additional_dep += _to_decimal(block.get("additional_depreciation", "0"))
        stcg_on_blocks += _to_decimal(block.get("stcg_on_block", "0"))

    return {
        "assessment_year": assessment_year,
        "blocks": block_results,
        "summary": {
            "total_normal_depreciation": str(total_depreciation),
            "total_additional_depreciation": str(total_additional_dep),
            "total_depreciation_allowed": str(total_depreciation + total_additional_dep),
            "stcg_on_depreciable_assets": str(stcg_on_blocks),
        },
        "notes": [
            "Depreciation computed using Written Down Value (WDV) method",
            "Assets used for less than 180 days: 50% of normal depreciation",
            "Additional depreciation u/s 32(1)(iia): 20% on new plant/machinery in manufacturing",
            "If WDV of block becomes nil/negative due to sales, excess is STCG u/s 50",
        ],
    }


def _compute_block_depreciation(asset: DepreciationAsset) -> Dict[str, Any]:
    """Compute depreciation for a single asset block."""
    rate_info = DEPRECIATION_RATES.get(asset.asset_category)
    if rate_info is None:
        return {
            "error": f"Unknown asset category: {asset.asset_category}",
            "valid_categories": list(DEPRECIATION_RATES.keys()),
        }

    dep_rate = rate_info["rate"]
    description = rate_info["description"]

    result = {
        "asset_category": asset.asset_category,
        "description": description if not asset.description else asset.description,
        "depreciation_rate": str(dep_rate) + "%",
    }

    # Opening WDV + Additions - Sale
    opening = asset.opening_wdv
    additions_full = asset.additions_first_half   # Before Oct 1 — full rate
    additions_half = asset.additions_second_half   # On/after Oct 1 — half rate
    total_additions = additions_full + additions_half
    sales = asset.sale_proceeds

    result["opening_wdv"] = str(opening)
    result["additions_first_half"] = str(additions_full)
    result["additions_second_half"] = str(additions_half)
    result["total_additions"] = str(total_additions)
    result["sale_proceeds"] = str(sales)

    # Check if block is wiped out by sales
    wdv_before_dep = opening + total_additions - sales
    result["wdv_before_depreciation"] = str(wdv_before_dep)

    if wdv_before_dep < ZERO:
        # Excess of sale over WDV + additions = STCG u/s 50
        stcg = abs(wdv_before_dep)
        result["stcg_on_block"] = str(stcg)
        result["normal_depreciation"] = "0"
        result["additional_depreciation"] = "0"
        result["closing_wdv"] = "0"
        result["note"] = (
            f"Sale proceeds exceed WDV + additions by Rs. {stcg:,.0f}. "
            f"This excess is Short-Term Capital Gain u/s 50."
        )
        return result

    if wdv_before_dep == ZERO:
        result["stcg_on_block"] = "0"
        result["normal_depreciation"] = "0"
        result["additional_depreciation"] = "0"
        result["closing_wdv"] = "0"
        result["note"] = "Block of assets fully transferred. No depreciation."
        return result

    # Normal depreciation
    # Full rate on (opening + additions_first_half - sales)
    base_full_rate = max(ZERO, opening + additions_full - sales)
    dep_on_full = _round_currency(base_full_rate * dep_rate / HUNDRED)

    # Half rate on additions_second_half (50% for first year)
    dep_on_half = _round_currency(additions_half * dep_rate / HUNDRED / D("2"))

    normal_depreciation = dep_on_full + dep_on_half
    result["normal_depreciation"] = str(normal_depreciation)
    result["dep_on_full_year_assets"] = str(dep_on_full)
    result["dep_on_half_year_assets"] = str(dep_on_half)

    # Additional depreciation u/s 32(1)(iia)
    additional_dep = ZERO
    if asset.is_new_manufacturing_asset:
        # Additional depreciation on new additions only
        additional_dep_full = _round_currency(additions_full * ADDITIONAL_DEPRECIATION_RATE / HUNDRED)
        additional_dep_half = _round_currency(
            additions_half * ADDITIONAL_DEPRECIATION_RATE / HUNDRED / D("2")
        )
        additional_dep = additional_dep_full + additional_dep_half
        result["additional_depreciation"] = str(additional_dep)
        result["additional_dep_full_year"] = str(additional_dep_full)
        result["additional_dep_half_year"] = str(additional_dep_half)
        result["additional_depreciation_note"] = (
            "Additional depreciation u/s 32(1)(iia) @ 20% on new plant/machinery "
            "acquired and installed for manufacturing"
        )
    else:
        result["additional_depreciation"] = "0"

    # Closing WDV
    total_dep = normal_depreciation + additional_dep
    closing_wdv = max(ZERO, wdv_before_dep - total_dep)
    result["total_depreciation"] = str(total_dep)
    result["closing_wdv"] = str(closing_wdv)
    result["stcg_on_block"] = "0"

    return result


def get_depreciation_rates_reference() -> List[Dict[str, str]]:
    """Return all IT Act depreciation rates as a reference table."""
    return [
        {"category": k, "rate": str(v["rate"]) + "%", "description": v["description"]}
        for k, v in DEPRECIATION_RATES.items()
    ]


# ---------------------------------------------------------------------------
# Full Tax Computation — Convenience Wrapper
# ---------------------------------------------------------------------------

def compute_full_tax(
    assessee_type: str = "individual",
    age_bracket: str = "general",
    salary_gross: D = ZERO,
    standard_deduction_applicable: bool = True,
    house_properties: Optional[List[HousePropertyInput]] = None,
    business_input: Optional[BusinessIncomeInput] = None,
    capital_gain_transactions: Optional[List[CapitalGainInput]] = None,
    other_sources_income: D = ZERO,
    deductions: Optional[Section80Deductions] = None,
    tds_entries: Optional[List[TDSEntry]] = None,
    advance_payments: Optional[List[AdvanceTaxPayment]] = None,
    company_section: str = "",
) -> Dict[str, Any]:
    """
    End-to-end tax computation combining all schedules.
    Computes under both regimes (for individuals/HUFs) and recommends optimal.
    """
    result = {
        "financial_year": FY,
        "assessment_year": AY,
        "assessee_type": assessee_type,
    }

    # ---- Salary Income ----
    salary_income = salary_gross
    salary_details = {"gross_salary": str(salary_gross)}
    if standard_deduction_applicable and salary_gross > ZERO:
        # Standard deduction will be applied per regime in compare_regimes
        # For now, compute with old regime standard deduction
        salary_income_old = max(ZERO, salary_gross - STANDARD_DEDUCTION_OLD_REGIME)
        salary_income_new = max(ZERO, salary_gross - STANDARD_DEDUCTION_NEW_REGIME)
        salary_details["standard_deduction_old"] = str(STANDARD_DEDUCTION_OLD_REGIME)
        salary_details["standard_deduction_new"] = str(STANDARD_DEDUCTION_NEW_REGIME)
        salary_details["net_salary_old_regime"] = str(salary_income_old)
        salary_details["net_salary_new_regime"] = str(salary_income_new)
    else:
        salary_income_old = salary_gross
        salary_income_new = salary_gross

    result["schedule_salary"] = salary_details

    # ---- House Property ----
    hp_income = ZERO
    if house_properties:
        hp_result = compute_house_property_income(house_properties)
        hp_income = _to_decimal(hp_result["hp_income_for_gti"])
        result["schedule_hp"] = hp_result

    # ---- Business Income ----
    business_income = ZERO
    if business_input:
        bp_result = compute_business_income(business_input)
        if "presumptive_income" in bp_result:
            business_income = _to_decimal(bp_result["presumptive_income"])
        elif "taxable_business_income" in bp_result:
            business_income = _to_decimal(bp_result["taxable_business_income"])
        result["schedule_bp"] = bp_result

    # ---- Capital Gains ----
    stcg_111a = ZERO
    stcg_normal = ZERO
    ltcg_112a = ZERO
    ltcg_112 = ZERO
    if capital_gain_transactions:
        cg_result = compute_capital_gains(capital_gain_transactions)
        summary = cg_result["summary"]
        stcg_111a = _to_decimal(summary["stcg_111a"])
        stcg_normal = _to_decimal(summary["stcg_normal"])
        ltcg_112a = _to_decimal(summary["ltcg_112a"])
        ltcg_112 = _to_decimal(summary["ltcg_112"])
        result["schedule_cg"] = cg_result

    # ---- TDS ----
    tds_total = ZERO
    if tds_entries:
        tds_total = sum(t.amount for t in tds_entries)
        result["tds_credits"] = {
            "total": str(tds_total),
            "entries": [
                {"tan": t.deductor_tan, "amount": str(t.amount),
                 "section": t.section, "quarter": t.quarter}
                for t in tds_entries
            ],
        }

    advance_tax_paid = ZERO
    if advance_payments:
        advance_tax_paid = sum(p.amount for p in advance_payments)

    # ---- Compare Regimes (for individuals / HUFs) ----
    try:
        a_type = AssesseeType(assessee_type.lower())
    except ValueError:
        a_type = AssesseeType.INDIVIDUAL

    if a_type in (AssesseeType.INDIVIDUAL, AssesseeType.HUF):
        # Old regime computation
        comparison = compare_regimes(
            assessee_type=assessee_type,
            salary_income=salary_income_old,
            hp_income=hp_income,
            business_income=business_income,
            stcg_111a=stcg_111a,
            stcg_normal=stcg_normal,
            ltcg_112a=ltcg_112a,
            ltcg_112=ltcg_112,
            other_income=other_sources_income,
            deductions=deductions,
            age_bracket=age_bracket,
            tds_total=tds_total,
            advance_tax_paid=advance_tax_paid,
        )
        result["regime_comparison"] = comparison
        result["recommended_regime"] = comparison["recommended_regime"]
    else:
        # Firms, companies, etc. — single computation
        gti = (salary_income_old + hp_income + business_income +
               stcg_111a + stcg_normal + ltcg_112a + ltcg_112 + other_sources_income)

        tax_result = compute_tax(
            assessee_type=assessee_type,
            regime="old",  # Firms/companies don't have regime choice
            gross_total_income=gti,
            salary_income=salary_income_old,
            hp_income=hp_income,
            business_income=business_income,
            stcg_111a=stcg_111a,
            stcg_normal=stcg_normal,
            ltcg_112a=ltcg_112a,
            ltcg_112=ltcg_112,
            other_income=other_sources_income,
            deductions=deductions,
            age_bracket=age_bracket,
            tds_total=tds_total,
            advance_tax_paid=advance_tax_paid,
            company_section=company_section,
        )
        result["tax_computation"] = {
            "total_tax_liability": str(tax_result.total_tax_liability),
            "net_tax_payable": str(tax_result.net_tax_payable),
            "breakdown": tax_result.breakdown,
        }

    # ---- Advance Tax & Interest ----
    if advance_payments or tds_entries:
        # Use the recommended regime's tax for advance tax calculation
        if "regime_comparison" in result:
            recommended = result["recommended_regime"]
            tax_liability = _to_decimal(
                result["regime_comparison"][f"{recommended}_regime"]["total_tax_liability"]
            )
        else:
            tax_liability = tax_result.total_tax_liability

        advance_result = compute_advance_tax(
            total_tax_liability=tax_liability,
            tds_credits=tds_entries,
            advance_payments=advance_payments,
            is_senior_no_business=(
                age_bracket in ("senior", "super_senior")
                and business_income == ZERO
            ),
        )
        result["advance_tax"] = advance_result

    return result


# ---------------------------------------------------------------------------
# ITR Form Checklist Generator
# ---------------------------------------------------------------------------

def generate_itr_checklist(form: str) -> Dict[str, Any]:
    """
    Generate a comprehensive checklist of documents and information needed
    for filing a specific ITR form.
    """
    common_docs = [
        "PAN card",
        "Aadhaar card",
        "Bank account details (IFSC, account number) for refund",
        "Form 26AS (AIS / TIS) — verify TDS credits",
        "Annual Information Statement (AIS)",
        "Previous year's ITR acknowledgement (if applicable)",
    ]

    form_specific = {
        "ITR-1": {
            "applicable_for": "Resident individual with salary + 1 HP + other sources, income <= Rs. 50L",
            "documents": common_docs + [
                "Form 16 from employer",
                "Salary slips (for HRA / LTA verification)",
                "House property rent agreement + municipal tax receipts",
                "Bank interest certificates (savings + FD)",
                "Section 80C investment proofs (PPF, ELSS, LIC, NSC, tuition fees)",
                "Section 80D mediclaim premium receipts",
                "Home loan interest certificate u/s 24(b)",
                "Section 80G donation receipts (Form 10BE)",
            ],
            "schedules": ["Part B — TI", "Part C — Deductions", "Part D — Tax Computation", "Schedule TDS"],
        },
        "ITR-2": {
            "applicable_for": "Individual/HUF without business income, with capital gains / foreign income / director",
            "documents": common_docs + [
                "Form 16 from employer",
                "Capital gains statements (broker / CAMS / mutual fund)",
                "Property sale deed / purchase deed for immovable property CG",
                "Cost Inflation Index for indexation",
                "Section 54/54F/54EC exemption proofs (new property / bonds)",
                "Foreign income details + DTAA country",
                "Schedule FA — foreign bank accounts, foreign assets",
                "Directorship details (DIN, company name, PAN)",
                "Unlisted share valuation reports",
                "All Section 80 deduction proofs",
                "Asset and liability schedule (if income > Rs. 50L)",
            ],
            "schedules": [
                "Schedule S", "Schedule HP", "Schedule CG", "Schedule OS",
                "Schedule CYLA", "Schedule BFLA", "Schedule VIA",
                "Schedule FA", "Schedule FSI", "Schedule TR",
                "Schedule AL", "Schedule 112A (scrip-wise LTCG)",
            ],
        },
        "ITR-3": {
            "applicable_for": "Individual/HUF with business/profession income (non-presumptive)",
            "documents": common_docs + [
                "Profit & Loss account and Balance Sheet",
                "Tax audit report (Form 3CD) if applicable",
                "Depreciation schedule as per IT Act",
                "TDS certificates (Form 16A)",
                "GST returns for turnover verification",
                "Section 43B compliance (statutory dues payment proof)",
                "Section 40A(3) cash payment register",
                "Capital gains documentation",
                "All Section 80 deduction proofs",
                "MAT/AMT computation working (if applicable)",
            ],
            "schedules": [
                "Schedule S", "Schedule HP", "Schedule BP", "Schedule CG",
                "Schedule OS", "Schedule DPM", "Schedule DOA", "Schedule ESR",
                "Schedule CYLA", "Schedule BFLA", "Schedule VIA",
                "Schedule OI", "Schedule SPI", "Schedule SI",
                "Balance Sheet", "P&L Account",
            ],
        },
        "ITR-4": {
            "applicable_for": "Presumptive income u/s 44AD/44ADA/44AE for Individual/HUF/Firm",
            "documents": common_docs + [
                "Bank statements (for turnover verification)",
                "Cash vs digital receipt breakup",
                "Professional receipts (for 44ADA)",
                "Vehicle registration details (for 44AE)",
                "GST returns (if registered)",
                "Section 80 deduction proofs",
            ],
            "schedules": [
                "Schedule BP (Presumptive)", "Schedule VIA",
                "Schedule S (if salary income)", "Schedule HP (one property only)",
            ],
        },
        "ITR-5": {
            "applicable_for": "Partnership firms, LLPs, AOPs, BOIs",
            "documents": common_docs + [
                "Partnership deed / LLP agreement",
                "P&L account and Balance Sheet (audited if applicable)",
                "Tax audit report Form 3CD",
                "Partner capital account statements",
                "Remuneration and interest to partners working",
                "Section 40(b) computation",
                "TDS certificates",
                "Depreciation schedule",
            ],
            "schedules": [
                "Schedule BP", "Schedule HP", "Schedule CG", "Schedule OS",
                "Schedule DPM", "Schedule CYLA", "Schedule Partners",
            ],
        },
        "ITR-6": {
            "applicable_for": "All companies (not claiming exemption u/s 11)",
            "documents": common_docs + [
                "Audited financial statements",
                "Tax audit report Form 3CD",
                "Board resolution for tax filing",
                "CIN and incorporation details",
                "MAT computation u/s 115JB",
                "Section 115BAA/115BAB option letter",
                "Related party transaction details",
                "Transfer pricing documentation (if applicable)",
                "CSR expenditure details u/s 135",
            ],
            "schedules": [
                "Schedule BP", "Schedule HP", "Schedule CG", "Schedule OS",
                "Schedule DPM", "Schedule DOA", "Schedule ESR",
                "Schedule CYLA", "Schedule MAT", "Schedule OA",
                "Balance Sheet", "P&L Account", "Schedule SH (Shareholding)",
            ],
        },
        "ITR-7": {
            "applicable_for": "Trusts, religious/charitable institutions, political parties, research institutions",
            "documents": common_docs + [
                "Trust deed / Registration certificate",
                "12A / 12AA / 12AB registration",
                "80G registration details",
                "Application of income details",
                "Accumulation details (Form 10)",
                "Voluntary contributions / donations received",
                "Investment schedule",
                "Audit report u/s 12A(1)(b)",
            ],
            "schedules": [
                "Schedule AI", "Schedule VC", "Schedule I",
                "Schedule J (Investments)", "Schedule K (Land/Building)",
            ],
        },
    }

    form_upper = form.upper().replace(" ", "")
    if form_upper not in form_specific:
        return {"error": f"Unknown form: {form}. Valid forms: {list(form_specific.keys())}"}

    return {
        "form": form_upper,
        **form_specific[form_upper],
        "filing_due_dates": {
            "non_audit": "July 31 of Assessment Year",
            "audit_cases": "October 31 of Assessment Year",
            "transfer_pricing": "November 30 of Assessment Year",
            "belated_return": "December 31 of Assessment Year",
            "revised_return": "December 31 of Assessment Year",
        },
    }


# ---------------------------------------------------------------------------
# Quick Tax Estimate (Simplified API)
# ---------------------------------------------------------------------------

def quick_tax_estimate(
    annual_income: D,
    regime: str = "new",
    age_bracket: str = "general",
    deductions_80c: D = ZERO,
    deductions_80d: D = ZERO,
    hra_exemption: D = ZERO,
    home_loan_interest: D = ZERO,
    nps_80ccd_1b: D = ZERO,
) -> Dict[str, Any]:
    """
    Quick single-call tax estimate for salaried individuals.
    Simplified API for common use cases.
    """
    try:
        tax_regime = TaxRegime(regime.lower())
    except ValueError:
        return {"error": f"Invalid regime: {regime}. Use 'old' or 'new'"}

    # Gross salary
    gross = annual_income

    # Standard deduction
    std_ded = STANDARD_DEDUCTION_NEW_REGIME if tax_regime == TaxRegime.NEW else STANDARD_DEDUCTION_OLD_REGIME
    salary_income = max(ZERO, gross - std_ded)

    # HRA exemption (only old regime)
    if tax_regime == TaxRegime.OLD:
        salary_income = max(ZERO, salary_income - hra_exemption)

    # HP loss (only old regime, limited by rules)
    hp_loss = ZERO
    if tax_regime == TaxRegime.OLD and home_loan_interest > ZERO:
        hp_loss = min(home_loan_interest, SEC_24B_SELF_OCCUPIED_LIMIT)

    gti = max(ZERO, salary_income - hp_loss)

    # Deductions
    total_ded = ZERO
    if tax_regime == TaxRegime.OLD:
        total_ded += min(deductions_80c, DEDUCTION_80C_LIMIT)
        total_ded += min(deductions_80d, DEDUCTION_80D_SELF_BELOW60)
        total_ded += min(nps_80ccd_1b, DEDUCTION_80CCD1B_LIMIT)

    taxable = max(ZERO, gti - total_ded)
    taxable = _round_to_nearest_ten(taxable)

    # Tax calculation
    if tax_regime == TaxRegime.NEW:
        tax = _compute_slab_tax(taxable, NEW_REGIME_SLABS)
    else:
        try:
            age = AgeBracket(age_bracket)
        except ValueError:
            age = AgeBracket.GENERAL
        slabs = _get_old_regime_slabs(age)
        tax = _compute_slab_tax(taxable, slabs)

    # Rebate u/s 87A
    rebate = ZERO
    if tax_regime == TaxRegime.NEW and taxable <= REBATE_87A_NEW_REGIME_INCOME_LIMIT:
        rebate = min(tax, REBATE_87A_NEW_REGIME_MAX)
    elif tax_regime == TaxRegime.OLD and taxable <= REBATE_87A_OLD_REGIME_INCOME_LIMIT:
        rebate = min(tax, REBATE_87A_OLD_REGIME_MAX)

    tax_after_rebate = max(ZERO, tax - rebate)

    # Surcharge
    surcharge = ZERO
    if tax_regime == TaxRegime.NEW:
        surcharge = _compute_surcharge(tax_after_rebate, taxable, SURCHARGE_NEW_REGIME)
    else:
        surcharge = _compute_surcharge(tax_after_rebate, taxable, SURCHARGE_OLD_REGIME)

    # Cess
    cess = _compute_cess(tax_after_rebate + surcharge)

    total_tax = _round_currency(tax_after_rebate + surcharge + cess)
    monthly_tax = _round_currency(total_tax / D("12"))
    effective_rate = ZERO
    if annual_income > ZERO:
        effective_rate = (total_tax * HUNDRED / annual_income).quantize(D("0.01"))

    return {
        "annual_income": str(annual_income),
        "regime": regime,
        "standard_deduction": str(std_ded),
        "hra_exemption": str(hra_exemption) if tax_regime == TaxRegime.OLD else "N/A (New Regime)",
        "house_property_loss": str(hp_loss),
        "gross_total_income": str(gti),
        "total_deductions": str(total_ded),
        "taxable_income": str(taxable),
        "tax_on_income": str(tax),
        "rebate_87a": str(rebate),
        "tax_after_rebate": str(tax_after_rebate),
        "surcharge": str(surcharge),
        "cess": str(cess),
        "total_tax_liability": str(total_tax),
        "monthly_tax_outgo": str(monthly_tax),
        "effective_tax_rate": str(effective_rate) + "%",
    }
