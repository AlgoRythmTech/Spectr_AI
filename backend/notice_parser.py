import re

class NoticeParserEngine:
    def __init__(self):
        # Common Regex Patterns for Indian Tax Notices
        self.patterns = {
            "section": r"(?i)under\s+section\s+([0-9a-zA-Z]+)(?:\s+of\s+the\s+([A-Za-z\s]+Act))?",
            "demand": r"(?i)(?:demand|penalty|tax|amount)\s+(?:of\s+)?(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{2})?)",
            "fin_year": r"(?i)(?:fy|financial\s+year|for\s+the\s+year)\s+(\d{4}-\d{2,4})",
            "asmt_10": r"(?i)form\s+gst\s+asmt-10",
            "drc_01": r"(?i)form\s+gst\s+drc-01"
        }

    def parse_notice(self, notice_text: str) -> dict:
        """Parses raw text from a PDF notice to extract critical metadata."""
        
        extracted = {
            "notice_type": "Unknown",
            "statute": "Unknown Act",
            "section": None,
            "financial_year": None,
            "demand_amount": None,
            "urgency": "High",
            "drafting_prompt": ""
        }

        # 1. Detect Notice Type
        if re.search(self.patterns["asmt_10"], notice_text):
            extracted["notice_type"] = "Scrutiny Notice (ASMT-10)"
            extracted["statute"] = "CGST Act, 2017"
        elif re.search(self.patterns["drc_01"], notice_text):
            extracted["notice_type"] = "Show Cause Notice (DRC-01)"
            extracted["statute"] = "CGST Act, 2017"
        elif "148A" in notice_text.upper():
            extracted["notice_type"] = "Income Escaping Assessment (148A)"
            extracted["statute"] = "Income Tax Act, 1961"

        # 2. Extract Section
        sec_match = re.search(self.patterns["section"], notice_text)
        if sec_match:
            extracted["section"] = sec_match.group(1).upper()
            if sec_match.group(2):
                extracted["statute"] = sec_match.group(2).strip()

        # 3. Extract Demand Amount
        demand_match = re.search(self.patterns["demand"], notice_text)
        if demand_match:
            # Clean up commas
            clean_amt = demand_match.group(1).replace(",", "")
            try:
                extracted["demand_amount"] = float(clean_amt)
            except:
                extracted["demand_amount"] = demand_match.group(1)

        # 4. Extract FY
        fy_match = re.search(self.patterns["fin_year"], notice_text)
        if fy_match:
            extracted["financial_year"] = fy_match.group(1)

        # 5. Generate AI Drafting Prompt
        if extracted["demand_amount"]:
            extracted["drafting_prompt"] = (
                f"I have received a {extracted['notice_type']} under Section {extracted['section']} "
                f"of the {extracted['statute']} for FY {extracted['financial_year']}. "
                f"The department is demanding a tax/penalty of Rs. {extracted['demand_amount']}. "
                f"Draft a formal, structured response to the Adjudicating Authority denying the liability, "
                f"citing relevant Supreme Court / Tribunal precedents favoring the taxpayer, and requesting a personal hearing."
            )
        else:
            extracted["drafting_prompt"] = (
                f"Draft a formal reply to this {extracted['notice_type']} under Section {extracted['section']} "
                f"of the {extracted['statute']}. Address the allegations raised in the notice."
            )

        return extracted
