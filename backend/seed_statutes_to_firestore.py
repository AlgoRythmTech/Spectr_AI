"""
seed_statutes_to_firestore.py — bulk upload bare-acts into Firestore.

USAGE
-----
1. Put one JSON file per act in `backend/seed_data/statutes/`
   Each file is a JSON ARRAY of section dicts. See `_SCHEMA.json` for format.
2. Run:
     python seed_statutes_to_firestore.py               # dry-run, shows what WOULD upload
     python seed_statutes_to_firestore.py --commit      # actually upload
     python seed_statutes_to_firestore.py --commit --replace-act "Bharatiya Nyaya Sanhita, 2023 (BNS)"
                                                         # wipe+reload one specific act
     python seed_statutes_to_firestore.py --commit --wipe-all
                                                         # nuclear: delete statutes collection first

DOCUMENT ID
-----------
Composite: f"{slugified_act}__{section_number}"
  e.g. "bharatiya_nyaya_sanhita_2023__103"
This makes re-runs idempotent — same act+section always updates the same Firestore doc
instead of creating duplicates.

COLLECTION
----------
Writes to `statutes` collection in the default Firestore database.
The collection the retriever queries (server.py:get_statute_context).
"""
import os
import sys
import json
import re
import argparse
import asyncio
from pathlib import Path
from collections import Counter

# Ensure we use the same Firestore init path as the rest of the backend
BACKEND_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BACKEND_DIR))

# Load .env so USE_FIRESTORE / FIREBASE_PROJECT_ID / etc are set
try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    pass

os.environ.setdefault("USE_FIRESTORE", "1")
if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    cred_path = BACKEND_DIR / "firebase-admin.json"
    if cred_path.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred_path)

from firestore_adapter import get_firestore_db, _init_firestore  # noqa


SEED_DIR = BACKEND_DIR / "seed_data" / "statutes"
REQUIRED = ("act_name", "section_number", "section_text", "keywords")


def _slug(s: str) -> str:
    """Turn an act name into a Firestore-safe slug."""
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _doc_id(entry: dict) -> str:
    return f"{_slug(entry['act_name'])}__{_slug(entry['section_number'])}"


def _load_files():
    """Read every *.json file in seed_data/statutes/ (except ones starting with _)."""
    if not SEED_DIR.exists():
        print(f"ERROR: seed directory does not exist: {SEED_DIR}")
        sys.exit(1)

    files = sorted(p for p in SEED_DIR.glob("*.json") if not p.name.startswith("_"))
    if not files:
        print(f"ERROR: no seed files found in {SEED_DIR}")
        print("       Drop JSON files in that folder (see _SCHEMA.json for format) then re-run.")
        sys.exit(1)

    entries = []
    skipped = 0
    for fp in files:
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  [SKIP] {fp.name} — invalid JSON: {e}")
            skipped += 1
            continue
        if not isinstance(data, list):
            print(f"  [SKIP] {fp.name} — top-level must be a JSON array of section objects")
            skipped += 1
            continue

        file_ok = 0
        file_bad = 0
        for i, entry in enumerate(data):
            if not isinstance(entry, dict):
                file_bad += 1
                continue
            missing = [k for k in REQUIRED if not entry.get(k)]
            if missing:
                print(f"  [BAD]  {fp.name}[{i}] missing fields: {missing}")
                file_bad += 1
                continue
            if not isinstance(entry["keywords"], list):
                print(f"  [BAD]  {fp.name}[{i}] 'keywords' must be an array")
                file_bad += 1
                continue
            entries.append(entry)
            file_ok += 1
        print(f"  [LOAD] {fp.name:40s}  ok={file_ok:4d}  rejected={file_bad}")

    if skipped:
        print(f"\nWARNING: {skipped} file(s) skipped due to format errors.")

    return entries


async def _wipe_act(db, act_name: str):
    """Delete every doc where act_name matches (exact)."""
    coll = db.statutes
    # Use the adapter's find which returns a cursor
    cur = coll.find({"act_name": act_name}, {"_id": 0})
    rows = await cur.to_list(length=10000)
    print(f"  Found {len(rows)} existing docs for '{act_name}' — deleting...")
    for r in rows:
        await coll.delete_one({
            "act_name": r["act_name"],
            "section_number": r.get("section_number", "")
        })
    print(f"  Deleted {len(rows)} old entries.")


async def _wipe_all(db):
    """Delete every doc in the statutes collection. Irreversible."""
    coll = db.statutes
    cur = coll.find({}, {"_id": 0})
    rows = await cur.to_list(length=100000)
    print(f"  Found {len(rows)} total docs in statutes — wiping all...")
    # Use the underlying firestore client for bulk delete
    fs_coll = coll._firestore_collection
    batch = coll._client.batch()
    n = 0
    for doc in fs_coll.stream():
        batch.delete(doc.reference)
        n += 1
        if n % 400 == 0:
            batch.commit()
            batch = coll._client.batch()
    batch.commit()
    print(f"  Wiped {n} docs.")


async def _upload(db, entries: list):
    """Batch-write all entries. Uses Firestore batched writes (500-doc cap)."""
    coll = db.statutes
    fs_coll = coll._firestore_collection
    client = coll._client

    total = len(entries)
    written = 0
    batch = client.batch()
    batch_size = 0

    for entry in entries:
        doc_id = _doc_id(entry)
        ref = fs_coll.document(doc_id)
        batch.set(ref, entry)  # overwrites — idempotent re-runs
        batch_size += 1
        written += 1
        if batch_size >= 400:  # Firestore hard cap is 500, leave headroom
            batch.commit()
            batch = client.batch()
            batch_size = 0
            print(f"    ... {written}/{total} uploaded")

    if batch_size:
        batch.commit()
    print(f"  Uploaded {written} docs to statutes collection.")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true",
                        help="Actually write to Firestore. Without this flag, runs a dry validation.")
    parser.add_argument("--replace-act", type=str, default=None,
                        help="Before uploading, delete all existing docs with this exact act_name.")
    parser.add_argument("--wipe-all", action="store_true",
                        help="Before uploading, wipe the entire statutes collection. Destructive.")
    args = parser.parse_args()

    print(f"seed_statutes_to_firestore — reading from {SEED_DIR}")
    print(f"  Firestore project: {os.environ.get('FIREBASE_PROJECT_ID', '(unset)')}")
    print(f"  Firestore database: {os.environ.get('FIRESTORE_DATABASE_ID', '(default)')}")
    print()

    entries = _load_files()

    # Dupe detection by (act_name, section_number)
    keys = [(e["act_name"], e["section_number"]) for e in entries]
    dupes = [k for k, n in Counter(keys).items() if n > 1]
    if dupes:
        print(f"\nWARNING: {len(dupes)} duplicate (act_name, section_number) pairs detected.")
        for d in dupes[:5]:
            print(f"   - {d}")
        print("  Later entries will overwrite earlier ones (same doc_id).")

    # Summary
    by_act = Counter(e["act_name"] for e in entries)
    print(f"\nSUMMARY — {len(entries)} total sections across {len(by_act)} acts:")
    for act, n in by_act.most_common():
        print(f"  {n:5d}  {act}")

    if not args.commit:
        print("\nDRY RUN — nothing written. Re-run with --commit to upload.")
        return

    db = get_firestore_db("spectr_primary")

    if args.wipe_all:
        print("\n[WIPE-ALL] About to delete ENTIRE statutes collection.")
        await _wipe_all(db)
    elif args.replace_act:
        print(f"\n[REPLACE] Wiping existing docs for act: {args.replace_act!r}")
        await _wipe_act(db, args.replace_act)

    print(f"\nUploading {len(entries)} docs...")
    await _upload(db, entries)

    # Verify
    final = await db.statutes.count_documents({})
    print(f"\nFinal statutes collection count: {final}")
    print("Done. The AI retrieval will now find these on next query.")


if __name__ == "__main__":
    asyncio.run(main())
