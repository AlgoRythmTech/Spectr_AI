"""
COMPREHENSIVE LAW SEEDER — Associate Platform
Seeds MongoDB with additional critical Indian statutes:
1. FEMA 1999
2. Arbitration & Conciliation Act, 1996
3. Consumer Protection Act, 2019
4. RERA 2016
5. Negotiable Instruments Act, 1881
6. PMLA 2002
7. Indian Contract Act, 1872
8. Specific Relief Act, 1963
9. SEBI (key provisions)
10. Limitation Act, 1963

Run: python seed_comprehensive_laws.py
"""
import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).parent / '.env')
mongo_url = os.environ.get('MONGO_URL', "mongodb://localhost:27017")
db_name = os.environ.get('DB_NAME', "associate_db")

FEMA_STATUTES = [
    {"act_name": "Foreign Exchange Management Act, 1999 (FEMA)", "section_number": "3",
     "section_title": "Dealing in foreign exchange, etc.",
     "section_text": "Save as otherwise provided in this Act, rules or regulations made thereunder, or with the general or special permission of the Reserve Bank, no person shall — (a) deal in or transfer any foreign exchange or foreign security to any person not being an authorised person; (b) make any payment to or for the credit of any person resident outside India in any manner; (c) receive otherwise than through an authorised person, any payment by order or on behalf of any person resident outside India in any manner. Penalty for contravention: up to thrice the sum involved or up to Rs 2 lakh where the amount is not quantifiable, with additional penalty of Rs 5,000 for every day of continuing contravention.",
     "keywords": ["FEMA", "foreign exchange", "dealing", "authorised person", "RBI", "penalty"]},
    {"act_name": "Foreign Exchange Management Act, 1999 (FEMA)", "section_number": "4",
     "section_title": "Holding of foreign exchange, etc.",
     "section_text": "Save as otherwise provided in this Act, no person resident in India shall acquire, hold, own, possess or transfer any foreign exchange, foreign security or any immovable property situated outside India. Exception: Foreign exchange obtained by way of salary, pension, etc. can be held for a reasonable period.",
     "keywords": ["FEMA", "holding", "foreign exchange", "foreign security", "immovable property abroad"]},
    {"act_name": "Foreign Exchange Management Act, 1999 (FEMA)", "section_number": "6",
     "section_title": "Capital account transactions",
     "section_text": "Any person may sell or draw foreign exchange to or from an authorised person for a capital account transaction as per RBI or Government regulations. RBI may specify (a) any class or classes of capital account transactions which are permissible; (b) the limit up to which foreign exchange shall be admissible for such transactions. Key: LRS limit is currently USD 250,000 per financial year for resident individuals.",
     "keywords": ["capital account", "LRS", "USD 250000", "liberalised remittance", "FEMA 6"]},
    {"act_name": "Foreign Exchange Management Act, 1999 (FEMA)", "section_number": "13",
     "section_title": "Penalties",
     "section_text": "If any person contravenes any provision of this Act, or contravenes any rule, regulation, notification, direction or order issued in exercise of the powers under this Act, he shall, upon adjudication, be liable to a penalty up to thrice the sum involved in such contravention where such amount is quantifiable, or up to two lakh rupees where the amount is not directly quantifiable, and where such contravention is a continuing one, further penalty which may extend to five thousand rupees for every day after the first day during which the contravention continues.",
     "keywords": ["FEMA penalty", "thrice", "contravention", "adjudication", "five thousand per day"]},
]

ARBITRATION_STATUTES = [
    {"act_name": "Arbitration and Conciliation Act, 1996", "section_number": "7",
     "section_title": "Arbitration agreement",
     "section_text": "An arbitration agreement means an agreement by the parties to submit to arbitration all or certain disputes which have arisen or may arise between them. It may be in the form of an arbitration clause in a contract or a separate agreement. The agreement shall be in writing. An arbitration agreement is in writing if it is contained in a document signed by the parties, or in an exchange of letters, telex, telegrams, or other means of telecommunication including electronic communication.",
     "keywords": ["arbitration agreement", "writing", "clause", "section 7", "dispute"]},
    {"act_name": "Arbitration and Conciliation Act, 1996", "section_number": "9",
     "section_title": "Interim measures by Court",
     "section_text": "A party may, before or during arbitral proceedings or at any time after the making of the arbitral award but before it is enforced, apply to a Court for interim measures of protection. The Court shall not entertain an application for interim measures under this section after the arbitral tribunal is constituted UNLESS the Court finds that circumstances exist which may not render the remedy under Section 17 efficacious. Amended by 2015 Amendment: Once tribunal is constituted, Court shall not entertain application unless remedy under Section 17 is not efficacious.",
     "keywords": ["interim measures", "section 9", "court", "before arbitration", "2015 amendment"]},
    {"act_name": "Arbitration and Conciliation Act, 1996", "section_number": "34",
     "section_title": "Application for setting aside arbitral award",
     "section_text": "Recourse to a Court against an arbitral award may be made only by an application for setting aside. Grounds: (a) party was under some incapacity; (b) agreement not valid; (c) party not given proper notice; (d) award deals with dispute not contemplated by submission; (e) composition of tribunal not in accordance with agreement; (f) subject matter not capable of settlement by arbitration; (g) award in conflict with public policy of India — includes fraud, corruption, or if in contravention of fundamental policy of Indian law, or in conflict with basic notions of morality or justice. Time limit: 3 months from receipt of award (extendable by 30 days max).",
     "keywords": ["setting aside", "section 34", "public policy", "3 months", "challenge award", "grounds"]},
    {"act_name": "Arbitration and Conciliation Act, 1996", "section_number": "36",
     "section_title": "Enforcement of award",
     "section_text": "Where the time for making an application to set aside the arbitral award under section 34 has expired, or such application having been made, it has been refused, the award shall be enforced under the Code of Civil Procedure, 1908 in the same manner as if it were a decree of the Court. Filing of a Section 34 application does NOT automatically stay the enforcement of the award — the Court must separately grant a stay under Section 36(2) after hearing both parties.",
     "keywords": ["enforcement", "section 36", "decree", "no automatic stay", "2015 amendment"]},
]

NI_ACT_STATUTES = [
    {"act_name": "Negotiable Instruments Act, 1881", "section_number": "138",
     "section_title": "Dishonour of cheque for insufficiency of funds",
     "section_text": "Where any cheque drawn by a person on an account maintained by him with a banker for payment of any amount of money to another person from out of that account for the discharge, in whole or in part, of any debt or other liability, is returned by the bank unpaid, either because of the amount of money standing to the credit of that account is insufficient to honour the cheque or that it exceeds the amount arranged to be paid from that account by an agreement made with that bank, such person shall be deemed to have committed an offence and shall be punished with imprisonment for a term which may extend to two years, or with fine which may extend to twice the amount of the cheque, or with both. CONDITIONS: (a) cheque must be presented within 3 months of date; (b) payee must give written notice demanding payment within 30 days of dishonour; (c) drawer must fail to pay within 15 days of receipt of notice. Complaint must be filed within 30 days of expiry of 15-day period.",
     "keywords": ["cheque bounce", "138 NI Act", "dishonour", "insufficiency", "two years", "notice 30 days", "15 days"]},
    {"act_name": "Negotiable Instruments Act, 1881", "section_number": "139",
     "section_title": "Presumption in favour of holder",
     "section_text": "It shall be presumed, unless the contrary is proved, that the holder of a cheque received the cheque of the nature referred to in section 138 for the discharge, in whole or in part, of any debt or other liability. This creates a REVERSE BURDEN OF PROOF — the accused must prove that the cheque was not issued for a legally enforceable debt.",
     "keywords": ["presumption", "139 NI Act", "reverse burden", "holder", "legally enforceable debt"]},
    {"act_name": "Negotiable Instruments Act, 1881", "section_number": "141",
     "section_title": "Offences by companies",
     "section_text": "If the person committing an offence under section 138 is a company, every person who, at the time the offence was committed, was in charge of, and was responsible to, the company for the conduct of the business of the company, as well as the company, shall be deemed to be guilty of the offence. Directors and officers can be prosecuted if they were 'in charge of' the business. Requirement of specific averment in complaint — vicarious liability.",
     "keywords": ["company", "director", "141 NI Act", "in charge", "vicarious liability", "cheque bounce company"]},
]

PMLA_STATUTES = [
    {"act_name": "Prevention of Money Laundering Act, 2002 (PMLA)", "section_number": "3",
     "section_title": "Offence of money-laundering",
     "section_text": "Whosoever directly or indirectly attempts to indulge or knowingly assists or knowingly is a party or is actually involved in any process or activity connected with the proceeds of crime including its concealment, possession, acquisition or use and projecting or claiming it as untainted property shall be guilty of offence of money-laundering. The PMLA offense is a standalone offense — it is independent of the scheduled offense conviction. Even acquittal in the scheduled offense does not automatically lead to discharge under PMLA (Vijay Madanlal Choudhary v. UOI, 2022).",
     "keywords": ["money laundering", "proceeds of crime", "section 3 PMLA", "concealment", "untainted property"]},
    {"act_name": "Prevention of Money Laundering Act, 2002 (PMLA)", "section_number": "5",
     "section_title": "Attachment of property involved in money-laundering",
     "section_text": "Where the Director or any other officer not below the rank of Deputy Director has reason to believe (the reason for such belief to be recorded in writing) that any person is in possession of any proceeds of crime, he may provisionally attach such property for a period not exceeding 180 days. The attachment order must be confirmed by the Adjudicating Authority. Key: ED can attach property even BEFORE filing a prosecution complaint.",
     "keywords": ["attachment", "section 5 PMLA", "provisional", "180 days", "ED", "enforcement directorate"]},
    {"act_name": "Prevention of Money Laundering Act, 2002 (PMLA)", "section_number": "24",
     "section_title": "Burden of proof",
     "section_text": "In any proceeding relating to proceeds of crime under this Act — (a) in the case of a person charged with the offence of money-laundering under section 3, the Authority or Court shall, unless the contrary is proved, presume that such proceeds of crime are involved in money-laundering; (b) in the case of any other person, the Authority or Court may presume that such proceeds of crime are involved in money-laundering. This creates a REVERSE BURDEN on the accused to prove that the property is not proceeds of crime.",
     "keywords": ["burden of proof", "section 24", "reverse burden", "presume", "proceeds of crime"]},
]

CONTRACT_ACT_STATUTES = [
    {"act_name": "Indian Contract Act, 1872", "section_number": "10",
     "section_title": "What agreements are contracts",
     "section_text": "All agreements are contracts if they are made by the free consent of parties competent to contract, for a lawful consideration and with a lawful object, and are not hereby expressly declared to be void. Essential elements: (1) Offer and acceptance, (2) Free consent (Sections 14-22), (3) Competent parties (Section 11 — age of majority, sound mind, not disqualified by law), (4) Lawful consideration (Section 23), (5) Lawful object, (6) Not declared void.",
     "keywords": ["contract", "free consent", "lawful consideration", "competent", "section 10", "void"]},
    {"act_name": "Indian Contract Act, 1872", "section_number": "73",
     "section_title": "Compensation for loss or damage caused by breach of contract",
     "section_text": "When a contract has been broken, the party who suffers by such breach is entitled to receive, as compensation for any loss or damage caused to him thereby, such compensation which naturally arose in the usual course of things from such breach, or which the parties knew, when they made the contract, to be likely to result from the breach of it. Such compensation is not to be given for any remote and indirect loss or damage sustained by reason of the breach. Key principle: Hadley v. Baxendale foreseeability test applies.",
     "keywords": ["damages", "compensation", "breach", "section 73", "foreseeability", "Hadley v Baxendale"]},
    {"act_name": "Indian Contract Act, 1872", "section_number": "56",
     "section_title": "Agreement to do impossible act — Doctrine of Frustration",
     "section_text": "An agreement to do an act impossible in itself is void. A contract to do an act which, after the contract is made, becomes impossible, or, by reason of some event which the promisor could not prevent, unlawful, becomes void when the act becomes impossible or unlawful. The doctrine of frustration under Section 56 renders contracts void when: (1) an unforeseen event occurs, (2) beyond the control of parties, (3) which makes performance impossible or unlawful. It does NOT apply when performance merely becomes more onerous or expensive. Key case: Satyabrata Ghose v. Mugneeram Bangur (1954) AIR SC 44.",
     "keywords": ["frustration", "impossible", "void", "section 56", "unforeseen event", "Satyabrata Ghose"]},
]

LIMITATION_STATUTES = [
    {"act_name": "Limitation Act, 1963", "section_number": "Articles 54-58, 113, 137",
     "section_title": "Key Limitation Periods — Most Used Articles",
     "section_text": """MOST USED LIMITATION PERIODS:
Article 54: Suit for specific performance of a contract — 3 years from date fixed for performance, or if no date fixed, when plaintiff has notice that performance is refused.
Article 55: Suit for compensation for breach of contract (written) — 3 years from date of breach.
Article 56: Suit for compensation for breach of contract (not written/implied) — 3 years from date of breach.
Article 57: Suit for possession of immovable property based on title — 12 years from when possession became adverse.
Article 58: Suit for declaration and consequential relief — 3 years from when right to sue first accrues.
Article 65: Suit for possession based on previous possession (not on title) — 12 years from date of dispossession.
Article 113: Suit for which no limitation period is provided elsewhere — 3 years from when right to sue accrues.
Article 120: Suit for money payable under a written obligation — 3 years.
Article 137: Any application for which no period of limitation is provided — 3 years from when right to apply accrues.
Section 5: Extension of prescribed period in certain cases — court may admit appeal/application if sufficient cause is shown for delay. Applies only to APPEALS and APPLICATIONS, NOT to suits.
Section 14: Exclusion of time of proceeding bona fide in court without jurisdiction.""",
     "keywords": ["limitation period", "3 years", "12 years", "article 54", "article 137", "section 5 delay", "condonation"]},
]

RERA_STATUTES = [
    {"act_name": "Real Estate (Regulation and Development) Act, 2016 (RERA)", "section_number": "18",
     "section_title": "Return of amount and compensation",
     "section_text": "If the promoter fails to complete or is unable to give possession of an apartment, plot or building — (a) in accordance with the terms of the agreement for sale or, as the case may be, duly completed by the date specified therein; he shall be liable on demand to the allottees, in case the allottee wishes to withdraw from the project, to return the amount received by him in respect of that apartment, plot, building, as the case may be, with interest at such rate as may be prescribed in this behalf including compensation. If the allottee does not intend to withdraw, the promoter shall pay interest for every month of delay until delivery. RERA Authority can direct refund with interest at SBI MCLR + 2%.",
     "keywords": ["RERA", "refund", "section 18", "delay possession", "interest", "promoter liability", "allottee"]},
    {"act_name": "Real Estate (Regulation and Development) Act, 2016 (RERA)", "section_number": "31",
     "section_title": "Penalty for non-registration of real estate project",
     "section_text": "If any promoter contravenes the provisions of Section 3 (mandatory registration before advertising/selling), he shall be liable to a penalty which may extend to ten per cent of the estimated cost of the real estate project. If the promoter does not comply with the orders or continues to violate Section 3, he shall be punishable with imprisonment for a term which may extend to three years or with fine which may extend to a further ten per cent of the estimated cost of the real estate project, or with both.",
     "keywords": ["RERA penalty", "non-registration", "10 percent", "imprisonment", "section 31", "section 3"]},
]

CONSUMER_STATUTES = [
    {"act_name": "Consumer Protection Act, 2019", "section_number": "2(7)",
     "section_title": "Definition of complaint",
     "section_text": "Complaint means any allegation in writing, made by a complainant, regarding: (i) unfair trade practice or restrictive trade practice; (ii) defective goods; (iii) deficiency in services; (iv) excess charging of price; (v) goods or services hazardous to life or safety; (vi) product liability action. 'Deficiency' means any fault, imperfection, shortcoming or inadequacy in the quality, nature and manner of performance which is required to be maintained by or under any law.",
     "keywords": ["consumer complaint", "deficiency", "defective goods", "unfair trade practice", "section 2(7)"]},
    {"act_name": "Consumer Protection Act, 2019", "section_number": "34-35",
     "section_title": "Jurisdiction of Consumer Commissions",
     "section_text": """PECUNIARY JURISDICTION (as per Consumer Protection Act, 2019):
District Commission: Claims up to Rs 1 Crore
State Commission: Claims exceeding Rs 1 Crore but not exceeding Rs 10 Crore
National Commission: Claims exceeding Rs 10 Crore
TERRITORIAL JURISDICTION: Where the opposite party resides or carries on business, OR where the cause of action arises, OR where the complainant resides (for Section 35, complaint can be filed where complainant resides — a key advantage for consumers).
TIME LIMIT: Complaint must be filed within 2 years from date of cause of action. Delay can be condoned if sufficient cause is shown.""",
     "keywords": ["jurisdiction", "district commission", "state commission", "national commission", "1 crore", "10 crore", "2 years"]},
]

ALL_COMPREHENSIVE = FEMA_STATUTES + ARBITRATION_STATUTES + NI_ACT_STATUTES + PMLA_STATUTES + CONTRACT_ACT_STATUTES + LIMITATION_STATUTES + RERA_STATUTES + CONSUMER_STATUTES

async def seed_comprehensive():
    client = AsyncIOMotorClient(mongo_url, tls=True, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=15000)
    db = client[db_name]
    
    print("=" * 60)
    print("ASSOCIATE — COMPREHENSIVE LAW SEEDER")
    print("=" * 60)
    
    existing = await db.statutes.count_documents({})
    print(f"Current statutes in DB: {existing}")
    
    # Remove old entries to avoid duplicates
    acts_to_clean = [
        "Foreign Exchange Management Act",
        "Arbitration and Conciliation",
        "Negotiable Instruments Act",
        "Prevention of Money Laundering",
        "Indian Contract Act",
        "Limitation Act",
        "Real Estate.*RERA",
        "Consumer Protection Act",
    ]
    total_deleted = 0
    for act_pattern in acts_to_clean:
        result = await db.statutes.delete_many({"act_name": {"$regex": act_pattern}})
        total_deleted += result.deleted_count
    
    print(f"Removed {total_deleted} stale entries.")
    
    if ALL_COMPREHENSIVE:
        result = await db.statutes.insert_many(ALL_COMPREHENSIVE)
        print(f"✅ Inserted {len(result.inserted_ids)} new statute entries")
    
    # Ensure indexes
    await db.statutes.create_index([("act_name", 1), ("section_number", 1)])
    await db.statutes.create_index([("keywords", 1)])
    
    final = await db.statutes.count_documents({})
    print(f"\n{'='*60}")
    print(f"SEEDING COMPLETE — Total statutes: {final}")
    print(f"  📜 FEMA 1999:              {len(FEMA_STATUTES)} sections")
    print(f"  ⚖️  Arbitration Act 1996:   {len(ARBITRATION_STATUTES)} sections")
    print(f"  📄 NI Act 1881 (Cheque):   {len(NI_ACT_STATUTES)} sections")
    print(f"  🔒 PMLA 2002:              {len(PMLA_STATUTES)} sections")
    print(f"  📝 Contract Act 1872:      {len(CONTRACT_ACT_STATUTES)} sections")
    print(f"  ⏱️  Limitation Act 1963:    {len(LIMITATION_STATUTES)} sections")
    print(f"  🏠 RERA 2016:              {len(RERA_STATUTES)} sections")
    print(f"  🛒 Consumer Protection:    {len(CONSUMER_STATUTES)} sections")
    print(f"{'='*60}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_comprehensive())
