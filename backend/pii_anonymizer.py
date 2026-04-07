import re
import logging

logger = logging.getLogger(__name__)

# Indian-specific PII patterns
PII_PATTERNS = [
    # Aadhaar Number (12 digits, often with spaces)
    (r'\b\d{4}\s?\d{4}\s?\d{4}\b', '[AADHAAR_REDACTED]', 'Aadhaar'),
    # PAN Number (ABCDE1234F format)
    (r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', '[PAN_REDACTED]', 'PAN'),
    # GSTIN (15 char alphanumeric)
    (r'\b\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][A-Z\d]\b', '[GSTIN_REDACTED]', 'GSTIN'),
    # Indian Phone Numbers
    (r'\b(?:\+91[\-\s]?)?[6-9]\d{9}\b', '[PHONE_REDACTED]', 'Phone'),
    # Email
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', 'Email'),
    # Bank Account Numbers (9-18 digits)
    (r'\b\d{9,18}\b', '[BANK_ACCT_REDACTED]', 'BankAccount'),
    # IFSC Code
    (r'\b[A-Z]{4}0[A-Z0-9]{6}\b', '[IFSC_REDACTED]', 'IFSC'),
    # Indian Passport
    (r'\b[A-Z]\d{7}\b', '[PASSPORT_REDACTED]', 'Passport'),
    # CIN (Company Identification Number)
    (r'\b[UL]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b', '[CIN_REDACTED]', 'CIN'),
    # DIN (Director Identification Number) 
    (r'\b\d{8}\b', None, 'DIN'),  # Too broad, skip auto-redact
]

# Sensitive Indian legal terms that should be flagged but not redacted
SENSITIVE_CONTEXT_KEYWORDS = [
    'accused', 'complainant', 'victim', 'witness', 'minor', 'juvenile',
    'rape', 'dowry', 'domestic violence', 'sexual harassment',
    'hiv', 'aids', 'mental health', 'psychiatric'
]


def anonymize_text(text: str, redact_level: str = "standard") -> dict:
    """
    Anonymize PII from text before it hits the LLM.
    
    Args:
        text: The raw text to anonymize
        redact_level: "standard" (PAN, Aadhaar, Phone, Email) or "aggressive" (all patterns)
    
    Returns:
        dict with 'anonymized_text', 'redactions' list, and 'sensitivity_flags'
    """
    redactions = []
    anonymized = text
    
    standard_types = {'Aadhaar', 'PAN', 'Phone', 'Email', 'GSTIN'}
    
    for pattern, replacement, pii_type in PII_PATTERNS:
        if replacement is None:
            continue
        if redact_level == "standard" and pii_type not in standard_types:
            continue
            
        matches = list(re.finditer(pattern, anonymized))
        for match in reversed(matches):  # Reverse to preserve positions
            original = match.group()
            redactions.append({
                "type": pii_type,
                "original_masked": original[:3] + "***",  # Partial for audit log
                "position": match.start(),
            })
            anonymized = anonymized[:match.start()] + replacement + anonymized[match.end():]
    
    # Sensitivity flags
    text_lower = text.lower()
    sensitivity_flags = [kw for kw in SENSITIVE_CONTEXT_KEYWORDS if kw in text_lower]
    
    return {
        "anonymized_text": anonymized,
        "redactions_count": len(redactions),
        "redactions": redactions,
        "sensitivity_flags": sensitivity_flags,
        "redact_level": redact_level
    }


def deanonymize_text(anonymized_text: str, redaction_map: dict) -> str:
    """Reverse anonymization using stored mapping (for export purposes only)."""
    result = anonymized_text
    for placeholder, original in redaction_map.items():
        result = result.replace(placeholder, original)
    return result
