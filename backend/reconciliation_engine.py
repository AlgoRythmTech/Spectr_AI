"""
GSTR-2B Reconciliation Engine — REAL multi-pass matching.
No mocked data. Actual column-by-column reconciliation.
Handles messy Indian invoice numbers, GSTIN variations, and rounding differences.
"""
import pandas as pd
import io
import re
import logging
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

# Common column name variations in Indian accounting exports
GSTIN_COLS = ["gstin", "gstin of supplier", "supplier gstin", "gstin/uin", "gstin_supplier", "vendor gstin", "party gstin"]
INVOICE_COLS = ["invoice number", "invoice no", "inv no", "inv number", "invoice_number", "document number", "doc no", "bill no", "bill number"]
INVOICE_DATE_COLS = ["invoice date", "inv date", "invoice_date", "document date", "bill date"]
TAXABLE_COLS = ["taxable value", "taxable amount", "taxable_value", "assessable value", "base amount"]
IGST_COLS = ["igst", "igst amount", "integrated tax"]
CGST_COLS = ["cgst", "cgst amount", "central tax"]
SGST_COLS = ["sgst", "sgst amount", "state tax", "utgst"]
TAX_COLS = ["tax amount", "total tax", "gst amount", "total gst", "tax_amount"]
TOTAL_COLS = ["invoice value", "total value", "total amount", "invoice amount", "total_value", "gross amount"]
VENDOR_COLS = ["vendor name", "supplier name", "party name", "trade name", "vendor", "supplier"]


def _find_col(df_columns: list, candidates: list) -> str:
    """Find matching column name from candidates (case-insensitive)."""
    cols_lower = {c.lower().strip(): c for c in df_columns}
    for candidate in candidates:
        if candidate.lower() in cols_lower:
            return cols_lower[candidate.lower()]
    return ""


def _normalize_invoice(inv: str) -> str:
    """Normalize Indian invoice numbers for fuzzy matching.
    Removes leading zeros, slashes, hyphens, spaces. Lowercases.
    'INV/001/24-25' and 'INV-1-2425' and 'inv 001 24-25' should all match.
    """
    if not inv or pd.isna(inv):
        return ""
    s = str(inv).strip().lower()
    s = re.sub(r'[/\-\s_.]', '', s)  # Remove separators
    s = re.sub(r'^0+', '', s)  # Remove leading zeros
    # Remove common prefixes that vendors add inconsistently
    for prefix in ['inv', 'bill', 'tax', 'gst']:
        if s.startswith(prefix):
            s = s[len(prefix):]
            s = s.lstrip('0')
    return s


def _normalize_gstin(gstin: str) -> str:
    """Normalize GSTIN: uppercase, strip spaces, validate 15-char format."""
    if not gstin or pd.isna(gstin):
        return ""
    s = str(gstin).strip().upper().replace(" ", "")
    if len(s) == 15 and s[:2].isdigit():
        return s
    return s  # Return as-is even if malformed (will be flagged)


def _safe_float(val) -> float:
    """Safely convert to float, handling Indian number formats."""
    if pd.isna(val) or val is None or val == "":
        return 0.0
    s = str(val).strip().replace(",", "").replace("₹", "").replace("Rs", "").replace("Rs.", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


def reconcile_gstr2b(purchase_bytes: bytes, gstr2b_bytes: bytes) -> dict:
    """
    Real multi-pass GSTR-2B reconciliation.
    Pass 1: Exact match (GSTIN + Invoice Number)
    Pass 2: Fuzzy match (normalized invoice numbers within same GSTIN)
    Pass 3: Amount-based match (GSTIN + tax amount within Rs 1 tolerance)

    Returns: exact matches, fuzzy matches, unmatched (ITC at risk), vendor risk report.
    """
    try:
        # Auto-detect file format
        try:
            df_pr = pd.read_excel(io.BytesIO(purchase_bytes))
        except Exception:
            df_pr = pd.read_csv(io.BytesIO(purchase_bytes))

        try:
            df_g2b = pd.read_excel(io.BytesIO(gstr2b_bytes))
        except Exception:
            df_g2b = pd.read_csv(io.BytesIO(gstr2b_bytes))

        if df_pr.empty or df_g2b.empty:
            return {"error": "One or both files are empty."}

        # Standardize column names
        df_pr.columns = [str(c).strip() for c in df_pr.columns]
        df_g2b.columns = [str(c).strip() for c in df_g2b.columns]

        # Identify columns
        pr_gstin = _find_col(df_pr.columns, GSTIN_COLS)
        pr_invoice = _find_col(df_pr.columns, INVOICE_COLS)
        pr_taxable = _find_col(df_pr.columns, TAXABLE_COLS)
        pr_igst = _find_col(df_pr.columns, IGST_COLS)
        pr_cgst = _find_col(df_pr.columns, CGST_COLS)
        pr_sgst = _find_col(df_pr.columns, SGST_COLS)
        pr_tax = _find_col(df_pr.columns, TAX_COLS)
        pr_total = _find_col(df_pr.columns, TOTAL_COLS)
        pr_vendor = _find_col(df_pr.columns, VENDOR_COLS)

        g2b_gstin = _find_col(df_g2b.columns, GSTIN_COLS)
        g2b_invoice = _find_col(df_g2b.columns, INVOICE_COLS)
        g2b_taxable = _find_col(df_g2b.columns, TAXABLE_COLS)
        g2b_igst = _find_col(df_g2b.columns, IGST_COLS)
        g2b_cgst = _find_col(df_g2b.columns, CGST_COLS)
        g2b_sgst = _find_col(df_g2b.columns, SGST_COLS)
        g2b_tax = _find_col(df_g2b.columns, TAX_COLS)
        g2b_total = _find_col(df_g2b.columns, TOTAL_COLS)

        if not pr_gstin or not pr_invoice:
            return {"error": f"Books GST Ledger missing GSTIN or Invoice column. Found columns: {list(df_pr.columns)}"}
        if not g2b_gstin or not g2b_invoice:
            return {"error": f"GSTR-2B missing GSTIN or Invoice column. Found columns: {list(df_g2b.columns)}"}

        # Compute tax amount for each row if individual tax columns exist
        def compute_tax(row, igst_col, cgst_col, sgst_col, tax_col):
            if tax_col:
                return _safe_float(row.get(tax_col, 0))
            total = 0
            if igst_col: total += _safe_float(row.get(igst_col, 0))
            if cgst_col: total += _safe_float(row.get(cgst_col, 0))
            if sgst_col: total += _safe_float(row.get(sgst_col, 0))
            return total

        # Build normalized lookup for GSTR-2B
        g2b_records = []
        for idx, row in df_g2b.iterrows():
            gstin = _normalize_gstin(row.get(g2b_gstin, ""))
            invoice_raw = str(row.get(g2b_invoice, "")).strip()
            invoice_norm = _normalize_invoice(invoice_raw)
            tax = compute_tax(row, g2b_igst, g2b_cgst, g2b_sgst, g2b_tax)
            taxable = _safe_float(row.get(g2b_taxable, 0)) if g2b_taxable else 0
            total = _safe_float(row.get(g2b_total, 0)) if g2b_total else taxable + tax

            g2b_records.append({
                "idx": idx,
                "gstin": gstin,
                "invoice_raw": invoice_raw,
                "invoice_norm": invoice_norm,
                "tax": round(tax, 2),
                "taxable": round(taxable, 2),
                "total": round(total, 2),
                "matched": False,
            })

        # Build GSTIN-indexed lookup for speed
        g2b_by_gstin = {}
        for rec in g2b_records:
            g2b_by_gstin.setdefault(rec["gstin"], []).append(rec)

        exact_matches = []
        fuzzy_matches = []
        unmatched_pr = []  # In PR but not in GSTR-2B (ITC AT RISK)
        amount_mismatches = []

        # === PASS 1: EXACT MATCH (GSTIN + Normalized Invoice) ===
        for idx, row in df_pr.iterrows():
            gstin = _normalize_gstin(row.get(pr_gstin, ""))
            invoice_raw = str(row.get(pr_invoice, "")).strip()
            invoice_norm = _normalize_invoice(invoice_raw)
            pr_tax_amt = compute_tax(row, pr_igst, pr_cgst, pr_sgst, pr_tax)
            pr_taxable_amt = _safe_float(row.get(pr_taxable, 0)) if pr_taxable else 0
            vendor_name = str(row.get(pr_vendor, "")) if pr_vendor else ""

            pr_record = {
                "row": idx + 2,  # Excel row (1-indexed + header)
                "gstin": gstin,
                "invoice_raw": invoice_raw,
                "invoice_norm": invoice_norm,
                "tax": round(pr_tax_amt, 2),
                "taxable": round(pr_taxable_amt, 2),
                "vendor": vendor_name,
            }

            matched = False
            candidates = g2b_by_gstin.get(gstin, [])

            # Pass 1: Exact normalized match
            for g2b in candidates:
                if not g2b["matched"] and g2b["invoice_norm"] == invoice_norm and invoice_norm:
                    g2b["matched"] = True
                    tax_diff = abs(pr_tax_amt - g2b["tax"])

                    match_record = {
                        "pr_row": pr_record["row"],
                        "gstin": gstin,
                        "pr_invoice": invoice_raw,
                        "g2b_invoice": g2b["invoice_raw"],
                        "pr_tax": pr_record["tax"],
                        "g2b_tax": g2b["tax"],
                        "tax_difference": round(tax_diff, 2),
                    }

                    if tax_diff > 1:  # More than Rs 1 difference
                        match_record["flag"] = "AMOUNT MISMATCH"
                        amount_mismatches.append(match_record)
                    else:
                        exact_matches.append(match_record)

                    matched = True
                    break

            if not matched:
                pr_record["_candidates"] = candidates  # For pass 2
                unmatched_pr.append(pr_record)

        # === PASS 2: FUZZY MATCH (same GSTIN, similar invoice number) ===
        still_unmatched = []
        for pr_rec in unmatched_pr:
            candidates = [g for g in pr_rec.get("_candidates", []) if not g["matched"]]
            best_match = None
            best_score = 0

            for g2b in candidates:
                if not g2b["invoice_norm"] or not pr_rec["invoice_norm"]:
                    continue
                score = fuzz.ratio(pr_rec["invoice_norm"], g2b["invoice_norm"])
                if score > best_score and score >= 75:  # 75% similarity threshold
                    best_score = score
                    best_match = g2b

            if best_match:
                best_match["matched"] = True
                tax_diff = abs(pr_rec["tax"] - best_match["tax"])
                fuzzy_matches.append({
                    "pr_row": pr_rec["row"],
                    "gstin": pr_rec["gstin"],
                    "pr_invoice": pr_rec["invoice_raw"],
                    "g2b_invoice": best_match["invoice_raw"],
                    "similarity_score": best_score,
                    "pr_tax": pr_rec["tax"],
                    "g2b_tax": best_match["tax"],
                    "tax_difference": round(tax_diff, 2),
                    "action": "VERIFY — invoice numbers differ but likely same transaction" + (
                        f". Tax mismatch of Rs {tax_diff:.2f}" if tax_diff > 1 else ""
                    ),
                })
            else:
                del pr_rec["_candidates"]  # Clean up
                still_unmatched.append(pr_rec)

        # === PASS 3: AMOUNT-BASED MATCH (same GSTIN, same tax amount within Rs 1) ===
        final_unmatched = []
        for pr_rec in still_unmatched:
            candidates = g2b_by_gstin.get(pr_rec["gstin"], [])
            amount_match = None

            for g2b in candidates:
                if not g2b["matched"] and abs(pr_rec["tax"] - g2b["tax"]) <= 1 and pr_rec["tax"] > 0:
                    amount_match = g2b
                    break

            if amount_match:
                amount_match["matched"] = True
                fuzzy_matches.append({
                    "pr_row": pr_rec["row"],
                    "gstin": pr_rec["gstin"],
                    "pr_invoice": pr_rec["invoice_raw"],
                    "g2b_invoice": amount_match["invoice_raw"],
                    "match_type": "amount_based",
                    "similarity_score": 0,
                    "pr_tax": pr_rec["tax"],
                    "g2b_tax": amount_match["tax"],
                    "tax_difference": round(abs(pr_rec["tax"] - amount_match["tax"]), 2),
                    "action": "VERIFY — matched by GSTIN + tax amount only. Invoice numbers do not match.",
                })
            else:
                final_unmatched.append(pr_rec)

        # Unmatched GSTR-2B records (in GSTR-2B but NOT in Books GST Ledgers — potential unclaimed ITC)
        unmatched_g2b = [g for g in g2b_records if not g["matched"]]

        # Calculate ITC at risk
        itc_at_risk = sum(r["tax"] for r in final_unmatched)
        itc_unclaimed = sum(r["tax"] for r in unmatched_g2b)
        itc_mismatched = sum(r["tax_difference"] for r in amount_mismatches)

        # Generate vendor risk report
        vendor_risk = _generate_vendor_risk(final_unmatched)

        total_pr = len(df_pr)
        return {
            "total_pr_invoices": total_pr,
            "total_g2b_invoices": len(df_g2b),
            "exact_matches": len(exact_matches),
            "fuzzy_matches": len(fuzzy_matches),
            "amount_mismatches": len(amount_mismatches),
            "unmatched_in_pr": len(final_unmatched),
            "unmatched_in_g2b": len(unmatched_g2b),
            "match_rate_percent": round((len(exact_matches) + len(fuzzy_matches)) / max(total_pr, 1) * 100, 1),
            "itc_at_risk": round(itc_at_risk, 2),
            "itc_unclaimed": round(itc_unclaimed, 2),
            "itc_amount_mismatch": round(itc_mismatched, 2),
            "details": {
                "exact_matches": exact_matches[:100],
                "fuzzy_matches": fuzzy_matches[:50],
                "amount_mismatches": amount_mismatches[:50],
                "unmatched_pr": [
                    {k: v for k, v in r.items() if k != "_candidates"}
                    for r in final_unmatched[:50]
                ],
                "unmatched_g2b": [
                    {"gstin": r["gstin"], "invoice": r["invoice_raw"], "tax": r["tax"]}
                    for r in unmatched_g2b[:50]
                ],
            },
            "vendor_risk": vendor_risk,
            "summary": (
                f"Reconciled {total_pr} purchase invoices against {len(df_g2b)} GSTR-2B records. "
                f"Exact matches: {len(exact_matches)}, Fuzzy matches: {len(fuzzy_matches)}, "
                f"Amount mismatches: {len(amount_mismatches)}. "
                f"ITC at risk (not in GSTR-2B): Rs {itc_at_risk:,.2f}. "
                f"Unclaimed ITC (in GSTR-2B but not in books): Rs {itc_unclaimed:,.2f}."
            ),
            "columns_detected": {
                "purchase_register": {"gstin": pr_gstin, "invoice": pr_invoice, "tax": pr_tax or "computed", "vendor": pr_vendor},
                "gstr2b": {"gstin": g2b_gstin, "invoice": g2b_invoice, "tax": g2b_tax or "computed"},
            },
        }

    except Exception as e:
        logger.error(f"Reconciliation failed: {e}", exc_info=True)
        raise ValueError(f"Reconciliation Engine Error: {str(e)}")


def _generate_vendor_risk(unmatched_records: list) -> dict:
    """Generate vendor-wise ITC risk matrix from unmatched records."""
    vendor_risk = {}

    for rec in unmatched_records:
        gstin = rec.get("gstin", "UNKNOWN")
        vendor = rec.get("vendor", gstin)
        key = gstin if gstin else vendor

        if key not in vendor_risk:
            vendor_risk[key] = {
                "vendor_name": vendor,
                "gstin": gstin,
                "total_itc_at_risk": 0,
                "invoice_count": 0,
                "invoices": [],
                "risk_level": "LOW",
                "legal_position": "",
                "action": "",
            }

        vendor_risk[key]["total_itc_at_risk"] += rec.get("tax", 0)
        vendor_risk[key]["invoice_count"] += 1
        vendor_risk[key]["invoices"].append(rec.get("invoice_raw", ""))

    for key, v in vendor_risk.items():
        total = v["total_itc_at_risk"]
        if total > 500000:
            v["risk_level"] = "HIGH"
            v["legal_position"] = (
                "Section 16(2)(c) CGST Act: ITC available only if supplier has paid tax. "
                "Reverse ITC in next GSTR-3B to avoid 18% interest under Section 50(1). "
                "Obtain vendor indemnity. Challenge constitutionality per Suncraft Energy (2023 Cal HC)."
            )
            v["action"] = "URGENT: Reverse ITC or obtain indemnity. File DRC-01A response if demand received."
        elif total > 100000:
            v["risk_level"] = "MEDIUM"
            v["legal_position"] = (
                "Circular 183/15/2022-GST provides relief for bona fide buyers. "
                "Document vendor communication and payment proof."
            )
            v["action"] = "Chase vendor for GSTR-1 filing within 15 days. Preserve transaction evidence."
        else:
            v["risk_level"] = "LOW"
            v["legal_position"] = "Low exposure. Monitor GSTR-2B monthly."
            v["action"] = "Auto-monitor."

    risk_list = list(vendor_risk.values())
    high_risk = [v for v in risk_list if v["risk_level"] == "HIGH"]
    total_at_risk = sum(v["total_itc_at_risk"] for v in risk_list)

    return {
        "vendor_risk_matrix": risk_list,
        "total_itc_at_risk": round(total_at_risk, 2),
        "high_risk_count": len(high_risk),
        "high_risk_vendors": high_risk,
        "summary": (
            f"Total ITC at risk: Rs {total_at_risk:,.0f} across {len(risk_list)} vendors. "
            f"{len(high_risk)} HIGH risk (>Rs 5L each). "
            f"Immediate reversal recommended for HIGH risk vendors."
        ),
    }
