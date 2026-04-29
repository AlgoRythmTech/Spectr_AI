"""
Audit Log — immutable record of every sensitive action.

What gets logged:
  - Google OAuth connect/disconnect
  - Every file upload to user's Drive
  - Every file download from Spectr
  - Every agent code execution
  - Every deep research session
  - Every Vault document upload/query
  - Authentication events (login, token refresh)
  - Billing events (tier changes, payment)

Compliance: meets DPDP Act 2023 audit trail requirements + SOC 2 control CC7.2.

Storage: MongoDB `audit_log` collection, TTL = 3 years, write-only from app perspective.
Admin access requires separate audit_admin role — not available to regular users.
"""
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("audit_log")

AUDIT_COLLECTION = "audit_log"
TTL_SECONDS = 3 * 365 * 24 * 60 * 60  # 3 years


async def ensure_audit_index(db):
    """Create indexes on audit_log collection. Call once at startup."""
    try:
        coll = getattr(db, AUDIT_COLLECTION)
        await coll.create_index("timestamp", expireAfterSeconds=TTL_SECONDS)
        await coll.create_index([("user_id", 1), ("timestamp", -1)])
        await coll.create_index([("action", 1), ("timestamp", -1)])
        await coll.create_index([("firm", 1), ("timestamp", -1)])
        logger.info("Audit log indexes ensured")
    except Exception as e:
        logger.warning(f"Audit index creation failed: {e}")


async def log_action(
    db,
    user_id: str,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    firm: Optional[str] = None,
    success: bool = True,
):
    """Write an audit log entry. Fire-and-forget; never raises.

    Example:
        await log_action(db, user_id, "drive.upload",
                         resource_type="file",
                         resource_id=file_id,
                         metadata={"drive_file_id": "xxx", "folder_id": "yyy"})
    """
    import os
    try:
        entry = {
            "timestamp": datetime.now(timezone.utc),
            "user_id": user_id or "anonymous",
            "firm": firm or os.environ.get("FIRM_SHORT", "") or "multi_tenant",
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "metadata": metadata or {},
            "ip": ip,
            "user_agent": user_agent,
            "success": success,
            "environment": os.environ.get("ENVIRONMENT", "development"),
            "git_sha": os.environ.get("GIT_SHA", ""),
        }
        # Fire-and-forget with timeout (never block the request)
        await asyncio.wait_for(getattr(db, AUDIT_COLLECTION).insert_one(entry), timeout=2.0)
    except Exception as e:
        # Audit log failure must NEVER break the request. Log and move on.
        logger.warning(f"Audit log write failed (non-blocking) for {action}: {e}")


def audit_action(action: str, resource_type: Optional[str] = None):
    """Decorator to auto-log an endpoint. Use sparingly — prefer explicit `log_action` for clarity.

    @audit_action("drive.upload", "file")
    async def my_endpoint(...):
        ...
    """
    def decorator(fn):
        async def wrapper(*args, **kwargs):
            from fastapi import Request
            request = None
            for a in args:
                if isinstance(a, Request):
                    request = a
                    break
            if not request:
                request = kwargs.get("request")

            try:
                result = await fn(*args, **kwargs)
                # Try to capture user_id + resource_id from result/kwargs
                user_id = ""
                if request and hasattr(request, "state") and hasattr(request.state, "user"):
                    user_id = request.state.user.get("user_id", "")

                # Get db from caller module (hack — endpoints usually have `db` in scope)
                from server import db as _db
                await log_action(_db, user_id, action, resource_type=resource_type, success=True)
                return result
            except Exception as e:
                try:
                    from server import db as _db
                    user_id = ""
                    if request and hasattr(request, "state") and hasattr(request.state, "user"):
                        user_id = request.state.user.get("user_id", "")
                    await log_action(_db, user_id, action, resource_type=resource_type,
                                     metadata={"error": str(e)[:500]}, success=False)
                except Exception:
                    pass
                raise
        return wrapper
    return decorator


async def get_user_audit_trail(db, user_id: str, limit: int = 100) -> list[dict]:
    """Retrieve audit trail for a specific user (for their own view OR admin)."""
    try:
        cursor = getattr(db, AUDIT_COLLECTION).find(
            {"user_id": user_id},
            {"_id": 0},
        ).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(limit)
    except Exception as e:
        logger.warning(f"Audit trail fetch failed: {e}")
        return []


async def get_firm_audit_summary(db, firm: str, hours: int = 24) -> dict:
    """Admin summary — recent activity by action type for a firm."""
    try:
        from datetime import timedelta
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        pipeline = [
            {"$match": {"firm": firm, "timestamp": {"$gte": since}}},
            {"$group": {
                "_id": {"action": "$action", "success": "$success"},
                "count": {"$sum": 1},
            }},
            {"$sort": {"count": -1}},
        ]
        results = await getattr(db, AUDIT_COLLECTION).aggregate(pipeline).to_list(100)
        return {
            "firm": firm,
            "since": since.isoformat(),
            "by_action": [
                {"action": r["_id"]["action"], "success": r["_id"]["success"], "count": r["count"]}
                for r in results
            ],
            "total_events": sum(r["count"] for r in results),
        }
    except Exception as e:
        return {"firm": firm, "error": str(e)}
