"""
MASTER STATUTE SEEDER — Associate Platform
Seeds MongoDB with:
1. Full BNS (Bharatiya Nyaya Sanhita) 2023 — replaces IPC 1860
2. Full BNSS (Bharatiya Nagarik Suraksha Sanhita) 2023 — replaces CrPC
3. BSA (Bharatiya Sakshya Adhiniyam) 2023 — replaces Evidence Act
4. IT Act 1961 — ALL key sections + Budget 2025-26 changes effective April 1 2026
5. New Tax Slabs AY 2026-27 (April 1 2026 effective)
6. TDS rate changes effective April 1 2026
7. Updated GST provisions including Budget 2025-26 amendments

Run: python seed_master_statutes.py
"""
import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).parent / '.env')

mongo_url = os.environ.get('MONGO_URL', "mongodb://localhost:27017")
db_name = os.environ.get('DB_NAME', "associate_db")

# ================================================================
# BNS — BHARATIYA NYAYA SANHITA 2023
# (Replaces IPC 1860, effective July 1, 2024)
# ================================================================
BNS_STATUTES = [
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "1", "section_title": "Short title, extent and commencement",
     "section_text": "This Act may be called the Bharatiya Nyaya Sanhita, 2023. It extends to the whole of India. It came into force on July 1, 2024, replacing the Indian Penal Code, 1860.",
     "keywords": ["BNS", "commencement", "July 2024", "IPC replaced"], "ipc_equivalent": "IPC 1"},

    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "3", "section_title": "General explanations — definitions",
     "section_text": "In this Sanhita: (1) 'act' denotes a series of acts as well as a single act; (2) 'animal' means any living creature, other than a human being; (3) 'child' means a person who has not completed eighteen years of age; (5) 'court' means a Judge who is empowered by law to act judicially alone, or a body of Judges which is empowered by law to act judicially as a body; (17) 'person' includes any Company or Association or Body of persons whether incorporated or not; (25) 'public servant' has the meaning assigned to it in clause (7) of section 2 of the Prevention of Corruption Act, 1988.",
     "keywords": ["definitions", "person", "court", "child", "public servant", "BNS"], "ipc_equivalent": "IPC 2-52A"},

    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "4", "section_title": "Punishment of offences committed within India",
     "section_text": "Every person shall be liable to punishment under this Sanhita and not otherwise for every act or omission contrary to the provisions thereof, of which he shall be guilty within India.",
     "keywords": ["jurisdiction", "within india", "punishment", "offence"], "ipc_equivalent": "IPC 2"},

    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "61", "section_title": "Sedition replaced by Acts endangering sovereignty",
     "section_text": "Whoever intentionally or knowingly, by words, either spoken or written, or by signs, or by visible representation, or by electronic communication or by use of financial mean, or otherwise, excites or attempts to excite, secession or armed rebellion or subversive activities, or encourages feelings of separatist activities or endangers sovereignty or unity and integrity of India shall be punished with imprisonment for life or with imprisonment which may extend to seven years, and shall also be liable to fine.",
     "keywords": ["sedition", "sovereignty", "secession", "armed rebellion", "life imprisonment", "61 BNS"], "ipc_equivalent": "IPC 124A (repealed)"},

    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "65", "section_title": "Voluntarily causing hurt — punishment",
     "section_text": "Whoever causes hurt to any person or causes criminal force is said to have committed an assault. Punishment: imprisonment up to one year or fine up to ten thousand rupees, or both.",
     "keywords": ["hurt", "assault", "imprisonment", "fine", "65 BNS"], "ipc_equivalent": "IPC 323/351"},

    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "70", "section_title": "Gang rape",
     "section_text": "When a woman is raped by one or more persons constituting a group or acting in furtherance of a common intention, each of those persons shall be deemed to have committed the offence of rape and shall be punished with rigorous imprisonment for a term which shall not be less than twenty years, but which may extend to imprisonment for life.",
     "keywords": ["gang rape", "group", "twenty years", "life imprisonment", "70 BNS"], "ipc_equivalent": "IPC 376D"},

    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "77", "section_title": "Sexual harassment",
     "section_text": "Any man who commits the following acts shall be guilty of sexual harassment: (i) physical contact and advances involving unwelcome and explicit sexual overtures; or (ii) a demand or request for sexual favours; or (iii) showing pornography against the will of a woman; or (iv) making sexually coloured remarks, shall be punished with rigorous imprisonment of not less than one year which may extend to three years and with fine.",
     "keywords": ["sexual harassment", "77 BNS", "workplace", "section 354A IPC", "punishment"], "ipc_equivalent": "IPC 354A"},

    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "85", "section_title": "Husband or relative of husband of a woman subjecting her to cruelty",
     "section_text": "Whoever, being the husband or the relative of the husband of a woman, subjects such woman to cruelty shall be punished with imprisonment for a term which may extend to three years and shall also be liable to fine. Explanation: 'cruelty' means any wilful conduct which is of such a nature as is likely to drive the woman to commit suicide or to cause grave injury or danger to life, limb or health (whether mental or physical) of the woman; or harassment of the woman where such harassment is with a view to coercing her or any person related to her to meet any unlawful demand for any property or valuable security or is on account of failure by her or any person related to her to meet such demand.",
     "keywords": ["cruelty", "husband", "relative", "dowry", "harassment", "85 BNS", "498A IPC"], "ipc_equivalent": "IPC 498A"},

    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "111", "section_title": "Organised crime",
     "section_text": "NEW IN BNS — NO IPC EQUIVALENT. Whoever commits organised crime shall be punished for: (i) if it results in the death of any person — with death or imprisonment for life and also liable to a fine not less than ten lakh rupees; (ii) in any other case — rigorous imprisonment for not less than five years but may extend to imprisonment for life and liable to fine not less than five lakh rupees. 'Organised crime syndicate' means a group of two or more persons who acting either singly or jointly, as a syndicate or gang for individual gain or gain of the group.",
     "keywords": ["organised crime", "syndicate", "gang", "death penalty", "111 BNS", "new provision"], "ipc_equivalent": "NEW — No IPC equivalent"},

    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "113", "section_title": "Terrorist act",
     "section_text": "NEW IN BNS. Whoever commits a terrorist act shall be punished with death or imprisonment for life. 'Terrorist act' means an act committed with intent to threaten or likely to threaten the unity, integrity, sovereignty, security, or economic security of India, or with intent to strike terror or likely to strike terror in the people or any section of the people in India or in any foreign country.",
     "keywords": ["terrorist", "terrorism", "death penalty", "life imprisonment", "113 BNS", "new provision"], "ipc_equivalent": "NEW — Previously under UAPA"},

    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "177", "section_title": "Theft",
     "section_text": "Whoever, intending to take dishonestly any moveable property out of the possession of any person without that person's consent, moves that property in order to such taking, is said to commit theft. Punishment: imprisonment of either description for a term which may extend to three years, or with fine, or with both.",
     "keywords": ["theft", "moveable property", "three years", "177 BNS", "dishonestly"], "ipc_equivalent": "IPC 378/379"},

    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "215", "section_title": "Cheating",
     "section_text": "Whoever, by deceiving any person, fraudulently or dishonestly induces the person so deceived to deliver any property to any person, or to consent that any person shall retain any property, or intentionally induces the person so deceived to do or omit to do anything which he would not do or omit if he were not so deceived, and which act or omission causes or is likely to cause damage or harm to that person in body, mind, reputation or property, is said to 'cheat'.",
     "keywords": ["cheating", "deceiving", "fraudulently", "property", "215 BNS"], "ipc_equivalent": "IPC 415"},

    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "318", "section_title": "Cheating and dishonestly inducing delivery of property",
     "section_text": "Whoever cheats and thereby dishonestly induces the person deceived to deliver any property to any person, or to make, alter or destroy the whole or any part of a valuable security, or anything which is signed or sealed, and which is capable of being converted into a valuable security, shall be punished with imprisonment of either description for a term which may extend to seven years, and shall also be liable to fine.",
     "keywords": ["cheating", "delivery of property", "valuable security", "seven years", "318 BNS", "420 IPC"], "ipc_equivalent": "IPC 420"},

    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "316", "section_title": "Criminal breach of trust",
     "section_text": "Whoever, being in any manner entrusted with property, or with any dominion over property, dishonestly misappropriates or converts to his own use that property, or dishonestly uses or disposes of that property in violation of any direction of law prescribing the mode in which such trust is to be discharged, or of any legal contract, express or implied, which he has made touching the discharge of such trust, or wilfully suffer any other person so to do, commits criminal breach of trust. Punishment: imprisonment of either description for a term which may extend to three years, or with fine, or with both.",
     "keywords": ["criminal breach of trust", "CBT", "misappropriation", "three years", "316 BNS", "406 IPC"], "ipc_equivalent": "IPC 406"},

    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "319", "section_title": "Cheating by personation",
     "section_text": "A person is said to 'cheat by personation' if he cheats by pretending to be some other person, or by knowingly substituting one person for another, or representing that he or any other person is a person other than he or such other person really is. Punishment: imprisonment of either description for a term may extend to five years, or with fine, or with both.",
     "keywords": ["personation", "impersonation", "identity fraud", "five years", "319 BNS"], "ipc_equivalent": "IPC 416/419"},

    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "336", "section_title": "Forgery",
     "section_text": "Whoever makes any false document or false electronic record or part of a document or electronic record, with intent to cause damage or injury, to the public or to any person, or to support any claim or title, or to cause any person to part with property, or to enter into any express or implied contract, or with intent to commit fraud or that fraud may be committed, commits forgery.",
     "keywords": ["forgery", "false document", "electronic record", "336 BNS", "463 IPC"], "ipc_equivalent": "IPC 463"},

    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "338", "section_title": "Forgery for purpose of cheating",
     "section_text": "Whoever commits forgery, intending that the document or electronic record forged shall be used for the purpose of cheating, shall be punished with imprisonment of either description for a term which may extend to seven years, and shall also be liable to fine.",
     "keywords": ["forgery", "cheating", "seven years", "338 BNS", "468 IPC"], "ipc_equivalent": "IPC 468"},

    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "340", "section_title": "Using as genuine a forged document or electronic record",
     "section_text": "Whoever fraudulently or dishonestly uses as genuine any document or electronic record which he knows or has reason to believe to be a forged document or electronic record, shall be punished in the same manner as if he had forged such document or electronic record.",
     "keywords": ["using forged document", "electronic record", "340 BNS", "471 IPC"], "ipc_equivalent": "IPC 471"},

    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "351", "section_title": "Criminal intimidation",
     "section_text": "Whoever threatens another with any injury to his person, reputation or property, or to the person or reputation of any one in whom that person is interested, with intent to cause alarm to that person, or to cause that person to do any act which he is not legally bound to do, or to omit to do any act which that person is legally entitled to do, as the means of avoiding the execution of such threat, commits criminal intimidation.",
     "keywords": ["intimidation", "threat", "injury", "alarm", "351 BNS", "503 IPC"], "ipc_equivalent": "IPC 503/506"},

    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "356", "section_title": "Defamation",
     "section_text": "Whoever, by words either spoken or intended to be read, or by signs or by visible representations, makes or publishes any imputation concerning any person intending to harm, or knowing or having reason to believe that such imputation will harm, the reputation of such person, is said to defame that person. Punishment: simple imprisonment for a term which may extend to two years, or with fine, or with both.",
     "keywords": ["defamation", "reputation", "imputation", "two years", "356 BNS", "499 IPC"], "ipc_equivalent": "IPC 499/500"},
]

# ================================================================
# BNSS — BHARATIYA NAGARIK SURAKSHA SANHITA 2023
# (Replaces CrPC 1973, effective July 1, 2024)
# ================================================================
BNSS_STATUTES = [
    {"act_name": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)", "section_number": "173", "section_title": "FIR — Information in cognizable cases",
     "section_text": "Every information relating to the commission of a cognizable offence, if given orally to an officer in charge of a police station, shall be reduced to writing by him or under his direction, and be read over to the informant. Shall also be entered in the book to be kept by such officer. Electronic FIR now enabled — zero day FIR registration. Copy to informant within 7 days.",
     "keywords": ["FIR", "first information report", "173 BNSS", "154 CrPC", "cognizable", "electronic FIR"], "crpc_equivalent": "CrPC 154"},

    {"act_name": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)", "section_number": "176", "section_title": "Investigation by senior police officers",
     "section_text": "An officer in charge of a police station shall, on receiving an FIR relating to a cognizable offence, investigate or cause the same to be investigated by a subordinate officer. Investigation report (chargesheet) must be filed within 60 days (extendable to 90 days with magistrate permission). Electronic case diary introduced.",
     "keywords": ["investigation", "chargesheet", "60 days", "90 days", "176 BNSS", "156 CrPC"], "crpc_equivalent": "CrPC 156/173"},

    {"act_name": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)", "section_number": "187", "section_title": "Remand — Detention of accused in custody",
     "section_text": "When any person accused of, or suspected of committing, an offence is arrested and detained in custody, and appears or is brought before a Magistrate, the Magistrate, may, if he thinks fit, authorize the detention of the accused in the custody of the police. NEW: Total custody cannot exceed 40 days (down from 60) for most offences, but up to 60 days in serious offences. First 15 days maximum police custody (extended from earlier provisions).",
     "keywords": ["remand", "police custody", "15 days", "40 days", "187 BNSS", "167 CrPC", "custody"], "crpc_equivalent": "CrPC 167"},

    {"act_name": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)", "section_number": "436", "section_title": "Bail in bailable offences",
     "section_text": "When any person other than a person accused of a non-bailable offence is arrested or detained without warrant by an officer in charge of a police station, or appears or is brought before a Court, and is prepared at any time while in the custody of such officer or at any stage of the proceeding before such Court to give bail, such person shall be released on bail. NEW: Electronic bail bonds now permitted.",
     "keywords": ["bail", "bailable", "436 BNSS", "436 CrPC", "electronic bail bond"], "crpc_equivalent": "CrPC 436"},

    {"act_name": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)", "section_number": "480", "section_title": "Bail in non-bailable offences",
     "section_text": "When any person accused of, or suspected of, the commission of any non-bailable offence is arrested or detained without warrant by an officer in charge of a police station, the officer may release such person on bail, with conditions. NEW: If investigation incomplete at time of bail application and accused has spent 1/2 the maximum sentence in detention, bail SHALL be granted.",
     "keywords": ["bail", "non-bailable", "480 BNSS", "437 CrPC", "half punishment", "default bail"], "crpc_equivalent": "CrPC 437"},

    {"act_name": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)", "section_number": "482", "section_title": "Anticipatory bail",
     "section_text": "When any person has reason to believe that he may be arrested on accusation of having committed a non-bailable offence, he may apply to the High Court or the Court of Session for a direction that in the event of such arrest he shall be released on bail. The Court shall decide within 7 days. NEW: Presence of Public Prosecutor mandatory before final anticipatory bail order is passed.",
     "keywords": ["anticipatory bail", "482 BNSS", "438 CrPC", "high court", "sessions court", "7 days"], "crpc_equivalent": "CrPC 438"},

    {"act_name": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)", "section_number": "528", "section_title": "Inherent powers of High Court",
     "section_text": "Nothing in this Sanhita shall be deemed to limit or affect the inherent powers of the High Court to make such orders as may be necessary to give effect to any order under this Code, or to prevent abuse of the process of any Court or otherwise to secure the ends of justice.",
     "keywords": ["inherent powers", "528 BNSS", "482 CrPC", "high court", "quashing", "abuse of process"], "crpc_equivalent": "CrPC 482"},

    {"act_name": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)", "section_number": "35", "section_title": "Attachment of property of persons absconding",
     "section_text": "If any Court has reason to believe (the reason for such belief to be recorded in writing) that any person has absconded or concealed himself so that such warrant cannot be executed, such Court may publish a written proclamation requiring him to appear at a specified place and at a specified time not less than thirty days from the date of publishing such proclamation.",
     "keywords": ["absconder", "proclaimed offender", "35 BNSS", "proclamation", "attachment"], "crpc_equivalent": "CrPC 82/83"},

    {"act_name": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)", "section_number": "356", "section_title": "Trial in absentia — NEW provision",
     "section_text": "NEW IN BNSS — NO CrPC EQUIVALENT. Where a proclaimed offender has declared as such for a period of more than three months, the Court may, after recording reasons, proceed to try the accused in his absence. This enables trial even when accused has absconded.",
     "keywords": ["trial in absentia", "356 BNSS", "proclaimed offender", "new provision", "absconder trial"], "crpc_equivalent": "NEW — No CrPC equivalent"},
]

# ================================================================
# BSA — BHARATIYA SAKSHYA ADHINIYAM 2023
# (Replaces Indian Evidence Act 1872, effective July 1, 2024)
# ================================================================
BSA_STATUTES = [
    {"act_name": "Bharatiya Sakshya Adhiniyam, 2023 (BSA)", "section_number": "2(1)(c)", "section_title": "Electronic record — Definition",
     "section_text": "BSA significantly expands electronic evidence recognition. 'Electronic record' means data, record or data generated, image or sound stored, received or sent in an electronic form or microfilm or computer generated microfiche. Digital and electronic signatures, emails, computer output, stored messages, cloud data all included.",
     "keywords": ["electronic record", "digital evidence", "BSA", "cloud data", "2(1)(c)"], "evidence_act_equivalent": "IEA 65B"},

    {"act_name": "Bharatiya Sakshya Adhiniyam, 2023 (BSA)", "section_number": "57", "section_title": "Admissibility of electronic records",
     "section_text": "All documents, including electronic records, produced for the inspection of the Court shall be called documentary evidence. Electronic records are admissible. A certificate from a responsible official certifying the electronic record is required for admissibility — replaces the stringent 65B certification requirements. Device owner's certificate sufficient.",
     "keywords": ["electronic evidence", "admissibility", "certificate", "57 BSA", "65B IEA", "device owner"], "evidence_act_equivalent": "IEA 65A/65B"},

    {"act_name": "Bharatiya Sakshya Adhiniyam, 2023 (BSA)", "section_number": "23", "section_title": "Admissions — When relevant",
     "section_text": "Statements, oral or documentary or contained in electronic form, which suggest any inference as to any fact in issue or relevant fact and which are made by any of the persons, and under the circumstances, hereinafter mentioned, are admissions.",
     "keywords": ["admission", "oral", "documentary", "electronic", "inference", "23 BSA"], "evidence_act_equivalent": "IEA 17"},
]

# ================================================================
# INCOME TAX ACT 1961 — BUDGET 2025-26 CHANGES (EFFECTIVE APRIL 1, 2026)
# Finance Act 2025 — Union Budget presented February 1, 2025
# ================================================================
IT_ACT_2026_CHANGES = [
    # NEW TAX SLABS — AY 2026-27 (For income earned in FY 2025-26)
    {"act_name": "Income Tax Act, 1961 — AY 2026-27 Tax Slabs (New Regime)", "section_number": "115BAC",
     "section_title": "New Tax Regime — Revised Slabs effective April 1 2026 (AY 2026-27)",
     "section_text": """NEW REGIME TAX SLABS FOR AY 2026-27 (FY 2025-26) — EFFECTIVE APRIL 1, 2026:
Income Slab → Tax Rate
Up to ₹4,00,000 → NIL (increased from ₹3L)
₹4,00,001 – ₹8,00,000 → 5%
₹8,00,001 – ₹12,00,000 → 10%
₹12,00,001 – ₹16,00,000 → 15%
₹16,00,001 – ₹20,00,000 → 20%
₹20,00,001 – ₹24,00,000 → 25%
Above ₹24,00,000 → 30%

REBATE: Full tax rebate u/s 87A for income up to ₹12,00,000 (increased from ₹7L) — effectively NO TAX up to ₹12 lakh under new regime.
STANDARD DEDUCTION: ₹75,000 (increased from ₹50,000) — so effectively NO TAX up to ₹12.75 lakh for salaried employees.
NOTE: Old regime tax slabs remain unchanged. New regime is DEFAULT from AY 2024-25 onwards.""",
     "keywords": ["new tax regime", "slab", "AY 2026-27", "12 lakh rebate", "87A", "115BAC", "April 2026", "zero tax", "75000 standard deduction"]},

    {"act_name": "Income Tax Act, 1961 — AY 2026-27", "section_number": "87A",
     "section_title": "Tax Rebate — Enhanced to ₹12 lakh (effective AY 2026-27)",
     "section_text": "An assessee being an individual resident in India, whose total income does not exceed twelve lakh rupees (increased from seven lakh rupees for AY 2025-26) shall be entitled to a deduction from the amount of income-tax on his total income with which he chargeable. The effect: no income tax payable for individuals with income up to ₹12,00,000 under the new tax regime. For income of ₹12,00,001 or more, full tax as per slabs applies (marginal relief available).",
     "keywords": ["rebate", "87A", "12 lakh", "zero tax", "April 2026", "new regime", "marginal relief"]},

    # TDS RATE CHANGES — EFFECTIVE OCTOBER 1, 2024 (FINANCE ACT 2024) & APRIL 1 2025
    {"act_name": "Income Tax Act, 1961 — TDS Rates Updated", "section_number": "194",
     "section_title": "TDS Rate Changes — Finance Act 2024 & Budget 2025-26",
     "section_text": """TDS RATE REVISIONS (Finance Act 2024 — effective October 1 2024, and Finance Act 2025 — effective April 1 2026):

Section 194D (Insurance Commission): Reduced from 5% to 2%
Section 194DA (Life insurance maturity proceeds): Reduced from 5% to 2%  
Section 194G (Lottery commission): Reduced from 5% to 2%
Section 194H (Commission or brokerage): Reduced from 5% to 2%
Section 194-IB (Rent by individuals/HUF above 50,000/month): Reduced from 5% to 2%
Section 194M (Payment to contractors/professionals by certain persons): Reduced from 5% to 2%
Section 194-O (E-commerce operators): Reduced from 1% to 0.1%
Section 194F (Repurchase of mutual fund units): ABOLISHED — No TDS from Oct 1 2024
Section 206C(1H) (TCS on sale of goods): ABOLISHED — No TCS from April 1 2025 (Finance Act 2025)
Section 194T (NEW): TDS on salary payments to partners of a firm — 10% on salary/commission/bonus/remuneration exceeding ₹20,000 per annum — EFFECTIVE April 1 2025""",
     "keywords": ["TDS rates", "2024", "2025", "2026", "194T", "partner salary", "194H", "194O", "ecommerce", "abolish 194F", "206C(1H) abolished"]},

    {"act_name": "Income Tax Act, 1961 — Finance Act 2025", "section_number": "194T",
     "section_title": "NEW Section 194T — TDS on payment to partners of a firm (April 1 2025)",
     "section_text": "NEW SECTION inserted by Finance Act 2025 — Effective April 1, 2025. Any firm (including LLP) responsible for paying any sum by way of salary, remuneration, commission, bonus or interest to a partner of the firm shall, at the time of credit of such sum to the account of the partner or at the time of payment thereof, whichever is earlier, deduct income tax at the rate of ten per cent. Threshold: ₹20,000 per annum. This means firms must now deduct TDS 10% on partner salary/remuneration exceeding ₹20,000/year.",
     "keywords": ["194T", "TDS partners", "firm", "LLP", "salary", "remuneration", "10%", "April 2025", "new section"]},

    {"act_name": "Income Tax Act, 1961 — Finance Act 2025", "section_number": "80CCD(1B)",
     "section_title": "NPS Deduction — Enhanced contribution by employer",
     "section_text": "Finance Act 2025: Employer's contribution to NPS (National Pension System) increased from 10% to 14% of salary for private sector employees (earlier 14% was only for government employees). Additional deduction u/s 80CCD(1B) of ₹50,000 continues. No change to 80C limits. Effective AY 2025-26 onwards.",
     "keywords": ["NPS", "80CCD", "employer contribution", "14%", "private sector", "pension", "80C"]},

    {"act_name": "Income Tax Act, 1961 — Finance Act 2025", "section_number": "Capital Gains Revised",
     "section_title": "Capital Gains Tax Simplification — Effective July 23 2024 (Finance Act 2024)",
     "section_text": """CAPITAL GAINS — AMENDED BY FINANCE ACT 2024 (effective July 23 2024):

LONG TERM CAPITAL GAINS (LTCG) on listed equity/equity MF/Business Trust:
- Rate: 12.5% (increased from 10%)
- Exemption limit: ₹1,25,000 (increased from ₹1,00,000)
- Indexation benefit: REMOVED for all assets from July 23 2024 onwards

SHORT TERM CAPITAL GAINS (STCG) on listed equity/equity MF/Business Trust:
- Rate: 20% (increased from 15%)
- Applicable when held < 12 months

STCG/LTCG on other assets (property, debt funds, gold, etc.):
- LTCG rate: 12.5% WITHOUT indexation (new) OR 20% WITH indexation (for assets acquired before July 23 2024)
- Holding period for LTCG: 24 months for immovable property (unchanged)

INDEXATION: Removed for new purchases from July 23 2024. For assets purchased BEFORE July 23 2024, taxpayers can choose between 12.5% without indexation or 20% with indexation (whichever is lower tax).""",
     "keywords": ["capital gains", "LTCG", "STCG", "July 2024", "12.5%", "20%", "indexation removed", "1.25 lakh exemption", "Finance Act 2024"]},

    {"act_name": "Income Tax Act, 1961 — Finance Act 2025", "section_number": "43B(h)",
     "section_title": "Section 43B(h) — MSME payment deduction allowed only on actual payment within 45 days",
     "section_text": "Finance Act 2023 — effective April 1 2024. Section 43B now includes clause (h): Any sum payable by an assessee to a micro or small enterprise beyond the time limit specified in MSMED Act 2006 (45 days if written agreement, 15 days if no agreement) shall be allowed as deduction ONLY in the year of actual payment. If payment not made within 45 days, disallowance in current year and deduction only in year of payment. This significantly affects large companies dealing with MSME vendors.",
     "keywords": ["43B(h)", "MSME", "45 days", "payment", "disallowance", "micro small enterprise", "April 2024"]},

    {"act_name": "Income Tax Act, 1961 — Finance Act 2025", "section_number": "Faceless Assessment Update",
     "section_title": "Faceless Assessment and Appeal — Enhancements",
     "section_text": "Finance Act 2025 updates to faceless assessment scheme: (1) Personal hearings now available for cases involving additions above ₹25 lakh; (2) Faceless Appeal scheme continues under Section 250(6C); (3) NaFAC (National Faceless Assessment Centre) jurisdiction expanded; (4) Time limit for completion of assessment extended to 12 months from end of assessment year (was 18 months); (5) Block assessment provisions enhanced for search cases. Disputes Resolution Panel (DRP) available for transfer pricing cases.",
     "keywords": ["faceless assessment", "NaFAC", "personal hearing", "25 lakh", "DRP", "transfer pricing", "12 months"]},

    {"act_name": "Income Tax Act, 1961 — Finance Act 2025", "section_number": "206AB/206CCA",
     "section_title": "Higher TDS/TCS for non-filers (Section 206AB and 206CCA)",
     "section_text": "Sections 206AB and 206CCA: If a payee/collectee has NOT filed Income Tax Return for two preceding years and TDS or TCS exceeds ₹50,000 in each of those years, the rate of TDS/TCS shall be: (a) Twice the normal rate specified; or (b) Twice the rate in force; or (c) 5%, whichever is higher. Deductor must check ITR filing compliance via TRACES before applying normal TDS rates. Non-compliance by deductor leads to assessee-in-default status.",
     "keywords": ["206AB", "206CCA", "non-filer", "higher TDS", "5%", "twice rate", "TRACES", "ITR compliance"]},

    {"act_name": "Income Tax Act, 1961 — Finance Act 2025", "section_number": "Vivad se Vishwas 2.0",
     "section_title": "Vivad se Vishwas Scheme 2.0 — Tax Dispute Resolution",
     "section_text": "Vivad se Vishwas 2.0 Scheme introduced in Finance Act 2024: Eligible disputes include those pending before Commissioner(Appeals), ITAT, High Court, Supreme Court as on July 22 2024. Settlement formula: (i) For disputed tax amount, pay 100% of disputed tax (no interest/penalty); (ii) If appeal filed by taxpayer, pay 100% of tax; (iii) If appeal filed by department, pay 75% of tax. Not available for search cases with additions > ₹5 crore or cases involving PMLA/SEBI/FEMA.",
     "keywords": ["Vivad se Vishwas", "VSV 2.0", "tax dispute", "settlement", "ITAT", "high court", "commissioner appeals", "75%"]},

    {"act_name": "Income Tax Act, 1961 — Budget 2025-26 (April 1 2026)", "section_number": "Updated Compliance Calendar",
     "section_title": "Key IT Deadlines — AY 2026-27 (Income earned FY 2025-26)",
     "section_text": """KEY INCOME TAX DEADLINES for AY 2026-27 (FY 2025-26 income):

Advance Tax (FY 2025-26):
- 1st instalment: June 15, 2025 (15% of tax)
- 2nd instalment: September 15, 2025 (45% cumulative)
- 3rd instalment: December 15, 2025 (75% cumulative)
- 4th instalment: March 15, 2026 (100%)

Income Tax Return Filing (AY 2026-27):
- Non-audit individuals: July 31, 2026
- Tax Audit report (Form 3CB/3CD): September 30, 2026 (Section 44AB, turnover > ₹1 crore business / ₹50 lakh profession)
- Audit cases (companies, firms): October 31, 2026
- Transfer Pricing Audit (Form 3CEB): October 31, 2026
- Belated return: December 31, 2026
- Updated return (ITR-U): 24 months from end of relevant AY

TDS Returns (AY 2026-27):
- Q1 (Apr-Jun 25): July 31, 2025
- Q2 (Jul-Sep 25): October 31, 2025
- Q3 (Oct-Dec 25): January 31, 2026
- Q4 (Jan-Mar 26): May 31, 2026""",
     "keywords": ["deadline", "AY 2026-27", "ITR filing", "July 31", "October 31", "TDS return", "advance tax", "Form 3CD", "Form 3CEB"]},

    {"act_name": "Income Tax Act, 1961 — Finance Act 2025", "section_number": "New Regime Effective April 2026",
     "section_title": "No tax up to ₹12.75L salaried — Complete benefit analysis",
     "section_text": """ZERO TAX STRUCTURE FOR SALARIED EMPLOYEES — AY 2026-27:

Example: Gross salary ₹13,00,000
Less: Standard Deduction ₹75,000
Net Income = ₹12,25,000
Tax at new slab = ₹(computation at 5%,10% slabs) = approx ₹27,500
Less: Rebate u/s 87A (income ≤ ₹12L before standard deduction, so ₹12,25,000 net — marginal relief applies)
Net Tax = Very minimal

For income EXACTLY ₹12,00,000:
Net income after standard deduction = ₹11,25,000
Tax = ₹0 (full rebate u/s 87A as total income ≤ ₹12,00,000)

For income of ₹12,00,001 or more:
Full slab tax applies with NO rebate.

COMPARISON WITH OLD REGIME:
Old regime still offers 80C (₹1.5L), 80D (₹25K-50K), HRA, LTA, etc.
Old regime may be better if total deductions exceed ₹4,00,000.

SURCHARGE RATES (unchanged):
- Income 50L–1Cr: 10%
- Income 1Cr–2Cr: 15%
- Income 2Cr–5Cr: 25%
- Above 5Cr: 25% (reduced from 37% by Finance Act 2023)""",
     "keywords": ["zero tax", "12 lakh", "12.75 lakh", "salaried", "new regime", "AY 2026-27", "surcharge", "comparison old new regime"]},
]

# ================================================================
# MASTER SEEDER FUNCTION
# ================================================================
ALL_NEW_STATUTES = BNS_STATUTES + BNSS_STATUTES + BSA_STATUTES + IT_ACT_2026_CHANGES

async def seed_master():
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]

    print("=" * 60)
    print("ASSOCIATE — MASTER STATUTE SEEDER")
    print("=" * 60)
    
    # Check existing count
    existing = await db.statutes.count_documents({})
    print(f"Current statutes in DB: {existing}")
    
    # Remove old duplicate BNS/BNSS/BSA if any
    del_bns = await db.statutes.delete_many({"act_name": {"$regex": "Bharatiya Nyaya Sanhita"}})
    del_bnss = await db.statutes.delete_many({"act_name": {"$regex": "Bharatiya Nagarik Suraksha"}})
    del_bsa = await db.statutes.delete_many({"act_name": {"$regex": "Bharatiya Sakshya"}})
    del_2026 = await db.statutes.delete_many({"act_name": {"$regex": "AY 2026"}})
    del_2026b = await db.statutes.delete_many({"act_name": {"$regex": "Finance Act 2025"}})
    del_2026c = await db.statutes.delete_many({"act_name": {"$regex": "Budget 2025"}})
    del_2026d = await db.statutes.delete_many({"act_name": {"$regex": "TDS Rates Updated"}})
    del_2026e = await db.statutes.delete_many({"act_name": {"$regex": "AY 2026-27 Tax Slabs"}})
    
    total_deleted = (del_bns.deleted_count + del_bnss.deleted_count + del_bsa.deleted_count +
                     del_2026.deleted_count + del_2026b.deleted_count + del_2026c.deleted_count +
                     del_2026d.deleted_count + del_2026e.deleted_count)
    print(f"Removed {total_deleted} stale entries to re-seed fresh.")
    
    # Insert all new statutes
    if ALL_NEW_STATUTES:
        result = await db.statutes.insert_many(ALL_NEW_STATUTES)
        print(f"✅ Inserted {len(result.inserted_ids)} new statute entries")
    
    # Ensure all indexes
    await db.statutes.create_index([("act_name", 1), ("section_number", 1)])
    await db.statutes.create_index([("keywords", 1)])
    try:
        await db.statutes.create_index([
            ("section_text", "text"),
            ("section_title", "text"),
            ("act_name", "text")
        ])
    except Exception as e:
        # Text index may already exist — drop and recreate
        await db.statutes.drop_index("section_text_text_section_title_text_act_name_text")
        await db.statutes.create_index([
            ("section_text", "text"),
            ("section_title", "text"),
            ("act_name", "text")
        ])
    
    # Final count
    final = await db.statutes.count_documents({})
    print(f"\n{'='*60}")
    print(f"SEEDING COMPLETE")
    print(f"Total statutes in DB: {final}")
    print(f"\nBreakdown of new additions:")
    print(f"  📜 BNS 2023 (replaces IPC):          {len(BNS_STATUTES)} sections")
    print(f"  ⚖️  BNSS 2023 (replaces CrPC):         {len(BNSS_STATUTES)} sections")
    print(f"  📖 BSA 2023 (replaces Evidence Act):  {len(BSA_STATUTES)} sections")
    print(f"  💰 IT Act 2026 changes (Budget 2025): {len(IT_ACT_2026_CHANGES)} entries")
    print(f"{'='*60}\n")
    
    # Print BNS-IPC mapping table
    print("\nBNS ↔ IPC REFERENCE TABLE:")
    for s in BNS_STATUTES:
        ipc = s.get("ipc_equivalent", "N/A")
        print(f"  {s['section_number']:8s} BNS = {ipc}")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(seed_master())
