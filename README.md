# Spectr

> **The senior associate Indian advocates, CAs, CSs, and in-house counsel reach for when a Claude tab in another window won't cut it.**

Spectr is a domain-tuned AI platform for Indian legal and tax practice. It produces filing-ready deliverables — precedent citation tables with IndianKanoon verification links, draft pleadings and SCN replies in proper Indian register, computation tables with worked arithmetic, and litigation timelines — grounded in the current state of Indian law (BNS/BNSS/BSA from 01.07.2024, GST 2.0 from 22.09.2025, Finance Act 2025, Labour Codes from 21.11.2025) and a 2,881-section bare-act corpus.

Built by [AlgoRythmTech](https://github.com/AlgoRythmTech). Production target: Indian Tier-1 firms, in-house tax/legal teams, and Big Four advisory.

---

## Why Spectr — and not just Claude

A free Claude tab gives you a memo about your matter. Spectr gives you a deliverable for your matter. Concretely:

| Pain point with vanilla LLMs | What Spectr does |
|---|---|
| Cites IPC §302 in 2025 — doesn't know IPC was repealed by BNS on 01.07.2024 | Always cites BNS §103 with `(formerly IPC §302)` for transitional readability. Same for CrPC→BNSS, IEA→BSA, EPF/Gratuity→Labour Codes. |
| Computes capital gains at 10% LTCG with ₹1L exemption | Knows §112A is now 12.5% beyond ₹1.25L post-23.07.2024 (Finance (No. 2) Act 2024) and the §112(1) proviso election (12.5% no-index OR 20% with-index for pre-23.07.2024 land/buildings). |
| Quotes 28% GST on cement, 18% on insurance | Cement → 18% from 22.09.2025 under GST 2.0; insurance → exempt. |
| §87A rebate at ₹25,000 / ₹7L threshold | ₹60,000 / ₹12L under new regime per Finance Act 2025. |
| Hallucinates Indian case names ("Bharat Jayantilal Patel (2022) 442 ITR 1 (Bom)" when no such case exists) | Curated case authority for high-stakes queries (Hexaware, Kankanala, Mon Mohan Kohli, Ashish Agarwal, Vineeta Sharma…). Hard hallucination rule: if not 100% certain, says so. |
| Returns generic memos | Closes every substantive answer with a **filing-ready deliverable**: precedent citation table with IndianKanoon links, draft text in Indian legal register, computation table, litigation timeline, Vault hook. |
| No memory of your firm's prior matters or templates | Document Vault retains client matters, prior briefs, firm-specific drafting templates. Threading via Supermemory carries context across sessions. |

---

## Headline features

**Chat advisory** — partner-grade memos with the angle the user didn't ask about. Three-beat ANALYSIS rhythm: state the rule → confront the strongest counter → explain why our reading wins on the facts.

**Document Vault** — upload PDFs, DOCX, scanned notices. Spectr produces Executive Summary, Night Before Digest, Chronological Timeline, or Cross-Examination Matrix.

**Workflows (38 templates)** — GST SCN reply, Section 148A reply, Bail application (BNSS §483), Writ petition under Article 226, Board resolutions, ROC filings, Director reports, Notice Reply auto-drafts.

**Reconcilers** — GSTR-2B vs purchase register, TDS 26AS vs books, bank statement vs ledger. Vendor risk and ITC exposure flagged.

**Tools** —
- TDS Classifier (Section + rate auto-detect)
- Penalty Calculator (late filing fees + interest by deadline type)
- Section Mapper (IPC ↔ BNS / CrPC ↔ BNSS / IEA ↔ BSA)
- Notice Reply (DRC-01A, §148A(b), §143(2) — auto-draft)
- Notice Check (validity, jurisdiction, limitation arithmetic)
- ITR Compute (regime comparison FY 2025-26 with full breakdown)
- Limitation Calculator
- Stamp Duty Calculator (state-specific)

**Court Tracker** — live IndianKanoon integration; track Supreme Court / High Court orders, stays, listings.

**Trust Layer** — every citation gets an IndianKanoon verification link the partner can click. No fabricated citations.

**Tally / Drive / Email Integration** — pull books from Tally, files from Google Drive, notices from email inbox.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (React + Tailwind + Plus Jakarta + EB Garamond) │
└────────────────────────────────────────────────────────────┘
                          ↓ /api/assistant/query (SSE)
┌─────────────────────────────────────────────────────────┐
│  FastAPI server.py                                        │
│  • Greeting fast-path (Groq llama-3.1-8b ~250ms canned)  │
│  • PII Guard + sanitization                              │
│  • Thread manager (Supermemory cross-session memory)     │
│  • Matter context + Library precedents + Firm context    │
└──────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  spectr_pipeline.py — 4-stage cascade                    │
│  ┌─────────────┐                                          │
│  │ -1. INTENT   │ Heuristic + Groq tiebreaker (~0-200ms)  │
│  └──────┬──────┘                                          │
│         ↓                                                  │
│  ┌─────────────┐                                          │
│  │ 0. ORCHESTR │ Groq llama-3.3-70b classifier            │
│  │             │ → domain, task, complexity, retrieval    │
│  │             │   queries, recommended_model             │
│  └──────┬──────┘                                          │
│         ↓                                                  │
│  ┌─────────────┐                                          │
│  │ 1. RETRIEVE │ MongoDB Atlas — 2,881 statute sections   │
│  │             │ + Serper web + IndianKanoon (optional)   │
│  └──────┬──────┘                                          │
│         ↓                                                  │
│  ┌─────────────┐                                          │
│  │ 2. DRAFT    │ GPT-5.5 (default) reasoning_effort=high  │
│  │             │ Claude Opus 4.6 (case-law / strategic)   │
│  │             │ With INDIAN_LAW_SNAPSHOT + DOMAIN_EXT    │
│  │             │ + DELIVERABLE MANDATE                     │
│  └──────┬──────┘                                          │
│         ↓                                                  │
│  ┌─────────────┐                                          │
│  │ 3. CRITIC   │ gpt-4o-mini citation-integrity gate      │
│  │             │ (force_deep mode only)                   │
│  └─────────────┘                                          │
└──────────────────────────────────────────────────────────┘
```

### Model routing

The Groq orchestrator picks the drafter per query. **Only peak-reasoning models in rotation** — no Sonnet, no GPT-4.1, no GPT-4o-mini for substantive work:

| Tier | Model | Used for | Surface |
|---|---|---|---|
| **Default** | `gpt-5.5` | Tax, accounting, GST, computation, statutory analysis | OpenAI direct (peak `reasoning_effort: high`) |
| **Case-law tier** | `claude-opus-4-6` | Case law digests, constitutional questions, opinions, strategic narratives, drafting petitions | Emergent universal key |
| **Greetings only** | `llama-3.1-8b-instant` | Triage of "hi", "thanks", typos, off-topic chitchat | Groq (free tier) |
| **Orchestrator only** | `llama-3.3-70b-versatile` | Stage-0 classification + model recommendation | Groq |

Cascade fallback so failed providers never show blank to user. 429 retry-with-backoff (3 attempts: 2s/4s/6s) on rate-limit hits.

### The deliverable mandate

Every substantive response (anything beyond a one-line lookup) ships with at least two of these artifacts — things vanilla Claude cannot produce because Claude has no IndianKanoon hook, no Vault, no compute-and-fill drafting layer, no litigation calendar engine:

1. **Precedent Citation Table** — 4-column markdown table (Case | Court/Year | Ratio in ≤ 18 words | IndianKanoon verify link). Lifts directly into a writ petition.
2. **Filing-Ready Draft Text** — operative paragraphs in Indian legal register, ready to paste into the SCN reply / writ / opinion.
3. **Computation Table** — formula → substitution → arithmetic → answer in markdown, with cess/surcharge/interest broken out.
4. **Litigation Timeline** — chronological calendar table with form numbers, authorities, days-from-notice.
5. **Vault Hook** — prompts the partner to upload the actual notice/document so Spectr cross-checks against the real file.

---

## Indian Law Snapshot (always loaded as freshness anchor)

The system prompt ships with a comprehensive freshness card the model must defer to over its training data:

- **BNS 2023 / BNSS 2023 / BSA 2023** — effective 01.07.2024. Full IPC↔BNS, CrPC↔BNSS, IEA↔BSA section mapping baked in.
- **Four Labour Codes** — effective 21.11.2025. Wage Code §2(y) 50% proviso, FTC gratuity carve-out, gig-worker chapter.
- **GST 2.0** — effective 22.09.2025. Two-rate structure (5%/18% + 40% sin), DRC sequence (DRC-01A → DRC-01 → DRC-06 → DRC-07 → APL-01), ITC bona-fide-recipient defence (Suncraft Energy, D.Y. Beathel, Arise India, LGW Industries, Tara Chand Rice Mills).
- **Finance Act 2025** — §87A ₹60K/₹12L, std deduction ₹75K, slab structure 0-4-8-12-16-20-24L, capital gains §112A 12.5%/₹1.25L + §111A 20% + §112(1) proviso election, §80CCD(2) 14% under new regime.
- **§148A reassessment** — Finance Act 2021 substituted regime + Ashish Agarwal (2022) + Rajeev Bansal (2024). For JAO-vs-FAO question post-Notification 18/2022, curated case authority (Hexaware Technologies, Kankanala Ravindra Reddy, etc.) loaded directly into prompt.
- **Companies Act 2013 + SEBI LODR + IBC + FEMA + RERA + IP** — current thresholds, forms, and key cases for each domain.

---

## Tech stack

**Frontend**
- React 18 + React Router
- Tailwind CSS + Plus Jakarta Sans + EB Garamond + Inter
- Framer Motion + Lucide icons
- Firebase Auth (Google SSO)
- Server-Sent Events for streaming responses

**Backend**
- FastAPI + Uvicorn (Python 3.12)
- MongoDB Atlas — primary (statutes, threads, audit, users)
- SQLite — local users + audit fallback
- Supermemory — long-term cross-thread memory
- Firebase Admin — auth verification
- Sentence-transformers (`all-MiniLM-L6-v2`) — embeddings for retrieval

**Models**
- OpenAI GPT-5.5 (direct API, `reasoning_effort: high`)
- Anthropic Claude Opus 4.6 (via Emergent universal key)
- Groq (Llama-3.1-8b-instant + Llama-3.3-70b-versatile)
- Emergent LLM proxy for budget-efficient routing
- Optional: Mistral, Gemini, Z.ai GLM (fallback only)

**Integrations**
- IndianKanoon — case law + verification links
- Serper — Google web/news/scholar
- Tally — books import
- Google Drive — file sync (OAuth)
- Email (AgentMail) — notice ingestion
- Blaxel sandbox — sandbox research / 5-phase deep research

---

## Quickstart

### Prerequisites

- Python 3.12+
- Node.js 20+
- MongoDB (Atlas or local)
- API keys: OpenAI, Anthropic-via-Emergent, Groq, Firebase Admin

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate    # or source .venv/bin/activate on Linux
pip install -r requirements.txt

# Create backend/.env (see backend/.env.example for shape)
# Critical keys:
#   OPENAI_KEY=sk-proj-...
#   EMERGENT_LLM_KEY=sk-emergent-...
#   GROQ_KEY=gsk_...
#   MONGO_URL=mongodb+srv://...
#   DB_NAME=spectr_primary
#   FIREBASE_PROJECT_ID=...

# Place firebase-admin.json (service account) in backend/
# (gitignored — never commit)

# Seed statute corpus to MongoDB (one-time)
python seed_statutes_to_mongo.py --commit --wipe

# Start backend (Windows — supervisor auto-restarts on crash)
.\backend_start.ps1

# Or run directly
python _run_backend.py
```

Backend serves at `http://localhost:8000`. Health check: `GET /health`.

### Frontend

```bash
cd frontend
npm install
npm start
```

Frontend serves at `http://localhost:3000`.

### Old laptop deployment (single-script)

For deploying on a constrained host (e.g., 8GB RAM old laptop running as production server):

```powershell
# Run as Administrator in PowerShell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup_old_laptop.ps1
```

Installs MongoDB Community + Python + Node, configures local Mongo, seeds statute corpus, starts backend under supervisor, and starts frontend dev server. See `setup_old_laptop.ps1` for details.

---

## Repository structure

```
Associate_Research/
├── backend/
│   ├── server.py                 # FastAPI entrypoint
│   ├── spectr_pipeline.py        # 4-stage cascade, prompt, routing
│   ├── war_room_engine.py        # Legacy multi-pass path (force_deep only)
│   ├── ai_engine.py              # Legacy ai engine
│   ├── thread_manager.py         # Conversation threading
│   ├── claude_emergent.py        # Claude direct + Emergent proxy
│   ├── seed_statutes_to_mongo.py # Atlas seeder
│   ├── seed_data/statutes/       # 18 bare-act JSON files
│   ├── _supervisor.py            # Auto-restart supervisor
│   ├── backend_start.ps1         # Windows launch
│   ├── workflow_chain.py         # 38 workflow templates
│   ├── reconciliation_engine.py  # GSTR-2B / TDS / ledger reconcilers
│   ├── case_law_engine.py        # IndianKanoon integration
│   ├── tax_audit_engine.py       # Tax audit reports
│   ├── ibc_engine.py             # IBC analysis
│   ├── notice_parser.py          # Notice extraction
│   └── ...
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── AssistantPage.js  # Chat advisory
│   │   │   ├── CaseLawPage.js
│   │   │   ├── VaultPage.js
│   │   │   ├── ReconcilerPage.js
│   │   │   ├── WorkflowsPage.js
│   │   │   └── ...
│   │   └── components/
│   │       ├── ResponseCard.js   # Markdown + citation rendering
│   │       ├── PreviousChatsSidebar.js
│   │       └── ...
│   └── public/
├── scripts/
│   ├── deploy.sh
│   ├── new-firm.sh
│   └── rollback.sh
├── setup_old_laptop.ps1          # One-shot deploy for HP Ryzen 3 host
└── README.md
```

---

## Voice & differentiation principles

These are baked into the system prompt and enforced by the deliverable mandate:

1. **No generic memo template.** No "1. ISSUE FRAMING / 2. GOVERNING LAW / 3. JUDICIAL TREATMENT" boilerplate. Headings emerge from what the user actually asked.
2. **Tier-1 firm register.** Headings are sober and substantive (`## The Leading Authority`, `## Bombay HC Position`, `## Limitation Analysis`). Banned heading words: *killer, opening shot, dispositive angle, the play, gotcha, game-changer*.
3. **Lead with the answer.** Opening sentence is the conclusion a partner would write at the top of an email — not a restatement of the question.
4. **Cite real cases.** Hard hallucination rule: if not 100% certain, say so. Curated case authority for high-stakes queries (§148A, §74 SCN, BNS bail, etc.) loaded directly into prompt.
5. **Three-beat ANALYSIS.** Per sub-issue: state the rule (with statute/case), confront the strongest counter, explain why our reading wins on the facts.
6. **Form numbers and deadlines, always.** Next-steps section names exact form (DIR-12, ADT-1, FC-GPR, DRC-06, Form 10-IEA, AOC-2, APL-01) + filing authority + deadline.
7. **Differentiation test embedded.** Every response self-checks: "could vanilla Claude in another tab have produced this?" If yes — fail, rewrite with artifacts (precedent table, IndianKanoon links, Vault hook, computation table, draft text).

---

## Operations

**Supervisor**: Backend runs under `_supervisor.py` which auto-restarts on crash. Logs at `backend/supervisor.log` + `backend/backend_live.log`.

**Health**: `GET /health` returns `{status, uptime_seconds, database, email_worker, dead_letter_count}`.

**Status**: `.\backend_status.ps1` shows supervisor + backend PIDs, memory, recent supervisor activity, and HTTP health.

**Resilience**:
- 429 retry-with-backoff on all model calls
- Cascade fallback (Emergent → direct OpenAI → cheaper sibling) so the user never sees a blank response
- Graceful degradation when Atlas/Firestore/Supermemory are down — pipeline still produces grounded answers from training, marked `[Unverified by corpus]` for honesty

---

## Security

- `.env` and `firebase-admin.json` are gitignored. Never commit secrets.
- PII Guard sanitizes user queries before LLM dispatch (PAN, Aadhaar, phone, addresses).
- Trust Layer verifies every citation against the corpus before rendering.
- Per-user matter scoping enforced on every Vault read.
- Audit log of every query (user, time, response hash) in MongoDB `spectr_logs.query_events`.

---

## Roadmap / not yet shipped

- Live Firestore RAG (project provisioned, database not yet created in GCP console — currently MongoDB Atlas only)
- Eval harness against the BharatLawBench-style benchmark (12 categories × 50 tasks)
- Full Vault → query grounding loop (currently Vault is read-only context, not yet surfaced as RAG citation source)
- Native mobile app
- Voice input / dictation

---

## License

Proprietary. © 2025 AlgoRythm Technologies. Built for Indian legal/tax professionals.

For commercial licensing or firm onboarding, contact: contact@algorythm.tech
