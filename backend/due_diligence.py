"""
Due Diligence Engine for Indian M&A Transactions
Comprehensive DD checklist generation, red flag detection, and compliance scoring
for acquisitions, mergers, demergers, JVs, and investments.

Covers:
- Legal DD (50+ items): Corporate structure, regulatory, litigation, contracts,
  property, employment, IP, environmental, insurance
- Financial DD (30+ items): Audited financials, revenue recognition, RPTs,
  tax compliance, debt, working capital, contingent liabilities
- Tax DD (20+ items): Income tax assessments, transfer pricing, MAT credit,
  GST compliance, TDS/TCS, international tax
- Red flag detection with Green/Yellow/Red scoring
- Compliance scoring with Go/No-Go recommendation
- Markdown DD report generation

References: Companies Act 2013, SEBI (LODR/SAST/ICDR), FEMA 1999,
Competition Act 2002, Income Tax Act 1961, CGST Act 2017, IBC 2016.
"""
import logging
from datetime import datetime, date
from typing import Optional

logger = logging.getLogger(__name__)


# =====================================================================
# TRANSACTION & SECTOR CONFIGURATION
# =====================================================================

TRANSACTION_TYPES = [
    "acquisition",
    "merger",
    "demerger",
    "joint_venture",
    "investment",
]

TARGET_TYPES = [
    "private_company",
    "public_company",
    "llp",
    "partnership",
    "sole_proprietor",
]

SECTORS = [
    "manufacturing",
    "IT",
    "pharma",
    "real_estate",
    "NBFC",
    "banking",
    "FMCG",
    "infra",
    "edtech",
    "fintech",
    "healthcare",
    "telecom",
    "media",
    "energy",
    "general",
]

# CCI combination thresholds (Competition Act 2002, Section 5)
CCI_ASSET_THRESHOLD_CRORES = 2000
CCI_TURNOVER_THRESHOLD_CRORES = 6000
CCI_ASSET_THRESHOLD_GROUP_CRORES = 8000
CCI_TURNOVER_THRESHOLD_GROUP_CRORES = 24000


# =====================================================================
# LEGAL DD CHECKLIST ITEMS (50+ items across 9 categories)
# =====================================================================

LEGAL_DD_CORPORATE_STRUCTURE = [
    {
        "id": "L-CS-01",
        "item": "Certificate of Incorporation and any name change certificates",
        "description": "Verify CIN, date of incorporation, and authorized capital from MCA records",
        "reference": "Companies Act 2013, Section 7",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company"],
    },
    {
        "id": "L-CS-02",
        "item": "Memorandum of Association (MOA) — current and all amendments",
        "description": "Review objects clause, authorized share capital, subscriber details; check ultra vires risk",
        "reference": "Companies Act 2013, Section 4",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company"],
    },
    {
        "id": "L-CS-03",
        "item": "Articles of Association (AOA) — current and all amendments",
        "description": "Review share transfer restrictions, director appointment rights, quorum, pre-emption rights, anti-dilution clauses",
        "reference": "Companies Act 2013, Section 5",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company"],
    },
    {
        "id": "L-CS-04",
        "item": "Board composition and director details (DIN, appointment letters, KYC)",
        "description": "Verify compliance with Section 149 (independent directors for public), Section 152 (rotational directors), and SEBI LODR if listed",
        "reference": "Companies Act 2013, Section 149, 152; SEBI LODR Reg 17",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company"],
    },
    {
        "id": "L-CS-05",
        "item": "Shareholding pattern — complete cap table with share certificates",
        "description": "Review all share issuances (equity, preference, convertible), ESOP grants, pending conversions; verify with MCA annual returns",
        "reference": "Companies Act 2013, Section 56, 62",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company"],
    },
    {
        "id": "L-CS-06",
        "item": "Group structure chart — subsidiaries, associates, JVs, holding companies",
        "description": "Map full corporate tree; verify Section 186 compliance for investments, Section 2(87) subsidiary status",
        "reference": "Companies Act 2013, Section 2(87), Section 186",
        "priority": "high",
        "applicable_to": ["private_company", "public_company"],
    },
    {
        "id": "L-CS-07",
        "item": "Shareholders' agreements (SHA), subscription agreements, side letters",
        "description": "Identify change of control triggers, tag-along/drag-along rights, anti-dilution provisions, liquidation preferences",
        "reference": "Contractual",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company"],
    },
    {
        "id": "L-CS-08",
        "item": "Board and general meeting minutes (last 5 years)",
        "description": "Check for undisclosed related party transactions, special resolutions, and any pending/contested resolutions",
        "reference": "Companies Act 2013, Section 118",
        "priority": "high",
        "applicable_to": ["private_company", "public_company"],
    },
    {
        "id": "L-CS-09",
        "item": "Statutory registers — members, directors, charges, significant beneficial owners",
        "description": "Verify Section 88 (register of members), Section 170 (register of directors), Section 77 (register of charges), SBO declaration under Section 90",
        "reference": "Companies Act 2013, Sections 77, 88, 90, 170",
        "priority": "high",
        "applicable_to": ["private_company", "public_company"],
    },
    {
        "id": "L-CS-10",
        "item": "LLP Agreement and all amendments, certificate of registration",
        "description": "Review capital contribution, profit sharing, partner admission/exit, designated partner obligations",
        "reference": "LLP Act 2008, Sections 7, 23",
        "priority": "critical",
        "applicable_to": ["llp"],
    },
    {
        "id": "L-CS-11",
        "item": "Partnership deed and all amendments/supplements",
        "description": "Review capital accounts, profit sharing ratio, retirement/admission clauses, goodwill valuation mechanism",
        "reference": "Indian Partnership Act 1932, Section 4",
        "priority": "critical",
        "applicable_to": ["partnership"],
    },
    {
        "id": "L-CS-12",
        "item": "Annual returns and financial statements filed with MCA/ROC (last 5 years)",
        "description": "Verify filing compliance; check for any defaulting company status under Section 164(2)",
        "reference": "Companies Act 2013, Sections 92, 137",
        "priority": "high",
        "applicable_to": ["private_company", "public_company"],
    },
]

LEGAL_DD_REGULATORY = [
    {
        "id": "L-RG-01",
        "item": "SEBI compliance — LODR, SAST, insider trading, ICDR compliance",
        "description": "Review SEBI LODR quarterly/annual filings, SAST trigger analysis, insider trading code compliance, any SEBI orders/directions",
        "reference": "SEBI (LODR) Regulations 2015; SEBI (SAST) Regulations 2011",
        "priority": "critical",
        "applicable_to": ["public_company"],
        "condition": "listed_entity",
    },
    {
        "id": "L-RG-02",
        "item": "RBI regulatory compliance — CRR/SLR, NPA classification, CRAR, priority sector",
        "description": "Review RBI inspection reports, NPA movement, CRAR compliance, provisioning adequacy, priority sector lending targets",
        "reference": "Banking Regulation Act 1949; RBI Master Directions",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company"],
        "condition": "sector_banking_nbfc",
    },
    {
        "id": "L-RG-03",
        "item": "FEMA compliance — FDI, ODI, ECB, downstream investment reporting",
        "description": "Verify FC-GPR/FC-TRS filings, sectoral cap compliance, pricing guidelines adherence, annual return on foreign liabilities and assets (FLA)",
        "reference": "FEMA 1999; FDI Policy 2020; FEMA 20(R)/2017",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company"],
        "condition": "foreign_investment",
    },
    {
        "id": "L-RG-04",
        "item": "CCI combination notification assessment",
        "description": "Evaluate if transaction triggers Section 5 thresholds: target/acquirer/combined assets > Rs 2,000Cr or turnover > Rs 6,000Cr (India); or group assets > Rs 8,000Cr or turnover > Rs 24,000Cr",
        "reference": "Competition Act 2002, Section 5, 6; CCI (Procedure in regard to transaction of business relating to combinations) Regulations 2011",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company", "llp"],
    },
    {
        "id": "L-RG-05",
        "item": "Sector-specific licenses, permits, and registrations",
        "description": "Pharma: DCGI/CDSCO licenses, drug manufacturing; Telecom: DoT license; NBFC: RBI CoR; Real estate: RERA registration; Food: FSSAI; IT: SEZ/STPI approvals",
        "reference": "Sector-specific legislation",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company", "llp"],
    },
    {
        "id": "L-RG-06",
        "item": "Foreign collaboration or technical assistance agreements",
        "description": "Review technology transfer, royalty obligations, brand licensing; verify RBI/AD bank approvals and FEMA compliance for outward remittances",
        "reference": "FEMA 1999; Income Tax Act Section 195 (withholding)",
        "priority": "high",
        "applicable_to": ["private_company", "public_company"],
    },
    {
        "id": "L-RG-07",
        "item": "Anti-money laundering (AML) compliance — PMLA registration, KYC records",
        "description": "Review PMLA compliance for reporting entities; check FIU-IND filings; verify internal AML policy existence",
        "reference": "Prevention of Money Laundering Act 2002",
        "priority": "high",
        "applicable_to": ["private_company", "public_company"],
        "condition": "sector_banking_nbfc",
    },
]

LEGAL_DD_LITIGATION = [
    {
        "id": "L-LT-01",
        "item": "All pending civil suits — schedule with case number, court, stage, relief claimed",
        "description": "Review plaints, written statements, interim orders; assess probable outcome and financial exposure",
        "reference": "Civil Procedure Code 1908",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company", "llp", "partnership", "sole_proprietor"],
    },
    {
        "id": "L-LT-02",
        "item": "Criminal proceedings — FIRs, charge sheets, complaints against company or directors",
        "description": "Check for Section 138 NI Act cases, fraud complaints, director liability under Section 141 NI Act and Section 34/35 Companies Act",
        "reference": "Negotiable Instruments Act 1881; BNS 2023; Companies Act 2013",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company", "llp", "partnership", "sole_proprietor"],
    },
    {
        "id": "L-LT-03",
        "item": "Tax litigation — income tax appeals (CIT-A, ITAT), GST appeals, customs disputes",
        "description": "Detail each pending assessment, demand amount, appellate stage, expected outcome based on precedent",
        "reference": "Income Tax Act 1961, Section 246A, 253; CGST Act 2017, Section 107",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company", "llp", "partnership", "sole_proprietor"],
    },
    {
        "id": "L-LT-04",
        "item": "Regulatory proceedings — SEBI, RBI, NCLT, CCI, environmental tribunal (NGT) orders",
        "description": "Identify any adjudication, consent orders, penalties imposed; check SEBI intermediate/final orders database",
        "reference": "SEBI Act 1992; RBI Act 1934; Companies Act 2013 (NCLT); Competition Act 2002",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company"],
    },
    {
        "id": "L-LT-05",
        "item": "Arbitration proceedings — pending and concluded (institutional and ad hoc)",
        "description": "Review arbitration clauses in key contracts; status of pending proceedings; any enforcement challenges under Section 34/36 A&C Act",
        "reference": "Arbitration and Conciliation Act 1996",
        "priority": "high",
        "applicable_to": ["private_company", "public_company", "llp", "partnership"],
    },
    {
        "id": "L-LT-06",
        "item": "Consumer complaints — district/state/national commission cases",
        "description": "Schedule of complaints with relief claimed; check for class action risks under Section 245 Companies Act",
        "reference": "Consumer Protection Act 2019; Companies Act 2013, Section 245",
        "priority": "medium",
        "applicable_to": ["private_company", "public_company", "llp"],
    },
    {
        "id": "L-LT-07",
        "item": "Labour disputes — pending cases before labour court, industrial tribunal, conciliation proceedings",
        "description": "Review workmen disputes, standing orders compliance, trade union negotiations; assess back-wage liability",
        "reference": "Industrial Disputes Act 1947; Industrial Relations Code 2020",
        "priority": "high",
        "applicable_to": ["private_company", "public_company", "llp", "partnership"],
    },
    {
        "id": "L-LT-08",
        "item": "Contingent liabilities — full schedule with provision adequacy assessment",
        "description": "Cross-check board minutes, auditor notes, and legal opinion letters; assess provision vs. actual exposure gap",
        "reference": "Ind AS 37 (Provisions, Contingent Liabilities and Contingent Assets)",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company", "llp"],
    },
]

LEGAL_DD_CONTRACTS = [
    {
        "id": "L-CT-01",
        "item": "Material contracts — top 20 by revenue/expenditure",
        "description": "Review term, termination rights, pricing mechanism, auto-renewal, liability caps, indemnity clauses",
        "reference": "Indian Contract Act 1872",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company", "llp", "partnership", "sole_proprietor"],
    },
    {
        "id": "L-CT-02",
        "item": "Change of control clauses in all material contracts",
        "description": "Identify contracts requiring consent on change of control; assess risk of contract termination post-acquisition",
        "reference": "Contractual; Companies Act 2013 Section 230-232 for schemes",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company", "llp"],
    },
    {
        "id": "L-CT-03",
        "item": "Non-compete and non-solicitation agreements with key employees and promoters",
        "description": "Review scope, duration, geographic limitations; note Indian law position on restraint of trade under Section 27 Contract Act",
        "reference": "Indian Contract Act 1872, Section 27",
        "priority": "high",
        "applicable_to": ["private_company", "public_company", "llp", "partnership"],
    },
    {
        "id": "L-CT-04",
        "item": "Key customer contracts — top 10 customers by revenue",
        "description": "Assess revenue concentration risk, payment terms, warranty/indemnity exposure, renewal likelihood",
        "reference": "Contractual",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company", "llp", "partnership", "sole_proprietor"],
    },
    {
        "id": "L-CT-05",
        "item": "Key supplier/vendor contracts — top 10 by spend",
        "description": "Assess supply chain concentration, alternate sourcing, pricing escalation clauses, exclusivity obligations",
        "reference": "Contractual",
        "priority": "high",
        "applicable_to": ["private_company", "public_company", "llp", "partnership", "sole_proprietor"],
    },
    {
        "id": "L-CT-06",
        "item": "IP licensing agreements — inbound and outbound licenses",
        "description": "Review scope of license, sublicensing rights, royalty obligations, assignability, termination on change of control",
        "reference": "Patents Act 1970; Copyright Act 1957; Trade Marks Act 1999",
        "priority": "high",
        "applicable_to": ["private_company", "public_company", "llp"],
    },
    {
        "id": "L-CT-07",
        "item": "Government contracts and public procurement agreements",
        "description": "Review tenure, performance guarantees, blacklisting risks, mandatory subcontracting, offset obligations",
        "reference": "GFR 2017; specific ministry procurement policies",
        "priority": "high",
        "applicable_to": ["private_company", "public_company", "llp"],
        "condition": "government_contracts",
    },
]

LEGAL_DD_PROPERTY = [
    {
        "id": "L-PR-01",
        "item": "Title documents for all owned immovable properties",
        "description": "Verify chain of title (minimum 30 years for freehold), verify registration under Registration Act 1908, obtain title search report from local advocate",
        "reference": "Transfer of Property Act 1882; Registration Act 1908",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company", "llp", "partnership", "sole_proprietor"],
    },
    {
        "id": "L-PR-02",
        "item": "Encumbrance certificates for all properties (last 30 years)",
        "description": "Obtain from Sub-Registrar office; verify no mortgages, liens, attachments, or encumbrances exist",
        "reference": "Registration Act 1908",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company", "llp", "partnership", "sole_proprietor"],
    },
    {
        "id": "L-PR-03",
        "item": "Mutation records (revenue records / 7/12 extract / patta / khata)",
        "description": "Verify mutation in revenue records corresponds to title holder; obtain latest revenue extract",
        "reference": "State-specific land revenue codes",
        "priority": "high",
        "applicable_to": ["private_company", "public_company", "llp", "partnership", "sole_proprietor"],
    },
    {
        "id": "L-PR-04",
        "item": "Lease/license agreements for all rented premises",
        "description": "Review term, rent escalation, lock-in, renewal rights, permitted use, assignment/subletting restrictions",
        "reference": "Transfer of Property Act 1882, Section 105; state Rent Control Acts",
        "priority": "high",
        "applicable_to": ["private_company", "public_company", "llp", "partnership", "sole_proprietor"],
    },
    {
        "id": "L-PR-05",
        "item": "Pending property litigation and land acquisition proceedings",
        "description": "Check for suits for possession, injunctions, acquisition notifications under RFCTLARR Act 2013",
        "reference": "RFCTLARR Act 2013; state land acquisition statutes",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company", "llp", "partnership", "sole_proprietor"],
    },
    {
        "id": "L-PR-06",
        "item": "Building plan approvals, completion/occupancy certificates",
        "description": "Verify approvals from municipal/development authority; check for unauthorized construction; confirm no demolition notices",
        "reference": "State municipal laws; local development authority regulations",
        "priority": "high",
        "applicable_to": ["private_company", "public_company", "llp", "partnership"],
    },
]

LEGAL_DD_EMPLOYMENT = [
    {
        "id": "L-EM-01",
        "item": "Employee census — total headcount, category-wise (workmen/staff/management)",
        "description": "Obtain org structure, department-wise headcount, contract vs. permanent ratio, attrition data for 3 years",
        "reference": "Industrial Disputes Act 1947; Occupational Safety Code 2020",
        "priority": "high",
        "applicable_to": ["private_company", "public_company", "llp", "partnership"],
    },
    {
        "id": "L-EM-02",
        "item": "ESOP/ESPS/SAR scheme documents, grant letters, vesting schedules",
        "description": "Review ESOP trust structure, exercise price, vesting conditions, SEBI SBEB compliance if listed; calculate fully diluted equity impact",
        "reference": "Companies Act 2013, Section 62(1)(b); SEBI (SBEB&SE) Regulations 2021",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company"],
    },
    {
        "id": "L-EM-03",
        "item": "Employment contracts for key management personnel (KMP) and senior management",
        "description": "Review non-compete, notice period, severance, incentive structure, IP assignment, confidentiality obligations",
        "reference": "Companies Act 2013, Section 2(51); Indian Contract Act 1872",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company", "llp"],
    },
    {
        "id": "L-EM-04",
        "item": "PF compliance — registration, contribution, annual returns, inspection reports",
        "description": "Verify EPFO registration, monthly contribution compliance (employee+employer 12%), Form 5A filing, any PF department inspections/demands",
        "reference": "Employees' Provident Funds & Miscellaneous Provisions Act 1952",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company", "llp", "partnership"],
    },
    {
        "id": "L-EM-05",
        "item": "ESI compliance — registration, contribution, accident/injury records",
        "description": "Verify ESIC registration (if 10+ employees, wages up to Rs 21,000/month), contribution compliance (employer 3.25%, employee 0.75%)",
        "reference": "Employees' State Insurance Act 1948",
        "priority": "high",
        "applicable_to": ["private_company", "public_company", "llp", "partnership"],
    },
    {
        "id": "L-EM-06",
        "item": "Shops & Establishment registration and compliance",
        "description": "Verify state-wise S&E registration, working hours compliance, leave policy, salary payment records under Payment of Wages Act",
        "reference": "State Shops & Establishments Acts; Payment of Wages Act 1936",
        "priority": "high",
        "applicable_to": ["private_company", "public_company", "llp", "partnership", "sole_proprietor"],
    },
    {
        "id": "L-EM-07",
        "item": "Labour law compliance — factory license, contract labour, bonus, gratuity",
        "description": "Verify Factories Act registration (if manufacturing), CLRA license, bonus computation under Payment of Bonus Act, gratuity trust/insurance",
        "reference": "Factories Act 1948; CLRA 1970; Payment of Bonus Act 1965; Payment of Gratuity Act 1972",
        "priority": "high",
        "applicable_to": ["private_company", "public_company", "llp", "partnership"],
    },
]

LEGAL_DD_IP = [
    {
        "id": "L-IP-01",
        "item": "Trademark registrations (registered and applied) — full schedule",
        "description": "Verify classes, validity, renewal dates, opposition proceedings; check if any marks are unregistered/common law only",
        "reference": "Trade Marks Act 1999; Trade Marks Rules 2017",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company", "llp", "partnership", "sole_proprietor"],
    },
    {
        "id": "L-IP-02",
        "item": "Patent portfolio — granted, pending, provisional applications",
        "description": "Review patent claims, validity, annual maintenance fees, freedom-to-operate analysis, licensing status",
        "reference": "Patents Act 1970; Patents Rules 2003",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company", "llp"],
    },
    {
        "id": "L-IP-03",
        "item": "Copyright registrations and assignments — software, literary, artistic works",
        "description": "Verify copyright ownership (especially for employee-created works under Section 17), registration status, assignment chain",
        "reference": "Copyright Act 1957, Section 17, 18",
        "priority": "high",
        "applicable_to": ["private_company", "public_company", "llp"],
    },
    {
        "id": "L-IP-04",
        "item": "Trade secrets and confidential information protection measures",
        "description": "Review NDA regime, employee IP assignment policy, access controls, reverse engineering risks; note India has no standalone trade secrets statute",
        "reference": "Indian Contract Act 1872 (NDA enforcement); IT Act 2000",
        "priority": "high",
        "applicable_to": ["private_company", "public_company", "llp"],
    },
    {
        "id": "L-IP-05",
        "item": "Domain names and social media handles — registration, renewal, ownership",
        "description": "Verify domain registration (NIXI/.in and international gTLDs), WHOIS records, renewal calendar, key social media account ownership",
        "reference": "ICANN; INDRP (.in Domain Name Dispute Resolution Policy)",
        "priority": "medium",
        "applicable_to": ["private_company", "public_company", "llp", "partnership", "sole_proprietor"],
    },
    {
        "id": "L-IP-06",
        "item": "IP infringement claims — received and initiated",
        "description": "Schedule of all IP disputes — trademark opposition, patent invalidity, copyright infringement; potential damages exposure",
        "reference": "Trade Marks Act 1999; Patents Act 1970; Copyright Act 1957",
        "priority": "high",
        "applicable_to": ["private_company", "public_company", "llp"],
    },
]

LEGAL_DD_ENVIRONMENTAL = [
    {
        "id": "L-EN-01",
        "item": "Environmental clearances (EC) from MoEFCC / SEIAA",
        "description": "Verify EC validity, conditions compliance, monitoring reports; check for any show cause or revocation proceedings",
        "reference": "Environment Protection Act 1986; EIA Notification 2006",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company", "llp"],
        "condition": "manufacturing_infra",
    },
    {
        "id": "L-EN-02",
        "item": "Consent to Establish (CTE) and Consent to Operate (CTO) from state PCB",
        "description": "Verify consent validity, prescribed pollution standards compliance, renewal dates; check for any default notices",
        "reference": "Water (Prevention and Control of Pollution) Act 1974; Air (Prevention and Control of Pollution) Act 1981",
        "priority": "critical",
        "applicable_to": ["private_company", "public_company", "llp"],
        "condition": "manufacturing_infra",
    },
    {
        "id": "L-EN-03",
        "item": "Hazardous waste authorization and management",
        "description": "Verify authorization under HW Rules 2016, waste inventory, disposal manifests, treatment/recycling arrangements",
        "reference": "Hazardous and Other Wastes (Management and Transboundary Movement) Rules 2016",
        "priority": "high",
        "applicable_to": ["private_company", "public_company", "llp"],
        "condition": "manufacturing_pharma",
    },
    {
        "id": "L-EN-04",
        "item": "Environmental Impact Assessment (EIA) reports (if applicable)",
        "description": "Review EIA/EMP reports, public hearing records, expert appraisal committee recommendations",
        "reference": "EIA Notification 2006 (Schedule I/II activities)",
        "priority": "high",
        "applicable_to": ["private_company", "public_company"],
        "condition": "manufacturing_infra_real_estate",
    },
    {
        "id": "L-EN-05",
        "item": "NGT orders or pending proceedings",
        "description": "Check for any National Green Tribunal proceedings involving the target or its facilities",
        "reference": "National Green Tribunal Act 2010",
        "priority": "high",
        "applicable_to": ["private_company", "public_company", "llp"],
    },
]

LEGAL_DD_INSURANCE = [
    {
        "id": "L-IN-01",
        "item": "All existing insurance policies — schedule with premium, sum insured, expiry",
        "description": "Property all risk, marine cargo/transit, fire, burglary, public liability, product liability, professional indemnity, cyber insurance",
        "reference": "Insurance Act 1938; IRDAI Regulations",
        "priority": "high",
        "applicable_to": ["private_company", "public_company", "llp", "partnership"],
    },
    {
        "id": "L-IN-02",
        "item": "Coverage adequacy assessment — sum insured vs. asset value and business interruption risk",
        "description": "Compare sum insured with replacement cost of assets; evaluate business interruption coverage against revenue",
        "reference": "IRDAI guidelines",
        "priority": "medium",
        "applicable_to": ["private_company", "public_company", "llp"],
    },
    {
        "id": "L-IN-03",
        "item": "Pending insurance claims and claim history (last 5 years)",
        "description": "Review all pending claims, rejected claims with reasons, settlement history; assess if target is an adverse risk",
        "reference": "Insurance Act 1938",
        "priority": "medium",
        "applicable_to": ["private_company", "public_company", "llp", "partnership"],
    },
    {
        "id": "L-IN-04",
        "item": "Directors & Officers (D&O) liability insurance",
        "description": "Verify existence and adequacy of D&O cover; check tail coverage provisions for pre-closing acts; Section 197 managerial remuneration compliance",
        "reference": "Companies Act 2013, Section 197; SEBI LODR",
        "priority": "high",
        "applicable_to": ["private_company", "public_company"],
    },
    {
        "id": "L-IN-05",
        "item": "Key-man insurance for promoters and critical personnel",
        "description": "Assess key-person dependency risk; review existing key-man policies and beneficiary structure",
        "reference": "IRDAI regulations",
        "priority": "medium",
        "applicable_to": ["private_company", "public_company"],
    },
]


# =====================================================================
# FINANCIAL DD CHECKLIST ITEMS (30+ items)
# =====================================================================

FINANCIAL_DD_ITEMS = [
    {
        "id": "F-01",
        "item": "Audited financial statements — last 5 years (or since incorporation if younger)",
        "description": "Balance sheet, P&L, cash flow statement, notes to accounts, schedules; verify auditor's report is unqualified",
        "reference": "Companies Act 2013, Section 129, 134; Ind AS / AS framework",
        "priority": "critical",
    },
    {
        "id": "F-02",
        "item": "Management accounts / provisional financials (current year-to-date)",
        "description": "Monthly MIS, management P&L, balance sheet; compare with audited trends to detect window dressing",
        "reference": "Internal",
        "priority": "critical",
    },
    {
        "id": "F-03",
        "item": "Audit qualifications and emphasis of matter paragraphs analysis",
        "description": "List all qualifications, emphasis of matter, key audit matters (KAMs) from last 5 years; assess materiality and management response",
        "reference": "SA 705 (Modified Opinions); SA 706 (Emphasis of Matter)",
        "priority": "critical",
    },
    {
        "id": "F-04",
        "item": "Revenue recognition policy review and consistency check",
        "description": "Verify Ind AS 115 compliance (5-step model); identify performance obligations, variable consideration, contract modifications; check for channel stuffing or round-tripping",
        "reference": "Ind AS 115 (Revenue from Contracts with Customers)",
        "priority": "critical",
    },
    {
        "id": "F-05",
        "item": "Related party transactions (RPT) — full schedule and arm's length justification",
        "description": "Map all related parties per Section 2(76); review Section 188 board/shareholder approvals; verify Ind AS 24 disclosures; obtain transfer pricing documentation if applicable",
        "reference": "Companies Act 2013, Section 188; Ind AS 24; SEBI LODR Reg 23",
        "priority": "critical",
    },
    {
        "id": "F-06",
        "item": "Income tax returns and computation — last 5 assessment years",
        "description": "Verify filed returns vs. audited financials; reconcile book profit to taxable income; review Section 143(1) intimations and Section 143(3) assessment orders",
        "reference": "Income Tax Act 1961, Sections 139, 143",
        "priority": "critical",
    },
    {
        "id": "F-07",
        "item": "GST compliance — returns filing status and reconciliation",
        "description": "GSTR-1/3B filing compliance, GSTR-9 annual return, GSTR-9C reconciliation, ITC claimed vs. available in GSTR-2B, any demand/SCN",
        "reference": "CGST Act 2017, Sections 37, 39, 44",
        "priority": "critical",
    },
    {
        "id": "F-08",
        "item": "TDS compliance — quarterly returns, certificates, demands",
        "description": "Verify 26Q/24Q/27Q filing, Form 16/16A issuance, TDS default notices, short deduction/late deposit penalties",
        "reference": "Income Tax Act 1961, Sections 192-206; Section 234E",
        "priority": "high",
    },
    {
        "id": "F-09",
        "item": "Transfer pricing documentation (if applicable)",
        "description": "Review TP study report, benchmarking analysis, Form 3CEB; check for TP adjustments in assessments; BEPS compliance (CbCR, Master File)",
        "reference": "Income Tax Act 1961, Sections 92A-92F; Rule 10D",
        "priority": "critical",
        "condition": "international_transactions",
    },
    {
        "id": "F-10",
        "item": "Debt schedule — all borrowings with terms, security, covenants",
        "description": "Comprehensive loan list (term loans, CC/OD, ECBs, NCDs, inter-corporate); security details, covenant compliance, default history, pre-payment obligations",
        "reference": "Companies Act 2013, Section 180(1)(c); FEMA (ECB)",
        "priority": "critical",
    },
    {
        "id": "F-11",
        "item": "Charge register — all charges created with ROC",
        "description": "Cross-verify with MCA charge records (CHG-1); identify unregistered charges (void under Section 77); check satisfaction status of discharged loans",
        "reference": "Companies Act 2013, Section 77, 82",
        "priority": "critical",
    },
    {
        "id": "F-12",
        "item": "Working capital analysis — receivables aging, payables aging, inventory quality",
        "description": "Age-wise receivables (30/60/90/180/360+ days); identify doubtful debts; payables concentration; inventory obsolescence; cash conversion cycle trend",
        "reference": "Ind AS 109 (ECL model for receivables); Ind AS 2 (Inventories)",
        "priority": "critical",
    },
    {
        "id": "F-13",
        "item": "Contingent liabilities and off-balance sheet items",
        "description": "Full schedule per Ind AS 37; guarantees given (corporate/personal), letters of comfort; off-balance sheet arrangements (operating leases pre-Ind AS 116, SPVs)",
        "reference": "Ind AS 37; Ind AS 116; Schedule III Companies Act 2013",
        "priority": "critical",
    },
    {
        "id": "F-14",
        "item": "Capital expenditure plan, commitments, and capital WIP aging",
        "description": "Review approved capex budget, pending commitments for plant/machinery/construction; age capital WIP items; check for stalled projects",
        "reference": "Ind AS 16 (Property, Plant and Equipment); CARO 2020",
        "priority": "high",
    },
    {
        "id": "F-15",
        "item": "Dividend history, distribution policy, and buyback history",
        "description": "Last 5 years dividend record; compliance with Section 123 (distributable profits); DDT history (pre-April 2020); any share buyback under Section 68",
        "reference": "Companies Act 2013, Sections 68, 123; SEBI Buyback Regulations",
        "priority": "medium",
    },
    {
        "id": "F-16",
        "item": "Cash flow statement analysis and free cash flow computation",
        "description": "Verify cash flow from operations vs. reported profit (quality of earnings); identify exceptional or non-recurring cash flows",
        "reference": "Ind AS 7 (Statement of Cash Flows)",
        "priority": "high",
    },
    {
        "id": "F-17",
        "item": "CARO (Companies Auditor's Report Order) observations — last 3 years",
        "description": "Review CARO 2020 clauses: fixed asset title (clause iii), inventory verification (clause ii), Section 185/186 compliance (clause iii), fraud reporting (clause xi)",
        "reference": "CARO 2020; Companies Act 2013, Section 143(11)",
        "priority": "critical",
    },
    {
        "id": "F-18",
        "item": "Bank statements — all operative accounts for last 12 months",
        "description": "Verify cash balances, identify unusual transactions, large round-figure transfers, check for unrecorded borrowings (CC/OD limits vs. utilization)",
        "reference": "Internal verification",
        "priority": "high",
    },
    {
        "id": "F-19",
        "item": "Fixed asset register and physical verification records",
        "description": "Reconcile FAR with audited balance sheet; verify last physical verification date and discrepancies; check for fully depreciated but in-use assets",
        "reference": "Ind AS 16; CARO 2020 clause (i)",
        "priority": "high",
    },
    {
        "id": "F-20",
        "item": "Segment-wise revenue and profitability analysis",
        "description": "Revenue and margin by business segment, product line, geography; identify cross-subsidization and segment viability",
        "reference": "Ind AS 108 (Operating Segments)",
        "priority": "high",
    },
    {
        "id": "F-21",
        "item": "Statutory dues — schedule of outstanding government dues",
        "description": "Income tax, GST, customs duty, excise duty, PF, ESI, professional tax, property tax; verify from auditor's report and CARO",
        "reference": "CARO 2020 clause (vii); Schedule III",
        "priority": "critical",
    },
    {
        "id": "F-22",
        "item": "Loans and advances to related parties — Section 185/186 compliance",
        "description": "Verify all inter-corporate loans, investments, guarantees are within Section 186 limits; Section 185 (loans to directors) compliance",
        "reference": "Companies Act 2013, Sections 185, 186",
        "priority": "critical",
    },
    {
        "id": "F-23",
        "item": "Foreign exchange exposure and hedging policy",
        "description": "Assess forex revenue/cost exposure; review hedging instruments (forwards, options); mark-to-market gains/losses; FEMA compliance for forex transactions",
        "reference": "Ind AS 109 (Hedge Accounting); FEMA 1999",
        "priority": "high",
        "condition": "forex_exposure",
    },
    {
        "id": "F-24",
        "item": "Deferred tax asset/liability computation and recoverability",
        "description": "Review DTA recoverability assessment (future profitability projections); verify DTL completeness; MAT credit entitlement under Section 115JAA",
        "reference": "Ind AS 12 (Income Taxes); Income Tax Act Section 115JAA",
        "priority": "high",
    },
    {
        "id": "F-25",
        "item": "Provisions and reserves — schedule with adequacy assessment",
        "description": "Warranty provisions, bad debt provisions, onerous contract provisions, restructuring provisions; assess adequacy against actual experience",
        "reference": "Ind AS 37; Ind AS 36 (Impairment)",
        "priority": "high",
    },
    {
        "id": "F-26",
        "item": "EBITDA normalization — identify one-time items and adjustments",
        "description": "Build normalized EBITDA bridge: remove one-time income/expenses, non-cash items, related party adjustments, owner-specific costs; derive sustainable earnings",
        "reference": "Transaction-specific",
        "priority": "critical",
    },
    {
        "id": "F-27",
        "item": "Net debt computation and adjustments",
        "description": "Total debt minus cash/equivalents; identify debt-like items (outstanding capex, deferred consideration, earn-outs, contingent liabilities to be treated as debt)",
        "reference": "Transaction-specific",
        "priority": "critical",
    },
    {
        "id": "F-28",
        "item": "Working capital normalization and peg computation",
        "description": "Calculate average NWC (current assets minus current liabilities excluding cash/debt); derive target NWC peg for locked box/completion mechanism",
        "reference": "Transaction-specific",
        "priority": "critical",
    },
    {
        "id": "F-29",
        "item": "Ind AS transition adjustments (if recently transitioned from AS)",
        "description": "Review Ind AS 101 first-time adoption choices; reconcile opening balance sheet adjustments; assess impact on comparability",
        "reference": "Ind AS 101 (First-time Adoption)",
        "priority": "medium",
    },
    {
        "id": "F-30",
        "item": "Internal audit reports and management letters (last 3 years)",
        "description": "Review internal audit scope, key findings, open items; management letter observations from statutory auditor; assess internal control environment",
        "reference": "Companies Act 2013, Section 138",
        "priority": "high",
    },
    {
        "id": "F-31",
        "item": "Fraud reported by auditor under Section 143(12) and CARO fraud clause",
        "description": "Check if statutory auditor reported fraud to Central Government; review CARO 2020 clause (xi) on fraud observations",
        "reference": "Companies Act 2013, Section 143(12); CARO 2020 clause (xi)",
        "priority": "critical",
    },
]


# =====================================================================
# TAX DD CHECKLIST ITEMS (20+ items)
# =====================================================================

TAX_DD_ITEMS = [
    {
        "id": "T-01",
        "item": "Income tax assessments — completed and pending for last 6 AYs",
        "description": "Schedule of assessments u/s 143(1), 143(3), 147, 153A; assessment orders, additions made, relief obtained at CIT(A)/ITAT",
        "reference": "Income Tax Act 1961, Sections 143, 147, 153A",
        "priority": "critical",
    },
    {
        "id": "T-02",
        "item": "Tax demands outstanding and appeals pending",
        "description": "Total demand outstanding; stage of appeal (CIT-A / ITAT / High Court / Supreme Court); pre-deposit amounts; expected timeline for resolution",
        "reference": "Income Tax Act 1961, Sections 220, 246A, 253, 260A",
        "priority": "critical",
    },
    {
        "id": "T-03",
        "item": "Transfer pricing adjustments and documentation",
        "description": "TP adjustments in past assessments; DRP proceedings; APA (advance pricing agreement) status; secondary adjustment compliance under Section 92CE",
        "reference": "Income Tax Act 1961, Sections 92-92F; Section 92CE",
        "priority": "critical",
        "condition": "international_transactions",
    },
    {
        "id": "T-04",
        "item": "MAT credit availability and computation",
        "description": "Verify MAT credit under Section 115JAA; 15-year utilization window; reconcile with income tax computation",
        "reference": "Income Tax Act 1961, Section 115JB, 115JAA",
        "priority": "high",
    },
    {
        "id": "T-05",
        "item": "Carried forward losses and unabsorbed depreciation — schedule with expiry",
        "description": "Business loss (8-year limit), speculation loss (4-year limit), capital loss (8-year limit); unabsorbed depreciation (no time limit); Section 79 change in shareholding impact",
        "reference": "Income Tax Act 1961, Sections 72-79",
        "priority": "critical",
    },
    {
        "id": "T-06",
        "item": "GST compliance status — all GSTINs, returns filed, demands",
        "description": "List all GSTIN registrations (state-wise); GSTR-1/3B filing compliance; GSTR-9/9C (audit) filing; ITC reversals under Rule 42/43; any show cause notices under Section 73/74",
        "reference": "CGST Act 2017, Sections 37, 39, 44, 73, 74",
        "priority": "critical",
    },
    {
        "id": "T-07",
        "item": "TDS/TCS compliance and default status",
        "description": "Review 26Q/24Q/27Q/27EQ filing; short deduction notices u/s 201; late filing fees u/s 234E; Section 40(a)(ia) disallowance risk for non-deduction",
        "reference": "Income Tax Act 1961, Sections 192-206C; Section 201; Section 234E",
        "priority": "critical",
    },
    {
        "id": "T-08",
        "item": "International tax issues — PE risk, withholding, DTAA applicability",
        "description": "Assess permanent establishment risk for foreign clients/branches; treaty benefit claims; withholding tax compliance on cross-border payments; equalization levy applicability",
        "reference": "Income Tax Act 1961, Section 9; DTAA network; Equalization Levy (Finance Act 2016)",
        "priority": "high",
        "condition": "international_operations",
    },
    {
        "id": "T-09",
        "item": "Tax indemnity requirements — quantification of exposure",
        "description": "Aggregate all uncertain tax positions; classify probability (probable/possible/remote); quantify indemnity basket for SPA",
        "reference": "Transaction-specific; Ind AS 37/12",
        "priority": "critical",
    },
    {
        "id": "T-10",
        "item": "Stamp duty and registration exposure on past transactions",
        "description": "Review past share transfers, property transactions, loan agreements for adequate stamping; assess deficiency exposure under Indian Stamp Act",
        "reference": "Indian Stamp Act 1899; state Stamp Acts",
        "priority": "high",
    },
    {
        "id": "T-11",
        "item": "Custom duty classification and drawback claims",
        "description": "Review HS code classifications; pending refund claims; anti-dumping duty exposure; advance authorization/DFIA compliance",
        "reference": "Customs Act 1962; Customs Tariff Act 1975; Foreign Trade Policy",
        "priority": "high",
        "condition": "import_export",
    },
    {
        "id": "T-12",
        "item": "Section 56(2)(x) applicability — shares issued below FMV",
        "description": "Check if any shares issued at premium without adequate FMV justification; verify Rule 11UA valuation for private companies; deemed income risk",
        "reference": "Income Tax Act 1961, Section 56(2)(x); Rule 11UA",
        "priority": "critical",
    },
    {
        "id": "T-13",
        "item": "Section 50CA/Section 56(2)(x) — transfer of unquoted shares below FMV",
        "description": "Verify past share transfers at or above FMV per Rule 11UA/11UAA; assess deemed capital gains or deemed income exposure",
        "reference": "Income Tax Act 1961, Sections 50CA, 56(2)(x)",
        "priority": "high",
    },
    {
        "id": "T-14",
        "item": "Professional tax registration and compliance",
        "description": "State-wise professional tax registration for employer and employees; monthly/annual return filing; check for defaults",
        "reference": "State Professional Tax Acts (Maharashtra, Karnataka, etc.)",
        "priority": "medium",
    },
    {
        "id": "T-15",
        "item": "Tax residency certificate and treaty eligibility assessment",
        "description": "Verify TRC issuance for inbound/outbound payments; POEM (Place of Effective Management) analysis for foreign subsidiaries; GAAR risk assessment",
        "reference": "Income Tax Act 1961, Sections 6, 90; CBDT POEM guidelines; Chapter XA (GAAR)",
        "priority": "high",
        "condition": "international_operations",
    },
    {
        "id": "T-16",
        "item": "Advance tax payment compliance and interest liability",
        "description": "Verify quarterly advance tax payments (15 Jun/15 Sep/15 Dec/15 Mar); calculate interest liability u/s 234B (non-payment) and 234C (deferment)",
        "reference": "Income Tax Act 1961, Sections 208-211; Sections 234B, 234C",
        "priority": "high",
    },
    {
        "id": "T-17",
        "item": "Goods and Services Tax — anti-profiteering compliance",
        "description": "Assess if target passed on input tax credit benefits from rate reductions; check for any anti-profiteering complaints or NAA orders",
        "reference": "CGST Act 2017, Section 171; Anti-Profiteering Rules",
        "priority": "medium",
    },
    {
        "id": "T-18",
        "item": "Tax incentive and exemption claims — SEZ, STPI, Section 10AA, Section 80IA/80IB",
        "description": "Verify eligibility conditions for each incentive claimed; check for retrospective withdrawal risk; remaining benefit period",
        "reference": "Income Tax Act 1961, Sections 10AA, 80IA, 80IB; SEZ Act 2005",
        "priority": "high",
    },
    {
        "id": "T-19",
        "item": "Retrospective tax amendments exposure assessment",
        "description": "Assess exposure from retrospective amendments (e.g., indirect transfer under Section 9(1)(i) post-2012 amendment, now resolved for some cases); carry-forward impact",
        "reference": "Income Tax Act 1961, Section 9(1)(i); Taxation Laws (Amendment) Act 2021",
        "priority": "medium",
    },
    {
        "id": "T-20",
        "item": "GST ITC reconciliation — GSTR-2B vs. books",
        "description": "Reconcile ITC claimed in GSTR-3B with ITC available in GSTR-2B; identify ineligible ITC, blocked credits under Section 17(5); excess credit risk",
        "reference": "CGST Act 2017, Sections 16-18; Section 17(5); Rule 36(4)",
        "priority": "critical",
    },
    {
        "id": "T-21",
        "item": "E-invoicing and e-way bill compliance",
        "description": "Verify e-invoicing compliance (mandatory if turnover > Rs 5Cr); e-way bill generation for goods movement > Rs 50,000; check for penalty exposure",
        "reference": "CGST Rules 2017, Rule 48(4); E-way Bill Rules",
        "priority": "high",
    },
]


# =====================================================================
# RED FLAG DEFINITIONS
# =====================================================================

RED_FLAG_RULES = [
    {
        "id": "RF-01",
        "flag": "Revenue concentration — single customer > 40% of total revenue",
        "category": "financial",
        "severity": "high",
        "check_key": "revenue_concentration_pct",
        "threshold": 40,
        "operator": "gt",
        "implication": "High customer dependency risk; pricing power concerns; loss of customer = existential threat",
    },
    {
        "id": "RF-02",
        "flag": "Related party revenue > 25% of total revenue",
        "category": "financial",
        "severity": "high",
        "check_key": "related_party_revenue_pct",
        "threshold": 25,
        "operator": "gt",
        "implication": "Arm's length pricing concerns; artificial revenue inflation risk; TP adjustment exposure",
    },
    {
        "id": "RF-03",
        "flag": "Qualified audit report in last 3 years",
        "category": "financial",
        "severity": "critical",
        "check_key": "has_qualified_audit",
        "threshold": True,
        "operator": "eq",
        "implication": "Material misstatement or scope limitation acknowledged by auditor; reliability of financials questioned",
    },
    {
        "id": "RF-04",
        "flag": "Pending tax demands > 10% of net worth",
        "category": "tax",
        "severity": "high",
        "check_key": "tax_demand_to_networth_pct",
        "threshold": 10,
        "operator": "gt",
        "implication": "Significant tax exposure; may require substantial indemnity; affects enterprise value",
    },
    {
        "id": "RF-05",
        "flag": "Director disqualification under Section 164 Companies Act 2013",
        "category": "legal",
        "severity": "critical",
        "check_key": "has_disqualified_director",
        "threshold": True,
        "operator": "eq",
        "implication": "Governance failure indicator; Section 164(2) disqualification for non-filing; may affect validity of board actions",
    },
    {
        "id": "RF-06",
        "flag": "NCLT/IBC proceedings — current or in past 3 years",
        "category": "legal",
        "severity": "critical",
        "check_key": "has_nclt_ibc_proceedings",
        "threshold": True,
        "operator": "eq",
        "implication": "Financial distress history; Section 29A eligibility concerns for acquirer; creditor claims may be outstanding",
    },
    {
        "id": "RF-07",
        "flag": "FEMA violations or ED (Enforcement Directorate) investigations",
        "category": "regulatory",
        "severity": "critical",
        "check_key": "has_fema_ed_issues",
        "threshold": True,
        "operator": "eq",
        "implication": "Potential compounding/adjudication exposure; asset attachment risk under PMLA; reputational damage",
    },
    {
        "id": "RF-08",
        "flag": "Fraud reported by auditor under Section 143(12) or CARO clause (xi)",
        "category": "financial",
        "severity": "critical",
        "check_key": "has_fraud_reporting",
        "threshold": True,
        "operator": "eq",
        "implication": "Fraud in the company; potential criminal proceedings; fundamental governance/integrity concern; deal-breaker in most cases",
    },
    {
        "id": "RF-09",
        "flag": "Negative net worth or erosion of > 50% of capital",
        "category": "financial",
        "severity": "critical",
        "check_key": "has_negative_networth",
        "threshold": True,
        "operator": "eq",
        "implication": "Going concern risk; Section 271 NCLT winding up trigger if net worth eroded fully; sick company under BIFR/NCLT provisions",
    },
    {
        "id": "RF-10",
        "flag": "Non-compliance with Section 185/186 — loans to directors or excessive investments",
        "category": "legal",
        "severity": "high",
        "check_key": "has_section_185_186_violation",
        "threshold": True,
        "operator": "eq",
        "implication": "Contravention of Companies Act; penalty on company and officers in default; loans may be voidable",
    },
    {
        "id": "RF-11",
        "flag": "Frequent change of statutory auditors (3+ changes in 5 years)",
        "category": "financial",
        "severity": "high",
        "check_key": "auditor_changes_5yr",
        "threshold": 3,
        "operator": "gte",
        "implication": "Potential disagreements with auditors; governance concern; may indicate pressure to modify audit opinion",
    },
    {
        "id": "RF-12",
        "flag": "Cash transactions exceeding reporting thresholds",
        "category": "financial",
        "severity": "high",
        "check_key": "has_excessive_cash_transactions",
        "threshold": True,
        "operator": "eq",
        "implication": "PMLA/black money risk; Section 269ST violation (Rs 2 lakh cash receipt limit); potential benami transactions",
    },
    {
        "id": "RF-13",
        "flag": "Non-filing of GST returns for consecutive months",
        "category": "tax",
        "severity": "high",
        "check_key": "gst_nonfiling_months",
        "threshold": 2,
        "operator": "gte",
        "implication": "GSTIN may be cancelled/suspended; blocked from issuing tax invoices; ITC reversal risk for buyers",
    },
    {
        "id": "RF-14",
        "flag": "Significant contingent liabilities not adequately provisioned",
        "category": "financial",
        "severity": "high",
        "check_key": "has_unprovisioned_contingencies",
        "threshold": True,
        "operator": "eq",
        "implication": "Hidden liabilities affecting enterprise value; potential post-closing indemnity claims; balance sheet understated",
    },
    {
        "id": "RF-15",
        "flag": "Multiple show cause notices from regulatory authorities in past 2 years",
        "category": "regulatory",
        "severity": "high",
        "check_key": "regulatory_scn_count",
        "threshold": 3,
        "operator": "gte",
        "implication": "Pattern of non-compliance; enhanced regulatory scrutiny; potential license/registration revocation risk",
    },
    {
        "id": "RF-16",
        "flag": "Promoter shares pledged > 30% of total holding",
        "category": "financial",
        "severity": "high",
        "check_key": "promoter_pledge_pct",
        "threshold": 30,
        "operator": "gt",
        "implication": "Promoter leverage risk; invocation scenario = hostile takeover/change of control; SEBI disclosure non-compliance risk",
    },
    {
        "id": "RF-17",
        "flag": "Pending RERA complaints or non-compliance (real estate sector)",
        "category": "regulatory",
        "severity": "high",
        "check_key": "has_rera_issues",
        "threshold": True,
        "operator": "eq",
        "implication": "Project delivery risk; buyer refund liability; potential RERA registration revocation; reputational damage",
        "condition": "sector_real_estate",
    },
]


# =====================================================================
# CORE ENGINE FUNCTIONS
# =====================================================================

def generate_dd_checklist(
    transaction_type: str,
    target_type: str,
    sector: str,
    deal_value_crores: float,
    is_listed: bool = False,
    has_foreign_investment: bool = False,
    has_international_transactions: bool = False,
) -> dict:
    """
    Generate a comprehensive due diligence checklist tailored to the transaction.

    Args:
        transaction_type: One of TRANSACTION_TYPES
        target_type: One of TARGET_TYPES
        sector: One of SECTORS
        deal_value_crores: Deal value in crores INR
        is_listed: Whether the target is a listed entity
        has_foreign_investment: Whether there is foreign investment involved
        has_international_transactions: Whether the target has international transactions

    Returns:
        dict with 'legal', 'financial', 'tax' checklists and 'metadata'
    """
    logger.info(
        "Generating DD checklist: type=%s, target=%s, sector=%s, deal=%.2f Cr",
        transaction_type, target_type, sector, deal_value_crores,
    )

    # Build condition context for filtering
    conditions = set()
    if is_listed:
        conditions.add("listed_entity")
    if has_foreign_investment:
        conditions.add("foreign_investment")
    if has_international_transactions:
        conditions.add("international_transactions")
    if sector in ("NBFC", "banking"):
        conditions.add("sector_banking_nbfc")
    if sector in ("manufacturing", "infra"):
        conditions.add("manufacturing_infra")
    if sector in ("manufacturing", "pharma"):
        conditions.add("manufacturing_pharma")
    if sector in ("manufacturing", "infra", "real_estate"):
        conditions.add("manufacturing_infra_real_estate")
    if sector == "real_estate":
        conditions.add("sector_real_estate")
    if deal_value_crores > 50:
        conditions.add("import_export")
    if has_international_transactions:
        conditions.add("international_operations")

    def _filter_items(items: list) -> list:
        """Filter checklist items by target type and conditions."""
        result = []
        for item in items:
            # Check target type applicability
            applicable = item.get("applicable_to")
            if applicable and target_type not in applicable:
                continue
            # Check condition
            condition = item.get("condition")
            if condition and condition not in conditions:
                continue
            result.append(item)
        return result

    # Assemble legal checklist
    legal_checklist = {
        "corporate_structure": _filter_items(LEGAL_DD_CORPORATE_STRUCTURE),
        "regulatory_approvals": _filter_items(LEGAL_DD_REGULATORY),
        "litigation": _filter_items(LEGAL_DD_LITIGATION),
        "contracts": _filter_items(LEGAL_DD_CONTRACTS),
        "property": _filter_items(LEGAL_DD_PROPERTY),
        "employment": _filter_items(LEGAL_DD_EMPLOYMENT),
        "intellectual_property": _filter_items(LEGAL_DD_IP),
        "environmental": _filter_items(LEGAL_DD_ENVIRONMENTAL),
        "insurance": _filter_items(LEGAL_DD_INSURANCE),
    }

    # Financial and tax items apply universally (no target_type filter)
    financial_checklist = _filter_items(FINANCIAL_DD_ITEMS)
    tax_checklist = _filter_items(TAX_DD_ITEMS)

    # CCI notification assessment
    cci_required = _assess_cci_notification(deal_value_crores, sector)

    # Count totals
    legal_count = sum(len(v) for v in legal_checklist.values())
    financial_count = len(financial_checklist)
    tax_count = len(tax_checklist)

    return {
        "metadata": {
            "transaction_type": transaction_type,
            "target_type": target_type,
            "sector": sector,
            "deal_value_crores": deal_value_crores,
            "is_listed": is_listed,
            "has_foreign_investment": has_foreign_investment,
            "generated_at": datetime.now().isoformat(),
            "total_items": legal_count + financial_count + tax_count,
            "legal_items": legal_count,
            "financial_items": financial_count,
            "tax_items": tax_count,
            "cci_notification_required": cci_required,
        },
        "legal": legal_checklist,
        "financial": financial_checklist,
        "tax": tax_checklist,
        "cci_assessment": _build_cci_assessment(deal_value_crores, sector),
        "transaction_specific_notes": _get_transaction_notes(transaction_type, target_type, sector),
    }


def _assess_cci_notification(deal_value_crores: float, sector: str) -> bool:
    """Check if CCI combination notification is required under Section 5 Competition Act."""
    # Simplified check — actual analysis requires both parties' financials
    if deal_value_crores >= CCI_ASSET_THRESHOLD_CRORES:
        return True
    if deal_value_crores >= CCI_TURNOVER_THRESHOLD_CRORES:
        return True
    # De minimis exemption: target with assets < Rs 450Cr AND turnover < Rs 1,250Cr
    # Cannot determine without target financials, so flag for review
    if deal_value_crores >= 450:
        return True  # Conservative — needs detailed analysis
    return False


def _build_cci_assessment(deal_value_crores: float, sector: str) -> dict:
    """Build CCI notification assessment details."""
    return {
        "deal_value_crores": deal_value_crores,
        "asset_threshold_crores": CCI_ASSET_THRESHOLD_CRORES,
        "turnover_threshold_crores": CCI_TURNOVER_THRESHOLD_CRORES,
        "group_asset_threshold_crores": CCI_ASSET_THRESHOLD_GROUP_CRORES,
        "group_turnover_threshold_crores": CCI_TURNOVER_THRESHOLD_GROUP_CRORES,
        "de_minimis_asset_crores": 450,
        "de_minimis_turnover_crores": 1250,
        "notification_likely": deal_value_crores >= 450,
        "green_channel_eligible": sector not in ("banking", "NBFC", "telecom", "media"),
        "standstill_obligation": "Parties must not consummate combination before CCI approval (Section 6(2A)) — 150 working days deemed approval",
        "reference": "Competition Act 2002, Section 5, 6; CCI Combination Regulations 2011",
    }


def _get_transaction_notes(transaction_type: str, target_type: str, sector: str) -> list:
    """Return transaction-specific DD notes and considerations."""
    notes = []

    if transaction_type == "acquisition":
        notes.extend([
            "Obtain seller representations and warranties covering pre-closing period",
            "Assess stamp duty on share transfer (state-wise variation; unlisted shares generally 0.015% buyer + 0.015% seller under Indian Stamp Act post-2020 amendment)",
            "For asset purchase: Section 281 IT Act tax clearance certificate required; GST on slump sale (if applicable post-2020 amendment)",
            "Verify Section 56(2)(x) implications if shares acquired below FMV",
        ])
    elif transaction_type == "merger":
        notes.extend([
            "NCLT scheme of arrangement process under Section 230-232 Companies Act 2013",
            "Appointed date vs. effective date — tax implications for gap period",
            "Section 2(1B) IT Act — merger must qualify as 'amalgamation' for tax neutrality",
            "Stamp duty on merger: varies by state; follow state-specific rates on authorized capital increase",
            "SEBI LODR Regulation 37 — NoC from stock exchanges for listed entities",
        ])
    elif transaction_type == "demerger":
        notes.extend([
            "Section 2(19AA) IT Act — conditions for tax-neutral demerger",
            "Proportionate transfer of assets/liabilities of undertaking being demerged",
            "Shareholder consideration must be in shares of resulting company (not cash for tax neutrality)",
            "GST implications — transfer of going concern exemption under Entry 2 Schedule II read with Notification 12/2017",
        ])
    elif transaction_type == "joint_venture":
        notes.extend([
            "JV agreement must address: shareholding, board nomination, reserved matters, exit mechanism, deadlock resolution",
            "Section 186 limits applicable for investment in JV company",
            "FEMA compliance if JV involves foreign partner — sectoral caps, pricing guidelines, reporting obligations",
            "Competition Act assessment — JV may constitute a combination if thresholds are met",
        ])
    elif transaction_type == "investment":
        notes.extend([
            "Valuation per Rule 11UA (IT Act) and Section 62(1)(c) / FEMA pricing guidelines",
            "Section 56(2)(x) — deemed income if shares issued below FMV to resident",
            "FEMA 20(R) — pricing floor/cap for shares issued to non-residents",
            "Section 186 investment limit compliance for investee if investor is a company",
        ])

    # Sector-specific notes
    if sector == "pharma":
        notes.append("Review Drug Controller General of India (DCGI) approvals, CDSCO compliance, WHO-GMP certifications, pending FDA/ANDA approvals")
    elif sector == "NBFC":
        notes.append("RBI prior approval required for change in control/management of NBFC under Section 45-IA of RBI Act; asset classification and provisioning norms; Fair Practices Code compliance")
    elif sector == "real_estate":
        notes.append("RERA registration for ongoing projects; buyer agreements review; unsold inventory valuation; land title chain verification; FSI/FAR compliance; municipal approvals")
    elif sector == "IT":
        notes.append("Review STPI/SEZ approvals, software export compliance, data privacy (DPDP Act 2023) compliance, open source license audit, SaaS subscription terms")
    elif sector == "banking":
        notes.append("RBI approval mandatory for acquisition of 5%+ of banking company shares; Section 12B Banking Regulation Act; NPA portfolio quality; CRAR minimum 9%")
    elif sector == "infra":
        notes.append("Review PPP/concession agreements; government approvals (NH Act, Land Acquisition); environmental clearances; NHAI/AAI/port trust compliance")
    elif sector == "fintech":
        notes.append("RBI PA/PPI/NBFC-P2P license; digital lending guidelines compliance; data localization requirements; DPDP Act 2023 compliance")

    return notes


# =====================================================================
# RED FLAG DETECTOR
# =====================================================================

def detect_red_flags(financial_data: dict, compliance_data: dict) -> dict:
    """
    Detect red flags from financial and compliance data.

    Args:
        financial_data: dict with keys matching RED_FLAG_RULES check_keys
            Example keys: revenue_concentration_pct, related_party_revenue_pct,
            has_qualified_audit, tax_demand_to_networth_pct, etc.
        compliance_data: dict with additional compliance-related flags

    Returns:
        dict with 'flags' list, 'summary' counts, and 'category_scores'
    """
    logger.info("Running red flag detection")

    combined_data = {**financial_data, **compliance_data}
    triggered_flags = []

    for rule in RED_FLAG_RULES:
        check_key = rule["check_key"]
        if check_key not in combined_data:
            continue

        value = combined_data[check_key]
        threshold = rule["threshold"]
        operator = rule["operator"]

        triggered = False
        if operator == "gt" and isinstance(value, (int, float)):
            triggered = value > threshold
        elif operator == "gte" and isinstance(value, (int, float)):
            triggered = value >= threshold
        elif operator == "lt" and isinstance(value, (int, float)):
            triggered = value < threshold
        elif operator == "eq":
            triggered = value == threshold

        # Check condition applicability
        condition = rule.get("condition")
        if condition and condition not in combined_data.get("conditions", set()):
            continue

        if triggered:
            triggered_flags.append({
                "id": rule["id"],
                "flag": rule["flag"],
                "category": rule["category"],
                "severity": rule["severity"],
                "actual_value": value,
                "threshold": threshold,
                "implication": rule["implication"],
            })

    # Categorize flags
    category_flags = {}
    for flag in triggered_flags:
        cat = flag["category"]
        if cat not in category_flags:
            category_flags[cat] = []
        category_flags[cat].append(flag)

    # Score each category
    category_scores = {}
    for cat, flags in category_flags.items():
        count = len(flags)
        if count <= 2:
            category_scores[cat] = {"status": "GREEN", "count": count, "label": "Low risk"}
        elif count <= 5:
            category_scores[cat] = {"status": "YELLOW", "count": count, "label": "Moderate risk — needs attention"}
        else:
            category_scores[cat] = {"status": "RED", "count": count, "label": "High risk — critical review required"}

    # Overall severity
    critical_count = sum(1 for f in triggered_flags if f["severity"] == "critical")
    high_count = sum(1 for f in triggered_flags if f["severity"] == "high")
    total_count = len(triggered_flags)

    if critical_count >= 3 or total_count >= 8:
        overall_status = "RED"
    elif critical_count >= 1 or total_count >= 4:
        overall_status = "YELLOW"
    else:
        overall_status = "GREEN"

    return {
        "flags": triggered_flags,
        "summary": {
            "total_flags": total_count,
            "critical_flags": critical_count,
            "high_flags": high_count,
            "overall_status": overall_status,
        },
        "category_scores": category_scores,
    }


# =====================================================================
# COMPLIANCE SCORING ENGINE
# =====================================================================

# Weights for each DD category in overall score
CATEGORY_WEIGHTS = {
    "legal": 0.30,
    "financial": 0.30,
    "tax": 0.20,
    "regulatory": 0.20,
}

# Risk rating thresholds
RISK_RATINGS = [
    {"min": 80, "max": 100, "rating": "Low", "recommendation": "Proceed — standard conditions precedent"},
    {"min": 60, "max": 79, "rating": "Medium", "recommendation": "Proceed with caution — enhanced indemnities and conditions recommended"},
    {"min": 40, "max": 59, "rating": "High", "recommendation": "Significant concerns — consider price adjustment, escrow, or restructuring"},
    {"min": 0, "max": 39, "rating": "Critical", "recommendation": "Serious impediments — consider walking away or fundamental deal restructuring"},
]


def compute_compliance_score(
    checklist_results: dict,
    red_flag_results: dict,
) -> dict:
    """
    Compute comprehensive DD compliance scores.

    Args:
        checklist_results: dict with category keys, each containing items with
            'status' field: 'compliant', 'non_compliant', 'partial', 'not_reviewed', 'not_applicable'
        red_flag_results: output from detect_red_flags()

    Returns:
        dict with overall_score, category_scores, risk_rating, recommendation
    """
    logger.info("Computing compliance score")

    category_scores = {}

    # Score each category
    for category in ("legal", "financial", "tax", "regulatory"):
        items = _extract_category_items(checklist_results, category)
        if not items:
            category_scores[category] = {
                "score": 100,
                "total_items": 0,
                "compliant": 0,
                "non_compliant": 0,
                "partial": 0,
                "not_reviewed": 0,
                "not_applicable": 0,
                "compliance_rate": 100.0,
            }
            continue

        compliant = sum(1 for i in items if i.get("status") == "compliant")
        non_compliant = sum(1 for i in items if i.get("status") == "non_compliant")
        partial = sum(1 for i in items if i.get("status") == "partial")
        not_reviewed = sum(1 for i in items if i.get("status") == "not_reviewed")
        not_applicable = sum(1 for i in items if i.get("status") == "not_applicable")

        reviewable = len(items) - not_applicable
        if reviewable == 0:
            base_score = 100
        else:
            # Compliant = full marks, partial = half marks, non-compliant = 0, not_reviewed = 0
            points = (compliant * 1.0 + partial * 0.5) / reviewable
            base_score = round(points * 100, 1)

        # Apply red flag penalty to this category
        cat_flags = red_flag_results.get("category_scores", {}).get(category, {})
        flag_count = cat_flags.get("count", 0)
        penalty = min(flag_count * 5, 30)  # Max 30 point penalty from red flags
        adjusted_score = max(0, base_score - penalty)

        category_scores[category] = {
            "score": adjusted_score,
            "base_score": base_score,
            "red_flag_penalty": penalty,
            "total_items": len(items),
            "compliant": compliant,
            "non_compliant": non_compliant,
            "partial": partial,
            "not_reviewed": not_reviewed,
            "not_applicable": not_applicable,
            "compliance_rate": round((compliant / reviewable * 100) if reviewable else 100, 1),
        }

    # Overall weighted score
    overall_score = sum(
        category_scores.get(cat, {}).get("score", 0) * weight
        for cat, weight in CATEGORY_WEIGHTS.items()
    )
    overall_score = round(overall_score, 1)

    # Risk rating
    risk_rating = "Critical"
    recommendation = "Serious impediments identified"
    go_no_go = "NO-GO"
    conditions = []

    for rating in RISK_RATINGS:
        if rating["min"] <= overall_score <= rating["max"]:
            risk_rating = rating["rating"]
            recommendation = rating["recommendation"]
            break

    if overall_score >= 80:
        go_no_go = "GO"
        conditions = ["Standard representations and warranties", "Customary conditions precedent"]
    elif overall_score >= 60:
        go_no_go = "CONDITIONAL GO"
        conditions = _generate_conditions(checklist_results, red_flag_results, category_scores)
    elif overall_score >= 40:
        go_no_go = "CONDITIONAL GO (HIGH RISK)"
        conditions = _generate_conditions(checklist_results, red_flag_results, category_scores)
        conditions.append("Consider price adjustment / escrow mechanism for identified risks")
        conditions.append("Enhanced indemnity package with extended survival period")
    else:
        go_no_go = "NO-GO"
        conditions = [
            "Fundamental deal restructuring required before proceeding",
            "Independent forensic audit recommended",
            "Consider walking away from the transaction",
        ]

    return {
        "overall_score": overall_score,
        "category_scores": category_scores,
        "risk_rating": risk_rating,
        "recommendation": recommendation,
        "go_no_go": go_no_go,
        "conditions": conditions,
        "generated_at": datetime.now().isoformat(),
    }


def _extract_category_items(checklist_results: dict, category: str) -> list:
    """Extract all items for a given category from nested checklist results."""
    items = []
    if category == "legal":
        legal = checklist_results.get("legal", {})
        if isinstance(legal, dict):
            for subcategory_items in legal.values():
                if isinstance(subcategory_items, list):
                    items.extend(subcategory_items)
        elif isinstance(legal, list):
            items.extend(legal)
    elif category in ("financial", "tax"):
        cat_items = checklist_results.get(category, [])
        if isinstance(cat_items, list):
            items.extend(cat_items)
    elif category == "regulatory":
        # Regulatory items come from legal.regulatory_approvals
        legal = checklist_results.get("legal", {})
        if isinstance(legal, dict):
            reg_items = legal.get("regulatory_approvals", [])
            items.extend(reg_items)
    return items


def _generate_conditions(
    checklist_results: dict,
    red_flag_results: dict,
    category_scores: dict,
) -> list:
    """Generate conditions precedent based on DD findings."""
    conditions = []

    # Non-compliant items generate specific conditions
    for category in ("legal", "financial", "tax"):
        items = _extract_category_items(checklist_results, category)
        non_compliant_items = [i for i in items if i.get("status") == "non_compliant"]
        for item in non_compliant_items[:5]:  # Top 5 per category
            conditions.append(
                f"Resolve {category} issue: {item.get('item', 'Unknown item')} — "
                f"must be compliant before closing"
            )

    # Red flag-driven conditions
    flags = red_flag_results.get("flags", [])
    critical_flags = [f for f in flags if f["severity"] == "critical"]
    for flag in critical_flags:
        conditions.append(
            f"Address critical red flag: {flag['flag']} — "
            f"specific indemnity required"
        )

    # Score-driven conditions
    for cat, score_data in category_scores.items():
        if score_data.get("score", 100) < 50:
            conditions.append(
                f"{cat.capitalize()} score below threshold ({score_data['score']}/100) — "
                f"detailed remediation plan required as CP"
            )

    if not conditions:
        conditions.append("Standard conditions precedent apply")

    return conditions


# =====================================================================
# DD REPORT GENERATOR
# =====================================================================

def generate_dd_report(
    checklist_results: dict,
    red_flag_results: Optional[dict] = None,
    compliance_score: Optional[dict] = None,
    metadata: Optional[dict] = None,
) -> str:
    """
    Generate a comprehensive markdown DD report.

    Args:
        checklist_results: Completed checklist with status for each item
        red_flag_results: Output from detect_red_flags() (optional)
        compliance_score: Output from compute_compliance_score() (optional)
        metadata: Transaction metadata from generate_dd_checklist() (optional)

    Returns:
        Formatted markdown string for the DD report
    """
    logger.info("Generating DD report")

    report_lines = []
    now = datetime.now().strftime("%d %B %Y")

    # ── Title and Executive Summary ──────────────────────────────
    report_lines.append("# Due Diligence Report")
    report_lines.append("")
    report_lines.append(f"**Date:** {now}")
    report_lines.append("")

    if metadata:
        report_lines.append(f"**Transaction Type:** {metadata.get('transaction_type', 'N/A').replace('_', ' ').title()}")
        report_lines.append(f"**Target Type:** {metadata.get('target_type', 'N/A').replace('_', ' ').title()}")
        report_lines.append(f"**Sector:** {metadata.get('sector', 'N/A')}")
        deal_val = metadata.get('deal_value_crores', 0)
        report_lines.append(f"**Indicative Deal Value:** Rs {deal_val:,.2f} Crores")
        report_lines.append(f"**Total Checklist Items:** {metadata.get('total_items', 0)}")
        report_lines.append("")

    # ── Executive Summary ────────────────────────────────────────
    report_lines.append("## Executive Summary")
    report_lines.append("")

    if compliance_score:
        overall = compliance_score.get("overall_score", 0)
        rating = compliance_score.get("risk_rating", "N/A")
        go_no_go = compliance_score.get("go_no_go", "N/A")
        recommendation = compliance_score.get("recommendation", "N/A")

        report_lines.append(f"**Overall DD Score:** {overall}/100")
        report_lines.append(f"**Risk Rating:** {rating}")
        report_lines.append(f"**Recommendation:** {go_no_go}")
        report_lines.append(f"**Summary:** {recommendation}")
        report_lines.append("")

        # Category-wise summary table
        report_lines.append("### Category-Wise Scores")
        report_lines.append("")
        report_lines.append("| Category | Score | Compliance Rate | Items | Non-Compliant |")
        report_lines.append("|----------|-------|-----------------|-------|---------------|")
        for cat in ("legal", "financial", "tax", "regulatory"):
            cat_data = compliance_score.get("category_scores", {}).get(cat, {})
            report_lines.append(
                f"| {cat.capitalize()} | {cat_data.get('score', 'N/A')}/100 | "
                f"{cat_data.get('compliance_rate', 'N/A')}% | "
                f"{cat_data.get('total_items', 0)} | "
                f"{cat_data.get('non_compliant', 0)} |"
            )
        report_lines.append("")

    # ── Red Flag Summary ─────────────────────────────────────────
    if red_flag_results:
        report_lines.append("## Red Flag Summary")
        report_lines.append("")

        summary = red_flag_results.get("summary", {})
        report_lines.append(f"**Overall Status:** {summary.get('overall_status', 'N/A')}")
        report_lines.append(f"**Total Flags:** {summary.get('total_flags', 0)}")
        report_lines.append(f"**Critical:** {summary.get('critical_flags', 0)}")
        report_lines.append(f"**High:** {summary.get('high_flags', 0)}")
        report_lines.append("")

        flags = red_flag_results.get("flags", [])
        if flags:
            report_lines.append("| ID | Flag | Category | Severity | Implication |")
            report_lines.append("|----|------|----------|----------|-------------|")
            for flag in flags:
                report_lines.append(
                    f"| {flag['id']} | {flag['flag']} | "
                    f"{flag['category'].capitalize()} | "
                    f"**{flag['severity'].upper()}** | "
                    f"{flag['implication'][:80]}{'...' if len(flag['implication']) > 80 else ''} |"
                )
            report_lines.append("")

    # ── Detailed Findings by Category ────────────────────────────
    report_lines.append("## Detailed Findings")
    report_lines.append("")

    # Legal findings
    legal = checklist_results.get("legal", {})
    if isinstance(legal, dict) and legal:
        report_lines.append("### Legal Due Diligence")
        report_lines.append("")

        subcategory_labels = {
            "corporate_structure": "Corporate Structure",
            "regulatory_approvals": "Regulatory Approvals",
            "litigation": "Litigation & Disputes",
            "contracts": "Material Contracts",
            "property": "Property & Real Estate",
            "employment": "Employment & Labour",
            "intellectual_property": "Intellectual Property",
            "environmental": "Environmental",
            "insurance": "Insurance",
        }

        for subcat, label in subcategory_labels.items():
            items = legal.get(subcat, [])
            if not items:
                continue
            report_lines.append(f"#### {label}")
            report_lines.append("")
            report_lines.append("| ID | Item | Priority | Status | Remarks |")
            report_lines.append("|----|------|----------|--------|---------|")
            for item in items:
                status = item.get("status", "not_reviewed")
                status_emoji = _status_indicator(status)
                remarks = item.get("remarks", item.get("description", "")[:60])
                report_lines.append(
                    f"| {item['id']} | {item['item'][:50]}{'...' if len(item['item']) > 50 else ''} | "
                    f"{item['priority'].upper()} | "
                    f"{status_emoji} {status.replace('_', ' ').title()} | "
                    f"{remarks[:60]}{'...' if len(str(remarks)) > 60 else ''} |"
                )
            report_lines.append("")

    # Financial findings
    financial = checklist_results.get("financial", [])
    if financial:
        report_lines.append("### Financial Due Diligence")
        report_lines.append("")
        report_lines.append("| ID | Item | Priority | Status | Remarks |")
        report_lines.append("|----|------|----------|--------|---------|")
        for item in financial:
            status = item.get("status", "not_reviewed")
            status_emoji = _status_indicator(status)
            remarks = item.get("remarks", item.get("description", "")[:60])
            report_lines.append(
                f"| {item['id']} | {item['item'][:50]}{'...' if len(item['item']) > 50 else ''} | "
                f"{item['priority'].upper()} | "
                f"{status_emoji} {status.replace('_', ' ').title()} | "
                f"{remarks[:60]}{'...' if len(str(remarks)) > 60 else ''} |"
            )
        report_lines.append("")

    # Tax findings
    tax = checklist_results.get("tax", [])
    if tax:
        report_lines.append("### Tax Due Diligence")
        report_lines.append("")
        report_lines.append("| ID | Item | Priority | Status | Remarks |")
        report_lines.append("|----|------|----------|--------|---------|")
        for item in tax:
            status = item.get("status", "not_reviewed")
            status_emoji = _status_indicator(status)
            remarks = item.get("remarks", item.get("description", "")[:60])
            report_lines.append(
                f"| {item['id']} | {item['item'][:50]}{'...' if len(item['item']) > 50 else ''} | "
                f"{item['priority'].upper()} | "
                f"{status_emoji} {status.replace('_', ' ').title()} | "
                f"{remarks[:60]}{'...' if len(str(remarks)) > 60 else ''} |"
            )
        report_lines.append("")

    # ── Conditions Precedent ─────────────────────────────────────
    if compliance_score and compliance_score.get("conditions"):
        report_lines.append("## Conditions Precedent (Recommended)")
        report_lines.append("")
        for i, condition in enumerate(compliance_score["conditions"], 1):
            report_lines.append(f"{i}. {condition}")
        report_lines.append("")

    # ── Representations & Warranties Suggestions ─────────────────
    report_lines.append("## Representations & Warranties — Suggested Protections")
    report_lines.append("")
    rw_suggestions = _generate_rw_suggestions(checklist_results, red_flag_results)
    for suggestion in rw_suggestions:
        report_lines.append(f"- **{suggestion['area']}:** {suggestion['suggestion']}")
    report_lines.append("")

    # ── Regulatory References ────────────────────────────────────
    report_lines.append("## Key Regulatory References")
    report_lines.append("")
    report_lines.append("| Statute | Relevant Provisions |")
    report_lines.append("|---------|---------------------|")
    report_lines.append("| Companies Act 2013 | Sections 2(19AA), 2(1B), 56(2)(x), 62, 77, 185, 186, 188, 230-232 |")
    report_lines.append("| Income Tax Act 1961 | Sections 9, 47, 50CA, 56(2)(x), 72-79, 92-92F, 115JB, 143, 195 |")
    report_lines.append("| CGST Act 2017 | Sections 16-18, 37, 39, 44, 73, 74, 171 |")
    report_lines.append("| FEMA 1999 | FDI Policy, FEMA 20(R), FC-GPR, FC-TRS |")
    report_lines.append("| Competition Act 2002 | Sections 5, 6 (combination thresholds and notification) |")
    report_lines.append("| SEBI Regulations | LODR 2015, SAST 2011, ICDR 2018, SBEB&SE 2021 |")
    report_lines.append("| IBC 2016 | Sections 7, 9, 29A (resolution applicant eligibility) |")
    report_lines.append("| Indian Stamp Act 1899 | Share transfer stamp duty; state-wise variation |")
    report_lines.append("")

    # ── Disclaimer ───────────────────────────────────────────────
    report_lines.append("---")
    report_lines.append("")
    report_lines.append("*This report is generated based on the information and documents provided. "
                        "It does not constitute legal advice and should be read in conjunction with "
                        "the detailed working papers. All findings are subject to verification "
                        "against original documents and regulatory records.*")

    return "\n".join(report_lines)


def _status_indicator(status: str) -> str:
    """Return a text-based status indicator for markdown tables."""
    indicators = {
        "compliant": "[OK]",
        "non_compliant": "[FAIL]",
        "partial": "[PARTIAL]",
        "not_reviewed": "[PENDING]",
        "not_applicable": "[N/A]",
    }
    return indicators.get(status, "[?]")


def _generate_rw_suggestions(
    checklist_results: dict,
    red_flag_results: Optional[dict] = None,
) -> list:
    """Generate R&W suggestions based on DD findings."""
    suggestions = [
        {
            "area": "Corporate Authority",
            "suggestion": "Target is duly incorporated and validly existing; board and shareholder approvals obtained for the transaction",
        },
        {
            "area": "Title to Assets",
            "suggestion": "Target has good and marketable title to all assets; no undisclosed encumbrances, liens, or charges",
        },
        {
            "area": "Financial Statements",
            "suggestion": "Audited financial statements present a true and fair view in accordance with Ind AS; no undisclosed liabilities",
        },
        {
            "area": "Tax Compliance",
            "suggestion": "All tax returns filed; no pending demands except as disclosed; adequate provisions for all tax liabilities; no tax avoidance arrangements",
        },
        {
            "area": "Litigation",
            "suggestion": "No pending or threatened litigation except as disclosed in the Disclosure Letter; adequate provisions for contingent liabilities",
        },
        {
            "area": "Regulatory Compliance",
            "suggestion": "Target holds all material licenses, permits, and approvals; no show cause notices or regulatory investigations except as disclosed",
        },
        {
            "area": "Contracts",
            "suggestion": "No material contract contains change of control termination trigger that would be activated by the transaction (except as disclosed)",
        },
        {
            "area": "Employment",
            "suggestion": "Full compliance with PF, ESI, gratuity, bonus, and minimum wages obligations; no pending labour disputes except as disclosed",
        },
        {
            "area": "Intellectual Property",
            "suggestion": "Target owns or has valid licenses for all IP used in business; no infringement claims (received or anticipated)",
        },
        {
            "area": "Environmental",
            "suggestion": "All environmental clearances, PCB consents are valid and in force; no NGT proceedings or environmental liability",
        },
        {
            "area": "Related Party Transactions",
            "suggestion": "All RPTs conducted at arm's length with proper Section 188 approvals; SEBI LODR Regulation 23 compliance (if listed)",
        },
        {
            "area": "Data Protection",
            "suggestion": "Compliance with IT Act 2000, SPDI Rules 2011, and DPDP Act 2023 (as applicable); no data breaches in past 3 years",
        },
    ]

    # Add flag-specific R&W suggestions
    if red_flag_results:
        flags = red_flag_results.get("flags", [])
        for flag in flags:
            if flag["severity"] == "critical":
                if "fraud" in flag["flag"].lower():
                    suggestions.append({
                        "area": "No Fraud",
                        "suggestion": "No fraud, misrepresentation, or material irregularity in financial statements or business conduct; specific indemnity for fraud-related losses with extended survival period",
                    })
                if "ibc" in flag["flag"].lower() or "nclt" in flag["flag"].lower():
                    suggestions.append({
                        "area": "Insolvency",
                        "suggestion": "No pending or threatened IBC/insolvency proceedings; no NCLT applications; target is solvent and able to pay debts as they fall due",
                    })
                if "fema" in flag["flag"].lower() or "ed" in flag["flag"].lower():
                    suggestions.append({
                        "area": "FEMA Compliance",
                        "suggestion": "Full FEMA compliance for all foreign exchange transactions; no pending ED investigations or FEMA adjudication proceedings; specific indemnity for FEMA violations",
                    })

    return suggestions


# =====================================================================
# SECTOR-SPECIFIC DD SUPPLEMENTS
# =====================================================================

SECTOR_SPECIFIC_ITEMS = {
    "pharma": [
        {"id": "S-PH-01", "item": "Drug manufacturing licenses (state-wise)", "reference": "Drugs and Cosmetics Act 1940"},
        {"id": "S-PH-02", "item": "CDSCO approvals for each product", "reference": "D&C Act; New Drugs and Clinical Trials Rules 2019"},
        {"id": "S-PH-03", "item": "WHO-GMP / EU-GMP / USFDA inspections and status", "reference": "International regulatory"},
        {"id": "S-PH-04", "item": "ANDA/DMF filings (if exporting to US)", "reference": "USFDA"},
        {"id": "S-PH-05", "item": "Schedule H / H1 drug inventory and compliance", "reference": "D&C Act Schedule H"},
        {"id": "S-PH-06", "item": "Clinical trial data and regulatory submissions", "reference": "New Drugs and Clinical Trials Rules 2019"},
        {"id": "S-PH-07", "item": "Drug price control (DPCO/NPPA) compliance for scheduled formulations", "reference": "DPCO 2013; Essential Commodities Act 1955"},
    ],
    "NBFC": [
        {"id": "S-NB-01", "item": "RBI Certificate of Registration (CoR) and classification", "reference": "RBI Act Section 45-IA"},
        {"id": "S-NB-02", "item": "CRAR / Capital adequacy computation and compliance", "reference": "RBI Master Direction DNBR"},
        {"id": "S-NB-03", "item": "NPA classification and provisioning (IRAC norms)", "reference": "RBI IRAC Norms"},
        {"id": "S-NB-04", "item": "Fair Practices Code (FPC) compliance", "reference": "RBI Fair Practices Code"},
        {"id": "S-NB-05", "item": "ALM (Asset Liability Management) statement", "reference": "RBI ALM Guidelines"},
        {"id": "S-NB-06", "item": "Scale-based regulation (SBR) classification — base/middle/upper layer", "reference": "RBI SBR Framework 2022"},
        {"id": "S-NB-07", "item": "Digital lending guidelines compliance", "reference": "RBI Digital Lending Guidelines 2022"},
    ],
    "real_estate": [
        {"id": "S-RE-01", "item": "RERA registrations for all ongoing projects", "reference": "RERA 2016, Section 3"},
        {"id": "S-RE-02", "item": "Buyer agreements — standard terms and deviation analysis", "reference": "RERA 2016, Section 13"},
        {"id": "S-RE-03", "item": "Unsold inventory valuation and absorption rate", "reference": "Ind AS 115; RERA"},
        {"id": "S-RE-04", "item": "Land bank — title, zoning, development permissions", "reference": "State development authority regulations"},
        {"id": "S-RE-05", "item": "Joint development agreements (JDA) — revenue sharing, construction obligations", "reference": "Contractual; GST on JDA"},
        {"id": "S-RE-06", "item": "FSI/FAR/TDR utilization and compliance", "reference": "State DC Regulations"},
    ],
    "IT": [
        {"id": "S-IT-01", "item": "STPI / SEZ registration and export obligation compliance", "reference": "STPI Guidelines; SEZ Act 2005"},
        {"id": "S-IT-02", "item": "Open source software license audit (GPL, LGPL, MIT, Apache)", "reference": "OSS license terms"},
        {"id": "S-IT-03", "item": "Data protection compliance — IT Act, SPDI Rules, DPDP Act 2023", "reference": "IT Act 2000, Section 43A; DPDP Act 2023"},
        {"id": "S-IT-04", "item": "SaaS subscription agreements and customer data handling", "reference": "IT Act 2000; DPDP Act 2023"},
        {"id": "S-IT-05", "item": "Source code escrow arrangements", "reference": "Contractual"},
        {"id": "S-IT-06", "item": "Cybersecurity audit and CERT-In compliance", "reference": "CERT-In Directions April 2022"},
    ],
    "banking": [
        {"id": "S-BK-01", "item": "RBI license and branch authorization", "reference": "Banking Regulation Act 1949, Section 22"},
        {"id": "S-BK-02", "item": "CRR / SLR maintenance compliance", "reference": "RBI Act 1934, Section 42; Banking Regulation Act Section 24"},
        {"id": "S-BK-03", "item": "Priority sector lending targets achievement", "reference": "RBI PSL Master Direction"},
        {"id": "S-BK-04", "item": "KYC/AML/CFT compliance — RBI inspection findings", "reference": "PML Act 2002; RBI KYC Directions"},
        {"id": "S-BK-05", "item": "Basel III compliance — capital adequacy, LCR, NSFR", "reference": "RBI Basel III Framework"},
        {"id": "S-BK-06", "item": "Prompt Corrective Action (PCA) framework status", "reference": "RBI PCA Framework"},
    ],
    "infra": [
        {"id": "S-IN-01", "item": "Concession/PPP agreements — term, obligations, termination", "reference": "PPP/concession-specific"},
        {"id": "S-IN-02", "item": "Government approvals — NH Act, land acquisition, environment", "reference": "RFCTLARR Act 2013; NH Act 1956"},
        {"id": "S-IN-03", "item": "Toll collection rights and revenue sharing mechanism", "reference": "Concession agreement"},
        {"id": "S-IN-04", "item": "EPC contractor agreements and construction progress", "reference": "Contractual"},
        {"id": "S-IN-05", "item": "Arbitration claims with government authorities (NHAI, AAI, etc.)", "reference": "Arbitration and Conciliation Act 1996"},
    ],
    "fintech": [
        {"id": "S-FT-01", "item": "RBI PA / PPI / NBFC-P2P authorization", "reference": "Payment and Settlement Systems Act 2007; RBI Master Directions"},
        {"id": "S-FT-02", "item": "Digital lending guidelines compliance (LSP/DLA framework)", "reference": "RBI Digital Lending Guidelines 2022"},
        {"id": "S-FT-03", "item": "Data localization — payment data storage in India", "reference": "RBI data localization circular 2018"},
        {"id": "S-FT-04", "item": "UPI/NPCI partnership and compliance", "reference": "NPCI guidelines"},
        {"id": "S-FT-05", "item": "DPDP Act 2023 compliance — consent, data fiduciary obligations", "reference": "DPDP Act 2023"},
    ],
}


def get_sector_specific_checklist(sector: str) -> list:
    """Return sector-specific DD checklist items."""
    return SECTOR_SPECIFIC_ITEMS.get(sector, [])


# =====================================================================
# VALUATION CROSS-CHECK PARAMETERS
# =====================================================================

VALUATION_PARAMETERS = {
    "dcf_required_for": ["acquisition", "merger", "investment"],
    "rule_11ua_required_for": ["private_company", "llp"],
    "sebi_icdr_valuation_for": ["public_company"],
    "fema_valuation_method": {
        "inbound": "DCF (floor price) for equity; NAV for preference; SEBI pricing for listed",
        "outbound": "Any internationally accepted methodology (ceiling price)",
    },
    "registered_valuer_required": True,
    "registered_valuer_reference": "Companies Act 2013, Section 247; Companies (Registered Valuers and Valuation) Rules 2017",
    "income_tax_valuation_methods": [
        "Rule 11UA — NAV method for unquoted equity shares",
        "Rule 11UAA — for share transfer by non-residents",
        "DCF method — available for shares issued to residents under Section 56(2)(x)",
    ],
}


# =====================================================================
# HELPER — QUICK DD SUMMARY FOR AI CONTEXT
# =====================================================================

def get_dd_context_summary(
    transaction_type: str,
    target_type: str,
    sector: str,
    deal_value_crores: float,
) -> str:
    """
    Return a concise text summary for AI engine context injection.
    Used when the assistant needs DD context for a user query.
    """
    checklist = generate_dd_checklist(
        transaction_type=transaction_type,
        target_type=target_type,
        sector=sector,
        deal_value_crores=deal_value_crores,
    )

    meta = checklist["metadata"]
    notes = checklist.get("transaction_specific_notes", [])
    cci = checklist.get("cci_assessment", {})

    summary_parts = [
        f"DD Checklist Generated: {meta['total_items']} total items "
        f"({meta['legal_items']} legal, {meta['financial_items']} financial, {meta['tax_items']} tax).",
        f"Transaction: {transaction_type.replace('_', ' ').title()} of {target_type.replace('_', ' ').title()} in {sector} sector.",
        f"Deal Value: Rs {deal_value_crores:,.2f} Crores.",
        f"CCI Notification: {'Likely required' if meta['cci_notification_required'] else 'Likely not required (below de minimis)'}.",
    ]

    if notes:
        summary_parts.append("Key considerations: " + "; ".join(notes[:3]))

    sector_items = get_sector_specific_checklist(sector)
    if sector_items:
        summary_parts.append(
            f"Sector-specific items ({sector}): {len(sector_items)} additional checks identified."
        )

    return " ".join(summary_parts)
