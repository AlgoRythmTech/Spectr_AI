"""
Financial Analysis Suite for Indian Chartered Accountants.

Comprehensive toolkit covering:
1. Trial Balance Parser with Indian CoA auto-classification
2. Ratio Analysis Engine (profitability, liquidity, solvency, efficiency, per-share, bank-loan)
3. Cash Flow Statement Generator (indirect method, AS-3 / Ind AS 7)
4. Debtor Aging Analysis with ECL provisioning (Ind AS 109 / AS-29)
5. Creditor Aging Analysis with MSME compliance (MSMED Act Sections 15-16)
6. Comparative Financial Statements with common-size and trend analysis
7. Red Flag Detector for audit and due-diligence

All monetary calculations use Decimal for precision.
Pandas used for data manipulation and Excel parsing.
"""

import pandas as pd
import numpy as np
import logging
import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any, Union
from collections import OrderedDict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants & Indian Chart-of-Accounts classification patterns
# ---------------------------------------------------------------------------

TWO_PLACES = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")

# Indian CoA account-name patterns for auto-classification
# Keys are regex patterns (case-insensitive), values are (category, sub_category)
INDIAN_COA_PATTERNS: List[Tuple[str, str, str]] = [
    # ----- Assets: Current -----
    (r"sundry\s*debtors?|trade\s*receivable|accounts?\s*receivable|debtors", "Assets", "Current Assets"),
    (r"cash\s*(in\s*hand|at\s*bank|&\s*bank|and\s*bank)|bank\s*(balance|account|a/?c)|cash\s*balance", "Assets", "Current Assets"),
    (r"stock[\s-]?in[\s-]?trade|closing\s*stock|inventory|raw\s*material|finished\s*goods|work[\s-]?in[\s-]?progress|wip|stores?\s*&?\s*spares?", "Assets", "Current Assets"),
    (r"prepaid\s*(expense|rent|insurance)|advance\s*(tax|to\s*supplier|paid)|tds\s*receivable|input\s*(cgst|sgst|igst|gst|tax\s*credit)|gst\s*input|cenvat\s*credit", "Assets", "Current Assets"),
    (r"short[\s-]?term\s*(loan|advance|deposit|investment)|fd\s*less\s*than|current\s*investment|marketable\s*securit", "Assets", "Current Assets"),
    (r"accrued\s*(income|interest|revenue)|interest\s*receivable|bills?\s*receivable", "Assets", "Current Assets"),
    (r"loan\s*(to\s*employee|to\s*staff|to\s*director|given|receivable)", "Assets", "Current Assets"),

    # ----- Assets: Non-Current -----
    (r"land|building|plant\s*&?\s*machiner|furniture\s*&?\s*fixture|office\s*equipment|computer|vehicle|motor\s*car|capital\s*wip|fixed\s*asset|property[\s,]*plant", "Assets", "Non-Current Assets"),
    (r"goodwill|patent|trademark|copyright|intangible|brand\s*value|software\s*license", "Assets", "Non-Current Assets"),
    (r"long[\s-]?term\s*(investment|loan|deposit|advance)|investment\s*in\s*(subsidiary|associate|shares?|debenture|mutual\s*fund|property)", "Assets", "Non-Current Assets"),
    (r"security\s*deposit|earnest\s*money\s*deposit|emd|capital\s*advance", "Assets", "Non-Current Assets"),
    (r"deferred\s*tax\s*asset|dta", "Assets", "Non-Current Assets"),
    (r"(accumulated|provision\s*for)\s*depreciation|depreciation\s*(fund|reserve)", "Assets", "Non-Current Assets"),

    # ----- Liabilities: Current -----
    (r"sundry\s*creditors?|trade\s*payable|accounts?\s*payable|creditors", "Liabilities", "Current Liabilities"),
    (r"outstanding\s*(expense|liabilit|salary|rent|wages)|expense\s*payable|accrued\s*(expense|liabilit)", "Liabilities", "Current Liabilities"),
    (r"provision\s*for\s*(tax|income\s*tax|gratuity|bonus|leave|audit\s*fee|expense)|tax\s*payable|income\s*tax\s*payable|gst\s*payable|tds\s*payable|output\s*(cgst|sgst|igst|gst)", "Liabilities", "Current Liabilities"),
    (r"short[\s-]?term\s*(borrowing|loan|debt)|cash\s*credit|overdraft|od\s*account|bank\s*od|cc\s*account|working\s*capital\s*loan|bills?\s*payable", "Liabilities", "Current Liabilities"),
    (r"advance\s*(from\s*customer|received)|unearned\s*revenue|deferred\s*revenue|customer\s*deposit", "Liabilities", "Current Liabilities"),
    (r"current\s*maturit|current\s*portion\s*of\s*long", "Liabilities", "Current Liabilities"),
    (r"dividend\s*payable|proposed\s*dividend|interim\s*dividend\s*payable", "Liabilities", "Current Liabilities"),
    (r"statutory\s*(dues?|liabilit)|pf\s*payable|esi\s*payable|professional\s*tax\s*payable", "Liabilities", "Current Liabilities"),

    # ----- Liabilities: Non-Current -----
    (r"long[\s-]?term\s*(borrowing|loan|debt)|term\s*loan|secured\s*loan|unsecured\s*loan|debenture|bond\s*payable", "Liabilities", "Non-Current Liabilities"),
    (r"provision\s*for\s*(gratuity|leave\s*encash|pension|superannuation)|gratuity\s*payable|leave\s*encash", "Liabilities", "Non-Current Liabilities"),
    (r"deferred\s*tax\s*liabilit|dtl", "Liabilities", "Non-Current Liabilities"),
    (r"security\s*deposit\s*(received|payable)", "Liabilities", "Non-Current Liabilities"),

    # ----- Equity -----
    (r"share\s*capital|equity\s*share|preference\s*share|authorized\s*capital|issued\s*capital|paid[\s-]?up\s*capital|subscribed\s*capital", "Equity", "Share Capital"),
    (r"reserves?\s*(&|and)\s*surplus|general\s*reserve|capital\s*reserve|securities?\s*premium|share\s*premium|revaluation\s*reserve|retained\s*earning", "Equity", "Reserves & Surplus"),
    (r"profit\s*(&|and)\s*loss\s*a/?c|p\s*&?\s*l\s*a/?c|surplus\s*in\s*p\s*&?\s*l|accumulated\s*profit|retained\s*profit", "Equity", "Reserves & Surplus"),
    (r"other\s*comprehensive\s*income|oci\s*reserve|hedging\s*reserve|translation\s*reserve", "Equity", "Other Equity"),
    (r"partner.?s?\s*capital|proprietor.?s?\s*capital|capital\s*account|drawing|owner.?s?\s*equity", "Equity", "Capital Account"),

    # ----- Revenue / Income -----
    (r"sale|revenue|turnover|income\s*from\s*operation|service\s*income|fee\s*income|professional\s*fee|consultation\s*income|export\s*sale|domestic\s*sale", "Revenue", "Operating Revenue"),
    (r"interest\s*(income|received|earned)|dividend\s*(income|received)|rental\s*income|rent\s*(received|income)|commission\s*(received|income)|other\s*income|miscellaneous\s*income|profit\s*on\s*sale\s*of\s*asset|gain\s*on|exchange\s*(gain|profit)", "Revenue", "Other Income"),
    (r"discount\s*received|bad\s*debt\s*recovered|insurance\s*claim\s*received|excess\s*provision\s*written\s*back", "Revenue", "Other Income"),

    # ----- Expenses -----
    (r"purchase|cost\s*of\s*(goods\s*sold|material|sales|revenue|production)|cogs|raw\s*material\s*consumed|consumption\s*of\s*material|material\s*consumed|opening\s*stock|closing\s*stock\s*(?:deducted|less)", "Expenses", "Cost of Goods Sold"),
    (r"salar(y|ies)|wage|staff\s*cost|employee\s*(benefit|cost|expense)|bonus|gratuity\s*expense|leave\s*encash.*expense|esi\s*contribution|pf\s*contribution|managerial\s*remuneration|director.?s?\s*remuneration|staff\s*welfare", "Expenses", "Employee Cost"),
    (r"rent\s*(paid|expense)|rates?\s*&?\s*taxes|electricity|power\s*&?\s*fuel|water\s*charge|repair\s*&?\s*maintenance|insurance\s*expense|office\s*expense|printing\s*&?\s*stationery|communication|telephone|internet|postage|courier|travel|conveyance|vehicle\s*expense", "Expenses", "Administrative Expenses"),
    (r"depreciation|amortization|amortisation", "Expenses", "Depreciation & Amortization"),
    (r"interest\s*(paid|expense|on\s*loan|on\s*borrowing|on\s*term\s*loan|on\s*cc|on\s*od)|finance\s*cost|bank\s*charge|processing\s*fee|loan\s*processing", "Expenses", "Finance Cost"),
    (r"advertisement|marketing|selling\s*expense|commission\s*(paid|expense)|brokerage|discount\s*allowed|sales?\s*promotion|distribution\s*expense|freight\s*outward|packaging|packing", "Expenses", "Selling & Distribution"),
    (r"audit\s*fee|legal\s*&?\s*professional|professional\s*fee\s*expense|consultant|statutory\s*audit|tax\s*audit|internal\s*audit", "Expenses", "Professional & Legal"),
    (r"bad\s*debt|provision\s*for\s*doubtful|doubtful\s*debt|write[\s-]?off|loss\s*on\s*sale\s*of\s*asset|exchange\s*(loss|fluctuation)|penalty|fine\s*(paid|expense)|donation|csr\s*expense|miscellaneous\s*expense|rounding\s*off|prior\s*period", "Expenses", "Other Expenses"),
    (r"income\s*tax\s*expense|current\s*tax|deferred\s*tax\s*expense|mat\s*credit|tax\s*expense", "Expenses", "Tax Expense"),
]

# Indian benchmark thresholds for ratio interpretation
RATIO_BENCHMARKS = {
    "gross_profit_margin": {"good": Decimal("0.30"), "average": Decimal("0.15")},
    "net_profit_margin": {"good": Decimal("0.10"), "average": Decimal("0.05")},
    "operating_profit_margin": {"good": Decimal("0.15"), "average": Decimal("0.08")},
    "ebitda_margin": {"good": Decimal("0.20"), "average": Decimal("0.10")},
    "roa": {"good": Decimal("0.10"), "average": Decimal("0.05")},
    "roe": {"good": Decimal("0.15"), "average": Decimal("0.10")},
    "roce": {"good": Decimal("0.15"), "average": Decimal("0.10")},
    "current_ratio": {"good": Decimal("2.0"), "average": Decimal("1.33")},
    "quick_ratio": {"good": Decimal("1.5"), "average": Decimal("1.0")},
    "cash_ratio": {"good": Decimal("0.5"), "average": Decimal("0.2")},
    "debt_to_equity": {"good": Decimal("0.5"), "average": Decimal("1.0")},
    "debt_to_assets": {"good": Decimal("0.3"), "average": Decimal("0.5")},
    "interest_coverage": {"good": Decimal("3.0"), "average": Decimal("1.5")},
    "dscr": {"good": Decimal("2.0"), "average": Decimal("1.5")},
    "inventory_turnover": {"good": Decimal("8.0"), "average": Decimal("5.0")},
    "receivables_turnover": {"good": Decimal("8.0"), "average": Decimal("5.0")},
    "payables_turnover": {"good": Decimal("6.0"), "average": Decimal("4.0")},
    "asset_turnover": {"good": Decimal("1.5"), "average": Decimal("1.0")},
    "tol_tnw": {"good": Decimal("2.0"), "average": Decimal("3.0")},
}

# MSME Act constants
MSME_PAYMENT_LIMIT_DAYS = 45
MSME_INTEREST_RATE_MULTIPLIER = 3  # 3x bank rate under Section 16

# Debtor aging buckets (in days)
AGING_BUCKETS = [
    ("Current (0-30)", 0, 30),
    ("31-60 days", 31, 60),
    ("61-90 days", 61, 90),
    ("91-180 days", 91, 180),
    ("180+ days", 181, 99999),
]

# ECL provisioning rates (simplified Ind AS 109 model)
ECL_PROVISION_RATES = {
    "Current (0-30)": Decimal("0.005"),    # 0.5%
    "31-60 days": Decimal("0.02"),          # 2%
    "61-90 days": Decimal("0.05"),          # 5%
    "91-180 days": Decimal("0.20"),         # 20%
    "180+ days": Decimal("0.50"),           # 50%
}

RECOMMENDED_ACTIONS = {
    "Current (0-30)": "No action required. Continue normal follow-up.",
    "31-60 days": "Send reminder letter/email. Make a follow-up call.",
    "61-90 days": "Escalate to senior management. Send legal notice warning. Put future orders on hold.",
    "91-180 days": "Issue formal legal notice under Order XXXVII CPC. Consider filing summary suit. Classify as sub-standard per RBI norms.",
    "180+ days": "Initiate legal proceedings. Consider write-off after exhausting recovery options. Engage collection agency. File insolvency application if amount exceeds Rs 1 crore.",
}


# ===================================================================
# Helper utilities
# ===================================================================

def _to_decimal(value: Any) -> Decimal:
    """Safely convert any value to Decimal. Returns Decimal('0') on failure."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
            return Decimal("0")
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def _safe_divide(numerator: Decimal, denominator: Decimal) -> Optional[Decimal]:
    """Safe division returning None when denominator is zero."""
    if denominator == Decimal("0"):
        return None
    return (numerator / denominator).quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)


def _pct(value: Optional[Decimal]) -> Optional[Decimal]:
    """Convert ratio to percentage (multiply by 100), rounded to 2 places."""
    if value is None:
        return None
    return (value * Decimal("100")).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _interpret_ratio(ratio_key: str, value: Optional[Decimal], higher_is_better: bool = True) -> str:
    """
    Interpret a ratio value against Indian benchmarks.

    Args:
        ratio_key: Key in RATIO_BENCHMARKS dict.
        value: The calculated ratio value.
        higher_is_better: True for most ratios. False for debt ratios.

    Returns:
        Interpretation string: 'Good', 'Average', or 'Poor'.
    """
    if value is None:
        return "N/A — insufficient data"
    benchmarks = RATIO_BENCHMARKS.get(ratio_key)
    if not benchmarks:
        return "No benchmark available"
    good_threshold = benchmarks["good"]
    avg_threshold = benchmarks["average"]

    if higher_is_better:
        if value >= good_threshold:
            return "Good"
        elif value >= avg_threshold:
            return "Average"
        else:
            return "Poor"
    else:
        # Lower is better (e.g., debt-to-equity)
        if value <= good_threshold:
            return "Good"
        elif value <= avg_threshold:
            return "Average"
        else:
            return "Poor"


def _find_column(df_columns: list, candidates: list) -> str:
    """Find matching column name from candidate list (case-insensitive)."""
    cols_lower = {c.lower().strip(): c for c in df_columns}
    for candidate in candidates:
        if candidate.lower() in cols_lower:
            return cols_lower[candidate.lower()]
    return ""


# ===================================================================
# 1. TRIAL BALANCE PARSER
# ===================================================================

def parse_trial_balance(
    file_content: bytes,
    filename: str = "trial_balance.xlsx",
    sheet_name: Union[str, int] = 0,
) -> Dict[str, Any]:
    """
    Parse an Excel trial balance and auto-classify accounts per Indian CoA.

    Expected columns (flexible matching):
        - account_code / code / a/c code
        - account_name / name / particulars / ledger
        - debit_balance / debit / dr / dr balance
        - credit_balance / credit / cr / cr balance

    Args:
        file_content: Raw bytes of the Excel file.
        filename: Original filename (for extension detection).
        sheet_name: Sheet name or index to read.

    Returns:
        Dict with keys: accounts (list of classified accounts),
        totals (debit_total, credit_total, difference),
        classification_summary, errors.
    """
    logger.info("Parsing trial balance from %s", filename)
    errors = []

    # Read Excel or CSV
    try:
        if filename.lower().endswith(".csv"):
            import io
            df = pd.read_csv(io.BytesIO(file_content))
        else:
            df = pd.read_excel(io.BytesIO(file_content) if isinstance(file_content, bytes) else file_content, sheet_name=sheet_name)
    except Exception as exc:
        logger.error("Failed to read file: %s", exc)
        return {"accounts": [], "totals": {}, "classification_summary": {}, "errors": [str(exc)]}

    # Strip whitespace from column names
    df.columns = [str(c).strip() for c in df.columns]

    # Flexible column detection
    code_candidates = ["account_code", "code", "a/c code", "ac code", "ledger code", "gl code", "account code"]
    name_candidates = ["account_name", "name", "particulars", "ledger", "ledger name", "account name", "head", "account head", "description"]
    debit_candidates = ["debit_balance", "debit", "dr", "dr balance", "dr amount", "debit balance", "debit amount"]
    credit_candidates = ["credit_balance", "credit", "cr", "cr balance", "cr amount", "credit balance", "credit amount"]

    code_col = _find_column(df.columns.tolist(), code_candidates)
    name_col = _find_column(df.columns.tolist(), name_candidates)
    debit_col = _find_column(df.columns.tolist(), debit_candidates)
    credit_col = _find_column(df.columns.tolist(), credit_candidates)

    if not name_col:
        errors.append("Could not find account name column. Expected one of: " + ", ".join(name_candidates))
        return {"accounts": [], "totals": {}, "classification_summary": {}, "errors": errors}
    if not debit_col and not credit_col:
        errors.append("Could not find debit or credit balance columns.")
        return {"accounts": [], "totals": {}, "classification_summary": {}, "errors": errors}

    # Drop rows where account name is empty
    df = df.dropna(subset=[name_col])
    df = df[df[name_col].astype(str).str.strip() != ""]

    accounts = []
    debit_total = Decimal("0")
    credit_total = Decimal("0")
    classification_summary: Dict[str, Decimal] = {}

    for _, row in df.iterrows():
        account_name = str(row[name_col]).strip()
        account_code = str(row[code_col]).strip() if code_col and pd.notna(row.get(code_col)) else ""
        debit_bal = _to_decimal(row.get(debit_col, 0)) if debit_col else Decimal("0")
        credit_bal = _to_decimal(row.get(credit_col, 0)) if credit_col else Decimal("0")

        # Auto-classify
        category, sub_category = _classify_account(account_name, account_code)

        net_balance = debit_bal - credit_bal
        debit_total += debit_bal
        credit_total += credit_bal

        account_entry = {
            "account_code": account_code,
            "account_name": account_name,
            "debit_balance": str(debit_bal),
            "credit_balance": str(credit_bal),
            "net_balance": str(net_balance),
            "category": category,
            "sub_category": sub_category,
        }
        accounts.append(account_entry)

        # Classification summary
        summary_key = f"{category} — {sub_category}"
        classification_summary[summary_key] = classification_summary.get(summary_key, Decimal("0")) + abs(net_balance)

    difference = debit_total - credit_total
    if difference != Decimal("0"):
        errors.append(f"Trial balance does not tally. Difference: {difference} (Debit: {debit_total}, Credit: {credit_total})")

    # Convert summary Decimals to strings for JSON serialization
    summary_str = {k: str(v.quantize(TWO_PLACES)) for k, v in classification_summary.items()}

    result = {
        "accounts": accounts,
        "totals": {
            "debit_total": str(debit_total.quantize(TWO_PLACES)),
            "credit_total": str(credit_total.quantize(TWO_PLACES)),
            "difference": str(difference.quantize(TWO_PLACES)),
            "is_balanced": difference == Decimal("0"),
        },
        "classification_summary": summary_str,
        "account_count": len(accounts),
        "errors": errors,
    }
    logger.info("Parsed %d accounts. Balanced: %s", len(accounts), result["totals"]["is_balanced"])
    return result


def _classify_account(account_name: str, account_code: str = "") -> Tuple[str, str]:
    """
    Classify an account into category and sub-category using Indian CoA patterns.

    Falls back to account code prefix heuristics if name pattern matching fails.
    Indian Tally-style account codes often follow:
        1xxx = Assets, 2xxx = Liabilities, 3xxx = Equity,
        4xxx = Revenue, 5xxx = Expenses

    Args:
        account_name: The account/ledger name.
        account_code: Optional account/GL code.

    Returns:
        Tuple of (category, sub_category).
    """
    name_lower = account_name.lower().strip()

    # Pattern-based matching
    for pattern, category, sub_category in INDIAN_COA_PATTERNS:
        if re.search(pattern, name_lower):
            return category, sub_category

    # Code-prefix fallback
    if account_code:
        code_clean = re.sub(r'[^0-9]', '', account_code)
        if code_clean:
            first_digit = code_clean[0]
            code_map = {
                "1": ("Assets", "Current Assets"),
                "2": ("Liabilities", "Current Liabilities"),
                "3": ("Equity", "Share Capital"),
                "4": ("Revenue", "Operating Revenue"),
                "5": ("Expenses", "Operating Expenses"),
                "6": ("Expenses", "Administrative Expenses"),
                "7": ("Revenue", "Other Income"),
                "8": ("Expenses", "Other Expenses"),
                "9": ("Assets", "Non-Current Assets"),
            }
            if first_digit in code_map:
                return code_map[first_digit]

    return "Unclassified", "Unclassified"


def extract_financials_from_tb(accounts: List[Dict]) -> Dict[str, Decimal]:
    """
    Extract key financial aggregates from classified trial balance accounts.

    Groups accounts by category/sub-category and returns aggregated values
    needed for ratio analysis and cash flow generation.

    Args:
        accounts: List of classified account dicts from parse_trial_balance.

    Returns:
        Dict of financial aggregates (all values as Decimal).
    """
    aggregates: Dict[str, Decimal] = {
        "current_assets": Decimal("0"),
        "non_current_assets": Decimal("0"),
        "total_assets": Decimal("0"),
        "current_liabilities": Decimal("0"),
        "non_current_liabilities": Decimal("0"),
        "total_liabilities": Decimal("0"),
        "equity": Decimal("0"),
        "revenue": Decimal("0"),
        "other_income": Decimal("0"),
        "total_income": Decimal("0"),
        "cogs": Decimal("0"),
        "employee_cost": Decimal("0"),
        "depreciation": Decimal("0"),
        "finance_cost": Decimal("0"),
        "other_expenses": Decimal("0"),
        "total_expenses": Decimal("0"),
        "tax_expense": Decimal("0"),
        "inventory": Decimal("0"),
        "receivables": Decimal("0"),
        "cash_and_bank": Decimal("0"),
        "payables": Decimal("0"),
        "short_term_borrowings": Decimal("0"),
        "long_term_borrowings": Decimal("0"),
    }

    for acc in accounts:
        net = _to_decimal(acc.get("net_balance", "0"))
        cat = acc.get("category", "")
        sub = acc.get("sub_category", "")
        name_lower = acc.get("account_name", "").lower()

        if cat == "Assets":
            if sub == "Current Assets":
                aggregates["current_assets"] += abs(net)
                if re.search(r"stock|inventory|raw\s*material|finished\s*goods|wip|work[\s-]?in[\s-]?progress|stores", name_lower):
                    aggregates["inventory"] += abs(net)
                elif re.search(r"debtor|receivable|bills?\s*receivable", name_lower):
                    aggregates["receivables"] += abs(net)
                elif re.search(r"cash|bank", name_lower):
                    aggregates["cash_and_bank"] += abs(net)
            elif sub == "Non-Current Assets":
                aggregates["non_current_assets"] += abs(net)

        elif cat == "Liabilities":
            if sub == "Current Liabilities":
                aggregates["current_liabilities"] += abs(net)
                if re.search(r"creditor|payable|bills?\s*payable", name_lower):
                    aggregates["payables"] += abs(net)
                if re.search(r"short[\s-]?term.*(borrowing|loan)|cash\s*credit|overdraft|od\s*account|cc\s*account|working\s*capital\s*loan", name_lower):
                    aggregates["short_term_borrowings"] += abs(net)
            elif sub == "Non-Current Liabilities":
                aggregates["non_current_liabilities"] += abs(net)
                if re.search(r"long[\s-]?term.*(borrowing|loan)|term\s*loan|secured\s*loan|unsecured\s*loan|debenture", name_lower):
                    aggregates["long_term_borrowings"] += abs(net)

        elif cat == "Equity":
            aggregates["equity"] += abs(net)

        elif cat == "Revenue":
            if sub == "Operating Revenue":
                aggregates["revenue"] += abs(net)
            else:
                aggregates["other_income"] += abs(net)

        elif cat == "Expenses":
            amount = abs(net)
            if sub == "Cost of Goods Sold":
                aggregates["cogs"] += amount
            elif sub == "Employee Cost":
                aggregates["employee_cost"] += amount
            elif sub == "Depreciation & Amortization":
                aggregates["depreciation"] += amount
            elif sub == "Finance Cost":
                aggregates["finance_cost"] += amount
            elif sub == "Tax Expense":
                aggregates["tax_expense"] += amount
            else:
                aggregates["other_expenses"] += amount

    aggregates["total_assets"] = aggregates["current_assets"] + aggregates["non_current_assets"]
    aggregates["total_liabilities"] = aggregates["current_liabilities"] + aggregates["non_current_liabilities"]
    aggregates["total_income"] = aggregates["revenue"] + aggregates["other_income"]
    aggregates["total_expenses"] = (
        aggregates["cogs"] + aggregates["employee_cost"] + aggregates["depreciation"]
        + aggregates["finance_cost"] + aggregates["other_expenses"] + aggregates["tax_expense"]
    )

    return aggregates


# ===================================================================
# 2. RATIO ANALYSIS ENGINE
# ===================================================================

def compute_ratios(
    financials: Dict[str, Decimal],
    shares_outstanding: Optional[Decimal] = None,
    dividend_paid: Optional[Decimal] = None,
    diluted_shares: Optional[Decimal] = None,
    industry: str = "general",
) -> Dict[str, Any]:
    """
    Compute comprehensive financial ratios from aggregated financial data.

    Covers profitability, liquidity, solvency/leverage, efficiency/activity,
    per-share metrics, and bank-loan covenant ratios with Indian benchmarks.

    Args:
        financials: Dict of financial aggregates from extract_financials_from_tb.
        shares_outstanding: Number of equity shares outstanding (for per-share ratios).
        dividend_paid: Total dividends paid during the period.
        diluted_shares: Diluted share count (for diluted EPS).
        industry: Industry for benchmark comparison notes.

    Returns:
        Dict with ratio categories, each containing individual ratios with
        value, percentage (where applicable), interpretation, and notes.
    """
    logger.info("Computing financial ratios for industry: %s", industry)

    # Convert all values to Decimal for precision (accepts float/int/str)
    financials = {k: _to_decimal(v) for k, v in financials.items()}

    rev = financials.get("revenue", Decimal("0"))
    total_income = financials.get("total_income", Decimal("0"))
    cogs = financials.get("cogs", Decimal("0"))
    total_expenses = financials.get("total_expenses", Decimal("0"))
    depreciation = financials.get("depreciation", Decimal("0"))
    finance_cost = financials.get("finance_cost", Decimal("0"))
    tax_expense = financials.get("tax_expense", Decimal("0"))
    employee_cost = financials.get("employee_cost", Decimal("0"))
    other_expenses = financials.get("other_expenses", Decimal("0"))

    gross_profit = rev - cogs
    operating_expenses = employee_cost + other_expenses + depreciation
    operating_profit = gross_profit - operating_expenses
    ebitda = operating_profit + depreciation
    pbt = total_income - total_expenses + tax_expense  # Profit Before Tax
    pat = total_income - total_expenses  # Profit After Tax

    current_assets = financials.get("current_assets", Decimal("0"))
    non_current_assets = financials.get("non_current_assets", Decimal("0"))
    total_assets = financials.get("total_assets", Decimal("0"))
    current_liabilities = financials.get("current_liabilities", Decimal("0"))
    non_current_liabilities = financials.get("non_current_liabilities", Decimal("0"))
    total_liabilities = financials.get("total_liabilities", Decimal("0"))
    equity = financials.get("equity", Decimal("0"))
    inventory = financials.get("inventory", Decimal("0"))
    receivables = financials.get("receivables", Decimal("0"))
    payables = financials.get("payables", Decimal("0"))
    cash_and_bank = financials.get("cash_and_bank", Decimal("0"))
    short_term_borrowings = financials.get("short_term_borrowings", Decimal("0"))
    long_term_borrowings = financials.get("long_term_borrowings", Decimal("0"))
    total_debt = short_term_borrowings + long_term_borrowings

    working_capital = current_assets - current_liabilities
    capital_employed = total_assets - current_liabilities
    tangible_net_worth = equity  # Simplified; excludes intangibles ideally
    total_outside_liabilities = total_liabilities

    ratios: Dict[str, Any] = OrderedDict()

    # ----- Profitability Ratios -----
    profitability = OrderedDict()

    gpm = _safe_divide(gross_profit, rev)
    profitability["gross_profit_margin"] = {
        "value": str(gpm) if gpm is not None else None,
        "percentage": str(_pct(gpm)) if gpm is not None else None,
        "interpretation": _interpret_ratio("gross_profit_margin", gpm),
        "formula": "Gross Profit / Revenue",
        "notes": "Measures core production efficiency. Indian manufacturing avg: 25-35%.",
    }

    npm = _safe_divide(pat, rev)
    profitability["net_profit_margin"] = {
        "value": str(npm) if npm is not None else None,
        "percentage": str(_pct(npm)) if npm is not None else None,
        "interpretation": _interpret_ratio("net_profit_margin", npm),
        "formula": "PAT / Revenue",
        "notes": "Bottom-line profitability. Indian SME avg: 5-8%.",
    }

    opm = _safe_divide(operating_profit, rev)
    profitability["operating_profit_margin"] = {
        "value": str(opm) if opm is not None else None,
        "percentage": str(_pct(opm)) if opm is not None else None,
        "interpretation": _interpret_ratio("operating_profit_margin", opm),
        "formula": "Operating Profit / Revenue",
        "notes": "Operational efficiency excluding finance costs and taxes.",
    }

    em = _safe_divide(ebitda, rev)
    profitability["ebitda_margin"] = {
        "value": str(em) if em is not None else None,
        "percentage": str(_pct(em)) if em is not None else None,
        "interpretation": _interpret_ratio("ebitda_margin", em),
        "formula": "EBITDA / Revenue",
        "notes": "Cash-generation ability from operations. Key valuation metric.",
    }

    roa = _safe_divide(pat, total_assets)
    profitability["return_on_assets"] = {
        "value": str(roa) if roa is not None else None,
        "percentage": str(_pct(roa)) if roa is not None else None,
        "interpretation": _interpret_ratio("roa", roa),
        "formula": "PAT / Total Assets",
        "notes": "Asset utilization efficiency. Banking sector avg: 0.8-1.2%.",
    }

    roe = _safe_divide(pat, equity)
    profitability["return_on_equity"] = {
        "value": str(roe) if roe is not None else None,
        "percentage": str(_pct(roe)) if roe is not None else None,
        "interpretation": _interpret_ratio("roe", roe),
        "formula": "PAT / Shareholders Equity",
        "notes": "Return earned on owner investment. Should exceed cost of equity.",
    }

    roce = _safe_divide(operating_profit + financials.get("other_income", Decimal("0")), capital_employed) if capital_employed != Decimal("0") else None
    profitability["return_on_capital_employed"] = {
        "value": str(roce) if roce is not None else None,
        "percentage": str(_pct(roce)) if roce is not None else None,
        "interpretation": _interpret_ratio("roce", roce),
        "formula": "EBIT / Capital Employed",
        "notes": "Overall capital efficiency. Must exceed WACC for value creation.",
    }

    ratios["profitability"] = profitability

    # ----- Liquidity Ratios -----
    liquidity = OrderedDict()

    cr = _safe_divide(current_assets, current_liabilities)
    liquidity["current_ratio"] = {
        "value": str(cr) if cr is not None else None,
        "interpretation": _interpret_ratio("current_ratio", cr),
        "formula": "Current Assets / Current Liabilities",
        "notes": "Bank minimum norm: 1.33. Below 1.0 indicates liquidity crisis.",
    }

    quick_assets = current_assets - inventory
    qr = _safe_divide(quick_assets, current_liabilities)
    liquidity["quick_ratio"] = {
        "value": str(qr) if qr is not None else None,
        "interpretation": _interpret_ratio("quick_ratio", qr),
        "formula": "(Current Assets - Inventory) / Current Liabilities",
        "notes": "Acid-test ratio. Excludes slow-moving inventory.",
    }

    cashr = _safe_divide(cash_and_bank, current_liabilities)
    liquidity["cash_ratio"] = {
        "value": str(cashr) if cashr is not None else None,
        "interpretation": _interpret_ratio("cash_ratio", cashr),
        "formula": "Cash & Bank / Current Liabilities",
        "notes": "Most conservative liquidity measure. Too high may indicate idle cash.",
    }

    liquidity["working_capital"] = {
        "value": str(working_capital.quantize(TWO_PLACES)),
        "interpretation": "Positive" if working_capital > Decimal("0") else "Negative — potential liquidity stress",
        "formula": "Current Assets - Current Liabilities",
        "notes": "Absolute liquidity cushion. Negative WC needs immediate attention.",
    }

    ratios["liquidity"] = liquidity

    # ----- Solvency / Leverage Ratios -----
    solvency = OrderedDict()

    de = _safe_divide(total_debt, equity)
    solvency["debt_to_equity"] = {
        "value": str(de) if de is not None else None,
        "interpretation": _interpret_ratio("debt_to_equity", de, higher_is_better=False),
        "formula": "Total Debt / Equity",
        "notes": "Indian MSME avg: 1.0-1.5. Above 2.0 is over-leveraged per bank norms.",
    }

    da = _safe_divide(total_debt, total_assets)
    solvency["debt_to_assets"] = {
        "value": str(da) if da is not None else None,
        "interpretation": _interpret_ratio("debt_to_assets", da, higher_is_better=False),
        "formula": "Total Debt / Total Assets",
        "notes": "Portion of assets financed by debt. Lower is safer.",
    }

    icr = _safe_divide(ebitda, finance_cost) if finance_cost > Decimal("0") else None
    solvency["interest_coverage_ratio"] = {
        "value": str(icr) if icr is not None else None,
        "interpretation": _interpret_ratio("interest_coverage", icr) if icr is not None else "N/A — no finance cost",
        "formula": "EBITDA / Interest Expense",
        "notes": "Ability to service interest. Below 1.5 is stress. Bank norm: min 1.5.",
    }

    # DSCR: (PAT + Depreciation + Interest) / (Principal Repayment + Interest)
    # Simplified: using total debt service as finance_cost + estimated principal
    dscr_numerator = pat + depreciation + finance_cost
    dscr_denominator = finance_cost + (long_term_borrowings * Decimal("0.15"))  # Rough annual principal
    dscr_val = _safe_divide(dscr_numerator, dscr_denominator) if dscr_denominator > Decimal("0") else None
    solvency["dscr"] = {
        "value": str(dscr_val) if dscr_val is not None else None,
        "interpretation": _interpret_ratio("dscr", dscr_val) if dscr_val is not None else "N/A — no debt service",
        "formula": "(PAT + Depreciation + Interest) / (Principal + Interest)",
        "notes": "Debt servicing capacity. Bank minimum norm: 1.5. Below 1.0 = default risk.",
    }

    ratios["solvency"] = solvency

    # ----- Efficiency / Activity Ratios -----
    efficiency = OrderedDict()

    inv_turnover = _safe_divide(cogs, inventory) if inventory > Decimal("0") else None
    efficiency["inventory_turnover"] = {
        "value": str(inv_turnover) if inv_turnover is not None else None,
        "interpretation": _interpret_ratio("inventory_turnover", inv_turnover),
        "formula": "COGS / Average Inventory",
        "notes": "Times inventory is sold and replaced. Higher = better stock management.",
    }

    rec_turnover = _safe_divide(rev, receivables) if receivables > Decimal("0") else None
    efficiency["receivables_turnover"] = {
        "value": str(rec_turnover) if rec_turnover is not None else None,
        "interpretation": _interpret_ratio("receivables_turnover", rec_turnover),
        "formula": "Revenue / Trade Receivables",
        "notes": "Speed of collecting receivables. Indian norm: 5-8 times.",
    }

    pay_turnover = _safe_divide(cogs, payables) if payables > Decimal("0") else None
    efficiency["payables_turnover"] = {
        "value": str(pay_turnover) if pay_turnover is not None else None,
        "interpretation": _interpret_ratio("payables_turnover", pay_turnover),
        "formula": "COGS / Trade Payables",
        "notes": "Speed of paying suppliers. Very high may strain supplier relations.",
    }

    asset_turnover = _safe_divide(rev, total_assets) if total_assets > Decimal("0") else None
    efficiency["asset_turnover"] = {
        "value": str(asset_turnover) if asset_turnover is not None else None,
        "interpretation": _interpret_ratio("asset_turnover", asset_turnover),
        "formula": "Revenue / Total Assets",
        "notes": "Revenue generated per rupee of assets.",
    }

    # Days ratios
    dso = _safe_divide(receivables * Decimal("365"), rev) if rev > Decimal("0") else None
    efficiency["days_sales_outstanding"] = {
        "value": str(dso.quantize(TWO_PLACES)) if dso is not None else None,
        "interpretation": f"{'Good (<45 days)' if dso and dso < Decimal('45') else 'High (>45 days) — collection needs improvement' if dso else 'N/A'}",
        "formula": "(Receivables / Revenue) * 365",
        "notes": "Average collection period. Indian SME avg: 45-90 days.",
    }

    dpo = _safe_divide(payables * Decimal("365"), cogs) if cogs > Decimal("0") else None
    efficiency["days_payable_outstanding"] = {
        "value": str(dpo.quantize(TWO_PLACES)) if dpo is not None else None,
        "interpretation": f"{'Within MSME limit' if dpo and dpo <= Decimal('45') else 'Exceeds MSME 45-day limit — check MSMED compliance' if dpo else 'N/A'}",
        "formula": "(Payables / COGS) * 365",
        "notes": "Average payment period. MSMED Act limit: 45 days for MSME vendors.",
    }

    dio = _safe_divide(inventory * Decimal("365"), cogs) if cogs > Decimal("0") else None
    efficiency["days_inventory_outstanding"] = {
        "value": str(dio.quantize(TWO_PLACES)) if dio is not None else None,
        "interpretation": f"{'Efficient' if dio and dio < Decimal('60') else 'Slow-moving inventory risk' if dio else 'N/A'}",
        "formula": "(Inventory / COGS) * 365",
        "notes": "Days to sell inventory. High DIO may indicate obsolescence risk.",
    }

    # Cash Conversion Cycle = DIO + DSO - DPO
    if dso is not None and dio is not None and dpo is not None:
        ccc = dio + dso - dpo
        ccc_interp = "Efficient" if ccc < Decimal("60") else "Needs working capital optimization"
    else:
        ccc = None
        ccc_interp = "N/A — insufficient data"
    efficiency["cash_conversion_cycle"] = {
        "value": str(ccc.quantize(TWO_PLACES)) if ccc is not None else None,
        "interpretation": ccc_interp,
        "formula": "DIO + DSO - DPO",
        "notes": "Days between cash outflow for materials and cash inflow from sales. Lower is better.",
    }

    ratios["efficiency"] = efficiency

    # ----- Per Share Ratios -----
    per_share = OrderedDict()
    if shares_outstanding and shares_outstanding > Decimal("0"):
        eps_basic = _safe_divide(pat, shares_outstanding)
        per_share["eps_basic"] = {
            "value": str(eps_basic.quantize(TWO_PLACES)) if eps_basic is not None else None,
            "formula": "PAT / Shares Outstanding",
            "notes": "Basic Earnings Per Share.",
        }

        if diluted_shares and diluted_shares > Decimal("0"):
            eps_diluted = _safe_divide(pat, diluted_shares)
            per_share["eps_diluted"] = {
                "value": str(eps_diluted.quantize(TWO_PLACES)) if eps_diluted is not None else None,
                "formula": "PAT / Diluted Shares",
                "notes": "Diluted EPS considering convertible instruments.",
            }

        bvps = _safe_divide(equity, shares_outstanding)
        per_share["book_value_per_share"] = {
            "value": str(bvps.quantize(TWO_PLACES)) if bvps is not None else None,
            "formula": "Equity / Shares Outstanding",
            "notes": "Net asset value per share. Floor for share valuation.",
        }

        if dividend_paid and dividend_paid > Decimal("0") and pat > Decimal("0"):
            dpr = _safe_divide(dividend_paid, pat)
            per_share["dividend_payout_ratio"] = {
                "value": str(dpr) if dpr is not None else None,
                "percentage": str(_pct(dpr)) if dpr is not None else None,
                "formula": "Dividends Paid / PAT",
                "notes": "Proportion of earnings distributed. Mature companies: 30-50%.",
            }

    ratios["per_share"] = per_share

    # ----- Bank Loan / Covenant Ratios -----
    bank_ratios = OrderedDict()

    tol_tnw = _safe_divide(total_outside_liabilities, tangible_net_worth) if tangible_net_worth > Decimal("0") else None
    bank_ratios["tol_tnw"] = {
        "value": str(tol_tnw) if tol_tnw is not None else None,
        "interpretation": _interpret_ratio("tol_tnw", tol_tnw, higher_is_better=False),
        "formula": "Total Outside Liabilities / Tangible Net Worth",
        "notes": "Key bank ratio. Manufacturing: max 3.0, Trading: max 4.0, Services: max 2.0.",
        "bank_norm": "Varies by industry. Generally max 3.0.",
    }

    bank_ratios["current_ratio_compliance"] = {
        "value": str(cr) if cr is not None else None,
        "compliant": bool(cr is not None and cr >= Decimal("1.33")),
        "minimum_required": "1.33",
        "notes": "RBI/bank minimum current ratio requirement for working capital lending.",
    }

    bank_ratios["dscr_compliance"] = {
        "value": str(dscr_val) if dscr_val is not None else None,
        "compliant": bool(dscr_val is not None and dscr_val >= Decimal("1.5")),
        "minimum_required": "1.50",
        "notes": "Minimum DSCR for term loan sanction. Below 1.5 = loan restructuring risk.",
    }

    bank_ratios["interest_coverage_compliance"] = {
        "value": str(icr) if icr is not None else None,
        "compliant": bool(icr is not None and icr >= Decimal("1.5")),
        "minimum_required": "1.50",
        "notes": "Interest coverage below 1.5 triggers SMA/NPA classification risk.",
    }

    ratios["bank_loan_ratios"] = bank_ratios

    return ratios


# ===================================================================
# 3. CASH FLOW STATEMENT GENERATOR (Indirect Method, AS-3 / Ind AS 7)
# ===================================================================

def generate_cash_flow(
    current_pl: Dict[str, Decimal],
    current_bs: Dict[str, Decimal],
    previous_bs: Dict[str, Decimal],
    additional_info: Optional[Dict[str, Decimal]] = None,
) -> Dict[str, Any]:
    """
    Generate a Cash Flow Statement using the Indirect Method per AS-3 / Ind AS 7.

    Args:
        current_pl: P&L items for current year. Expected keys:
            pat, depreciation, finance_cost, interest_income, dividend_income,
            loss_on_sale_of_asset, gain_on_sale_of_asset, tax_expense,
            provision_for_doubtful_debts, other_non_cash_items
        current_bs: Current year balance sheet items. Expected keys:
            receivables, inventory, other_current_assets, payables,
            other_current_liabilities, provisions, fixed_assets_gross,
            accumulated_depreciation, capital_wip, investments,
            long_term_borrowings, short_term_borrowings, equity,
            reserves_surplus, cash_and_bank
        previous_bs: Previous year balance sheet items (same keys).
        additional_info: Optional dict with:
            capex, asset_sale_proceeds, investment_purchases,
            investment_sale_proceeds, equity_raised, dividends_paid,
            borrowings_raised, borrowings_repaid

    Returns:
        Dict with operating_activities, investing_activities,
        financing_activities, net_cash_flow, free_cash_flow,
        cash_flow_adequacy, and reconciliation.
    """
    logger.info("Generating Cash Flow Statement (indirect method)")
    info = additional_info or {}

    def _get(d: Dict, key: str) -> Decimal:
        return _to_decimal(d.get(key, 0))

    # ---- A. Operating Activities (Indirect Method) ----
    pat = _get(current_pl, "pat")
    depreciation = _get(current_pl, "depreciation")
    finance_cost = _get(current_pl, "finance_cost")
    interest_income = _get(current_pl, "interest_income")
    dividend_income = _get(current_pl, "dividend_income")
    loss_on_asset_sale = _get(current_pl, "loss_on_sale_of_asset")
    gain_on_asset_sale = _get(current_pl, "gain_on_sale_of_asset")
    provision_doubtful = _get(current_pl, "provision_for_doubtful_debts")
    other_non_cash = _get(current_pl, "other_non_cash_items")

    # Non-cash and non-operating adjustments
    adjustments = OrderedDict()
    adjustments["depreciation_amortization"] = depreciation
    adjustments["finance_cost_added_back"] = finance_cost
    adjustments["interest_income_removed"] = -interest_income
    adjustments["dividend_income_removed"] = -dividend_income
    adjustments["loss_on_sale_of_assets"] = loss_on_asset_sale
    adjustments["gain_on_sale_of_assets"] = -gain_on_asset_sale
    adjustments["provision_for_doubtful_debts"] = provision_doubtful
    adjustments["other_non_cash_items"] = other_non_cash

    total_adjustments = sum(adjustments.values(), Decimal("0"))
    operating_profit_before_wc = pat + total_adjustments

    # Working capital changes
    wc_changes = OrderedDict()
    wc_changes["change_in_receivables"] = -(
        _get(current_bs, "receivables") - _get(previous_bs, "receivables")
    )
    wc_changes["change_in_inventory"] = -(
        _get(current_bs, "inventory") - _get(previous_bs, "inventory")
    )
    wc_changes["change_in_other_current_assets"] = -(
        _get(current_bs, "other_current_assets") - _get(previous_bs, "other_current_assets")
    )
    wc_changes["change_in_payables"] = (
        _get(current_bs, "payables") - _get(previous_bs, "payables")
    )
    wc_changes["change_in_other_current_liabilities"] = (
        _get(current_bs, "other_current_liabilities") - _get(previous_bs, "other_current_liabilities")
    )
    wc_changes["change_in_provisions"] = (
        _get(current_bs, "provisions") - _get(previous_bs, "provisions")
    )

    total_wc_changes = sum(wc_changes.values(), Decimal("0"))
    cash_from_operations = operating_profit_before_wc + total_wc_changes

    # Tax paid (use direct info if provided, otherwise estimate)
    tax_paid = _get(info, "tax_paid")
    if tax_paid == Decimal("0"):
        tax_paid = _get(current_pl, "tax_expense")

    operating_cash_flow = cash_from_operations - tax_paid

    operating_activities = {
        "pat": str(pat.quantize(TWO_PLACES)),
        "adjustments": {k: str(v.quantize(TWO_PLACES)) for k, v in adjustments.items()},
        "total_adjustments": str(total_adjustments.quantize(TWO_PLACES)),
        "operating_profit_before_wc_changes": str(operating_profit_before_wc.quantize(TWO_PLACES)),
        "working_capital_changes": {k: str(v.quantize(TWO_PLACES)) for k, v in wc_changes.items()},
        "total_wc_changes": str(total_wc_changes.quantize(TWO_PLACES)),
        "cash_from_operations": str(cash_from_operations.quantize(TWO_PLACES)),
        "tax_paid": str((-tax_paid).quantize(TWO_PLACES)),
        "net_operating_cash_flow": str(operating_cash_flow.quantize(TWO_PLACES)),
    }

    # ---- B. Investing Activities ----
    capex = _get(info, "capex")
    if capex == Decimal("0"):
        # Estimate from balance sheet if not provided
        fa_change = _get(current_bs, "fixed_assets_gross") - _get(previous_bs, "fixed_assets_gross")
        cwip_change = _get(current_bs, "capital_wip") - _get(previous_bs, "capital_wip")
        capex = max(fa_change + cwip_change, Decimal("0"))

    asset_sale_proceeds = _get(info, "asset_sale_proceeds")
    investment_purchases = _get(info, "investment_purchases")
    if investment_purchases == Decimal("0"):
        inv_change = _get(current_bs, "investments") - _get(previous_bs, "investments")
        if inv_change > Decimal("0"):
            investment_purchases = inv_change
    investment_sales = _get(info, "investment_sale_proceeds")
    interest_received = interest_income
    dividend_received = dividend_income

    investing_items = OrderedDict()
    investing_items["purchase_of_fixed_assets"] = -capex
    investing_items["sale_of_fixed_assets"] = asset_sale_proceeds
    investing_items["purchase_of_investments"] = -investment_purchases
    investing_items["sale_of_investments"] = investment_sales
    investing_items["interest_received"] = interest_received
    investing_items["dividend_received"] = dividend_received

    investing_cash_flow = sum(investing_items.values(), Decimal("0"))

    investing_activities = {
        "items": {k: str(v.quantize(TWO_PLACES)) for k, v in investing_items.items()},
        "net_investing_cash_flow": str(investing_cash_flow.quantize(TWO_PLACES)),
    }

    # ---- C. Financing Activities ----
    borrowings_raised = _get(info, "borrowings_raised")
    borrowings_repaid = _get(info, "borrowings_repaid")
    if borrowings_raised == Decimal("0") and borrowings_repaid == Decimal("0"):
        lt_change = _get(current_bs, "long_term_borrowings") - _get(previous_bs, "long_term_borrowings")
        st_change = _get(current_bs, "short_term_borrowings") - _get(previous_bs, "short_term_borrowings")
        net_borrowing_change = lt_change + st_change
        if net_borrowing_change > Decimal("0"):
            borrowings_raised = net_borrowing_change
        else:
            borrowings_repaid = abs(net_borrowing_change)

    equity_raised = _get(info, "equity_raised")
    if equity_raised == Decimal("0"):
        eq_change = (
            (_get(current_bs, "equity") + _get(current_bs, "reserves_surplus"))
            - (_get(previous_bs, "equity") + _get(previous_bs, "reserves_surplus"))
            - pat
        )
        if eq_change > Decimal("0"):
            equity_raised = eq_change

    dividends_paid = _get(info, "dividends_paid")
    interest_paid = finance_cost

    financing_items = OrderedDict()
    financing_items["proceeds_from_borrowings"] = borrowings_raised
    financing_items["repayment_of_borrowings"] = -borrowings_repaid
    financing_items["equity_raised"] = equity_raised
    financing_items["dividends_paid"] = -dividends_paid
    financing_items["interest_paid"] = -interest_paid

    financing_cash_flow = sum(financing_items.values(), Decimal("0"))

    financing_activities = {
        "items": {k: str(v.quantize(TWO_PLACES)) for k, v in financing_items.items()},
        "net_financing_cash_flow": str(financing_cash_flow.quantize(TWO_PLACES)),
    }

    # ---- Summary ----
    net_cash_flow = operating_cash_flow + investing_cash_flow + financing_cash_flow
    opening_cash = _get(previous_bs, "cash_and_bank")
    closing_cash = opening_cash + net_cash_flow
    actual_closing_cash = _get(current_bs, "cash_and_bank")
    reconciliation_diff = actual_closing_cash - closing_cash

    free_cash_flow = operating_cash_flow - capex

    # Cash Flow Adequacy analysis
    adequacy = _compute_cash_flow_adequacy(
        operating_cash_flow, capex, finance_cost, dividends_paid, borrowings_repaid, pat
    )

    result = {
        "operating_activities": operating_activities,
        "investing_activities": investing_activities,
        "financing_activities": financing_activities,
        "summary": {
            "net_operating_cash_flow": str(operating_cash_flow.quantize(TWO_PLACES)),
            "net_investing_cash_flow": str(investing_cash_flow.quantize(TWO_PLACES)),
            "net_financing_cash_flow": str(financing_cash_flow.quantize(TWO_PLACES)),
            "net_change_in_cash": str(net_cash_flow.quantize(TWO_PLACES)),
            "opening_cash": str(opening_cash.quantize(TWO_PLACES)),
            "closing_cash_computed": str(closing_cash.quantize(TWO_PLACES)),
            "closing_cash_actual": str(actual_closing_cash.quantize(TWO_PLACES)),
            "reconciliation_difference": str(reconciliation_diff.quantize(TWO_PLACES)),
        },
        "free_cash_flow": str(free_cash_flow.quantize(TWO_PLACES)),
        "cash_flow_adequacy": adequacy,
    }
    return result


def _compute_cash_flow_adequacy(
    ocf: Decimal, capex: Decimal, interest: Decimal,
    dividends: Decimal, debt_repayment: Decimal, pat: Decimal,
) -> Dict[str, Any]:
    """
    Compute cash flow adequacy metrics per Indian CA analysis standards.

    Args:
        ocf: Operating Cash Flow.
        capex: Capital expenditure.
        interest: Interest paid.
        dividends: Dividends paid.
        debt_repayment: Debt repaid during the year.
        pat: Profit After Tax.

    Returns:
        Dict of adequacy ratios and interpretations.
    """
    adequacy = OrderedDict()

    # Cash Flow Adequacy Ratio = OCF / (CapEx + Debt Repayment + Dividends)
    denominator = capex + debt_repayment + dividends
    cfa = _safe_divide(ocf, denominator) if denominator > Decimal("0") else None
    adequacy["cash_flow_adequacy_ratio"] = {
        "value": str(cfa.quantize(TWO_PLACES)) if cfa is not None else None,
        "formula": "OCF / (CapEx + Debt Repayment + Dividends)",
        "interpretation": (
            "Good — internally funding growth and obligations" if cfa and cfa >= Decimal("1")
            else "Inadequate — relying on external funding" if cfa
            else "N/A"
        ),
    }

    # Capital Expenditure Ratio = OCF / CapEx
    capex_ratio = _safe_divide(ocf, capex) if capex > Decimal("0") else None
    adequacy["capex_coverage_ratio"] = {
        "value": str(capex_ratio.quantize(TWO_PLACES)) if capex_ratio is not None else None,
        "formula": "OCF / Capital Expenditure",
        "interpretation": (
            "Self-funding capex" if capex_ratio and capex_ratio >= Decimal("1")
            else "CapEx exceeds cash generation" if capex_ratio
            else "N/A — no capex"
        ),
    }

    # Earnings Quality = OCF / PAT
    eq = _safe_divide(ocf, pat) if pat != Decimal("0") else None
    adequacy["earnings_quality"] = {
        "value": str(eq.quantize(TWO_PLACES)) if eq is not None else None,
        "formula": "Operating Cash Flow / PAT",
        "interpretation": (
            "Good earnings quality — profits backed by cash" if eq and eq >= Decimal("0.8")
            else "Poor earnings quality — profits not translating to cash (red flag)" if eq and eq < Decimal("0.5")
            else "Moderate earnings quality" if eq
            else "N/A"
        ),
        "notes": "OCF/PAT below 0.5 is a serious concern. May indicate aggressive revenue recognition.",
    }

    # Cash Interest Coverage = OCF / Interest
    cic = _safe_divide(ocf, interest) if interest > Decimal("0") else None
    adequacy["cash_interest_coverage"] = {
        "value": str(cic.quantize(TWO_PLACES)) if cic is not None else None,
        "formula": "Operating Cash Flow / Interest Paid",
        "interpretation": (
            "Comfortable debt servicing" if cic and cic >= Decimal("3")
            else "Tight — interest consuming most operating cash" if cic and cic < Decimal("1.5")
            else "Adequate" if cic
            else "N/A — no interest"
        ),
    }

    return adequacy


# ===================================================================
# 4. DEBTOR AGING ANALYSIS
# ===================================================================

def analyze_debtor_aging(
    debtor_data: Union[pd.DataFrame, List[Dict]],
    as_of_date: Optional[date] = None,
    ecl_model: str = "simplified",
) -> Dict[str, Any]:
    """
    Perform debtor aging analysis with ECL provisioning (Ind AS 109 / AS-29).

    Args:
        debtor_data: DataFrame or list of dicts with columns:
            customer_name, invoice_no, invoice_date, amount, payment_date, balance
        as_of_date: Date for aging calculation. Defaults to today.
        ecl_model: 'simplified' for simplified approach (Ind AS 109),
                   'general' for general approach.

    Returns:
        Dict with aging_summary, provision_for_doubtful_debts,
        concentration_risk, collection_efficiency, recommended_actions,
        and detail records.
    """
    logger.info("Performing debtor aging analysis (ECL model: %s)", ecl_model)
    if as_of_date is None:
        as_of_date = date.today()

    # Convert to DataFrame if needed
    if isinstance(debtor_data, list):
        df = pd.DataFrame(debtor_data)
    else:
        df = debtor_data.copy()

    # Normalize column names
    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]

    # Ensure date columns are datetime
    for date_col in ["invoice_date", "payment_date"]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)

    # Ensure numeric columns
    for num_col in ["amount", "balance"]:
        if num_col in df.columns:
            df[num_col] = pd.to_numeric(df[num_col], errors="coerce").fillna(0)

    # If balance column missing, use amount
    if "balance" not in df.columns:
        df["balance"] = df.get("amount", 0)

    # Filter to only outstanding (balance > 0)
    outstanding = df[df["balance"] > 0].copy()

    # Calculate age in days
    as_of_dt = pd.Timestamp(as_of_date)
    outstanding["age_days"] = (as_of_dt - outstanding["invoice_date"]).dt.days
    outstanding["age_days"] = outstanding["age_days"].fillna(0).astype(int)

    # Assign aging buckets
    def _assign_bucket(days: int) -> str:
        for label, low, high in AGING_BUCKETS:
            if low <= days <= high:
                return label
        return "180+ days"

    outstanding["aging_bucket"] = outstanding["age_days"].apply(_assign_bucket)

    # Aging summary
    aging_summary = OrderedDict()
    total_outstanding = Decimal("0")
    total_provision = Decimal("0")

    for label, low, high in AGING_BUCKETS:
        bucket_df = outstanding[outstanding["aging_bucket"] == label]
        bucket_amount = _to_decimal(bucket_df["balance"].sum())
        count = len(bucket_df)
        provision_rate = ECL_PROVISION_RATES.get(label, Decimal("0"))
        provision_amount = (bucket_amount * provision_rate).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        total_outstanding += bucket_amount
        total_provision += provision_amount

        aging_summary[label] = {
            "count": count,
            "amount": str(bucket_amount.quantize(TWO_PLACES)),
            "percentage_of_total": None,  # Filled below
            "provision_rate": str(_pct(provision_rate)) + "%",
            "provision_amount": str(provision_amount),
            "recommended_action": RECOMMENDED_ACTIONS.get(label, ""),
        }

    # Fill percentage of total
    for label in aging_summary:
        amount = _to_decimal(aging_summary[label]["amount"])
        pct = _safe_divide(amount * Decimal("100"), total_outstanding) if total_outstanding > Decimal("0") else Decimal("0")
        aging_summary[label]["percentage_of_total"] = str(pct.quantize(TWO_PLACES)) + "%" if pct else "0.00%"

    # Concentration risk — top 10 debtors
    concentration = _compute_concentration_risk(outstanding, total_outstanding)

    # Collection efficiency
    total_billed = _to_decimal(df["amount"].sum()) if "amount" in df.columns else Decimal("0")
    total_collected = total_billed - total_outstanding
    collection_ratio = _safe_divide(total_collected, total_billed) if total_billed > Decimal("0") else None

    collection_efficiency = {
        "total_billed": str(total_billed.quantize(TWO_PLACES)),
        "total_collected": str(total_collected.quantize(TWO_PLACES)),
        "total_outstanding": str(total_outstanding.quantize(TWO_PLACES)),
        "collection_efficiency_ratio": str(_pct(collection_ratio)) + "%" if collection_ratio else "N/A",
        "interpretation": (
            "Excellent collection" if collection_ratio and collection_ratio >= Decimal("0.90")
            else "Good collection" if collection_ratio and collection_ratio >= Decimal("0.80")
            else "Needs improvement" if collection_ratio and collection_ratio >= Decimal("0.70")
            else "Poor — significant collection issues" if collection_ratio
            else "N/A"
        ),
    }

    # Average collection period
    avg_age = outstanding["age_days"].mean() if len(outstanding) > 0 else 0
    weighted_avg = Decimal("0")
    if total_outstanding > Decimal("0") and len(outstanding) > 0:
        for _, row in outstanding.iterrows():
            w = _to_decimal(row["balance"]) / total_outstanding
            weighted_avg += w * _to_decimal(row["age_days"])

    result = {
        "as_of_date": as_of_date.isoformat(),
        "aging_summary": aging_summary,
        "totals": {
            "total_outstanding": str(total_outstanding.quantize(TWO_PLACES)),
            "total_provision_required": str(total_provision.quantize(TWO_PLACES)),
            "net_realizable_receivables": str((total_outstanding - total_provision).quantize(TWO_PLACES)),
            "provision_percentage": str(_pct(_safe_divide(total_provision, total_outstanding))) + "%" if total_outstanding > Decimal("0") else "N/A",
        },
        "ecl_model_used": ecl_model,
        "ecl_note": (
            "Provision computed using simplified ECL approach under Ind AS 109 "
            "(lifetime expected credit losses using provision matrix). "
            "For AS-29 entities, provision is based on assessment of recoverability."
        ),
        "concentration_risk": concentration,
        "collection_efficiency": collection_efficiency,
        "average_collection_period": {
            "simple_average_days": round(avg_age, 1),
            "weighted_average_days": str(weighted_avg.quantize(TWO_PLACES)),
        },
        "record_count": len(outstanding),
    }
    return result


def _compute_concentration_risk(
    outstanding: pd.DataFrame,
    total_outstanding: Decimal,
) -> Dict[str, Any]:
    """
    Compute debtor concentration risk.

    Identifies top 10 debtors and their share of total receivables.
    Flags customers exceeding 10% of total as concentration risks.

    Args:
        outstanding: DataFrame of outstanding invoices.
        total_outstanding: Total outstanding receivable amount.

    Returns:
        Dict with top_debtors list, hhi_index, and risk assessment.
    """
    if total_outstanding == Decimal("0") or len(outstanding) == 0:
        return {"top_debtors": [], "hhi_index": None, "risk_level": "N/A"}

    # Group by customer
    customer_totals = outstanding.groupby("customer_name")["balance"].sum().sort_values(ascending=False)

    top_debtors = []
    hhi_sum = Decimal("0")  # Herfindahl-Hirschman Index

    for i, (customer, amount) in enumerate(customer_totals.head(10).items()):
        dec_amount = _to_decimal(amount)
        share = _safe_divide(dec_amount, total_outstanding)
        share_pct = _pct(share) if share else Decimal("0")
        hhi_sum += (share_pct if share_pct else Decimal("0")) ** 2

        top_debtors.append({
            "rank": i + 1,
            "customer_name": str(customer),
            "outstanding_amount": str(dec_amount.quantize(TWO_PLACES)),
            "percentage_of_total": str(share_pct) + "%" if share_pct else "0%",
            "is_concentration_risk": bool(share and share > Decimal("0.10")),
        })

    # Compute full HHI
    for customer, amount in customer_totals.items():
        if customer not in [d["customer_name"] for d in top_debtors]:
            dec_amount = _to_decimal(amount)
            share = _safe_divide(dec_amount, total_outstanding)
            share_pct = _pct(share) if share else Decimal("0")
            hhi_sum += (share_pct if share_pct else Decimal("0")) ** 2

    top_10_share = sum(
        _to_decimal(d["outstanding_amount"]) for d in top_debtors
    )
    top_10_pct = _pct(_safe_divide(top_10_share, total_outstanding))

    risk_level = "Low"
    if top_10_pct and top_10_pct > Decimal("80"):
        risk_level = "High — top 10 customers hold >80% of receivables"
    elif top_10_pct and top_10_pct > Decimal("60"):
        risk_level = "Medium — moderate concentration in top customers"

    return {
        "top_debtors": top_debtors,
        "top_10_share_percentage": str(top_10_pct) + "%" if top_10_pct else "N/A",
        "hhi_index": str(hhi_sum.quantize(TWO_PLACES)) if hhi_sum else None,
        "risk_level": risk_level,
        "total_unique_debtors": len(customer_totals),
    }


# ===================================================================
# 5. CREDITOR AGING ANALYSIS with MSME Compliance
# ===================================================================

def analyze_creditor_aging(
    creditor_data: Union[pd.DataFrame, List[Dict]],
    as_of_date: Optional[date] = None,
    msme_vendors: Optional[List[str]] = None,
    bank_rate: Decimal = Decimal("6.50"),
) -> Dict[str, Any]:
    """
    Perform creditor aging analysis with MSME compliance checking.

    Checks compliance with Section 15 of MSMED Act, 2006 (payment within 45 days)
    and computes interest liability under Section 16 (3x bank rate).

    Args:
        creditor_data: DataFrame or list of dicts with columns:
            vendor_name, invoice_no, invoice_date, amount, payment_date, balance
        as_of_date: Date for aging calculation.
        msme_vendors: List of vendor names registered as MSMEs.
        bank_rate: Current RBI bank rate (for Section 16 interest calculation).

    Returns:
        Dict with aging_summary, msme_compliance, interest_liability,
        schedule_iii_disclosure, and detail records.
    """
    logger.info("Performing creditor aging analysis with MSME compliance check")
    if as_of_date is None:
        as_of_date = date.today()
    if msme_vendors is None:
        msme_vendors = []

    msme_set = {v.lower().strip() for v in msme_vendors}

    # Convert to DataFrame
    if isinstance(creditor_data, list):
        df = pd.DataFrame(creditor_data)
    else:
        df = creditor_data.copy()

    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]

    for date_col in ["invoice_date", "payment_date"]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)

    for num_col in ["amount", "balance"]:
        if num_col in df.columns:
            df[num_col] = pd.to_numeric(df[num_col], errors="coerce").fillna(0)

    if "balance" not in df.columns:
        df["balance"] = df.get("amount", 0)

    outstanding = df[df["balance"] > 0].copy()
    as_of_dt = pd.Timestamp(as_of_date)
    outstanding["age_days"] = (as_of_dt - outstanding["invoice_date"]).dt.days
    outstanding["age_days"] = outstanding["age_days"].fillna(0).astype(int)

    def _assign_bucket(days: int) -> str:
        for label, low, high in AGING_BUCKETS:
            if low <= days <= high:
                return label
        return "180+ days"

    outstanding["aging_bucket"] = outstanding["age_days"].apply(_assign_bucket)

    # Tag MSME vendors
    outstanding["is_msme"] = outstanding.get("vendor_name", pd.Series(dtype=str)).apply(
        lambda x: str(x).lower().strip() in msme_set if pd.notna(x) else False
    )

    # Aging summary
    aging_summary = OrderedDict()
    total_outstanding = Decimal("0")

    for label, low, high in AGING_BUCKETS:
        bucket_df = outstanding[outstanding["aging_bucket"] == label]
        bucket_amount = _to_decimal(bucket_df["balance"].sum())
        count = len(bucket_df)
        total_outstanding += bucket_amount

        aging_summary[label] = {
            "count": count,
            "amount": str(bucket_amount.quantize(TWO_PLACES)),
            "percentage_of_total": None,
        }

    for label in aging_summary:
        amount = _to_decimal(aging_summary[label]["amount"])
        pct = _safe_divide(amount * Decimal("100"), total_outstanding) if total_outstanding > Decimal("0") else Decimal("0")
        aging_summary[label]["percentage_of_total"] = str(pct.quantize(TWO_PLACES)) + "%" if pct else "0.00%"

    # MSME compliance analysis
    msme_compliance = _check_msme_compliance(outstanding, as_of_date, bank_rate)

    # Schedule III disclosure (Ind AS / Companies Act)
    schedule_iii = _generate_schedule_iii_disclosure(outstanding, as_of_date, total_outstanding)

    result = {
        "as_of_date": as_of_date.isoformat(),
        "aging_summary": aging_summary,
        "totals": {
            "total_outstanding": str(total_outstanding.quantize(TWO_PLACES)),
            "total_vendors": len(outstanding["vendor_name"].unique()) if "vendor_name" in outstanding.columns else 0,
        },
        "msme_compliance": msme_compliance,
        "schedule_iii_disclosure": schedule_iii,
        "record_count": len(outstanding),
    }
    return result


def _check_msme_compliance(
    outstanding: pd.DataFrame,
    as_of_date: date,
    bank_rate: Decimal,
) -> Dict[str, Any]:
    """
    Check MSME compliance under Sections 15-16 of MSMED Act, 2006.

    Section 15: Payment to MSME suppliers within 45 days of acceptance.
    Section 16: Interest at 3x bank rate for delayed payments.

    Args:
        outstanding: DataFrame with is_msme flag and age_days.
        as_of_date: Reference date.
        bank_rate: Current RBI bank rate.

    Returns:
        Dict with compliance status, violating vendors, interest liability.
    """
    msme_outstanding = outstanding[outstanding["is_msme"] == True].copy()  # noqa: E712

    if len(msme_outstanding) == 0:
        return {
            "msme_vendors_count": 0,
            "total_msme_outstanding": "0.00",
            "violations": [],
            "total_interest_liability": "0.00",
            "compliant": True,
            "notes": "No MSME vendors identified in the creditor ledger.",
        }

    # Section 16 interest rate = 3x bank rate (compound monthly)
    annual_interest_rate = bank_rate * MSME_INTEREST_RATE_MULTIPLIER
    daily_rate = annual_interest_rate / Decimal("365") / Decimal("100")

    violations = []
    total_interest = Decimal("0")
    total_msme_outstanding = Decimal("0")

    for _, row in msme_outstanding.iterrows():
        balance = _to_decimal(row["balance"])
        age_days = int(row.get("age_days", 0))
        total_msme_outstanding += balance

        if age_days > MSME_PAYMENT_LIMIT_DAYS:
            overdue_days = age_days - MSME_PAYMENT_LIMIT_DAYS
            # Simple interest for estimation (Act prescribes monthly compounding)
            interest = (balance * daily_rate * Decimal(str(overdue_days))).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            total_interest += interest

            violations.append({
                "vendor_name": str(row.get("vendor_name", "Unknown")),
                "invoice_no": str(row.get("invoice_no", "")),
                "invoice_date": str(row.get("invoice_date", ""))[:10],
                "amount": str(balance.quantize(TWO_PLACES)),
                "age_days": age_days,
                "overdue_days": overdue_days,
                "interest_liability": str(interest),
            })

    violations.sort(key=lambda x: int(x.get("overdue_days", 0)), reverse=True)

    return {
        "msme_vendors_count": len(msme_outstanding["vendor_name"].unique()) if "vendor_name" in msme_outstanding.columns else 0,
        "total_msme_outstanding": str(total_msme_outstanding.quantize(TWO_PLACES)),
        "overdue_count": len(violations),
        "violations": violations[:50],  # Limit for response size
        "total_interest_liability": str(total_interest.quantize(TWO_PLACES)),
        "interest_rate_applied": f"{annual_interest_rate}% p.a. (3x bank rate of {bank_rate}%)",
        "compliant": len(violations) == 0,
        "section_15_note": (
            "Section 15 of MSMED Act, 2006: Buyer shall make payment to MSME supplier "
            "within 45 days from the day of acceptance or deemed acceptance of goods/services."
        ),
        "section_16_note": (
            "Section 16: Buyer liable to pay compound interest with monthly rests at "
            "3 times the bank rate notified by RBI on the amount due."
        ),
    }


def _generate_schedule_iii_disclosure(
    outstanding: pd.DataFrame,
    as_of_date: date,
    total_outstanding: Decimal,
) -> Dict[str, Any]:
    """
    Generate Schedule III disclosure for trade payables per Companies Act, 2013.

    Required disclosure: Outstanding dues of micro and small enterprises
    (separately from other creditors) with amounts outstanding > 45 days.

    Args:
        outstanding: DataFrame with MSME flags.
        as_of_date: Reference date.
        total_outstanding: Total creditor balance.

    Returns:
        Dict formatted for Schedule III Note to Accounts.
    """
    msme_df = outstanding[outstanding.get("is_msme", False) == True]  # noqa: E712
    non_msme_df = outstanding[outstanding.get("is_msme", False) != True]  # noqa: E712

    msme_total = _to_decimal(msme_df["balance"].sum()) if len(msme_df) > 0 else Decimal("0")
    msme_overdue = _to_decimal(
        msme_df[msme_df["age_days"] > 45]["balance"].sum()
    ) if len(msme_df) > 0 and "age_days" in msme_df.columns else Decimal("0")

    non_msme_total = _to_decimal(non_msme_df["balance"].sum()) if len(non_msme_df) > 0 else Decimal("0")

    # Disputed vs undisputed breakdown
    disputed_col_exists = "disputed" in outstanding.columns
    disputed_total = Decimal("0")
    undisputed_total = total_outstanding
    if disputed_col_exists:
        disputed_total = _to_decimal(outstanding[outstanding["disputed"] == True]["balance"].sum())  # noqa: E712
        undisputed_total = total_outstanding - disputed_total

    return {
        "note_title": "Trade Payables Aging Schedule (Schedule III, Division II)",
        "as_at": as_of_date.isoformat(),
        "msme_outstanding": {
            "total": str(msme_total.quantize(TWO_PLACES)),
            "overdue_beyond_45_days": str(msme_overdue.quantize(TWO_PLACES)),
            "within_due_date": str((msme_total - msme_overdue).quantize(TWO_PLACES)),
        },
        "others_outstanding": {
            "total": str(non_msme_total.quantize(TWO_PLACES)),
        },
        "total_trade_payables": str(total_outstanding.quantize(TWO_PLACES)),
        "disputed": str(disputed_total.quantize(TWO_PLACES)),
        "undisputed": str(undisputed_total.quantize(TWO_PLACES)),
        "disclosure_note": (
            "The above information regarding Micro, Small and Medium Enterprises has been "
            "determined to the extent such parties have been identified on the basis of "
            "information available with the Company. This has been relied upon by the auditors."
        ),
    }


# ===================================================================
# 6. COMPARATIVE FINANCIAL STATEMENTS
# ===================================================================

def generate_comparative_statements(
    periods: List[Dict[str, Any]],
    period_labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate comparative financial statements with trend and common-size analysis.

    Supports 2-3 years of data. Computes absolute change, percentage change,
    and common-size ratios for both P&L and Balance Sheet items.

    Args:
        periods: List of financial aggregates dicts (one per year, newest first).
            Each dict should have keys from extract_financials_from_tb output.
        period_labels: Optional labels like ['FY 2024-25', 'FY 2023-24'].

    Returns:
        Dict with comparative_pl, comparative_bs, trend_flags, and common_size.
    """
    logger.info("Generating comparative financial statements for %d periods", len(periods))

    if len(periods) < 2:
        return {"error": "At least 2 periods required for comparative analysis."}
    if len(periods) > 3:
        periods = periods[:3]

    if period_labels is None:
        period_labels = [f"Period {i+1}" for i in range(len(periods))]

    # P&L line items for comparison
    pl_items = [
        ("revenue", "Revenue from Operations"),
        ("other_income", "Other Income"),
        ("total_income", "Total Income"),
        ("cogs", "Cost of Goods Sold / Materials Consumed"),
        ("employee_cost", "Employee Benefit Expense"),
        ("depreciation", "Depreciation & Amortization"),
        ("finance_cost", "Finance Costs"),
        ("other_expenses", "Other Expenses"),
        ("total_expenses", "Total Expenses"),
        ("tax_expense", "Tax Expense"),
    ]

    # Balance sheet items
    bs_items = [
        ("current_assets", "Total Current Assets"),
        ("non_current_assets", "Total Non-Current Assets"),
        ("total_assets", "Total Assets"),
        ("current_liabilities", "Total Current Liabilities"),
        ("non_current_liabilities", "Total Non-Current Liabilities"),
        ("total_liabilities", "Total Liabilities"),
        ("equity", "Shareholders Equity"),
        ("inventory", "Inventories"),
        ("receivables", "Trade Receivables"),
        ("cash_and_bank", "Cash & Bank Balances"),
        ("payables", "Trade Payables"),
        ("short_term_borrowings", "Short-Term Borrowings"),
        ("long_term_borrowings", "Long-Term Borrowings"),
    ]

    comparative_pl = _build_comparative_table(periods, period_labels, pl_items)
    comparative_bs = _build_comparative_table(periods, period_labels, bs_items)

    # Common-size analysis
    common_size_pl = _build_common_size(periods, period_labels, pl_items, base_key="revenue")
    common_size_bs = _build_common_size(periods, period_labels, bs_items, base_key="total_assets")

    # Trend flags (items with >20% YoY variance)
    trend_flags = _detect_trends(periods, period_labels, pl_items + bs_items)

    # Computed metrics
    computed_metrics = []
    for i in range(len(periods)):
        p = periods[i]
        pat = _to_decimal(p.get("total_income", 0)) - _to_decimal(p.get("total_expenses", 0))
        gross_profit = _to_decimal(p.get("revenue", 0)) - _to_decimal(p.get("cogs", 0))
        working_capital = _to_decimal(p.get("current_assets", 0)) - _to_decimal(p.get("current_liabilities", 0))
        computed_metrics.append({
            "period": period_labels[i],
            "pat": str(pat.quantize(TWO_PLACES)),
            "gross_profit": str(gross_profit.quantize(TWO_PLACES)),
            "working_capital": str(working_capital.quantize(TWO_PLACES)),
        })

    return {
        "comparative_pl": comparative_pl,
        "comparative_bs": comparative_bs,
        "common_size_pl": common_size_pl,
        "common_size_bs": common_size_bs,
        "trend_flags": trend_flags,
        "computed_metrics": computed_metrics,
        "periods": period_labels,
    }


def _build_comparative_table(
    periods: List[Dict],
    labels: List[str],
    items: List[Tuple[str, str]],
) -> List[Dict[str, Any]]:
    """
    Build a comparative table with absolute and percentage changes.

    For each line item, shows values for each period and computes
    YoY absolute change and percentage change.

    Args:
        periods: List of period data dicts.
        labels: Period labels.
        items: List of (key, display_name) tuples.

    Returns:
        List of row dicts with values, changes, and change percentages.
    """
    rows = []
    for key, display_name in items:
        row: Dict[str, Any] = {"item": display_name, "key": key}
        values = []

        for i, period in enumerate(periods):
            val = _to_decimal(period.get(key, 0))
            row[labels[i]] = str(val.quantize(TWO_PLACES))
            values.append(val)

        # YoY changes (comparing consecutive periods)
        changes = []
        for i in range(len(values) - 1):
            current = values[i]
            previous = values[i + 1]
            abs_change = current - previous
            pct_change = _safe_divide(abs_change * Decimal("100"), abs(previous)) if previous != Decimal("0") else None

            changes.append({
                "comparison": f"{labels[i]} vs {labels[i+1]}",
                "absolute_change": str(abs_change.quantize(TWO_PLACES)),
                "percentage_change": str(pct_change.quantize(TWO_PLACES)) + "%" if pct_change is not None else "N/A",
            })

        row["changes"] = changes
        rows.append(row)

    return rows


def _build_common_size(
    periods: List[Dict],
    labels: List[str],
    items: List[Tuple[str, str]],
    base_key: str,
) -> List[Dict[str, Any]]:
    """
    Build common-size analysis (each item as % of base).

    For P&L: base = Revenue. For BS: base = Total Assets.

    Args:
        periods: Period data.
        labels: Period labels.
        items: Line items.
        base_key: Key for the base value (e.g., 'revenue', 'total_assets').

    Returns:
        List of rows with common-size percentages for each period.
    """
    rows = []
    for key, display_name in items:
        row: Dict[str, Any] = {"item": display_name}
        for i, period in enumerate(periods):
            val = _to_decimal(period.get(key, 0))
            base = _to_decimal(period.get(base_key, 0))
            pct = _safe_divide(val * Decimal("100"), base) if base != Decimal("0") else None
            row[f"{labels[i]}_pct"] = str(pct.quantize(TWO_PLACES)) + "%" if pct is not None else "N/A"
            row[f"{labels[i]}_value"] = str(val.quantize(TWO_PLACES))
        rows.append(row)
    return rows


def _detect_trends(
    periods: List[Dict],
    labels: List[str],
    items: List[Tuple[str, str]],
    threshold_pct: Decimal = Decimal("20"),
) -> List[Dict[str, Any]]:
    """
    Detect significant trends — items with >20% YoY variance.

    Args:
        periods: Period data.
        labels: Period labels.
        items: Line items to check.
        threshold_pct: Percentage change threshold for flagging.

    Returns:
        List of flagged items with details.
    """
    flags = []

    for key, display_name in items:
        for i in range(len(periods) - 1):
            current = _to_decimal(periods[i].get(key, 0))
            previous = _to_decimal(periods[i + 1].get(key, 0))

            if previous == Decimal("0"):
                if current != Decimal("0"):
                    flags.append({
                        "item": display_name,
                        "comparison": f"{labels[i]} vs {labels[i+1]}",
                        "current_value": str(current.quantize(TWO_PLACES)),
                        "previous_value": "0.00",
                        "change": "New item (did not exist in prior period)",
                        "severity": "Info",
                    })
                continue

            abs_change = current - previous
            pct_change = _safe_divide(abs_change * Decimal("100"), abs(previous))

            if pct_change is not None and abs(pct_change) > threshold_pct:
                direction = "Increase" if pct_change > Decimal("0") else "Decrease"
                severity = "High" if abs(pct_change) > Decimal("50") else "Medium"

                flags.append({
                    "item": display_name,
                    "comparison": f"{labels[i]} vs {labels[i+1]}",
                    "current_value": str(current.quantize(TWO_PLACES)),
                    "previous_value": str(previous.quantize(TWO_PLACES)),
                    "absolute_change": str(abs_change.quantize(TWO_PLACES)),
                    "percentage_change": str(pct_change.quantize(TWO_PLACES)) + "%",
                    "direction": direction,
                    "severity": severity,
                })

    # Sort by absolute percentage change descending
    flags.sort(key=lambda x: abs(_to_decimal(x.get("percentage_change", "0").replace("%", ""))), reverse=True)
    return flags


# ===================================================================
# 7. RED FLAG DETECTOR
# ===================================================================

def detect_red_flags(
    current_financials: Dict[str, Decimal],
    previous_financials: Optional[Dict[str, Decimal]] = None,
    current_ocf: Optional[Decimal] = None,
    related_party_transactions: Optional[Decimal] = None,
    contingent_liabilities: Optional[Decimal] = None,
) -> Dict[str, Any]:
    """
    Detect financial red flags for audit and due-diligence purposes.

    Checks for earnings quality, solvency risks, operational deterioration,
    and governance concerns based on Indian regulatory thresholds.

    Args:
        current_financials: Current period financial aggregates.
        previous_financials: Prior period aggregates (for trend checks).
        current_ocf: Operating Cash Flow for current period.
        related_party_transactions: Total RPT amount.
        contingent_liabilities: Total contingent liabilities.

    Returns:
        Dict with red_flags list (each with severity, description, recommendation),
        risk_score, and overall assessment.
    """
    logger.info("Running red flag detection")
    red_flags: List[Dict[str, Any]] = []

    curr = current_financials
    prev = previous_financials or {}

    revenue = _to_decimal(curr.get("revenue", 0))
    cogs = _to_decimal(curr.get("cogs", 0))
    total_expenses = _to_decimal(curr.get("total_expenses", 0))
    total_income = _to_decimal(curr.get("total_income", 0))
    pat = total_income - total_expenses
    gross_profit = revenue - cogs
    equity = _to_decimal(curr.get("equity", 0))
    total_debt = _to_decimal(curr.get("short_term_borrowings", 0)) + _to_decimal(curr.get("long_term_borrowings", 0))
    current_assets = _to_decimal(curr.get("current_assets", 0))
    current_liabilities = _to_decimal(curr.get("current_liabilities", 0))
    receivables = _to_decimal(curr.get("receivables", 0))
    inventory = _to_decimal(curr.get("inventory", 0))
    finance_cost = _to_decimal(curr.get("finance_cost", 0))
    depreciation = _to_decimal(curr.get("depreciation", 0))
    ebitda = gross_profit - _to_decimal(curr.get("employee_cost", 0)) - _to_decimal(curr.get("other_expenses", 0))

    prev_revenue = _to_decimal(prev.get("revenue", 0))
    prev_cogs = _to_decimal(prev.get("cogs", 0))
    prev_receivables = _to_decimal(prev.get("receivables", 0))
    prev_inventory = _to_decimal(prev.get("inventory", 0))
    prev_gross_profit = prev_revenue - prev_cogs

    # --- Flag 1: Declining gross margins (>5% drop YoY) ---
    if prev_revenue > Decimal("0") and revenue > Decimal("0"):
        curr_gpm = _safe_divide(gross_profit, revenue)
        prev_gpm = _safe_divide(prev_gross_profit, prev_revenue)
        if curr_gpm is not None and prev_gpm is not None:
            gpm_decline = prev_gpm - curr_gpm
            if gpm_decline > Decimal("0.05"):
                red_flags.append({
                    "flag": "Declining Gross Margins",
                    "severity": "High",
                    "current_value": str(_pct(curr_gpm)) + "%",
                    "previous_value": str(_pct(prev_gpm)) + "%",
                    "decline": str(_pct(gpm_decline)) + " percentage points",
                    "description": (
                        f"Gross profit margin declined by {_pct(gpm_decline)} percentage points. "
                        "May indicate pricing pressure, input cost inflation, or loss of competitive advantage."
                    ),
                    "recommendation": (
                        "Investigate cost structure. Check raw material price trends. "
                        "Review pricing strategy. Analyze product mix changes."
                    ),
                })

    # --- Flag 2: Receivables growing faster than revenue ---
    if prev_revenue > Decimal("0") and prev_receivables > Decimal("0"):
        rev_growth = _safe_divide((revenue - prev_revenue), prev_revenue)
        rec_growth = _safe_divide((receivables - prev_receivables), prev_receivables)
        if rev_growth is not None and rec_growth is not None and rec_growth > rev_growth + Decimal("0.05"):
            red_flags.append({
                "flag": "Receivables Growing Faster Than Revenue",
                "severity": "High",
                "revenue_growth": str(_pct(rev_growth)) + "%",
                "receivables_growth": str(_pct(rec_growth)) + "%",
                "description": (
                    "Trade receivables are growing significantly faster than revenue. "
                    "This could indicate channel stuffing, relaxed credit policies, or revenue recognition issues."
                ),
                "recommendation": (
                    "Review credit policies. Check for related party sales. "
                    "Verify revenue recognition. Analyze debtor aging for spikes."
                ),
            })

    # --- Flag 3: Inventory buildup without revenue growth ---
    if prev_revenue > Decimal("0") and prev_inventory > Decimal("0"):
        inv_growth = _safe_divide((inventory - prev_inventory), prev_inventory)
        if rev_growth is not None and inv_growth is not None:
            if inv_growth > Decimal("0.15") and (rev_growth is None or rev_growth < Decimal("0.05")):
                red_flags.append({
                    "flag": "Inventory Buildup Without Revenue Growth",
                    "severity": "Medium",
                    "inventory_growth": str(_pct(inv_growth)) + "%",
                    "revenue_growth": str(_pct(rev_growth)) + "%" if rev_growth is not None else "N/A",
                    "description": (
                        "Inventory is accumulating while revenue growth is stagnant. "
                        "Risk of obsolescence, overvaluation, or demand slowdown."
                    ),
                    "recommendation": (
                        "Physical stock verification. Check NRV assessment. "
                        "Review slow/non-moving inventory. Verify FIFO/weighted average method."
                    ),
                })

    # --- Flag 4: Negative OCF with positive PAT (earnings quality) ---
    if current_ocf is not None and pat > Decimal("0") and current_ocf < Decimal("0"):
        red_flags.append({
            "flag": "Negative Operating Cash Flow with Positive PAT",
            "severity": "Critical",
            "pat": str(pat.quantize(TWO_PLACES)),
            "operating_cash_flow": str(current_ocf.quantize(TWO_PLACES)),
            "description": (
                "Company reports profits but is burning cash from operations. "
                "Severe earnings quality concern. May indicate aggressive revenue "
                "recognition, capitalization of expenses, or working capital mismanagement."
            ),
            "recommendation": (
                "Deep-dive into revenue recognition policies. Check for fictitious sales. "
                "Verify receivables directly with customers. Review capitalization policies. "
                "This is a CARO 2020 reportable matter."
            ),
        })

    # --- Flag 5: Related party transactions > 10% of revenue ---
    if related_party_transactions is not None and revenue > Decimal("0"):
        rpt_pct = _safe_divide(related_party_transactions, revenue)
        if rpt_pct is not None and rpt_pct > Decimal("0.10"):
            red_flags.append({
                "flag": "Significant Related Party Transactions",
                "severity": "High",
                "rpt_amount": str(related_party_transactions.quantize(TWO_PLACES)),
                "rpt_percentage_of_revenue": str(_pct(rpt_pct)) + "%",
                "description": (
                    f"Related party transactions constitute {_pct(rpt_pct)}% of revenue. "
                    "High RPT levels require scrutiny for arm's length pricing and commercial substance."
                ),
                "recommendation": (
                    "Verify arm's length pricing per Section 188 Companies Act. "
                    "Check transfer pricing compliance. Review Board/Audit Committee approvals. "
                    "Ensure AS-18/Ind AS 24 disclosures are complete."
                ),
            })

    # --- Flag 6: Contingent liabilities > 20% of net worth ---
    if contingent_liabilities is not None and equity > Decimal("0"):
        cl_pct = _safe_divide(contingent_liabilities, equity)
        if cl_pct is not None and cl_pct > Decimal("0.20"):
            red_flags.append({
                "flag": "High Contingent Liabilities",
                "severity": "High",
                "contingent_liabilities": str(contingent_liabilities.quantize(TWO_PLACES)),
                "percentage_of_net_worth": str(_pct(cl_pct)) + "%",
                "description": (
                    f"Contingent liabilities are {_pct(cl_pct)}% of net worth. "
                    "Material contingencies may crystallize and impair solvency."
                ),
                "recommendation": (
                    "Review each contingent liability for probability of outflow. "
                    "Check if any should be reclassified as provisions per AS-29/Ind AS 37. "
                    "Verify adequacy of disclosures."
                ),
            })

    # --- Flag 7: Debt-to-equity > 2.0 (over-leveraged) ---
    if equity > Decimal("0"):
        de_ratio = _safe_divide(total_debt, equity)
        if de_ratio is not None and de_ratio > Decimal("2.0"):
            red_flags.append({
                "flag": "Over-Leveraged (High Debt-to-Equity)",
                "severity": "High",
                "debt_to_equity": str(de_ratio.quantize(TWO_PLACES)),
                "total_debt": str(total_debt.quantize(TWO_PLACES)),
                "equity": str(equity.quantize(TWO_PLACES)),
                "description": (
                    f"Debt-to-equity ratio of {de_ratio.quantize(TWO_PLACES)} exceeds "
                    "the prudent threshold of 2.0. Company is heavily leveraged."
                ),
                "recommendation": (
                    "Review debt covenants for potential breaches. "
                    "Assess refinancing risk. Consider equity infusion or debt restructuring. "
                    "Check going concern implications."
                ),
            })

    # --- Flag 8: Current ratio < 1.0 (liquidity crisis) ---
    if current_liabilities > Decimal("0"):
        cr = _safe_divide(current_assets, current_liabilities)
        if cr is not None and cr < Decimal("1.0"):
            red_flags.append({
                "flag": "Liquidity Crisis (Current Ratio Below 1.0)",
                "severity": "Critical",
                "current_ratio": str(cr.quantize(TWO_PLACES)),
                "current_assets": str(current_assets.quantize(TWO_PLACES)),
                "current_liabilities": str(current_liabilities.quantize(TWO_PLACES)),
                "description": (
                    "Current liabilities exceed current assets. "
                    "Immediate liquidity risk. Company may struggle to meet short-term obligations."
                ),
                "recommendation": (
                    "Assess going concern. Review cash flow forecasts. "
                    "Negotiate extended credit terms. Consider working capital loan. "
                    "Check bank covenant compliance. SA 570 going concern evaluation required."
                ),
            })

    # --- Flag 9: Interest coverage < 1.5 (debt servicing stress) ---
    if finance_cost > Decimal("0"):
        icr = _safe_divide(ebitda, finance_cost)
        if icr is not None and icr < Decimal("1.5"):
            severity = "Critical" if icr < Decimal("1.0") else "High"
            red_flags.append({
                "flag": "Debt Servicing Stress (Low Interest Coverage)",
                "severity": severity,
                "interest_coverage_ratio": str(icr.quantize(TWO_PLACES)),
                "ebitda": str(ebitda.quantize(TWO_PLACES)),
                "finance_cost": str(finance_cost.quantize(TWO_PLACES)),
                "description": (
                    f"Interest coverage ratio of {icr.quantize(TWO_PLACES)} is below "
                    "the safe threshold of 1.5. "
                    + ("Unable to cover interest from operations." if icr < Decimal("1.0")
                       else "Tight margin for debt servicing.")
                ),
                "recommendation": (
                    "Renegotiate interest rates. Consider debt restructuring. "
                    "Check SMA/NPA classification risk with lenders. "
                    "Explore refinancing at lower rates."
                ),
            })

    # --- Compute risk score ---
    severity_weights = {"Critical": 30, "High": 20, "Medium": 10, "Low": 5}
    risk_score = sum(severity_weights.get(f.get("severity", "Low"), 0) for f in red_flags)
    risk_score = min(risk_score, 100)

    if risk_score >= 70:
        overall_assessment = "Critical Risk — Immediate attention required. Consider qualified audit opinion."
    elif risk_score >= 40:
        overall_assessment = "High Risk — Multiple significant concerns. Enhanced audit procedures recommended."
    elif risk_score >= 20:
        overall_assessment = "Moderate Risk — Some areas need attention. Standard audit procedures with focused testing."
    elif risk_score > 0:
        overall_assessment = "Low Risk — Minor concerns noted. Normal audit procedures sufficient."
    else:
        overall_assessment = "No Red Flags — Financial position appears healthy based on available data."

    return {
        "red_flags": red_flags,
        "total_flags": len(red_flags),
        "risk_score": risk_score,
        "risk_score_max": 100,
        "overall_assessment": overall_assessment,
        "severity_summary": {
            "critical": sum(1 for f in red_flags if f.get("severity") == "Critical"),
            "high": sum(1 for f in red_flags if f.get("severity") == "High"),
            "medium": sum(1 for f in red_flags if f.get("severity") == "Medium"),
            "low": sum(1 for f in red_flags if f.get("severity") == "Low"),
        },
        "audit_implications": _get_audit_implications(red_flags),
    }


def _get_audit_implications(red_flags: List[Dict]) -> List[str]:
    """
    Derive audit implications from detected red flags.

    Maps red flags to relevant Standards on Auditing (SA) and
    audit procedures that should be performed.

    Args:
        red_flags: List of red flag dicts.

    Returns:
        List of audit implication strings.
    """
    implications = []
    flag_names = {f.get("flag", "") for f in red_flags}

    if "Negative Operating Cash Flow with Positive PAT" in flag_names:
        implications.append(
            "SA 240: Perform extended revenue testing for fraud risk. "
            "Verify revenue cut-off. Send debtor confirmations."
        )
        implications.append(
            "CARO 2020 Clause (ix): Report on utilization of term loans and working capital."
        )

    if "Liquidity Crisis (Current Ratio Below 1.0)" in flag_names:
        implications.append(
            "SA 570: Evaluate going concern. Obtain management representation on "
            "ability to continue operations. Consider emphasis of matter paragraph."
        )

    if "Over-Leveraged (High Debt-to-Equity)" in flag_names:
        implications.append(
            "SA 570: Assess ability to refinance. Review debt covenant compliance. "
            "Verify completeness of borrowing disclosures."
        )

    if "Significant Related Party Transactions" in flag_names:
        implications.append(
            "SA 550: Verify arm's length nature. Check Board/Audit Committee approvals. "
            "Verify Section 188 compliance and Ind AS 24 disclosures."
        )

    if "Receivables Growing Faster Than Revenue" in flag_names:
        implications.append(
            "SA 505: Send direct confirmations to major debtors. "
            "SA 540: Review ECL model assumptions and provisioning adequacy."
        )

    if "Declining Gross Margins" in flag_names:
        implications.append(
            "SA 520: Perform analytical procedures on cost components. "
            "Verify inventory valuation at NRV per AS-2/Ind AS 2."
        )

    if "High Contingent Liabilities" in flag_names:
        implications.append(
            "SA 501: Obtain legal confirmations. Review litigation status. "
            "Assess whether provisions should be recognized per AS-29/Ind AS 37."
        )

    if "Debt Servicing Stress (Low Interest Coverage)" in flag_names:
        implications.append(
            "SA 570: Going concern assessment required. Check for SMA classification. "
            "Verify interest capitalization policies."
        )

    if not implications:
        implications.append("No specific audit implications arising from the analysis.")

    return implications


# ===================================================================
# Convenience: Full Analysis Pipeline
# ===================================================================

def run_full_analysis(
    trial_balance_bytes: bytes,
    filename: str = "trial_balance.xlsx",
    previous_period_bytes: Optional[bytes] = None,
    previous_filename: str = "previous_tb.xlsx",
    shares_outstanding: Optional[Decimal] = None,
    debtor_data: Optional[List[Dict]] = None,
    creditor_data: Optional[List[Dict]] = None,
    msme_vendors: Optional[List[str]] = None,
    additional_cf_info: Optional[Dict[str, Decimal]] = None,
    related_party_transactions: Optional[Decimal] = None,
    contingent_liabilities: Optional[Decimal] = None,
) -> Dict[str, Any]:
    """
    Run the complete financial analysis pipeline.

    Orchestrates trial balance parsing, ratio analysis, cash flow generation,
    debtor/creditor aging, comparative statements, and red flag detection.

    Args:
        trial_balance_bytes: Current period trial balance Excel file bytes.
        filename: Filename of current trial balance.
        previous_period_bytes: Optional previous period trial balance bytes.
        previous_filename: Filename of previous trial balance.
        shares_outstanding: Number of equity shares.
        debtor_data: Debtor ledger data for aging analysis.
        creditor_data: Creditor ledger data for aging analysis.
        msme_vendors: List of MSME vendor names.
        additional_cf_info: Additional info for cash flow statement.
        related_party_transactions: RPT amount for red flag detection.
        contingent_liabilities: Contingent liabilities for red flag detection.

    Returns:
        Dict containing all analysis results keyed by module name.
    """
    logger.info("Starting full financial analysis pipeline")
    results: Dict[str, Any] = {}

    # Step 1: Parse current trial balance
    tb_result = parse_trial_balance(trial_balance_bytes, filename)
    results["trial_balance"] = tb_result

    if not tb_result["accounts"]:
        results["error"] = "Failed to parse trial balance. Cannot proceed with analysis."
        return results

    # Step 2: Extract financial aggregates
    current_financials = extract_financials_from_tb(tb_result["accounts"])
    results["financial_aggregates"] = {k: str(v.quantize(TWO_PLACES)) for k, v in current_financials.items()}

    # Step 3: Ratio analysis
    ratios = compute_ratios(current_financials, shares_outstanding=shares_outstanding)
    results["ratio_analysis"] = ratios

    # Step 4: Previous period (if provided)
    previous_financials = {}
    if previous_period_bytes:
        prev_tb = parse_trial_balance(previous_period_bytes, previous_filename)
        if prev_tb["accounts"]:
            previous_financials = extract_financials_from_tb(prev_tb["accounts"])

            # Comparative statements
            periods = [current_financials, previous_financials]
            labels = ["Current Year", "Previous Year"]
            comparative = generate_comparative_statements(
                [{k: str(v) for k, v in p.items()} for p in periods],
                labels
            )
            results["comparative_statements"] = comparative

    # Step 5: Cash flow statement (if previous period available)
    if previous_financials:
        current_pl = {
            "pat": current_financials.get("total_income", Decimal("0")) - current_financials.get("total_expenses", Decimal("0")),
            "depreciation": current_financials.get("depreciation", Decimal("0")),
            "finance_cost": current_financials.get("finance_cost", Decimal("0")),
            "interest_income": Decimal("0"),
            "dividend_income": Decimal("0"),
            "loss_on_sale_of_asset": Decimal("0"),
            "gain_on_sale_of_asset": Decimal("0"),
            "provision_for_doubtful_debts": Decimal("0"),
            "other_non_cash_items": Decimal("0"),
            "tax_expense": current_financials.get("tax_expense", Decimal("0")),
        }
        current_bs = {
            "receivables": current_financials.get("receivables", Decimal("0")),
            "inventory": current_financials.get("inventory", Decimal("0")),
            "other_current_assets": Decimal("0"),
            "payables": current_financials.get("payables", Decimal("0")),
            "other_current_liabilities": Decimal("0"),
            "provisions": Decimal("0"),
            "fixed_assets_gross": current_financials.get("non_current_assets", Decimal("0")),
            "accumulated_depreciation": Decimal("0"),
            "capital_wip": Decimal("0"),
            "investments": Decimal("0"),
            "long_term_borrowings": current_financials.get("long_term_borrowings", Decimal("0")),
            "short_term_borrowings": current_financials.get("short_term_borrowings", Decimal("0")),
            "equity": current_financials.get("equity", Decimal("0")),
            "reserves_surplus": Decimal("0"),
            "cash_and_bank": current_financials.get("cash_and_bank", Decimal("0")),
        }
        previous_bs = {
            "receivables": previous_financials.get("receivables", Decimal("0")),
            "inventory": previous_financials.get("inventory", Decimal("0")),
            "other_current_assets": Decimal("0"),
            "payables": previous_financials.get("payables", Decimal("0")),
            "other_current_liabilities": Decimal("0"),
            "provisions": Decimal("0"),
            "fixed_assets_gross": previous_financials.get("non_current_assets", Decimal("0")),
            "accumulated_depreciation": Decimal("0"),
            "capital_wip": Decimal("0"),
            "investments": Decimal("0"),
            "long_term_borrowings": previous_financials.get("long_term_borrowings", Decimal("0")),
            "short_term_borrowings": previous_financials.get("short_term_borrowings", Decimal("0")),
            "equity": previous_financials.get("equity", Decimal("0")),
            "reserves_surplus": Decimal("0"),
            "cash_and_bank": previous_financials.get("cash_and_bank", Decimal("0")),
        }

        cash_flow = generate_cash_flow(current_pl, current_bs, previous_bs, additional_cf_info)
        results["cash_flow_statement"] = cash_flow

        # Get OCF for red flag detection
        current_ocf = _to_decimal(cash_flow["summary"]["net_operating_cash_flow"])
    else:
        current_ocf = None

    # Step 6: Debtor aging
    if debtor_data:
        results["debtor_aging"] = analyze_debtor_aging(debtor_data)

    # Step 7: Creditor aging
    if creditor_data:
        results["creditor_aging"] = analyze_creditor_aging(creditor_data, msme_vendors=msme_vendors)

    # Step 8: Red flag detection
    red_flags = detect_red_flags(
        current_financials,
        previous_financials=previous_financials if previous_financials else None,
        current_ocf=current_ocf,
        related_party_transactions=related_party_transactions,
        contingent_liabilities=contingent_liabilities,
    )
    results["red_flags"] = red_flags

    logger.info(
        "Full analysis complete. Red flags: %d, Risk score: %d/100",
        red_flags["total_flags"], red_flags["risk_score"]
    )
    return results
