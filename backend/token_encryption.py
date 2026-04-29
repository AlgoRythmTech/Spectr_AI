"""
Token Encryption — application-level encryption for OAuth refresh tokens + other secrets.

Why: MongoDB Atlas encrypts at rest by default, BUT a DBA or cloud breach could still read
plaintext tokens. This adds a second layer — tokens are encrypted BEFORE they hit Mongo.

Algorithm: Fernet (AES-128-CBC + HMAC-SHA256), from the `cryptography` library.
Key: loaded from env var TOKEN_ENCRYPTION_KEY (base64-encoded 32 bytes).
Rotation: generate new key, decrypt-reencrypt all tokens, swap env var.

If key is missing, encryption is NO-OP (useful for dev), and a warning is logged.
In production/dedicated deployments, missing key raises.
"""
import os
import base64
import logging

logger = logging.getLogger("token_encryption")

_FERNET = None


def _get_fernet():
    """Lazily initialize Fernet cipher from env key."""
    global _FERNET
    if _FERNET is not None:
        return _FERNET

    key = os.environ.get("TOKEN_ENCRYPTION_KEY", "").strip()
    if not key:
        environment = os.environ.get("ENVIRONMENT", "development")
        firm = os.environ.get("FIRM_SHORT", "")
        if environment == "production" or firm:
            raise RuntimeError(
                "TOKEN_ENCRYPTION_KEY is required in production/dedicated mode. "
                "Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        logger.warning(
            "TOKEN_ENCRYPTION_KEY not set — tokens stored PLAINTEXT (dev mode only). "
            "DO NOT USE IN PRODUCTION."
        )
        return None

    try:
        from cryptography.fernet import Fernet
        # Accept either base64 Fernet key or a 32-byte passphrase
        if len(key) == 44 and key.endswith("="):
            # Looks like a Fernet key already
            _FERNET = Fernet(key.encode())
        else:
            # Derive a key from arbitrary string via SHA256
            import hashlib
            derived = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
            _FERNET = Fernet(derived)
        return _FERNET
    except ImportError:
        logger.error("cryptography package not installed. Run: pip install cryptography")
        return None
    except Exception as e:
        logger.error(f"Failed to init Fernet: {e}")
        return None


def encrypt(plaintext: str) -> str:
    """Encrypt a string. Returns base64-encoded ciphertext.

    If no key is configured (dev mode), returns plaintext unchanged with a PT: prefix
    so decrypt() can round-trip cleanly.
    """
    if plaintext is None or plaintext == "":
        return plaintext
    f = _get_fernet()
    if f is None:
        return "PT:" + plaintext  # Dev mode marker
    try:
        return "ENC:" + f.encrypt(plaintext.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return "PT:" + plaintext


def decrypt(ciphertext: str) -> str:
    """Decrypt a string. Round-trips with encrypt()."""
    if ciphertext is None or ciphertext == "":
        return ciphertext
    # Dev-mode plaintext marker
    if ciphertext.startswith("PT:"):
        return ciphertext[3:]
    # Legacy/unprefixed ciphertext handling
    if not ciphertext.startswith("ENC:"):
        # Assume it's an unencrypted legacy token
        return ciphertext

    f = _get_fernet()
    if f is None:
        logger.warning("Encrypted token encountered but no key available")
        return ""
    try:
        return f.decrypt(ciphertext[4:].encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.warning(f"Decryption failed: {e}")
        return ""


def encrypt_dict_fields(d: dict, fields: list[str]) -> dict:
    """Encrypt specific fields in a dict in-place-safe (returns new dict)."""
    d = dict(d)
    for f in fields:
        if f in d and d[f]:
            d[f] = encrypt(str(d[f]))
    return d


def decrypt_dict_fields(d: dict, fields: list[str]) -> dict:
    """Decrypt specific fields in a dict."""
    d = dict(d)
    for f in fields:
        if f in d and d[f]:
            d[f] = decrypt(str(d[f]))
    return d


# Diagnostic
if __name__ == "__main__":
    test = "sk-test-1234567890"
    enc = encrypt(test)
    dec = decrypt(enc)
    print(f"Plain:   {test}")
    print(f"Encrypt: {enc[:80]}...")
    print(f"Decrypt: {dec}")
    print(f"Match:   {test == dec}")
