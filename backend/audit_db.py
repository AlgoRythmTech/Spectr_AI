import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / '.env')

async def audit():
    c = AsyncIOMotorClient(os.environ['MONGO_URL'], tls=True, tlsAllowInvalidCertificates=True)
    db = c['associate_db']
    t = await db.statutes.count_documents({})
    print(f"Total statutes: {t}")
    
    pipeline = [
        {"$group": {"_id": {"$substr": ["$act_name", 0, 55]}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    async for d in db.statutes.aggregate(pipeline):
        print(f"  {d['_id']}: {d['count']}")
    
    stats = await db.command("dbstats")
    data_mb = stats.get("dataSize", 0) / (1024 * 1024)
    storage_mb = stats.get("storageSize", 0) / (1024 * 1024)
    print(f"\nData Size: {data_mb:.2f} MB")
    print(f"Storage Size: {storage_mb:.2f} MB / 512 MB limit")
    print(f"Usage: {(storage_mb/512)*100:.1f}%")
    c.close()

asyncio.run(audit())
