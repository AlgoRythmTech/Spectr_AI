import asyncio
import os
import uuid
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'associate_db')]

# Hardcoded system user ID so all users can see these baseline templates, or they attach to a default user.
# For simplicity in this build, we associate them with "SYSTEM_TEMPLATES" user.
SYSTEM_USER_ID = "SYSTEM_TEMPLATES"

TEMPLATES = [
    {
        "title": "Complaint Under Section 138 NI Act (Cheque Bounce)",
        "item_type": "template",
        "tags": ["criminal", "cheque bounce", "section 138", "ni act", "magistrate court"],
        "content": """IN THE COURT OF THE METROPOLITAN MAGISTRATE AT _________
CRIMINAL COMPLAINT NO. ______ OF 202X

IN THE MATTER OF:
[COMPLAINANT_NAME] ... COMPLAINANT
VERSUS
[ACCUSED_NAME] ... ACCUSED

COMPLAINT UNDER SECTION 138 READ WITH SECTION 142 OF THE NEGOTIABLE INSTRUMENTS ACT, 1881.

MAY IT PLEASE YOUR HONOUR:
The Complainant above-named most respectfully showeth:
1. That the Complainant is a company incorporated under...
2. That the Accused approached the Complainant for...
3. That in discharge of the legally enforceable debt, the Accused issued Cheque No. [CHEQUE_NUMBER] dated [DATE] for Rs. [AMOUNT] drawn on [BANK_NAME].
4. That the said cheque was presented but returned unpaid with remarks "[REASON]".
5. That the statutory demand notice was issued on [NOTICE_DATE].
...
PRAYER
It is therefore most respectfully prayed that this Hon'ble Court may be pleased to take cognizance..."""
    },
    {
        "title": "Anticipatory Bail Application (Section 438 CrPC / Section 482 BNSS)",
        "item_type": "template",
        "tags": ["criminal", "bail", "anticipatory bail", "high court", "sessions court"],
        "content": """IN THE COURT OF THE HON'BLE SESSIONS JUDGE AT _________
ANTICIPATORY BAIL APPLICATION NO. ______ OF 202X
(Under Section 438 of the Code of Criminal Procedure / Section 482 of the Bharatiya Nagarik Suraksha Sanhita, 2023)

IN THE MATTER OF:
[APPLICANT_NAME] ... APPLICANT
VERSUS
STATE OF _________
THROUGH S.H.O., P.S. [POLICE_STATION] ... RESPONDENT

FIR NO.: [FIR_NUMBER]
U/S: [CHARGES]

MAY IT PLEASE YOUR HONOUR:
1. That the Applicant is a law-abiding citizen with deep roots in society...
2. That the Applicant apprehends arrest in the captioned FIR, which is entirely false and motivated...
3. That the dispute is primarily civil in nature and has been given a criminal color...
4. That the Applicant undertakes to cooperate with the investigation...
...
PRAYER
It is therefore prayed that in the event of arrest, the Applicant be released on bail..."""
    }
]

async def seed_library():
    print("Clearing existing system templates...")
    await db.library_items.delete_many({"user_id": SYSTEM_USER_ID})
    
    docs = []
    for t in TEMPLATES:
        docs.append({
            "item_id": f"lib_{uuid.uuid4().hex[:12]}",
            "user_id": SYSTEM_USER_ID,
            "title": t["title"],
            "content": t["content"],
            "item_type": t["item_type"],
            "tags": t["tags"],
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    if docs:
        await db.library_items.insert_many(docs)
        print(f"Successfully seeded {len(docs)} highly structured Indian litigation templates into the Library.")

if __name__ == "__main__":
    asyncio.run(seed_library())
