"""
statutory_thresholds.py — Dynamic statutory thresholds from MongoDB.

Finance Act amendments change thresholds, rates, and slab structures every year.
Hardcoding them in the system prompt means stale advice. This module:
  1. Fetches current values from `statutory_thresholds` collection in MongoDB
  2. Caches them with a configurable TTL (default 1 hour)
  3. Returns formatted prompt text for injection into SPECTR_SYSTEM_PROMPT

If the collection doesn't exist or is empty, falls back to hardcoded defaults
(the values that were previously inline in the prompt).
"""

import os
import time
import logging
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URL", os.getenv("MONGO_URI", "mongodb://localhost:27017"))
client = AsyncIOMotorClient(MONGO_URI)
db = client["associate_db"]
thresholds_collection = db["statutory_thresholds"]

# ── Cache ────────────────────────────────────────────────────────────
_cache: dict = {}
_cache_ts: float = 0.0
CACHE_TTL: int = 3600  # 1 hour

# ── Hardcoded fallbacks (last known good — Finance Act 2025) ─────────
DEFAULTS = {
    # Income Tax — New Regime slabs (AY 2026-27)
    "new_regime_slabs": (
        "0-4L (nil), 4-8L (5%), 8-12L (10%), 12-16L (15%), "
        "16-20L (20%), 20-24L (25%), 24L+ (30%)"
    ),
    "new_regime_effective_ay": "2026-27",
    "new_regime_statute": "Section 115BAC as amended by Finance Act 2025",

    # Section 87A Rebate
    "s87a_rebate_amount": "60,000",
    "s87a_income_limit": "12,00,000",
    "s87a_effective_ay": "2026-27",
    "s87a_regime": "new regime",

    # Section 194T — TDS on partner payments
    "s194t_threshold": "20,000",
    "s194t_rate": "10%",
    "s194t_effective_date": "01-04-2025",

    # Rule 36(4) CGST Rules
    "rule_36_4_status": (
        "Provisional ITC concept (20%/10%/5% beyond GSTR-2B) was ABOLISHED "
        "w.e.f. 01-01-2022 by Notification 40/2021-CT. Rule 36(4) now restricts "
        "ITC availment to 100% of what appears in GSTR-2B. Do NOT say Rule 36(4) "
        'was "removed" — it was AMENDED to impose a stricter 100% cap.'
    ),

    # GSTR-9C certification
    "gstr9c_self_cert_from": "FY 2020-21",
    "gstr9c_notification": "Notification 30/2021-CT",

    # Section 16(4) CGST — ITC time limit
    "s16_4_deadline": "30th November of the following year",
    "s16_4_amended_by": "Finance Act 2022",

    # Section 73/74 CGST — limitation periods
    "s73_limitation_years": "3",
    "s74_limitation_years": "5",

    # Section 269SS/269T cash limit
    "s269ss_cash_limit": "20,000",

    # Section 270A penalty rates
    "s270a_underreporting_rate": "50%",
    "s270a_misreporting_rate": "200%",

    # Section 43B — PF/ESI case law
    "s43b_landmark_case": "Checkmate Fiscal Services — SC 2023",

    # Goodwill depreciation exclusion
    "goodwill_exclusion_effective_ay": "2021-22",
    "goodwill_exclusion_amendment": "Finance Act 2021",

    # Audit trail / edit log
    "audit_trail_effective_fy": "2023-24",
    "audit_trail_notification": "MCA Notification dated 24-03-2021 (effective 01-04-2023)",

    # Old Tax Regime default cutoff
    "default_new_regime_from_ay": "2026-27",
}


async def _fetch_from_db() -> dict:
    """Fetch all thresholds from MongoDB."""
    try:
        cursor = thresholds_collection.find({}, {"_id": 0})
        docs = await cursor.to_list(length=200)
        if not docs:
            return {}
        # Flatten: each doc has {"key": "...", "value": "..."}
        result = {}
        for doc in docs:
            k = doc.get("key")
            v = doc.get("value")
            if k and v is not None:
                result[k] = str(v)
        return result
    except Exception as e:
        logger.warning(f"Failed to fetch statutory thresholds from DB: {e}")
        return {}


async def get_thresholds() -> dict:
    """Get current thresholds (DB with cache, fallback to defaults)."""
    global _cache, _cache_ts

    now = time.time()
    if _cache and (now - _cache_ts) < CACHE_TTL:
        return _cache

    db_values = await _fetch_from_db()
    if db_values:
        # Merge: DB overrides defaults
        merged = {**DEFAULTS, **db_values}
        logger.info(f"Statutory thresholds loaded from DB: {len(db_values)} overrides")
    else:
        merged = dict(DEFAULTS)
        logger.info("Statutory thresholds: using hardcoded defaults (DB empty or unavailable)")

    _cache = merged
    _cache_ts = now
    return merged


async def build_amendment_guardrail() -> str:
    """Build the AMENDMENT-AWARENESS GUARDRAIL prompt section from current thresholds.

    This replaces the previously hardcoded block in SPECTR_SYSTEM_PROMPT.
    """
    t = await get_thresholds()

    return f"""
## AMENDMENT-AWARENESS GUARDRAIL (MANDATORY — LIVE FROM DATABASE)

Before citing ANY statutory provision, you MUST internally verify:
1. **Is this the CURRENT version of the provision?** Many provisions have been amended, substituted, or omitted post-2020.
2. **Known stale provisions you MUST NOT cite in their old form:**
   - Rule 36(4) CGST Rules — {t['rule_36_4_status']}
   - GSTR-9C (Annual Reconciliation) — CA/CMA certification requirement was REMOVED w.e.f. {t['gstr9c_self_cert_from']} by {t['gstr9c_notification']}. It is now self-certified.
   - Section 16(4) CGST Act — time limit for claiming ITC was AMENDED by {t['s16_4_amended_by']}. The new deadline is {t['s16_4_deadline']} (not the earlier September deadline).
   - Section 73/74 CGST Act — Section 74 requires proof of fraud/suppression. Section 73 is for non-fraud cases. These have different limitation periods ({t['s73_limitation_years']} years vs {t['s74_limitation_years']} years).
   - Old Tax Regime slabs — if the query is about AY {t['default_new_regime_from_ay']} or later, DEFAULT to the New Tax Regime under {t['new_regime_statute']} unless the taxpayer explicitly opts out.
   - Section 194T (TDS on partner payments) — NEW provision effective {t['s194t_effective_date']}. Threshold ₹{t['s194t_threshold']}. Rate {t['s194t_rate']}.
   - Section 87A Rebate — enhanced to ₹{t['s87a_rebate_amount']} for income up to ₹{t['s87a_income_limit']} under {t['s87a_regime']} from AY {t['s87a_effective_ay']}.
   - Section 32 Depreciation on Goodwill — {t['goodwill_exclusion_amendment']} EXCLUDED goodwill from depreciable assets w.e.f. AY {t['goodwill_exclusion_effective_ay']}. Do NOT cite CIT v. Smifs Securities (2012 SC) for goodwill depreciation post-AY 2020-21. Smifs Securities STILL applies to other intangibles (patents, copyrights, trademarks, licences, software IP).
   - Section 43(1) Actual Cost — For non-monetary (barter) acquisitions, "actual cost" is determined by fair market value at the date of acquisition per Section 43(1), Explanation 2 and 3. Do NOT cite cases on revaluation reserves (like Indo Rama Synthetics) for barter acquisition valuation — the controlling provision is Section 43(1) itself.
   - Audit Trail (Edit Log) — Companies (Accounts) Rules, 2014, Rule 3(1) as amended by {t['audit_trail_notification']}. MANDATORY for all companies from FY {t['audit_trail_effective_fy']}. Every accounting software must record an edit log with timestamp and user ID. NEVER omit this for Companies Act disclosure queries.
3. **If you are unsure whether a provision has been amended**, state: *"[Note: This provision may have been amended. Verify the current text from the e-Gazette or official bare act before relying on this.]"*
4. **Always state the effective date** of the provision you are citing. If you cannot state the effective date, that is a red flag that you may be citing a stale version.
"""


async def build_hard_negative_tax_slabs() -> str:
    """Build the tax slab portion of the HARD NEGATIVE RULES from current thresholds."""
    t = await get_thresholds()

    return (
        f"9. **When advising on new regime tax calculations for AY {t['new_regime_effective_ay']}**: "
        f"The slab structure is {t['new_regime_slabs']}. "
        f"Rebate under Section 87A makes tax NIL for income up to ₹{t['s87a_income_limit']}. "
        f"Marginal relief applies for income slightly above ₹{t['s87a_income_limit']}."
    )


async def seed_defaults_if_empty():
    """Seed the statutory_thresholds collection with defaults if it's empty.

    Call this on server startup so operators can see/edit values in MongoDB.
    """
    try:
        count = await thresholds_collection.count_documents({})
        if count > 0:
            logger.info(f"Statutory thresholds collection already has {count} documents")
            return

        docs = []
        for key, value in DEFAULTS.items():
            docs.append({
                "key": key,
                "value": str(value),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "source": "hardcoded_defaults_seed",
            })

        await thresholds_collection.insert_many(docs)
        logger.info(f"Seeded {len(docs)} statutory thresholds into MongoDB")
    except Exception as e:
        logger.warning(f"Failed to seed statutory thresholds (non-blocking): {e}")
