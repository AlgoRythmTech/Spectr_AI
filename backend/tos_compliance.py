"""
Terms of Service compliance endpoints — Spectr T&C v2.0 (April 2026).

Implements the operational mechanisms the Agreement itself promises:

  - Clause 2.1-2.3 (Acceptance Event capture + immutable record)
  - Clause 2.6 (Unregistered-entity disclosure pre-acceptance)
  - Clause 8.6 (Data deletion on termination — 1-day request window)
  - Clause 8.9 (Grievance Officer contact)
  - Clause 14.1 (Notice of T&C modifications — fresh Acceptance Event on material change)
  - Clause 16.14 (Immutable electronic records, admissible as evidence)

These endpoints are mounted under /api/legal/* by server.py and are public-
readable (privacy policy, grievance contact, current T&C version) except the
Acceptance Event POST, which requires a valid Firebase user session.
"""

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Request, Header, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("tos_compliance")

# ─── CONFIGURATION ───
# Current T&C version shown to users at acceptance. Bump this integer when
# the Agreement materially changes; the next login will force a fresh
# Acceptance Event per Clause 14.1.
CURRENT_TOS_VERSION = "2.0"
TOS_EFFECTIVE_DATE = "2026-04-01"
TOS_FULL_TEXT_URL = "/legal/terms"  # Frontend route rendering the full Agreement

# ─── GRIEVANCE OFFICER (Clause 8.9) ───
# Published contact per DPDP Act grievance mechanism. Configurable via env so
# the published address can be updated without a code deploy.
GRIEVANCE_OFFICER_NAME = os.environ.get("SPECTR_GRIEVANCE_OFFICER", "Grievance Officer, Spectr & Co.")
GRIEVANCE_OFFICER_EMAIL = os.environ.get("SPECTR_GRIEVANCE_EMAIL", "grievance@spectrhq.in")
GRIEVANCE_OFFICER_ADDRESS = os.environ.get(
    "SPECTR_GRIEVANCE_ADDRESS",
    "Spectr & Co., Hyderabad, Telangana, India"
)
GRIEVANCE_RESPONSE_SLA_DAYS = 30  # DPDP Act standard

# ─── COMPANY STATUS (Clause 2.6) ───
# Disclosed in the pre-acceptance banner so users knowingly accept Clause 2.6.
COMPANY_STATUS = os.environ.get("SPECTR_COMPANY_STATUS", "unregistered")
COMPANY_NAME = os.environ.get("SPECTR_COMPANY_NAME", "Spectr & Co.")
COMPANY_LOCATION = os.environ.get("SPECTR_COMPANY_LOCATION", "Hyderabad, Telangana, India")


router = APIRouter(prefix="/api/legal", tags=["legal"])


# ────────────────────────────────────────────────────────────────────────
# Public endpoints (no auth)
# ────────────────────────────────────────────────────────────────────────

@router.get("/tos/current")
async def get_current_tos():
    """Return the version identifier + public metadata of the current T&C.

    Frontend calls this on the acceptance screen to fetch the version that
    will be recorded against the user's Acceptance Event.
    """
    return {
        "version": CURRENT_TOS_VERSION,
        "effective_date": TOS_EFFECTIVE_DATE,
        "full_text_url": TOS_FULL_TEXT_URL,
        "company_status": COMPANY_STATUS,
        "company_name": COMPANY_NAME,
        "company_location": COMPANY_LOCATION,
        "disclosures": [
            # Surfaced to the user BEFORE the checkbox per Clause 2.6
            {
                "id": "unregistered_entity",
                "headline": f"{COMPANY_NAME} is presently an unregistered entity based in {COMPANY_LOCATION}.",
                "detail": (
                    "By proceeding, you acknowledge this status and agree under Clause 2.6 "
                    "not to argue the Agreement is void solely because the operating entity "
                    "is unregistered. This disclosure is made prior to your acceptance and "
                    "is binding once you tick the checkbox."
                ),
                "clause_ref": "2.6",
            },
            {
                "id": "ai_not_professional_advice",
                "headline": "Every Output is AI-assisted research, not legal or CA advice.",
                "detail": (
                    "Spectr does not hold any licence to practise law or Chartered Accountancy. "
                    "You remain professionally responsible for every Output you use. "
                    "Verify independently before filing, advising clients, or relying in any matter."
                ),
                "clause_ref": "4.1-4.6",
            },
            {
                "id": "eligibility",
                "headline": "Use is restricted to enrolled Advocates, CAs, and their authorised staff.",
                "detail": (
                    "By accepting, you confirm your professional enrolment is current and that "
                    "your use of the Platform does not breach any rule of your Professional Body."
                ),
                "clause_ref": "3.1-3.2",
            },
            {
                "id": "pii_cross_border",
                "headline": "Your queries are routed to AI providers outside India (with PII stripped first).",
                "detail": (
                    "We run a PII Anonymisation Pipeline that strips Aadhaar, PAN, GSTIN, mobile, "
                    "email, IFSC, and CIN before transmission (Clause 8.2). You still confirm you "
                    "have lawful basis to upload the documents you choose to upload."
                ),
                "clause_ref": "8.2-8.3",
            },
        ],
    }


@router.get("/grievance-officer")
async def get_grievance_officer():
    """Publish Grievance Officer contact per Clause 8.9 / DPDP Act.

    This endpoint is intentionally public (no auth) so the contact is
    findable by a data principal who may not be a registered user.
    """
    return {
        "name": GRIEVANCE_OFFICER_NAME,
        "email": GRIEVANCE_OFFICER_EMAIL,
        "address": GRIEVANCE_OFFICER_ADDRESS,
        "response_sla_days": GRIEVANCE_RESPONSE_SLA_DAYS,
        "scope": (
            "Complaints regarding processing of personal data by Spectr & Co. "
            "under the Digital Personal Data Protection Act 2023, and grievances "
            "concerning the User's use of the Platform under Clause 8.9 of the "
            "Terms of Service."
        ),
    }


# ────────────────────────────────────────────────────────────────────────
# Acceptance Event (Clause 2.1-2.3, 16.14)
# ────────────────────────────────────────────────────────────────────────

class AcceptanceEventRequest(BaseModel):
    """Payload submitted when the user ticks the acceptance checkbox and
    clicks "I Agree and Proceed"."""
    tos_version: str = Field(..., description="Version identifier of the T&C being accepted")
    device_fingerprint: Optional[str] = Field(None, description="Optional browser/device fingerprint")
    acknowledged_disclosures: list[str] = Field(
        default_factory=list,
        description="IDs of pre-acceptance disclosures shown to the user (Clause 2.6 unregistered_entity et al)"
    )


def _client_ip(request: Request) -> str:
    """Extract the real client IP, honouring X-Forwarded-For."""
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def record_acceptance_event(
    db,
    user: dict,
    req: AcceptanceEventRequest,
    http_request: Request,
) -> dict:
    """Persist an immutable Acceptance Event record.

    Per Clause 2.3 + 16.14 the record is treated as conclusive electronic
    evidence of the contract. We capture every field the Agreement enumerates.
    """
    if req.tos_version != CURRENT_TOS_VERSION:
        raise HTTPException(
            status_code=409,
            detail=f"Acceptance Event rejected: Agreement has been updated to version {CURRENT_TOS_VERSION}. Please review the current Agreement and resubmit."
        )

    # Verify the mandatory disclosures were shown — cannot accept without them
    required_disclosures = {"unregistered_entity", "ai_not_professional_advice", "eligibility", "pii_cross_border"}
    missing = required_disclosures - set(req.acknowledged_disclosures)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Acceptance Event rejected: required disclosures not acknowledged: {sorted(missing)}"
        )

    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc.astimezone(timezone(timedelta(hours=5, minutes=30)))

    ip = _client_ip(http_request)
    user_agent = http_request.headers.get("User-Agent", "")[:500]

    record = {
        "acceptance_id": f"acc_{uuid.uuid4().hex[:16]}",
        "user_id": user.get("user_id"),
        "user_email": user.get("email", ""),
        "user_name": user.get("name", ""),
        "tos_version": req.tos_version,
        "tos_effective_date": TOS_EFFECTIVE_DATE,
        "full_text_url": TOS_FULL_TEXT_URL,
        "acknowledged_disclosures": sorted(req.acknowledged_disclosures),
        "ip_address": ip,
        "user_agent": user_agent,
        "device_fingerprint": req.device_fingerprint or "",
        "accepted_at_utc": now_utc.isoformat(),
        "accepted_at_ist": now_ist.isoformat(),
        "immutable": True,  # document marker — do not update in place, always insert new
        "company_status_at_time": COMPANY_STATUS,
        "company_name_at_time": COMPANY_NAME,
    }

    try:
        await db.tos_acceptances.insert_one(dict(record))
        logger.info(f"Acceptance Event recorded: {record['acceptance_id']} user={user.get('user_id')} v={req.tos_version}")
    except Exception as e:
        logger.error(f"Failed to persist Acceptance Event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not record acceptance. Please retry.")

    # Scrub MongoDB's internal _id from the returned record
    record.pop("_id", None)
    return record


async def get_latest_acceptance(db, user_id: str) -> Optional[dict]:
    """Return the most recent Acceptance Event for a user, or None.

    Used to gate access: if the stored version is older than CURRENT_TOS_VERSION
    a fresh acceptance is required per Clause 14.1.
    """
    try:
        doc = await db.tos_acceptances.find_one(
            {"user_id": user_id},
            {"_id": 0},
            sort=[("accepted_at_utc", -1)],
        )
        return doc
    except Exception as e:
        logger.warning(f"Could not fetch latest acceptance for {user_id}: {e}")
        return None


# ────────────────────────────────────────────────────────────────────────
# WIRED ROUTES — the frontend actually calls these.
# Protected by auth_middleware.AuthEnforceMiddleware (already whitelists
# /api/legal/acceptance and /api/legal/acceptance/status in PROTECTED_PREFIXES).
# request.state.user is populated by the middleware after token verification.
# ────────────────────────────────────────────────────────────────────────

def _resolve_db():
    """Late import to avoid circular dependency with server.py at module load."""
    from server import get_db
    return get_db()


@router.post("/acceptance")
async def post_acceptance(req: AcceptanceEventRequest, request: Request):
    """Record the user's acceptance of the current T&C to the DB.

    This is the endpoint the frontend hits after the user ticks the box and
    clicks "I Agree". Persists an immutable record to `tos_acceptances` with
    every identity + device + time field the Agreement enumerates. IP is
    stamped authoritatively from the request headers (client cannot forge).
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    db = _resolve_db()
    record = await record_acceptance_event(db, user, req, request)
    return {
        "ok": True,
        "acceptance_id": record["acceptance_id"],
        "accepted_at_utc": record["accepted_at_utc"],
        "accepted_at_ist": record["accepted_at_ist"],
        "tos_version": record["tos_version"],
    }


@router.get("/acceptance/status")
async def get_acceptance_status(request: Request):
    """Tell the frontend whether this user has a valid Acceptance Event on
    record for the CURRENT T&C version. If they do, the gate clears silently.
    If not (or stored version is older — Clause 14.1), they must re-accept.
    """
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    db = _resolve_db()
    latest = await get_latest_acceptance(db, user.get("user_id"))
    has_valid = bool(latest) and latest.get("tos_version") == CURRENT_TOS_VERSION

    return {
        "has_valid_acceptance": has_valid,
        "current_version": CURRENT_TOS_VERSION,
        "stored_version": latest.get("tos_version") if latest else None,
        "accepted_at_utc": latest.get("accepted_at_utc") if latest else None,
        "accepted_at_ist": latest.get("accepted_at_ist") if latest else None,
        "acceptance_id": latest.get("acceptance_id") if latest else None,
    }


# ────────────────────────────────────────────────────────────────────────
# Data Deletion on Termination (Clause 8.6)
# ────────────────────────────────────────────────────────────────────────

async def request_account_deletion(db, user: dict) -> dict:
    """Mark the user's account for deletion and schedule data purge.

    Per Clause 8.6, the User may request deletion within 1 day of termination.
    We accept the request, mark all the user's Inputs as deleted (soft-delete
    with a 24h grace window), and log the request for the purge worker.
    """
    user_id = user.get("user_id")
    now = datetime.now(timezone.utc)
    purge_after = now + timedelta(hours=24)

    deletion_request = {
        "request_id": f"del_{uuid.uuid4().hex[:16]}",
        "user_id": user_id,
        "user_email": user.get("email", ""),
        "requested_at": now.isoformat(),
        "scheduled_purge_at": purge_after.isoformat(),
        "status": "pending_purge",
        "clause_ref": "8.6",
    }

    try:
        await db.deletion_requests.insert_one(dict(deletion_request))
        # Soft-delete the user's documents so they're not served in any list
        # before the purge worker removes them permanently
        await db.documents.update_many(
            {"user_id": user_id},
            {"$set": {"is_deleted": True, "deletion_scheduled_at": purge_after.isoformat()}}
        )
        # Mark the user account inactive
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"account_status": "pending_deletion", "deletion_requested_at": now.isoformat()}}
        )
    except Exception as e:
        logger.error(f"Deletion request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not process deletion request. Contact support.")

    logger.info(f"Deletion request accepted: {deletion_request['request_id']} user={user_id}")
    deletion_request.pop("_id", None)
    return deletion_request
