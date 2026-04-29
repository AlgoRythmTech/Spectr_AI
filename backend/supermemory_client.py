"""
Supermemory integration — persistent per-user memory for long-running CA/lawyer
conversations.

Why this exists:
  CAs and lawyers run chat sessions that span days, weeks, and multiple matters.
  A single session can reach 30+ turns. Stuffing all of that into every Claude
  call is wasteful and context-window-bounded. Supermemory holds every turn as
  an indexed memory and retrieves just the relevant pieces per new query.

Integration contract:
  - Every user message and every assistant reply is persisted as a separate
    memory (fire-and-forget; never blocks the reply).
  - On each new user turn, we retrieve top-K semantically relevant memories
    scoped to the user and inject them into the LLM context.
  - Container-tag scheme: one tag per user — `spectr_user_{user_id}`. This
    dodges Supermemory's exact-match tag-array footgun. Matter ID is stored
    in metadata, so retrieval can still filter to a specific matter when
    needed via the metadata-filter API.

Failure mode:
  If Supermemory is unreachable or returns an error, we log and proceed
  without context. Memory is a quality enhancer, never a dependency.
"""

import os
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("supermemory_client")

_API_KEY = os.environ.get("SUPERMEMORY_API_KEY", "").strip()
_SM_ENABLED = bool(_API_KEY)

# Lazy-initialised clients (sync + async). We use the async client inside
# FastAPI handlers and the sync client only for startup self-tests.
_async_client = None
_sync_client = None


def _get_async_client():
    global _async_client
    if _async_client is not None:
        return _async_client
    if not _SM_ENABLED:
        return None
    try:
        from supermemory import AsyncSupermemory
        _async_client = AsyncSupermemory(api_key=_API_KEY)
        return _async_client
    except Exception as e:
        logger.warning(f"Supermemory AsyncClient init failed: {e}")
        return None


def _container_tag_for_user(user_id: str) -> str:
    """Single-tag-per-user convention. Dodges the exact-match tag-array
    footgun documented in Supermemory's filtering guide."""
    # Sanitise to avoid any control/special chars in the tag
    safe = "".join(c for c in (user_id or "unknown") if c.isalnum() or c in ("_", "-"))[:128]
    return f"spectr_user_{safe}"


# ═══════════════════════════════════════════════════════════════════════
# Save a conversation turn — fire-and-forget
# ═══════════════════════════════════════════════════════════════════════

async def save_turn(
    user_id: str,
    conversation_id: str,
    turn_index: int,
    role: str,  # "user" | "assistant"
    content: str,
    matter_id: Optional[str] = None,
    doc_ids: Optional[list] = None,
    mode: Optional[str] = None,
) -> None:
    """Persist a single chat turn to Supermemory.

    Called async fire-and-forget from the assistant query flow so reply latency
    is never affected by Supermemory's eventual-consistency ingest queue.
    """
    if not _SM_ENABLED:
        return
    client = _get_async_client()
    if client is None or not content or len(content) < 3:
        return

    tag = _container_tag_for_user(user_id)
    # customId enables upsert/dedup if the same turn is retried
    custom_id = f"conv_{conversation_id}_turn_{turn_index:03d}_{role}"

    # Cap content size — Supermemory accepts big docs but 16K is plenty per turn
    # and keeps ingest latency + cost bounded
    trimmed = content[:16000]

    # Metadata must be primitive types only (string/number/bool)
    metadata = {
        "role": role,
        "conversation_id": conversation_id,
        "turn_index": int(turn_index),
        "saved_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if matter_id:
        metadata["matter_id"] = str(matter_id)[:128]
    if mode:
        metadata["mode"] = str(mode)[:32]
    if doc_ids:
        # Comma-separated string — metadata doesn't accept arrays
        metadata["doc_ids"] = ",".join(str(d) for d in doc_ids)[:500]

    try:
        # SDK 3.34: documents.add. Use `container_tag` singular (not
        # container_tags list) — matches Supermemory's recommended single-tag
        # pattern that avoids the exact-array-match footgun on search.
        await client.documents.add(
            content=trimmed,
            container_tag=tag,
            custom_id=custom_id,
            metadata=metadata,
        )
        logger.debug(f"Supermemory saved: {custom_id} ({len(trimmed)} chars)")
    except Exception as e:
        # Never block the reply — just log and move on
        logger.warning(f"Supermemory save_turn failed: {type(e).__name__}: {str(e)[:120]}")


def save_turn_background(user_id: str, **kwargs) -> None:
    """Fire-and-forget wrapper. Schedules save_turn() as a detached task
    so the caller returns immediately."""
    if not _SM_ENABLED or not user_id:
        return
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(save_turn(user_id=user_id, **kwargs))
        else:
            # Shouldn't happen in FastAPI handlers but defend anyway
            loop.create_task(save_turn(user_id=user_id, **kwargs))
    except Exception as e:
        logger.warning(f"Supermemory background schedule failed: {e}")


# ═══════════════════════════════════════════════════════════════════════
# Retrieve context before generating the reply
# ═══════════════════════════════════════════════════════════════════════

async def retrieve_context(
    user_id: str,
    query: str,
    limit: int = 6,
    matter_id: Optional[str] = None,
    timeout_s: float = 4.0,
) -> str:
    """Return a formatted context block of prior-turn memories relevant to the
    current query, scoped to the user. Empty string if Supermemory is off,
    times out, or has no results.

    Format is designed to inject directly into Claude's user-content block
    ahead of the new query — each chunk is tagged with its role + matter
    so Claude can weight it appropriately.
    """
    if not _SM_ENABLED:
        return ""
    client = _get_async_client()
    if client is None or not user_id or not query or len(query) < 5:
        return ""

    tag = _container_tag_for_user(user_id)

    # Build optional metadata filter for matter-scoped retrieval.
    # Using `container_tag` singular — matches the save-side convention.
    # We use search.memories (not search.documents) because memories are the
    # atomic extracted facts — exactly what we want to inject into LLM context.
    # search.documents returns whole-document-level hits which is the wrong
    # granularity for multi-turn chat memory retrieval.
    search_kwargs = {
        "q": query[:1000],
        "container_tag": tag,
        "limit": limit,
        "rerank": True,
        "rewrite_query": True,  # improves recall for terse user turns
    }
    if matter_id:
        # Supermemory supports AND filters on metadata
        search_kwargs["filters"] = {"AND": [{"key": "matter_id", "value": matter_id}]}

    try:
        res = await asyncio.wait_for(
            client.search.memories(**search_kwargs),
            timeout=timeout_s,
        )
    except asyncio.TimeoutError:
        logger.info(f"Supermemory search timed out after {timeout_s}s — proceeding without context")
        return ""
    except Exception as e:
        logger.warning(f"Supermemory search failed: {type(e).__name__}: {str(e)[:120]}")
        return ""

    results = getattr(res, "results", None) or []
    if not results:
        return ""

    lines = [
        "=== PRIOR CONVERSATION CONTEXT (from long-term memory) ===",
        "These are the most relevant fragments from this user's earlier Spectr sessions,",
        "ranked by semantic similarity to the current query. Use them to avoid re-asking",
        "facts the user has already established; reference them only when directly relevant.",
        "",
    ]
    seen_chunks = set()
    for r in results[:limit]:
        # SDK returns objects with .memory and/or .chunk
        memory = getattr(r, "memory", None) or ""
        chunk = getattr(r, "chunk", None) or ""
        similarity = getattr(r, "similarity", None) or 0
        md = getattr(r, "metadata", None) or {}
        role = (md.get("role") or "note").upper() if isinstance(md, dict) else "NOTE"
        matter = md.get("matter_id") if isinstance(md, dict) else None

        # Prefer the atomic extracted memory; fall back to the raw chunk
        snippet = (memory or chunk).strip()
        if not snippet or snippet in seen_chunks:
            continue
        seen_chunks.add(snippet)
        snippet = snippet[:1200]  # cap each fragment

        tag_bits = [role]
        if matter:
            tag_bits.append(f"matter={matter}")
        tag_bits.append(f"sim={similarity:.2f}")
        header = " · ".join(tag_bits)

        lines.append(f"• [{header}] {snippet}")

    if len(lines) <= 5:  # just the header lines, no fragments
        return ""

    lines.append("")
    lines.append("=== END PRIOR CONTEXT ===")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# Health / self-test
# ═══════════════════════════════════════════════════════════════════════

async def health_check() -> dict:
    """Quick probe for startup logs — confirms the key works."""
    if not _SM_ENABLED:
        return {"enabled": False, "reason": "SUPERMEMORY_API_KEY not set"}
    client = _get_async_client()
    if client is None:
        return {"enabled": False, "reason": "SDK init failed"}
    try:
        # A search against a dummy tag that returns nothing is cheap + confirms auth
        await asyncio.wait_for(
            client.search.memories(
                q="health probe", container_tag="__spectr_health_probe__", limit=1
            ),
            timeout=5.0,
        )
        return {"enabled": True, "status": "reachable"}
    except Exception as e:
        return {"enabled": True, "status": "unreachable", "error": str(e)[:160]}
