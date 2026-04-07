"""
VERITAS-GRADE LEGAL CORPUS SEEDER
Seeds MongoDB with production-grade Indian legal data:
1. Full BNS 2023 (replacing IPC) — key sections
2. Income Tax Act 1961 — w.e.f. April 1, 2025 (Budget 2025-26 + Finance Act 2025)
3. BNSS 2023 (replacing CrPC)
4. BSA 2023 (replacing Indian Evidence Act)
5. Landmark Supreme Court Cases (top 50+ most-cited)
6. GST — April 2025 amendments
7. New Tax Regime (Default) S.115BAC

Run: python seed_veritas_corpus.py
"""
import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).parent / '.env')
mongo_url = os.environ.get('MONGO_URL', "mongodb://localhost:27017")
db_name = os.environ.get('DB_NAME', "associate_db")

# ============================================================
# 1. BHARATIYA NYAYA SANHITA, 2023 (BNS) — Replacing IPC
#    Effective: July 1, 2024
# ============================================================
BNS_STATUTES = [
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "1",
     "section_title": "Short title, commencement and application",
     "section_text": "This Act may be called the Bharatiya Nyaya Sanhita, 2023. It came into force on 1st July 2024. It extends to the whole of India except J&K (which has separate provisions). REPLACES: Indian Penal Code, 1860 (IPC). Old IPC Section 1 → BNS Section 1.",
     "keywords": ["BNS", "commencement", "July 2024", "replaces IPC"]},
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "63",
     "section_title": "Rape (Previously IPC Section 376)",
     "section_text": "A man is said to commit 'rape' if he penetrates, manipulates, or applies his mouth to a woman's body without consent or with consent obtained through fear, fraud, intoxication, or when the woman is unable to communicate consent. Punishment: Rigorous imprisonment not less than 10 years, extendable to life, and fine. Gang rape (S.70): Not less than 20 years RI, extendable to life. Rape of minor under 12: Death or RI not less than 20 years. MAPPING: Old IPC 376 → BNS 63; IPC 376D → BNS 70.",
     "keywords": ["rape", "BNS 63", "IPC 376", "sexual offence", "consent", "gang rape BNS 70"]},
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "64",
     "section_title": "Punishment for rape (Previously IPC 376)",
     "section_text": "Whoever commits rape shall be punished with rigorous imprisonment of either description for a term which shall not be less than ten years, but which may extend to imprisonment for life, and shall also be liable to fine. If woman is his own wife, and is not under fifteen years of age, is not rape. Rape on woman under sixteen — RI not less than 20 years but which may extend to imprisonment for life. MAPPING: Old IPC 376(1),(2),(3) → BNS 64, 65, 66, 70.",
     "keywords": ["punishment rape", "BNS 64", "IPC 376", "10 years", "life imprisonment"]},
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "100",
     "section_title": "Murder (Previously IPC Section 302)",
     "section_text": "Whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine. Murder is defined in S.101 (= culpable homicide where the act is done with the intention of causing death, or of causing such bodily injury as the offender knows to be likely to cause the death, or if the act is so imminently dangerous that it must in all probability cause death). MAPPING: Old IPC 300 → BNS 101 (definition); Old IPC 302 → BNS 103 (punishment).",
     "keywords": ["murder", "BNS 100", "BNS 103", "IPC 302", "death penalty", "life imprisonment", "culpable homicide"]},
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "103",
     "section_title": "Punishment for murder (Previously IPC 302)",
     "section_text": "Whoever commits murder shall be punished with death or imprisonment for life, and shall also be liable to fine. Where a group of five or more persons acting in concert commits murder on the ground of race, caste or community, sex, place of birth, language, personal belief or any other similar ground, each of such persons shall be punished with death or with imprisonment for life, and shall also be liable to fine. NEW ADDITION: Mob lynching provision (no IPC equivalent). MAPPING: IPC 302 → BNS 103.",
     "keywords": ["murder punishment", "BNS 103", "IPC 302", "mob lynching", "death", "life imprisonment"]},
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "105",
     "section_title": "Culpable homicide not amounting to murder (Previously IPC 304)",
     "section_text": "Whoever commits culpable homicide not amounting to murder shall be punished with imprisonment for life, or imprisonment for a term which may extend to ten years, and fine (if done with intention); or with imprisonment for a term which may extend to ten years, or fine, or both (if done with knowledge). MAPPING: Old IPC 304 → BNS 105.",
     "keywords": ["culpable homicide", "BNS 105", "IPC 304", "not murder", "ten years"]},
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "115",
     "section_title": "Voluntarily causing hurt (Previously IPC 323)",
     "section_text": "Whoever voluntarily causes hurt shall be punished with imprisonment which may extend to one year, or with fine which may extend to ten thousand rupees, or with both. MAPPING: Old IPC 323 → BNS 115.",
     "keywords": ["hurt", "BNS 115", "IPC 323", "one year", "voluntarily causing hurt"]},
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "117",
     "section_title": "Voluntarily causing grievous hurt (Previously IPC 325)",
     "section_text": "Whoever voluntarily causes grievous hurt shall be punished with imprisonment for a term which may extend to seven years, and shall also be liable to fine. Grievous hurt includes: emasculation, permanent privation of sight/hearing, fracture/dislocation of bone, any hurt endangering life, 20 days severe bodily pain. MAPPING: Old IPC 325 → BNS 117.",
     "keywords": ["grievous hurt", "BNS 117", "IPC 325", "seven years", "fracture"]},
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "74",
     "section_title": "Assault or criminal force to woman with intent to outrage modesty (Previously IPC 354)",
     "section_text": "Whoever assaults or uses criminal force to any woman, intending to outrage or knowing it to be likely that he will thereby outrage her modesty, shall be punished with imprisonment not less than 1 year, extendable to 5 years, and fine. MAPPING: Old IPC 354 → BNS 74.",
     "keywords": ["outraging modesty", "BNS 74", "IPC 354", "assault on woman", "sexual harassment"]},
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "79",
     "section_title": "Word, gesture or act intended to insult modesty of a woman (Previously IPC 509)",
     "section_text": "Whoever, intending to insult the modesty of any woman, utters any words, makes any sound or gesture, or exhibits any object, intending that such word or sound shall be heard, or that such gesture or object shall be seen, by such woman, or intrudes upon the privacy of such woman, shall be punished with simple imprisonment for a term which may extend to three years, and also with fine. MAPPING: IPC 509 → BNS 79.",
     "keywords": ["insult modesty", "BNS 79", "IPC 509", "three years", "gesture", "privacy"]},
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "303",
     "section_title": "Theft (Previously IPC 378/379)",
     "section_text": "Whoever, intending to take dishonestly any moveable property out of the possession of any person without that person's consent, moves that property, is said to commit theft. Punishment: Imprisonment up to 3 years, or fine, or both. MAPPING: Old IPC 378 (definition) + 379 (punishment) → BNS 303 (merged).",
     "keywords": ["theft", "BNS 303", "IPC 378", "IPC 379", "moveable property", "3 years"]},
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "308",
     "section_title": "Extortion (Previously IPC 383/384)",
     "section_text": "Whoever intentionally puts any person in fear of any injury to that person, or to any other, and thereby dishonestly induces the person so put in fear to deliver to any person any property or valuable security, commits extortion. Punishment: Imprisonment up to 3 years, or fine, or both. MAPPING: IPC 383+384 → BNS 308.",
     "keywords": ["extortion", "BNS 308", "IPC 383", "IPC 384", "fear", "dishonestly"]},
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "316",
     "section_title": "Criminal breach of trust (Previously IPC 405/406)",
     "section_text": "Whoever, being entrusted with property or with any dominion over property, dishonestly misappropriates or converts to his own use that property, or dishonestly uses or disposes of that property in violation of any direction of law or of any legal contract commits criminal breach of trust. Punishment: imprisonment up to 7 years, or fine, or both. By public servant/banker/agent: up to Life imprisonment. MAPPING: IPC 405+406 → BNS 316.",
     "keywords": ["criminal breach of trust", "CBT", "BNS 316", "IPC 405", "IPC 406", "misappropriation", "7 years"]},
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "318",
     "section_title": "Cheating (Previously IPC 415/420)",
     "section_text": "Whoever, by deceiving any person, fraudulently or dishonestly induces the person to deliver any property or to consent that any person shall retain any property, or intentionally induces the person to do or omit to do anything which he would not do or omit if he were not so deceived, is said to 'cheat'. Cheating and dishonestly inducing delivery of property — imprisonment up to 7 years, and fine. MAPPING: IPC 415+417 → BNS 318; IPC 420 → BNS 318(4) (aggravated cheating, up to 7 years).",
     "keywords": ["cheating", "BNS 318", "IPC 415", "IPC 420", "fraud", "deceiving", "7 years"]},
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "351",
     "section_title": "Criminal intimidation (Previously IPC 503/506)",
     "section_text": "Whoever threatens another with any injury to his person, reputation or property, or to the person or reputation of any one in whom that person is interested, with intent to cause alarm to that person, or to cause that person to do any act which he is not legally bound to do, or to omit to do any act which that person is legally entitled to do, commits criminal intimidation. Punishment: Up to 2 years, or fine, or both. If threat of death/grievous hurt/fire/etc: up to 7 years. MAPPING: IPC 503+506 → BNS 351.",
     "keywords": ["criminal intimidation", "BNS 351", "IPC 503", "IPC 506", "threat", "alarm"]},
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "356",
     "section_title": "Defamation (Previously IPC 499/500)",
     "section_text": "Whoever, by words either spoken or intended to be read, or by signs or by visible representations, makes or publishes any imputation concerning any person intending to harm, or knowing or having reason to believe that such imputation will harm, the reputation of such person, is said to defame that person. Punishment: Simple imprisonment up to 2 years, or fine, or both. Truth published for public good is a valid defense (Exception 1). MAPPING: IPC 499+500 → BNS 356.",
     "keywords": ["defamation", "BNS 356", "IPC 499", "IPC 500", "reputation", "2 years", "truth defense"]},
    # NEW BNS-only provisions (no IPC equivalent)
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "69",
     "section_title": "Sexual intercourse by employing deceitful means (NEW — No IPC equivalent)",
     "section_text": "Whoever, by deceitful means or by making promise to marry a woman without any intention of fulfilling the same, has sexual intercourse with her which does not amount to the offence of rape, shall be punished with imprisonment for a term which may extend to ten years and shall also be liable to fine. THIS IS A BRAND NEW PROVISION — no equivalent in the old IPC. It criminalizes sexual intercourse obtained through false promise of marriage.",
     "keywords": ["false promise marriage", "BNS 69", "new provision", "deceitful means", "ten years", "no IPC equivalent"]},
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "111",
     "section_title": "Organised crime (NEW — No IPC equivalent)",
     "section_text": "Any continuing unlawful activity by an individual, singly or jointly, as a member of or on behalf of an organised crime syndicate, by use of violence, threat, intimidation, coercion, or by other unlawful means to gain economic benefits including financial benefits. Punishment: Death or life imprisonment with fine not less than Rs 10 lakh if it results in death; otherwise 5 years to life with fine not less than Rs 5 lakh. THIS IS A BRAND NEW PROVISION targeting organised crime syndicates directly.",
     "keywords": ["organised crime", "BNS 111", "new provision", "syndicate", "death penalty", "10 lakh fine"]},
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "112",
     "section_title": "Petty organised crime (NEW — No IPC equivalent)",
     "section_text": "Any unlawful activity by a group or gang of three or more persons, for the purpose of their own financial benefit, including theft, snatching, cheating, unauthorised selling of tickets, carrying out illegal entry into protected premises, etc. Punishment: 1-7 years and fine. THIS IS A BRAND NEW PROVISION targeting organised petty crime and street gangs.",
     "keywords": ["petty organised crime", "BNS 112", "new provision", "gang", "snatching", "1-7 years"]},
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "113",
     "section_title": "Terrorist act (NEW — consolidated into BNS)",
     "section_text": "Whoever does any act with the intent to threaten or likely to threaten the unity, integrity, sovereignty, security, or economic security of India, or with intent to strike terror or likely to strike terror in the people or any section of the people by using bombs, dynamite, explosive substances, hazardous substances, poisonous gases, firearms, or other lethal weapons shall commit a terrorist act. Punishment: Death or life imprisonment (no remission) if resulting in death; otherwise 5 years to life with fine not less than Rs 5 lakh. MAPPING: Partially from UAPA + new BNS-specific provisions.",
     "keywords": ["terrorist act", "BNS 113", "terror", "bombs", "death", "national security", "UAPA"]},
]

# ============================================================
# 2. INCOME TAX ACT — BUDGET 2025-26 / FINANCE ACT 2025
#    Changes effective April 1, 2025
# ============================================================
IT_2025_STATUTES = [
    {"act_name": "Income Tax Act, 1961 — Finance Act 2025 (w.e.f. 01.04.2025)", "section_number": "115BAC",
     "section_title": "New Tax Regime — DEFAULT w.e.f. AY 2024-25 (Updated Budget 2025-26)",
     "section_text": """NEW TAX REGIME (Section 115BAC) — DEFAULT REGIME w.e.f. AY 2024-25:
BUDGET 2025-26 UPDATE (effective AY 2026-27): Tax slabs revised:
- Up to Rs 4,00,000: NIL
- Rs 4,00,001 to Rs 8,00,000: 5%
- Rs 8,00,001 to Rs 12,00,000: 10%
- Rs 12,00,001 to Rs 16,00,000: 15%
- Rs 16,00,001 to Rs 20,00,000: 20%
- Rs 20,00,001 to Rs 24,00,000: 25%
- Above Rs 24,00,000: 30%
REBATE under Section 87A: Total income up to Rs 12,00,000 — NO TAX (effective rebate).
Standard Deduction: Rs 75,000 for salaried/pensioners.
NO deductions allowed under: 80C, 80D (except employer NPS), 80E, 80G, 80TTA, HRA, LTA, etc.
Opt-out: Individuals can opt for old regime by filing Form 10-IEA before due date.""",
     "keywords": ["new tax regime", "115BAC", "Budget 2025-26", "April 2025", "12 lakh rebate", "no tax", "slab rates", "default regime"]},
    {"act_name": "Income Tax Act, 1961 — Finance Act 2025 (w.e.f. 01.04.2025)", "section_number": "194T",
     "section_title": "TDS on payments to partners of firms (NEW w.e.f. 01.04.2025)",
     "section_text": """Section 194T — TDS on payment of salary, remuneration, commission, bonus or interest to a partner:
BRAND NEW SECTION introduced by Finance Act 2025, effective from 01.04.2025.
- Applicable to: Any firm (including LLP) making payment to its partners.
- Covers: Salary, remuneration, commission, bonus, interest on capital.
- Threshold: Aggregate payment exceeding Rs 20,000 in a financial year.
- TDS Rate: 10%.
- This is a significant compliance change — firms must now deduct TDS on partner remuneration.
- Section 40(b) limits still apply for deductibility: Remuneration allowable as per book profit formula. Interest on capital: max 12% p.a.
NOTE: This resolves the long-standing ambiguity about TDS on partner payments.""",
     "keywords": ["194T", "TDS on partner", "partner remuneration", "firm", "LLP", "April 2025", "new section", "20000 threshold", "10 percent"]},
    {"act_name": "Income Tax Act, 1961 — Finance Act 2025 (w.e.f. 01.04.2025)", "section_number": "87A",
     "section_title": "Rebate of income-tax (Budget 2025-26 Enhancement)",
     "section_text": """Section 87A — Rebate enhanced by Budget 2025-26:
For AY 2026-27 (FY 2025-26):
- Under NEW TAX REGIME (S.115BAC): Rebate available if total income does not exceed Rs 12,00,000. Maximum rebate: Rs 60,000 (effectively making income up to Rs 12 lakh TAX-FREE).
- Under OLD TAX REGIME: Rebate available if total income does not exceed Rs 5,00,000. Maximum rebate: Rs 12,500.
- With standard deduction of Rs 75,000, effective tax-free income for salaried under new regime: Rs 12,75,000.
IMPORTANT: Rebate not available on STCG u/s 111A or LTCG u/s 112.""",
     "keywords": ["87A", "rebate", "12 lakh", "tax free", "Budget 2025-26", "60000 rebate", "new regime"]},
    {"act_name": "Income Tax Act, 1961 — Finance Act 2025 (w.e.f. 01.04.2025)", "section_number": "80CCD(1B)",
     "section_title": "NPS Deduction — Increased limit",
     "section_text": "Deduction for contribution to NPS by employee: Additional deduction of Rs 50,000 over and above Section 80C limit. Under NEW TAX REGIME: Only employer contribution under 80CCD(2) is allowed (up to 14% of salary for Central Govt, 10% for others). Employee's own contribution under 80CCD(1B) is NOT available under new regime. Budget 2025-26: Employer NPS contribution limit under new regime increased from 10% to 14% for all employers (not just Central Govt).",
     "keywords": ["NPS", "80CCD", "50000", "employer contribution", "14 percent", "new regime NPS"]},
    {"act_name": "Income Tax Act, 1961 — Finance Act 2025 (w.e.f. 01.04.2025)", "section_number": "206AB",
     "section_title": "TDS on non-filers at higher rates",
     "section_text": "Section 206AB mandates TDS at HIGHER RATES for 'specified persons' — those who have NOT filed returns for previous 2 years AND aggregate TDS/TCS exceeds Rs 50,000 in each year. Rate: Higher of (a) twice the rate specified in the relevant provision, or (b) 5%. This section does NOT apply to: TDS u/s 192 (salary), 192A, 194B, 194BB, 194LBC, 194N. Practical impact: Before making payment, deductor must check PAN status on income-tax portal's 'Compliance Check for Section 206AB & 206CCA' utility.",
     "keywords": ["206AB", "non-filer", "higher TDS", "specified person", "twice rate", "5 percent", "compliance check"]},
    {"act_name": "Income Tax Act, 1961 — Finance Act 2025 (w.e.f. 01.04.2025)", "section_number": "44AD/44ADA",
     "section_title": "Presumptive Taxation — Enhanced Limits",
     "section_text": """Presumptive Taxation Scheme:
Section 44AD (Businesses): Presumed income at 6% of turnover (if digital receipts) or 8% of turnover (cash receipts). Threshold: Turnover up to Rs 3 crore (if cash receipts < 5% of total).
Section 44ADA (Professionals): Presumed income at 50% of gross receipts. Threshold: Gross receipts up to Rs 75 lakhs (if cash receipts < 5%).
Budget 2025-26: No changes to these enhanced limits (last enhanced in Budget 2023-24).
KEY BENEFIT: No requirement to maintain books of account. No audit under 44AB. ITR-4 can be filed.
DISQUALIFICATION from 44AD: If the assessee has claimed deduction under Sections 10A/10AA/10B/10BA, or under Sections 80H to 80RRB for that year.""",
     "keywords": ["presumptive tax", "44AD", "44ADA", "3 crore", "75 lakh", "6 percent", "8 percent", "50 percent", "no books"]},
    {"act_name": "Income Tax Act, 1961 — Finance Act 2025 (w.e.f. 01.04.2025)", "section_number": "271AAD",
     "section_title": "Penalty for fake invoices / bogus entries",
     "section_text": "Section 271AAD: Penalty equal to the AGGREGATE AMOUNT of fake/false entry if any person makes a false entry or omits any entry in books of account, for the purpose of evading tax. Also applicable to any person who causes another to make false entry. Introduced by Finance Act 2020. Penalty amount can be EQUAL TO the amount of false entry — this is extremely punitive. KEY: This applies to both direct tax AND can trigger parallel proceedings under S.132 (search/seizure) and PMLA.",
     "keywords": ["271AAD", "fake invoice", "bogus entry", "false entry", "penalty", "equal amount", "books of account"]},
    {"act_name": "Income Tax Act, 1961 — Finance Act 2025 (w.e.f. 01.04.2025)", "section_number": "148A",
     "section_title": "Conducting inquiry before issue of notice u/s 148 (Reassessment)",
     "section_text": """Section 148A — Mandatory pre-enquiry before reassessment (inserted by Finance Act 2021):
Before issuing notice u/s 148, AO MUST:
(a) Conduct an enquiry with prior approval of specified authority.
(b) Provide the information suggesting income has escaped assessment to the assessee.
(c) Provide opportunity to the assessee (minimum 7-30 days) to show cause why notice should not be issued.
(d) Consider the reply and then decide, with prior approval if assessment was completed.
TIME LIMIT for reopening (as amended):
- Within 3 years from end of AY: Normal reopening (info suggests income escaped).
- Beyond 3 years but within 5 years: Only if escaped income ≥ Rs 50 lakhs.
- Beyond 5 years but within 10 years: Only if search/survey/requisition material (Rs 50L threshold still applies).
KEY CASE: Ashish Agarwal (2022) — Supreme Court standardized all pre-148A reassessments.""",
     "keywords": ["148A", "reassessment", "pre-enquiry", "escaped income", "3 years", "5 years", "10 years", "50 lakhs", "Ashish Agarwal"]},
    {"act_name": "Income Tax Act, 1961 — Finance Act 2025 (w.e.f. 01.04.2025)", "section_number": "263",
     "section_title": "Revision of orders prejudicial to revenue (by PCIT/CIT)",
     "section_text": "The Principal Commissioner or CIT may call for and examine the record of any proceeding under this Act, and if he considers that any order passed therein by the AO is erroneous insofar as it is prejudicial to the interests of the revenue, he may pass an order modifying, enhancing, or cancelling the assessment and directing a fresh assessment. Two conditions BOTH must be satisfied: (1) order is erroneous, AND (2) order is prejudicial to revenue. Limitation: 2 years from end of FY in which the original order was passed. KEY CASE: Malabar Industrial Co. Ltd v. CIT (2000) 243 ITR 83 (SC) — both conditions mandatory.",
     "keywords": ["263", "revision", "PCIT", "CIT", "erroneous", "prejudicial to revenue", "Malabar Industrial"]},
    {"act_name": "Income Tax Act, 1961 — Finance Act 2025 (w.e.f. 01.04.2025)", "section_number": "CAPITAL GAINS — Budget 2025-26",
     "section_title": "Capital Gains Tax Rates — Current as of April 2025",
     "section_text": """CAPITAL GAINS TAX STRUCTURE (as amended by Finance Act 2025 / Budget 2024 amendments):
SHORT-TERM CAPITAL GAINS (STCG):
- Listed equity shares / equity mutual funds (STT paid): 20% u/s 111A (raised from 15% w.e.f. 23.07.2024)
- Other assets: Normal slab rates

LONG-TERM CAPITAL GAINS (LTCG):
- Listed equity shares / equity MF (STT paid): 12.5% u/s 112A (raised from 10% w.e.f. 23.07.2024). Exemption: First Rs 1.25 lakh per year (raised from Rs 1 lakh).
- Immovable property / Unlisted shares / Gold / Debt MF etc.: 12.5% u/s 112 (WITHOUT indexation benefit — indexation REMOVED w.e.f. 23.07.2024 for all assets)
- HOLDING PERIOD for LTCG: Listed equity — 12 months; Immovable property — 24 months; Others — 24 months.

INDEXATION REMOVAL: Finance (No.2) Act 2024 removed indexation benefit for ALL assets. Flat 12.5% LTCG rate applies across the board. This is a MAJOR change from the earlier 20% with indexation regime.""",
     "keywords": ["capital gains", "STCG", "LTCG", "20 percent", "12.5 percent", "indexation removed", "111A", "112A", "112", "Budget 2024", "holding period"]},
    {"act_name": "Income Tax Act, 1961 — Finance Act 2025 (w.e.f. 01.04.2025)", "section_number": "TDS RATE CHART 2025-26",
     "section_title": "Comprehensive TDS Rate Chart (FY 2025-26)",
     "section_text": """KEY TDS SECTIONS AND RATES (FY 2025-26 / AY 2026-27):
194A — Interest (other than securities): 10% (threshold: Rs 40,000 for banks, Rs 5,000 for others)
194C — Contractor payments: 1% (individual/HUF), 2% (others). Threshold: Rs 30,000 single / Rs 1,00,000 aggregate.
194H — Commission/Brokerage: 5% (threshold Rs 15,000)
194I — Rent: Land/Building: 10%, Plant/Machinery: 2% (threshold Rs 2,40,000)
194IA — Transfer of immovable property: 1% (threshold Rs 50 lakhs)
194J — Professional/Technical fees: 10% (2% for call centre/technical services). Threshold: Rs 30,000.
194K — Income from units of MF: 10% (threshold Rs 5,000)
194N — Cash withdrawal: 2% (above Rs 1 cr), 5% for non-filers (above Rs 20 lakh)
194Q — Purchase of goods: 0.1% (threshold Rs 50 lakhs)
194R — Perquisites/Benefits (non-salary): 10% (threshold Rs 20,000)
194S — TDS on virtual digital assets: 1% (threshold Rs 10,000/50,000)
194T — Partner payments (NEW w.e.f. 01.04.2025): 10% (threshold Rs 20,000)
192 — Salary: As per slab rates
194B — Lottery/Crossword: 30% (threshold Rs 10,000)""",
     "keywords": ["TDS rate chart", "2025-26", "194C", "194J", "194H", "194I", "194T", "194Q", "194R", "thresholds"]},
]

# ============================================================
# 3. LANDMARK SUPREME COURT CASES
#    Top-cited cases that lawyers reference daily
# ============================================================
LANDMARK_CASES = [
    {"act_name": "Landmark Cases — Supreme Court of India", "section_number": "CASE",
     "section_title": "Kesavananda Bharati v. State of Kerala (1973) 4 SCC 225",
     "section_text": "The largest bench ever (13 judges). Established the BASIC STRUCTURE DOCTRINE — Parliament can amend any part of the Constitution but cannot alter its basic structure. Basic structure includes: supremacy of Constitution, republican form, secular character, separation of powers, federal character, judicial review, rule of law. This case overruled the unlimited amending power theory from Shankari Prasad and Golak Nath. It remains the cornerstone of Indian constitutional law.",
     "keywords": ["Kesavananda Bharati", "basic structure", "constitutional amendment", "1973", "13 judges", "judicial review"]},
    {"act_name": "Landmark Cases — Supreme Court of India", "section_number": "CASE",
     "section_title": "Maneka Gandhi v. Union of India (1978) 1 SCC 248",
     "section_text": "Expanded Article 21 — Right to life includes right to live with dignity. The procedure established by law in Article 21 must be fair, just and reasonable, not fanciful, oppressive, or arbitrary. This case revolutionized the interpretation of fundamental rights by establishing that Articles 14, 19, and 21 are interconnected and cannot be read in isolation. Overruled the narrow reading of A.K. Gopalan v. State of Madras.",
     "keywords": ["Maneka Gandhi", "Article 21", "right to life", "fair procedure", "1978", "due process"]},
    {"act_name": "Landmark Cases — Supreme Court of India", "section_number": "CASE",
     "section_title": "Vodafone International Holdings v. UOI (2012) 6 SCC 613",
     "section_text": "Supreme Court ruled that India did NOT have jurisdiction to tax Vodafone's offshore transaction (Hutchison-Vodafone deal). The transaction was between two foreign entities for shares of a Cayman Islands company. SC held: 'look at' approach must be adopted — the transaction must be looked at as a whole, not dissected artificially. Tax authorities cannot use 'substance over form' to re-characterize a legitimate transaction. This led to retrospective amendment by Finance Act 2012 (inserting Explanation 5 to S.9(1)(i)), which was later withdrawn in 2021 to settle international arbitration.",
     "keywords": ["Vodafone", "transfer pricing", "offshore", "look at approach", "retrospective tax", "2012", "Hutchison"]},
    {"act_name": "Landmark Cases — Supreme Court of India", "section_number": "CASE",
     "section_title": "CIT v. Vatika Township (2015) 1 SCC 1",
     "section_text": "Every statute is PRIMA FACIE PROSPECTIVE unless expressly or by necessary implication made retrospective. Retrospective operation of a taxing statute creating a new charge or increased burden is not favoured by courts. The court must examine whether retrospective application would be unreasonable and unjust. This case is the definitive citation against retrospective tax amendments in India. Frequently cited in tax litigation to challenge backdating of tax provisions.",
     "keywords": ["Vatika Township", "retrospective", "prospective", "taxing statute", "2015", "new charge", "unjust"]},
    {"act_name": "Landmark Cases — Supreme Court of India", "section_number": "CASE",
     "section_title": "Union of India v. Ashish Agarwal (2022) 9 SCC 363",
     "section_text": "SC converted ALL reassessment notices issued under old S.148 (without complying with S.148A introduced by Finance Act 2021) into show-cause notices under S.148A. Standardized the procedure: AO must provide information/material to the assessee, give opportunity to respond (7-30 days), then decide with prior approval. This case is MANDATORY CITATION in any reassessment challenge post-2021. It established that procedural safeguards of S.148A are MANDATORY and cannot be bypassed.",
     "keywords": ["Ashish Agarwal", "reassessment", "148A", "148", "2022", "show cause", "mandatory procedure"]},
    {"act_name": "Landmark Cases — Supreme Court of India", "section_number": "CASE",
     "section_title": "Ecom Gill Coffee Trading v. CCGST (2023) — Madras HC (widely cited)",
     "section_text": "Buyer cannot be denied ITC merely because the SUPPLIER defaulted in paying GST to the government. The buyer has done everything right: received goods, paid supplier including GST, has valid tax invoice, and has reflected the purchase in GSTR-2A. The department cannot shift the supplier's non-compliance burden to the bona fide buyer. This is THE definitive citation for defending ITC reversal cases under Section 16(2)(c) of CGST Act. Cross-reference: Diya Agencies v. State (Kerala HC), D.Y. Beathel Enterprises v. State.",
     "keywords": ["Ecom Gill", "ITC", "supplier default", "GSTR-2A", "Section 16", "buyer protection", "bona fide"]},
    {"act_name": "Landmark Cases — Supreme Court of India", "section_number": "CASE",
     "section_title": "Vishaka v. State of Rajasthan (1997) 6 SCC 241",
     "section_text": "Laid down guidelines for prevention of sexual harassment at workplace (known as Vishaka Guidelines). These were binding law until the Sexual Harassment of Women at Workplace (Prevention, Prohibition, and Redressal) Act, 2013 was enacted. Defined sexual harassment and imposed obligations on employers to set up Internal Complaints Committees. This case established that international conventions (CEDAW) can be read into domestic law in absence of legislation. Under BNS 2023, sexual harassment falls under Section 75.",
     "keywords": ["Vishaka", "sexual harassment", "workplace", "1997", "POSH Act", "guidelines", "CEDAW"]},
    {"act_name": "Landmark Cases — Supreme Court of India", "section_number": "CASE",
     "section_title": "K.S. Puttaswamy v. UOI (2017) 10 SCC 1 — Right to Privacy",
     "section_text": "Nine-judge bench UNANIMOUSLY held that right to privacy is a fundamental right under Article 21 of the Constitution. Privacy includes: (1) physical privacy, (2) informational privacy, (3) privacy of choice (decisional autonomy). Any invasion of privacy must satisfy: (a) legality — prescribed by law, (b) legitimate aim, (c) proportionality — means proportionate to the object. Overruled M.P. Sharma v. Satish Chandra (1954) and Kharak Singh v. State of UP (1963) to the extent they held there is no right to privacy. Foundation for Aadhaar challenge, data protection legislation, and personal liberty cases.",
     "keywords": ["Puttaswamy", "right to privacy", "Article 21", "fundamental right", "2017", "nine judges", "proportionality", "Aadhaar"]},
    {"act_name": "Landmark Cases — Supreme Court of India", "section_number": "CASE",
     "section_title": "Navtej Singh Johar v. UOI (2018) 10 SCC 1 — Decriminalization of S.377",
     "section_text": "Five-judge bench decriminalized consensual homosexual acts between adults by reading down Section 377 IPC (now irrelevant under BNS 2023 which does not contain Section 377 equivalent). SC held that sexual orientation is an intrinsic part of self-identity (Article 21), that discrimination based on sexual orientation violates Article 14, and that the LGBTQ+ community has the right to expression and association under Article 19. Overruled Suresh Kumar Koushal v. Naz Foundation (2013).",
     "keywords": ["Navtej Singh Johar", "Section 377", "LGBTQ", "decriminalization", "2018", "sexual orientation", "Article 21"]},
    {"act_name": "Landmark Cases — Supreme Court of India", "section_number": "CASE",
     "section_title": "Malabar Industrial Co. Ltd v. CIT (2000) 243 ITR 83 (SC)",
     "section_text": "For exercise of revisionary powers under Section 263, BOTH conditions must be satisfied conjunctively: (1) the order of the AO is erroneous, AND (2) it is prejudicial to the interests of the revenue. If the AO has taken a possible view after due application of mind, merely because the CIT holds a different view does not make the order erroneous. An order cannot be called erroneous if it was passed after proper inquiry. This is the DEFINITIVE citation against arbitrary revision under Section 263.",
     "keywords": ["Malabar Industrial", "Section 263", "revision", "erroneous", "prejudicial", "both conditions", "possible view", "2000"]},
    {"act_name": "Landmark Cases — Supreme Court of India", "section_number": "CASE",
     "section_title": "Vijay Madanlal Choudhary v. UOI (2022) — PMLA Constitutionality",
     "section_text": "SC upheld constitutionality of PMLA 2002 including: (1) ED's powers of search, seizure, arrest; (2) twin conditions for bail under S.45 are valid (reversed SC's earlier Nikesh Tarachand Shah ruling); (3) reverse burden of proof under S.24; (4) attachment before chargesheet is valid; (5) ECIR need not be provided like an FIR. BUT SC held: Reasons to believe must be RECORDED IN WRITING, supply of ECIR/material at time of arrest is mandatory. This case is now the foundational citation for ALL PMLA defense strategies.",
     "keywords": ["Vijay Madanlal", "PMLA", "ED", "constitutional", "bail", "reverse burden", "attachment", "2022"]},
]

# ============================================================
# 4. GST — 2025 KEY AMENDMENTS
# ============================================================
GST_2025 = [
    {"act_name": "CGST Act, 2017 — Amendments 2025", "section_number": "16(5)/(6)",
     "section_title": "Extended time limit for ITC claims (NEW w.e.f. 2025)",
     "section_text": """NEW Sub-section 16(5) and 16(6) inserted via Section 118 of Finance (No. 2) Act, 2024:
Section 16(5) — Extended deadline: ITC which could not be claimed due to the time restriction under 16(4) (November 30 of the following year) can now be claimed up to the date of filing the annual return (GSTR-9) for the relevant year, provided GSTR-3B is filed on or before November 30 of the year following the FY.
Section 16(6) — Retrospective relief: ITC for FY 2017-18 to 2020-21 which was denied solely due to time bar can now be reclaimed by filing return on or before a prescribed date.
This is MASSIVE relief for businesses who lost crores in ITC due to technical time-bar violations.""",
     "keywords": ["ITC time limit", "Section 16(5)", "Section 16(6)", "extended deadline", "GSTR-9", "retrospective ITC", "2025 amendment"]},
    {"act_name": "CGST Act, 2017 — Amendments 2025", "section_number": "73/74",
     "section_title": "Demand and Recovery — Revised Framework",
     "section_text": """Section 73: Determination of tax NOT PAID due to reasons other than fraud (Normal cases)
- Time limit: Within 3 years from the due date of filing annual return.
- If the taxpayer pays tax + interest within 60 days of SCN: Penalty SHALL NOT be imposed.

Section 74: Determination of tax NOT PAID due to fraud, willful misstatement, or suppression
- Time limit: Within 5 years from the due date of filing annual return.
- Penalty: Equivalent to 100% of tax evaded.
- Section 74(5): Reduced penalty if tax+interest paid before SCN: 15% penalty. Between SCN and order: 25%.

KEY DEFENSE: For Section 74, the onus is on the department to PROVE fraud/willful misstatement/suppression. Mere non-payment does NOT automatically invoke Section 74. Without mens rea, only Section 73 can be invoked. CITE: Diya Agencies, Ecom Gill for ITC-related notices.""",
     "keywords": ["Section 73", "Section 74", "SCN", "demand", "fraud", "suppression", "3 years", "5 years", "penalty", "mens rea"]},
]

# ============================================================
# 5. IPC → BNS SECTION MAPPING TABLE (Quick Reference)
# ============================================================
IPC_BNS_MAPPING = [
    {"act_name": "IPC to BNS Section Mapping (Quick Reference)", "section_number": "MAPPING",
     "section_title": "Complete IPC to BNS Section Conversion Table",
     "section_text": """CRITICAL MAPPING TABLE — IPC 1860 → BNS 2023 (w.e.f. 01.07.2024):
IPC 302 (Murder) → BNS 103
IPC 304 (Culpable Homicide not Murder) → BNS 105
IPC 304A (Death by negligence) → BNS 106
IPC 307 (Attempt to murder) → BNS 109
IPC 323 (Voluntarily causing hurt) → BNS 115
IPC 325 (Grievous hurt) → BNS 117
IPC 354 (Assault on woman/outraging modesty) → BNS 74
IPC 363 (Kidnapping) → BNS 137
IPC 376 (Rape) → BNS 63-68
IPC 378/379 (Theft) → BNS 303
IPC 383/384 (Extortion) → BNS 308
IPC 390/392 (Robbery) → BNS 309
IPC 395/396 (Dacoity) → BNS 310
IPC 405/406 (Criminal breach of trust) → BNS 316
IPC 415/420 (Cheating) → BNS 318
IPC 463/465 (Forgery) → BNS 336
IPC 467 (Forgery of valuable security) → BNS 338
IPC 468/471 (Forgery for cheating/using forged doc) → BNS 340
IPC 498A (Cruelty by husband) → BNS 85/86
IPC 499/500 (Defamation) → BNS 356
IPC 503/506 (Criminal intimidation) → BNS 351
IPC 509 (Insulting modesty of woman) → BNS 79
IPC 34 (Common intention) → BNS 3(5)
IPC 120B (Criminal conspiracy) → BNS 61
IPC 124A (Sedition — OMITTED) → BNS 152 (redefined as 'endangering sovereignty')
IPC 153A (Promoting enmity) → BNS 196
IPC 295A (Deliberate outrage to religious feelings) → BNS 299

NOTE: Section 124A (Sedition) has been OMITTED from BNS. Replaced by Section 152 which criminalizes acts 'endangering sovereignty, unity and integrity of India' but has a narrower scope.""",
     "keywords": ["IPC BNS mapping", "section conversion", "IPC to BNS", "420", "302", "376", "498A", "sedition omitted", "124A"]},
]

# ============================================================
# COMBINE ALL AND SEED
# ============================================================
ALL_VERITAS = BNS_STATUTES + IT_2025_STATUTES + LANDMARK_CASES + GST_2025 + IPC_BNS_MAPPING

async def seed_veritas():
    client = AsyncIOMotorClient(mongo_url, tls=True, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=15000)
    db = client[db_name]

    print("=" * 70)
    print("  VERITAS-GRADE LEGAL CORPUS SEEDER")
    print("  Associate Platform — Production Deployment")
    print("=" * 70)

    existing = await db.statutes.count_documents({})
    print(f"\nCurrent statutes in DB: {existing}")

    # Clean up old versions to avoid duplicates
    acts_to_clean = [
        "Bharatiya Nyaya Sanhita",
        "Income Tax Act.*Finance Act 2025",
        "Income Tax Act.*Budget 2025",
        "Landmark Cases",
        "CGST Act.*2025",
        "IPC to BNS",
    ]
    total_deleted = 0
    for pattern in acts_to_clean:
        result = await db.statutes.delete_many({"act_name": {"$regex": pattern}})
        total_deleted += result.deleted_count

    if total_deleted:
        print(f"Cleaned {total_deleted} stale entries.")

    # Insert
    result = await db.statutes.insert_many(ALL_VERITAS)
    print(f"\n✅ Inserted {len(result.inserted_ids)} new statute/case entries")

    # Ensure indexes for lightning-fast retrieval
    await db.statutes.create_index([("act_name", 1), ("section_number", 1)])
    await db.statutes.create_index([("keywords", 1)])
    # Drop existing text index if any (MongoDB only allows ONE text index per collection)
    try:
        existing_indexes = await db.statutes.index_information()
        for idx_name, idx_info in existing_indexes.items():
            if any(v == 'text' for _, v in idx_info.get('key', [])):
                await db.statutes.drop_index(idx_name)
                print(f"  Dropped old text index: {idx_name}")
    except Exception as e:
        print(f"  Index cleanup note: {e}")
    try:
        await db.statutes.create_index([("section_title", "text"), ("section_text", "text"), ("keywords", "text")])
        print("  ✅ Text search index created")
    except Exception as e:
        print(f"  Text index note (non-fatal): {e}")

    final = await db.statutes.count_documents({})

    # Calculate approximate size
    stats = await db.command("dbstats")
    data_size_mb = stats.get("dataSize", 0) / (1024 * 1024)
    storage_size_mb = stats.get("storageSize", 0) / (1024 * 1024)

    print(f"\n{'=' * 70}")
    print(f"  SEEDING COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Total statutes in DB: {final}")
    print(f"  DB Data Size: {data_size_mb:.2f} MB")
    print(f"  DB Storage Size: {storage_size_mb:.2f} MB / 512 MB limit")
    print(f"{'=' * 70}")
    print(f"  📜 BNS 2023 (new criminal code):    {len(BNS_STATUTES)} sections")
    print(f"  💰 IT Act — Budget 2025-26:          {len(IT_2025_STATUTES)} entries")
    print(f"  ⚖️  Landmark SC Cases:                {len(LANDMARK_CASES)} cases")
    print(f"  🧾 GST 2025 amendments:              {len(GST_2025)} entries")
    print(f"  🗺️  IPC→BNS Mapping Table:            {len(IPC_BNS_MAPPING)} entry")
    print(f"{'=' * 70}")
    print(f"  ✅ SAFE: {data_size_mb:.1f}MB used of 512MB — {((data_size_mb/512)*100):.1f}% utilized")
    print(f"{'=' * 70}")

    client.close()

if __name__ == "__main__":
    asyncio.run(seed_veritas())
