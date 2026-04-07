import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).parent / '.env')

mongo_url = os.environ.get('MONGO_URL', "mongodb://localhost:27017")
db_name = os.environ.get('DB_NAME', "associate_db")

INCOME_TAX_STATUTES = [
    {"act_name": "Income Tax Act, 1961", "section_number": "2(1)", "section_title": "Advance tax definition", "section_text": "'Advance tax' means the advance tax payable in accordance with the provisions of Chapter XVII-C.", "keywords": ["definition", "advance tax", "assessee", "income"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "2(1A)", "section_title": "Agricultural income definition", "section_text": "'Agricultural income' means (a) any rent or revenue derived from land which is situated in India and is used for agricultural purposes.", "keywords": ["agricultural income", "rent", "agriculture"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "2(7)", "section_title": "Assessee definition", "section_text": "'Assessee' means a person by whom any tax or any other sum of money is payable under this Act.", "keywords": ["assessee", "taxpayer"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "4", "section_title": "Charge of income-tax", "section_text": "Income-tax shall be charged for any assessment year at any rate or rates in respect of the total income of the previous year.", "keywords": ["charge", "income tax", "assessment year", "total income"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "5", "section_title": "Scope of total income", "section_text": "Total income of any previous year of a resident includes all income from whatever source derived which is received or deemed to be received in India, or accrues or arises or is deemed to accrue or arise to him in India or outside India.", "keywords": ["scope", "total income", "resident", "india", "accrues"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "9", "section_title": "Income deemed to accrue or arise in India", "section_text": "The following incomes shall be deemed to accrue or arise in India: (i) all income accruing or arising through any business connection in India, property in India, or transfer of a capital asset situate in India.", "keywords": ["deemed income", "business connection", "capital asset", "india"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "10(1)", "section_title": "Agricultural income exemption", "section_text": "In computing the total income of a previous year, agricultural income shall not be included.", "keywords": ["exemption", "agricultural income"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "15", "section_title": "Salaries", "section_text": "The following income shall be chargeable to income-tax under the head 'Salaries': any salary due from an employer, paid or allowed in previous year, or arrears.", "keywords": ["salaries", "due", "employer", "arrears"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "22", "section_title": "Income from house property", "section_text": "The annual value of property consisting of any buildings or lands appurtenant thereto of which the assessee is the owner shall be chargeable to income-tax under the head 'Income from house property'.", "keywords": ["house property", "annual value", "building", "rent"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "28", "section_title": "Profits and gains of business or profession", "section_text": "The profits and gains of any business or profession which was carried on by the assessee at any time during the previous year shall be chargeable to income-tax under the head 'Profits and gains of business or profession'.", "keywords": ["business income", "profession", "profits", "gains"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "32", "section_title": "Depreciation", "section_text": "In respect of depreciation of buildings, machinery, plant or furniture, being tangible assets; and intangibles like know-how, patents, copyrights, owned wholly or partly by the assessee and used for business.", "keywords": ["depreciation", "tangible assets", "intangible assets", "wdv"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "37", "section_title": "General deduction", "section_text": "Any expenditure (not being capital expenditure or personal expenses) laid out wholly and exclusively for the purposes of the business or profession shall be allowed in computing the income chargeable under the head 'Profits and gains of business or profession'.", "keywords": ["general deduction", "business expenditure", "wholly exclusively"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "43B", "section_title": "Certain deductions only on actual payment", "section_text": "Notwithstanding anything contained in any other provision, a deduction otherwise allowable in respect of tax, duty, cess, employer provident fund contribution, etc. shall be allowed only in computing the income of that previous year in which such sum is actually paid.", "keywords": ["actual payment", "tax", "provident fund"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "44AB", "section_title": "Audit of accounts of certain persons carrying on business or profession", "section_text": "Every person carrying on business shall get his accounts audited if his total sales, turnover or gross receipts in business exceed one crore rupees in any previous year.", "keywords": ["tax audit", "44AB", "one crore", "accountant"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "44AD", "section_title": "Presumptive income - eligible business", "section_text": "In case of an eligible assessee engaged in an eligible business having turnover not exceeding two crore rupees, a sum equal to 8% (or 6% for digital receipts) of turnover shall be deemed to be profits and gains.", "keywords": ["presumptive income", "44AD", "eight percent", "turnover"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "45", "section_title": "Capital gains", "section_text": "Any profits or gains arising from the transfer of a capital asset effected in the previous year shall be chargeable to income-tax under the head 'Capital gains'.", "keywords": ["capital gains", "transfer", "capital asset", "previous year"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "50C", "section_title": "Special provision for full value of consideration in certain cases", "section_text": "Where the consideration received as a result of the transfer of land or building is less than the stamp duty value, the stamp duty value shall be deemed to be the full value of consideration.", "keywords": ["50C", "stamp duty value", "SDV", "full value consideration"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "54", "section_title": "Exemption on sale of residential house", "section_text": "If capital gain arises from transfer of a long-term residential house, and assessee purchases or constructs another residential house in India within specified time, capital gain is exempt.", "keywords": ["section 54", "residential house", "exemption", "long term"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "56(2)(x)", "section_title": "Income from other sources - gifts and inadequate consideration", "section_text": "Where any person receives sum of money or property without consideration or inadequate consideration exceeding Rs. 50,000, it is taxable under Income from other sources.", "keywords": ["gift", "inadequate consideration", "stamp duty value"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "68", "section_title": "Cash credits", "section_text": "Where any sum is found credited in the books of an assessee and he offers no explanation about the nature and source thereof, it may be charged to income-tax as the income of the assessee.", "keywords": ["cash credit", "unexplained", "books of account", "nature source"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "80C", "section_title": "Deduction in respect of LIC, PPF, etc.", "section_text": "In computing total income, deduction allowed for amount paid for LIC, PPF, tuition fees, etc. up to Rs. 1.5 lakh.", "keywords": ["80C", "deduction", "LIC", "PPF", "1.5 lakh"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "139(1)", "section_title": "Return of income", "section_text": "Every person being a company or firm, or others if total income exceeds non-taxable limit, shall furnish a return of his income on or before the due date.", "keywords": ["return of income", "filing", "due date", "139(1)"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "143(1)", "section_title": "Intimation after processing", "section_text": "Return shall be processed computing total income or loss after making adjustments for arithmetical errors or incorrect claims.", "keywords": ["143(1)", "intimation", "processing", "arithmetical error"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "143(2)", "section_title": "Notice for scrutiny assessment", "section_text": "Where return furnished, Assessing Officer may serve notice if he considers it necessary to ensure assessee has not understated income or under-paid tax.", "keywords": ["143(2)", "scrutiny", "assessment", "notice"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "147", "section_title": "Income escaping assessment", "section_text": "If any income chargeable to tax has escaped assessment for any year, Assessing Officer may assess or reassess such income.", "keywords": ["147", "escaped assessment", "reassessment"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "148A", "section_title": "Inquiry before notice under 148", "section_text": "Assessing Officer shall conduct enquiry, provide opportunity of being heard by issuing show cause notice before issuing reassessment notice under section 148.", "keywords": ["148A", "show cause notice", "reopening"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "263", "section_title": "Revision of orders prejudicial to revenue", "section_text": "Principal Commissioner or Commissioner may call for and examine record if order by Assessing Officer is erroneous and prejudicial to interests of revenue.", "keywords": ["263", "revision", "prejudicial to revenue", "erroneous order"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "270A", "section_title": "Penalty for under-reporting and misreporting of income", "section_text": "Penalty of 50% for under-reporting, and 200% for misreporting of income.", "keywords": ["270A", "penalty", "under-reporting", "misreporting"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "276C", "section_title": "Wilful attempt to evade tax", "section_text": "If a person wilfully attempts to evade tax, penalty or interest, he shall be punishable with rigorous imprisonment.", "keywords": ["276C", "prosecution", "evasion", "wilful attempt", "imprisonment"]}
]

async def seed():
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    await db.statutes.insert_many(INCOME_TAX_STATUTES)
    
    # Indexes
    await db.statutes.create_index([("act_name", 1), ("section_number", 1)])
    await db.statutes.create_index([("keywords", 1)])
    await db.statutes.create_index([
        ("section_text", "text"),
        ("section_title", "text"),
        ("act_name", "text")
    ])
    print(f"Seeded {len(INCOME_TAX_STATUTES)} sections from IT Act 1961")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed())
