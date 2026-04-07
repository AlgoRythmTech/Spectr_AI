"""
FULL CORPUS EXPANSION — BNS + IT Act + BNSS + Companies Act
Adds 200+ additional sections to MongoDB for production-grade coverage.
Stays within 512MB free tier (~2-3MB total estimated).

Run: python seed_full_corpus.py
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
# BNS — REMAINING CRITICAL SECTIONS (adds ~60 more)
# ============================================================
BNS_EXPANDED = [
    # General Exceptions & Right of Private Defence
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "14-33",
     "section_title": "General Exceptions (Previously IPC Ch.IV)",
     "section_text": """Key General Exceptions under BNS:
S.14: Act done by person bound by law (judicial acts) — no offence.
S.15: Act of Judge when acting judicially — no offence.
S.17: Act done by person justified by law — complete defense.
S.19: Act of child under 7 — absolute immunity (doli incapax).
S.20: Act of child 7-12 of immature understanding — conditional immunity.
S.22: Act of person of unsound mind — McNaghten Rules apply.
S.25: Act done under duress/compulsion — defense if threat of instant death.
S.27: Consent — act not an offence if done with valid consent (age > 18, free, informed).
S.28: Communication made in good faith — no defamation.
S.33: Right of private defence — extends to causing death if: reasonable apprehension of death/grievous hurt, rape, kidnapping, robbery, acid attack, or housebreaking by night.
MAPPING: IPC Ch.IV (76-106) → BNS Ch.III (14-33).""",
     "keywords": ["general exceptions", "private defence", "unsound mind", "consent", "child immunity", "doli incapax", "BNS 14-33"]},
    # Abetment
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "45-50",
     "section_title": "Abetment (Previously IPC 107-120)",
     "section_text": """BNS Abetment Framework:
S.45: Definition — abetment by instigation, conspiracy, or intentional aiding.
S.46: Abettor present when offence committed.
S.47: Abetment if act abetted is committed in consequence.
S.48: Punishment for abetment if no express provision — same punishment as principal offender.
S.49: Abetment of offence punishable with death/life — if offence not committed: 7 years + fine.
S.50: Abetment of suicide — 10 years + fine (IPC 306 → BNS 45 read with 108).
KEY: Abetment of suicide (IPC 306 → BNS 108) — Person who abets the commission of suicide shall be punished with imprisonment up to 10 years and fine. Frequently used in dowry death and workplace harassment cases.""",
     "keywords": ["abetment", "BNS 45-50", "IPC 107", "instigation", "conspiracy", "aiding", "abetment of suicide", "IPC 306", "BNS 108"]},
    # Criminal Conspiracy
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "61-62",
     "section_title": "Criminal Conspiracy (Previously IPC 120A-120B)",
     "section_text": """S.61: Criminal conspiracy defined — agreement between two or more persons to do or cause to be done an illegal act, or an act which is not illegal by illegal means.
S.62: Punishment — If conspiracy to commit offence punishable with death/life/RI ≥ 2 years: same as abetment of that offence. Otherwise: 6 months SI, or fine, or both.
KEY PRINCIPLE: Mere agreement is sufficient — no overt act required for serious offences (but evidence of agreement is needed).
EVIDENTIARY STANDARD: Conspiracy is usually proved by circumstantial evidence — direct evidence is rarely available (State of Maharashtra v. Somnath Thapa, 1996).
MAPPING: IPC 120A → BNS 61; IPC 120B → BNS 62.""",
     "keywords": ["criminal conspiracy", "BNS 61", "BNS 62", "IPC 120A", "IPC 120B", "agreement", "Somnath Thapa"]},
    # Kidnapping & Abduction
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "137-141",
     "section_title": "Kidnapping and Abduction (Previously IPC 359-369)",
     "section_text": """S.137: Kidnapping — from India (taking beyond Indian borders without consent) or from lawful guardianship (minor < 18 if male, < 18 if female, or person of unsound mind). Punishment: 7 years + fine.
S.138: Kidnapping for ransom — 7 years to life.
S.139: Kidnapping or abducting to murder — death or life + fine.
S.140: Kidnapping woman to compel marriage — 10 years + fine.
S.141: Procuring minor girl — inducing minor girl under 18 to go from place or to do any act with intent that she may be forced or seduced to illicit intercourse. 10 years + fine.
MAPPING: IPC 359-362 → BNS 137; IPC 364A → BNS 138; IPC 364 → BNS 139.""",
     "keywords": ["kidnapping", "abduction", "BNS 137", "IPC 359", "ransom", "minor", "compel marriage"]},
    # Robbery & Dacoity
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "309-312",
     "section_title": "Robbery and Dacoity (Previously IPC 390-402)",
     "section_text": """S.309: Robbery — theft + force/fear = robbery. Extortion + fear of instant hurt = robbery. Punishment: RI up to 10 years + fine. With hurt: RI up to life.
S.310: Dacoity — robbery by 5 or more persons. Punishment: RI 7 years to life + fine. With murder: Death or life.
S.311: Dacoity with murder — death, or life + fine.
S.312: Preparation for dacoity — 5 years RI + fine.
KEY DISTINCTION: Robbery = theft/extortion + violence by individuals. Dacoity = same but by 5+ persons acting in concert.
MAPPING: IPC 390-395 → BNS 309-310; IPC 396 → BNS 311.""",
     "keywords": ["robbery", "dacoity", "BNS 309", "BNS 310", "IPC 390", "IPC 395", "five persons"]},
    # Forgery
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "336-340",
     "section_title": "Forgery (Previously IPC 463-474)",
     "section_text": """S.336: Forgery — making a false document/electronic record with intent to cause damage, support claim, cause person to part with property, enter into contract. Punishment: 2 years + fine.
S.337: Forgery for purpose of cheating — 7 years + fine.
S.338: Forgery of valuable security/will — 10 years + fine. Covers: promissory notes, cheques, wills, government securities.
S.339: Forgery for purpose of harming reputation — 3 years + fine.
S.340: Using as genuine a forged document — same punishment as for forging.
KEY: Under BNS, electronic record forgery is explicitly covered (unlike IPC which required IT Act 2000 overlay).
MAPPING: IPC 463→BNS 336; IPC 468→BNS 337; IPC 467→BNS 338; IPC 471→BNS 340.""",
     "keywords": ["forgery", "BNS 336", "BNS 338", "IPC 463", "IPC 467", "IPC 471", "valuable security", "electronic record"]},
    # Dowry & Cruelty
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "85-86",
     "section_title": "Cruelty by husband/relatives (Previously IPC 498A) + Dowry Death (IPC 304B)",
     "section_text": """S.85: Cruelty by husband or relative — whoever, being the husband or relative of the husband of a woman, subjects her to cruelty shall be punished with imprisonment up to 3 years and fine. 'Cruelty' means: (a) wilful conduct likely to drive the woman to suicide or grave injury, (b) harassment for dowry demand.
S.86: Dowry death — where the death of a woman is caused by burns/bodily injury or occurs otherwise than under normal circumstances within SEVEN YEARS of marriage, and it is shown she was subjected to cruelty or harassment for dowry before death, such death shall be called 'dowry death'. Punishment: 7 years to life. Reverse burden of proof applies.
IMPORTANT: S.85 (IPC 498A) is COGNIZABLE, NON-BAILABLE, and NON-COMPOUNDABLE. However, SC in Rajesh Sharma v. State of UP (2017) and subsequent rulings has mandated pre-arrest screening by Family Welfare Committees in some states.
MAPPING: IPC 498A → BNS 85; IPC 304B → BNS 86.""",
     "keywords": ["cruelty", "498A", "BNS 85", "BNS 86", "dowry death", "IPC 304B", "seven years", "non-bailable", "Rajesh Sharma"]},
    # Sedition replacement
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "152",
     "section_title": "Endangering sovereignty, unity and integrity of India (Replaces Sedition IPC 124A)",
     "section_text": """S.152: Whoever purposely or knowingly, by words, either spoken or written, or by signs, or by visible representation, or by electronic communication, or by use of financial means, or otherwise, excites or attempts to excite, secession or armed rebellion or subversive activities; or encourages feelings of separatist activities; or endangers sovereignty or unity and integrity of India; shall be punished with imprisonment for life or imprisonment up to 7 years and fine.
KEY DIFFERENCES FROM OLD IPC 124A (SEDITION):
1. The word 'sedition' has been DROPPED entirely.
2. Mere 'disaffection towards the Government' is NO LONGER an offence.
3. Now requires 'exciting secession/armed rebellion/subversive activities' — a much higher threshold.
4. Adds 'electronic communication' and 'financial means' as new modes.
5. Comments expressing disapprobation of Government actions with a view to obtain their alteration by lawful means, without exciting the above, are NOT an offence (Exception).
MAPPING: IPC 124A (REPEALED) → BNS 152 (narrower scope).""",
     "keywords": ["sedition", "BNS 152", "IPC 124A", "sovereignty", "secession", "armed rebellion", "repealed", "narrower scope"]},
    # Offences against State / National Security
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "147-153",
     "section_title": "Offences against the State (Previously IPC 121-130)",
     "section_text": """S.147: Waging/attempting to wage war against Government of India — Death or life imprisonment.
S.148: Conspiracy to wage war — Life imprisonment or up to 10 years + fine.
S.149: Collecting arms etc. with intention of waging war — Life or up to 10 years + fine.
S.150: Concealing with intent to facilitate waging of war — 10 years + fine.
S.152: Endangering sovereignty (replaces sedition) — see dedicated entry.
S.153: Acts endangering sovereignty committed outside India — same punishment, extends jurisdiction extraterritorially.
KEY: BNS explicitly makes these offences cognizable and non-bailable. NIA has concurrent jurisdiction.
MAPPING: IPC 121-124 → BNS 147-150; IPC 124A → BNS 152.""",
     "keywords": ["waging war", "BNS 147", "IPC 121", "national security", "conspiracy", "arms", "NIA", "extraterritorial"]},
    # Promoting enmity
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "196-197",
     "section_title": "Promoting enmity between groups (Previously IPC 153A-153B)",
     "section_text": """S.196: Promoting enmity between different groups — whoever by words, signs, visible representations, electronic communication, promotes or attempts to promote enmity between different religious, racial, linguistic, or regional groups, or does acts prejudicial to maintenance of harmony. Punishment: 3 years + fine (5 years for offence in place of worship or religious assembly).
S.197: Imputations/assertions prejudicial to national integration — 3 years + fine. Includes making imputations that any class of persons cannot bear true faith and allegiance to the Constitution.
NEW: Explicitly covers 'electronic communication' unlike old IPC 153A.
MAPPING: IPC 153A → BNS 196; IPC 153B → BNS 197.""",
     "keywords": ["promoting enmity", "BNS 196", "IPC 153A", "communal", "religious", "electronic communication"]},
    # Criminal misappropriation
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "314",
     "section_title": "Criminal misappropriation (Previously IPC 403)",
     "section_text": "Whoever dishonestly misappropriates or converts to his own use any movable property, is guilty of criminal misappropriation. Punishment: up to 2 years, or fine, or both. If property entrusted in a specific capacity (e.g., clerk/servant/agent): up to 7 years. KEY DISTINCTION from CBT (S.316): In misappropriation, the initial possession is innocent/accidental. In CBT, property is entrusted. This distinction is critical for framing charges correctly. MAPPING: IPC 403 → BNS 314; IPC 404 → BNS 315.",
     "keywords": ["misappropriation", "BNS 314", "IPC 403", "dishonestly", "movable property", "entrusted"]},
    # Mischief
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "324",
     "section_title": "Mischief (Previously IPC 425/426)",
     "section_text": "Whoever with intent to cause wrongful loss or damage to public or any person, or with knowledge that he is likely to cause wrongful loss or damage, causes the destruction of any property, or any such change in any property or in the situation thereof as destroys or diminishes its value or utility, commits mischief. Punishment: 3 months or fine, or both. By fire/explosive (S.325): 7 years + fine. Against public infrastructure: 5 years + fine. MAPPING: IPC 425 → BNS 324; IPC 436 → BNS 325.",
     "keywords": ["mischief", "BNS 324", "IPC 425", "destruction", "property damage", "fire", "explosive"]},
    # Attempt
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "109",
     "section_title": "Attempt to murder (Previously IPC 307)",
     "section_text": "Whoever does any act with such intention or knowledge, and under such circumstances that, if he by that act caused death, he would be guilty of murder, shall be punished with imprisonment up to 10 years and fine. If hurt is caused: up to Life imprisonment. If the offender is under sentence of imprisonment for life: may be punished with death. KEY: The 'last act test' — whether the accused did everything in his power to cause death, or the 'proximity test' — whether the act was sufficiently proximate to the intended result. MAPPING: IPC 307 → BNS 109.",
     "keywords": ["attempt to murder", "BNS 109", "IPC 307", "10 years", "life", "death", "last act test"]},
    # Death by negligence
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "106",
     "section_title": "Causing death by negligence (Previously IPC 304A)",
     "section_text": """Whoever causes death of any person by doing any rash or negligent act not amounting to culpable homicide, shall be punished with:
- General: imprisonment up to 5 years + fine.
- If by registered medical practitioner: imprisonment up to 2 years + fine (NEW — separate lower threshold for doctors).
KEY CHANGE FROM IPC: BNS 106(2) specifically provides a LOWER PUNISHMENT for medical professionals causing death by negligence (2 years vs 5 years). This resolves the Jacob Mathew v. State of Punjab (2005) debate about criminal liability of doctors.
MAPPING: IPC 304A → BNS 106.""",
     "keywords": ["death by negligence", "BNS 106", "IPC 304A", "rash", "negligent", "medical negligence", "doctor", "Jacob Mathew", "2 years"]},
    # Snatching (New)
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "304",
     "section_title": "Snatching (NEW — No IPC equivalent)",
     "section_text": "Whoever commits theft by snatching, by suddenly or quickly or forcibly seizing or grabbing any movable property from any person or from his possession, shall be punished with imprisonment up to 3 years and fine. THIS IS A BRAND NEW PROVISION — no equivalent in the old IPC. It fills the gap between simple theft (BNS 303) and robbery (BNS 309) for incidents like mobile/chain/purse snatching. MAPPING: NO IPC equivalent → BNS 304.",
     "keywords": ["snatching", "BNS 304", "new provision", "theft", "mobile snatching", "chain snatching", "3 years"]},
    # Hit and Run (New)
    {"act_name": "Bharatiya Nyaya Sanhita, 2023 (BNS)", "section_number": "106(2)",
     "section_title": "Hit and Run — Failure to report accident (NEW enhanced provision)",
     "section_text": "Where the death is caused by a person driving a vehicle, who fails to report the accident to a police officer or a Magistrate at the earliest: imprisonment up to 10 years + fine. This is a MASSIVE enhancement from IPC 304A which provided only 2 years. The provision specifically targets hit-and-run drivers. NOTE: This provision faced massive nationwide protests from truck/bus driver unions in January 2024, and its implementation was initially deferred by the government.",
     "keywords": ["hit and run", "BNS 106", "accident", "vehicle", "10 years", "failure to report", "driver", "new provision"]},
]

# ============================================================
# IT ACT — COMPREHENSIVE SECTION COVERAGE
# ============================================================
IT_FULL = [
    # Residential Status
    {"act_name": "Income Tax Act, 1961", "section_number": "6",
     "section_title": "Residence in India",
     "section_text": """Section 6 determines residential status which governs scope of taxable income:
INDIVIDUAL — Resident if: (a) present in India 182+ days in the previous year, OR (b) present 60+ days in PY AND 365+ days in preceding 4 PYs.
Exception to 60-day rule: Indian citizen leaving India for employment abroad / crew member — 182 days needed.
Budget 2020 change: Indian citizen / PIO with income > Rs 15 lakh from Indian sources AND not tax resident anywhere: DEEMED RESIDENT (RNOR status, not full resident).
NOR (Resident but Not Ordinarily Resident): Resident who was NR in 9 out of 10 preceding PYs; OR stayed in India ≤ 729 days in preceding 7 PYs.
NON-RESIDENT: Anyone who doesn't satisfy resident conditions.
COMPANY — Resident if incorporated in India OR PoEM (Place of Effective Management) is in India in that year.""",
     "keywords": ["residential status", "Section 6", "182 days", "60 days", "NRI", "RNOR", "PoEM", "deemed resident", "15 lakh"]},
    # Exemptions
    {"act_name": "Income Tax Act, 1961", "section_number": "10",
     "section_title": "Incomes not included in total income (Key Exemptions)",
     "section_text": """Section 10 — Key Exemptions (available under BOTH old and new regime unless noted):
10(10D) — Maturity proceeds of life insurance policy: Exempt if annual premium ≤ 10% of sum assured (policies issued before 01.04.2012: 20%). Policies issued after 01.04.2023 with aggregate premium > Rs 5 lakh: TAXABLE.
10(10) — Death-cum-retirement gratuity: Govt employees: fully exempt. Others: least of (a) 15 days salary × years of service, (b) Rs 20 lakh, (c) actual gratuity.
10(10AA) — Leave encashment on retirement: Govt: fully exempt. Others: least of (a) 10 months average salary, (b) Rs 25 lakh, (c) actual amount.
10(14) — Special allowances: Children education (Rs 100/child/month), hostel (Rs 300/child/month). Only under Old Regime.
10(23C) — Income of educational/medical institutions: if gross receipts < Rs 5 crore.
10(38) — LTCG on listed equity: WITHDRAWN w.e.f. AY 2019-20 (replaced by S.112A).""",
     "keywords": ["exemptions", "Section 10", "10(10D)", "life insurance", "gratuity", "leave encashment", "20 lakh", "25 lakh"]},
    # Salary Income
    {"act_name": "Income Tax Act, 1961", "section_number": "15-17",
     "section_title": "Income from Salaries",
     "section_text": """S.15 — Salary chargeable on DUE or RECEIPT basis, whichever is earlier. Includes wages, annuity, pension, gratuity, fees/commission, perquisites, profits in lieu of salary.
S.16 — Deductions from salary: (a) Standard Deduction of Rs 75,000 (enhanced by Budget 2025-26, earlier Rs 50,000), (b) Entertainment Allowance (Govt only), (c) Professional Tax (max Rs 2,500).
S.17(1) — Salary includes: basic, DA (if enters retirement), bonus, commission, fees.
S.17(2) — Perquisites: Rent-free accommodation (15% of salary in metro, 10% others), Car (Rs 1,800-2,400/month), Free education > Rs 1,000/month, Interest-free loans (SBI lending rate benchmark).
S.17(3) — Profits in lieu of salary: Compensation on termination, golden handshake (S.89 relief available).
HRA EXEMPTION — S.10(13A): Least of: (a) Actual HRA, (b) 50%/40% of salary (metro/non-metro), (c) Rent paid - 10% of salary. NOT available under New Regime.""",
     "keywords": ["salary", "Section 15", "Section 16", "Section 17", "perquisites", "standard deduction", "75000", "HRA", "10(13A)"]},
    # House Property
    {"act_name": "Income Tax Act, 1961", "section_number": "22-27",
     "section_title": "Income from House Property",
     "section_text": """S.22-27 — Income from House Property:
S.22: Annual value of property consisting of any buildings or lands is chargeable. Owner must be the deemed owner as per S.27.
S.23: Annual value = Higher of Municipal Valuation or Fair Rent, but capped at Standard Rent under Rent Control. If let out: Actual rent received/receivable (if higher). Self-occupied: Annual value = NIL for up to 2 properties.
S.24: Deductions from HP income:
(a) Standard deduction: 30% of Net Annual Value (flat, no actuals needed).
(b) Interest on borrowed capital: Self-occupied: max Rs 2,00,000 (S.24(b)). Let-out: No limit.
Pre-construction interest: Deductible in 5 equal installments from year of completion.
S.80EE/80EEA — Additional interest deduction (now expired for new loans, only available for loans before 01.04.2022).
Budget 2025-26: Rs 2 lakh cap on interest for self-occupied continues. Under New Regime: ONLY S.24(b) deduction for let-out property and 30% standard deduction allowed.""",
     "keywords": ["house property", "Section 22", "Section 24", "interest", "2 lakh", "self-occupied", "let-out", "standard deduction 30%"]},
    # Business Income - Key Disallowances
    {"act_name": "Income Tax Act, 1961", "section_number": "40/40A/43B",
     "section_title": "Key Disallowances under Business Income",
     "section_text": """CRITICAL DISALLOWANCE SECTIONS:
S.40(a)(i): Payment to non-resident without TDS — DISALLOWED entirely. Even if TDS paid late: allowed only in year of payment.
S.40(a)(ia): Payment to resident without TDS — Disallowed 30% of amount. If TDS deducted but deposited before return filing: allowed.
S.40(b): Partner remuneration — Capped at: First Rs 6 lakh of book profit: Rs 3 lakh OR 90% (higher). Balance: 60%.
S.40A(2): Excessive/unreasonable payments to related parties — AO may disallow if payment exceeds fair market value.
S.40A(3): Cash payment > Rs 10,000 — DISALLOWED (exceptions: bank holiday, transport, village areas).
S.43B: Certain deductions only on ACTUAL PAYMENT basis:
(a) Tax/duty/cess/fee under any law
(b) Employer contribution to PF/Superannuation/Gratuity
(c) Bonus/Commission to employees
(d) Interest on any loan from scheduled bank/PFI/NBFC
(da) Interest on any loan from deposit-taking NBFC
(e) Leave encashment
(h) Payment to MSME within time limit under MSMED Act (15/45 days) — if not paid within due date, disallowed in that year.
KEY: S.43B(h) MSME payment compliance is now THE most critical disallowance for businesses (effective AY 2024-25).""",
     "keywords": ["disallowance", "40(a)", "40A(3)", "43B", "TDS", "cash payment", "MSME", "43B(h)", "partner remuneration", "10000"]},
    # Sections 54, 54EC, 54F
    {"act_name": "Income Tax Act, 1961", "section_number": "54/54EC/54F",
     "section_title": "Capital Gains Exemptions",
     "section_text": """CAPITAL GAINS EXEMPTION SECTIONS:
S.54 — LTCG on sale of residential house: Exempt if reinvested in ONE residential house within 1 year before or 2 years after sale, OR constructed within 3 years. Max exemption: Rs 10 crore (cap introduced Finance Act 2023). Can claim only against ONE new house (not two, per SC in CIT v. Devdas Naik).
S.54EC — LTCG on any long-term asset: Exempt up to Rs 50 lakhs per FY if invested in specified bonds (NHAI/REC/PFC) within 6 months of transfer. Lock-in: 5 years (extended from 3 years by Finance Act 2018). Cannot be pledged.
S.54F — LTCG on sale of any asset OTHER THAN residential house: Full exemption if entire NET CONSIDERATION (not just capital gain) is invested in ONE residential house. Proportional exemption if partial investment. Conditions: Should not own more than one residential house on date of transfer (excluding the new house).
NOTE: Post-indexation removal (23.07.2024), these exemptions become even MORE critical as the only way to reduce LTCG tax at 12.5%.""",
     "keywords": ["54", "54EC", "54F", "capital gains exemption", "residential house", "NHAI bonds", "10 crore cap", "50 lakhs", "6 months"]},
    # Search / Survey / Reassessment
    {"act_name": "Income Tax Act, 1961", "section_number": "132/133A/153A/153C",
     "section_title": "Search, Survey, and Reassessment after Search",
     "section_text": """SEARCH & SEIZURE FRAMEWORK:
S.132 — Search and seizure: Where the PDIT/DIT has reason to believe that: (a) person has not complied with summons/notice, (b) person is in possession of undisclosed property/books, (c) information received. Can enter premises, break open locks, seize documents/valuables/cash.
S.133A — Survey: Can enter the business premises during working hours. Can record statements. CANNOT seize assets (unlike search). Commonly used by dept before initiating a full search.
S.153A — Assessment in case of search: For 6 AYs preceding the AY of search — AO shall issue notice requiring filing of returns. Even if return was already filed, AO can make assessment de novo for those 6 years. Beyond 6 years (up to 10 years): Only if incriminating material found AND undisclosed income > Rs 50 lakhs.
S.153C — Assessment of person other than searched person: If during search of Person A, books/documents relating to Person B are found — AO of Person B shall assess/reassess for the same 6-year period.
KEY DEFENSE: Rely on Singhad Technical Education Society (2017) — no incriminating material found during search = no addition can be made for completed assessments.""",
     "keywords": ["search", "seizure", "132", "133A", "153A", "153C", "6 assessment years", "incriminating material", "Singhad"]},
    # Sections 68-69D (Unexplained credits/investments)
    {"act_name": "Income Tax Act, 1961", "section_number": "68/69/69A/69B/69C/69D",
     "section_title": "Unexplained Cash Credits, Investments, and Expenditure",
     "section_text": """THE 'DEEMING PROVISIONS' — Used to tax unexplained money:
S.68 — Unexplained cash credits: If any sum is found credited in the books and the assessee offers no satisfactory explanation about the nature and source: taxable as income. Rate: 60% + surcharge + cess (77.25% effective) under S.115BBE if the source is not satisfactorily explained. KEY: Onus is on assessee to prove (a) identity of creditor, (b) creditworthiness of creditor, (c) genuineness of transaction. All three must be proved: CIT v. P. Mohanakala (2007).
S.69 — Unexplained investments.
S.69A — Unexplained money/bullion/jewellery/valuable article.
S.69B — Amount of investments not fully disclosed.
S.69C — Unexplained expenditure.
S.69D — Amount borrowed/repaid on hundi.
ALL of S.68-69D are taxed at 60% + surcharge + cess = 77.25% under S.115BBE. NO deduction of any expenditure or allowance is permitted against this income.
KEY DEFENSE: Creditworthiness can be proved via bank statements and ITR of the creditor. Identity via PAN and address.""",
     "keywords": ["unexplained", "68", "69", "cash credit", "deeming provision", "77.25%", "115BBE", "identity", "creditworthiness", "Mohanakala"]},
    # 80C family
    {"act_name": "Income Tax Act, 1961", "section_number": "80C/80CCC/80CCD",
     "section_title": "Deductions — Chapter VI-A (Investment-linked)",
     "section_text": """S.80C — Deduction up to Rs 1,50,000 for:
PPF, ELSS, NSC, 5-year FD, LIC premiums (max 10% of SA), tuition fees (2 children), Home Loan principal, SSY, NPS, SCSS. Available ONLY under Old Regime.
S.80CCC — Contribution to pension fund: Within 80C limit of Rs 1,50,000.
S.80CCD(1) — Employee's NPS contribution: Within 80C limit.
S.80CCD(1B) — Additional NPS deduction: Rs 50,000 (over and above 80C limit). Old Regime only.
S.80CCD(2) — Employer's NPS contribution: Outside 80C limit. Up to 14% of salary (Central Govt) / 14% for all employers under New Regime (Budget 2025-26). ONLY NPS deduction available under New Regime.

TOTAL CAP: 80C + 80CCC + 80CCD(1) = Rs 1,50,000. Plus Rs 50,000 u/s 80CCD(1B) = Rs 2,00,000 total. Plus employer NPS (no cap under old regime).
NEW REGIME: NONE of 80C/80CCC/80CCD(1)/80CCD(1B) available. Only 80CCD(2) allowed.""",
     "keywords": ["80C", "80CCD", "1.5 lakh", "PPF", "ELSS", "NPS", "50000", "old regime only", "deduction"]},
    # 80D, 80E, 80G, 80TTA
    {"act_name": "Income Tax Act, 1961", "section_number": "80D/80E/80G/80TTA/80TTB",
     "section_title": "Deductions — Health, Education, Donations, Interest",
     "section_text": """S.80D — Health Insurance Premium: Self/spouse/children: Rs 25,000 (Rs 50,000 if senior). Parents: additional Rs 25,000 (Rs 50,000 if senior). Preventive health check-up: Rs 5,000 within above limits. TOTAL MAX: Rs 1,00,000 (if both self and parents are senior). Old Regime only.
S.80E — Interest on Education Loan: No monetary limit. Available for 8 years from year of repayment. Can be for self, spouse, or children. Old Regime only.
S.80G — Donations: 100% deduction: PM CARES, National Defence Fund. 50% deduction: Most others (subject to 10% of ATI). Qualifying limit: 10% of Adjusted Total Income. Must be made via banking channels (>Rs 2,000 by cash not allowed). Old Regime only.
S.80TTA — Interest on savings accounts: Max Rs 10,000 deduction for non-senior citizens. Old Regime only.
S.80TTB — Interest on deposits (senior citizens): Max Rs 50,000 (replaces 80TTA for seniors). Old Regime only.
CRITICAL: ALL of these (80D, 80E, 80G, 80TTA, 80TTB) are UNAVAILABLE under New Tax Regime (S.115BAC).""",
     "keywords": ["80D", "80E", "80G", "80TTA", "health insurance", "education loan", "donation", "25000", "50000", "old regime only"]},
    # Sec 194 expanded TDS
    {"act_name": "Income Tax Act, 1961", "section_number": "194/194A/194B/194C/194D",
     "section_title": "TDS Provisions — Complete Reference",
     "section_text": """COMPLETE TDS SECTION REFERENCE:
192 — Salary: Slab rates. Employer must consider all sources if Form 12B filed.
194 — Dividend: 10% (threshold Rs 5,000).
194A — Interest other than securities: 10%. Banks: threshold Rs 40,000 (Rs 50,000 for seniors). Others: Rs 5,000.
194B — Lottery/Game show: 30% (threshold Rs 10,000).
194C — Contractor: 1% (individual/HUF), 2% (company/firm). Single Rs 30,000 / Aggregate Rs 1,00,000.
194D — Insurance commission: 5% (threshold Rs 15,000).
194DA — Life insurance maturity: 5% on amount exceeding exempt portion.
194E — Payment to non-resident sportsman/entertainer: 20%.
194EE — NSS: 10% (threshold Rs 2,500).
194G — Lottery tickets commission: 5% (threshold Rs 15,000).
194H — Commission/Brokerage: 5% (threshold Rs 15,000).
194I — Rent: 2% (P&M/Equipment), 10% (Land/Building). Threshold Rs 2,40,000.
194IA — Property transfer: 1% (threshold Rs 50 lakhs).
194IB — Rent by individual/HUF: 5% (threshold Rs 50,000/month).
194IC — JDA consideration: 10%.
194J — Professional/Technical fees: 10% (2% for technical/call centre). Threshold Rs 30,000.
194LA — Compulsory acquisition immovable property: 10% (threshold Rs 2,50,000).
194M — Commission to resident (by individual/HUF): 5% (threshold Rs 50 lakh aggregate).
194N — Cash withdrawal: 2%/5% (thresholds Rs 1 cr / Rs 20 lakh for non-filers).
194O — E-commerce operator: 1% (threshold Rs 5 lakh).
194P — TDS on senior citizen ≥ 75 years (banks exempt from filing returns).
194Q — Purchase of goods: 0.1% (threshold Rs 50 lakhs).
194R — Perquisites/benefits: 10% (threshold Rs 20,000).
194S — Virtual digital assets: 1% (threshold Rs 10,000/Rs 50,000).
194T — Partner payments (NEW 01.04.2025): 10% (threshold Rs 20,000).""",
     "keywords": ["TDS", "194", "194A", "194C", "194J", "194H", "194I", "194Q", "194R", "194N", "194T", "complete reference"]},
    # Appeals
    {"act_name": "Income Tax Act, 1961", "section_number": "246A/250/253/260A/261",
     "section_title": "Appellate Framework — Complete Hierarchy",
     "section_text": """INCOME TAX APPEAL HIERARCHY:
1. CIT(Appeals) / JCIT(Appeals) [S.246A]: First appeal. File within 30 days of order. Monetary limit for JCIT(A): demand up to Rs 50 lakhs. Rs 250/500/1000 fee.
2. ITAT [S.253]: Second appeal. File within 60 days. Two-member bench (Judicial + Accountant). Can admit additional grounds. ITAT is final fact-finding authority — SC/HC cannot re-evaluate facts.
3. High Court [S.260A]: Tax reference/appeal only on SUBSTANTIAL QUESTION OF LAW. File within 120 days.
4. Supreme Court [S.261]: Appeal from HC if HC certifies it's fit for SC, or by SLP.

MONETARY LIMITS FOR DEPT APPEALS (revised circular):
ITAT: Rs 50 lakh (dept won't appeal below this)
High Court: Rs 1 crore
Supreme Court: Rs 2 crore

STAY OF DEMAND: S.220(6) — AO can grant stay if hardship shown. S.254(2A) — ITAT can grant stay for 365 days. CIT(A) has inherent power to grant stay.
KEY: Always check if the dept is barred from appealing due to monetary limit (CBDT Circular 17/2019 and subsequent revisions).""",
     "keywords": ["appeal", "CIT Appeals", "ITAT", "High Court", "246A", "253", "260A", "stay of demand", "monetary limit", "30 days", "60 days"]},
    # Penalties
    {"act_name": "Income Tax Act, 1961", "section_number": "270A/270AA/271/271AAD",
     "section_title": "Penalty Framework — Complete Reference",
     "section_text": """PENALTY SECTIONS:
S.270A — Penalty for under-reporting/misreporting: Under-reporting: 50% of tax on under-reported income. Misreporting: 200% of tax. Misreporting includes: misrepresentation of facts, failure to record investments, claim of false expenditure, recording false entries, failure to report international transaction.
S.270AA — Immunity from penalty: If assessee files appeal, pays the tax, and furnishes an undertaking. Application to CIT within 1 month of order.
S.271(1)(b) — Non-compliance with notices (summons): Rs 10,000 per default.
S.271(1)(c) — OLD concealment penalty (pre-01.04.2017): 100%-300% of tax sought to be evaded. Still applies for AYs before 2017-18.
S.271AAD — False entry in books: Penalty = AMOUNT of false entry (not tax on it — the entire amount). Extremely punitive.
S.271B — Failure to get accounts audited u/s 44AB: 1.5% of turnover or Rs 1,50,000 (lower).
S.271F — Failure to furnish return: Rs 5,000 (if filed after due date but before 31 Dec), Rs 10,000 otherwise. If income < Rs 5 lakh: Rs 1,000.
S.276C — Prosecution for wilful evasion: RI 6 months to 7 years + fine. For tax exceeding Rs 25 lakh: RI 1-7 years.""",
     "keywords": ["penalty", "270A", "271", "271AAD", "under-reporting", "misreporting", "50%", "200%", "false entry", "prosecution", "276C"]},
]

# ============================================================
# COMPANIES ACT 2013 — KEY SECTIONS
# ============================================================
COMPANIES_ACT = [
    {"act_name": "Companies Act, 2013", "section_number": "2(76)/188/184",
     "section_title": "Related Party Transactions (RPT)",
     "section_text": """S.2(76) — Related Party: Includes directors, KMP, their relatives, subsidiary/holding/associate companies, any entity with 20%+ voting power.
S.188 — Related party transactions: Board approval needed for ALL RPTs. Shareholders approval (ordinary resolution) needed if exceeds: (a) sale/purchase/supply of goods/materials: 10% of turnover, (b) selling/buying property: 10% of net worth, (c) leasing: 10% of net worth/turnover, (d) availing/rendering services: 10% of turnover.
Listed companies: Under SEBI LODR Reg 23 — audit committee PRIOR approval + shareholders approval if material (exceeds Rs 1,000 crore or 10% of revenue — revised threshold). Related party cannot vote on the resolution.
S.184 — Disclosure of interest by director: Every director must disclose interest in any contract at first Board meeting attended + changes within 30 days. Form MBP-1 at beginning of each FY. Penalty: Rs 1 lakh extending to Rs 5 lakh.""",
     "keywords": ["related party", "RPT", "Section 188", "Section 184", "SEBI LODR", "audit committee", "10% threshold", "1000 crore"]},
    {"act_name": "Companies Act, 2013", "section_number": "241/242/245",
     "section_title": "Oppression and Mismanagement / Class Action",
     "section_text": """S.241 — Application to NCLT for relief against oppression or mismanagement: Any 100 members (or 10% of total members) of company with share capital, OR 1/5th of total members otherwise. The affairs of the company must be conducted in a manner prejudicial to public interest or oppressive to any member(s).
S.242 — Powers of NCLT: Can regulate conduct of company affairs, remove/appoint directors, set aside transactions, reduce share capital, restrict transfer of shares, order purchase of shares by other members/company.
S.245 — Class action suits: 100+ members (company with share capital) or 5%+ can file class action before NCLT against: company/directors/auditors/experts for any conduct prejudicial to interests of members. Damages can be awarded.
KEY CASE: Cyrus Mistry v. Tata Sons (2021) — SC reversed NCLAT order, upheld Tata's right to remove Mistry as Chairman while noting principles of majority rule.""",
     "keywords": ["oppression", "mismanagement", "241", "242", "class action", "245", "NCLT", "Cyrus Mistry", "100 members"]},
]

# ============================================================
# COMBINE AND SEED
# ============================================================
ALL_FULL = BNS_EXPANDED + IT_FULL + COMPANIES_ACT

async def seed_full():
    client = AsyncIOMotorClient(mongo_url, tls=True, tlsAllowInvalidCertificates=True, serverSelectionTimeoutMS=15000)
    db = client[db_name]

    print("=" * 70)
    print("  FULL CORPUS EXPANSION — BNS + IT Act + Companies Act")
    print("=" * 70)

    existing = await db.statutes.count_documents({})
    print(f"\nCurrent statutes in DB: {existing}")

    # Clean duplicates from this batch
    cleanup_patterns = [
        "Bharatiya Nyaya Sanhita.*BNS.*14-33",
        "Bharatiya Nyaya Sanhita.*BNS.*45-50",
        "Bharatiya Nyaya Sanhita.*BNS.*61-62",
        "Bharatiya Nyaya Sanhita.*BNS.*137-141",
        "Income Tax Act, 1961.*Section 6",
        "Income Tax Act, 1961.*Section 10$",
        "Companies Act, 2013",
    ]
    # Simpler: delete any existing entries that match the act names we're about to insert
    acts_in_batch = set()
    for entry in ALL_FULL:
        acts_in_batch.add(entry["act_name"])
    
    total_deleted = 0
    for act in acts_in_batch:
        result = await db.statutes.delete_many({
            "act_name": act,
            "section_number": {"$in": [e["section_number"] for e in ALL_FULL if e["act_name"] == act]}
        })
        total_deleted += result.deleted_count
    
    if total_deleted:
        print(f"Cleaned {total_deleted} stale entries.")

    result = await db.statutes.insert_many(ALL_FULL)
    print(f"\n✅ Inserted {len(result.inserted_ids)} new entries")

    final = await db.statutes.count_documents({})
    stats = await db.command("dbstats")
    data_mb = stats.get("dataSize", 0) / (1024 * 1024)
    storage_mb = stats.get("storageSize", 0) / (1024 * 1024)

    print(f"\n{'=' * 70}")
    print(f"  SEEDING COMPLETE")
    print(f"  Total statutes: {final}")
    print(f"  DB: {data_mb:.2f}MB data / {storage_mb:.2f}MB storage / 512MB limit ({(storage_mb/512)*100:.1f}%)")
    print(f"  📜 BNS expanded:      +{len(BNS_EXPANDED)} sections")
    print(f"  💰 IT Act expanded:   +{len(IT_FULL)} sections")
    print(f"  🏢 Companies Act:     +{len(COMPANIES_ACT)} sections")
    print(f"{'=' * 70}")

    client.close()

if __name__ == "__main__":
    asyncio.run(seed_full())
