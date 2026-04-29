"""
Usage Tracker + Per-User Rate Limiter.

Tracks daily usage per user for each billable action:
  - queries      (LLM calls)
  - files        (file uploads to executor)
  - deep_research (5-phase sandbox runs)
  - drive_uploads
  - sandbox_minutes

Enforces limits from config_loader (tier-based in multi-tenant, fixed in dedicated).

Storage: MongoDB `usage_daily` collection, keyed by (user_id, date).
Upsert is idempotent; increments are atomic via $inc.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger("usage_tracker")

USAGE_COLLECTION = "usage_daily"


async def ensure_usage_index(db):
    """Create index on usage_daily. Call once at startup."""
    try:
        coll = getattr(db, USAGE_COLLECTION)
        await coll.create_index([("user_id", 1), ("date", 1)], unique=True)
        # Keep 90 days of daily usage
        await coll.create_index("date_ts", expireAfterSeconds=90 * 24 * 60 * 60)
        logger.info("Usage tracker indexes ensured")
    except Exception as e:
        logger.warning(f"Usage index creation failed: {e}")


def _today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


async def get_usage(db, user_id: str, date: Optional[str] = None) -> dict:
    """Get today's usage counters for a user."""
    date = date or _today_key()
    try:
        doc = await getattr(db, USAGE_COLLECTION).find_one(
            {"user_id": user_id, "date": date},
            {"_id": 0},
        )
        return doc or {"user_id": user_id, "date": date}
    except Exception as e:
        logger.warning(f"Get usage failed: {e}")
        return {"user_id": user_id, "date": date}


async def increment_usage(db, user_id: str, field: str, amount: int = 1):
    """Atomically increment a usage counter."""
    date = _today_key()
    try:
        await getattr(db, USAGE_COLLECTION).update_one(
            {"user_id": user_id, "date": date},
            {
                "$inc": {field: amount},
                "$setOnInsert": {
                    "user_id": user_id,
                    "date": date,
                    "date_ts": datetime.now(timezone.utc),
                },
            },
            upsert=True,
        )
    except Exception as e:
        logger.warning(f"Increment usage failed for {user_id}.{field}: {e}")


async def check_limit(db, user_id: str, field: str, limit: int) -> dict:
    """Check if user is under limit. Returns {allowed, current, limit, remaining}."""
    usage = await get_usage(db, user_id)
    current = usage.get(field, 0)
    remaining = max(0, limit - current)
    return {
        "allowed": current < limit,
        "current": current,
        "limit": limit,
        "remaining": remaining,
        "reset_at": (datetime.now(timezone.utc) + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat(),
    }


async def enforce_limit(db, user_id: str, field: str, limit: int):
    """Raise HTTPException if user is over limit. Use at start of endpoints."""
    from fastapi import HTTPException
    check = await check_limit(db, user_id, field, limit)
    if not check["allowed"]:
        raise HTTPException(
            status_code=429,
            detail={
                "error": f"Daily limit exceeded for {field}",
                "limit": check["limit"],
                "current": check["current"],
                "reset_at": check["reset_at"],
                "upgrade_url": "/pricing",
            },
        )


async def get_user_tier(db, user_id: str) -> str:
    """Get user's tier from users collection. Defaults to 'free'."""
    try:
        user = await db.users.find_one({"user_id": user_id}, {"tier": 1, "_id": 0})
        if user:
            return user.get("tier", "free")
    except Exception:
        pass
    return "free"


async def get_limit_for_user(db, user_id: str, limit_key: str) -> int:
    """Resolve user's limit for a given action via config_loader + their tier."""
    from config_loader import get_config
    config = get_config()

    if config.is_dedicated:
        # Dedicated firms have fixed high limits
        return config.tier_limit("", limit_key, default=99999)

    tier = await get_user_tier(db, user_id)
    return config.tier_limit(tier, limit_key, default=0)


async def check_and_track(db, user_id: str, field: str):
    """Combined helper: check limit → increment on success → raise if over.

    Usage at start of protected endpoints:
        await check_and_track(db, user['user_id'], 'max_queries_per_day')
    """
    limit = await get_limit_for_user(db, user_id, field)
    await enforce_limit(db, user_id, field, limit)
    await increment_usage(db, user_id, field)


# Convenience action shortcuts
async def track_query(db, user_id: str):
    await check_and_track(db, user_id, "max_queries_per_day")


async def track_deep_research(db, user_id: str):
    await check_and_track(db, user_id, "max_deep_research_per_day")


async def track_drive_upload(db, user_id: str):
    await check_and_track(db, user_id, "max_drive_uploads_per_day")


async def track_file_upload(db, user_id: str):
    await check_and_track(db, user_id, "max_files_upload")


async def get_user_dashboard(db, user_id: str) -> dict:
    """Return usage + limits overview for the user's account page."""
    tier = await get_user_tier(db, user_id)
    usage = await get_usage(db, user_id)
    from config_loader import get_config
    config = get_config()

    limits = {}
    for key in ("max_queries_per_day", "max_deep_research_per_day",
                "max_drive_uploads_per_day", "max_files_upload"):
        l = await get_limit_for_user(db, user_id, key)
        current = usage.get(key, 0)
        limits[key] = {
            "limit": l,
            "used": current,
            "remaining": max(0, l - current),
            "pct": round(100 * current / l, 1) if l > 0 else 0,
        }

    return {
        "user_id": user_id,
        "tier": tier,
        "date": usage.get("date", _today_key()),
        "usage": limits,
        "firm": config.firm_short,
        "mode": "dedicated" if config.is_dedicated else "multi_tenant",
    }
