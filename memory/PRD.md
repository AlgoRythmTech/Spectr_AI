# Associate — PRD (Product Requirements Document)
## Built by AlgoRythm Group

### Original Problem Statement
Build a full-stack AI legal and financial intelligence platform called Associate — the Harvey.ai of India. Built for India's 1.5M lawyers, 160K CAs, and the world's largest legal system.

### Architecture
- **Frontend**: React + Tailwind CSS (white bg, Inter + IBM Plex Mono)
- **Backend**: FastAPI (Python) — async
- **Database**: MongoDB (statutes, users, sessions, documents, history, library)
- **AI**: Claude Opus 4.5 / Sonnet 4.5 via Emergent LLM Key
- **APIs**: IndianKanoon (case law), InstaFinancials (company data)
- **Auth**: Emergent Google OAuth + JWT session tokens
- **Storage**: Emergent Object Storage for document uploads
- **Export**: python-docx (Word), WeasyPrint (PDF)

### User Personas
1. **Litigation Lawyer** — Needs precedent research, drafting, deadline tracking
2. **Chartered Accountant** — Needs GST SCN responses, IT notice replies, compliance
3. **Corporate Counsel** — Needs due diligence, IBC applications, FEMA compliance
4. **Everyday User** — Needs plain-language legal guidance

### Core Requirements
- 5 modules: Assistant, Vault, Workflows, Library, History
- 20 pre-built workflows (10 litigation, 10 taxation)
- Structured AI responses (Issue → Law → Cases → Analysis → Exposure → Recommendation)
- Partner Mode / Everyday Mode toggle
- Document upload with auto-classification and analysis
- Word + PDF export
- 64 Indian statute sections indexed in MongoDB

### What's Been Implemented (March 20, 2026)
- [x] Landing page — stunning, professional, white bg
- [x] Google OAuth authentication via Emergent Auth
- [x] Dashboard layout with 240px sidebar, 5 navigation modules
- [x] Assistant module — Claude AI with IndianKanoon integration, statute DB, mode toggle
- [x] Vault module — file upload, document classification, 6 analysis types
- [x] Workflows module — all 20 workflows with form fields and document generation
- [x] Library module — CRUD for templates, playbooks, memos, annotations
- [x] History module — query audit trail with filters and search
- [x] Word (.docx) and PDF export
- [x] 64 Indian statute entries seeded (Income Tax, GST, Companies Act, IPC/BNS, CrPC/BNSS, CPC, NI Act, PMLA, FEMA, Consumer Protection, RERA, IBC, Arbitration, Specific Relief, TPA, Registration, SEBI)
- [x] IndianKanoon API integration (live case law search)
- [x] InstaFinancials API integration (company data search)
- [x] Emergent Object Storage for document uploads
- [x] Matter management system
- [x] ResponseCard component — structured memo-style AI responses

### Prioritized Backlog
#### P0 (Critical)
- [ ] Voice input for dictation
- [ ] Response streaming for better UX on long queries

#### P1 (Important)
- [ ] Custom workflow builder
- [ ] Excel (.xlsx) export for financial calculations
- [ ] Full InstaFinancials deep integration (company DD reports)
- [ ] Multi-language output (Hindi, Telugu, Tamil, Kannada, Marathi)
- [ ] Client profiles in Library
- [ ] Bulk document Q&A enhancements

#### P2 (Nice to have)
- [ ] Firm branding/letterhead upload
- [ ] Shared workspaces / collaboration
- [ ] Mobile-responsive design
- [ ] Email integration (ask@associate.ai)
- [ ] RBAC roles (Admin/Partner/Associate/Client-Guest)
- [ ] More comprehensive statute database (additional sections)
- [ ] Comparison mode for financial documents
- [ ] Redline suggestions for contracts

### Next Tasks
1. Add response streaming for Claude API (real-time output)
2. Expand statute database with more sections from all 18 acts
3. Build custom workflow builder
4. Add voice input/dictation
5. Implement multi-language support
