"""
Statute Database Seeder for Associate
Seeds MongoDB with comprehensive Indian legal statute data.
Run: python statute_seeder.py
"""
import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).parent / '.env')

mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

STATUTES = [
    # ============ INCOME TAX ACT 1961 ============
    {"act_name": "Income Tax Act, 1961", "section_number": "2", "section_title": "Definitions", 
     "section_text": "In this Act, unless the context otherwise requires — (1) 'advance tax' means the advance tax payable in accordance with the provisions of Chapter XVII-C; (1A) 'agricultural income' means — (a) any rent or revenue derived from land which is situated in India and is used for agricultural purposes; (b) any income derived from such land by agriculture; (c) any income derived from any building owned and occupied by the receiver of the rent or revenue of any such land.",
     "keywords": ["definition", "advance tax", "agricultural income", "assessee", "income"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "4", "section_title": "Charge of income-tax",
     "section_text": "(1) Where any Central Act enacts that income-tax shall be charged for any assessment year at any rate or rates, income-tax at that rate or those rates shall be charged for that year in accordance with, and subject to the provisions of, this Act in respect of the total income of the previous year of every person. (2) In respect of income chargeable under sub-section (1), income-tax shall be deducted at the source or paid in advance, where it is so deductible or payable under any provision of this Act.",
     "keywords": ["charge", "income tax", "assessment year", "total income", "previous year"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "5", "section_title": "Scope of total income",
     "section_text": "(1) Subject to the provisions of this Act, the total income of any previous year of a person who is a resident includes all income from whatever source derived which — (a) is received or is deemed to be received in India in such year by or on behalf of such person; or (b) accrues or arises or is deemed to accrue or arise to him in India during such year; or (c) accrues or arises to him outside India during such year.",
     "keywords": ["scope", "total income", "resident", "india", "accrues", "arises"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "9", "section_title": "Income deemed to accrue or arise in India",
     "section_text": "(1) The following incomes shall be deemed to accrue or arise in India: (i) all income accruing or arising, whether directly or indirectly, through or from any business connection in India, or through or from any property in India, or through or from any asset or source of income in India, or through the transfer of a capital asset situate in India.",
     "keywords": ["deemed income", "business connection", "capital asset", "india", "transfer"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "10", "section_title": "Incomes not included in total income",
     "section_text": "In computing the total income of a previous year of any person, any income falling within any of the following clauses shall not be included — (1) agricultural income; (2) any sum received by a member of a Hindu undivided family; (10) gratuity; (10A) commuted pension; (10B) statutory provident fund; (10C) compensation on voluntary retirement; (10D) maturity proceeds of LIC; (13A) house rent allowance; (14) dividends from Indian companies (subject to Section 115BBDA).",
     "keywords": ["exemption", "agricultural income", "gratuity", "pension", "provident fund", "hra", "dividends"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "22", "section_title": "Income from house property",
     "section_text": "The annual value of property consisting of any buildings or lands appurtenant thereto of which the assessee is the owner, other than such portions of such property as he may occupy for the purposes of any business or profession carried on by him the profits of which are chargeable to income-tax, shall be chargeable to income-tax under the head 'Income from house property'.",
     "keywords": ["house property", "annual value", "building", "rent", "owner"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "24", "section_title": "Deductions from income from house property",
     "section_text": "Income chargeable under the head 'Income from house property' shall be computed after making the following deductions, namely: (a) a sum equal to thirty per cent of the annual value; (b) where the property has been acquired, constructed, repaired, renewed or reconstructed with borrowed capital, the amount of any interest payable on such capital: Provided that the aggregate amount of deduction under this clause shall not exceed two lakh rupees in certain cases.",
     "keywords": ["deduction", "house property", "standard deduction", "interest", "borrowed capital", "30 percent"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "28", "section_title": "Profits and gains of business or profession",
     "section_text": "The following income shall be chargeable to income-tax under the head 'Profits and gains of business or profession': (i) the profits and gains of any business or profession which was carried on by the assessee at any time during the previous year; (ii) any compensation or other payment due to or received by any person, by whatever name called.",
     "keywords": ["business income", "profession", "profits", "gains", "compensation"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "32", "section_title": "Depreciation",
     "section_text": "(1) In respect of depreciation of — (i) buildings, machinery, plant or furniture, being tangible assets; (ii) know-how, patents, copyrights, trade marks, licences, franchises or any other business or commercial rights of similar nature, being intangible assets acquired on or after the 1st day of April, 1998, owned, wholly or partly, by the assessee and used for the purposes of the business or profession, the following deductions shall be allowed.",
     "keywords": ["depreciation", "tangible assets", "intangible assets", "building", "machinery", "plant", "wdv"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "37", "section_title": "General deduction",
     "section_text": "(1) Any expenditure (not being expenditure of the nature described in sections 30 to 36 and not being in the nature of capital expenditure or personal expenses of the assessee), laid out or expended wholly and exclusively for the purposes of the business or profession shall be allowed in computing the income chargeable under the head 'Profits and gains of business or profession'. Explanation 1: For the removal of doubts, it is hereby declared that any expenditure incurred by an assessee for any purpose which is an offence or which is prohibited by law shall not be deemed to have been incurred for the purpose of business or profession.",
     "keywords": ["general deduction", "business expenditure", "wholly exclusively", "capital expenditure", "personal expense"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "40A(3)", "section_title": "Cash payment exceeding prescribed limit",
     "section_text": "Where the assessee incurs any expenditure in respect of which a payment or aggregate of payments made to a person in a day, otherwise than by an account payee cheque drawn on a bank or account payee bank draft or use of electronic clearing system through a bank account, exceeds ten thousand rupees, no deduction shall be allowed in respect of such expenditure.",
     "keywords": ["cash payment", "ten thousand", "account payee cheque", "disallowance"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "43B", "section_title": "Certain deductions only on actual payment",
     "section_text": "Notwithstanding anything contained in any other provision of this Act, a deduction otherwise allowable under this Act in respect of — (a) any sum payable by the assessee by way of tax, duty, cess or fee; (b) any sum payable by the assessee as an employer by way of contribution to any provident fund or superannuation fund or any other fund for the welfare of employees — shall be allowed only in computing the income of that previous year in which such sum is actually paid.",
     "keywords": ["actual payment", "tax", "duty", "cess", "provident fund", "employer contribution"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "44AD", "section_title": "Presumptive income — eligible business",
     "section_text": "(1) Notwithstanding anything to the contrary contained in sections 28 to 43C, in the case of an eligible assessee engaged in an eligible business having total turnover or gross receipts not exceeding two crore rupees in the previous year, a sum equal to eight per cent of the total turnover or gross receipts of the assessee in the previous year on account of such business or, as the case may be, a sum higher than the aforesaid sum claimed to have been earned by the eligible assessee, shall be deemed to be the profits and gains of such business chargeable to tax under the head 'Profits and gains of business or profession'.",
     "keywords": ["presumptive income", "44AD", "eight percent", "two crore", "turnover", "eligible business"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "45", "section_title": "Capital gains",
     "section_text": "(1) Any profits or gains arising from the transfer of a capital asset effected in the previous year shall, save as otherwise provided in sections 54, 54B, 54D, 54EC, 54F, 54G, 54GA, 54GB, and 54H, be chargeable to income-tax under the head 'Capital gains', and shall be deemed to be the income of the previous year in which the transfer took place.",
     "keywords": ["capital gains", "transfer", "capital asset", "previous year", "54"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "54", "section_title": "Exemption on sale of residential house",
     "section_text": "(1) Subject to the provisions of sub-section (2), where, in the case of an assessee being an individual or a Hindu undivided family, the capital gain arises from the transfer of a long-term capital asset, being a residential house, the income of which is chargeable under the head 'Income from house property', and the assessee has, within a period of one year before or two years after the date on which the transfer took place purchased, or has within a period of three years after that date constructed, one residential house in India, then the capital gain shall be dealt with in accordance with the following provisions.",
     "keywords": ["section 54", "residential house", "exemption", "capital gain", "long term", "purchase", "construction"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "68", "section_title": "Cash credits",
     "section_text": "Where any sum is found credited in the books of an assessee maintained for any previous year, and the assessee offers no explanation about the nature and source thereof or the explanation offered by him is not, in the opinion of the Assessing Officer, satisfactory, the sum so credited may be charged to income-tax as the income of the assessee of that previous year.",
     "keywords": ["cash credit", "unexplained", "books of account", "nature source", "assessing officer"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "80C", "section_title": "Deduction in respect of LIC, PPF, etc.",
     "section_text": "(1) In computing the total income of an assessee, being an individual or a Hindu undivided family, there shall be deducted, in accordance with and subject to the provisions of this section, the whole of the amount paid or deposited in the previous year, being the aggregate of the sums referred to in sub-section (2), as does not exceed one lakh and fifty thousand rupees.",
     "keywords": ["80C", "deduction", "LIC", "PPF", "ELSS", "tuition fee", "home loan principal", "1.5 lakh"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "80D", "section_title": "Deduction for medical insurance",
     "section_text": "In computing the total income of an assessee, being an individual or a Hindu undivided family, there shall be deducted such sum as is specified under sub-section (2) or sub-section (3), as the case may be, paid by the assessee in the previous year to effect or keep in force an insurance on the health of the assessee or the family.",
     "keywords": ["80D", "medical insurance", "health insurance", "deduction", "25000", "50000", "senior citizen"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "115BAC", "section_title": "New Tax Regime",
     "section_text": "The income-tax payable in respect of the total income of a person, being an individual or a Hindu undivided family or association of persons (other than a co-operative society), for any previous year relevant to the assessment year beginning on or after the 1st day of April, 2024, shall, at the option of such person, be computed at the rate of tax given in the following table. New regime is default from AY 2024-25.",
     "keywords": ["new tax regime", "115BAC", "default", "2024", "slab", "individual"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "139", "section_title": "Return of income",
     "section_text": "(1) Every person — (a) being a company or a firm; or (b) being a person other than a company or a firm, if his total income or the total income of any other person in respect of which he is assessable under this Act during the previous year exceeded the maximum amount which is not chargeable to income-tax, shall, on or before the due date, furnish a return of his income.",
     "keywords": ["return of income", "filing", "due date", "139", "ITR", "company", "firm"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "143(1)", "section_title": "Intimation after processing",
     "section_text": "(1) Where a return has been made under section 139, or in response to a notice under sub-section (1) of section 142, (a) the return shall be processed in the following manner, namely: (i) the total income or loss shall be computed after making the following adjustments: (I) any arithmetical error in the return; (II) an incorrect claim, if such incorrect claim is apparent from any information in the return.",
     "keywords": ["143(1)", "intimation", "processing", "arithmetical error", "incorrect claim", "adjustment"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "143(2)", "section_title": "Notice for scrutiny assessment",
     "section_text": "Where a return has been furnished under section 139, or in response to a notice under section 142(1), the Assessing Officer or the prescribed income-tax authority, as the case may be, if, considers it necessary or expedient to ensure that the assessee has not understated the income or has not computed excessive loss or has not under-paid the tax in any manner, shall serve on the assessee a notice requiring him, on a date to be specified therein, to attend the office of the Assessing Officer.",
     "keywords": ["143(2)", "scrutiny", "assessment", "notice", "assessing officer", "understatement"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "148", "section_title": "Notice for reassessment (Escaped Assessment)",
     "section_text": "Before making the assessment, reassessment or recomputation under section 147, and subject to the provisions of section 148A, the Assessing Officer shall serve on the assessee a notice, along with a copy of the order passed under section 148A(d), requiring him to furnish within such period, as may be specified in such notice, a return of his income or the income of any other person in respect of which he is assessable under this Act.",
     "keywords": ["148", "reassessment", "escaped assessment", "notice", "148A", "reopening"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "194C", "section_title": "TDS on contractor payments",
     "section_text": "Any person responsible for paying any sum to any resident for carrying out any work (including supply of labour for carrying out any work) in pursuance of a contract between the contractor and a specified person shall, at the time of credit of such sum to the account of the contractor or at the time of payment thereof in cash or by issue of a cheque or draft or by any other mode, whichever is earlier, deduct an amount equal to — (i) one per cent where the payment is being made or credit is being given to an individual or a Hindu undivided family; (ii) two per cent where the payment is being made or credit is being given to any other person.",
     "keywords": ["194C", "TDS", "contractor", "work", "one percent", "two percent"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "234A", "section_title": "Interest for default in furnishing return",
     "section_text": "Where the return of income for any assessment year under section 139(1) or section 139(4), is furnished after the due date, the assessee shall be liable to pay simple interest at the rate of one per cent for every month or part of a month on the amount of the tax as determined on regular assessment.",
     "keywords": ["234A", "interest", "delay", "return filing", "one percent per month"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "234B", "section_title": "Interest for default in payment of advance tax",
     "section_text": "Where, in any financial year, an assessee who is liable to pay advance tax under section 208 has failed to pay such tax or, the advance tax paid by such assessee is less than ninety per cent of the assessed tax, the assessee shall be liable to pay simple interest at the rate of one per cent for every month or part of a month.",
     "keywords": ["234B", "advance tax", "interest", "default", "ninety percent"]},
    {"act_name": "Income Tax Act, 1961", "section_number": "271(1)(c)", "section_title": "Penalty for concealment of income",
     "section_text": "If the Assessing Officer or the Commissioner (Appeals) in the course of any proceedings under this Act, is satisfied that any person — has concealed the particulars of his income or furnished inaccurate particulars of such income, he may direct that such person shall pay by way of penalty a sum which shall not be less than, but which shall not exceed three times, the amount of tax sought to be evaded.",
     "keywords": ["271(1)(c)", "penalty", "concealment", "inaccurate particulars", "three times"]},
    # ============ GST / CGST ACT 2017 ============
    {"act_name": "Central Goods and Services Tax Act, 2017 (CGST)", "section_number": "2", "section_title": "Definitions",
     "section_text": "In this Act, unless the context otherwise requires: (6) 'aggregate turnover' means the aggregate value of all taxable supplies, exempt supplies, exports of goods or services and inter-State supplies of persons having the same PAN; (17) 'business' includes any trade, commerce, manufacture, profession, vocation, adventure, wager; (52) 'goods' means every kind of movable property; (102) 'services' means anything other than goods.",
     "keywords": ["cgst", "definition", "aggregate turnover", "goods", "services", "business", "supply"]},
    {"act_name": "CGST Act, 2017", "section_number": "7", "section_title": "Scope of supply",
     "section_text": "(1) For the purposes of this Act, the expression 'supply' includes — (a) all forms of supply of goods or services or both such as sale, transfer, barter, exchange, licence, rental, lease or disposal made or agreed to be made for a consideration by a person in the course or furtherance of business.",
     "keywords": ["supply", "scope", "sale", "transfer", "barter", "consideration", "business"]},
    {"act_name": "CGST Act, 2017", "section_number": "9", "section_title": "Levy and collection of tax",
     "section_text": "(1) Subject to the provisions of sub-section (2), there shall be levied a tax called the central goods and services tax on all intra-State supplies of goods or services or both, except on the supply of alcoholic liquor for human consumption, on the value determined under section 15 and at such rates, not exceeding twenty per cent.",
     "keywords": ["levy", "cgst", "intra-state", "twenty percent", "rate", "value"]},
    {"act_name": "CGST Act, 2017", "section_number": "16", "section_title": "Eligibility and conditions for Input Tax Credit",
     "section_text": "(1) Every registered person shall, subject to such conditions and restrictions as may be prescribed, be entitled to take credit of input tax charged on any supply of goods or services or both to him which are used or intended to be used in the course or furtherance of his business. (2) Notwithstanding anything contained in this section, no registered person shall be entitled to the credit of any input tax in respect of any supply of goods or services or both to him unless — (a) he is in possession of a tax invoice; (b) he has received the goods or services; (c) the tax charged has been actually paid to the Government; (d) he has furnished the return under section 39.",
     "keywords": ["ITC", "input tax credit", "section 16", "conditions", "tax invoice", "return", "eligibility"]},
    {"act_name": "CGST Act, 2017", "section_number": "17(5)", "section_title": "Blocked credits",
     "section_text": "Notwithstanding anything contained in sub-section (1) of section 16 and sub-section (1) of section 18, input tax credit shall not be available in respect of the following: (a) motor vehicles and other conveyances except when they are used for making further supply or transportation of passengers or goods or imparting training; (b) food and beverages, outdoor catering, beauty treatment, health services, cosmetic and plastic surgery (except where used by same line of business); (d) goods or services used for construction of immovable property on his own account.",
     "keywords": ["blocked credit", "17(5)", "motor vehicle", "food", "construction", "immovable property"]},
    {"act_name": "CGST Act, 2017", "section_number": "73", "section_title": "Determination of tax not paid — Non-fraud cases",
     "section_text": "(1) Where it appears to the proper officer that any tax has not been paid or short paid or erroneously refunded, or where input tax credit has been wrongly availed or utilised for any reason, other than the reason of fraud or any wilful-misstatement or suppression of facts to evade tax, he shall serve notice on the person chargeable with tax which has not been so paid or which has been so short paid or to whom the refund has erroneously been made, requiring him to show cause. Time limit: within two years and nine months from the due date of filing annual return.",
     "keywords": ["73", "show cause notice", "SCN", "non-fraud", "tax not paid", "short paid", "ITC wrongly availed"]},
    {"act_name": "CGST Act, 2017", "section_number": "74", "section_title": "Determination of tax — Fraud cases",
     "section_text": "(1) Where it appears to the proper officer that any tax has not been paid or short paid or erroneously refunded or where input tax credit has been wrongly availed or utilised by reason of fraud, or any wilful-misstatement or suppression of facts to evade tax, he shall serve notice on the person chargeable with tax which has not been so paid. Time limit: within four years and six months from the due date of filing annual return. Penalty: equal to the tax amount determined.",
     "keywords": ["74", "fraud", "wilful misstatement", "suppression", "show cause", "penalty equal to tax"]},
    # ============ COMPANIES ACT 2013 ============
    {"act_name": "Companies Act, 2013", "section_number": "2(20)", "section_title": "Definition of Company",
     "section_text": "'company' means a company incorporated under this Act or under any previous company law.",
     "keywords": ["company", "definition", "incorporation"]},
    {"act_name": "Companies Act, 2013", "section_number": "149", "section_title": "Company to have Board of Directors",
     "section_text": "(1) Every company shall have a Board of Directors consisting of individuals as directors. (2) Every company shall have a minimum number of three directors in the case of a public company, two directors in the case of a private company, and one director in the case of a One Person Company.",
     "keywords": ["board of directors", "minimum directors", "public company", "private company", "OPC"]},
    {"act_name": "Companies Act, 2013", "section_number": "164", "section_title": "Disqualifications for appointment of director",
     "section_text": "(2) No person who is or has been a director of a company which — (a) has not filed financial statements or annual returns for any continuous period of three financial years; shall be eligible to be re-appointed as a director of that company or appointed in other company for a period of five years.",
     "keywords": ["disqualification", "director", "164", "non-filing", "five years"]},
    {"act_name": "Companies Act, 2013", "section_number": "447", "section_title": "Punishment for fraud",
     "section_text": "Without prejudice to any liability including repayment of any debt under this Act or any other law for the time being in force, any person who is found to be guilty of fraud, shall be punishable with imprisonment for a term which shall not be less than six months but which may extend to ten years and shall also be liable to fine which shall not be less than the amount involved in the fraud, but which may extend to three times the amount involved in the fraud.",
     "keywords": ["fraud", "447", "punishment", "imprisonment", "six months", "ten years", "fine"]},
    # ============ NI ACT 1881 ============
    {"act_name": "Negotiable Instruments Act, 1881", "section_number": "138", "section_title": "Dishonour of cheque for insufficiency of funds",
     "section_text": "Where any cheque drawn by a person on an account maintained by him with a banker for payment of any amount of money to another person from out of that account for the discharge, in whole or in part, of any debt or other liability, is returned by the bank unpaid, either because of the amount of money standing to the credit of that account is insufficient to honour the cheque or that it exceeds the amount arranged to be paid from that account by an agreement made with that bank, such person shall be deemed to have committed an offence and shall be punishable with imprisonment for a term which may extend to two years, or with fine which may extend to twice the amount of the cheque, or with both.",
     "keywords": ["138", "cheque bounce", "dishonour", "insufficient funds", "two years imprisonment", "twice amount"]},
    {"act_name": "Negotiable Instruments Act, 1881", "section_number": "141", "section_title": "Offences by companies",
     "section_text": "(1) If the person committing an offence under section 138 is a company, every person who, at the time the offence was committed, was in charge of, and was responsible to, the company for the conduct of the business of the company, as well as the company, shall be deemed to be guilty of the offence.",
     "keywords": ["141", "company", "director liability", "person in charge", "offence"]},
    # ============ IPC / BNS ============
    {"act_name": "Indian Penal Code, 1860 / Bharatiya Nyaya Sanhita, 2023", "section_number": "IPC 420 / BNS 318", "section_title": "Cheating and dishonestly inducing delivery of property",
     "section_text": "Whoever cheats and thereby dishonestly induces the person deceived to deliver any property to any person, or to make, alter or destroy the whole or any part of a valuable security, or anything which is signed or sealed, and which is capable of being converted into a valuable security, shall be punished with imprisonment of either description for a term which may extend to seven years, and shall also be liable to fine.",
     "keywords": ["cheating", "420", "318 BNS", "dishonestly", "property", "seven years"]},
    {"act_name": "Indian Penal Code, 1860 / Bharatiya Nyaya Sanhita, 2023", "section_number": "IPC 406 / BNS 316", "section_title": "Criminal breach of trust",
     "section_text": "Whoever, being in any manner entrusted with property, or with any dominion over property, dishonestly misappropriates or converts to his own use that property, or dishonestly uses or disposes of that property in violation of any direction of law, shall be punished with imprisonment of either description for a term which may extend to three years, or with fine, or with both.",
     "keywords": ["criminal breach of trust", "406", "316 BNS", "misappropriation", "three years"]},
    # ============ CrPC / BNSS ============
    {"act_name": "Code of Criminal Procedure, 1973 / BNSS, 2023", "section_number": "CrPC 437 / BNSS 480", "section_title": "Bail in non-bailable offences",
     "section_text": "When any person accused of, or suspected of, the commission of any non-bailable offence is arrested or detained without warrant by an officer in charge of a police station or appears or is brought before a Court other than the High Court or Court of Session, he may be released on bail.",
     "keywords": ["bail", "non-bailable", "437", "480 BNSS", "police station", "court"]},
    {"act_name": "Code of Criminal Procedure, 1973 / BNSS, 2023", "section_number": "CrPC 482 / BNSS 528", "section_title": "Inherent powers of High Court",
     "section_text": "Nothing in this Code shall be deemed to limit or affect the inherent powers of the High Court to make such orders as may be necessary to give effect to any order under this Code, or to prevent abuse of the process of any Court or otherwise to secure the ends of justice.",
     "keywords": ["482", "528 BNSS", "inherent powers", "high court", "quashing", "abuse of process"]},
    # ============ CPC 1908 ============
    {"act_name": "Code of Civil Procedure, 1908", "section_number": "9", "section_title": "Courts to try all civil suits unless barred",
     "section_text": "The Courts shall (subject to the provisions herein contained) have jurisdiction to try all suits of a civil nature excepting suits of which their cognizance is either expressly or impliedly barred.",
     "keywords": ["jurisdiction", "civil suit", "cognizance", "barred"]},
    {"act_name": "Code of Civil Procedure, 1908", "section_number": "Order 39", "section_title": "Temporary injunctions and interlocutory orders",
     "section_text": "Rule 1: Where in any suit it is proved by affidavit or otherwise — (a) that any property in dispute in a suit is in danger of being wasted, damaged, or alienated by any party to the suit, or wrongfully sold in execution of a decree, or (b) that the defendant threatens, or intends, to remove or dispose of his property with a view to defrauding his creditors — the Court may by order grant a temporary injunction to restrain such act.",
     "keywords": ["temporary injunction", "Order 39", "interlocutory", "restraint"]},
    # ============ PMLA 2002 ============
    {"act_name": "Prevention of Money Laundering Act, 2002", "section_number": "3", "section_title": "Offence of money-laundering",
     "section_text": "Whosoever directly or indirectly attempts to indulge or knowingly assists or knowingly is a party or is actually involved in any process or activity connected with the proceeds of crime including its concealment, possession, acquisition or use and projecting or claiming it as untainted property shall be guilty of offence of money-laundering.",
     "keywords": ["money laundering", "proceeds of crime", "concealment", "possession", "untainted property"]},
    {"act_name": "Prevention of Money Laundering Act, 2002", "section_number": "4", "section_title": "Punishment for money-laundering",
     "section_text": "Whoever commits the offence of money-laundering shall be punishable with rigorous imprisonment for a term which shall not be less than three years but which may extend to seven years and shall also be liable to fine.",
     "keywords": ["punishment", "rigorous imprisonment", "three years", "seven years", "fine"]},
    {"act_name": "PMLA, 2002", "section_number": "5", "section_title": "Attachment of property involved in money-laundering",
     "section_text": "Where the Director or any other officer not below the rank of Deputy Director authorised by the Director for the purposes of this section, has reason to believe (the reason for such belief to be recorded in writing), on the basis of material in his possession, that any person is in possession of any proceeds of crime, he may provisionally attach such property for a period not exceeding one hundred and eighty days.",
     "keywords": ["attachment", "provisional", "180 days", "proceeds of crime", "director", "ED"]},
    # ============ FEMA 1999 ============
    {"act_name": "Foreign Exchange Management Act, 1999", "section_number": "3", "section_title": "Dealing in foreign exchange",
     "section_text": "Save as otherwise provided in this Act, rules or regulations made thereunder, or with the general or special permission of the Reserve Bank, no person shall — (a) deal in or transfer any foreign exchange or foreign security to any person not being an authorised person; (b) make any payment to or for the credit of any person resident outside India in any manner.",
     "keywords": ["foreign exchange", "FEMA", "RBI permission", "authorised person", "resident outside india"]},
    {"act_name": "FEMA, 1999", "section_number": "13", "section_title": "Penalties",
     "section_text": "(1) If any person contravenes any provision of this Act, or contravenes any rule, regulation, notification, direction or order issued in exercise of the powers under this Act, he shall, upon adjudication, be liable to a penalty up to thrice the sum involved in such contravention where such amount is quantifiable, or up to two lakh rupees where the amount is not directly quantifiable.",
     "keywords": ["penalty", "FEMA", "contravention", "thrice", "two lakh"]},
    # ============ CONSUMER PROTECTION ACT 2019 ============
    {"act_name": "Consumer Protection Act, 2019", "section_number": "2(7)", "section_title": "Definition of Consumer",
     "section_text": "'consumer' means any person who — (i) buys any goods for a consideration; (ii) hires or avails of any service for a consideration. It does not include a person who obtains goods for resale or for any commercial purpose.",
     "keywords": ["consumer", "definition", "goods", "service", "consideration", "resale"]},
    {"act_name": "Consumer Protection Act, 2019", "section_number": "34", "section_title": "Jurisdiction of District Commission",
     "section_text": "Subject to the other provisions of this Act, the District Commission shall have jurisdiction to entertain complaints where the value of the goods or services paid as consideration, does not exceed one crore rupees.",
     "keywords": ["district commission", "jurisdiction", "one crore", "complaint"]},
    # ============ RERA 2016 ============
    {"act_name": "Real Estate (Regulation and Development) Act, 2016", "section_number": "18", "section_title": "Return of amount and compensation",
     "section_text": "(1) If the promoter fails to complete or is unable to give possession of an apartment, plot or building — (a) in accordance with the terms of the agreement for sale or, as the case may be, duly completed by the date specified therein; the promoter shall be liable on demand to the allottees to return the amount received by him with interest at such rate as may be prescribed.",
     "keywords": ["RERA", "delay", "possession", "refund", "interest", "promoter", "allottee"]},
    # ============ IBC 2016 ============
    {"act_name": "Insolvency and Bankruptcy Code, 2016", "section_number": "7", "section_title": "Initiation of CIRP by financial creditor",
     "section_text": "(1) A financial creditor either by itself or jointly with other financial creditors, or any other person on behalf of the financial creditor, as may be notified by the Central Government, may file an application for initiating corporate insolvency resolution process against a corporate debtor before the Adjudicating Authority when a default has occurred.",
     "keywords": ["IBC", "section 7", "financial creditor", "CIRP", "default", "NCLT"]},
    {"act_name": "Insolvency and Bankruptcy Code, 2016", "section_number": "9", "section_title": "Application by operational creditor",
     "section_text": "(1) After the expiry of the period of ten days from the date of delivery of the notice or invoice demanding payment under sub-section (1) of section 8, if the operational creditor does not receive payment from the corporate debtor or does not receive notice of the dispute under sub-section (2) of section 8, the operational creditor may file an application before the Adjudicating Authority for initiating a corporate insolvency resolution process.",
     "keywords": ["IBC", "section 9", "operational creditor", "ten days", "demand notice", "CIRP"]},
    # ============ ARBITRATION ACT 1996 ============
    {"act_name": "Arbitration and Conciliation Act, 1996", "section_number": "34", "section_title": "Application for setting aside arbitral award",
     "section_text": "(1) Recourse to a Court against an arbitral award may be made only by an application for setting aside such award in accordance with sub-section (2) and sub-section (3). (2) An arbitral award may be set aside by the Court only if — (a) the party making the application furnishes proof that: (i) a party was under some incapacity; (ii) the arbitration agreement is not valid; (iii) the party was not given proper notice.",
     "keywords": ["section 34", "setting aside", "arbitral award", "court", "challenge"]},
    {"act_name": "Arbitration and Conciliation Act, 1996", "section_number": "36", "section_title": "Enforcement of arbitral award",
     "section_text": "(1) Where the time for making an application to set aside the arbitral award under section 34 has expired, then, subject to the provisions of sub-section (2), such award shall be enforced in accordance with the provisions of the Code of Civil Procedure, 1908 in the same manner as if it were a decree of the Court.",
     "keywords": ["enforcement", "arbitral award", "decree", "CPC", "section 36"]},
    # ============ SPECIFIC RELIEF ACT 1963 ============
    {"act_name": "Specific Relief Act, 1963", "section_number": "14", "section_title": "Contracts not specifically enforceable",
     "section_text": "The following contracts cannot be specifically enforced: (a) where a party to the contract has obtained substituted performance of contract; (b) a contract which is so dependent on the personal qualifications of the parties that the court cannot enforce specific performance of its material terms; (c) a contract which is in its nature determinable; (d) a contract the performance of which involves the performance of a continuous duty which the court cannot supervise.",
     "keywords": ["specific performance", "not enforceable", "personal qualification", "determinable"]},
    # ============ TRANSFER OF PROPERTY ACT 1882 ============
    {"act_name": "Transfer of Property Act, 1882", "section_number": "54", "section_title": "Sale defined",
     "section_text": "'Sale' is a transfer of ownership in exchange for a price paid or promised or part-paid and part-promised. A contract for the sale of immovable property is a contract that a sale of such property shall take place on terms settled between the parties. It does not, of itself, create any interest in or charge on such property.",
     "keywords": ["sale", "transfer", "ownership", "price", "immovable property", "contract"]},
    {"act_name": "Transfer of Property Act, 1882", "section_number": "58", "section_title": "Mortgage defined",
     "section_text": "A mortgage is the transfer of an interest in specific immoveable property for the purpose of securing the payment of money advanced or to be advanced by way of loan, an existing or future debt, or the performance of an engagement which may give rise to a pecuniary liability.",
     "keywords": ["mortgage", "immovable property", "loan", "security", "debt"]},
    # ============ SEBI ACT ============
    {"act_name": "Securities and Exchange Board of India Act, 1992", "section_number": "11", "section_title": "Functions of SEBI",
     "section_text": "Subject to the provisions of this Act, it shall be the duty of the Board to protect the interests of investors in securities and to promote the development of, and to regulate the securities market, by such measures as it thinks fit.",
     "keywords": ["SEBI", "investor protection", "securities market", "regulate"]},
    {"act_name": "SEBI (Listing Obligations and Disclosure Requirements) Regulations, 2015", "section_number": "Regulation 30", "section_title": "Disclosure of material events",
     "section_text": "Every listed entity shall make disclosures of any events or information which, in the opinion of the board of directors of the listed entity, is material.",
     "keywords": ["LODR", "disclosure", "material events", "listed entity", "regulation 30"]},
    # ============ REGISTRATION ACT 1908 ============
    {"act_name": "Registration Act, 1908", "section_number": "17", "section_title": "Documents of which registration is compulsory",
     "section_text": "(1) The following documents shall be registered if the property to which they relate is situate in a district in which, and if they have been executed on or after the date on which, Act No. XVI of 1864, or this Act or the Indian Registration Act, 1866 came into force: (a) instruments of gift of immovable property; (b) other non-testamentary instruments which purport or operate to create, declare, assign, limit or extinguish any right, title or interest of the value of one hundred rupees or upwards, to or in immovable property.",
     "keywords": ["registration", "compulsory", "immovable property", "gift", "section 17"]},
]


async def seed_statutes():
    client = AsyncIOMotorClient(mongo_url)
    database = client[db_name]
    
    # Check if already seeded
    count = await database.statutes.count_documents({})
    if count > 0:
        print(f"Statutes already seeded ({count} documents). Skipping.")
        client.close()
        return
    
    print(f"Seeding {len(STATUTES)} statute entries...")
    await database.statutes.insert_many(STATUTES)
    
    # Create indexes
    await database.statutes.create_index([("act_name", 1), ("section_number", 1)])
    await database.statutes.create_index([("keywords", 1)])
    await database.statutes.create_index([
        ("section_text", "text"),
        ("section_title", "text"),
        ("act_name", "text")
    ])
    
    print(f"Successfully seeded {len(STATUTES)} statute entries with indexes.")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed_statutes())
