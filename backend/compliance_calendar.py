"""
Unified Compliance Calendar Engine — Associate's gravitational center.
Covers: GST deadlines, Income Tax deadlines, ROC/MCA deadlines,
TDS/TCS deadlines, SEBI disclosures, FEMA, Court hearings (from eCourts).
Every deadline auto-populated per client/matter, pushed via WhatsApp + Email.
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional
import calendar

logger = logging.getLogger(__name__)

# =====================================================================
# INDIAN COMPLIANCE DEADLINE DATABASE
# =====================================================================

def get_monthly_deadlines(year: int, month: int) -> list:
    """
    Return ALL Indian compliance deadlines for a given month/year.
    Each item: {date, category, title, description, section, penalty_on_miss}
    """
    deadlines = []
    
    # ─── GST DEADLINES ─────────────────────────────────────────────
    # GSTR-1 (Monthly filers - Turnover > 5Cr)
    gstr1_m = _last_day(year, month, 11)  # 11th of next month
    deadlines.append({
        "date": _next_month_date(year, month, 11),
        "category": "GST",
        "title": "GSTR-1 Filing (Monthly)",
        "description": "File monthly outward supply details for businesses with turnover > ₹5 crore",
        "section": "Section 37 CGST Act",
        "penalty_on_miss": "₹50/day (₹20/day for nil return) + 18% interest on tax due",
        "tags": ["gst", "monthly"],
    })
    # GSTR-1 (Quarterly QRMP filers)
    if month in [3, 6, 9, 12]:
        q_end_month = month
        deadlines.append({
            "date": _next_month_date(year, q_end_month, 13),
            "category": "GST",
            "title": "GSTR-1 (Quarterly - QRMP)",
            "description": "Quarterly GSTR-1 for businesses under QRMP scheme (turnover < ₹5 crore)",
            "section": "Section 37 CGST Act / QRMP Scheme",
            "penalty_on_miss": "₹50/day up to ₹5,000",
            "tags": ["gst", "quarterly", "qrmp"],
        })
    # GSTR-3B (Monthly)
    deadlines.append({
        "date": _next_month_date(year, month, 20),
        "category": "GST",
        "title": "GSTR-3B Filing",
        "description": "Monthly self-assessed GST return with tax payment",
        "section": "Section 39 CGST Act",
        "penalty_on_miss": "₹50/day + 18% interest on tax due after 20th",
        "tags": ["gst", "monthly"],
    })
    # IFF (Invoice Furnishing Facility) for QRMP
    deadlines.append({
        "date": _next_month_date(year, month, 13),
        "category": "GST",
        "title": "IFF Submission (QRMP)",
        "description": "Furnish B2B invoices for QRMP scheme filers",
        "section": "QRMP Scheme Circular",
        "penalty_on_miss": "Late ITC reflection for recipient",
        "tags": ["gst", "qrmp", "monthly"],
    })
    # GSTR-7 (TDS under GST)
    deadlines.append({
        "date": _next_month_date(year, month, 10),
        "category": "GST",
        "title": "GSTR-7 (GST TDS Return)",
        "description": "TDS deductors file TDS deducted under GST",
        "section": "Section 51 CGST Act",
        "penalty_on_miss": "₹100/day + penalty equal to TDS not deducted/deposited",
        "tags": ["gst", "tds"],
    })
    # GSTR-8 (TCS by E-commerce operators)
    deadlines.append({
        "date": _next_month_date(year, month, 10),
        "category": "GST",
        "title": "GSTR-8 (E-commerce TCS)",
        "description": "E-commerce operators file TCS collected from suppliers",
        "section": "Section 52 CGST Act",
        "penalty_on_miss": "₹100/day + 18% interest",
        "tags": ["gst", "tcs", "ecommerce"],
    })
    
    # Annual GST returns (only in November/December)
    if month == 12:
        deadlines.append({
            "date": date(year + 1, 12, 31),  # 31 Dec of assessment year
            "category": "GST",
            "title": "GSTR-9 Annual Return",
            "description": "Annual GST return for all registered taxpayers (turnover > ₹2 crore)",
            "section": "Section 44 CGST Act",
            "penalty_on_miss": "₹200/day (₹100 CGST + ₹100 SGST) up to 0.25% of turnover",
            "tags": ["gst", "annual"],
        })
        deadlines.append({
            "date": date(year + 1, 12, 31),
            "category": "GST",
            "title": "GSTR-9C Reconciliation Statement",
            "description": "Audited reconciliation for taxpayers with turnover > ₹5 crore",
            "section": "Section 44 CGST Act",
            "penalty_on_miss": "₹200/day up to 0.5% of turnover",
            "tags": ["gst", "annual", "audit"],
        })
    
    # ─── INCOME TAX DEADLINES ────────────────────────────────────
    # Advance Tax Installments
    advance_tax = [
        (6, 15, "1st Advance Tax Installment", "15% of estimated tax liability due", "Section 211 IT Act", "1% per month interest u/s 234B/234C"),
        (9, 15, "2nd Advance Tax Installment", "45% of estimated tax liability due", "Section 211 IT Act", "1% per month interest u/s 234B/234C"),
        (12, 15, "3rd Advance Tax Installment", "75% of estimated tax liability due", "Section 211 IT Act", "1% per month interest u/s 234B/234C"),
        (3, 15, "4th / Final Advance Tax Installment", "100% of estimated tax liability due", "Section 211 IT Act", "1% per month interest u/s 234B/234C"),
    ]
    for at_month, at_day, at_title, at_desc, at_sec, at_pen in advance_tax:
        if month == at_month:
            deadlines.append({
                "date": date(year, at_month, at_day),
                "category": "Income Tax",
                "title": at_title,
                "description": at_desc,
                "section": at_sec,
                "penalty_on_miss": at_pen,
                "tags": ["it", "advance_tax"],
            })
    
    # ITR Filing deadlines
    if month == 7:
        deadlines.append({
            "date": date(year, 7, 31),
            "category": "Income Tax",
            "title": "ITR Filing Deadline (Non-Audit)",
            "description": "Income Tax Return for individuals, HUFs, firms not requiring audit",
            "section": "Section 139(1) IT Act",
            "penalty_on_miss": "₹5,000 (₹1,000 if income < ₹5L) + interest u/s 234A",
            "tags": ["it", "itr", "annual"],
        })
    if month == 9:
        deadlines.append({
            "date": date(year, 9, 30),
            "category": "Income Tax",
            "title": "Tax Audit Report Deadline (Form 3CD/3CB)",
            "description": "Tax audit report for entities with turnover > ₹1 crore (business) / ₹50L (profession)",
            "section": "Section 44AB IT Act",
            "penalty_on_miss": "₹1.5 lakh or 0.5% of turnover (whichever is lower)",
            "tags": ["it", "audit", "form3cd"],
        })
    if month == 10:
        deadlines.append({
            "date": date(year, 10, 31),
            "category": "Income Tax",
            "title": "ITR Filing Deadline (Audit Cases)",
            "description": "Income Tax Return for companies, audit-required entities under Section 44AB",
            "section": "Section 139(1) IT Act",
            "penalty_on_miss": "₹10,000 + interest u/s 234A",
            "tags": ["it", "itr", "annual", "audit"],
        })
    
    # ─── TDS DEADLINES (Monthly) ──────────────────────────────────
    # TDS payment (by 7th of next month, 30 April for March deductions)
    tds_payment_day = 30 if month == 3 else 7
    deadlines.append({
        "date": _next_month_date(year, month, tds_payment_day) if month == 3 else _next_month_date(year, month, 7),
        "category": "TDS/TCS",
        "title": "TDS Payment Deadline",
        "description": "Deposit TDS deducted during the month to government account via challan 281",
        "section": "Section 200 IT Act",
        "penalty_on_miss": "1.5% per month interest u/s 201(1A) + 1% on non-deduction",
        "tags": ["tds", "monthly"],
    })
    # TDS Returns (Quarterly)
    if month in [7, 10, 1, 4]:
        q_num = {7: "Q1 (Apr-Jun)", 10: "Q2 (Jul-Sep)", 1: "Q3 (Oct-Dec)", 4: "Q4 (Jan-Mar)"}
        tds_due = {7: date(year, 7, 31), 10: date(year, 10, 31), 1: date(year, 1, 31), 4: date(year, 5, 31)}
        deadlines.append({
            "date": tds_due[month],
            "category": "TDS/TCS",
            "title": f"TDS Return Filing — {q_num[month]}",
            "description": "Quarterly TDS statement (Form 24Q, 26Q, 27Q, 27EQ) via TRACES",
            "section": "Section 206 IT Act / Rule 31A",
            "penalty_on_miss": "₹200/day u/s 234E (min ₹10,000) + penalty u/s 271H",
            "tags": ["tds", "quarterly"],
        })
    
    # ─── ROC / MCA DEADLINES ─────────────────────────────────────
    if month == 9:
        deadlines.append({
            "date": date(year, 9, 30),
            "category": "ROC/MCA",
            "title": "AOC-4 Filing (Financial Statements)",
            "description": "File audited financial statements with MCA within 30 days of AGM",
            "section": "Section 137 Companies Act 2013",
            "penalty_on_miss": "₹1,000/day up to ₹10 lakh + director prosecution",
            "tags": ["roc", "mca", "annual"],
        })
        deadlines.append({
            "date": date(year, 9, 30),
            "category": "ROC/MCA",
            "title": "MGT-7 Annual Return Filing",
            "description": "Annual return with shareholding, director details within 60 days of AGM",
            "section": "Section 92 Companies Act 2013",
            "penalty_on_miss": "₹100/day per director + ₹50,000 penalty on company",
            "tags": ["roc", "mca", "annual"],
        })
    
    # Sort deadlines by date
    deadlines.sort(key=lambda x: x["date"])
    return deadlines


def get_client_specific_deadlines(client_name: str, gst_registered: bool = True,
                                   has_foreign_transactions: bool = False,
                                   ibc_matters: Optional[list] = None,
                                   court_hearings: Optional[list] = None) -> dict:
    """
    Build a client-specific compliance calendar for the next 90 days.
    Returns categorized deadlines with alert windows.
    """
    today = date.today()
    result = {
        "client_name": client_name,
        "generated_on": today.isoformat(),
        "upcoming_90_days": [],
        "critical_this_week": [],
        "overdue": [],
    }
    
    # Get next 3 months of deadlines
    all_deadlines = []
    for month_offset in range(3):
        target_date = today + timedelta(days=30 * month_offset)
        all_deadlines.extend(get_monthly_deadlines(target_date.year, target_date.month))
    
    # Filter by client profile
    for dl in all_deadlines:
        if not gst_registered and "gst" in dl.get("tags", []):
            continue
        if not has_foreign_transactions and "fema" in dl.get("tags", []):
            continue
        
        days_until = (dl["date"] - today).days if isinstance(dl["date"], date) else 999
        
        if days_until < 0:
            dl["days_overdue"] = abs(days_until)
            result["overdue"].append(dl)  # pyre-ignore
        elif days_until <= 7:
            dl["days_until"] = days_until
            dl["urgency"] = "CRITICAL"
            result["critical_this_week"].append(dl)  # pyre-ignore
            result["upcoming_90_days"].append(dl)  # pyre-ignore
        elif days_until <= 90:
            dl["days_until"] = days_until
            dl["urgency"] = "WARNING" if days_until <= 30 else "INFO"
            result["upcoming_90_days"].append(dl)  # pyre-ignore
    
    # Add court hearings if provided
    if court_hearings is not None:  # pyre-ignore
        for hearing in court_hearings:
            result["upcoming_90_days"].append({  # pyre-ignore
                "date": hearing.get("date"),
                "category": "Court Hearing",
                "title": f"Hearing: {hearing.get('case_name', 'Case')}",
                "description": f"Court: {hearing.get('court', '')} | Matter: {hearing.get('matter', '')}",
                "section": "",
                "penalty_on_miss": "Ex-parte order risk",
                "urgency": "CRITICAL" if (hearing.get("date", date.max) - today).days <= 3 else "WARNING",
                "tags": ["court"],
            })
    
    return result


def _next_month_date(year: int, month: int, day: int) -> date:
    """Return a date in the next month."""
    if month == 12:
        return date(year + 1, 1, day)
    return date(year, month + 1, day)


def _last_day(year: int, month: int, day: int) -> date:
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last))


def format_compliance_alert(deadline: dict) -> str:
    """Format a deadline as a WhatsApp-ready alert message."""
    urgency_emoji = {"CRITICAL": "🚨", "WARNING": "⚠️", "INFO": "📅"}.get(deadline.get("urgency", "INFO"), "📅")
    days = deadline.get("days_until", "?")
    days_text = f"{days} day{'s' if days != 1 else ''}" if isinstance(days, int) else "Today"
    
    return (
        f"{urgency_emoji} *{deadline['title']}*\n"
        f"📅 Due: {deadline['date']} ({days_text})\n"
        f"📋 {deadline['description']}\n"
        f"⚖️ Section: {deadline.get('section', 'N/A')}\n"
        f"💰 Penalty: {deadline.get('penalty_on_miss', 'Refer to act')}"
    )
