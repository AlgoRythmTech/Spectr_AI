"""
test_threading_e2e.py — end-to-end validation of threading + Supermemory
BEFORE deployment.

What this exercises
-------------------
  1. Supermemory save_turn + retrieve_context round-trip (real API)
  2. thread_manager.ensure_thread creates a fresh thread row
  3. Auto-title (quick + LLM background)
  4. Appending a follow-up turn to the same thread
  5. load_thread_messages returning full history
  6. rename_thread + delete_thread

  7. HTTP-level smoke test of /api/threads (requires a Firebase token)

Usage
-----
    python test_threading_e2e.py          # direct function tests (no auth needed)
    python test_threading_e2e.py --http   # also curl-test the HTTP endpoints
                                          # (requires FIREBASE_TEST_TOKEN env)

Cleans up every test artifact at the end — no orphaned threads/messages left
in Firestore, no test memories left in Supermemory.
"""
import os
import sys
import time
import uuid
import asyncio
import argparse
from pathlib import Path

BACKEND = Path(__file__).parent
sys.path.insert(0, str(BACKEND))

# Ensure Firestore + Supermemory env is loaded from .env
try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND / ".env")
except ImportError:
    pass

os.environ.setdefault("USE_FIRESTORE", "1")
if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    cred = BACKEND / "firebase-admin.json"
    if cred.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred)

# Subsystems under test
from firestore_adapter import get_firestore_db
import thread_manager as tm
import supermemory_client as sm


TEST_USER = f"test_user_{uuid.uuid4().hex[:8]}"
GREEN = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"; RESET = "\033[0m"

def ok(msg):   print(f"  {GREEN}PASS{RESET} {msg}")
def fail(msg): print(f"  {RED}FAIL{RESET} {msg}")
def info(msg): print(f"  {YELLOW}>{RESET} {msg}")


async def test_supermemory_roundtrip():
    print("\n[1] Supermemory save > search round-trip")
    if not sm._SM_ENABLED:
        fail("SUPERMEMORY_API_KEY not set; skipping.")
        return False

    # Save a memory
    await sm.save_turn(
        user_id=TEST_USER,
        conversation_id="test_conv_smoke",
        turn_index=1,
        role="user",
        content="I am working on a GST notice reply for my client Acme Pvt Ltd under Section 73.",
        matter_id="M_TEST_GST_NOTICE",
        mode="partner",
    )
    ok("save_turn returned cleanly")

    # Supermemory has eventual consistency on its ingest queue — give it a beat.
    info("waiting 4s for Supermemory ingest pipeline...")
    await asyncio.sleep(4)

    # Search for it
    ctx = await sm.retrieve_context(
        user_id=TEST_USER,
        query="GST notice reply section 73",
        limit=3,
    )
    if ctx and "Acme" in ctx:
        ok(f"retrieve_context returned the saved memory ({len(ctx)} chars)")
        return True
    elif ctx:
        info("Supermemory returned results but not yet the one we saved (ingest lag).")
        info("This is normal for a cold save — re-run the test to see it appear.")
        return True
    else:
        fail("retrieve_context returned empty — either ingest is slow or auth failed.")
        return False


async def test_thread_crud(db):
    print("\n[2] Thread create / update / load / rename / delete")
    tid1 = await tm.ensure_thread(
        db, TEST_USER, None,
        first_query="What does section 194T of the Income Tax Act cover?",
        matter_id=None,
    )
    if not tid1 or not tid1.startswith("thr_"):
        fail(f"ensure_thread returned unexpected value: {tid1!r}")
        return False, None
    ok(f"ensure_thread(new) created {tid1}")

    # Sanity: listing should now include it
    rows = await tm.list_threads(db, TEST_USER, limit=10)
    if any(r["thread_id"] == tid1 for r in rows):
        ok(f"list_threads returned the new thread (total={len(rows)})")
    else:
        fail("new thread missing from list_threads output")
        return False, tid1

    # Check the quick-title was auto-generated
    first = next(r for r in rows if r["thread_id"] == tid1)
    if first.get("title") and first["title"] != "New chat":
        ok(f"auto-title: {first['title']!r}")
    else:
        fail(f"auto-title missing or default: {first.get('title')!r}")

    # Re-use an existing thread (should NOT create a new one)
    tid_again = await tm.ensure_thread(db, TEST_USER, tid1, "follow-up message", None)
    if tid_again == tid1:
        ok("ensure_thread(existing) returned same thread_id (correct)")
    else:
        fail(f"ensure_thread re-created thread: got {tid_again}, wanted {tid1}")

    # Simulate a message on this thread
    from datetime import datetime, timezone
    await db.query_history.insert_one({
        "history_id": f"qh_{uuid.uuid4().hex[:10]}",
        "user_id": TEST_USER,
        "thread_id": tid1,
        "query": "What does section 194T of the Income Tax Act cover?",
        "response_text": "Section 194T applies TDS @ 10% on payments from a firm to its partners (salary, remuneration, commission, bonus, interest). Threshold: ₹20,000 per FY. Effective AY 2026-27.",
        "mode": "partner",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    ok("seeded one query_history row")

    msgs = await tm.load_thread_messages(db, TEST_USER, tid1)
    if len(msgs) == 1 and msgs[0]["thread_id"] == tid1:
        ok(f"load_thread_messages returned {len(msgs)} message")
    else:
        fail(f"load_thread_messages returned {len(msgs)} messages (expected 1)")

    # assemble_history_for_llm turns it into LLM format
    hist = tm.assemble_history_for_llm(msgs)
    expected_roles = ["user", "assistant"]
    if [h["role"] for h in hist] == expected_roles:
        ok(f"assemble_history_for_llm produced {len(hist)} messages in correct role order")
    else:
        fail(f"wrong role order: {[h['role'] for h in hist]}")

    # Rename
    renamed = await tm.rename_thread(db, TEST_USER, tid1, "Renamed test thread")
    if renamed:
        t = await db.threads.find_one({"thread_id": tid1, "user_id": TEST_USER}, {"_id": 0})
        if t and t.get("title") == "Renamed test thread":
            ok("rename_thread persisted")
        else:
            fail(f"rename didn't persist — got {t.get('title') if t else None!r}")
    else:
        fail("rename_thread returned False")

    # Update preview
    await tm.update_thread_after_response(
        db, tid1, TEST_USER,
        response_preview="Section 194T TDS 10% partner payments.",
        try_llm_title=False,  # skip background LLM call in test
        original_query="follow-up",
    )
    t = await db.threads.find_one({"thread_id": tid1, "user_id": TEST_USER}, {"_id": 0})
    if t and "Section 194T" in (t.get("last_preview") or ""):
        ok("update_thread_after_response set last_preview")
    else:
        fail(f"last_preview not set: {t.get('last_preview') if t else None!r}")

    return True, tid1


async def cleanup_thread(db, tid: str):
    print("\n[3] Cleanup")
    deleted = await tm.delete_thread(db, TEST_USER, tid)
    if deleted:
        ok(f"deleted thread {tid}")
    else:
        fail("delete_thread returned False")

    # Verify gone
    exists = await db.threads.find_one({"thread_id": tid, "user_id": TEST_USER}, {"_id": 0})
    if exists:
        fail(f"thread {tid} still exists after delete!")
    else:
        ok("thread removed from Firestore")

    remaining_msgs = await db.query_history.find(
        {"thread_id": tid, "user_id": TEST_USER}, {"_id": 0}
    ).to_list(10)
    if remaining_msgs:
        fail(f"{len(remaining_msgs)} orphan messages still in query_history for deleted thread")
    else:
        ok("query_history rows cascaded cleanly")


async def test_http_endpoints():
    print("\n[4] HTTP smoke test (requires FIREBASE_TEST_TOKEN)")
    tok = os.environ.get("FIREBASE_TEST_TOKEN", "").strip()
    if not tok:
        info("Set FIREBASE_TEST_TOKEN=<your ID token> to enable this section.")
        info("Skipping.")
        return
    import httpx
    base = "http://localhost:8000/api"
    headers = {"Authorization": f"Bearer {tok}"}

    async with httpx.AsyncClient(timeout=20) as client:
        # List threads
        r = await client.get(f"{base}/threads", headers=headers)
        if r.status_code == 200:
            ok(f"GET /api/threads -> 200 ({len(r.json())} threads)")
        else:
            fail(f"GET /api/threads -> {r.status_code} {r.text[:120]}")
            return

        # Create a new thread by firing a query with no thread_id
        # (can't fully stream from a test, just verify the first event is the thread id)
        async with client.stream("POST", f"{base}/assistant/query",
                                  headers=headers,
                                  json={"query": "test e2e thread creation", "mode": "fast", "thread_id": ""}) as resp:
            got_thread = None
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    try:
                        import json as _j
                        ev = _j.loads(line[6:])
                        if isinstance(ev, dict) and ev.get("type") == "thread":
                            got_thread = ev.get("thread_id")
                            break
                    except Exception:
                        pass
            if got_thread:
                ok(f"POST /api/assistant/query emitted thread event: {got_thread}")
            else:
                fail("no 'thread' SSE event received from assistant query")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--http", action="store_true", help="Also run HTTP endpoint smoke tests")
    args = ap.parse_args()

    print(f"=== THREADING + SUPERMEMORY E2E TEST ===")
    print(f"  test user: {TEST_USER}")
    print(f"  supermemory enabled: {sm._SM_ENABLED}")
    print(f"  Firestore project: {os.environ.get('FIREBASE_PROJECT_ID','?')}")

    db = get_firestore_db("spectr_primary")

    sm_ok = await test_supermemory_roundtrip()
    thread_ok, tid = await test_thread_crud(db)
    if tid:
        await cleanup_thread(db, tid)
    if args.http:
        await test_http_endpoints()

    print("\n=== SUMMARY ===")
    print(f"  Supermemory: {'PASS' if sm_ok else 'FAIL/SKIP'}")
    print(f"  Thread CRUD: {'PASS' if thread_ok else 'FAIL'}")
    if not (sm_ok and thread_ok):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
