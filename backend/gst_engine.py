"""
GST Return Computation Engine — Production-grade for Indian Chartered Accountants.

Handles:
  - GSTR-1 auto-generation from invoice register (Excel/JSON)
  - GSTR-3B computation with ITC set-off
  - ITC tracker with Section 17(5) blocking, Rule 36(4), Rule 42/43 reversals
  - GSTIN structural validation with Luhn checksum
  - HSN/SAC code validation with rate lookup
  - Place of supply determination (Sections 10, 12, 13 IGST Act)

All monetary values in Indian Rupees. Uses Decimal for financial precision.
"""

import io
import re
import json
import logging
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime, date, timedelta
from typing import Optional, Any
from enum import Enum

import pandas as pd

logger = logging.getLogger("spectr.gst_engine")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0")

VALID_GST_RATES = {
    Decimal("0"), Decimal("0.25"), Decimal("3"), Decimal("5"),
    Decimal("12"), Decimal("18"), Decimal("28"),
}

# Cess rates for selected HSN codes (luxury/sin goods)
CESS_RATES: dict[str, Decimal] = {
    "2402": Decimal("5"),    # Cigarettes (base cess; actual varies by length)
    "8703": Decimal("15"),   # Motor vehicles (mid/large segment)
    "2202": Decimal("12"),   # Aerated beverages
    "2106": Decimal("12"),   # Pan masala
}


class InvoiceType(str, Enum):
    B2B = "B2B"
    B2CL = "B2CL"       # B2C Large (interstate > Rs 2.5 lakh)
    B2CS = "B2CS"        # B2C Small
    EXPORT = "EXPORT"
    SEZ = "SEZ"
    CDN = "CDN"          # Credit / Debit Note
    NIL = "NIL"          # Nil-rated / Exempt
    ADVANCES = "ADV"     # Advance received


# =====================================================================
# 1. GSTIN VALIDATOR — Full structural + checksum validation
# =====================================================================

# State codes as per GST notification (01 to 37, 97 for Other Territory)
STATE_CODE_MAP: dict[str, str] = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana",
    "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
    "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
    "16": "Tripura", "17": "Meghalaya", "18": "Assam",
    "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
    "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "25": "Daman & Diu", "26": "Dadra & Nagar Haveli",
    "27": "Maharashtra", "28": "Andhra Pradesh (Old)",
    "29": "Karnataka", "30": "Goa", "31": "Lakshadweep",
    "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
    "35": "Andaman & Nicobar Islands", "36": "Telangana",
    "37": "Andhra Pradesh", "38": "Ladakh",
    "97": "Other Territory",
}

# Characters used in GSTIN checksum (position values)
_GSTIN_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _gstin_checksum(gstin_14: str) -> str:
    """Compute the GSTIN check digit (15th character) using the Luhn mod-36 variant.

    The algorithm multiplies each character's positional value by (1 if odd position,
    2 if even position), divides the product by 36 and sums quotient+remainder. The
    check digit is ``(36 - (total % 36)) % 36`` mapped back to the charset.
    """
    total = 0
    for i, ch in enumerate(gstin_14.upper()):
        val = _GSTIN_CHARSET.index(ch)
        factor = 2 if (i + 1) % 2 == 0 else 1
        product = val * factor
        total += (product // 36) + (product % 36)
    check_val = (36 - (total % 36)) % 36
    return _GSTIN_CHARSET[check_val]


def validate_gstin(gstin: str) -> dict:
    """Full structural validation of a GSTIN.

    Returns a dict with ``valid`` (bool) and ``errors`` (list of strings).
    On success also returns ``state``, ``pan``, ``entity_type``.
    """
    errors: list[str] = []
    result: dict[str, Any] = {"valid": False, "errors": errors, "gstin": gstin}

    if not gstin or not isinstance(gstin, str):
        errors.append("GSTIN is empty or not a string")
        return result

    gstin = gstin.strip().upper()
    result["gstin"] = gstin

    # Length check
    if len(gstin) != 15:
        errors.append(f"GSTIN must be 15 characters, got {len(gstin)}")
        return result

    # Regex for basic structure
    pattern = re.compile(r'^(\d{2})([A-Z]{5}\d{4}[A-Z])(\d)([A-Z])([A-Z\d])$')
    match = pattern.match(gstin)
    if not match:
        errors.append("GSTIN does not match structural pattern: 2-digit state + 10-char PAN + entity code + Z + check")
        return result

    state_code = match.group(1)
    pan = match.group(2)
    entity_num = match.group(3)
    default_z = match.group(4)
    check_digit = match.group(5)

    # State code validation
    if state_code not in STATE_CODE_MAP:
        errors.append(f"Invalid state code '{state_code}'. Valid: 01-38, 97")

    # Default character should be 'Z' (for regular taxpayers)
    if default_z != "Z":
        errors.append(f"14th character should be 'Z' for regular taxpayers, got '{default_z}'")

    # Checksum validation
    expected_check = _gstin_checksum(gstin[:14])
    if check_digit != expected_check:
        errors.append(f"Checksum mismatch: expected '{expected_check}', got '{check_digit}'")

    if errors:
        return result

    result["valid"] = True
    result["state"] = STATE_CODE_MAP.get(state_code, "Unknown")
    result["state_code"] = state_code
    result["pan"] = pan
    result["entity_type"] = _entity_type_label(entity_num)
    return result


def _entity_type_label(code: str) -> str:
    """Decode the 13th character (entity number) of GSTIN."""
    mapping = {
        "1": "Proprietorship / First Registration",
        "2": "Second Registration / Additional Place of Business",
        "3": "Third Registration",
    }
    return mapping.get(code, f"Registration number {code}")


def validate_gstin_batch(gstins: list[str]) -> list[dict]:
    """Validate multiple GSTINs. Returns list of validation results."""
    return [validate_gstin(g) for g in gstins]


# =====================================================================
# 2. HSN / SAC CODE VALIDATOR + RATE LOOKUP
# =====================================================================

# Top 200 goods HSN codes with GST rates (representative subset covering
# the most commonly-encountered codes in Indian CA practice).
HSN_RATE_MAP: dict[str, dict] = {
    # Chapter 1-4: Live animals, meat, dairy
    "0401": {"rate": Decimal("0"), "desc": "Milk (fresh)"},
    "0402": {"rate": Decimal("5"), "desc": "Milk (condensed/powder)"},
    "0406": {"rate": Decimal("12"), "desc": "Cheese"},
    # Chapter 7-8: Vegetables, Fruits
    "0701": {"rate": Decimal("0"), "desc": "Potatoes (fresh)"},
    "0713": {"rate": Decimal("5"), "desc": "Dried leguminous vegetables"},
    "0802": {"rate": Decimal("5"), "desc": "Nuts (almonds, cashews etc.)"},
    "0804": {"rate": Decimal("0"), "desc": "Dates, figs, pineapples"},
    # Chapter 9-10: Spices, Cereals
    "0904": {"rate": Decimal("5"), "desc": "Pepper"},
    "0910": {"rate": Decimal("5"), "desc": "Ginger, turmeric"},
    "1001": {"rate": Decimal("0"), "desc": "Wheat and meslin"},
    "1005": {"rate": Decimal("0"), "desc": "Maize (corn)"},
    "1006": {"rate": Decimal("5"), "desc": "Rice"},
    # Chapter 11: Products of milling industry
    "1101": {"rate": Decimal("0"), "desc": "Wheat flour (atta)"},
    # Chapter 15: Fats and oils
    "1507": {"rate": Decimal("5"), "desc": "Soyabean oil"},
    "1508": {"rate": Decimal("5"), "desc": "Groundnut oil"},
    "1509": {"rate": Decimal("5"), "desc": "Olive oil"},
    "1511": {"rate": Decimal("5"), "desc": "Palm oil"},
    "1515": {"rate": Decimal("5"), "desc": "Other vegetable fats and oils"},
    # Chapter 17: Sugars
    "1701": {"rate": Decimal("5"), "desc": "Cane/beet sugar"},
    "1704": {"rate": Decimal("18"), "desc": "Sugar confectionery"},
    # Chapter 18-19: Cocoa, bakery
    "1806": {"rate": Decimal("18"), "desc": "Chocolate and preparations"},
    "1905": {"rate": Decimal("18"), "desc": "Bread, biscuits, cakes"},
    # Chapter 20-22: Prepared food, beverages
    "2009": {"rate": Decimal("12"), "desc": "Fruit juices"},
    "2106": {"rate": Decimal("18"), "desc": "Food preparations n.e.s."},
    "2201": {"rate": Decimal("18"), "desc": "Mineral water, aerated water"},
    "2202": {"rate": Decimal("28"), "desc": "Aerated beverages with sugar"},
    # Chapter 24: Tobacco
    "2401": {"rate": Decimal("28"), "desc": "Unmanufactured tobacco"},
    "2402": {"rate": Decimal("28"), "desc": "Cigars, cigarettes"},
    # Chapter 25-27: Minerals, ores, fuels
    "2523": {"rate": Decimal("28"), "desc": "Portland cement"},
    "2710": {"rate": Decimal("18"), "desc": "Petroleum oils"},
    # Chapter 30: Pharmaceuticals
    "3003": {"rate": Decimal("12"), "desc": "Medicaments (not dosed/packed)"},
    "3004": {"rate": Decimal("12"), "desc": "Medicaments (dosed/packed for retail)"},
    "3006": {"rate": Decimal("12"), "desc": "Pharmaceutical goods"},
    # Chapter 33: Essential oils, cosmetics
    "3301": {"rate": Decimal("18"), "desc": "Essential oils"},
    "3304": {"rate": Decimal("28"), "desc": "Beauty/makeup preparations"},
    "3305": {"rate": Decimal("18"), "desc": "Hair preparations (shampoo etc.)"},
    "3306": {"rate": Decimal("18"), "desc": "Oral hygiene preparations"},
    # Chapter 34: Soap, detergent
    "3401": {"rate": Decimal("18"), "desc": "Soap, organic surface-active agents"},
    "3402": {"rate": Decimal("18"), "desc": "Washing preparations, detergents"},
    # Chapter 39: Plastics
    "3917": {"rate": Decimal("18"), "desc": "Tubes, pipes of plastics"},
    "3923": {"rate": Decimal("18"), "desc": "Plastic articles for packing"},
    "3926": {"rate": Decimal("18"), "desc": "Other articles of plastics"},
    # Chapter 40: Rubber
    "4011": {"rate": Decimal("28"), "desc": "New pneumatic tyres of rubber"},
    "4013": {"rate": Decimal("28"), "desc": "Inner tubes of rubber"},
    # Chapter 44: Wood
    "4415": {"rate": Decimal("18"), "desc": "Packing cases of wood"},
    "4418": {"rate": Decimal("18"), "desc": "Builders' joinery of wood"},
    # Chapter 48-49: Paper
    "4802": {"rate": Decimal("12"), "desc": "Paper and paperboard"},
    "4819": {"rate": Decimal("18"), "desc": "Cartons, boxes of paper"},
    "4901": {"rate": Decimal("0"), "desc": "Printed books"},
    "4902": {"rate": Decimal("0"), "desc": "Newspapers, journals"},
    # Chapter 52-63: Textiles
    "5208": {"rate": Decimal("5"), "desc": "Woven fabrics of cotton"},
    "6101": {"rate": Decimal("12"), "desc": "Men's overcoats, knitted"},
    "6109": {"rate": Decimal("5"), "desc": "T-shirts, vests (value <= Rs 1000)"},
    "6203": {"rate": Decimal("12"), "desc": "Men's suits, trousers"},
    "6204": {"rate": Decimal("12"), "desc": "Women's suits, dresses"},
    # Chapter 68-70: Stone, ceramic, glass
    "6802": {"rate": Decimal("28"), "desc": "Worked building stone"},
    "6907": {"rate": Decimal("18"), "desc": "Ceramic tiles"},
    "7005": {"rate": Decimal("18"), "desc": "Float glass"},
    "7013": {"rate": Decimal("18"), "desc": "Glassware"},
    # Chapter 72-73: Iron and steel
    "7204": {"rate": Decimal("18"), "desc": "Ferrous waste and scrap"},
    "7210": {"rate": Decimal("18"), "desc": "Flat-rolled products of iron/steel"},
    "7308": {"rate": Decimal("18"), "desc": "Structures of iron/steel"},
    "7318": {"rate": Decimal("18"), "desc": "Screws, bolts, nuts of iron/steel"},
    # Chapter 74-76: Copper, aluminium
    "7404": {"rate": Decimal("18"), "desc": "Copper waste and scrap"},
    "7606": {"rate": Decimal("18"), "desc": "Aluminium plates, sheets"},
    "7615": {"rate": Decimal("12"), "desc": "Aluminium kitchenware"},
    # Chapter 82-84: Tools, machinery
    "8201": {"rate": Decimal("12"), "desc": "Hand tools"},
    "8414": {"rate": Decimal("18"), "desc": "Air/vacuum pumps, compressors"},
    "8415": {"rate": Decimal("28"), "desc": "Air conditioning machines"},
    "8418": {"rate": Decimal("18"), "desc": "Refrigerators, freezers"},
    "8422": {"rate": Decimal("18"), "desc": "Dish washing machines"},
    "8443": {"rate": Decimal("18"), "desc": "Printing machinery, printers"},
    "8450": {"rate": Decimal("18"), "desc": "Household washing machines"},
    "8471": {"rate": Decimal("18"), "desc": "Computers, data processing units"},
    # Chapter 85: Electrical
    "8501": {"rate": Decimal("18"), "desc": "Electric motors and generators"},
    "8504": {"rate": Decimal("18"), "desc": "Electrical transformers"},
    "8507": {"rate": Decimal("28"), "desc": "Electric accumulators (batteries)"},
    "8517": {"rate": Decimal("18"), "desc": "Telephone sets, smartphones"},
    "8521": {"rate": Decimal("18"), "desc": "Video recording apparatus"},
    "8528": {"rate": Decimal("18"), "desc": "Monitors, projectors, TVs"},
    "8534": {"rate": Decimal("18"), "desc": "Printed circuits"},
    "8539": {"rate": Decimal("18"), "desc": "Electric lamps (LED, filament)"},
    "8544": {"rate": Decimal("18"), "desc": "Insulated wire, cables"},
    # Chapter 87: Vehicles
    "8703": {"rate": Decimal("28"), "desc": "Motor cars and vehicles"},
    "8711": {"rate": Decimal("28"), "desc": "Motorcycles"},
    "8712": {"rate": Decimal("12"), "desc": "Bicycles"},
    # Chapter 90: Instruments
    "9018": {"rate": Decimal("12"), "desc": "Medical instruments and appliances"},
    # Chapter 94: Furniture
    "9401": {"rate": Decimal("18"), "desc": "Seats and chairs"},
    "9403": {"rate": Decimal("18"), "desc": "Other furniture"},
    "9404": {"rate": Decimal("18"), "desc": "Mattresses"},
    # Chapter 95-96: Toys, misc manufactured
    "9503": {"rate": Decimal("12"), "desc": "Toys, puzzles, games"},
    "9608": {"rate": Decimal("18"), "desc": "Ball-point pens"},
    "9619": {"rate": Decimal("12"), "desc": "Sanitary pads, diapers"},
    # Gold, silver, jewellery
    "7108": {"rate": Decimal("3"), "desc": "Gold (unwrought/semi-manufactured)"},
    "7113": {"rate": Decimal("3"), "desc": "Articles of jewellery"},
    "7106": {"rate": Decimal("3"), "desc": "Silver (unwrought)"},
}

# Top 100 SAC (Service Accounting Codes) with GST rates
SAC_RATE_MAP: dict[str, dict] = {
    # Professional services
    "9971": {"rate": Decimal("18"), "desc": "Financial and related services"},
    "9972": {"rate": Decimal("18"), "desc": "Real estate services"},
    "9973": {"rate": Decimal("18"), "desc": "Leasing or rental services (non-financial)"},
    "9981": {"rate": Decimal("18"), "desc": "Research and development services"},
    "9982": {"rate": Decimal("18"), "desc": "Legal and accounting services"},
    "9983": {"rate": Decimal("18"), "desc": "Other professional, technical, and business services"},
    "9984": {"rate": Decimal("18"), "desc": "Telecommunications services"},
    "9985": {"rate": Decimal("5"), "desc": "Transport of passengers"},
    "9986": {"rate": Decimal("5"), "desc": "Transport of goods (GTA)"},
    "9987": {"rate": Decimal("18"), "desc": "Maintenance and repair services"},
    "9988": {"rate": Decimal("18"), "desc": "Manufacturing services on physical inputs"},
    "9989": {"rate": Decimal("18"), "desc": "Other manufacturing services"},
    "9991": {"rate": Decimal("18"), "desc": "Public administration services"},
    "9992": {"rate": Decimal("12"), "desc": "Education services"},
    "9993": {"rate": Decimal("18"), "desc": "Human health and social care services"},
    "9994": {"rate": Decimal("18"), "desc": "Sewage and waste collection services"},
    "9995": {"rate": Decimal("18"), "desc": "Services of membership organizations"},
    "9996": {"rate": Decimal("18"), "desc": "Recreational, cultural, and sporting services"},
    "9997": {"rate": Decimal("18"), "desc": "Other services"},
    "9998": {"rate": Decimal("18"), "desc": "Domestic services"},
    "9954": {"rate": Decimal("18"), "desc": "Construction services"},
    "9961": {"rate": Decimal("18"), "desc": "Postal and courier services"},
    "9962": {"rate": Decimal("18"), "desc": "Cargo handling services"},
    "9963": {"rate": Decimal("18"), "desc": "Accommodation and food services"},
    "9964": {"rate": Decimal("18"), "desc": "Passenger transport services"},
    "9965": {"rate": Decimal("5"), "desc": "Goods transport agency services"},
    "9966": {"rate": Decimal("18"), "desc": "Rental services of transport vehicles"},
    "9967": {"rate": Decimal("18"), "desc": "Supporting services in transport"},
    "9968": {"rate": Decimal("0"), "desc": "Postal services by Govt."},
    "9969": {"rate": Decimal("18"), "desc": "Electricity distribution services"},
    # IT / ITES
    "998311": {"rate": Decimal("18"), "desc": "Management consulting services"},
    "998312": {"rate": Decimal("18"), "desc": "Business consulting services"},
    "998313": {"rate": Decimal("18"), "desc": "IT consulting services"},
    "998314": {"rate": Decimal("18"), "desc": "IT design and development services"},
    "998315": {"rate": Decimal("18"), "desc": "Hosting and IT infrastructure"},
    "998316": {"rate": Decimal("18"), "desc": "IT infrastructure management (AMC)"},
    # Manpower supply, security
    "998519": {"rate": Decimal("18"), "desc": "Labour/manpower supply services"},
    "998521": {"rate": Decimal("18"), "desc": "Investigation and security services"},
    # Rent
    "997211": {"rate": Decimal("18"), "desc": "Rental of residential property (commercial use)"},
    "997212": {"rate": Decimal("18"), "desc": "Rental of non-residential property"},
    # Insurance
    "997131": {"rate": Decimal("18"), "desc": "Life insurance services"},
    "997132": {"rate": Decimal("18"), "desc": "General insurance services"},
    "997133": {"rate": Decimal("18"), "desc": "Reinsurance services"},
    # Banking
    "997111": {"rate": Decimal("18"), "desc": "Central banking services"},
    "997112": {"rate": Decimal("18"), "desc": "Deposit services"},
    "997113": {"rate": Decimal("18"), "desc": "Credit-granting services (loans)"},
    "997119": {"rate": Decimal("18"), "desc": "Other financial services"},
    # Commission / brokerage
    "997159": {"rate": Decimal("18"), "desc": "Brokerage and commission services"},
}


def validate_hsn_code(code: str) -> dict:
    """Validate an HSN or SAC code and return rate information if available.

    Validation rules (per GSTN advisory):
      - Turnover > 5Cr: minimum 6-digit HSN mandatory
      - Turnover 1.5Cr - 5Cr: minimum 4-digit HSN mandatory
      - Below 1.5Cr: 4-digit recommended
      - SAC codes: typically 4-6 digits (service codes starting with 99)
    """
    errors: list[str] = []
    result: dict[str, Any] = {"valid": False, "code": code, "errors": errors}

    if not code or not isinstance(code, str):
        errors.append("HSN/SAC code is empty")
        return result

    code = code.strip()

    if not re.match(r'^\d{4,8}$', code):
        errors.append(f"HSN/SAC must be 4-8 digits, got '{code}'")
        return result

    if len(code) < 4:
        errors.append("HSN/SAC code must be at least 4 digits")
        return result

    # Look up rate in HSN map (try progressively shorter prefixes)
    rate_info = None
    is_service = code.startswith("99")

    lookup_map = SAC_RATE_MAP if is_service else HSN_RATE_MAP
    for prefix_len in range(len(code), 3, -1):
        prefix = code[:prefix_len]
        if prefix in lookup_map:
            rate_info = lookup_map[prefix]
            break

    result["valid"] = True
    result["is_service"] = is_service
    result["code_type"] = "SAC" if is_service else "HSN"

    if rate_info:
        result["gst_rate"] = str(rate_info["rate"])
        result["description"] = rate_info["desc"]
        # Check for cess
        cess_prefix = code[:4]
        if cess_prefix in CESS_RATES:
            result["cess_rate"] = str(CESS_RATES[cess_prefix])
    else:
        result["gst_rate"] = None
        result["description"] = "Rate not in lookup table; verify on cbic-gst.gov.in"

    return result


# =====================================================================
# 3. PLACE OF SUPPLY DETERMINER
# =====================================================================

class SupplyCategory(str, Enum):
    GOODS = "goods"
    SERVICES = "services"
    IMPORT = "import"
    EXPORT = "export"


def determine_place_of_supply(
    supplier_state_code: str,
    recipient_state_code: str,
    category: str = "goods",
    recipient_gstin: Optional[str] = None,
    delivery_state_code: Optional[str] = None,
    service_type: Optional[str] = None,
    immovable_property_state: Optional[str] = None,
) -> dict:
    """Determine Place of Supply under IGST Act 2017.

    Section 10: Goods (domestic)
    Section 12: Services (domestic)
    Section 13: Import/Export of services

    Returns ``place_of_supply``, ``tax_type`` (IGST or CGST+SGST), and ``section``.
    """
    result: dict[str, Any] = {
        "supplier_state": supplier_state_code,
        "recipient_state": recipient_state_code,
    }

    cat = category.lower().strip()

    # --- Section 10: Goods ---
    if cat == "goods":
        # Default rule: POS = location where movement of goods terminates
        pos = delivery_state_code or recipient_state_code
        result["place_of_supply"] = pos
        result["section"] = "Section 10(1)(a) IGST Act"
        result["rule"] = "Location where movement of goods terminates"

        if delivery_state_code and delivery_state_code != recipient_state_code:
            result["note"] = (
                f"Delivery state ({delivery_state_code}) differs from recipient "
                f"state ({recipient_state_code}). POS follows delivery location."
            )

    # --- Section 12: Services (domestic) ---
    elif cat == "services":
        # Immovable property services: POS = location of property
        if immovable_property_state:
            pos = immovable_property_state
            result["section"] = "Section 12(3) IGST Act"
            result["rule"] = "Location of immovable property"

        # Restaurant / catering / personal care: POS = location where service performed
        elif service_type and service_type.lower() in (
            "restaurant", "catering", "beauty", "health", "fitness",
            "personal_care", "hotel", "accommodation",
        ):
            pos = supplier_state_code  # Performed at supplier's location
            result["section"] = "Section 12(4) IGST Act"
            result["rule"] = "Location where services are actually performed"

        # Transportation of goods: POS = destination of goods
        elif service_type and service_type.lower() in ("gta", "transport_goods", "courier"):
            pos = recipient_state_code  # location of recipient
            if recipient_gstin:
                result["section"] = "Section 12(8) IGST Act"
                result["rule"] = "Location of registered recipient"
            else:
                pos = delivery_state_code or recipient_state_code
                result["section"] = "Section 12(8) IGST Act"
                result["rule"] = "Location where goods are handed over for transport"

        # Banking / financial: POS = location of recipient
        elif service_type and service_type.lower() in ("banking", "financial", "insurance", "stock_broking"):
            pos = recipient_state_code
            result["section"] = "Section 12(12) IGST Act"
            result["rule"] = "Location of recipient of services"

        # General rule for services
        else:
            if recipient_gstin:
                pos = recipient_state_code
                result["section"] = "Section 12(2)(a) IGST Act"
                result["rule"] = "Location of registered recipient"
            else:
                pos = recipient_state_code or supplier_state_code
                result["section"] = "Section 12(2)(b) IGST Act"
                result["rule"] = "Location of recipient (address on record), else supplier location"

        result["place_of_supply"] = pos

    # --- Section 13: Import / Export of services ---
    elif cat in ("import", "export"):
        pos = supplier_state_code if cat == "import" else recipient_state_code
        result["place_of_supply"] = pos
        result["section"] = "Section 13(2) IGST Act"
        result["rule"] = "Location of recipient for imports, location of supplier for exports"

        if cat == "export":
            result["tax_type"] = "IGST (may claim refund or supply under LUT)"
            result["export_note"] = "Zero-rated supply under Section 16 IGST Act"
            return result
    else:
        pos = recipient_state_code
        result["place_of_supply"] = pos
        result["section"] = "Default"
        result["rule"] = "Recipient state used as fallback"

    # Determine IGST vs CGST+SGST
    if pos and supplier_state_code:
        if pos == supplier_state_code:
            result["tax_type"] = "CGST + SGST/UTGST"
            result["is_interstate"] = False
        else:
            result["tax_type"] = "IGST"
            result["is_interstate"] = True
    else:
        result["tax_type"] = "IGST"  # Default to IGST if state unknown
        result["is_interstate"] = True

    return result


# =====================================================================
# 4. INVOICE PARSING AND VALIDATION HELPERS
# =====================================================================

# Common column name aliases (mirrors the pattern in reconciliation_engine)
_COL_ALIASES: dict[str, list[str]] = {
    "invoice_no": ["invoice number", "invoice no", "inv no", "inv number",
                    "invoice_number", "document number", "doc no", "bill no"],
    "invoice_date": ["invoice date", "inv date", "invoice_date", "document date", "bill date"],
    "customer_name": ["customer name", "party name", "buyer name", "recipient name",
                       "consignee name", "buyer", "customer"],
    "customer_gstin": ["customer gstin", "buyer gstin", "recipient gstin",
                        "gstin/uin of recipient", "gstin_buyer", "party gstin"],
    "place_of_supply": ["place of supply", "pos", "pos code", "supply place"],
    "hsn_code": ["hsn code", "hsn/sac", "hsn", "sac code", "sac", "hsn_code", "hsn_sac"],
    "taxable_value": ["taxable value", "taxable amount", "taxable_value",
                       "assessable value", "base amount"],
    "cgst_rate": ["cgst rate", "cgst %", "cgst_rate", "central tax rate"],
    "sgst_rate": ["sgst rate", "sgst %", "sgst_rate", "state tax rate", "utgst rate"],
    "igst_rate": ["igst rate", "igst %", "igst_rate", "integrated tax rate"],
    "cgst_amount": ["cgst amount", "cgst", "cgst_amount", "central tax"],
    "sgst_amount": ["sgst amount", "sgst", "sgst_amount", "state tax", "utgst", "utgst amount"],
    "igst_amount": ["igst amount", "igst", "igst_amount", "integrated tax"],
    "total_value": ["total value", "invoice value", "total amount", "gross amount",
                     "invoice amount", "total_value"],
    "invoice_type": ["invoice type", "type", "supply type", "invoice_type", "doc type"],
    "cess_amount": ["cess amount", "cess", "cess_amount"],
    "note_type": ["note type", "note_type", "cr/dr", "credit/debit"],
    "original_invoice_no": ["original invoice no", "against invoice", "ref invoice",
                              "original_invoice_no", "original invoice number"],
}


def _find_column(df_columns: list[str], field: str) -> str:
    """Find a matching column from known aliases, case-insensitive."""
    cols_lower = {c.lower().strip(): c for c in df_columns}
    # Try exact canonical name first
    if field.lower() in cols_lower:
        return cols_lower[field.lower()]
    # Try aliases
    aliases = _COL_ALIASES.get(field, [])
    for alias in aliases:
        if alias.lower() in cols_lower:
            return cols_lower[alias.lower()]
    return ""


def _to_decimal(val: Any) -> Decimal:
    """Safely convert a value to Decimal, handling Indian number formats."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ZERO
    s = str(val).strip().replace(",", "").replace("\u20b9", "").replace("Rs", "").replace("Rs.", "")
    if not s or s == "-" or s.lower() == "nan":
        return ZERO
    try:
        return Decimal(s).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return ZERO


def _parse_date(val: Any) -> Optional[date]:
    """Parse common Indian date formats: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, (datetime, date)):
        return val if isinstance(val, date) else val.date()
    s = str(val).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _classify_invoice_type(row: dict, supplier_state: str) -> InvoiceType:
    """Auto-classify invoice into GSTR-1 table category.

    Rules:
      - Has recipient GSTIN and is B2B -> B2B
      - No GSTIN, interstate, value > 2.5L -> B2CL
      - No GSTIN, intrastate or value <= 2.5L -> B2CS
      - Export / SEZ -> EXPORT / SEZ
      - Has note_type (credit/debit) -> CDN
    """
    explicit_type = str(row.get("invoice_type", "")).upper().strip()
    if explicit_type in ("EXPORT", "EXPWP", "EXPWOP"):
        return InvoiceType.EXPORT
    if explicit_type in ("SEZ", "SEZWP", "SEZWOP"):
        return InvoiceType.SEZ
    if explicit_type in ("CDN", "CREDIT NOTE", "DEBIT NOTE", "CR", "DR"):
        return InvoiceType.CDN

    note_type = str(row.get("note_type", "")).upper().strip()
    if note_type in ("C", "CR", "CREDIT", "CREDIT NOTE", "D", "DR", "DEBIT", "DEBIT NOTE"):
        return InvoiceType.CDN

    customer_gstin = str(row.get("customer_gstin", "")).strip()
    has_gstin = bool(customer_gstin) and len(customer_gstin) >= 15

    taxable_value = _to_decimal(row.get("taxable_value", 0))
    pos = str(row.get("place_of_supply", "")).strip()[:2]
    is_interstate = pos != supplier_state if (pos and supplier_state) else False

    if has_gstin:
        return InvoiceType.B2B
    elif is_interstate and taxable_value > Decimal("250000"):
        return InvoiceType.B2CL
    else:
        return InvoiceType.B2CS


def _validate_invoice_row(row: dict, idx: int) -> list[str]:
    """Validate a single invoice row. Returns list of error strings."""
    errors: list[str] = []
    prefix = f"Row {idx}"

    # Invoice number
    inv_no = row.get("invoice_no", "")
    if not inv_no or (isinstance(inv_no, float) and pd.isna(inv_no)):
        errors.append(f"{prefix}: Missing invoice number")
    elif len(str(inv_no)) > 16:
        errors.append(f"{prefix}: Invoice number exceeds 16 characters (GSTN limit)")

    # Invoice date
    inv_date = _parse_date(row.get("invoice_date"))
    if not inv_date:
        errors.append(f"{prefix}: Invalid or missing invoice date")

    # GSTIN validation (only for B2B)
    gstin = str(row.get("customer_gstin", "")).strip()
    if gstin and len(gstin) >= 15:
        gstin_result = validate_gstin(gstin)
        if not gstin_result["valid"]:
            errors.append(f"{prefix}: Invalid GSTIN '{gstin}' - {'; '.join(gstin_result['errors'])}")

    # Place of supply
    pos = str(row.get("place_of_supply", "")).strip()
    if pos:
        pos_code = pos[:2] if len(pos) >= 2 else pos
        if pos_code.isdigit() and pos_code not in STATE_CODE_MAP:
            errors.append(f"{prefix}: Invalid place of supply code '{pos_code}'")

    # HSN code
    hsn = str(row.get("hsn_code", "")).strip()
    if hsn and hsn.lower() != "nan":
        if not re.match(r'^\d{4,8}$', hsn):
            errors.append(f"{prefix}: HSN/SAC code '{hsn}' must be 4-8 digits")

    # Taxable value
    taxable = _to_decimal(row.get("taxable_value", 0))
    if taxable < ZERO:
        inv_type_str = str(row.get("invoice_type", "")).upper()
        note_type_str = str(row.get("note_type", "")).upper()
        if inv_type_str not in ("CDN", "CREDIT NOTE") and note_type_str not in ("C", "CR", "CREDIT"):
            errors.append(f"{prefix}: Negative taxable value (Rs {taxable}) not allowed for regular invoices")

    # Rate consistency
    igst_rate = _to_decimal(row.get("igst_rate", 0))
    cgst_rate = _to_decimal(row.get("cgst_rate", 0))
    sgst_rate = _to_decimal(row.get("sgst_rate", 0))

    if igst_rate > ZERO and (cgst_rate > ZERO or sgst_rate > ZERO):
        errors.append(f"{prefix}: Cannot have both IGST and CGST/SGST rates on same invoice")

    total_rate = igst_rate if igst_rate > ZERO else (cgst_rate + sgst_rate)
    if total_rate > ZERO and total_rate not in VALID_GST_RATES:
        errors.append(f"{prefix}: Unusual GST rate {total_rate}% — expected one of {sorted(VALID_GST_RATES)}")

    # CGST and SGST should be equal
    if cgst_rate > ZERO and sgst_rate > ZERO and cgst_rate != sgst_rate:
        errors.append(f"{prefix}: CGST rate ({cgst_rate}%) and SGST rate ({sgst_rate}%) should be equal")

    # Tax amount cross-check
    if taxable > ZERO:
        if igst_rate > ZERO:
            expected_igst = (taxable * igst_rate / Decimal("100")).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            actual_igst = _to_decimal(row.get("igst_amount", 0))
            if actual_igst > ZERO and abs(actual_igst - expected_igst) > Decimal("1"):
                errors.append(
                    f"{prefix}: IGST amount mismatch: expected Rs {expected_igst}, "
                    f"got Rs {actual_igst} (diff: Rs {abs(actual_igst - expected_igst)})"
                )
        if cgst_rate > ZERO:
            expected_cgst = (taxable * cgst_rate / Decimal("100")).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            actual_cgst = _to_decimal(row.get("cgst_amount", 0))
            if actual_cgst > ZERO and abs(actual_cgst - expected_cgst) > Decimal("1"):
                errors.append(
                    f"{prefix}: CGST amount mismatch: expected Rs {expected_cgst}, "
                    f"got Rs {actual_cgst}"
                )

    return errors


# =====================================================================
# 5. GSTR-1 AUTO-GENERATION
# =====================================================================

async def parse_invoice_register(
    file_bytes: bytes,
    file_type: str = "excel",
    supplier_gstin: Optional[str] = None,
) -> dict:
    """Parse an invoice register from Excel or JSON bytes.

    Returns parsed invoice list, validation errors, and summary statistics.
    """
    invoices: list[dict] = []
    parse_errors: list[str] = []

    if file_type.lower() in ("excel", "xlsx", "xls"):
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
        except Exception as exc:
            return {"success": False, "error": f"Failed to read Excel file: {exc}", "invoices": []}
    elif file_type.lower() == "json":
        try:
            raw = json.loads(file_bytes.decode("utf-8"))
            if isinstance(raw, list):
                df = pd.DataFrame(raw)
            elif isinstance(raw, dict) and "invoices" in raw:
                df = pd.DataFrame(raw["invoices"])
            else:
                df = pd.DataFrame([raw])
        except Exception as exc:
            return {"success": False, "error": f"Failed to parse JSON: {exc}", "invoices": []}
    elif file_type.lower() == "csv":
        try:
            df = pd.read_csv(io.BytesIO(file_bytes), dtype=str)
        except Exception as exc:
            return {"success": False, "error": f"Failed to read CSV: {exc}", "invoices": []}
    else:
        return {"success": False, "error": f"Unsupported file type: {file_type}", "invoices": []}

    if df.empty:
        return {"success": False, "error": "File contains no data rows", "invoices": []}

    # Map columns to canonical names
    col_map: dict[str, str] = {}
    for canonical in _COL_ALIASES:
        found = _find_column(list(df.columns), canonical)
        if found:
            col_map[canonical] = found

    # Supplier state code from GSTIN
    supplier_state = ""
    if supplier_gstin:
        supplier_state = supplier_gstin[:2]

    for idx, raw_row in df.iterrows():
        row: dict[str, Any] = {}
        for canonical, actual_col in col_map.items():
            row[canonical] = raw_row.get(actual_col, "")

        # Also keep original row index for error reporting
        row_num = int(idx) + 2  # +2 for header row and 0-indexing

        invoices.append(row)

    # Validate all rows
    all_errors: list[str] = []
    for i, inv in enumerate(invoices):
        row_errors = _validate_invoice_row(inv, i + 2)
        all_errors.extend(row_errors)

    return {
        "success": True,
        "invoices": invoices,
        "total_rows": len(invoices),
        "validation_errors": all_errors,
        "columns_mapped": col_map,
    }


async def generate_gstr1(
    invoices: list[dict],
    supplier_gstin: str,
    return_period: str,
) -> dict:
    """Generate GSTR-1 JSON matching GSTN portal format.

    Args:
        invoices: List of invoice dicts (output from parse_invoice_register)
        supplier_gstin: Supplier's GSTIN (15-char)
        return_period: Filing period in MMYYYY format (e.g., '032025' for March 2025)

    Returns:
        GSTR-1 JSON structure with all tables populated.
    """
    gstin_result = validate_gstin(supplier_gstin)
    if not gstin_result["valid"]:
        return {"success": False, "error": f"Invalid supplier GSTIN: {gstin_result['errors']}"}

    supplier_state = supplier_gstin[:2]

    # Classify invoices into GSTR-1 tables
    b2b_invoices: list[dict] = []       # Table 4
    b2cl_invoices: list[dict] = []      # Table 5
    b2cs_records: list[dict] = []       # Table 7
    cdn_records: list[dict] = []        # Table 9
    export_invoices: list[dict] = []    # Table 6
    hsn_summary: dict[str, dict] = {}   # Table 12
    doc_summary: dict[str, dict] = {}   # Table 13

    # Validation errors during classification
    classification_errors: list[str] = []

    for idx, inv in enumerate(invoices):
        inv_type = _classify_invoice_type(inv, supplier_state)
        inv_no = str(inv.get("invoice_no", "")).strip()
        inv_date = _parse_date(inv.get("invoice_date"))
        inv_date_str = inv_date.strftime("%d-%m-%Y") if inv_date else ""

        taxable = _to_decimal(inv.get("taxable_value", 0))
        igst = _to_decimal(inv.get("igst_amount", 0))
        cgst = _to_decimal(inv.get("cgst_amount", 0))
        sgst = _to_decimal(inv.get("sgst_amount", 0))
        cess = _to_decimal(inv.get("cess_amount", 0))
        total = _to_decimal(inv.get("total_value", 0))

        # If total not provided, compute it
        if total == ZERO and taxable > ZERO:
            total = taxable + igst + cgst + sgst + cess

        pos = str(inv.get("place_of_supply", "")).strip()
        pos_code = pos[:2] if len(pos) >= 2 and pos[:2].isdigit() else supplier_state

        igst_rate = _to_decimal(inv.get("igst_rate", 0))
        cgst_rate = _to_decimal(inv.get("cgst_rate", 0))
        sgst_rate = _to_decimal(inv.get("sgst_rate", 0))
        gst_rate = igst_rate if igst_rate > ZERO else (cgst_rate + sgst_rate)

        hsn = str(inv.get("hsn_code", "")).strip()
        if hsn.lower() == "nan":
            hsn = ""

        # --- Table 4: B2B ---
        if inv_type == InvoiceType.B2B:
            cust_gstin = str(inv.get("customer_gstin", "")).strip().upper()
            b2b_invoices.append({
                "inum": inv_no,
                "idt": inv_date_str,
                "val": str(total),
                "pos": pos_code,
                "rchrg": "N",
                "inv_typ": "R",
                "itms": [{
                    "num": 1,
                    "itm_det": {
                        "txval": str(taxable),
                        "rt": str(gst_rate),
                        "iamt": str(igst),
                        "camt": str(cgst),
                        "samt": str(sgst),
                        "csamt": str(cess),
                    }
                }],
                "ctin": cust_gstin,
            })

        # --- Table 5: B2C Large ---
        elif inv_type == InvoiceType.B2CL:
            b2cl_invoices.append({
                "inum": inv_no,
                "idt": inv_date_str,
                "val": str(total),
                "pos": pos_code,
                "itms": [{
                    "num": 1,
                    "itm_det": {
                        "txval": str(taxable),
                        "rt": str(gst_rate),
                        "iamt": str(igst),
                        "csamt": str(cess),
                    }
                }],
            })

        # --- Table 7: B2C Small (aggregated by POS + rate) ---
        elif inv_type == InvoiceType.B2CS:
            b2cs_key = f"{pos_code}_{gst_rate}"
            if b2cs_key not in {r.get("_key") for r in b2cs_records}:
                b2cs_records.append({
                    "_key": b2cs_key,
                    "pos": pos_code,
                    "typ": "OE",  # Outward taxable (Exempted = E)
                    "rt": str(gst_rate),
                    "txval": taxable,
                    "iamt": igst,
                    "camt": cgst,
                    "samt": sgst,
                    "csamt": cess,
                })
            else:
                for rec in b2cs_records:
                    if rec.get("_key") == b2cs_key:
                        rec["txval"] += taxable
                        rec["iamt"] += igst
                        rec["camt"] += cgst
                        rec["samt"] += sgst
                        rec["csamt"] += cess
                        break

        # --- Table 9: Credit / Debit Notes ---
        elif inv_type == InvoiceType.CDN:
            note_type = str(inv.get("note_type", "C")).strip().upper()
            is_credit = note_type in ("C", "CR", "CREDIT", "CREDIT NOTE")
            orig_inv = str(inv.get("original_invoice_no", "")).strip()
            cust_gstin = str(inv.get("customer_gstin", "")).strip().upper()

            cdn_records.append({
                "ctin": cust_gstin,
                "nt": [{
                    "ntty": "C" if is_credit else "D",
                    "nt_num": inv_no,
                    "nt_dt": inv_date_str,
                    "val": str(abs(total)),
                    "pos": pos_code,
                    "rchrg": "N",
                    "inv_typ": "R",
                    "itms": [{
                        "num": 1,
                        "itm_det": {
                            "txval": str(abs(taxable)),
                            "rt": str(gst_rate),
                            "iamt": str(abs(igst)),
                            "camt": str(abs(cgst)),
                            "samt": str(abs(sgst)),
                            "csamt": str(abs(cess)),
                        }
                    }],
                }],
            })

        # --- Table 6: Exports ---
        elif inv_type in (InvoiceType.EXPORT, InvoiceType.SEZ):
            exp_typ = "WPAY" if igst > ZERO else "WOPAY"
            export_invoices.append({
                "exp_typ": exp_typ,
                "inum": inv_no,
                "idt": inv_date_str,
                "val": str(total),
                "sbpcode": "",
                "sbnum": "",
                "sbdt": "",
                "itms": [{
                    "txval": str(taxable),
                    "rt": str(gst_rate),
                    "iamt": str(igst),
                    "csamt": str(cess),
                }],
            })

        # --- Table 12: HSN Summary ---
        if hsn:
            hsn_key = f"{hsn}_{gst_rate}"
            if hsn_key not in hsn_summary:
                hsn_desc = ""
                hsn_lookup = validate_hsn_code(hsn)
                if hsn_lookup.get("description"):
                    hsn_desc = hsn_lookup["description"]

                hsn_summary[hsn_key] = {
                    "hsn_sc": hsn,
                    "desc": hsn_desc,
                    "uqc": "NOS",
                    "qty": Decimal("0"),
                    "txval": ZERO,
                    "iamt": ZERO,
                    "camt": ZERO,
                    "samt": ZERO,
                    "csamt": ZERO,
                    "rt": gst_rate,
                    "num": 0,
                }
            entry = hsn_summary[hsn_key]
            entry["txval"] += taxable
            entry["iamt"] += igst
            entry["camt"] += cgst
            entry["samt"] += sgst
            entry["csamt"] += cess
            entry["qty"] += Decimal("1")
            entry["num"] += 1

        # --- Table 13: Document Summary ---
        doc_type = "Invoices for outward supply"
        if inv_type == InvoiceType.CDN:
            note_type_str = str(inv.get("note_type", "")).upper()
            doc_type = "Credit Note" if note_type_str in ("C", "CR", "CREDIT") else "Debit Note"
        elif inv_type in (InvoiceType.EXPORT, InvoiceType.SEZ):
            doc_type = "Invoices for outward supply"

        if doc_type not in doc_summary:
            doc_summary[doc_type] = {"num": 0, "from": inv_no, "to": inv_no, "total": 0, "cancel": 0}
        doc_summary[doc_type]["num"] += 1
        doc_summary[doc_type]["total"] += 1
        doc_summary[doc_type]["to"] = inv_no

    # Serialize B2CS records (convert Decimal to str, remove _key)
    b2cs_output = []
    for rec in b2cs_records:
        b2cs_output.append({
            "pos": rec["pos"],
            "typ": rec["typ"],
            "rt": rec["rt"],
            "txval": str(rec["txval"]),
            "iamt": str(rec["iamt"]),
            "camt": str(rec["camt"]),
            "samt": str(rec["samt"]),
            "csamt": str(rec["csamt"]),
        })

    # Serialize HSN summary
    hsn_output = []
    for entry in hsn_summary.values():
        hsn_output.append({
            "hsn_sc": entry["hsn_sc"],
            "desc": entry["desc"],
            "uqc": entry["uqc"],
            "qty": str(entry["qty"]),
            "txval": str(entry["txval"]),
            "iamt": str(entry["iamt"]),
            "camt": str(entry["camt"]),
            "samt": str(entry["samt"]),
            "csamt": str(entry["csamt"]),
            "rt": str(entry["rt"]),
        })

    # Document summary
    doc_output = []
    for doc_type_name, doc_info in doc_summary.items():
        doc_output.append({
            "doc_type": doc_type_name,
            "docs": [{
                "num": doc_info["num"],
                "from": doc_info["from"],
                "to": doc_info["to"],
                "totnum": doc_info["total"],
                "cancel": doc_info["cancel"],
                "net_issue": doc_info["total"] - doc_info["cancel"],
            }],
        })

    # Group B2B invoices by recipient GSTIN
    b2b_grouped: dict[str, list] = {}
    for inv_item in b2b_invoices:
        ctin = inv_item.pop("ctin", "")
        b2b_grouped.setdefault(ctin, []).append(inv_item)

    b2b_output = [{"ctin": ctin, "inv": inv_list} for ctin, inv_list in b2b_grouped.items()]

    # Group B2CL by POS
    b2cl_grouped: dict[str, list] = {}
    for inv_item in b2cl_invoices:
        pos_val = inv_item.get("pos", "")
        b2cl_grouped.setdefault(pos_val, []).append(inv_item)

    b2cl_output = [{"pos": pos_val, "inv": inv_list} for pos_val, inv_list in b2cl_grouped.items()]

    gstr1_json = {
        "gstin": supplier_gstin,
        "fp": return_period,
        "gt": "",
        "cur_gt": "",
        "b2b": b2b_output,
        "b2cl": b2cl_output,
        "b2cs": b2cs_output,
        "cdnr": cdn_records,
        "exp": export_invoices,
        "hsn": {"data": hsn_output},
        "doc_issue": {"doc_det": doc_output},
    }

    # Summary statistics
    total_taxable = sum(_to_decimal(inv.get("taxable_value", 0)) for inv in invoices)
    total_igst = sum(_to_decimal(inv.get("igst_amount", 0)) for inv in invoices)
    total_cgst = sum(_to_decimal(inv.get("cgst_amount", 0)) for inv in invoices)
    total_sgst = sum(_to_decimal(inv.get("sgst_amount", 0)) for inv in invoices)
    total_tax = total_igst + total_cgst + total_sgst

    summary = {
        "total_invoices": len(invoices),
        "b2b_count": sum(len(g["inv"]) for g in b2b_output),
        "b2cl_count": sum(len(g["inv"]) for g in b2cl_output),
        "b2cs_count": len(b2cs_output),
        "cdn_count": len(cdn_records),
        "export_count": len(export_invoices),
        "total_taxable_value": str(total_taxable),
        "total_igst": str(total_igst),
        "total_cgst": str(total_cgst),
        "total_sgst": str(total_sgst),
        "total_tax": str(total_tax),
    }

    return {
        "success": True,
        "gstr1": gstr1_json,
        "summary": summary,
        "classification_errors": classification_errors,
    }


# =====================================================================
# 6. GSTR-3B COMPUTATION
# =====================================================================

# Section 17(5) — Blocked ITC categories (keywords for auto-detection)
BLOCKED_ITC_KEYWORDS: list[dict[str, Any]] = [
    {"keywords": ["motor vehicle", "car", "automobile", "vehicle"],
     "section": "17(5)(a)", "desc": "Motor vehicles and conveyances (except for specified purposes)"},
    {"keywords": ["food", "catering", "outdoor catering", "pantry", "beverages"],
     "section": "17(5)(b)(i)", "desc": "Food and beverages, outdoor catering"},
    {"keywords": ["beauty", "cosmetic", "health", "fitness", "salon", "spa", "parlour"],
     "section": "17(5)(b)(ii)", "desc": "Beauty treatment, health, fitness, cosmetic/plastic surgery"},
    {"keywords": ["club", "membership", "subscription"],
     "section": "17(5)(b)(iii)", "desc": "Membership of club, health and fitness centre"},
    {"keywords": ["travel", "leave travel", "ltc", "holiday", "vacation"],
     "section": "17(5)(b)(iv)", "desc": "Travel benefits extended to employees on vacation (LTC)"},
    {"keywords": ["works contract", "construction", "immovable", "building"],
     "section": "17(5)(c)(d)", "desc": "Works contract/construction of immovable property (except plant & machinery)"},
    {"keywords": ["personal", "gift", "free sample"],
     "section": "17(5)(h)", "desc": "Goods/services for personal consumption or gifts/free samples"},
]


def _is_blocked_itc(description: str, hsn_code: str = "") -> Optional[dict]:
    """Check if a purchase falls under Section 17(5) blocked ITC.

    Returns blocking reason dict if blocked, else None.
    """
    desc_lower = (description or "").lower()
    for blocked in BLOCKED_ITC_KEYWORDS:
        for keyword in blocked["keywords"]:
            if keyword in desc_lower:
                return {"section": blocked["section"], "reason": blocked["desc"]}

    # Motor vehicles by HSN (8703, 8711)
    if hsn_code and hsn_code[:4] in ("8703", "8711"):
        return {"section": "17(5)(a)", "reason": "Motor vehicles (HSN 8703/8711)"}

    return None


async def compute_gstr3b(
    gstr1_data: dict,
    purchase_register: list[dict],
    itc_ledger: Optional[list[dict]] = None,
    gstr2b_data: Optional[list[dict]] = None,
    previous_period_balance: Optional[dict] = None,
) -> dict:
    """Compute GSTR-3B from GSTR-1 output, purchase register, and ITC data.

    Args:
        gstr1_data: Output from generate_gstr1 (the 'gstr1' key)
        purchase_register: List of purchase dicts with fields:
            supplier_gstin, invoice_no, invoice_date, description, hsn_code,
            taxable_value, igst, cgst, sgst, cess, total, supply_type
        itc_ledger: Optional existing ITC balance ledger
        gstr2b_data: Optional GSTR-2B data for Rule 36(4) check
        previous_period_balance: Optional dict with carried-forward ITC balances

    Returns:
        GSTR-3B computation with all tables.
    """
    # ── Table 3.1: Outward Supplies ──
    table_3_1 = {
        "a": {"taxable": ZERO, "igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cess": ZERO,
              "label": "Outward taxable supplies (other than zero rated, nil rated and exempted)"},
        "b": {"taxable": ZERO, "igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cess": ZERO,
              "label": "Outward taxable supplies (zero rated)"},
        "c": {"taxable": ZERO, "igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cess": ZERO,
              "label": "Other outward supplies (nil rated, exempted)"},
        "d": {"taxable": ZERO, "igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cess": ZERO,
              "label": "Inward supplies (liable to reverse charge)"},
        "e": {"taxable": ZERO, "igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cess": ZERO,
              "label": "Non-GST outward supplies"},
    }

    # Process B2B invoices
    for b2b_group in gstr1_data.get("b2b", []):
        for inv in b2b_group.get("inv", []):
            for itm in inv.get("itms", []):
                det = itm.get("itm_det", {})
                table_3_1["a"]["taxable"] += _to_decimal(det.get("txval", 0))
                table_3_1["a"]["igst"] += _to_decimal(det.get("iamt", 0))
                table_3_1["a"]["cgst"] += _to_decimal(det.get("camt", 0))
                table_3_1["a"]["sgst"] += _to_decimal(det.get("samt", 0))
                table_3_1["a"]["cess"] += _to_decimal(det.get("csamt", 0))

    # Process B2CL
    for b2cl_group in gstr1_data.get("b2cl", []):
        for inv in b2cl_group.get("inv", []):
            for itm in inv.get("itms", []):
                det = itm.get("itm_det", {})
                table_3_1["a"]["taxable"] += _to_decimal(det.get("txval", 0))
                table_3_1["a"]["igst"] += _to_decimal(det.get("iamt", 0))
                table_3_1["a"]["cess"] += _to_decimal(det.get("csamt", 0))

    # Process B2CS
    for rec in gstr1_data.get("b2cs", []):
        table_3_1["a"]["taxable"] += _to_decimal(rec.get("txval", 0))
        table_3_1["a"]["igst"] += _to_decimal(rec.get("iamt", 0))
        table_3_1["a"]["cgst"] += _to_decimal(rec.get("camt", 0))
        table_3_1["a"]["sgst"] += _to_decimal(rec.get("samt", 0))
        table_3_1["a"]["cess"] += _to_decimal(rec.get("csamt", 0))

    # Process Exports (zero rated)
    for exp in gstr1_data.get("exp", []):
        for itm in exp.get("itms", []):
            table_3_1["b"]["taxable"] += _to_decimal(itm.get("txval", 0))
            table_3_1["b"]["igst"] += _to_decimal(itm.get("iamt", 0))
            table_3_1["b"]["cess"] += _to_decimal(itm.get("csamt", 0))

    # Process Credit/Debit Notes (adjust from outward supplies)
    for cdn in gstr1_data.get("cdnr", []):
        for nt in cdn.get("nt", []):
            for itm in nt.get("itms", []):
                det = itm.get("itm_det", {})
                multiplier = Decimal("-1") if nt.get("ntty") == "C" else Decimal("1")
                table_3_1["a"]["taxable"] += _to_decimal(det.get("txval", 0)) * multiplier
                table_3_1["a"]["igst"] += _to_decimal(det.get("iamt", 0)) * multiplier
                table_3_1["a"]["cgst"] += _to_decimal(det.get("camt", 0)) * multiplier
                table_3_1["a"]["sgst"] += _to_decimal(det.get("samt", 0)) * multiplier
                table_3_1["a"]["cess"] += _to_decimal(det.get("csamt", 0)) * multiplier

    # ── Table 3.2: Interstate supplies to unregistered persons ──
    table_3_2 = {
        "unreg_supplies": [],
        "comp_supplies": [],
        "uin_holders": [],
    }

    for b2cl_group in gstr1_data.get("b2cl", []):
        pos = b2cl_group.get("pos", "")
        total_txval = ZERO
        total_igst = ZERO
        for inv in b2cl_group.get("inv", []):
            for itm in inv.get("itms", []):
                det = itm.get("itm_det", {})
                total_txval += _to_decimal(det.get("txval", 0))
                total_igst += _to_decimal(det.get("iamt", 0))
        if total_txval > ZERO:
            table_3_2["unreg_supplies"].append({
                "pos": pos,
                "state": STATE_CODE_MAP.get(pos, "Unknown"),
                "taxable_value": str(total_txval),
                "igst": str(total_igst),
            })

    # ── Table 4: ITC Computation ──
    itc_eligible = {"igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cess": ZERO}
    itc_blocked = {"igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cess": ZERO}
    itc_reversed = {"igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cess": ZERO}
    itc_ineligible_others = {"igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cess": ZERO}
    blocked_details: list[dict] = []

    # Build GSTR-2B index for Rule 36(4) check
    gstr2b_total = {"igst": ZERO, "cgst": ZERO, "sgst": ZERO}
    if gstr2b_data:
        for entry in gstr2b_data:
            gstr2b_total["igst"] += _to_decimal(entry.get("igst", 0))
            gstr2b_total["cgst"] += _to_decimal(entry.get("cgst", 0))
            gstr2b_total["sgst"] += _to_decimal(entry.get("sgst", 0))

    for purchase in purchase_register:
        p_igst = _to_decimal(purchase.get("igst", 0))
        p_cgst = _to_decimal(purchase.get("cgst", 0))
        p_sgst = _to_decimal(purchase.get("sgst", 0))
        p_cess = _to_decimal(purchase.get("cess", 0))
        description = str(purchase.get("description", ""))
        hsn_code = str(purchase.get("hsn_code", ""))
        supply_type = str(purchase.get("supply_type", "")).lower()

        # Check if blocked under Section 17(5)
        blocked = _is_blocked_itc(description, hsn_code)
        if blocked:
            itc_blocked["igst"] += p_igst
            itc_blocked["cgst"] += p_cgst
            itc_blocked["sgst"] += p_sgst
            itc_blocked["cess"] += p_cess
            blocked_details.append({
                "invoice_no": purchase.get("invoice_no", ""),
                "supplier_gstin": purchase.get("supplier_gstin", ""),
                "amount": str(p_igst + p_cgst + p_sgst + p_cess),
                "section": blocked["section"],
                "reason": blocked["reason"],
            })
            continue

        # Check exempt / non-GST inward supplies
        if supply_type in ("exempt", "nil", "non-gst"):
            itc_ineligible_others["igst"] += p_igst
            itc_ineligible_others["cgst"] += p_cgst
            itc_ineligible_others["sgst"] += p_sgst
            itc_ineligible_others["cess"] += p_cess
            continue

        # Eligible ITC
        itc_eligible["igst"] += p_igst
        itc_eligible["cgst"] += p_cgst
        itc_eligible["sgst"] += p_sgst
        itc_eligible["cess"] += p_cess

    # Rule 36(4) check — ITC restricted to 105% of GSTR-2B
    rule_36_4_restriction = {"applied": False, "details": {}}
    if gstr2b_data:
        limit_factor = Decimal("1.05")
        for tax_head in ("igst", "cgst", "sgst"):
            max_allowed = (gstr2b_total[tax_head] * limit_factor).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            if itc_eligible[tax_head] > max_allowed:
                excess = itc_eligible[tax_head] - max_allowed
                itc_reversed[tax_head] += excess
                itc_eligible[tax_head] = max_allowed
                rule_36_4_restriction["applied"] = True
                rule_36_4_restriction["details"][tax_head] = {
                    "claimed": str(itc_eligible[tax_head] + excess),
                    "gstr2b_amount": str(gstr2b_total[tax_head]),
                    "max_allowed_105pct": str(max_allowed),
                    "reversed": str(excess),
                }

    # Add carry-forward ITC from previous period
    if previous_period_balance:
        for head in ("igst", "cgst", "sgst", "cess"):
            itc_eligible[head] += _to_decimal(previous_period_balance.get(head, 0))

    net_itc = {
        "igst": itc_eligible["igst"] - itc_reversed["igst"],
        "cgst": itc_eligible["cgst"] - itc_reversed["cgst"],
        "sgst": itc_eligible["sgst"] - itc_reversed["sgst"],
        "cess": itc_eligible["cess"] - itc_reversed["cess"],
    }

    table_4 = {
        "A_eligible_itc": {head: str(itc_eligible[head]) for head in ("igst", "cgst", "sgst", "cess")},
        "B_reversed_rule_42_43": {head: str(itc_reversed[head]) for head in ("igst", "cgst", "sgst", "cess")},
        "C_net_itc": {head: str(net_itc[head]) for head in ("igst", "cgst", "sgst", "cess")},
        "D_ineligible_blocked": {head: str(itc_blocked[head]) for head in ("igst", "cgst", "sgst", "cess")},
        "blocked_details": blocked_details,
        "rule_36_4": rule_36_4_restriction,
    }

    # ── Table 5: Exempt, nil-rated, non-GST inward supplies ──
    exempt_inter = ZERO
    exempt_intra = ZERO
    nil_inter = ZERO
    nil_intra = ZERO
    nongst_inter = ZERO
    nongst_intra = ZERO

    supplier_gstin_str = gstr1_data.get("gstin", "")
    supplier_state_code = supplier_gstin_str[:2] if len(supplier_gstin_str) >= 2 else ""

    for purchase in purchase_register:
        supply_type = str(purchase.get("supply_type", "")).lower()
        if supply_type not in ("exempt", "nil", "non-gst"):
            continue
        taxable = _to_decimal(purchase.get("taxable_value", 0))
        p_gstin = str(purchase.get("supplier_gstin", "")).strip()
        p_state = p_gstin[:2] if len(p_gstin) >= 2 else ""
        is_inter = p_state != supplier_state_code if (p_state and supplier_state_code) else False

        if supply_type == "exempt":
            if is_inter:
                exempt_inter += taxable
            else:
                exempt_intra += taxable
        elif supply_type == "nil":
            if is_inter:
                nil_inter += taxable
            else:
                nil_intra += taxable
        elif supply_type == "non-gst":
            if is_inter:
                nongst_inter += taxable
            else:
                nongst_intra += taxable

    table_5 = {
        "exempt": {"inter": str(exempt_inter), "intra": str(exempt_intra)},
        "nil_rated": {"inter": str(nil_inter), "intra": str(nil_intra)},
        "non_gst": {"inter": str(nongst_inter), "intra": str(nongst_intra)},
    }

    # ── Table 6.1: Tax Liability and Payment ──
    # ITC set-off order (post-2019 amendment):
    #   IGST liability: IGST ITC first -> CGST ITC -> SGST ITC
    #   CGST liability: IGST ITC first (if remaining) -> CGST ITC
    #   SGST liability: IGST ITC first (if remaining) -> SGST ITC
    #   Cross-utilization: CGST ITC cannot be used for SGST and vice versa

    output_igst = table_3_1["a"]["igst"] + table_3_1["b"]["igst"]
    output_cgst = table_3_1["a"]["cgst"]
    output_sgst = table_3_1["a"]["sgst"]
    output_cess = table_3_1["a"]["cess"] + table_3_1["b"]["cess"]

    avail_igst = net_itc["igst"]
    avail_cgst = net_itc["cgst"]
    avail_sgst = net_itc["sgst"]
    avail_cess = net_itc["cess"]

    setoff_log: list[str] = []

    # Step 1: Set off IGST liability using IGST ITC
    igst_from_igst = min(output_igst, avail_igst)
    avail_igst -= igst_from_igst
    remaining_igst = output_igst - igst_from_igst
    if igst_from_igst > ZERO:
        setoff_log.append(f"IGST liability Rs {output_igst} set off with IGST ITC Rs {igst_from_igst}")

    # Step 2: Set off remaining IGST liability using CGST ITC
    igst_from_cgst = min(remaining_igst, avail_cgst)
    avail_cgst -= igst_from_cgst
    remaining_igst -= igst_from_cgst
    if igst_from_cgst > ZERO:
        setoff_log.append(f"Remaining IGST liability Rs {remaining_igst + igst_from_cgst} "
                          f"set off with CGST ITC Rs {igst_from_cgst}")

    # Step 3: Set off remaining IGST liability using SGST ITC
    igst_from_sgst = min(remaining_igst, avail_sgst)
    avail_sgst -= igst_from_sgst
    remaining_igst -= igst_from_sgst
    if igst_from_sgst > ZERO:
        setoff_log.append(f"Remaining IGST liability set off with SGST ITC Rs {igst_from_sgst}")

    # Step 4: Set off remaining IGST ITC against CGST liability
    cgst_from_igst = min(output_cgst, avail_igst)
    avail_igst -= cgst_from_igst
    remaining_cgst = output_cgst - cgst_from_igst
    if cgst_from_igst > ZERO:
        setoff_log.append(f"CGST liability Rs {output_cgst} set off with IGST ITC Rs {cgst_from_igst}")

    # Step 5: Set off remaining IGST ITC against SGST liability
    sgst_from_igst = min(output_sgst, avail_igst)
    avail_igst -= sgst_from_igst
    remaining_sgst = output_sgst - sgst_from_igst
    if sgst_from_igst > ZERO:
        setoff_log.append(f"SGST liability Rs {output_sgst} set off with IGST ITC Rs {sgst_from_igst}")

    # Step 6: Set off CGST liability with CGST ITC
    cgst_from_cgst = min(remaining_cgst, avail_cgst)
    avail_cgst -= cgst_from_cgst
    remaining_cgst -= cgst_from_cgst
    if cgst_from_cgst > ZERO:
        setoff_log.append(f"CGST liability set off with CGST ITC Rs {cgst_from_cgst}")

    # Step 7: Set off SGST liability with SGST ITC
    sgst_from_sgst = min(remaining_sgst, avail_sgst)
    avail_sgst -= sgst_from_sgst
    remaining_sgst -= sgst_from_sgst
    if sgst_from_sgst > ZERO:
        setoff_log.append(f"SGST liability set off with SGST ITC Rs {sgst_from_sgst}")

    # Step 8: Cess set-off (cess ITC can only set off cess liability)
    cess_from_cess = min(output_cess, avail_cess)
    remaining_cess = output_cess - cess_from_cess
    avail_cess -= cess_from_cess

    # Cash payment = remaining liability after ITC set-off
    cash_igst = max(remaining_igst, ZERO)
    cash_cgst = max(remaining_cgst, ZERO)
    cash_sgst = max(remaining_sgst, ZERO)
    cash_cess = max(remaining_cess, ZERO)
    total_cash = cash_igst + cash_cgst + cash_sgst + cash_cess

    table_6_1 = {
        "tax_liability": {
            "igst": str(output_igst),
            "cgst": str(output_cgst),
            "sgst": str(output_sgst),
            "cess": str(output_cess),
        },
        "itc_setoff": {
            "igst": {
                "from_igst": str(igst_from_igst),
                "from_cgst": str(igst_from_cgst),
                "from_sgst": str(igst_from_sgst),
            },
            "cgst": {
                "from_igst": str(cgst_from_igst),
                "from_cgst": str(cgst_from_cgst),
            },
            "sgst": {
                "from_igst": str(sgst_from_igst),
                "from_sgst": str(sgst_from_sgst),
            },
            "cess": {
                "from_cess": str(cess_from_cess),
            },
        },
        "cash_payment": {
            "igst": str(cash_igst),
            "cgst": str(cash_cgst),
            "sgst": str(cash_sgst),
            "cess": str(cash_cess),
            "total": str(total_cash),
        },
        "itc_balance_carried_forward": {
            "igst": str(max(avail_igst, ZERO)),
            "cgst": str(max(avail_cgst, ZERO)),
            "sgst": str(max(avail_sgst, ZERO)),
            "cess": str(max(avail_cess, ZERO)),
        },
        "setoff_log": setoff_log,
    }

    return {
        "success": True,
        "return_period": gstr1_data.get("fp", ""),
        "gstin": gstr1_data.get("gstin", ""),
        "table_3_1": {
            k: {kk: str(vv) if isinstance(vv, Decimal) else vv for kk, vv in v.items()}
            for k, v in table_3_1.items()
        },
        "table_3_2": table_3_2,
        "table_4_itc": table_4,
        "table_5_exempt": table_5,
        "table_6_1_payment": table_6_1,
    }


# =====================================================================
# 7. ITC TRACKER — Rule 36(4), Rule 42/43, Section 16(2) aging
# =====================================================================

async def track_itc(
    purchase_register: list[dict],
    gstr2b_data: list[dict],
    payment_ledger: Optional[list[dict]] = None,
    capital_goods_register: Optional[list[dict]] = None,
    common_credit_details: Optional[dict] = None,
) -> dict:
    """Comprehensive ITC tracker with all restriction checks.

    Checks performed:
      1. Match claimed ITC against GSTR-2B availability
      2. Flag Section 17(5) blocked credits
      3. Rule 36(4): restrict to 105% of GSTR-2B
      4. Section 16(2): payment within 180 days check
      5. Rule 42: common credit apportionment
      6. Rule 43: capital goods credit reversal

    Args:
        purchase_register: Purchases with invoice_no, supplier_gstin, invoice_date,
                          description, hsn_code, igst, cgst, sgst, cess, total,
                          payment_date (optional), supply_type
        gstr2b_data: GSTR-2B entries with supplier_gstin, invoice_no, igst, cgst, sgst
        payment_ledger: Optional list of payments with invoice_no, payment_date, amount
        capital_goods_register: Optional list of capital goods with asset_id, invoice_no,
                                 invoice_date, igst, cgst, sgst, useful_life_months,
                                 taxable_use_percentage
        common_credit_details: Optional dict with turnover_taxable, turnover_exempt,
                                turnover_total for Rule 42 computation
    """
    # Index GSTR-2B by (supplier_gstin, normalized_invoice_no)
    gstr2b_index: dict[str, dict] = {}
    for entry in gstr2b_data:
        gstin = str(entry.get("supplier_gstin", "")).strip().upper()
        inv_no = str(entry.get("invoice_no", "")).strip().upper()
        key = f"{gstin}_{inv_no}"
        gstr2b_index[key] = entry

    # Index payments by invoice_no
    payment_index: dict[str, date] = {}
    if payment_ledger:
        for pmt in payment_ledger:
            inv_no = str(pmt.get("invoice_no", "")).strip()
            pmt_date = _parse_date(pmt.get("payment_date"))
            if inv_no and pmt_date:
                payment_index[inv_no] = pmt_date

    # Process each purchase
    matched: list[dict] = []
    unmatched: list[dict] = []
    blocked: list[dict] = []
    aging_reversals: list[dict] = []
    today = date.today()

    total_claimed = {"igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cess": ZERO}
    total_available_2b = {"igst": ZERO, "cgst": ZERO, "sgst": ZERO}
    total_blocked = {"igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cess": ZERO}
    total_aging_reversal = {"igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cess": ZERO}

    for purchase in purchase_register:
        p_gstin = str(purchase.get("supplier_gstin", "")).strip().upper()
        p_inv = str(purchase.get("invoice_no", "")).strip().upper()
        p_igst = _to_decimal(purchase.get("igst", 0))
        p_cgst = _to_decimal(purchase.get("cgst", 0))
        p_sgst = _to_decimal(purchase.get("sgst", 0))
        p_cess = _to_decimal(purchase.get("cess", 0))
        p_desc = str(purchase.get("description", ""))
        p_hsn = str(purchase.get("hsn_code", ""))
        p_date = _parse_date(purchase.get("invoice_date"))
        supply_type = str(purchase.get("supply_type", "")).lower()

        total_claimed["igst"] += p_igst
        total_claimed["cgst"] += p_cgst
        total_claimed["sgst"] += p_sgst
        total_claimed["cess"] += p_cess

        entry_result: dict[str, Any] = {
            "supplier_gstin": p_gstin,
            "invoice_no": p_inv,
            "invoice_date": p_date.isoformat() if p_date else None,
            "igst": str(p_igst),
            "cgst": str(p_cgst),
            "sgst": str(p_sgst),
            "cess": str(p_cess),
            "flags": [],
        }

        # Check Section 17(5) blocked
        blocked_info = _is_blocked_itc(p_desc, p_hsn)
        if blocked_info:
            entry_result["status"] = "BLOCKED"
            entry_result["flags"].append(f"Blocked u/s {blocked_info['section']}: {blocked_info['reason']}")
            blocked.append(entry_result)
            total_blocked["igst"] += p_igst
            total_blocked["cgst"] += p_cgst
            total_blocked["sgst"] += p_sgst
            total_blocked["cess"] += p_cess
            continue

        # Check if exempt/nil/non-GST
        if supply_type in ("exempt", "nil", "non-gst"):
            entry_result["status"] = "INELIGIBLE"
            entry_result["flags"].append(f"Ineligible: {supply_type} supply")
            blocked.append(entry_result)
            continue

        # Match against GSTR-2B
        lookup_key = f"{p_gstin}_{p_inv}"
        gstr2b_entry = gstr2b_index.get(lookup_key)

        if gstr2b_entry:
            b2b_igst = _to_decimal(gstr2b_entry.get("igst", 0))
            b2b_cgst = _to_decimal(gstr2b_entry.get("cgst", 0))
            b2b_sgst = _to_decimal(gstr2b_entry.get("sgst", 0))

            total_available_2b["igst"] += b2b_igst
            total_available_2b["cgst"] += b2b_cgst
            total_available_2b["sgst"] += b2b_sgst

            # Check for amount mismatch
            igst_diff = abs(p_igst - b2b_igst)
            cgst_diff = abs(p_cgst - b2b_cgst)
            sgst_diff = abs(p_sgst - b2b_sgst)

            if igst_diff > Decimal("1") or cgst_diff > Decimal("1") or sgst_diff > Decimal("1"):
                entry_result["status"] = "MISMATCH"
                entry_result["flags"].append(
                    f"Amount mismatch with GSTR-2B: IGST diff Rs {igst_diff}, "
                    f"CGST diff Rs {cgst_diff}, SGST diff Rs {sgst_diff}"
                )
                entry_result["gstr2b_amounts"] = {
                    "igst": str(b2b_igst), "cgst": str(b2b_cgst), "sgst": str(b2b_sgst),
                }
            else:
                entry_result["status"] = "MATCHED"

            matched.append(entry_result)
        else:
            entry_result["status"] = "NOT_IN_2B"
            entry_result["flags"].append("Invoice not found in GSTR-2B — supplier may not have filed")
            unmatched.append(entry_result)

        # Section 16(2) — 180-day payment check
        if p_date:
            payment_date = payment_index.get(p_inv)
            days_since_invoice = (today - p_date).days

            if days_since_invoice > 180 and not payment_date:
                entry_result["flags"].append(
                    f"MANDATORY REVERSAL: Invoice older than 180 days ({days_since_invoice} days) "
                    f"without payment — Section 16(2) proviso"
                )
                entry_result["reversal_required"] = True
                aging_reversals.append({
                    "invoice_no": p_inv,
                    "supplier_gstin": p_gstin,
                    "invoice_date": p_date.isoformat(),
                    "days_overdue": days_since_invoice,
                    "igst": str(p_igst),
                    "cgst": str(p_cgst),
                    "sgst": str(p_sgst),
                    "reason": "Section 16(2) — payment not made within 180 days",
                })
                total_aging_reversal["igst"] += p_igst
                total_aging_reversal["cgst"] += p_cgst
                total_aging_reversal["sgst"] += p_sgst
                total_aging_reversal["cess"] += p_cess

            elif payment_date and (payment_date - p_date).days > 180:
                entry_result["flags"].append(
                    f"WARNING: Payment made {(payment_date - p_date).days} days after invoice. "
                    f"ITC reversal was required between day 181 and payment date."
                )

    # Rule 36(4) — Restrict to 105% of GSTR-2B
    rule_36_4_result: dict[str, Any] = {"applied": False}
    if gstr2b_data:
        limit_factor = Decimal("1.05")
        eligible_after_blocking = {
            "igst": total_claimed["igst"] - total_blocked["igst"] - total_aging_reversal["igst"],
            "cgst": total_claimed["cgst"] - total_blocked["cgst"] - total_aging_reversal["cgst"],
            "sgst": total_claimed["sgst"] - total_blocked["sgst"] - total_aging_reversal["sgst"],
        }

        for head in ("igst", "cgst", "sgst"):
            max_allowed = (total_available_2b[head] * limit_factor).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            if eligible_after_blocking[head] > max_allowed:
                excess = eligible_after_blocking[head] - max_allowed
                rule_36_4_result["applied"] = True
                rule_36_4_result[head] = {
                    "claimed": str(eligible_after_blocking[head]),
                    "gstr2b": str(total_available_2b[head]),
                    "max_105pct": str(max_allowed),
                    "excess_to_reverse": str(excess),
                }

    # Rule 42 — Common credit apportionment
    rule_42_result: dict[str, Any] = {"applied": False}
    if common_credit_details:
        t_taxable = _to_decimal(common_credit_details.get("turnover_taxable", 0))
        t_exempt = _to_decimal(common_credit_details.get("turnover_exempt", 0))
        t_total = _to_decimal(common_credit_details.get("turnover_total", 0))
        common_igst = _to_decimal(common_credit_details.get("common_igst", 0))
        common_cgst = _to_decimal(common_credit_details.get("common_cgst", 0))
        common_sgst = _to_decimal(common_credit_details.get("common_sgst", 0))

        if t_total > ZERO:
            taxable_ratio = (t_taxable / t_total).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            exempt_ratio = (t_exempt / t_total).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

            # ITC attributable to taxable supplies = Common credit * (taxable turnover / total turnover)
            eligible_common = {
                "igst": (common_igst * taxable_ratio).quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
                "cgst": (common_cgst * taxable_ratio).quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
                "sgst": (common_sgst * taxable_ratio).quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
            }
            reversal_common = {
                "igst": (common_igst * exempt_ratio).quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
                "cgst": (common_cgst * exempt_ratio).quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
                "sgst": (common_sgst * exempt_ratio).quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
            }

            rule_42_result = {
                "applied": True,
                "taxable_turnover_ratio": str(taxable_ratio),
                "exempt_turnover_ratio": str(exempt_ratio),
                "common_credit": {
                    "igst": str(common_igst), "cgst": str(common_cgst), "sgst": str(common_sgst),
                },
                "eligible_portion": {h: str(v) for h, v in eligible_common.items()},
                "reversal_portion": {h: str(v) for h, v in reversal_common.items()},
            }

    # Rule 43 — Capital goods ITC reversal (proportionate for mixed use)
    rule_43_result: dict[str, Any] = {"applied": False, "assets": []}
    if capital_goods_register:
        for asset in capital_goods_register:
            asset_id = str(asset.get("asset_id", ""))
            a_igst = _to_decimal(asset.get("igst", 0))
            a_cgst = _to_decimal(asset.get("cgst", 0))
            a_sgst = _to_decimal(asset.get("sgst", 0))
            useful_life = int(asset.get("useful_life_months", 60))
            taxable_use_pct = _to_decimal(asset.get("taxable_use_percentage", 100))

            total_credit = a_igst + a_cgst + a_sgst

            # Credit attributable to taxable use
            eligible_credit = (total_credit * taxable_use_pct / Decimal("100")).quantize(
                TWO_PLACES, rounding=ROUND_HALF_UP
            )
            # Monthly reversal for exempt use portion
            exempt_pct = Decimal("100") - taxable_use_pct
            monthly_reversal = ZERO
            if exempt_pct > ZERO and useful_life > 0:
                exempt_credit = total_credit - eligible_credit
                monthly_reversal = (exempt_credit / Decimal(str(useful_life))).quantize(
                    TWO_PLACES, rounding=ROUND_HALF_UP
                )

            rule_43_result["applied"] = True
            rule_43_result["assets"].append({
                "asset_id": asset_id,
                "invoice_no": str(asset.get("invoice_no", "")),
                "total_credit": str(total_credit),
                "taxable_use_percentage": str(taxable_use_pct),
                "eligible_credit": str(eligible_credit),
                "monthly_reversal": str(monthly_reversal),
                "useful_life_months": useful_life,
            })

    # Net eligible ITC
    net_eligible = {
        "igst": total_claimed["igst"] - total_blocked["igst"] - total_aging_reversal["igst"],
        "cgst": total_claimed["cgst"] - total_blocked["cgst"] - total_aging_reversal["cgst"],
        "sgst": total_claimed["sgst"] - total_blocked["sgst"] - total_aging_reversal["sgst"],
        "cess": total_claimed["cess"] - total_blocked["cess"] - total_aging_reversal["cess"],
    }

    return {
        "success": True,
        "summary": {
            "total_claimed": {h: str(v) for h, v in total_claimed.items()},
            "total_available_in_2b": {h: str(v) for h, v in total_available_2b.items()},
            "total_blocked_17_5": {h: str(v) for h, v in total_blocked.items()},
            "total_aging_reversal_16_2": {h: str(v) for h, v in total_aging_reversal.items()},
            "net_eligible": {h: str(v) for h, v in net_eligible.items()},
        },
        "matched_invoices": len(matched),
        "unmatched_invoices": len(unmatched),
        "blocked_invoices": len(blocked),
        "aging_reversals_count": len(aging_reversals),
        "details": {
            "matched": matched,
            "unmatched": unmatched,
            "blocked": blocked,
            "aging_reversals": aging_reversals,
        },
        "rule_36_4": rule_36_4_result,
        "rule_42_common_credit": rule_42_result,
        "rule_43_capital_goods": rule_43_result,
    }


# =====================================================================
# 8. UTILITY: E-INVOICE JSON GENERATION
# =====================================================================

def generate_einvoice_json(invoice: dict, supplier_details: dict) -> dict:
    """Generate e-Invoice JSON (IRN-ready) for invoices above Rs 5 crore threshold.

    Follows NIC e-Invoice schema version 1.1.

    Args:
        invoice: Single invoice dict
        supplier_details: Dict with legal_name, trade_name, gstin, address, city,
                         state_code, pincode, phone, email
    """
    inv_date = _parse_date(invoice.get("invoice_date"))
    taxable = _to_decimal(invoice.get("taxable_value", 0))
    igst = _to_decimal(invoice.get("igst_amount", 0))
    cgst = _to_decimal(invoice.get("cgst_amount", 0))
    sgst = _to_decimal(invoice.get("sgst_amount", 0))
    cess = _to_decimal(invoice.get("cess_amount", 0))
    total = taxable + igst + cgst + sgst + cess

    igst_rate = _to_decimal(invoice.get("igst_rate", 0))
    cgst_rate = _to_decimal(invoice.get("cgst_rate", 0))
    gst_rate = igst_rate if igst_rate > ZERO else (cgst_rate * 2)

    sup_state = str(supplier_details.get("state_code", ""))
    pos = str(invoice.get("place_of_supply", ""))[:2]
    if not pos:
        pos = sup_state

    inv_type_str = str(invoice.get("invoice_type", "")).upper()
    if inv_type_str in ("EXPORT", "EXPWP", "EXPWOP"):
        supply_type = "EXPWP" if igst > ZERO else "EXPWOP"
    elif inv_type_str in ("SEZ", "SEZWP", "SEZWOP"):
        supply_type = "SEZWP" if igst > ZERO else "SEZWOP"
    elif pos == sup_state:
        supply_type = "B2B"
    else:
        supply_type = "B2B"

    einvoice = {
        "Version": "1.1",
        "TranDtls": {
            "TaxSch": "GST",
            "SupTyp": supply_type,
            "RegRev": "N",
            "IgstOnIntra": "N",
        },
        "DocDtls": {
            "Typ": "INV",
            "No": str(invoice.get("invoice_no", "")),
            "Dt": inv_date.strftime("%d/%m/%Y") if inv_date else "",
        },
        "SellerDtls": {
            "Gstin": str(supplier_details.get("gstin", "")),
            "LglNm": str(supplier_details.get("legal_name", "")),
            "TrdNm": str(supplier_details.get("trade_name", "")),
            "Addr1": str(supplier_details.get("address", "")),
            "Loc": str(supplier_details.get("city", "")),
            "Pin": int(supplier_details.get("pincode", 0)),
            "Stcd": sup_state,
        },
        "BuyerDtls": {
            "Gstin": str(invoice.get("customer_gstin", "")).upper(),
            "LglNm": str(invoice.get("customer_name", "")),
            "Pos": pos,
            "Addr1": str(invoice.get("customer_address", "")),
            "Loc": str(invoice.get("customer_city", "")),
            "Pin": int(invoice.get("customer_pincode", 0)) if invoice.get("customer_pincode") else 0,
            "Stcd": str(invoice.get("customer_gstin", ""))[:2] if invoice.get("customer_gstin") else "",
        },
        "ItemList": [{
            "SlNo": "1",
            "IsServc": "Y" if str(invoice.get("hsn_code", "")).startswith("99") else "N",
            "HsnCd": str(invoice.get("hsn_code", "")),
            "Qty": 1,
            "Unit": "NOS",
            "UnitPrice": str(taxable),
            "TotAmt": str(taxable),
            "AssAmt": str(taxable),
            "GstRt": str(gst_rate),
            "IgstAmt": str(igst),
            "CgstAmt": str(cgst),
            "SgstAmt": str(sgst),
            "CesAmt": str(cess),
            "TotItemVal": str(total),
        }],
        "ValDtls": {
            "AssVal": str(taxable),
            "IgstVal": str(igst),
            "CgstVal": str(cgst),
            "SgstVal": str(sgst),
            "CesVal": str(cess),
            "TotInvVal": str(total),
        },
    }

    return einvoice


# =====================================================================
# 9. GST RETURN FILING SUMMARY
# =====================================================================

async def generate_filing_summary(
    gstr1_result: dict,
    gstr3b_result: dict,
    return_period: str,
    supplier_gstin: str,
) -> dict:
    """Generate a consolidated filing summary for CA review.

    Combines GSTR-1 and GSTR-3B results into a single review document
    with cross-checks and flags.
    """
    flags: list[dict] = []

    # Cross-check GSTR-1 totals vs GSTR-3B Table 3.1
    gstr1_summary = gstr1_result.get("summary", {})
    table_3_1 = gstr3b_result.get("table_3_1", {})

    gstr1_taxable = _to_decimal(gstr1_summary.get("total_taxable_value", 0))
    gstr3b_taxable = _to_decimal(table_3_1.get("a", {}).get("taxable", 0))

    if gstr1_taxable > ZERO and abs(gstr1_taxable - gstr3b_taxable) > Decimal("100"):
        flags.append({
            "severity": "HIGH",
            "check": "GSTR-1 vs GSTR-3B taxable value mismatch",
            "gstr1_value": str(gstr1_taxable),
            "gstr3b_value": str(gstr3b_taxable),
            "difference": str(abs(gstr1_taxable - gstr3b_taxable)),
            "action": "Reconcile outward supply figures before filing",
        })

    # Check for high cash payment
    payment = gstr3b_result.get("table_6_1_payment", {}).get("cash_payment", {})
    total_cash = _to_decimal(payment.get("total", 0))
    if total_cash > Decimal("100000"):
        flags.append({
            "severity": "INFO",
            "check": "Significant cash payment required",
            "amount": str(total_cash),
            "action": "Ensure sufficient balance in electronic cash ledger before filing",
        })

    # Check for Rule 36(4) restriction
    itc_data = gstr3b_result.get("table_4_itc", {})
    rule_36_4 = itc_data.get("rule_36_4", {})
    if rule_36_4.get("applied"):
        flags.append({
            "severity": "HIGH",
            "check": "Rule 36(4) ITC restriction applied",
            "details": rule_36_4.get("details", {}),
            "action": "ITC claimed exceeds 105% of GSTR-2B. Follow up with suppliers for return filing.",
        })

    # Check for blocked ITC
    blocked = itc_data.get("blocked_details", [])
    if blocked:
        total_blocked_amt = sum(_to_decimal(b.get("amount", 0)) for b in blocked)
        flags.append({
            "severity": "MEDIUM",
            "check": f"Section 17(5) blocked ITC: {len(blocked)} invoices",
            "total_blocked": str(total_blocked_amt),
            "action": "Verify blocked ITC classification; some may qualify for exceptions",
        })

    # Filing deadline reminder
    # Parse return_period (MMYYYY)
    if len(return_period) == 6:
        rp_month = int(return_period[:2])
        rp_year = int(return_period[2:])

        # GSTR-1 due: 11th of next month
        gstr1_due_month = rp_month + 1
        gstr1_due_year = rp_year
        if gstr1_due_month > 12:
            gstr1_due_month = 1
            gstr1_due_year += 1
        gstr1_due = date(gstr1_due_year, gstr1_due_month, 11)

        # GSTR-3B due: 20th of next month
        gstr3b_due = date(gstr1_due_year, gstr1_due_month, 20)
    else:
        gstr1_due = None
        gstr3b_due = None

    return {
        "return_period": return_period,
        "gstin": supplier_gstin,
        "gstr1_summary": gstr1_summary,
        "gstr3b_payment": payment,
        "flags": flags,
        "flag_count": {"high": sum(1 for f in flags if f["severity"] == "HIGH"),
                       "medium": sum(1 for f in flags if f["severity"] == "MEDIUM"),
                       "info": sum(1 for f in flags if f["severity"] == "INFO")},
        "deadlines": {
            "gstr1_due": gstr1_due.isoformat() if gstr1_due else None,
            "gstr3b_due": gstr3b_due.isoformat() if gstr3b_due else None,
        },
        "late_fee": {
            "gstr1": "Rs 50/day (Rs 20/day for nil return), max Rs 5,000 per return",
            "gstr3b": "Rs 50/day + 18% p.a. interest on outstanding tax from due date",
        },
    }


# =====================================================================
# 10. INTEREST AND LATE FEE CALCULATOR
# =====================================================================

def calculate_gst_interest(
    tax_amount: str | Decimal,
    due_date: str | date,
    payment_date: str | date,
    interest_rate: Decimal = Decimal("18"),
) -> dict:
    """Calculate interest on delayed GST payment under Section 50.

    Section 50(1): 18% p.a. on net tax liability (after ITC).
    Section 50(3): 24% p.a. on wrongly availed and utilized ITC.
    """
    tax = _to_decimal(tax_amount)
    if isinstance(due_date, str):
        due = _parse_date(due_date)
    else:
        due = due_date
    if isinstance(payment_date, str):
        pay = _parse_date(payment_date)
    else:
        pay = payment_date

    if not due or not pay:
        return {"error": "Invalid date(s) provided"}

    if pay <= due:
        return {"interest": "0.00", "days_delayed": 0, "message": "No delay — no interest applicable"}

    days_delayed = (pay - due).days
    # Interest = Principal * Rate * Days / 365
    interest = (tax * interest_rate * Decimal(str(days_delayed)) / (Decimal("100") * Decimal("365"))).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )

    return {
        "tax_amount": str(tax),
        "due_date": due.isoformat(),
        "payment_date": pay.isoformat(),
        "days_delayed": days_delayed,
        "interest_rate": f"{interest_rate}% p.a.",
        "interest_amount": str(interest),
        "section": "Section 50(1) CGST Act" if interest_rate == Decimal("18") else "Section 50(3) CGST Act",
        "total_payable": str(tax + interest),
    }


def calculate_late_fee(
    return_type: str,
    due_date: str | date,
    filing_date: str | date,
    is_nil_return: bool = False,
    has_tax_liability: bool = True,
) -> dict:
    """Calculate late fee for delayed GST return filing.

    GSTR-1/3B: Rs 50/day (Rs 25 CGST + Rs 25 SGST), max Rs 5,000 per return
    Nil return: Rs 20/day (Rs 10 CGST + Rs 10 SGST)
    """
    if isinstance(due_date, str):
        due = _parse_date(due_date)
    else:
        due = due_date
    if isinstance(filing_date, str):
        filed = _parse_date(filing_date)
    else:
        filed = filing_date

    if not due or not filed:
        return {"error": "Invalid date(s) provided"}

    if filed <= due:
        return {"late_fee": "0.00", "days_delayed": 0, "message": "Filed on time"}

    days = (filed - due).days

    if is_nil_return:
        daily_cgst = Decimal("10")
        daily_sgst = Decimal("10")
        daily_total = Decimal("20")
        max_fee = Decimal("5000")
    else:
        daily_cgst = Decimal("25")
        daily_sgst = Decimal("25")
        daily_total = Decimal("50")
        max_fee = Decimal("5000")

    raw_fee = daily_total * Decimal(str(days))
    actual_fee = min(raw_fee, max_fee)
    cgst_fee = min(daily_cgst * Decimal(str(days)), max_fee / 2)
    sgst_fee = min(daily_sgst * Decimal(str(days)), max_fee / 2)

    return {
        "return_type": return_type,
        "due_date": due.isoformat(),
        "filing_date": filed.isoformat(),
        "days_delayed": days,
        "is_nil_return": is_nil_return,
        "daily_fee": str(daily_total),
        "raw_late_fee": str(raw_fee),
        "capped_late_fee": str(actual_fee),
        "cgst_component": str(min(cgst_fee, max_fee / 2)),
        "sgst_component": str(min(sgst_fee, max_fee / 2)),
        "max_cap": str(max_fee),
    }


# =====================================================================
# 11. ANNUAL RETURN (GSTR-9) HELPER
# =====================================================================

async def compute_annual_summary(monthly_gstr3b_data: list[dict]) -> dict:
    """Aggregate monthly GSTR-3B data into annual totals for GSTR-9 preparation.

    Args:
        monthly_gstr3b_data: List of GSTR-3B results (output from compute_gstr3b)
                              for 12 months of a financial year.

    Returns:
        Annual aggregated figures for GSTR-9 tables.
    """
    annual = {
        "outward_taxable": {"igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cess": ZERO},
        "outward_zero_rated": {"igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cess": ZERO},
        "outward_exempt_nil": {"igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cess": ZERO},
        "total_itc_availed": {"igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cess": ZERO},
        "total_itc_reversed": {"igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cess": ZERO},
        "total_tax_paid_cash": {"igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cess": ZERO},
        "total_tax_paid_itc": {"igst": ZERO, "cgst": ZERO, "sgst": ZERO, "cess": ZERO},
        "months_covered": 0,
    }

    for m3b in monthly_gstr3b_data:
        if not m3b.get("success"):
            continue

        annual["months_covered"] += 1

        # Table 3.1 aggregation
        t31 = m3b.get("table_3_1", {})
        for head in ("igst", "cgst", "sgst", "cess"):
            annual["outward_taxable"][head] += _to_decimal(t31.get("a", {}).get(head, 0))
            annual["outward_zero_rated"][head] += _to_decimal(t31.get("b", {}).get(head, 0))
            annual["outward_exempt_nil"][head] += _to_decimal(t31.get("c", {}).get(head, 0))

        # Table 4 ITC aggregation
        t4 = m3b.get("table_4_itc", {})
        for head in ("igst", "cgst", "sgst", "cess"):
            annual["total_itc_availed"][head] += _to_decimal(t4.get("A_eligible_itc", {}).get(head, 0))
            annual["total_itc_reversed"][head] += _to_decimal(t4.get("B_reversed_rule_42_43", {}).get(head, 0))

        # Table 6.1 payment aggregation
        t61 = m3b.get("table_6_1_payment", {})
        cash = t61.get("cash_payment", {})
        for head in ("igst", "cgst", "sgst", "cess"):
            annual["total_tax_paid_cash"][head] += _to_decimal(cash.get(head, 0))

    # Serialize
    serialized: dict[str, Any] = {"months_covered": annual["months_covered"]}
    for key in annual:
        if key == "months_covered":
            continue
        serialized[key] = {h: str(v) for h, v in annual[key].items()}

    serialized["total_turnover"] = str(
        sum(annual["outward_taxable"][h] for h in ("igst", "cgst", "sgst"))
        + sum(annual["outward_zero_rated"][h] for h in ("igst", "cgst", "sgst"))
        + sum(annual["outward_exempt_nil"][h] for h in ("igst", "cgst", "sgst"))
    )

    return serialized


# =====================================================================
# 12. REVERSE CHARGE MECHANISM (RCM) HELPER
# =====================================================================

# Services/supplies under RCM (Section 9(3) / Notification 13/2017)
RCM_SUPPLIES: list[dict[str, str]] = [
    {"category": "GTA", "desc": "Goods Transport Agency (freight)", "sac": "9965", "rate": "5"},
    {"category": "Legal", "desc": "Legal services by individual advocate", "sac": "9982", "rate": "18"},
    {"category": "Sponsorship", "desc": "Sponsorship services", "sac": "9983", "rate": "18"},
    {"category": "Govt", "desc": "Services by Government/local authority", "sac": "9991", "rate": "18"},
    {"category": "Director", "desc": "Services by director (not employee)", "sac": "9983", "rate": "18"},
    {"category": "Insurance", "desc": "Insurance agent services", "sac": "9971", "rate": "18"},
    {"category": "Recovery", "desc": "Recovery agent services", "sac": "9983", "rate": "18"},
    {"category": "Author", "desc": "Services by author/music composer", "sac": "9983", "rate": "18"},
    {"category": "Security", "desc": "Security services by individual", "sac": "998521", "rate": "18"},
    {"category": "Renting", "desc": "Renting of motor vehicle (if specific conditions)", "sac": "9966", "rate": "5"},
    {"category": "Unregistered", "desc": "Any supply from unregistered person (for notified goods)", "sac": "", "rate": ""},
]


def check_rcm_applicability(description: str, supplier_type: str = "") -> dict:
    """Check if a supply falls under Reverse Charge Mechanism.

    Args:
        description: Description of the service/supply
        supplier_type: 'registered', 'unregistered', 'individual', 'gta', etc.
    """
    desc_lower = description.lower()
    sup_lower = supplier_type.lower()
    matches: list[dict] = []

    for rcm in RCM_SUPPLIES:
        keywords = rcm["category"].lower().split()
        if any(kw in desc_lower for kw in keywords):
            matches.append(rcm)
        elif rcm["category"].lower() == sup_lower:
            matches.append(rcm)

    # Special check: GTA
    if any(kw in desc_lower for kw in ("freight", "transport", "gta", "lorry", "truck")):
        if not any(m["category"] == "GTA" for m in matches):
            matches.append(next(r for r in RCM_SUPPLIES if r["category"] == "GTA"))

    # Legal services from advocate
    if any(kw in desc_lower for kw in ("advocate", "lawyer", "legal", "counsel")):
        if sup_lower in ("individual", "unregistered", ""):
            if not any(m["category"] == "Legal" for m in matches):
                matches.append(next(r for r in RCM_SUPPLIES if r["category"] == "Legal"))

    return {
        "rcm_applicable": len(matches) > 0,
        "matches": matches,
        "note": (
            "RCM supplies: recipient is liable to pay GST. "
            "ITC on RCM is available subject to Section 16 conditions."
        ) if matches else "No RCM applicability detected based on description.",
    }


# =====================================================================
# 13. CONVENIENCE: FULL PIPELINE
# =====================================================================

async def process_gst_return(
    invoice_file_bytes: bytes,
    file_type: str,
    supplier_gstin: str,
    return_period: str,
    purchase_register: Optional[list[dict]] = None,
    gstr2b_data: Optional[list[dict]] = None,
    payment_ledger: Optional[list[dict]] = None,
) -> dict:
    """End-to-end GST return computation pipeline.

    1. Parse invoice register
    2. Generate GSTR-1
    3. Compute GSTR-3B (if purchase register provided)
    4. Track ITC (if GSTR-2B data provided)
    5. Generate filing summary

    Returns consolidated result.
    """
    logger.info("Starting GST return processing for GSTIN %s, period %s", supplier_gstin, return_period)

    # Step 1: Parse invoices
    parsed = await parse_invoice_register(invoice_file_bytes, file_type, supplier_gstin)
    if not parsed.get("success"):
        return {"success": False, "stage": "parsing", "error": parsed.get("error", "Unknown parsing error")}

    if parsed.get("validation_errors"):
        logger.warning("Invoice validation found %d errors", len(parsed["validation_errors"]))

    # Step 2: Generate GSTR-1
    gstr1_result = await generate_gstr1(parsed["invoices"], supplier_gstin, return_period)
    if not gstr1_result.get("success"):
        return {"success": False, "stage": "gstr1", "error": gstr1_result.get("error", "GSTR-1 generation failed")}

    result: dict[str, Any] = {
        "success": True,
        "gstr1": gstr1_result,
        "invoice_validation_errors": parsed.get("validation_errors", []),
    }

    # Step 3: GSTR-3B
    if purchase_register is not None:
        gstr3b_result = await compute_gstr3b(
            gstr1_data=gstr1_result["gstr1"],
            purchase_register=purchase_register,
            gstr2b_data=gstr2b_data,
        )
        result["gstr3b"] = gstr3b_result

        # Step 4: ITC Tracker
        if gstr2b_data:
            itc_result = await track_itc(
                purchase_register=purchase_register,
                gstr2b_data=gstr2b_data,
                payment_ledger=payment_ledger,
            )
            result["itc_tracker"] = itc_result

        # Step 5: Filing summary
        summary = await generate_filing_summary(
            gstr1_result=gstr1_result,
            gstr3b_result=gstr3b_result,
            return_period=return_period,
            supplier_gstin=supplier_gstin,
        )
        result["filing_summary"] = summary
    else:
        logger.info("No purchase register provided — skipping GSTR-3B and ITC computation")

    logger.info("GST return processing complete for %s", supplier_gstin)
    return result
