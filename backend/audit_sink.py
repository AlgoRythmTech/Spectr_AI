"""
Exhaustive audit sink — dedicated MongoDB cluster for ALL platform activity.

Purpose
-------
A SEPARATE cluster from the operational database, solely for logs/audit.
This cluster never holds user-facing data (Vault docs, matters, etc.) —
it holds the forensic trail: who logged in from where at what time, what
they queried, what the system returned, what they uploaded, every error,
every admin action, every T&C acceptance.

Why separate:
  - Ops cluster outage does NOT silence audit writes
  - Log cluster ransomware/deletion does NOT lose user data
  - Audit cluster can be retained 7+ years for compliance
    independently of the operational TTL
  - Different security policy: logs are write-once-append-only, users
    cluster is read-write

Environment config
------------------
    MONGO_LOG_URL       — full SRV connection string for the logs cluster
    LOG_DB_NAME         — default "spectr_logs"

If MONGO_LOG_URL is not set, every function here degrades to a no-op and
falls back to the existing SQLite audit_logs table — nothing crashes.

What we log (every collection in the logs DB)
---------------------------------------------
    events            — every significant user action with full context
    auth_events       — login success/fail, logout, token-refresh
    query_events      — every /api/assistant/query submission + response summary
    vault_events      — every upload / analyse / ask / delete
    workflow_events   — every workflow generation
    court_tracker_events — track/refresh/delete
    tos_events        — acceptance, declines, version bumps
    error_events      — every unhandled exception with stack trace
    security_events   — rate-limit hits, auth failures, suspicious IPs

Every document captures:
    timestamp_utc (ms precision), timestamp_ist
    user_id, user_email, user_name, role
    ip_address, user_agent, device_fingerprint
    endpoint, http_method
    request_id (uuid per request)
    session_id (if tracked)
    tenant / firm_id
    payload_summary (sanitized — no PII in raw form)
    outcome (success | failure | rate_limited | blocked)
    latency_ms
    details (collection-specific fields)
"""

import os
import uuid
import asyncio
import logging
import traceback
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

logger = logging.getLogger("audit_sink")

# ─── Configuration ───────────────────────────────────────────────────
_LOG_URL = os.environ.get("MONGO_LOG_URL", "").strip()
_LOG_DB = os.environ.get("LOG_DB_NAME", "spectr_logs").strip()
_TENANT = os.environ.get("FIRM_SHORT", "_default").strip()
_INSTANCE_ID = os.environ.get("SPECTR_INSTANCE_ID", "default-instance").strip()
_USE_FIRESTORE = os.environ.get("USE_FIRESTORE", "").strip() in ("1", "true", "yes")

# Sink is enabled if EITHER Firestore (same project as main db) OR legacy
# Mongo log URL is configured. Firestore wins if both are set.
_ENABLED = _USE_FIRESTORE or bool(_LOG_URL)
_log_client = None
_log_db = None


def _ist_now() -> str:
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_db():
    """Lazy-init the logs backend — Firestore (preferred) or legacy Mongo."""
    global _log_client, _log_db
    if not _ENABLED:
        return None
    if _log_db is not None:
        return _log_db

    if _USE_FIRESTORE:
        try:
            # Logs live in the SAME Firestore project as main data, but in
            # collections prefixed so there's no ambiguity vs operational docs.
            # We create a thin namespace on top of the shared adapter so
            # writes to `events` here land in `logs_events`, etc.
            from firestore_adapter import get_firestore_db
            base_db = get_firestore_db(_LOG_DB)

            class _Prefixed:
                # Names that are DB-level methods/attrs, not collections —
                # must pass through to the underlying db unchanged.
                _PASSTHROUGH = {"command", "list_collection_names", "name",
                                "client", "_client"}

                def __init__(self, base):
                    self._base = base
                def __getitem__(self, name):
                    # Prefix every log collection with "logs_" so they're
                    # visibly separate from operational collections in the
                    # Firebase console.
                    return self._base[f"logs_{name}"]
                def __getattr__(self, name):
                    if name.startswith("_"):
                        raise AttributeError(name)
                    if name in self._PASSTHROUGH:
                        return getattr(self._base, name)
                    return self[name]

            _log_db = _Prefixed(base_db)
            logger.info(f"Audit sink: using Firestore (prefix 'logs_')")
            return _log_db
        except Exception as e:
            logger.error(f"Audit sink Firestore init failed: {e}")
            _log_db = None
            return None

    # Legacy Mongo path — aggressive timeouts so Atlas outages don't cascade
    # into 8-second per-request hangs (audit writes are non-critical path).
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        _log_client = AsyncIOMotorClient(
            _LOG_URL,
            tls=True,
            tlsAllowInvalidCertificates=True,
            serverSelectionTimeoutMS=1500,
            connectTimeoutMS=1500,
            socketTimeoutMS=2500,
            retryWrites=False,
            maxPoolSize=15,
            minPoolSize=0,
        )
        _log_db = _log_client[_LOG_DB]
        logger.info(f"Audit sink: connected to {_LOG_DB} (Mongo)")
        return _log_db
    except Exception as e:
        logger.error(f"Audit sink init failed: {e}")
        return None


def _redact_sensitive(data: Any, depth: int = 0) -> Any:
    """Strip PII / secrets before writing to log cluster. We log the USER's
    identity (intentional) but not the content of their documents or query
    answers in raw form — only a hashed/truncated summary."""
    if depth > 5:
        return "<nested>"
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            kl = str(k).lower()
            if kl in ("password", "authorization", "token", "api_key", "secret", "firebase_uid"):
                out[k] = "***REDACTED***"
            elif kl in ("content", "extracted_text", "response_text", "body"):
                # Log shape, not content
                if isinstance(v, str):
                    out[k] = f"<{len(v)} chars>"
                else:
                    out[k] = "<non-string>"
            else:
                out[k] = _redact_sensitive(v, depth + 1)
        return out
    if isinstance(data, (list, tuple)):
        return [_redact_sensitive(x, depth + 1) for x in data[:20]]
    if isinstance(data, str):
        return data[:2000]  # cap individual strings
    if isinstance(data, (int, float, bool)) or data is None:
        return data
    return str(data)[:200]


def _base_envelope(
    user: Optional[dict] = None,
    request: Any = None,
    event_type: str = "event",
) -> dict:
    """Every log document starts with the same envelope. Collection-specific
    payload merges on top via .update()."""
    env = {
        "log_id": f"log_{uuid.uuid4().hex[:20]}",
        "timestamp_utc": _utc_now(),
        "timestamp_ist": _ist_now(),
        "tenant": _TENANT,
        "instance_id": _INSTANCE_ID,
        "event_type": event_type,
    }
    if user and isinstance(user, dict):
        env["user_id"] = user.get("user_id", "")
        env["user_email"] = user.get("email", "")
        env["user_name"] = user.get("name", "")
        env["user_role"] = user.get("role", "")
        env["user_firm"] = user.get("firm_name", "")
    if request is not None:
        try:
            fwd = request.headers.get("X-Forwarded-For", "") if hasattr(request, "headers") else ""
            env["ip_address"] = (
                fwd.split(",")[0].strip()
                if fwd
                else (request.client.host if getattr(request, "client", None) else "")
            )
            env["user_agent"] = (request.headers.get("User-Agent", "") if hasattr(request, "headers") else "")[:500]
            env["http_method"] = getattr(request, "method", "")
            env["endpoint"] = str(getattr(request, "url", {}).path if hasattr(getattr(request, "url", None), "path") else "")
            env["referer"] = (request.headers.get("Referer", "") if hasattr(request, "headers") else "")[:500]
        except Exception:
            pass
    return env


# Circuit breaker: when Firestore throws 429 (quota) or repeatedly times
# out, we stop attempting writes for a short cooling-off period. Otherwise
# every endpoint that awaits an audit write sits blocked for 60s per call.
_CIRCUIT_OPEN_UNTIL: float = 0.0
_WRITE_TIMEOUT_S: float = 2.0  # fast fail — never block the request path
_CIRCUIT_COOLDOWN_S: float = 90.0

async def _write(collection: str, doc: dict) -> None:
    """Fire-and-forget insert. Never blocks the caller; never raises.

    Circuit-broken when Firestore is rate-limited — we skip writes for 90s
    rather than letting every request hang for 60s on the internal retry.
    """
    import time as _t
    global _CIRCUIT_OPEN_UNTIL
    if not _ENABLED:
        return
    now = _t.time()
    if now < _CIRCUIT_OPEN_UNTIL:
        # Circuit is open (quota/error burst) — silently drop
        return
    try:
        db = _get_db()
        if db is None:
            return
        await asyncio.wait_for(
            db[collection].insert_one(doc),
            timeout=_WRITE_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        _CIRCUIT_OPEN_UNTIL = now + _CIRCUIT_COOLDOWN_S
        logger.warning(
            f"audit_sink write to {collection} timed out — opening circuit for "
            f"{_CIRCUIT_COOLDOWN_S:.0f}s (likely Firestore quota/unreachable)"
        )
    except Exception as e:
        msg = str(e)[:200]
        # 429 / quota → trip the breaker so we don't hammer Firestore
        if "429" in msg or "Quota" in msg or "quota" in msg:
            _CIRCUIT_OPEN_UNTIL = now + _CIRCUIT_COOLDOWN_S
            logger.warning(
                f"audit_sink quota error to {collection} — opening circuit for "
                f"{_CIRCUIT_COOLDOWN_S:.0f}s"
            )
        else:
            logger.warning(f"audit_sink write to {collection} failed: {type(e).__name__}: {msg[:120]}")


def fire(collection: str, doc: dict) -> None:
    """Schedule an async write without awaiting. Callers stay synchronous."""
    if not _ENABLED:
        return
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_write(collection, doc))
        else:
            loop.create_task(_write(collection, doc))
    except Exception:
        pass  # if there's no loop context, skip — we never block the caller


# ═══════════════════════════════════════════════════════════════════════
# Public helpers — call these from server.py endpoints
# ═══════════════════════════════════════════════════════════════════════

async def log_auth_event(
    user: Optional[dict],
    request: Any,
    outcome: str,  # success | failure | logout | token_refresh
    reason: str = "",
    method: str = "firebase",
) -> None:
    doc = _base_envelope(user, request, event_type="auth")
    doc.update({"outcome": outcome, "reason": reason[:200], "auth_method": method})
    await _write("auth_events", doc)
    # Mirror into the catch-all 'events' collection for a single chronological view
    await _write("events", {**doc})


async def log_query_event(
    user: Optional[dict],
    request: Any,
    query: str,
    mode: str,
    outcome: str,
    latency_ms: int = 0,
    response_chars: int = 0,
    citations_count: int = 0,
    matter_id: Optional[str] = None,
    trust_score: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    doc = _base_envelope(user, request, event_type="query")
    doc.update({
        "query_preview": query[:500] if query else "",
        "query_length": len(query or ""),
        "mode": mode,
        "outcome": outcome,
        "latency_ms": int(latency_ms),
        "response_chars": int(response_chars),
        "citations_count": int(citations_count),
        "matter_id": matter_id,
        "trust_score": trust_score,
        "error": (error or "")[:500],
    })
    await _write("query_events", doc)
    await _write("events", {**doc})


async def log_vault_event(
    user: Optional[dict],
    request: Any,
    action: str,  # upload | analyze | ask | delete | list
    outcome: str,
    doc_id: Optional[str] = None,
    filename: Optional[str] = None,
    doc_type: Optional[str] = None,
    size_bytes: Optional[int] = None,
    pii_redactions: int = 0,
    latency_ms: int = 0,
    error: Optional[str] = None,
) -> None:
    doc = _base_envelope(user, request, event_type="vault")
    doc.update({
        "action": action,
        "outcome": outcome,
        "doc_id": doc_id,
        "filename": (filename or "")[:200],
        "doc_type": doc_type,
        "size_bytes": size_bytes,
        "pii_redactions": int(pii_redactions),
        "latency_ms": int(latency_ms),
        "error": (error or "")[:500],
    })
    await _write("vault_events", doc)
    await _write("events", {**doc})


async def log_workflow_event(
    user: Optional[dict],
    request: Any,
    workflow_type: str,
    outcome: str,
    docx_file_id: Optional[str] = None,
    response_chars: int = 0,
    latency_ms: int = 0,
    error: Optional[str] = None,
) -> None:
    doc = _base_envelope(user, request, event_type="workflow")
    doc.update({
        "workflow_type": workflow_type,
        "outcome": outcome,
        "docx_file_id": docx_file_id,
        "response_chars": int(response_chars),
        "latency_ms": int(latency_ms),
        "error": (error or "")[:500],
    })
    await _write("workflow_events", doc)
    await _write("events", {**doc})


async def log_court_tracker_event(
    user: Optional[dict],
    request: Any,
    action: str,  # track | refresh | delete | list
    outcome: str,
    case_number: Optional[str] = None,
    track_id: Optional[str] = None,
    court: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    doc = _base_envelope(user, request, event_type="court_tracker")
    doc.update({
        "action": action,
        "outcome": outcome,
        "case_number": (case_number or "")[:200],
        "track_id": track_id,
        "court": court,
        "error": (error or "")[:500],
    })
    await _write("court_tracker_events", doc)
    await _write("events", {**doc})


async def log_tos_event(
    user: Optional[dict],
    request: Any,
    action: str,  # accept | decline | view | version_bump
    outcome: str,
    tos_version: Optional[str] = None,
    acknowledged_disclosures: Optional[list] = None,
    acceptance_id: Optional[str] = None,
) -> None:
    doc = _base_envelope(user, request, event_type="tos")
    doc.update({
        "action": action,
        "outcome": outcome,
        "tos_version": tos_version,
        "acknowledged_disclosures": acknowledged_disclosures or [],
        "acceptance_id": acceptance_id,
    })
    await _write("tos_events", doc)
    await _write("events", {**doc})


async def log_error_event(
    request: Any,
    error: Exception,
    user: Optional[dict] = None,
    context: Optional[dict] = None,
) -> None:
    doc = _base_envelope(user, request, event_type="error")
    doc.update({
        "error_type": type(error).__name__,
        "error_message": str(error)[:1000],
        "traceback": traceback.format_exc()[:4000],
        "context": _redact_sensitive(context) if context else {},
    })
    await _write("error_events", doc)
    await _write("events", {**doc})


async def log_security_event(
    request: Any,
    kind: str,  # rate_limit | auth_failure | suspicious_ip | injection_blocked | upload_rejected
    outcome: str,
    user: Optional[dict] = None,
    detail: Optional[dict] = None,
) -> None:
    doc = _base_envelope(user, request, event_type="security")
    doc.update({
        "kind": kind,
        "outcome": outcome,
        "detail": _redact_sensitive(detail) if detail else {},
    })
    await _write("security_events", doc)
    await _write("events", {**doc})


async def log_generic_event(
    user: Optional[dict],
    request: Any,
    event_type: str,
    action: str,
    outcome: str = "success",
    details: Optional[dict] = None,
) -> None:
    """Catch-all for actions that don't have a dedicated helper."""
    doc = _base_envelope(user, request, event_type=event_type)
    doc.update({
        "action": action,
        "outcome": outcome,
        "details": _redact_sensitive(details) if details else {},
    })
    await _write("events", doc)


# ═══════════════════════════════════════════════════════════════════════
# Startup indexing — run once at boot
# ═══════════════════════════════════════════════════════════════════════

async def ensure_indexes() -> None:
    """Create indexes on the logs cluster for fast query-by-user + query-by-time.
    Safe to call multiple times — MongoDB idempotent on existing indexes."""
    if not _ENABLED:
        return
    db = _get_db()
    if db is None:
        return
    try:
        # Per-user, time-descending — main query pattern for user history view
        for coll in ["events", "auth_events", "query_events", "vault_events",
                     "workflow_events", "court_tracker_events", "tos_events",
                     "error_events", "security_events"]:
            await db[coll].create_index([("user_id", 1), ("timestamp_utc", -1)])
            await db[coll].create_index([("timestamp_utc", -1)])
        # IP-based abuse investigation
        await db["events"].create_index([("ip_address", 1), ("timestamp_utc", -1)])
        # Security event lookups by kind
        await db["security_events"].create_index([("kind", 1), ("timestamp_utc", -1)])
        logger.info("Audit sink indexes ensured")
    except Exception as e:
        logger.warning(f"Audit index creation failed (non-blocking): {e}")


async def health_check() -> dict:
    if not _ENABLED:
        return {"enabled": False, "reason": "MONGO_LOG_URL not set"}
    db = _get_db()
    if db is None:
        return {"enabled": False, "reason": "init failed"}
    try:
        await asyncio.wait_for(db.command("ping"), timeout=5.0)
        # How many events have we captured?
        counts = {}
        for coll in ["events", "auth_events", "query_events", "vault_events", "error_events"]:
            try:
                counts[coll] = await db[coll].estimated_document_count()
            except Exception:
                counts[coll] = "?"
        return {"enabled": True, "status": "reachable", "counts": counts}
    except Exception as e:
        return {"enabled": True, "status": "unreachable", "error": str(e)[:200]}
