"""
Pre-Flight Enrichment — Extract facts → auto-run deterministic tools → inject COMPUTED FACTS into LLM context.

This is what separates Spectr from wrappers. Instead of letting the LLM guess at:
- Penalty amounts
- Interest calculations
- Deadlines
- Section mappings
- Notice validity

...we extract the facts from the user's query, run actual deterministic tools, and feed
the LLM with PRE-COMPUTED answers. The LLM's job becomes: use these verified facts to
build a strategic response, NOT compute anything itself.

Architecture:
  User query → fact extraction → parallel tool execution → COMPUTED FACTS context block → LLM

Every number in the final response is traceable to a deterministic calculation.
"""
import re
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("pre_flight")


# ==================== FACT EXTRACTION ====================

# Date patterns (various Indian formats)
_DATE_PATTERNS = [
    # DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY
    (r'\b(\d{1,2})[\-/.](\d{1,2})[\-/.](\d{4})\b', "%d-%m-%Y", ["day", "month", "year"]),
    # YYYY-MM-DD (ISO)
    (r'\b(\d{4})[\-/.](\d{1,2})[\-/.](\d{1,2})\b', "%Y-%m-%d", ["year", "month", "day"]),
    # DD Month YYYY (e.g. "15 April 2024")
    (r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b', "%d %B %Y", ["day", "monthname", "year"]),
    # DD Mon YYYY (e.g. "15 Apr 2024")
    (r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})\b', "%d %b %Y", ["day", "monthname_short", "year"]),
]

# INR amount patterns
_AMOUNT_PATTERN = re.compile(
    r'(?:₹|Rs\.?|INR|rupees?)\s*([\d,]+(?:\.\d+)?)\s*(crore|cr|lakh|lac|L|thousand|K)?',
    re.IGNORECASE
)

# Notice type patterns — match GST/IT context anywhere in query
_NOTICE_PATTERNS = [
    # GST first (more specific)
    (r'\b(?:section\s+|sec\.\s*|u/s\s*|s\.\s*)?73\b', "73", ["gst", "cgst", "scn", "show cause", "itc"]),
    (r'\b(?:section\s+|sec\.\s*|u/s\s*|s\.\s*)?74\b', "74", ["gst", "cgst", "scn", "show cause", "fraud", "suppression"]),
    # IT
    (r'\b(?:section\s+|sec\.\s*|u/s\s*|s\.\s*)?148\s*A\b', "148A", []),  # No context required
    (r'\bnotice\s+under\s+(?:section\s+)?148\b(?!A)', "148", []),
    (r'\b(?:section\s+|u/s\s*|s\.\s*)148\b(?!A)', "148", ["reassessment", "escape", "reopen"]),
    (r'\b(?:section\s+|sec\.\s*|u/s\s*)?143\s*\(\s*2\s*\)\b', "143(2)", []),
    (r'\b(?:section\s+|sec\.\s*|u/s\s*)?142\s*\(\s*1\s*\)\b', "142(1)", []),
    (r'\bscrutiny\s+notice\b', "143(2)", []),
]

# Payment descriptions for TDS
_TDS_PAYMENT_PATTERNS = {
    r'\b(?:professional|consultancy|CA|chartered\s+accountant|advocate|doctor|engineer|architect)\s+fees?\b': "professional fees",
    r'\b(?:contract|contractor|labour\s+contract)\s+payment\b': "contractor payment",
    r'\b(?:rent|rental)\b.*(?:office|building|premises|land)\b': "rent for building",
    r'\bcommission\b': "commission",
    r'\bbrokerage\b': "brokerage",
    r'\bsalary\b': "salary",
    r'\binterest\s+on\b': "interest payment",
    r'\broyalt(?:y|ies)\b': "royalty",
    r'\btechnical\s+fees?\b': "technical fees",
}


def extract_dates(query: str) -> list[dict]:
    """Extract all dates mentioned in the query."""
    dates = []
    for pattern, fmt, keys in _DATE_PATTERNS:
        for m in re.finditer(pattern, query, re.IGNORECASE):
            try:
                if "monthname" in keys or "monthname_short" in keys:
                    dt = datetime.strptime(m.group(0), fmt)
                else:
                    dt = datetime.strptime(m.group(0).replace(".", "-").replace("/", "-"), fmt.replace(".", "-").replace("/", "-"))
                dates.append({
                    "raw": m.group(0),
                    "iso": dt.strftime("%Y-%m-%d"),
                    "position": m.start(),
                })
            except (ValueError, TypeError):
                continue
    return sorted(dates, key=lambda x: x["position"])


def extract_amounts(query: str) -> list[dict]:
    """Extract all INR amounts mentioned."""
    amounts = []
    for m in _AMOUNT_PATTERN.finditer(query):
        try:
            val = float(m.group(1).replace(",", ""))
            unit = (m.group(2) or "").lower()
            if unit in ("crore", "cr"):
                absolute = val * 10_000_000
            elif unit in ("lakh", "lac", "l"):
                absolute = val * 100_000
            elif unit in ("thousand", "k"):
                absolute = val * 1_000
            else:
                absolute = val
            amounts.append({
                "raw": m.group(0),
                "absolute": absolute,
                "value": val,
                "unit": unit,
                "position": m.start(),
            })
        except ValueError:
            continue
    return amounts


def extract_sections(query: str) -> list[dict]:
    """Extract section references with context."""
    pattern = re.compile(
        r'(?:Section|Sec\.|u/s|under\s+Section)\s*(\d+[A-Za-z]*(?:\([a-z0-9]+\))*)'
        r'(?:\s+of(?:\s+the)?\s+([A-Za-z,&\-\s]+?(?:Act|Code|Rules)(?:,?\s*\d{4})?))?',
        re.IGNORECASE
    )
    sections = []
    for m in pattern.finditer(query):
        sections.append({
            "section": m.group(1).strip(),
            "act": (m.group(2) or "").strip(),
            "raw": m.group(0),
            "position": m.start(),
        })
    return sections


def extract_notice_type(query: str) -> Optional[str]:
    """Detect if query is about a specific tax notice.

    Returns notice type if pattern matches AND required context keywords appear anywhere in query.
    """
    q_lower = query.lower()
    for pattern, notice_type, required_context in _NOTICE_PATTERNS:
        if re.search(pattern, q_lower, re.IGNORECASE):
            # If no context required, return immediately
            if not required_context:
                return notice_type
            # Otherwise, at least one context keyword must appear anywhere
            if any(ctx in q_lower for ctx in required_context):
                return notice_type
    return None


def extract_payment_description(query: str) -> Optional[str]:
    """Detect if query is about TDS on a specific payment type."""
    q_lower = query.lower()
    for pattern, payment_type in _TDS_PAYMENT_PATTERNS.items():
        if re.search(pattern, q_lower, re.IGNORECASE):
            return payment_type
    return None


def extract_financial_year(query: str) -> Optional[str]:
    """Extract FY/AY references."""
    # FY 2022-23, FY 22-23, FY2022-23
    m = re.search(r'\bFY\s*(\d{2,4})\s*[\-/]\s*(\d{2,4})\b', query, re.IGNORECASE)
    if m:
        y1 = m.group(1)
        y2 = m.group(2)
        if len(y1) == 2:
            y1 = "20" + y1
        if len(y2) == 2:
            y2 = "20" + y2
        return f"{y1}-{y2[-2:]}"
    # AY 2023-24 → FY 2022-23 (subtract 1 from both)
    m = re.search(r'\bAY\s*(\d{2,4})\s*[\-/]\s*(\d{2,4})\b', query, re.IGNORECASE)
    if m:
        y1, y2 = m.group(1), m.group(2)
        if len(y1) == 2:
            y1 = "20" + y1
        if len(y2) == 2:
            y2 = "20" + y2
        # AY corresponds to FY - 1 (both start and end years)
        fy_start = int(y1) - 1
        fy_end = int(y2) - 1
        return f"{fy_start}-{str(fy_end)[-2:]}"
    return None


# ==================== AUTO-RUN DETERMINISTIC TOOLS ====================

async def run_tds_classifier(description: str, amount: float) -> dict:
    """Run the real TDS classifier from practice_tools."""
    try:
        from practice_tools import classify_tds_section
        result = classify_tds_section(
            payment_description=description,
            amount=amount,
            payee_type="individual",
            is_non_filer=False,
        )
        return result
    except Exception as e:
        logger.warning(f"TDS classifier failed: {e}")
        return {}


async def run_penalty_calc(deadline_type: str, due_date: str, actual_date: str, tax_amount: float) -> dict:
    """Run the real penalty/interest calculator."""
    try:
        from practice_tools import calculate_deadline_penalty
        result = calculate_deadline_penalty(
            deadline_type=deadline_type,
            due_date=due_date,
            actual_date=actual_date,
            tax_amount=tax_amount,
        )
        return result
    except Exception as e:
        logger.warning(f"Penalty calc failed: {e}")
        return {}


async def run_notice_validity(notice_type: str, notice_date: str, fy: Optional[str] = None) -> dict:
    """Run notice validity check."""
    try:
        from practice_tools import check_notice_validity
        result = check_notice_validity(
            notice_type=notice_type,
            notice_date=notice_date,
            financial_year=fy or "",
            has_din=True,
            is_fraud_alleged=False,
        )
        return result
    except Exception as e:
        logger.warning(f"Notice validity check failed: {e}")
        return {}


async def run_section_mapping(section: str) -> dict:
    """Run BNS↔IPC section mapping."""
    try:
        from practice_tools import map_section
        # Try both directions
        old_to_new = map_section(section, direction="old_to_new")
        if old_to_new.get("found"):
            return {"direction": "old_to_new", "result": old_to_new}
        new_to_old = map_section(section, direction="new_to_old")
        if new_to_old.get("found"):
            return {"direction": "new_to_old", "result": new_to_old}
        return {}
    except Exception as e:
        logger.warning(f"Section mapping failed: {e}")
        return {}


# ==================== DEADLINE COMPUTATION ====================

def _add_years(dt: datetime, years: int) -> datetime:
    """Add N years accurately (handles leap years and Feb 29)."""
    try:
        return dt.replace(year=dt.year + years)
    except ValueError:
        # Feb 29 → Feb 28 on non-leap target year
        return dt.replace(year=dt.year + years, day=28)


def compute_limitation_deadline(notice_type: str, notice_date: str, fy: Optional[str] = None) -> dict:
    """Compute EXACT deadline for various tax notice scenarios.

    No LLM math. Pure arithmetic from Indian tax limitation rules.
    """
    try:
        notice = datetime.strptime(notice_date, "%Y-%m-%d")
    except ValueError:
        return {}

    result = {"notice_type": notice_type, "notice_date": notice_date}

    if notice_type == "73":
        # GST S.73: order within 3 years from due date of annual return
        # Annual return due: 31 Dec of year following FY
        if fy:
            fy_end_year = int(fy.split("-")[0]) + 1
            annual_return_due = datetime(fy_end_year, 12, 31)
            order_deadline = _add_years(annual_return_due, 3)
            scn_deadline = order_deadline - timedelta(days=90)  # SCN at least 3 months before order
            result["annual_return_due"] = annual_return_due.strftime("%Y-%m-%d")
            result["order_deadline"] = order_deadline.strftime("%Y-%m-%d")
            result["scn_deadline"] = scn_deadline.strftime("%Y-%m-%d")
            result["is_barred"] = notice > scn_deadline
            result["reply_deadline"] = (notice + timedelta(days=30)).strftime("%Y-%m-%d")
            result["controlling_provision"] = "Section 73(10) CGST Act — order within 3 years from annual return due date"

    elif notice_type == "74":
        # GST S.74: order within 5 years
        if fy:
            fy_end_year = int(fy.split("-")[0]) + 1
            annual_return_due = datetime(fy_end_year, 12, 31)
            order_deadline = _add_years(annual_return_due, 5)
            scn_deadline = order_deadline - timedelta(days=180)  # SCN at least 6 months before order
            result["annual_return_due"] = annual_return_due.strftime("%Y-%m-%d")
            result["order_deadline"] = order_deadline.strftime("%Y-%m-%d")
            result["scn_deadline"] = scn_deadline.strftime("%Y-%m-%d")
            result["is_barred"] = notice > scn_deadline
            result["reply_deadline"] = (notice + timedelta(days=30)).strftime("%Y-%m-%d")
            result["controlling_provision"] = "Section 74(10) CGST Act — order within 5 years from annual return due date"

    elif notice_type == "148A":
        # IT S.148A(b): reply within 7 days from notice
        reply = notice + timedelta(days=7)
        result["reply_deadline"] = reply.strftime("%Y-%m-%d")
        result["controlling_provision"] = "Section 148A(b) Income-tax Act — minimum 7 days for reply"

    elif notice_type == "148":
        # IT S.148: reply/file ITR within 30 days (extended by notice typically 30)
        reply = notice + timedelta(days=30)
        result["reply_deadline"] = reply.strftime("%Y-%m-%d")
        result["controlling_provision"] = "Section 148 Income-tax Act — file return in response"

    elif notice_type == "143(2)":
        # Scrutiny notice — order within 12 months from end of FY in which notice served (post FY 2021)
        fy_of_notice_end = datetime(notice.year if notice.month >= 4 else notice.year, 3, 31) if notice.month < 4 else datetime(notice.year + 1, 3, 31)
        order_deadline = fy_of_notice_end + timedelta(days=365)
        result["order_deadline"] = order_deadline.strftime("%Y-%m-%d")
        result["reply_deadline"] = (notice + timedelta(days=15)).strftime("%Y-%m-%d")
        result["controlling_provision"] = "Section 143(3) read with S.153 Income-tax Act"

    elif notice_type == "142(1)":
        # General inquiry — reply as specified in notice, typically 15 days
        reply = notice + timedelta(days=15)
        result["reply_deadline"] = reply.strftime("%Y-%m-%d")
        result["controlling_provision"] = "Section 142(1) Income-tax Act"

    # Universal appeal deadlines (if relevant)
    result["cit_a_appeal_deadline"] = (notice + timedelta(days=30)).strftime("%Y-%m-%d") + " (if adverse order is received today)"
    result["itat_appeal_deadline"] = (notice + timedelta(days=60)).strftime("%Y-%m-%d") + " (from date of CIT(A) order)"

    return result


# ==================== ORCHESTRATOR ====================

async def run_pre_flight(user_query: str) -> dict:
    """Main orchestrator: extract facts, run tools in parallel, return COMPUTED FACTS.

    Returns dict with:
      - extracted: raw extracted facts
      - computed: deterministic tool outputs
      - context_block: formatted string to inject into LLM context
    """
    extracted = {
        "dates": extract_dates(user_query),
        "amounts": extract_amounts(user_query),
        "sections": extract_sections(user_query),
        "notice_type": extract_notice_type(user_query),
        "payment_description": extract_payment_description(user_query),
        "fy": extract_financial_year(user_query),
    }

    # Build list of parallel tool invocations
    tool_tasks = []
    tool_names = []

    # TDS classifier if payment mentioned
    if extracted["payment_description"]:
        amount = extracted["amounts"][0]["absolute"] if extracted["amounts"] else 100000
        tool_tasks.append(run_tds_classifier(extracted["payment_description"], amount))
        tool_names.append("tds_classifier")

    # Notice validity + deadline if notice mentioned
    if extracted["notice_type"] and extracted["dates"]:
        notice_date = extracted["dates"][0]["iso"]
        tool_tasks.append(run_notice_validity(extracted["notice_type"], notice_date, extracted["fy"]))
        tool_names.append("notice_validity")
        # Synchronous — add computed deadline directly
        deadline_data = compute_limitation_deadline(extracted["notice_type"], notice_date, extracted["fy"])

    # Section mapping if IPC/BNS section mentioned
    mapped_sections = []
    for sec_info in extracted["sections"]:
        sec_num = sec_info["section"]
        # Quick heuristic: if act mentions BNS/IPC/CrPC/BNSS, run mapper
        act_lower = sec_info["act"].lower()
        if any(kw in act_lower for kw in ["bns", "ipc", "crpc", "bnss", "penal", "criminal"]):
            tool_tasks.append(run_section_mapping(sec_num))
            tool_names.append(f"section_mapping_{sec_num}")

    # Execute all tools in parallel
    computed = {}
    if tool_tasks:
        results = await asyncio.gather(*tool_tasks, return_exceptions=True)
        for name, result in zip(tool_names, results):
            if isinstance(result, Exception):
                continue
            if result:
                computed[name] = result

    # Add synchronous deadline computation if applicable
    if extracted["notice_type"] and extracted["dates"]:
        deadline_data = compute_limitation_deadline(
            extracted["notice_type"], extracted["dates"][0]["iso"], extracted["fy"]
        )
        if deadline_data:
            computed["limitation_deadline"] = deadline_data

    # Build context block
    context_parts = []
    if computed:
        context_parts.append("=== COMPUTED FACTS (Deterministic — Use These Exact Numbers) ===")
        context_parts.append("The following values have been computed by verified deterministic tools.")
        context_parts.append("DO NOT recompute. Cite these as authoritative.")
        context_parts.append("")

        if "tds_classifier" in computed:
            tds = computed["tds_classifier"]
            context_parts.append(f"**TDS Classification:**")
            context_parts.append(f"- Section: {tds.get('section', 'N/A')}")
            context_parts.append(f"- Rate: {tds.get('rate_percent', tds.get('rate', 'N/A'))}%")
            context_parts.append(f"- Threshold: ₹{tds.get('threshold', 0):,}")
            if tds.get('tds_amount'):
                context_parts.append(f"- TDS Amount to deduct: ₹{tds['tds_amount']:,}")
            if tds.get('note'):
                context_parts.append(f"- Note: {tds['note']}")
            context_parts.append("")

        if "notice_validity" in computed:
            nv = computed["notice_validity"]
            context_parts.append(f"**Notice Validity Check:**")
            if nv.get("overall_validity"):
                context_parts.append(f"- Status: {nv['overall_validity']}")
            if nv.get("limitation_check"):
                context_parts.append(f"- Limitation: {nv['limitation_check']}")
            if nv.get("challenge_grounds"):
                context_parts.append(f"- Challenge grounds found: {len(nv['challenge_grounds'])}")
                for g in nv["challenge_grounds"][:3]:
                    context_parts.append(f"  • {g.get('ground', '')} [{g.get('severity', '')}]: {g.get('legal_basis', '')}")
            context_parts.append("")

        if "limitation_deadline" in computed:
            ld = computed["limitation_deadline"]
            context_parts.append(f"**Deadline Computation (for S.{ld.get('notice_type', '')} notice):**")
            if ld.get("reply_deadline"):
                context_parts.append(f"- Reply deadline: **{ld['reply_deadline']}**")
            if ld.get("order_deadline"):
                context_parts.append(f"- Order must issue by: **{ld['order_deadline']}**")
            if ld.get("scn_deadline"):
                context_parts.append(f"- SCN must issue by: **{ld['scn_deadline']}**")
            if ld.get("is_barred"):
                context_parts.append(f"- ⚠ **LIMITATION BARRED** — this notice is time-barred")
            if ld.get("controlling_provision"):
                context_parts.append(f"- Controlling provision: {ld['controlling_provision']}")
            context_parts.append("")

        # Section mappings
        for name, result in computed.items():
            if name.startswith("section_mapping_") and result.get("result"):
                r = result["result"]
                context_parts.append(f"**Section Mapping ({r.get('old_section', '')} ↔ {r.get('new_section', '')}):**")
                context_parts.append(f"- {r.get('title', '')}")
                if r.get('effective_from'):
                    context_parts.append(f"- Effective: {r['effective_from']}")
                if r.get('note'):
                    context_parts.append(f"- Note: {r['note']}")
                context_parts.append("")

        context_parts.append("**INSTRUCTION TO LLM:** Use ONLY the above computed values in your response.")
        context_parts.append("Do NOT invent penalty amounts, interest, or deadlines. These are authoritative.")

    # Extracted facts summary (even if no tools ran)
    if extracted["amounts"] or extracted["dates"]:
        context_parts.append("")
        context_parts.append("=== EXTRACTED FROM QUERY ===")
        if extracted["amounts"]:
            context_parts.append(f"Amounts detected: {', '.join(a['raw'] for a in extracted['amounts'])}")
        if extracted["dates"]:
            context_parts.append(f"Dates detected: {', '.join(d['raw'] + ' (→ ' + d['iso'] + ')' for d in extracted['dates'])}")
        if extracted["fy"]:
            context_parts.append(f"Financial Year: FY {extracted['fy']}")

    return {
        "extracted": extracted,
        "computed": computed,
        "context_block": "\n".join(context_parts),
        "has_computed_facts": bool(computed),
    }
