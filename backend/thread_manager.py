"""
thread_manager.py — Claude-style chat threading on top of query_history.

Design
------
We keep the existing `query_history` collection (one doc per user message +
assistant response) and add a new `threads` collection that groups those
messages by thread_id. Each thread has:

  thread_id    str   — unique, generated on first message
  user_id      str   — owner (scoping all queries)
  title        str   — auto-generated from first user query (Claude does this)
  created_at   iso8601
  updated_at   iso8601
  message_count int
  last_preview str  — first ~200 chars of the latest assistant response

Auto-titling
------------
First-pass title: truncate user's first query to ~60 chars (cheap, instant).
Second-pass title (background): a ~5-word smart title like "GST Section 73
notice reply" via a small LLM call. Swapped in atomically on the thread doc
once ready, so the sidebar refresh shows the nicer title.

Context retention
-----------------
When a follow-up message arrives with thread_id set, we fetch the last N
messages from query_history for that thread and prepend them as conversation
history to the LLM prompt. This is the "continuing the chat" mechanism.

Supermemory
-----------
Optional — if SUPERMEMORY_API_KEY env is set, after each turn we store a
memory for the user ("user asked X, got answer Y") and retrieve matching
memories before each new query for broader context (e.g. "last month user
was working on matter Z"). See supermemory_client.py.
"""
import os
import re
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("thread_manager")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_thread_id() -> str:
    return f"thr_{uuid.uuid4().hex[:14]}"


# ─── Auto-title generation ────────────────────────────────────────────────
_STOPWORDS = {"what", "is", "the", "a", "an", "of", "in", "for", "to", "on",
              "and", "or", "how", "do", "does", "can", "please", "tell", "me",
              "about", "would", "could", "should", "whether", "are", "which"}


def quick_title(query: str, max_len: int = 60) -> str:
    """Fast, deterministic title from the first user query.

    Used immediately so the sidebar shows something sensible while the
    background LLM title job runs. Strategy:
      - strip question marks, collapse whitespace
      - if the query starts with a stopword, skip forward to the first
        content word ("What is section 73 CGST?" -> "Section 73 CGST")
      - truncate at word boundary near max_len
    """
    q = re.sub(r"\s+", " ", (query or "").strip()).rstrip("?!. ")
    if not q:
        return "New chat"

    words = q.split()
    # Skip leading stopwords/fillers
    start = 0
    while start < len(words) - 1 and words[start].lower() in _STOPWORDS:
        start += 1
    trimmed = " ".join(words[start:])
    # Capitalize first letter
    trimmed = trimmed[:1].upper() + trimmed[1:] if trimmed else ""

    if len(trimmed) <= max_len:
        return trimmed
    # Truncate on a word boundary
    cut = trimmed[:max_len]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "…"


async def llm_title(query: str, response_preview: str = "") -> Optional[str]:
    """Smart 3-6 word title via a cheap LLM call.

    Called in the background after the main response streams — if it
    succeeds, we update the thread's title field atomically. If the LLM
    call fails (rate limit, no key, etc.), we silently keep the quick_title.
    """
    try:
        # Lazy import so this module stays light if emergent LLM isn't configured
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        api_key = os.environ.get("EMERGENT_LLM_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return None

        prompt = (
            "You are a title generator. Given a legal/tax/finance question "
            "and the start of the answer, output a concise 3-6 word title "
            "for the conversation. No quotes, no punctuation at end. "
            "Examples:\n"
            '  Q: "what does section 194T of Income Tax Act say about TDS on partners"\n'
            '  Title: Section 194T partner TDS\n'
            '  Q: "help me draft a reply to a GST notice under section 73"\n'
            '  Title: GST Section 73 notice reply\n\n'
            f"Q: {query[:500]}\n"
            + (f"Answer starts with: {response_preview[:300]}\n" if response_preview else "")
            + "Title:"
        )

        chat = LlmChat(
            api_key=api_key,
            session_id=f"title_{uuid.uuid4().hex[:8]}",
            system_message="You generate short, specific titles.",
        ).with_model("openai", "gpt-4o-mini").with_max_tokens(40)
        resp = await chat.send_message(UserMessage(text=prompt))
        if not resp:
            return None

        title = resp.strip().strip('"').strip("'").rstrip(".!?,")
        # Cap length and sanity-check
        if 3 <= len(title) <= 60 and " " in title:
            return title
        return None
    except Exception as e:
        logger.debug(f"llm_title failed (non-blocking): {e}")
        return None


# ─── Thread CRUD ──────────────────────────────────────────────────────────
async def ensure_thread(db, user_id: str, thread_id: Optional[str],
                         first_query: str, matter_id: Optional[str] = None) -> str:
    """Get an existing thread id or create a new one.

    Returns the canonical thread_id to attach to the current message.
    If thread_id is None/blank, we create a new thread row with a
    quick_title and schedule an llm_title upgrade.
    """
    if thread_id:
        # Verify ownership; if valid, bump updated_at and return
        try:
            existing = await db.threads.find_one(
                {"thread_id": thread_id, "user_id": user_id}, {"_id": 0}
            )
            if existing:
                await db.threads.update_one(
                    {"thread_id": thread_id, "user_id": user_id},
                    {"$set": {"updated_at": now_iso()},
                     "$inc": {"message_count": 1}}
                )
                return thread_id
            # Unknown thread_id — fall through and create a new one. We don't
            # surface an error because a stale tab or cleared DB shouldn't
            # break the user's message.
            logger.info(f"Unknown thread_id {thread_id} for user {user_id}; creating new thread")
        except Exception as e:
            logger.warning(f"ensure_thread lookup failed: {e}")

    # Create a new thread
    tid = new_thread_id()
    title = quick_title(first_query)
    doc = {
        "thread_id": tid,
        "user_id": user_id,
        "matter_id": matter_id,
        "title": title,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "message_count": 1,
        "last_preview": "",
    }
    try:
        await db.threads.insert_one(doc)
    except Exception as e:
        logger.warning(f"thread insert failed (continuing): {e}")
    return tid


async def update_thread_after_response(db, thread_id: str, user_id: str,
                                        response_preview: str,
                                        try_llm_title: bool = True,
                                        original_query: str = ""):
    """Called after the assistant's response streams. Updates last_preview and,
    if the thread still has a quick_title (no LLM title yet), kicks off a
    background LLM title generation."""
    try:
        # Always bump the preview for the sidebar
        await db.threads.update_one(
            {"thread_id": thread_id, "user_id": user_id},
            {"$set": {"last_preview": response_preview[:240],
                      "updated_at": now_iso()}}
        )
    except Exception as e:
        logger.warning(f"update_thread preview failed: {e}")

    if not try_llm_title:
        return

    async def _bg_title():
        # Only re-title if the thread is still on its first message and
        # the current title looks like the auto-truncated quick_title.
        try:
            t = await db.threads.find_one(
                {"thread_id": thread_id, "user_id": user_id}, {"_id": 0}
            )
            if not t or t.get("message_count", 0) > 1:
                return  # user already followed up; keep whatever title is there
            new_title = await llm_title(original_query, response_preview)
            if new_title:
                await db.threads.update_one(
                    {"thread_id": thread_id, "user_id": user_id},
                    {"$set": {"title": new_title}}
                )
                logger.info(f"thread {thread_id} titled: {new_title!r}")
        except Exception as e:
            logger.debug(f"bg llm title failed (silent): {e}")

    asyncio.create_task(_bg_title())


async def list_threads(db, user_id: str, limit: int = 50) -> list[dict]:
    try:
        rows = await db.threads.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort("updated_at", -1).limit(limit).to_list(limit)
        return rows
    except Exception as e:
        logger.warning(f"list_threads failed: {e}")
        return []


async def load_thread_messages(db, user_id: str, thread_id: str,
                                limit: int = 40) -> list[dict]:
    """Return messages for a thread, oldest → newest, scoped to the owner."""
    try:
        rows = await db.query_history.find(
            {"thread_id": thread_id, "user_id": user_id}, {"_id": 0}
        ).sort("created_at", 1).limit(limit).to_list(limit)
        return rows
    except Exception as e:
        logger.warning(f"load_thread_messages failed: {e}")
        return []


async def delete_thread(db, user_id: str, thread_id: str) -> bool:
    """Delete a thread AND its messages. Returns True if the thread existed."""
    try:
        existing = await db.threads.find_one(
            {"thread_id": thread_id, "user_id": user_id}, {"_id": 0}
        )
        if not existing:
            return False
        await db.threads.delete_one({"thread_id": thread_id, "user_id": user_id})
        # Cascade delete messages
        try:
            await db.query_history.delete_many({"thread_id": thread_id, "user_id": user_id})
        except Exception as e:
            logger.warning(f"cascade delete of thread messages failed: {e}")
        return True
    except Exception as e:
        logger.warning(f"delete_thread failed: {e}")
        return False


async def rename_thread(db, user_id: str, thread_id: str, new_title: str) -> bool:
    new_title = (new_title or "").strip()[:80]
    if not new_title:
        return False
    try:
        r = await db.threads.update_one(
            {"thread_id": thread_id, "user_id": user_id},
            {"$set": {"title": new_title, "updated_at": now_iso()}}
        )
        return bool(getattr(r, "matched_count", 0))
    except Exception as e:
        logger.warning(f"rename_thread failed: {e}")
        return False


# ─── Context assembly for follow-ups ──────────────────────────────────────
def assemble_history_for_llm(messages: list[dict], max_chars: int = 8000) -> list[dict]:
    """Turn thread messages into the conversation_history list that
    ai_engine.process_natural_query expects.

    Each history item becomes two role/content entries (user + assistant).
    We trim oldest messages if total character count exceeds max_chars so the
    LLM context stays bounded even on long threads.
    """
    out = []
    total = 0
    # Walk messages newest→oldest, accumulate until budget; reverse at end
    reversed_msgs = list(reversed(messages))
    picked = []
    for m in reversed_msgs:
        q = (m.get("query") or "").strip()
        r = (m.get("response_text") or "").strip()
        if not q:
            continue
        entry_size = len(q) + len(r) + 20
        if total + entry_size > max_chars and picked:
            break
        picked.append(m)
        total += entry_size
    # Reverse back to chronological order
    picked = list(reversed(picked))

    for m in picked:
        q = (m.get("query") or "").strip()
        r = (m.get("response_text") or "").strip()
        if q:
            out.append({"role": "user", "content": q})
        if r:
            out.append({"role": "assistant", "content": r})
    return out


async def ensure_indexes(db):
    """Create Firestore/Mongo indexes needed for thread queries."""
    try:
        await db.threads.create_index([("user_id", 1), ("updated_at", -1)])
        await db.query_history.create_index([("thread_id", 1), ("created_at", 1)])
        logger.info("thread_manager indexes ensured")
    except Exception as e:
        logger.debug(f"thread index creation skipped (non-blocking): {e}")
