"""
Harvey.ai / Ivo.ai-style Playbooks for Indian CA/Lawyer workflows.

Each playbook is a curated prompt + pipeline that produces a specific high-value deliverable:
- Contract drafting (NDA, SPA, SHA, JV, Service Agreement, Employment, Lease, Franchise)
- Contract redlining with risk matrix
- Due diligence extraction
- Chronology builder
- Notice reply drafting
- Ratio analysis
- Reconciliations (GST, TDS, Payroll, Bank)
- Ageing schedules with red flags
- Advance tax trackers
- Tax computation (old vs new regime)

These playbooks bake in years of Big 4 / top law firm practice so the LLM doesn't need to
rediscover standard approaches each time.
"""

# ==================== CONTRACT DRAFTING PLAYBOOKS ====================

NDA_PLAYBOOK = """# NDA Drafting Playbook (Indian Law)

Generate a Non-Disclosure Agreement that would pass senior partner review at a top-tier firm.

## MANDATORY CLAUSES (include ALL unless user excludes)
1. **Parties & Recitals** — full legal names, registered addresses, CIN if company, PAN
2. **Definition of Confidential Information** — broad + technical/business/personal data + legally privileged info
3. **Permitted Purpose** — narrowly defined, linked to specific transaction/discussion
4. **Obligations of Receiving Party**:
   - Use only for Permitted Purpose
   - Standard of care: same as own confidential info, NO LESS than reasonable care
   - Restricted access (need-to-know basis)
   - Flow-down to representatives/affiliates with back-to-back undertaking
5. **Exclusions from Confidentiality**:
   - Already in public domain (burden on Receiving Party)
   - Lawfully received from third party without restriction
   - Independently developed (with contemporaneous written evidence)
   - Disclosed with prior written consent
6. **Legal/Regulatory Disclosure Carve-out** — prompt notice + minimum necessary + reasonable assistance to quash
7. **Return/Destruction** — on demand or at termination; retain backup copies subject to continuing confidentiality
8. **Term** — duration of discussions + 3 years (for business info) to 5 years (for technical/IP) post-termination
9. **No License / IP Retention** — no rights granted; IP retained by Disclosing Party
10. **Remedies** — injunctive relief + damages + liquidated damages cap (if applicable)
11. **Indemnity** — for breach causing damage to Disclosing Party
12. **Governing Law & Jurisdiction** — Indian law, exclusive jurisdiction of [Mumbai/Delhi/Bengaluru] courts
13. **Arbitration** — seat at [city], Arbitration and Conciliation Act 1996, sole arbitrator for disputes < ₹5cr, 3-arbitrator panel for > ₹5cr
14. **Notices** — physical address + email with read receipt, deemed delivery periods
15. **Severability, Waiver, Entire Agreement, Amendment, Counterparts** — standard boilerplate
16. **Stamp Duty** — state-specific per Indian Stamp Act 1899; typically ₹100-₹500 depending on state

## OUTPUT FORMAT
- Times New Roman 12pt body, 14pt bold for title
- Numbered clauses 1., 1.1, 1.2
- Justified alignment, 1.5 line spacing
- "CONFIDENTIAL — PRIVILEGED & ATTORNEY WORK PRODUCT" header on every page
- Page numbers in footer
- Signature block with witness lines
- Stamp paper note at bottom
"""

SPA_PLAYBOOK = """# Share Purchase Agreement (SPA) Drafting Playbook — Indian Law

Generate an SPA of institutional quality suitable for M&A/PE transactions.

## MANDATORY SECTIONS
1. **Parties** — Seller, Purchaser, Company (and Promoter/Guarantor if any)
2. **Recitals** — transaction background, share structure, agreed heads of terms
3. **Definitions** — 40-60 defined terms: Affiliate, Applicable Law, Business Day, Closing, Conditions Precedent, Encumbrance, ESOP, Fundamental Warranties, Group Company, Longstop Date, Material Adverse Change, Promoter, Purchase Price, Sale Shares, Tax, Tax Warranties, Transaction Documents, Warranty Claim, etc.
4. **Sale and Purchase** — Sale Shares, Purchase Price (fixed vs variable), Price Adjustment mechanism (net debt, working capital)
5. **Consideration** — upfront vs deferred, escrow arrangement, earn-out structure
6. **Conditions Precedent** — regulatory approvals (CCI if applicable, RBI for FEMA, sectoral regulators), corporate approvals (board + shareholder), third-party consents, no MAC
7. **Pre-Completion Covenants** — ordinary course, restricted actions, information rights, cooperation for approvals
8. **Completion** — mechanics, deliverables by Seller (share transfer forms, resignations, statutory registers updated), deliverables by Purchaser (consideration, board resolution)
9. **Post-Completion Covenants** — non-compete (reasonable duration + geography), non-solicit of employees/customers, transition assistance, handover
10. **Warranties**:
    - Fundamental (title, capacity, capitalization) — unlimited liability, no time cap
    - Tax Warranties — 7-year limitation, separate cap
    - Business Warranties — 18-24 month limitation, 30-50% of consideration cap, de minimis + basket
11. **Tax Indemnity** — specific tax indemnity with pass-through mechanism for historical tax liabilities, separate from warranty claims
12. **General Indemnity** — for breach of covenants, third-party claims, specific identified risks
13. **Limitations on Liability** — de minimis, basket (tipping vs deductible), cap, time limits, reasonable foreseeability, disclosure letter exclusions
14. **Seller Disclosure** — general disclosure + specific disclosure letter; knowledge qualifiers ("to the Seller's knowledge after reasonable inquiry")
15. **Termination** — mutual consent, breach with cure period, failure of CPs by Longstop Date
16. **Escrow** — quantum, duration (18-24 months typical), trigger events for release
17. **Dispute Resolution** — Arbitration at [Mumbai/Delhi/Singapore], SIAC/ICC/DIAC rules, 3 arbitrators, English
18. **Governing Law** — Indian law (or English law for cross-border, with India-specific carve-outs)
19. **Boilerplate** — severability, waiver, amendment, entire agreement, notices, counterparts, costs and taxes (each party bears own), stamp duty
20. **Schedules** — Schedule 1 (Sale Shares), Schedule 2 (Warranties), Schedule 3 (Disclosure Letter), Schedule 4 (Completion Deliverables), Schedule 5 (Restricted Actions), Schedule 6 (Form of Resignation)

## KEY COMMERCIAL POINTS (DON'T MISS THESE)
- **FEMA compliance** — pricing guidelines for non-residents (Rule 21 of NDI Rules 2019)
- **CCI threshold check** — ₹2,500 cr asset / ₹7,500 cr turnover (as amended by Competition Amendment Act 2023)
- **Stamp duty** — state-specific on share transfer form SH-4; SDR rate typically 0.015% of consideration
- **Tax structuring** — Section 9 chargeability, Section 56(2)(x) fair market value check, Indirect transfer (S.9(1)(i) Explanations)
- **Indemnity escrow** — FEMA-compliant structure (NRE/Escrow accounts only for non-residents)

## OUTPUT FORMAT
Full SPA runs 80-150 pages. Use formal legal English, numbered clauses with cross-references, schedules labeled alphabetically, execution block with witness attestation.
"""

SHA_PLAYBOOK = """# Shareholders' Agreement (SHA) Drafting Playbook — Indian Law

## MANDATORY SECTIONS
1. **Parties** — Company + all Shareholders (or classes thereof)
2. **Recitals** — relationship background, AoA/MoA reference, funding rounds
3. **Definitions** — Investor, Founder, Promoter, Affiliate, ESOP, Conversion, Qualified IPO, Liquidation Event, Exit, Tag-Along, Drag-Along, Right of First Refusal (ROFR), Right of First Offer (ROFO), Pre-emptive Rights, Deadlock, Change of Control, Key Personnel
4. **Board Composition** — director nomination rights (pro-rata to shareholding), chair, quorum, observer rights
5. **Reserved Matters / Affirmative Voting Rights** — matters requiring unanimous/super-majority (amendment of AoA, issuance of shares, related-party transactions > threshold, capex > threshold, change of business, liquidation, merger, dividend)
6. **Information Rights** — monthly/quarterly financials, annual audited accounts, budgets, inspection rights
7. **Rights of First Refusal / First Offer** — mechanism, timelines (30-60 days typical), valuation (agreed formula or independent valuer)
8. **Pre-emptive Rights** — on issuance of new shares, pro-rata participation to maintain holding
9. **Tag-Along** — if Promoter sells > threshold, minority can tag along at same price
10. **Drag-Along** — if majority decides to sell, minority can be dragged (trigger: shareholding % + price hurdle)
11. **Liquidation Preference** — for preferred shareholders (1x non-participating / 1x participating with cap / participating uncapped)
12. **Anti-Dilution** — full ratchet (rare), broad-based weighted average (standard), narrow-based weighted average
13. **Non-Compete & Non-Solicit** — for Founders/Promoters during tenure + 2-3 years post-exit
14. **Founder Lock-in & Vesting** — 4-year vesting with 1-year cliff typical
15. **ESOP Pool** — size (10-15% typical pre-Series A), authority to grant, dilution treatment
16. **Exit Rights** — Qualified IPO definition, drag trigger, put options (where permitted under FEMA), strategic sale
17. **Deadlock Resolution** — escalation to chairs → mediation → Buy-Sell / Texas Shoot-out / Russian Roulette
18. **Transfer Restrictions** — lock-in periods, permitted transfers (to affiliates only)
19. **Conversion** — preferred to equity on liquidity events, conversion ratio, triggers
20. **Regulatory Compliance** — AoA conformity (SHA rights must be mirrored in AoA), FEMA compliance for non-resident parties, SEBI compliance if listed/pre-IPO
21. **Confidentiality, Dispute Resolution, Governing Law, Notices, Boilerplate**

## KEY INDIAN LAW NUANCES
- **AoA mirroring mandatory** — V. B. Rangaraj v. V. B. Gopalakrishnan (SC 1992) — shareholder agreement clauses enforceable against company only if in AoA
- **Section 58 Companies Act 2013** — transfer restrictions must be in AoA
- **FEMA Schedule I (NDI Rules 2019)** — pricing guidelines, put/call options permitted for Indian residents ↔ non-residents subject to rules
- **Tag/drag limits** — enforceable if in AoA and comply with Companies Act
- **Section 47 ITA** — tax implications on transfer to holding company
"""

JV_PLAYBOOK = """# Joint Venture Agreement Drafting Playbook — Indian Law

## MANDATORY STRUCTURE
1. **Parties** — JV Partner A, JV Partner B, JV Company (if incorporating a Newco)
2. **Recitals** — business rationale, complementary capabilities, regulatory landscape
3. **Business Scope** — clearly defined business; exclusivity/non-compete carve-outs
4. **Incorporation & Capital Structure** — authorized capital, paid-up, shareholding %
5. **Capital Contributions** — initial + deferred + follow-on mechanisms; default consequences
6. **Board & Management** — director nomination, CEO appointment rights, quorum, deadlock at board
7. **Reserved Matters** — list of decisions requiring both/all partners' consent
8. **Business Plan & Budget** — annual approval, deviation thresholds
9. **Technology/IP Licensing** — license scope (exclusive/non-exclusive, field-of-use, territory), royalties, improvements
10. **Non-Compete & Non-Solicit** — during JV term + 2-3 years post-exit; carve-outs for existing businesses
11. **Exclusivity** — geographic/product/customer exclusivity for JV scope
12. **Dividend Policy** — minimum distribution, retention for growth, debt servicing priority
13. **Deadlock Resolution** — escalation → mediation → Buy-Sell (at stated valuation)
14. **Exit Mechanisms** — ROFR, put/call options (subject to FEMA), tag-along, drag-along, IPO, third-party sale
15. **Termination** — events of default, material breach, change of control, deadlock, insolvency
16. **Post-Termination** — winding-up procedures, non-use of JV IP, customer transition
17. **Regulatory Approvals** — FDI compliance, sector-specific (defense, telecom, insurance, pharma, etc.), FEMA reporting
18. **CCI Notification** — if combination thresholds triggered

## COMMERCIAL KEY POINTS
- **Equity vs Contractual JV** — incorporated JV for long-term, contractual JV for project-specific
- **Technology licensing royalties** — FEMA cap (10% of sales for technology, 8% of exports for licenses)
- **Management fees** — benchmarking to arm's-length per Transfer Pricing
- **Make-or-buy decisions** — framework for sourcing from partners vs third parties
"""

SERVICE_AGREEMENT_PLAYBOOK = """# Service Agreement / Consulting Agreement Drafting Playbook

## MANDATORY CLAUSES
1. Parties, Recitals, Definitions
2. Scope of Services (detailed scope, not vague; attached as Schedule)
3. Service Levels / KPIs (measurable, with consequence)
4. Term & Renewal (fixed term + auto-renew with opt-out notice)
5. Fees & Payment Terms (milestone vs time-and-material, invoicing, TDS deduction)
6. Expenses (pre-approval thresholds, reimbursement mechanism)
7. Intellectual Property (work product ownership — default to client; background IP retained by service provider)
8. Confidentiality (2-3 year post-termination survival)
9. Data Protection (DPDP Act 2023 compliance — processor obligations)
10. Non-Solicit (client's employees, service provider's resources)
11. Representations & Warranties (professional standard, no conflict, capacity)
12. Indemnity (third-party IP claims, service provider's negligence)
13. Limitation of Liability (cap at 1x/2x annual fees, exclusion of consequential damages, indirect losses)
14. Force Majeure (post-COVID: pandemics, lockdowns, cyber attacks)
15. Termination (for cause with cure period, for convenience with notice)
16. Governing Law, Jurisdiction, Arbitration
17. Boilerplate

## KEY TDS / GST CONSIDERATIONS
- TDS under S.194J @ 10% for professional/technical services (threshold ₹30,000 p.a.)
- GST @ 18% on professional services (IGST for inter-state/export, CGST+SGST for intra-state)
- Place of supply rules for services to foreign clients (export of services if conditions met → zero-rated)
- Reverse Charge for services from non-residents to Indian clients
"""

EMPLOYMENT_AGREEMENT_PLAYBOOK = """# Employment Agreement Drafting Playbook — Indian Law

## MANDATORY CLAUSES
1. Parties, Position, Reporting, Location
2. Term (permanent / fixed term / probation)
3. Compensation (base, variable, ESOP, benefits, reimbursements, allowances)
4. Working Hours & Leave (adherence to Shops & Establishments Act of state)
5. Duties & Obligations (fiduciary, full-time attention, no conflict)
6. Confidentiality & IP Assignment (works created during employment — assigned to employer)
7. Non-Solicit (of employees, customers — during + 1-2 years post)
8. Non-Compete (post-employment; narrow scope — INDIA: only during employment; post-termination is largely unenforceable per Sec 27 Indian Contract Act)
9. Garden Leave (paid leave during notice period)
10. Termination (notice period, payment in lieu, for-cause triggers)
11. Full and Final Settlement
12. Governing Law, Jurisdiction

## KEY INDIAN LAW NUANCES
- **Section 27 Indian Contract Act** — post-employment non-compete VOID; only non-solicit enforceable
- **Industrial Disputes Act** — applicable for "workmen" (≤ ₹10,000/month supervisory or technical staff); retrenchment compensation, notice period
- **Shops & Establishments** — state-specific; weekly off, overtime, leave entitlements
- **Gratuity** — Payment of Gratuity Act 1972; 5 years continuous service; 15 days wages × years
- **Provident Fund** — mandatory for establishments > 20 employees; employee + employer @ 12% of basic+DA
- **ESIC** — applicable if wages ≤ ₹21,000/month
- **Bonus** — Payment of Bonus Act; min 8.33%, max 20% of salary+DA
- **Maternity Benefit** — 26 weeks paid leave (Maternity Benefit Amendment 2017)
- **POSH compliance** — Sexual Harassment Act 2013; Internal Committee mandatory for > 10 employees
"""

LEASE_AGREEMENT_PLAYBOOK = """# Lease / Leave & License Agreement Drafting Playbook — Indian Law

## STRUCTURE DEPENDS ON
- **Lease** (Transfer of Property Act 1882, Sec 105) — transfers interest; registration mandatory if > 1 year
- **Leave & License** (Easements Act 1882, Sec 52) — personal permission, no interest; used for residential/commercial to avoid Rent Control Acts

## MANDATORY CLAUSES
1. Parties (Lessor/Licensor, Lessee/Licensee)
2. Property Description (full legal description, boundaries, area)
3. Term (period, commencement, expiry)
4. Rent / License Fee (monthly, payment date, escalation: 5-10% every 2-3 years, mode of payment)
5. Security Deposit (typically 3-10 months rent; refund terms)
6. Purpose of Use (residential / commercial — specific; no change without consent)
7. Maintenance & Repairs (allocation between parties)
8. Utilities (electricity, water, society charges)
9. Alterations & Structural Changes (no structural without consent)
10. Lessor's Covenants (quiet enjoyment, title, peaceful possession)
11. Lessee's Covenants (no sub-letting without consent, reasonable use)
12. Termination (for breach with cure, for convenience with notice, lock-in period)
13. Exit Notice Period
14. Stamp Duty & Registration (state-specific — Maharashtra: 0.25% of consideration for L&L; Karnataka: varies; Delhi: 2% for lease)
15. GST Implications (commercial lease attracts 18% GST if licensor is registered; residential exempt)
16. TDS (S.194-I 10% on rent if > ₹2,40,000/year; S.194-IB 2% for individuals paying > ₹50,000/month as amended w.e.f. 01-10-2024)
"""

FRANCHISE_AGREEMENT_PLAYBOOK = """# Franchise Agreement Drafting Playbook — Indian Law

## MANDATORY CLAUSES
1. Parties, Recitals (brand history, system)
2. Grant of Franchise (territorial rights, exclusivity)
3. Term & Renewal (typically 5-10 years with renewal options)
4. Trademark License (marks covered, usage guidelines)
5. Operations Manual (standards, updates binding on franchisee)
6. Initial Fee & Ongoing Royalty (% of revenue; FEMA cap for foreign franchisors: 8% of exports, 10% of domestic sales on technology fees)
7. Marketing Contribution (ad fund contribution)
8. Training (initial + ongoing)
9. Site Selection, Fit-Out Standards
10. Supply Chain (franchisor-controlled vs approved vendors)
11. Quality Control & Audits
12. Non-Compete (during + 2 years post)
13. Confidentiality of Operations Manual
14. Termination (for cause with cure, for-convenience rare in franchise)
15. Post-Termination (de-branding, non-compete, good will)
16. FEMA Compliance (royalty remittance; Form A2)
17. GST (18% on royalties; place of supply rules for IP licensing)
"""


# ==================== CONTRACT REDLINING PLAYBOOK ====================

REDLINING_PLAYBOOK = """# Contract Redlining Playbook — Risk-Weighted Review

Review the uploaded contract and produce a redlined version + risk matrix.

## APPROACH
1. Read the ENTIRE contract before making any suggestions
2. For EACH clause, rate: CRITICAL / HIGH / MEDIUM / LOW / NONE
3. Use track-changes semantics — strikethrough original + bold insertion
4. Add margin comments explaining rationale

## RED FLAG CHECKLIST (IDENTIFY EACH IF PRESENT)
### Liability & Risk Allocation
- Unlimited liability (no cap) → CRITICAL — insert cap at 1-2x contract value
- Consequential damages NOT excluded → CRITICAL — add explicit exclusion
- One-sided indemnity → HIGH — make mutual or limit to specific heads
- Indemnity uncapped → CRITICAL — cap at same liability cap
- Gross negligence/wilful misconduct NOT carved out from cap → HIGH

### Term & Termination
- Auto-renewal without opt-out → HIGH — add 30/60-day opt-out notice
- No termination for convenience → MEDIUM — add with appropriate notice
- Termination only for material breach with no cure period → HIGH — add 30-day cure

### Commercial
- Price escalation without cap → MEDIUM — add CPI-linked or % cap
- Late payment interest uncapped → LOW — cap at RBI LAF rate or commercial rate
- No Most-Favored-Nation / benchmark rights → LOW
- Exclusivity without reciprocal obligations → MEDIUM

### IP & Confidentiality
- IP assignment without carve-out for background IP → HIGH
- Confidentiality without term → MEDIUM — add 3-5 year survival
- Data protection clause missing (DPDP Act 2023) → HIGH for service providers

### Regulatory
- FEMA compliance for cross-border payments not addressed → HIGH if foreign party
- GST clause silent on who bears GST → MEDIUM
- TDS allocation unclear → MEDIUM
- No force majeure or pre-COVID boilerplate only → HIGH (must cover pandemic, lockdown)

### Dispute Resolution
- Jurisdiction in unfavorable forum → HIGH
- Arbitration missing or in expensive seat → MEDIUM — prefer Mumbai/Delhi/Bengaluru
- No expedited arbitration for disputes under ₹5cr → LOW

### Missing Clauses (MUST ADD if absent)
- Severability
- Entire Agreement
- Amendment (written only)
- Waiver (no implied)
- Notice (address + email + deemed delivery)
- Counterparts
- Stamp duty & registration
- Governing law

## OUTPUT FORMAT (ALWAYS AS DOCX)
1. **Redlined Contract** — track-changes style (strikethrough + insertions)
2. **Risk Matrix Table** — Clause | Severity | Current Language | Issue | Recommended Revision | Legal Basis
3. **Executive Summary** — TOP 5 critical issues, estimated negotiation outcomes

## NEVER
- Don't water down legitimate protections — keep strong ones
- Don't insert new clauses beyond the stated checklist without flagging
- Don't change commercial terms (price, scope) unless instructed
"""


# ==================== DUE DILIGENCE PLAYBOOK ====================

DUE_DILIGENCE_PLAYBOOK = """# Due Diligence Extraction Playbook

Extract structured data from uploaded documents and produce a DD report.

## STANDARD DD AREAS (check ALL applicable to uploaded docs)

### 1. CORPORATE
- Certificate of Incorporation, MoA/AoA, CIN
- Current shareholding pattern (cap table with share classes)
- Board composition, Key Managerial Personnel
- Statutory registers maintained (S.88 Companies Act)
- Annual filings status (AOC-4, MGT-7, MGT-14)
- Pending corporate actions (ROC filings, board resolutions)

### 2. COMMERCIAL
- Top 10 customer contracts (exclusivity, termination, change of control, non-compete)
- Top 10 vendor contracts
- Key IP agreements
- Related-party transactions (S.188 — arm's length test)

### 3. FINANCIAL
- Last 3 years audited financials + current year interim
- Revenue concentration (top 5 customers as % of revenue)
- Gross margin trends
- Working capital cycles
- CapEx history and forward pipeline
- Debt schedule (lender, outstanding, interest rate, maturity, security)
- Cash flow trends

### 4. TAX
- Income tax assessment status (open years, pending demands, appeals)
- GST registration, returns filing status, open notices
- Transfer pricing documentation (if cross-border related parties)
- Pending tax litigation
- Retention of records (Section 44AA, 44AB)

### 5. REGULATORY
- Sector-specific licenses (FSSAI, drug license, pollution clearance, labour licenses)
- FEMA compliance for any foreign exposure (FDI reporting, ECB, ODI)
- Data protection compliance (DPDP Act 2023)
- Environmental clearances
- Fire/safety/building certificates

### 6. LITIGATION
- Pending civil suits (as plaintiff, as defendant)
- Criminal complaints/FIRs/chargesheets
- Tax appeals (CIT(A), ITAT, HC, SC)
- Arbitrations
- Regulatory investigations (SEBI, CCI, MCA, ED)
- Notices received (pending action)
- Labour disputes

### 7. EMPLOYMENT
- Employee count with category (permanent, contract, consultant)
- Top 10 employees compensation
- ESOP pool, vesting status
- PF/ESI/Gratuity compliance
- POSH committee constitution
- Key-person insurance
- Pending labour claims

### 8. IP
- Trademarks (registered, pending, renewals due)
- Patents (granted, pending)
- Copyrights
- Domain names
- Brand guidelines & usage

### 9. REAL ESTATE
- Owned properties (title chain, encumbrances, tax receipts)
- Leased properties (term, rent escalation, renewal, security deposit)
- Stamp duty and registration compliance

### 10. INSURANCE
- Policies held (general, D&O, cyber, professional indemnity)
- Premium paid, renewal schedule
- Claims history

## OUTPUT FORMAT
Produce a MULTI-SHEET Excel:
1. **DD Summary** — area-wise findings with risk rating (Red/Amber/Green)
2. **Open Items** — list of documents/info still pending with deadline
3. **Red Flags** — specific issues requiring closure before transaction
4. **Deal Points** — items to address in SPA (reps, warranties, indemnities, conditions)
5. **Document Inventory** — all reviewed documents with file names, dates, signatures
"""


# ==================== CHRONOLOGY / TIMELINE PLAYBOOK ====================

CHRONOLOGY_PLAYBOOK = """# Litigation Chronology Builder Playbook

Extract all dates, events, notices, payments from the uploaded documents and build a Chronology Excel.

## EXTRACTION TARGETS
For each document, extract:
- **Date** (DD-MMM-YYYY)
- **Event Type** (Notice issued / Reply filed / Order / Payment / Hearing / Document / Internal event)
- **Description** (one-line summary)
- **Parties** (who issued / received)
- **Reference** (document page, notice number, order number)
- **Amount** (if financial event, in ₹)
- **Source Document** (filename)

## CHRONOLOGY STRUCTURE
```
Date | Event Type | Description | Party | Reference | Amount | Source | Annotation
```

## SORT & GROUP
- Sort by Date ASC
- Group by phase (Pre-Assessment / Assessment / Appeal / Execution)
- Highlight limitation-critical events in red
- Highlight hearing dates in yellow

## LIMITATION CHECKS (auto-compute)
For each event, check if it triggered a limitation:
- S.148 notice → 30 days to file ITR (or per notice)
- Order u/s 143(3) → 30 days to CIT(A) appeal
- CIT(A) order → 60 days to ITAT
- GST SCN S.73 → 30 days reply; order within 3Y from annual return due date
- GST SCN S.74 → 30 days reply; order within 5Y

Add a "Next Action Due" column showing what needs to be done by what date.

## OUTPUT FORMAT
Multi-sheet Excel:
1. **Master Chronology** — all events sorted by date
2. **By Phase** — grouped view
3. **Deadlines** — all pending deadlines sorted by proximity
4. **Parties Index** — cross-reference by party
5. **Financial Summary** — payments, demands, refunds with running balance
"""


# ==================== NOTICE REPLY PLAYBOOK ====================

NOTICE_REPLY_PLAYBOOK = """# Notice Reply Drafting Playbook (Tax/GST)

Draft a formal reply to the uploaded notice following the "kill shot → secondary → fallback → quantum" framework.

## MANDATORY STRUCTURE
1. **Without Prejudice** header
2. **Reference** — Notice number, date, financial year, amount
3. **Preliminary Objections** (if any procedural defect exists):
   - DIN compliance (CBIC Circular 128/47/2019, CBDT Circular 19/2019)
   - Jurisdiction
   - Limitation period
   - Natural justice (opportunity of hearing)
   - Approval of specified authority (S.151 for IT reassessment)
4. **Statement of Facts** — chronology of events
5. **Point-wise Reply** — each allegation answered with:
   - Denial (if incorrect)
   - Legal position (statutes + case law)
   - Factual explanation
   - Supporting documents referenced
6. **Legal Submissions** — organized by issue with case law citations
7. **Prayer** — specific relief sought
8. **Documents** — Annexure list

## DEFENSE HIERARCHY
For each issue, present defenses in this order:
1. **Procedural Kill Shot** (DIN, limitation, jurisdiction) — if available, lead with this
2. **Merits Defense** (substantive legal position + case law)
3. **Factual Re-characterization** (different interpretation of facts)
4. **Quantum Reduction** (even if liability accepted, reduce amount)

## EVIDENCE STANDARDS
- Every factual claim must be supported by a document or be marked as "to be furnished"
- Every legal claim must cite section + case name + reporter
- Use tables for numerical reconciliations
- Separate Annexure for each category of evidence

## TONE
Formal, respectful, confident. NEVER aggressive. Present arguments as "respectfully submitted".
"""


# ==================== REGISTRY ====================

PLAYBOOKS = {
    "nda": NDA_PLAYBOOK,
    "spa": SPA_PLAYBOOK,
    "sha": SHA_PLAYBOOK,
    "jv": JV_PLAYBOOK,
    "service_agreement": SERVICE_AGREEMENT_PLAYBOOK,
    "employment_agreement": EMPLOYMENT_AGREEMENT_PLAYBOOK,
    "lease_agreement": LEASE_AGREEMENT_PLAYBOOK,
    "franchise_agreement": FRANCHISE_AGREEMENT_PLAYBOOK,
    "redlining": REDLINING_PLAYBOOK,
    "due_diligence": DUE_DILIGENCE_PLAYBOOK,
    "chronology": CHRONOLOGY_PLAYBOOK,
    "notice_reply": NOTICE_REPLY_PLAYBOOK,
}


def get_playbook(playbook_name: str) -> str:
    """Retrieve a playbook by name, or return empty string."""
    return PLAYBOOKS.get(playbook_name.lower(), "")


def list_playbooks() -> list[dict]:
    """List available playbooks with metadata."""
    return [
        {"id": "nda", "title": "Non-Disclosure Agreement", "category": "contract"},
        {"id": "spa", "title": "Share Purchase Agreement", "category": "contract"},
        {"id": "sha", "title": "Shareholders' Agreement", "category": "contract"},
        {"id": "jv", "title": "Joint Venture Agreement", "category": "contract"},
        {"id": "service_agreement", "title": "Service / Consulting Agreement", "category": "contract"},
        {"id": "employment_agreement", "title": "Employment Agreement", "category": "contract"},
        {"id": "lease_agreement", "title": "Lease / Leave & License", "category": "contract"},
        {"id": "franchise_agreement", "title": "Franchise Agreement", "category": "contract"},
        {"id": "redlining", "title": "Contract Redlining + Risk Matrix", "category": "review"},
        {"id": "due_diligence", "title": "Due Diligence Extraction", "category": "analysis"},
        {"id": "chronology", "title": "Litigation Chronology Builder", "category": "litigation"},
        {"id": "notice_reply", "title": "Tax/GST Notice Reply", "category": "litigation"},
    ]


def detect_playbook_intent(user_query: str) -> str:
    """Heuristically detect which playbook (if any) the user wants.

    Returns playbook ID or empty string.
    """
    import re
    q = user_query.lower()

    patterns = [
        (r"\b(redlin|mark\s*up|review\s+(this|the)\s+(contract|agreement)|annotate.*contract|risk\s+(matrix|assess)\s+of\s+(this|the))\b", "redlining"),
        (r"\b(due\s+dilig|dd\s+report|data\s+room|extract.*documents)\b", "due_diligence"),
        (r"\b(chronolog|timeline|dates\s+extract|litigation\s+summary)\b", "chronology"),
        (r"\b(notice\s+reply|reply\s+to\s+(this|the|my)\s+notice|respond\s+to\s+(notice|scn)|draft.*reply)\b", "notice_reply"),
        (r"\b(nda|non.?disclosure|confidential(ity)?\s+agreement)\b", "nda"),
        (r"\b(share\s+purchase|spa\b|stock\s+purchase)\b", "spa"),
        (r"\b(shareholders?[’'\s]*agreement|\bsha\b)\b", "sha"),
        (r"\b(joint\s+venture|\bjv\b)\b", "jv"),
        (r"\b(service\s+(agreement|contract)|consult(ing|ancy)\s+agreement|professional\s+services\s+agreement)\b", "service_agreement"),
        (r"\b(employment\s+(agreement|contract)|appointment\s+letter|offer\s+letter)\b", "employment_agreement"),
        (r"\b(lease|leave\s+(and|&)\s+licen[sc]e|rental\s+agreement|tenancy)\b", "lease_agreement"),
        (r"\b(franchise|franchising)\b", "franchise_agreement"),
    ]

    for pattern, playbook_id in patterns:
        if re.search(pattern, q):
            return playbook_id

    return ""
