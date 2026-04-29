"""
seed_statutes_to_mongo.py — bulk upload bare-act sections to MongoDB.

Mirror of seed_statutes_to_firestore.py but writes to MongoDB (Atlas or
local). Reads the same JSON files out of seed_data/statutes/.

Usage
-----
    python seed_statutes_to_mongo.py                # dry-run
    python seed_statutes_to_mongo.py --commit        # upload
    python seed_statutes_to_mongo.py --commit --wipe # wipe collection first
    python seed_statutes_to_mongo.py --commit --replace-act "Income Tax Act, 1961"

Connection
----------
Reads MONGO_URL + DB_NAME from .env. Falls back to mongodb://localhost:27017
if MONGO_URL isn't set. Works against local MongoDB Community, MongoDB Atlas,
or a self-hosted replica set.

Indexes
-------
After seeding, creates these indexes on the statutes collection:
  - section_number (ASC)
  - act_name (ASC)
  - keywords (MULTIKEY) for array $in queries
  - {act_name: 1, section_number: 1} compound (for Pass 1 retrieval)
These are what get_statute_context() hits every query — without them, a
2,881-doc collection scans linearly and feels slow.
"""
import os
import sys
import json
import re
import argparse
import asyncio
from pathlib import Path
from collections import Counter

BACKEND = Path(__file__).parent
sys.path.insert(0, str(BACKEND))

try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND / ".env")
except ImportError:
    pass

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ.get("MONGO_URL") or "mongodb://localhost:27017"
DB_NAME = os.environ.get("DB_NAME", "spectr_primary")
SEED_DIR = BACKEND / "seed_data" / "statutes"
REQUIRED = ("act_name", "section_number", "section_text", "keywords")


def _slug(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _load_files():
    files = sorted(p for p in SEED_DIR.glob("*.json") if not p.name.startswith("_"))
    if not files:
        print(f"ERROR: no seed JSON files in {SEED_DIR}")
        sys.exit(1)

    entries = []
    for fp in files:
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  [SKIP] {fp.name} — invalid JSON: {e}")
            continue
        if not isinstance(data, list):
            print(f"  [SKIP] {fp.name} — top level must be array")
            continue
        ok = bad = 0
        for i, entry in enumerate(data):
            if not isinstance(entry, dict):
                bad += 1; continue
            missing = [k for k in REQUIRED if not entry.get(k)]
            if missing:
                bad += 1; continue
            if not isinstance(entry["keywords"], list):
                bad += 1; continue
            entries.append(entry)
            ok += 1
        print(f"  [LOAD] {fp.name:56s}  ok={ok:4d}  rejected={bad}")
    return entries


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", action="store_true")
    ap.add_argument("--wipe", action="store_true", help="Drop all existing statutes first")
    ap.add_argument("--replace-act", type=str, default=None,
                    help="Delete docs whose act_name matches exactly, then insert")
    args = ap.parse_args()

    masked = re.sub(r"://[^@]+@", "://***:***@", MONGO_URL)
    print(f"seed_statutes_to_mongo")
    print(f"  MONGO_URL: {masked}")
    print(f"  DB_NAME:   {DB_NAME}")
    print(f"  SEED_DIR:  {SEED_DIR}")
    print()

    entries = _load_files()

    by_act = Counter(e["act_name"] for e in entries)
    print(f"\nSUMMARY — {len(entries)} total sections across {len(by_act)} acts:")
    for act, n in by_act.most_common():
        print(f"  {n:5d}  {act}")

    if not args.commit:
        print("\nDRY RUN — re-run with --commit to upload.")
        return

    # Connect
    client = AsyncIOMotorClient(
        MONGO_URL,
        tls=True,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=10000,
    )
    db = client[DB_NAME]

    # Ping
    try:
        await db.command("ping")
    except Exception as e:
        print(f"FAIL: cannot reach MongoDB: {e}")
        sys.exit(1)
    print("\nMongoDB reachable.")

    if args.wipe:
        print("[WIPE] dropping entire statutes collection...")
        await db.statutes.drop()

    if args.replace_act:
        print(f"[REPLACE] deleting existing docs for act: {args.replace_act!r}")
        r = await db.statutes.delete_many({"act_name": args.replace_act})
        print(f"  deleted {r.deleted_count}")

    # Deduplicate by (act_name, section_number) — last-wins within a single
    # seed run (same behaviour as the Firestore seeder's doc-id overwrite).
    deduped = {}
    for e in entries:
        key = f"{e['act_name']}|{e['section_number']}"
        deduped[key] = e
    final = list(deduped.values())

    print(f"\nUploading {len(final)} docs (after de-dup)...")
    # Batched inserts — Mongo handles thousands per batch fine
    BATCH = 500
    total = 0
    for i in range(0, len(final), BATCH):
        chunk = final[i:i+BATCH]
        try:
            await db.statutes.insert_many(chunk, ordered=False)
            total += len(chunk)
            print(f"  ... {total}/{len(final)}")
        except Exception as e:
            # DuplicateKeyError on re-run is fine — count successes
            inserted = getattr(e, "details", {}).get("nInserted", 0) if hasattr(e, "details") else 0
            total += inserted
            print(f"  partial batch: {inserted} inserted (re-run / dup keys OK)")

    print(f"\nDone — inserted {total}")

    print("\nCreating indexes (idempotent)...")
    try:
        await db.statutes.create_index("section_number")
        await db.statutes.create_index("act_name")
        await db.statutes.create_index("keywords")  # multikey for array $in
        await db.statutes.create_index([("act_name", 1), ("section_number", 1)])
        print("  indexes created.")
    except Exception as e:
        print(f"  index creation warning: {e}")

    final_count = await db.statutes.count_documents({})
    print(f"\nFinal statutes collection size: {final_count}")
    print("Retrieval will now hit MongoDB with zero quota limits.")


if __name__ == "__main__":
    asyncio.run(main())
