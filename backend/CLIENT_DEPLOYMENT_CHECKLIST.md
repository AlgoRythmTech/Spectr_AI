# Spectr — Client Deployment Checklist

## Before sending the hosted link to clients

### 1. Environment variables on the hosted server (MANDATORY)

```bash
# Server MUST set these before accepting traffic:
ENVIRONMENT=production
ALLOWED_ORIGINS=https://spectrhq.in,https://spectr.thealgorythm.in
FIRM_SHORT=spectr

# Server MUST NOT set:
# ALLOW_DEV_TOKEN  (any value — even "0" is OK; just don't set "1")
```

Without `ENVIRONMENT=production` and `FIRM_SHORT` set, the backend:
- Accepts the dev token (only from localhost, but still — a hole)
- Leaks a CRITICAL warning to logs

Without `ALLOWED_ORIGINS`, the backend:
- CORS-rejects every cross-origin request (fail-closed by design — good, but breaks UI)

### 2. MongoDB Atlas Network Access

Atlas currently shows `database: "error"` intermittently on `/health`. The cause is IP allowlist drift. Before clients arrive:

1. Log into MongoDB Atlas → Network Access
2. Add the hosted server's public IP to the allowlist
3. Or, for Railway/Render/Fly/Heroku where the IP is dynamic: add `0.0.0.0/0` temporarily (LESS SECURE — only for the pilot window)
4. Confirm `/health` returns `database: "connected"`

If Atlas stays "error" during the pilot, the in-memory Vault cache + Court Tracker stub will keep the UI working, but:
- Uploaded documents won't survive backend restart
- Tracked cases won't survive backend restart

### 3. Rotate the three keys that were in an old git commit

Commit `23c41fc` (Mar 2026) briefly committed `.env` before it was added to `.gitignore`. The keys exposed:

- `EMERGENT_LLM_KEY`
- `INDIANKANOON_API_KEY`
- `INSTAFINANCIALS_API_KEY`

Rotate each by logging into the respective dashboard, regenerating, and updating the production `.env`. Restart the backend.

### 4. API key credit/rate headroom

Spectr has been configured for 5 concurrent clients:
- LLM endpoints: 30 queries/IP/min (handles bursts)
- Upload endpoints: 30/IP/min
- Total estimated cost per client per day of active testing: ~$5-15 in Emergent credits

Check the Emergent dashboard:
- Credits remaining ≥ 200 for a multi-day pilot
- No RPM/TPM limits active

### 5. Frontend `.env`

Set `REACT_APP_BACKEND_URL` to your hosted backend URL on the frontend build:
```
REACT_APP_BACKEND_URL=https://api.spectrhq.in
```
(DO NOT use `localhost` or `127.0.0.1` for production.)

## What clients will see — feature inventory

### Assistant (main chat)
- Three modes: **Quick** (~10s), **Research** (~60-90s), **Depth Research** (3-5 min with sandbox browser research)
- Every response follows the 9-section shape:
  1. `## Bottom Line` (3-4 sentences, verdict first)
  2. `> **THE KILL-SHOT:**` callout (one-sentence ratio)
  3. `## Issues Framed` (numbered questions, each ≤22 words)
  4. `## Governing Framework` (statute + case + notification with pincite)
  5. `## Analysis` (one sub-head per issue, each with `> **KEY:**` callout)
  6. `## What the Department/Opponent Will Argue` (adversarial pre-emption)
  7. `## Risk Matrix` (tight table, 3-5 rows)
  8. `## Action Items` with `[CRITICAL]` / `[URGENT]` / `[KEY]` urgency tags (red/amber/grey pills + colored underlines)
  9. `## Authorities Relied On` + `## Research Provenance` (transparency footer)

### Vault (document analysis)
- Upload PDFs, DOCX, images, spreadsheets up to 50 MB
- Auto-classification (SCN, contract, judgment, etc.)
- Four skills per doc: Executive Summary, Night Before Digest, Chronological Timeline, Cross-Examination Matrix
- Custom Q&A per document

### Court Tracker
- Add case number + court, get live eCourts/NJDG scrape
- Auto-refresh per case
- Supports SC, HC, NCLT, CESTAT

### Workflows
- 25 filing-ready document templates (bail app, SCN reply, writ, cheque bounce notice, consumer complaint, etc.)
- DOCX download via `docx_file_id`

### Case Law Finder
- Natural-language scenario → LLM reformulation → IK live search → ranked results with pincites
- 10 results per query, verified against IK

## Backend operations — ops commands

Stored in `backend/`:
- `backend_start.ps1` — launch supervisor + backend (detached)
- `backend_status.ps1` — show supervisor PID + backend PID + `/health` + last 15 supervisor log lines
- `backend_stop.ps1` — clean shutdown (supervisor first to prevent relaunch)

Logs:
- `backend/supervisor.log` — restart events (each crash → uptime → relaunch)
- `backend/backend_stdout.log` / `backend/backend_stderr.log` — uvicorn output

## Known issues (non-blocking)

1. **Backend crashes every 15-20 min on Windows** (exit code 4294967295 = abnormal termination). Supervisor relaunches in ~3s. A client mid-query during a crash gets an error; next query works. Linux hosting should resolve this (it's a Windows-specific fork/thread issue with sentence-transformers).

2. **MongoDB Atlas "error"** when IP allowlist drifts. In-memory fallback keeps UI functional. Fix per step 2 above.

3. **Gemini 2.5-Pro 429s** constantly on the free tier — tier is disabled in the cascade. To re-enable after billing upgrade: set `ENABLE_GEMINI_PRO_TIER=1` in env.

## First-query cold start

The FIRST query a client makes on a fresh backend takes 2-3 min because:
- Sentence-transformer model loads
- MongoDB connection pool warms
- Sandbox browser spins up (Depth Research only)

**Pre-warm before sending the link:**
```bash
# On the hosted server after starting:
curl -X POST -H 'Authorization: Bearer <test-token>' \
  -H 'Content-Type: application/json' \
  -d '{"query":"hi","mode":"everyday"}' \
  https://api.spectrhq.in/api/assistant/query > /dev/null
```

Subsequent queries from all clients hit warm caches.

## Golden queries for the pilot

Paste these into the Assistant in Research mode to showcase depth:

1. **GST SCN — 74:** *"Client received SCN under Section 74 CGST for Rs 48 lakh ITC mismatch FY 2019-20. SCN dated 2 Jan 2025. Draft reply covering limitation, ITC entitlement, natural justice."*
2. **DPDP / Right to be Forgotten:** *"Client acquitted 12 years ago approaches us to erase his judicial records from NJDG under DPDP Section 12(3). Draft our opinion on maintainability given post-2024 SC stays."*
3. **Constitutional writ:** *"Draft writ to challenge Union notification mandating Aadhaar-based biometric for all social media users > 50K followers. Cite Puttaswamy II, Article 14/19/21."*
4. **BNS bail:** *"Client arrested 40 days under BNS S.318 cheating. First-time offender, fixed Mumbai address. Draft bail application under BNSS S.483."*

Each showcases a different strength: tax depth, DPDP/constitutional interplay, constitutional writ drafting, criminal code fluency.
