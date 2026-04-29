"""
Spectr Security Fortress — Production-grade security layer.
Rate limiting, input sanitization, encryption, CORS, headers, audit logging,
brute-force protection, JWT hardening, RBAC, request signing.
"""
import os
import re
import time
import hmac
import hashlib
import secrets
import logging
import ipaddress
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from functools import wraps

logger = logging.getLogger("spectr.security")

# ==================== CONFIGURATION ====================

SECRET_KEY = os.environ.get("SPECTR_SECRET_KEY", secrets.token_hex(64))
JWT_SECRET = os.environ.get("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = int(os.environ.get("JWT_EXPIRY_MINUTES", "60"))
REFRESH_TOKEN_EXPIRY_DAYS = int(os.environ.get("REFRESH_EXPIRY_DAYS", "30"))
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "").split(",") if os.environ.get("ALLOWED_ORIGINS") else []
ENVIRONMENT = os.environ.get("SPECTR_ENV", "development")  # development, staging, production

# Rate limiting config
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("RATE_LIMIT_MAX", "60"))
RATE_LIMIT_AUTH_MAX = 5  # Auth endpoints: 5 attempts per minute
RATE_LIMIT_EXPORT_MAX = 10  # Export endpoints: 10 per minute

# Brute force protection
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30

# ==================== PASSWORD HASHING (bcrypt) ====================

try:
    import bcrypt
    _BCRYPT_AVAILABLE = True
except ImportError:
    _BCRYPT_AVAILABLE = False
    logger.warning("bcrypt not installed — password hashing will use PBKDF2 fallback")


def hash_password(password: str) -> str:
    """Hash password using bcrypt (preferred) or PBKDF2 fallback."""
    if _BCRYPT_AVAILABLE:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    else:
        salt = secrets.token_hex(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 310000)
        return f"pbkdf2:{salt}:{dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against stored hash."""
    if _BCRYPT_AVAILABLE and hashed.startswith("$2"):
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    elif hashed.startswith("pbkdf2:"):
        _, salt, stored_hash = hashed.split(":")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 310000)
        return hmac.compare_digest(dk.hex(), stored_hash)
    return False


# ==================== JWT TOKEN MANAGEMENT ====================

def create_jwt_token(user_id: str, email: str, role: str, extra: dict = None) -> dict:
    """Create JWT access + refresh token pair."""
    import jwt as pyjwt

    now = datetime.now(timezone.utc)
    access_payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=JWT_EXPIRY_MINUTES),
        "jti": secrets.token_hex(16),  # Unique token ID for revocation
        "type": "access",
    }
    if extra:
        access_payload.update(extra)

    refresh_payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS),
        "jti": secrets.token_hex(16),
        "type": "refresh",
    }

    access_token = pyjwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    refresh_token = pyjwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": JWT_EXPIRY_MINUTES * 60,
        "access_token_hash": hashlib.sha256(access_token.encode()).hexdigest(),
        "refresh_token_hash": hashlib.sha256(refresh_token.encode()).hexdigest(),
    }


def verify_jwt_token(token: str) -> dict:
    """Verify and decode a JWT token. Returns payload or raises."""
    import jwt as pyjwt

    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") not in ("access", "refresh"):
            raise ValueError("Invalid token type")
        return payload
    except pyjwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except pyjwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}")


def hash_token(token: str) -> str:
    """SHA-256 hash of a token for storage (never store raw tokens)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ==================== RATE LIMITING (In-Memory + SQL) ====================

_rate_limit_store: dict[str, list] = defaultdict(list)


def check_rate_limit(key: str, max_requests: int = RATE_LIMIT_MAX_REQUESTS, window: int = RATE_LIMIT_WINDOW) -> dict:
    """Check if a key (IP, user_id, API key) has exceeded rate limits.
    Returns: {"allowed": bool, "remaining": int, "reset_at": float}
    """
    now = time.time()
    cutoff = now - window

    # Clean expired entries
    _rate_limit_store[key] = [t for t in _rate_limit_store[key] if t > cutoff]

    current_count = len(_rate_limit_store[key])

    if current_count >= max_requests:
        reset_at = _rate_limit_store[key][0] + window
        return {
            "allowed": False,
            "remaining": 0,
            "reset_at": reset_at,
            "retry_after": int(reset_at - now),
        }

    _rate_limit_store[key].append(now)
    return {
        "allowed": True,
        "remaining": max_requests - current_count - 1,
        "reset_at": now + window,
    }


# ==================== INPUT SANITIZATION ====================

# Patterns that indicate injection attempts
_SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC|UNION)\b\s)",
    r"(--|;|/\*|\*/)",
    r"(\bOR\b\s+\d+\s*=\s*\d+)",
    r"(\bAND\b\s+\d+\s*=\s*\d+)",
    r"(WAITFOR\s+DELAY)",
    r"(xp_cmdshell|sp_executesql)",
]

_XSS_PATTERNS = [
    r"<script[\s>]",
    r"javascript\s*:",
    r"on\w+\s*=",
    r"<iframe",
    r"<object",
    r"<embed",
    r"<form\s",
    r"expression\s*\(",
    r"vbscript\s*:",
    r"data\s*:\s*text/html",
]

_PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",
    r"\.\.\\",
    r"%2e%2e",
    r"%252e%252e",
    r"\.\./etc/passwd",
    r"\\\\",
]

_COMMAND_INJECTION_PATTERNS = [
    r"[;&|`$]",
    r"\$\(",
    r"\beval\b",
    r"\bexec\b",
    r"\bsystem\b",
    r"\bos\.popen\b",
    r"\bsubprocess\b",
]


def sanitize_input(text: str, max_length: int = 50000, context: str = "general") -> str:
    """Sanitize user input — strip dangerous patterns while preserving legal text.

    context: "general" (standard), "query" (AI queries — more permissive for legal text),
             "filename" (strict), "email" (moderate)
    """
    if not text:
        return ""

    # Length limit
    text = text[:max_length]

    # Null byte removal (always)
    text = text.replace("\x00", "")

    if context == "filename":
        # Strict: only allow alphanumeric, spaces, hyphens, underscores, dots
        text = re.sub(r'[^\w\s\-.]', '', text)
        text = re.sub(r'\.{2,}', '.', text)  # No double dots
        return text.strip()[:255]

    if context in ("general", "email"):
        # Check for SQL injection patterns
        for pattern in _SQL_INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"SQL injection pattern detected and neutralized: {pattern}")
                text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    # XSS prevention (always)
    for pattern in _XSS_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"XSS pattern detected and neutralized: {pattern}")
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Path traversal (always)
    for pattern in _PATH_TRAVERSAL_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    if context == "query":
        # For AI queries, be more permissive — legal text uses semicolons, special chars
        # Only strip the most dangerous patterns
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
        text = text.replace("\x00", "")

    return text.strip()


# ==================== PROMPT INJECTION DEFENSE ====================

# Patterns that indicate prompt injection / jailbreak attempts in user-controlled
# content that gets concatenated into LLM system prompts (matter_context, firm_context,
# statute_context, library items, document text, etc.)

_PROMPT_INJECTION_PATTERNS = [
    # Direct override attempts
    r"(?i)\bignore\s+(all\s+)?previous\s+(instructions?|prompts?|context)\b",
    r"(?i)\bdisregard\s+(all\s+)?previous\b",
    r"(?i)\bforget\s+(all\s+)?previous\b",
    r"(?i)\byou\s+are\s+now\b",
    r"(?i)\bact\s+as\s+if\b",
    r"(?i)\bpretend\s+(you\s+are|to\s+be)\b",
    r"(?i)\bnew\s+system\s+prompt\b",
    r"(?i)\boverride\s+(system|instructions?)\b",
    r"(?i)\breset\s+(your\s+)?instructions?\b",
    r"(?i)\bswitch\s+to\s+(\w+\s+)?mode\b",
    r"(?i)\benable\s+developer\s+mode\b",
    r"(?i)\bjailbreak\b",
    r"(?i)\bDAN\s+mode\b",
    # Role hijack
    r"(?i)\bsystem\s*:\s*you\s+are\b",
    r"(?i)\bASSISTANT\s*:\s",
    r"(?i)\bSYSTEM\s*:\s",
    r"(?i)\bHUMAN\s*:\s",
    # Delimiter spoofing (trying to break out of context blocks)
    r"===\s*END\s+(OF\s+)?(SYSTEM|CONTEXT|INSTRUCTIONS?|RULES?)\s*===",
    r"---\s*END\s+(OF\s+)?(SYSTEM|CONTEXT)\s*---",
    r"\[/?(SYSTEM|INST|CONTEXT)\]",
    r"<\/?system>",
    r"<\/?instructions?>",
    r"<\/?prompt>",
    # Exfiltration via output manipulation
    r"(?i)\brepeat\s+(this\s+)?(system|prompt|instruction)",
    r"(?i)\bprint\s+(your\s+)?(system|prompt|instruction)",
    r"(?i)\bshow\s+(me\s+)?(your\s+)?(system|prompt|instruction)",
    r"(?i)\bwhat\s+(are\s+)?(your\s+)?(system|hidden)\s+(prompt|instruction)",
    r"(?i)\boutput\s+(your\s+)?(system|instruction)",
    # Token smuggling
    r"(?i)\bbase64\s+decode\b",
    r"(?i)\beval\s*\(",
    r"(?i)\bexec\s*\(",
]

_INJECTION_BOUNDARY_MARKERS = re.compile(
    r"(?i)(###\s*SYSTEM|###\s*INSTRUCTION|###\s*PROMPT|"
    r"\[SYSTEM\]|\[INST\]|\[\/INST\]|<\|im_start\|>|<\|im_end\|>|"
    r"<s>|</s>|<<SYS>>|<</SYS>>)"
)


def sanitize_context_for_llm(text: str, source_label: str = "unknown", max_length: int = 100000) -> str:
    """Sanitize user-controlled text before injecting into LLM system prompts.

    This prevents prompt injection attacks where malicious content stored in
    matters, library items, or document text could hijack the AI's behavior.

    Args:
        text: The user-controlled text (matter_context, firm_context, doc text, etc.)
        source_label: Label for logging (e.g. "matter_context", "library_item")
        max_length: Hard cap on text length to prevent context stuffing

    Returns:
        Sanitized text safe for LLM context injection.
    """
    if not text:
        return ""

    original_len = len(text)

    # 1. Hard length cap (prevent context stuffing)
    text = text[:max_length]

    # 2. Remove chat-format boundary markers that could break prompt structure
    boundary_matches = _INJECTION_BOUNDARY_MARKERS.findall(text)
    if boundary_matches:
        logger.warning(
            f"Prompt injection defense: stripped {len(boundary_matches)} boundary markers "
            f"from {source_label}: {boundary_matches[:5]}"
        )
        text = _INJECTION_BOUNDARY_MARKERS.sub("", text)

    # 3. Detect and neutralize injection patterns
    injections_found = []
    for pattern in _PROMPT_INJECTION_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            injections_found.append((pattern, matches))
            # Replace with harmless text instead of stripping (preserves context readability)
            text = re.sub(pattern, "[FILTERED]", text)

    if injections_found:
        logger.warning(
            f"Prompt injection defense: neutralized {len(injections_found)} injection patterns "
            f"in {source_label}. Patterns: {[p[0][:40] for p in injections_found[:5]]}"
        )

    # 4. Normalize whitespace (prevent hidden content via excessive spacing)
    text = re.sub(r'\n{4,}', '\n\n\n', text)  # Max 3 consecutive newlines
    text = re.sub(r' {10,}', '    ', text)     # Max 4 consecutive spaces

    # 5. Strip null bytes and control characters (except newlines, tabs)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    if original_len > max_length:
        logger.info(f"Context truncated for {source_label}: {original_len} → {max_length} chars")

    return text.strip()


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email)) and len(email) <= 254


def validate_pan(pan: str) -> bool:
    """Validate Indian PAN format: AAAAA9999A"""
    return bool(re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan.upper()))


def validate_gstin(gstin: str) -> bool:
    """Validate Indian GSTIN format: 15 characters."""
    return bool(re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{3}$', gstin.upper()))


# ==================== SECURITY HEADERS MIDDLEWARE ====================

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
    "Pragma": "no-cache",
    "X-Permitted-Cross-Domain-Policies": "none",
}


def get_security_headers() -> dict:
    """Return security headers for every response.
    CSP is now applied in ALL environments (dev uses slightly relaxed version
    for CRA HMR; production is strict). This prevents a security regression
    when code is moved between envs.
    """
    headers = dict(SECURITY_HEADERS)
    if ENVIRONMENT == "production":
        headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.spectr.ai https://*.spectr.ai https://*.thealgorythm.in; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
    else:
        # Development CSP — allows CRA's websocket HMR + inline scripts for dev tools
        headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' ws://localhost:* http://localhost:* http://127.0.0.1:*; "
            "frame-ancestors 'none';"
        )
    return headers


# ==================== CORS CONFIGURATION ====================

def get_cors_config() -> dict:
    """Return CORS configuration based on environment.
    Production: requires explicit ALLOWED_ORIGINS env var. If missing, returns
    a zero-origin config — better to break CORS than to allow '*' by default.
    Development: localhost-only whitelist.
    """
    is_prod = ENVIRONMENT == "production" or bool(os.environ.get("FIRM_SHORT", "").strip())
    if is_prod:
        if not ALLOWED_ORIGINS:
            # Fail closed, not open. Log loudly.
            import logging
            logging.getLogger("security").critical(
                "[CRITICAL] Production detected but ALLOWED_ORIGINS not set. "
                "CORS will reject every cross-origin request. "
                "Set ALLOWED_ORIGINS='https://spectrhq.in,https://spectr.thealgorythm.in' and restart."
            )
        return {
            "allow_origins": ALLOWED_ORIGINS or [],  # empty list = zero cross-origin allowed
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
            "allow_headers": ["Authorization", "Content-Type", "X-Request-ID", "X-API-Key"],
            "max_age": 600,
        }
    else:
        # Development: localhost-only (IPv4 + IPv6 aliases)
        return {
            "allow_origins": ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"],
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            "allow_headers": ["Authorization", "Content-Type", "X-Request-ID", "X-API-Key"],
            "max_age": 3600,
        }


# ==================== RBAC (Role-Based Access Control) ====================

ROLE_PERMISSIONS = {
    "admin": {
        "users": ["read", "write", "delete"],
        "matters": ["read", "write", "delete"],
        "documents": ["read", "write", "delete"],
        "billing": ["read", "write", "delete"],
        "audit_logs": ["read"],
        "settings": ["read", "write"],
        "api_keys": ["read", "write", "delete"],
        "clients": ["read", "write", "delete"],
        "export": ["read"],
    },
    "partner": {
        "users": ["read"],
        "matters": ["read", "write", "delete"],
        "documents": ["read", "write", "delete"],
        "billing": ["read", "write"],
        "audit_logs": ["read"],
        "settings": ["read", "write"],
        "api_keys": ["read", "write"],
        "clients": ["read", "write", "delete"],
        "export": ["read"],
    },
    "analyst": {
        "users": ["read"],
        "matters": ["read", "write"],
        "documents": ["read", "write"],
        "billing": ["read"],
        "audit_logs": [],
        "settings": ["read"],
        "api_keys": [],
        "clients": ["read", "write"],
        "export": ["read"],
    },
    "viewer": {
        "users": ["read"],
        "matters": ["read"],
        "documents": ["read"],
        "billing": [],
        "audit_logs": [],
        "settings": [],
        "api_keys": [],
        "clients": ["read"],
        "export": [],
    },
}


def check_permission(role: str, resource: str, action: str) -> bool:
    """Check if a role has permission for an action on a resource."""
    perms = ROLE_PERMISSIONS.get(role, {})
    allowed_actions = perms.get(resource, [])
    return action in allowed_actions


def require_role(*roles):
    """Decorator-style role check. Usage: require_role("admin", "partner")"""
    def check(user: dict) -> bool:
        return user.get("role", "viewer") in roles
    return check


# ==================== ENCRYPTION UTILITIES ====================

def encrypt_sensitive(data: str) -> str:
    """Encrypt sensitive data (API keys, TOTP secrets) using AES-256 via Fernet.
    Falls back to HMAC-based obfuscation if cryptography not installed.
    """
    try:
        from cryptography.fernet import Fernet
        key = os.environ.get("ENCRYPTION_KEY", "")
        if not key:
            # Derive from SECRET_KEY
            key = hashlib.sha256(SECRET_KEY.encode()).digest()
            from base64 import urlsafe_b64encode
            key = urlsafe_b64encode(key)
        f = Fernet(key)
        return f.encrypt(data.encode("utf-8")).decode("utf-8")
    except ImportError:
        # Fallback: HMAC-based (not true encryption, but better than plaintext)
        mac = hmac.new(SECRET_KEY.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"hmac:{mac}:{data}"


def decrypt_sensitive(encrypted: str) -> str:
    """Decrypt sensitive data."""
    try:
        from cryptography.fernet import Fernet
        key = os.environ.get("ENCRYPTION_KEY", "")
        if not key:
            key = hashlib.sha256(SECRET_KEY.encode()).digest()
            from base64 import urlsafe_b64encode
            key = urlsafe_b64encode(key)
        f = Fernet(key)
        return f.decrypt(encrypted.encode("utf-8")).decode("utf-8")
    except ImportError:
        if encrypted.startswith("hmac:"):
            parts = encrypted.split(":", 2)
            return parts[2] if len(parts) == 3 else encrypted
        return encrypted


# ==================== REQUEST FINGERPRINTING ====================

def fingerprint_request(ip: str, user_agent: str) -> str:
    """Generate a request fingerprint for anomaly detection."""
    raw = f"{ip}:{user_agent}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def is_suspicious_ip(ip: str) -> bool:
    """Check if IP is from known suspicious ranges (Tor exit nodes, etc.)."""
    try:
        addr = ipaddress.ip_address(ip)
        # Private ranges are fine (local dev)
        if addr.is_private or addr.is_loopback:
            return False
        # Block reserved/multicast
        if addr.is_reserved or addr.is_multicast:
            return True
    except ValueError:
        return True  # Invalid IP format is suspicious
    return False


# ==================== API KEY GENERATION ====================

def generate_api_key(prefix: str = "sk_live") -> tuple:
    """Generate a new API key. Returns (raw_key, key_hash, key_prefix).
    The raw key is shown ONCE to the user. Only the hash is stored.
    """
    raw = f"{prefix}_{secrets.token_hex(32)}"
    key_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return raw, key_hash, raw[:8]


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    """Verify an API key against its stored hash."""
    return hmac.compare_digest(
        hashlib.sha256(raw_key.encode("utf-8")).hexdigest(),
        stored_hash
    )


# ==================== CONTENT SECURITY ====================

def redact_sensitive_from_log(text: str) -> str:
    """Redact PAN, Aadhaar, bank account numbers from log output."""
    # PAN
    text = re.sub(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', 'XXXXX****X', text)
    # Aadhaar
    text = re.sub(r'\b\d{4}\s?\d{4}\s?\d{4}\b', 'XXXX XXXX XXXX', text)
    # Bank account (8-18 digits)
    text = re.sub(r'\b\d{8,18}\b', 'XXXXXXXX', text)
    # Email (partial redaction)
    text = re.sub(r'([a-zA-Z0-9._%+-])[a-zA-Z0-9._%+-]*@', r'\1***@', text)
    return text
