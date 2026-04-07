import io
import re
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def validate_gstin(gstin: str) -> bool:
    """Basic structural validation of Indian GSTIN (15 chars, PAN embedded, state code)."""
    if not isinstance(gstin, str):
        return False
    gstin = gstin.strip().upper()
    if len(gstin) != 15:
        return False
    # Pattern: 2 digits(state code) + 10 chars(PAN) + 1 digit(entity code) + 1 char(Z) + 1 char(checksum)
    pattern = r"^[0-3][0-9][A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    return bool(re.match(pattern, gstin))

def classify_vendors(file_data: bytes) -> dict:
    """Reads a vendor ledger Excel/CSV and classifies them for Clause 44 Form 3CD."""
    try:
        # Try reading as Excel first
        try:
            df = pd.read_excel(io.BytesIO(file_data))
        except Exception:
            # Fallback to CSV
            df = pd.read_csv(io.BytesIO(file_data))
        
        # Standardize column names (lowercase, strip whitespace)
        df.columns = [str(c).lower().strip() for c in df.columns]
        
        # Identify columns
        vendor_col = next((c for c in df.columns if "name" in c or "vendor" in c or "party" in c), None)
        gstin_col = next((c for c in df.columns if "gstin" in c or "gst" in c or "registration" in c), None)
        amount_col = next((c for c in df.columns if "amount" in c or "value" in c or "expenditure" in c or "total" in c), None)
        
        if not vendor_col or not amount_col:
            raise ValueError(f"Could not reliably detect vendor name or amount columns. Found: {df.columns.tolist()}")
            
        line_items = []
        summary = {
            "vendor_count": len(df),
            "total_expenditure": 0.0,
            "registered_expenditure": 0.0,
            "unregistered_expenditure": 0.0,
        }
        
        for index, row in df.iterrows():
            vendor_name = str(row[vendor_col]) if pd.notna(row[vendor_col]) else "Unknown Vendor"
            
            # Handle amount safely
            try:
                amt_str = str(row[amount_col]).replace(",", "").strip()
                amount = float(amt_str) if pd.notna(row[amount_col]) and amt_str else 0.0
            except:
                amount = 0.0
                
            gstin = str(row[gstin_col]).strip() if gstin_col and pd.notna(row[gstin_col]) else ""
            
            status = "Unregistered"
            flags = ""
            
            if gstin and gstin.lower() not in ["none", "nan", "null", "na"]:
                if validate_gstin(gstin):
                    status = "Registered"
                else:
                    status = "Registered (Invalid Format)"
                    flags = "GSTIN fails structural validation checksum"
            
            summary["total_expenditure"] += amount
            if "Registered" in status:
                summary["registered_expenditure"] += amount
            else:
                summary["unregistered_expenditure"] += amount
                
            line_items.append({
                "vendor_name": vendor_name,
                "amount": amount,
                "gstin": gstin if "Registered" in status else "N/A",
                "status": status,
                "flags": flags
            })
            
        # Add derived metrics
        if summary["total_expenditure"] > 0:
            summary["registered_percentage"] = round((summary["registered_expenditure"] / summary["total_expenditure"]) * 100, 2)
        else:
            summary["registered_percentage"] = 0.0
            
        return {
            "summary": summary,
            "line_items": line_items
        }
        
    except Exception as e:
        logger.error(f"Error classifying vendors: {e}")
        raise
