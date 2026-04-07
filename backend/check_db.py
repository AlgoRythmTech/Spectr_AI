import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / '.env')

async def check():
    url = os.environ.get('MONGO_URL')
    client = AsyncIOMotorClient(url, tls=True, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=10000)
    db = client['associate_db']
    total = await db.statutes.count_documents({})
    print(f'Total statutes: {total}')
    pipeline = [
        {"$group": {"_id": {"$substr": ["$act_name", 0, 45]}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    async for doc in db.statutes.aggregate(pipeline):
        print(f'  {doc["_id"]}: {doc["count"]}')
    client.close()

asyncio.run(check())
