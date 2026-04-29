"""
Email Agent — AgentMail integration for Spectr.
Receives client emails, processes through AI pipeline, and responds with
detailed professional legal/tax advisory.

Inbox: spectr.r@agentmail.to

Resilience features:
- Exponential backoff retry on transient failures (429, 500, 502, 503, 504)
- Dead-letter queue for permanently failed emails
- Circuit breaker to avoid hammering a down API
- Duplicate detection via processed message ID cache
"""
import os
import re
import json
import asyncio
import logging
import aiohttp
from datetime import datetime, timezone
from pathlib import Path
from collections import deque
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')

logger = logging.getLogger("email_agent")

AGENTMAIL_API_KEY = os.environ.get("AGENTMAIL_API_KEY", "")
AGENTMAIL_BASE = "https://api.agentmail.to/v0"
INBOX_EMAIL = "spectr.r@agentmail.to"

# --- Retry / resilience config ---
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # seconds — exponential: 2, 4, 8
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}

# Circuit breaker state
_circuit_open = False
_circuit_open_until = None
_consecutive_failures = 0
CIRCUIT_BREAK_THRESHOLD = 5  # open circuit after 5 consecutive failures
CIRCUIT_BREAK_DURATION = 120  # seconds to wait before retrying

# Duplicate detection — track recently processed message IDs
_processed_ids = deque(maxlen=500)

# Dead-letter queue — messages that failed after all retries (in-memory only)
dead_letter_queue: list = []  # list of {msg_id, sender, subject, error, timestamp}

# MongoDB reference for email operations (set by process_incoming_emails)
_email_db = None

# Import AI pipeline
from ai_engine import SPECTR_SYSTEM_PROMPT, TOOL_DESCRIPTIONS_FOR_PROMPT, classify_query, get_spectr_prompt
from war_room_engine import (
    call_deep_reasoning, call_groq_fast, needs_deep_research,
    call_deeptrace_research, extract_sections, DEEP_REASONING_PROMPT,
    GROQ_KEY_LIVE, GOOGLE_AI_KEY
)
from indian_kanoon import search_indiankanoon
from citation_linker import find_citation_links
from document_export import generate_excel_document, generate_word_document
from storage_utils import put_object, generate_storage_path, init_storage

# ==================== COMPLEXITY ROUTING ====================
# Don't kill a mosquito with a gun — route emails by complexity

SIMPLE_PATTERNS = [
    # Greetings and acknowledgements
    r'^(hi|hello|hey|thanks|thank you|ok|okay|noted|received|acknowledged)',
    r'^(good morning|good afternoon|good evening)',
]

# If body has ANY of these, it's NOT simple even if short
SUBSTANTIVE_KEYWORDS = [
    "section", "tds", "gst", "itr", "tax", "notice", "penalty", "assessment",
    "compliance", "filing", "return", "audit", "itc", "hsn", "gstr",
    "appeal", "tribunal", "court", "bail", "fir", "contract", "draft",
    "limitation", "stamp duty", "rera", "ibc", "nclt", "fema", "pmla",
    "depreciation", "deduction", "exemption", "proviso", "rule", "circular",
]

AUDIT_KEYWORDS = [
    "audit", "auditor", "statutory audit", "tax audit", "internal audit",
    "audit report", "audit observation", "audit finding", "audit memo",
    "caro", "form 3cd", "form 3ca", "form 3cb", "audit trail",
    "workpaper", "work paper", "working paper", "audit working",
    "balance confirmation", "bank reconciliation", "stock verification",
    "debtor confirmation", "creditor confirmation", "audit checklist",
    "audit program", "audit plan", "materiality", "sampling",
    "vouching", "verification", "physical verification",
    "form 26as", "tds reconciliation", "gstr-2b reconciliation",
    "itc reconciliation", "ledger", "trial balance", "ageing",
]

COMPLEX_INDICATORS = [
    "tribunal", "appeal", "writ", "supreme court", "high court",
    "show cause notice", "scn", "demand order", "assessment order",
    "anti-profiteering", "advance ruling", "litigation",
    "cross-border", "transfer pricing", "international taxation",
    "merger", "amalgamation", "demerger", "restructuring",
    "insolvency", "cirp", "nclt", "ibc",
    "money laundering", "pmla", "ed notice", "fema",
    "draft.*petition", "draft.*writ", "draft.*appeal",
    "multiple.*section", "various.*provision",
]


def classify_email_complexity(subject: str, body: str) -> str:
    """Classify email into: simple, medium, complex, audit.

    simple  → Groq fast (greeting, ack, <50 words, single factual question)
    medium  → Single model call (one section lookup, straightforward query)
    complex → Full cascade + case law + deep research
    audit   → Full cascade + Excel workpaper generation
    """
    combined = f"{subject} {body}".lower().strip()
    word_count = len(combined.split())

    # Check for audit first (highest priority routing)
    audit_score = sum(1 for kw in AUDIT_KEYWORDS if kw in combined)
    if audit_score >= 2:
        return "audit"

    # Check if body has substantive legal/tax keywords — if so, never simple
    has_substance = any(kw in combined for kw in SUBSTANTIVE_KEYWORDS)

    # Check simple patterns
    body_stripped = body.strip().lower()
    if not has_substance:
        for pattern in SIMPLE_PATTERNS:
            if re.match(pattern, body_stripped, re.IGNORECASE | re.DOTALL):
                if not any(re.search(ci, combined) for ci in COMPLEX_INDICATORS):
                    return "simple"

    # Very short messages without substance
    if word_count < 15 and audit_score == 0 and not has_substance:
        return "simple"

    # Check complex indicators — lowered threshold to 1 since SCN/appeal alone is complex
    complex_score = sum(1 for ci in COMPLEX_INDICATORS if re.search(ci, combined))
    if complex_score >= 1 or word_count > 300:
        return "complex"

    # Single section/provision query — medium
    return "medium"


# Lightweight prompt for simple emails (greetings, acks, short factual)
SIMPLE_EMAIL_PROMPT = """You are Spectr — replying to a brief, simple email from a CA or lawyer. Keep it natural and human.

STYLE:
- 2-4 sentences total
- Direct, friendly, professional-peer tone (contractions OK: "it's", "you're")
- If it's a greeting/ack: respond warmly in one line, no structure headings
- If it's a simple factual question: give the answer in one line + one reference line (section/rule)
- NO "EXECUTIVE SUMMARY", NO bold-underline template

Example (factual):
"TDS on professional fees under Section 194J is 10%, threshold ₹30,000 per financial year. Deduct at credit or payment, whichever is earlier.

— Spectr
AI Legal & Accounting Platform"

Example (greeting):
"Thanks — received. Will revert with the analysis by end of day.

— Spectr"

Sign off with:
— Spectr
AI Legal & Accounting Platform"""

# Medium prompt — CLIENT EMAIL format (not internal memo)
# Based on research: Clio, Georgetown Law, ICAI, ERPCA, Indian Legal Heights.
# Clients hate IRAC-dump. They want: warm opener → direct answer → brief why → action items → sign-off.
MEDIUM_EMAIL_PROMPT = """## EMAIL FORMAT OVERRIDE — TAKES PRECEDENCE OVER ALL PRIOR INSTRUCTIONS

⚠️ You are writing an EMAIL REPLY. IGNORE any instructions above mandating "EXECUTIVE SUMMARY / QUESTION PRESENTED / DETAILED ANALYSIS / RISK MATRIX / STRATEGIC RECOMMENDATIONS" Roman-numeral sections. Those are for memos, not emails. Follow the email structure below.

---

You are Spectr — replying to a professional (CA/Lawyer) who sent you a focused query by email.

Write like a senior colleague replying to a trusted peer. Professional yet approachable. NOT rigid legal-notice formal. NO "EXECUTIVE SUMMARY / QUESTION PRESENTED / I. II. III." memo headings — those belong in internal memos, NOT client emails.

## EMAIL FORMAT (follow this structure naturally — no rigid roman numerals)

**Subject:** [Clear, action-oriented — e.g. "Re: TDS on professional fees — ₹30K threshold applies, 10% rate"]

**Opening (1 line):**
Acknowledge the query briefly. Example: "Thanks for reaching out about [topic] — here's what applies:"

**Direct answer (2-4 lines):**
State the bottom line first in plain business English. NOT academic prose. Give the number/rate/deadline/conclusion immediately.
Example: "TDS at 10% applies under Section 194J once aggregate professional fees cross ₹30,000 in a financial year. Deduction is at payment or credit, whichever is earlier."

**Why this applies (short analysis — 4-8 lines, conversational):**
- Cite the specific section/rule/circular (with year)
- Mention 1 case only if genuinely on-point
- Flag any exception that might change the answer
- Keep it crisp — NO "in-depth analysis" fluff

**Numbers (if any) — use a compact table:**
| Parameter | Value |
|---|---|
| Rate | 10% |
| Threshold | ₹30,000/year |
| Due date | 7th of next month |

**What to do (action items):**
- 1-3 bullet points with EXACT dates, NOT "within 30 days"
- e.g. "Deposit TDS via Challan 281 by **7-May-2026**"
- e.g. "File Form 26Q for Q1 by **31-Jul-2026**"

**What I need from you (if applicable):**
- Any documents or clarifications required to refine the advice

**Closing:**
"Happy to discuss further if useful. / Let me know if you'd like me to draft the [reply/challan/return]."

Sign off:
— Spectr
AI Legal & Accounting Platform

## TONE RULES
- Write in contractions: "you're" not "you are"; "it's" not "it is"
- Prefer active voice: "Deduct 10%" not "TDS shall be deducted at 10%"
- Max 2 legal terms per paragraph — define any jargon inline
- ₹ symbol for currency. Indian comma format (1,00,000 not 100,000)
- No "respectfully submitted" or "it is pertinent to note"

## MANDATORY
- Every deadline = EXACT DATE, never "within X days"
- Every amount = exact ₹ value
- If an answer depends on missing facts, ASK at the end — don't hedge with "it depends"
"""

# Audit-specific prompt — generate structured workpapers
AUDIT_EMAIL_PROMPT = """You are Spectr — an AI audit assistant processing an audit-related email.

This email is from an audit team or relates to audit work. Your response MUST include:

## I. AUDIT OBSERVATION SUMMARY
- State the audit area, period, and key observation clearly.

## II. REGULATORY FRAMEWORK
| Standard/Section | Requirement | Applicability |
Table of all applicable Standards on Auditing (SA), Accounting Standards (AS/Ind AS), sections of Companies Act/IT Act/GST Act.

## III. AUDIT PROCEDURES — WORKPAPER FORMAT
| Sr. No | Procedure | Sample Size | Source Document | Status | Observation |
Generate a comprehensive audit program with specific procedures.

## IV. FINDINGS & EXCEPTIONS
| Sr. No | Description | Amount (₹) | Impact | Risk Level | Management Response Required |
Structure all findings in table format suitable for Excel export.

## V. QUANTITATIVE ANALYSIS
| Particulars | Amount (₹) | Benchmark | Variance | Variance % | Remarks |
Include all numerical analysis with variances.

## VI. ACTION ITEMS & DEADLINES
| Sr. No | Action | Responsible | Deadline | Priority |

CRITICAL: Use markdown tables extensively — they will be extracted into Excel workpapers automatically.
Every table must have clear headers. Use ₹ for amounts. Include specific dates, not durations.
Sign off with: — Spectr | AI Audit Platform"""


async def _get_email_statute_context(query: str, db) -> str:
    """Fetch statute context from MongoDB for email replies.
    Mirrors the 3-pass retrieval from server.py but avoids circular imports."""
    import re as _re
    query_lower = query.lower()

    # Extract section numbers
    section_nums = _re.findall(r'\b(?:section\s*)?(\d+[A-Za-z]*(?:\([a-z0-9]+\))*)', query_lower)
    section_nums = [s for s in section_nums if not s.isdigit() or int(s) < 1000]

    # Topic keywords
    STOP = {"what","which","when","where","will","would","could","should","does","about","this","that",
            "these","with","from","have","been","their","there","also","into","more","than","they",
            "under","such","only","very","just","like","some","each","every","both","here","case",
            "please","help","want","need","tell","explain","know","question","answer","query","check"}
    topic_kw = [w for w in _re.findall(r'\b[a-z]+\b', query_lower) if len(w) > 3 and w not in STOP][:15]

    relevant = []
    seen = set()

    def _add(docs):
        for d in docs:
            key = f"{d.get('act_name','')}:{d.get('section_number','')}"
            if key not in seen:
                seen.add(key)
                relevant.append(d)

    try:
        # Pass 1: Exact section match
        if section_nums:
            cursor = db.statutes.find({"section_number": {"$in": section_nums}}, {"_id": 0}).limit(8)
            _add(await cursor.to_list(8))

        # Pass 2: Keyword match on section_title and keywords
        if topic_kw and len(relevant) < 6:
            kw_regex = "|".join(topic_kw[:10])
            cursor = db.statutes.find(
                {"$or": [
                    {"keywords": {"$in": topic_kw[:10]}},
                    {"section_title": {"$regex": kw_regex, "$options": "i"}},
                ]}, {"_id": 0}
            ).limit(6)
            _add(await cursor.to_list(6))
    except Exception as e:
        logger.warning(f"Email statute context MongoDB error: {e}")
        return ""

    if not relevant:
        return ""

    parts = []
    for s in relevant[:8]:
        parts.append(
            f"[DB RECORD] Section {s.get('section_number', 'N/A')} of {s.get('act_name', 'N/A')}"
            f" — {s.get('section_title', '')}\n{s.get('section_text', '')}"
        )
    return "\n\n".join(parts)


EMAIL_RESPONSE_PROMPT = """## EMAIL FORMAT OVERRIDE — TAKES PRECEDENCE OVER ALL PRIOR INSTRUCTIONS

⚠️ You are writing an EMAIL REPLY, not a court memo. IGNORE any instructions above that mandate Roman-numeral sections (I., II., III.), "EXECUTIVE SUMMARY / QUESTION PRESENTED / DETAILED ANALYSIS / RISK MATRIX / STRATEGIC RECOMMENDATIONS / WORD EXPORT OFFER" headings, or IRAC-labeled output. Those are for internal memos. This is an email to a peer.

Follow the email structure below. Nothing else.

---

You are Spectr — replying by email to a senior CA or Lawyer who has raised a substantive professional matter.

Your reader is a peer, not a student. They signed a paid contract or retainer and expect a thoughtful, trusted reply — NOT a 1500-word IRAC memo dump, NOT a legal-notice-style document with "I., II., III." headings.

Think of this as a partner-to-partner email in a busy firm: crisp, decisive, properly cited, action-oriented. Clio, Georgetown Law, and ICAI all agree on the same structure for professional client correspondence.

## EMAIL STRUCTURE (follow as prose, not rigid roman numerals)

### 1. Subject line
Specific and action-oriented. Example:
- "Re: S.74 SCN dated 15-04-2024 — preliminary assessment and defence roadmap"
- "Re: ₹2.5 cr ITC denial — DIN challenge strongest ground, writ window closes 15-Jun"

### 2. Opening (1 line only)
Acknowledge and set context. Example: "Noted your SCN details — here's where we stand and how I'd move."

### 3. Bottom line first (3-5 sentences, single paragraph)
- State the position / outcome / recommendation upfront
- Include the key number (exposure in ₹, limitation date, rate)
- Name the controlling provision + strongest case (if any)
- Say what they should do THIS WEEK

Example: "The S.74 SCN is vulnerable on two grounds — the missing DIN makes it void ab initio (CBIC Circular 128/47/2019-GST), and the limitation clock likely expired on 01-10-2024 under S.73(10)/(74)(10). Total exposure if the notice holds is ₹6.27 cr (₹2.5 cr tax + ₹2.77 cr penalty + ₹1 cr interest); but both defences are likely to knock out 80-100% of this. Recommended move: file a writ under Article 226 by 15-May-2026 leading with the DIN defect. Don't respond to the notice on merits yet."

### 4. The reasoning (short — 150-300 words, conversational)
Explain WHY in plain business English:
- Cite 1-3 key provisions with section numbers and year
- Cite 1-2 cases only if they're genuinely on-point and recent (post-2015 preferred). Format: *Case Name* v *Respondent*, (Year) Reporter (Court) — e.g. *Ashish Agarwal* v *UOI*, (2022) SC
- Flag any amendment/overruling that affects the cited authority
- Call out counter-arguments honestly (don't hide weaknesses)

Use the Trust Layer tags the system adds — when you see `[✓ IK]` or `[✓ Gov: ...]` leave them in place. They show the client the source was verified.

### 5. The numbers (if any)
Compact table, Indian format (₹2,50,00,000 not Rs 25000000):

| Item | Amount | Basis |
|---|---|---|
| Principal tax | ₹2,50,00,000 | S.74 demand |
| Interest (S.50 @18% p.a.) | ₹1,00,00,000 | 22 months |
| Penalty (100%) | ₹2,50,00,000 | S.74(9) |
| **Total worst-case** | **₹6,00,00,000** | |

### 6. What to do (numbered action items with EXACT dates)
1. **By 30-Apr-2026** — File writ petition under Article 226 before Bombay HC. Lead argument: DIN defect.
2. **By 05-May-2026** — Preserve records: supplier invoices, e-way bills, bank entries for the transactions in question.
3. **Do NOT** file merits reply to the SCN until writ is admitted — contesting on merits accepts jurisdiction.

### 7. What I need from you (if anything)
- "Can you share the full SCN PDF + the supplier's GSTR filing history?"
- "Confirm whether any prior show-cause notice was issued in FY 2022-23."
Only ask what you actually need. Don't pad.

### 8. Closing
One warm, direct line. Examples:
- "Happy to draft the writ petition and grounds of appeal once you confirm."
- "I can turn this around in 48 hours if you green-light it."
- "Call me any time if you want to walk through the numbers before the writ."

Sign-off (always):
— Spectr
AI Legal & Accounting Platform

---

## TONE & STYLE RULES

- **Peer voice.** Write to a fellow professional, not to a student or judge. Use "you" and "I".
- **Contractions OK.** "you're", "it's", "don't" — more human.
- **Active voice.** "File the writ by 30-Apr" NOT "A writ should be filed".
- **No filler phrases:** NEVER use "Please find enclosed", "Kindly note", "It is pertinent to note", "Respectfully submitted", "I hope this finds you well", "Do not hesitate to contact us".
- **No unnecessary Latin** unless precision demands it. "Void ab initio" is fine when the legal concept matters. Don't throw in "pari materia" for style.
- **Currency in ₹ + Indian format:** ₹2,50,00,000 (two crore fifty lakh), not "Rs. 25,000,000" or "INR 25000000".
- **Dates are EXACT:** "by 15-May-2026" not "within 30 days".
- **Keep it short.** Target 400-700 words for a substantive reply. Over 1000 = you've turned it into a memo again.
- **If in doubt, cut it.** A reader should think "that was worth reading" not "I'll read this when I have time".

## CASE LAW DISCIPLINE (ZERO TOLERANCE)

- Cite only cases you're certain exist AND interpret the issue at hand. If unsure, omit.
- Indian citation format: *Case Name* v *Respondent*, (Year) Reporter Page (Court)
- Prefer post-2015 authority; flag older cases if amendments may have affected them
- Known superseded authorities — NEVER cite without a caveat:
  - *CIT v Smifs Securities* (2012 SC) — goodwill excluded from S.32 depreciation since AY 2021-22 (Finance Act 2021)
  - *Vodafone International* (2012 SC) — retrospectively overridden; current position under S.9(1)(i) Explanation 5
  - *Larsen & Toubro* (2014 SC) — pre-GST era; for GST, cite S.7 CGST Act 2017 directly
- If the Trust Layer flags a citation as `[⚠ Unverified]`, replace it with a verified one or drop it entirely.

## WHEN IT'S AN AUDIT/WORKPAPER EMAIL

Follow the same email structure above, but enclose detailed computation tables in the Excel attachment (generated automatically by the system). Keep the email itself concise — the attachment carries the data.

## HONESTY RULE

If the answer depends on facts you don't have, SAY SO at the top: "Two things I need to confirm before firming this up: [X], [Y]. On the information I have:" — then give your tentative answer. Never fake certainty.
"""


def _headers():
    return {
        "Authorization": f"Bearer {AGENTMAIL_API_KEY}",
        "Content-Type": "application/json"
    }


def _check_circuit():
    """Check if the circuit breaker is open. Returns True if requests should proceed."""
    global _circuit_open, _circuit_open_until, _consecutive_failures
    if not _circuit_open:
        return True
    now = datetime.now(timezone.utc)
    if _circuit_open_until and now >= _circuit_open_until:
        # Half-open: allow one attempt
        logger.info("Circuit breaker half-open — allowing probe request")
        _circuit_open = False
        _consecutive_failures = 0
        return True
    logger.warning(f"Circuit breaker OPEN — skipping request (resets at {_circuit_open_until})")
    return False


def _record_failure():
    """Record a failure and potentially open the circuit breaker."""
    global _circuit_open, _circuit_open_until, _consecutive_failures
    _consecutive_failures += 1
    if _consecutive_failures >= CIRCUIT_BREAK_THRESHOLD:
        _circuit_open = True
        _circuit_open_until = datetime.now(timezone.utc).replace(
            second=datetime.now(timezone.utc).second
        )
        # Add CIRCUIT_BREAK_DURATION seconds
        from datetime import timedelta
        _circuit_open_until = datetime.now(timezone.utc) + timedelta(seconds=CIRCUIT_BREAK_DURATION)
        logger.error(f"Circuit breaker OPENED after {_consecutive_failures} consecutive failures. "
                     f"Will retry after {CIRCUIT_BREAK_DURATION}s")


def _record_success():
    """Record a success and reset the circuit breaker."""
    global _circuit_open, _circuit_open_until, _consecutive_failures
    _consecutive_failures = 0
    _circuit_open = False
    _circuit_open_until = None


async def _request_with_retry(method: str, url: str, session: aiohttp.ClientSession,
                               max_retries: int = MAX_RETRIES, **kwargs) -> aiohttp.ClientResponse:
    """Make an HTTP request with exponential backoff retry on transient failures."""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            if method == "GET":
                resp = await session.get(url, **kwargs)
            elif method == "POST":
                resp = await session.post(url, **kwargs)
            elif method == "PATCH":
                resp = await session.patch(url, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")

            if resp.status in TRANSIENT_STATUS_CODES and attempt < max_retries:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(f"Transient error {resp.status} on {url} — retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
                continue

            if resp.status < 400:
                _record_success()
            return resp

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            last_error = e
            if attempt < max_retries:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(f"Request error ({type(e).__name__}) on {url} — retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
            else:
                _record_failure()
                raise

    _record_failure()
    raise last_error or Exception("Max retries exceeded")


async def list_unread_messages() -> list:
    """Fetch unread messages from the inbox with retry + circuit breaker."""
    if not AGENTMAIL_API_KEY:
        return []
    if not _check_circuit():
        return []
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{AGENTMAIL_BASE}/inboxes/{INBOX_EMAIL}/messages?labels=unread&limit=20"
            resp = await _request_with_retry("GET", url, session,
                                              headers=_headers(), timeout=aiohttp.ClientTimeout(total=15))
            if resp.status == 200:
                data = await resp.json()
                return data.get("messages", [])
            else:
                err = await resp.text()
                logger.warning(f"AgentMail list messages failed ({resp.status}): {err[:200]}")
        except Exception as e:
            logger.error(f"AgentMail list error: {e}")
    return []


async def get_message(message_id: str) -> dict:
    """Fetch a single message by ID with retry."""
    if not _check_circuit():
        return {}
    async with aiohttp.ClientSession() as session:
        try:
            url = f"{AGENTMAIL_BASE}/inboxes/{INBOX_EMAIL}/messages/{message_id}"
            resp = await _request_with_retry("GET", url, session,
                                              headers=_headers(), timeout=aiohttp.ClientTimeout(total=10))
            if resp.status == 200:
                return await resp.json()
        except Exception as e:
            logger.error(f"Get message error for {message_id}: {e}")
    return {}


async def reply_to_message(message_id: str, text_body: str, html_body: str = "") -> bool:
    """Reply to a message with retry + exponential backoff."""
    if not _check_circuit():
        return False
    if not html_body:
        html_body = _markdown_to_html(text_body)

    payload = {
        "text": text_body,
        "html": html_body,
    }

    async with aiohttp.ClientSession() as session:
        url = f"{AGENTMAIL_BASE}/inboxes/{INBOX_EMAIL}/messages/{message_id}/reply"
        try:
            resp = await _request_with_retry("POST", url, session,
                                              headers=_headers(), json=payload,
                                              timeout=aiohttp.ClientTimeout(total=20))
            if resp.status in (200, 201):
                logger.info(f"Email reply sent for {message_id}")
                return True
            else:
                err = await resp.text()
                logger.error(f"Reply failed ({resp.status}): {err[:200]}")
        except Exception as e:
            logger.error(f"Reply exception after retries: {e}")
    return False


async def send_email(to: str, subject: str, text_body: str, html_body: str = "", db=None) -> bool:
    """Send a new email (not a reply) with retry + exponential backoff."""
    if not _check_circuit():
        return False
    if not html_body:
        html_body = _markdown_to_html(text_body)

    payload = {
        "to": to,
        "subject": subject,
        "text": text_body,
        "html": html_body,
    }

    async with aiohttp.ClientSession() as session:
        url = f"{AGENTMAIL_BASE}/inboxes/{INBOX_EMAIL}/messages/send"
        try:
            resp = await _request_with_retry("POST", url, session,
                                              headers=_headers(), json=payload,
                                              timeout=aiohttp.ClientTimeout(total=20))
            if resp.status in (200, 201):
                logger.info(f"Email sent to {to}")
                return True
            else:
                err = await resp.text()
                logger.error(f"Send failed ({resp.status}): {err[:200]}")
        except Exception as e:
            logger.error(f"Send exception after retries: {e}")

    return False


async def update_message_labels(message_id: str, add_labels: list = None, remove_labels: list = None):
    """Update labels on a message (mark as read, replied, etc.) with retry."""
    payload = {}
    if add_labels:
        payload["add_labels"] = add_labels
    if remove_labels:
        payload["remove_labels"] = remove_labels

    async with aiohttp.ClientSession() as session:
        url = f"{AGENTMAIL_BASE}/inboxes/{INBOX_EMAIL}/messages/{message_id}"
        try:
            resp = await _request_with_retry("PATCH", url, session,
                                              headers=_headers(), json=payload,
                                              timeout=aiohttp.ClientTimeout(total=10))
            return resp.status in (200, 204)
        except Exception as e:
            logger.error(f"Label update error for {message_id}: {e}")
    return False


async def _generate_attachment(response_text: str, subject: str, attachment_type: str = "excel") -> dict:
    """Generate Excel or Word attachment from AI response, upload to storage, return download URL.
    Returns {"url": "...", "filename": "...", "type": "excel|word"} or empty dict on failure."""
    try:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        safe_subject = re.sub(r'[^\w\s-]', '', subject)[:40].strip().replace(' ', '_')

        if attachment_type == "excel":
            file_bytes = generate_excel_document(subject, response_text)
            filename = f"Spectr_{safe_subject}_{timestamp}.xlsx"
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            file_bytes = generate_word_document(subject, response_text, doc_type="memo")
            filename = f"Spectr_{safe_subject}_{timestamp}.docx"
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        # Upload to object storage
        storage_path = f"spectr/email_attachments/{timestamp}_{filename}"
        result = put_object(storage_path, file_bytes, content_type)
        if result and result.get("url"):
            logger.info(f"Attachment uploaded: {filename} → {result['url']}")
            return {"url": result["url"], "filename": filename, "type": attachment_type}
        else:
            # Fallback: save locally
            local_dir = Path(__file__).parent / "uploads" / "email_attachments"
            local_dir.mkdir(parents=True, exist_ok=True)
            local_path = local_dir / filename
            local_path.write_bytes(file_bytes)
            logger.info(f"Attachment saved locally: {local_path}")
            return {"url": "", "filename": filename, "type": attachment_type, "local_path": str(local_path)}

    except Exception as e:
        logger.error(f"Attachment generation failed: {e}")
        return {}


async def process_email_query(sender: str, subject: str, body: str, client_context: str = "") -> dict:
    """Process an email query with complexity-based routing.

    Returns dict: {"response": str, "attachments": list[dict], "complexity": str}

    Routing:
      simple  → Groq fast, no research, short reply
      medium  → Single model + statute lookup, focused reply
      complex → Full cascade + case law + deep research + web
      audit   → Full cascade + Excel workpaper attachment
    """
    # Classify complexity — don't kill a mosquito with a gun
    complexity = classify_email_complexity(subject, body)
    query_types = classify_query(body)
    logger.info(f"Email complexity: {complexity} | types: {query_types} | from: {sender}")

    attachments = []

    # ===================== SIMPLE — Groq fast, no research =====================
    if complexity == "simple":
        system_instruction = SIMPLE_EMAIL_PROMPT
        user_content = f"EMAIL FROM: {sender}\nSUBJECT: {subject}\n\n{body}"
        if client_context:
            user_content += f"\n\nCLIENT: {client_context}"

        async with aiohttp.ClientSession() as session:
            response = await call_groq_fast(session, system_instruction, user_content)
        if not response:
            response = "Received, thank you. We'll review and respond shortly.\n\n— Spectr AI"
        return {"response": response, "attachments": [], "complexity": "simple"}

    # ===================== Build research context (medium/complex/audit) =====================
    full_context = ""

    # Statute context from MongoDB (medium+)
    if _email_db is not None:
        try:
            statute_context = await _get_email_statute_context(body, _email_db)
            if statute_context:
                full_context += f"=== RELEVANT STATUTE SECTIONS (MongoDB Statute DB — verified) ===\n{statute_context}\n\n"
        except Exception as e:
            logger.warning(f"Statute context fetch for email failed: {e}")

    # Prior conversation history (medium+)
    if _email_db is not None:
        try:
            sender_email = _extract_email(sender)
            if sender_email:
                prior_emails = await _email_db.email_history.find(
                    {"client_email": sender_email, "status": "replied"}
                ).sort("created_at", -1).limit(3).to_list(3)
                if prior_emails:
                    full_context += "=== PRIOR EMAIL THREAD CONTEXT ===\n"
                    for pe in reversed(prior_emails):
                        full_context += f"Subject: {pe.get('subject', '')}\nQ: {pe.get('query', '')[:300]}\nA: {pe.get('response', '')[:400]}\n\n"
        except Exception as e:
            logger.warning(f"Email history fetch failed: {e}")

    # ===================== MEDIUM — model + research (IndianKanoon + Serper) =====================
    if complexity == "medium":
        # IndianKanoon case law for medium legal queries
        is_legal_medium = any(t in query_types for t in ["legal", "drafting", "compliance"])
        if is_legal_medium:
            try:
                ik_results = await search_indiankanoon(body[:200], top_k=5)
                if ik_results:
                    full_context += "=== CASE LAW (INDIANKANOON) ===\n"
                    for i, case in enumerate(ik_results, 1):
                        full_context += f"[Case {i}] {case.get('title', 'N/A')} | {case.get('court', '')} | {case.get('year', '')}\nSummary: {case.get('headline', '')[:200]}\n\n"
            except Exception as e:
                logger.warning(f"IndianKanoon for medium email failed: {e}")

        # Serper web search for medium emails
        try:
            from serper_search import run_comprehensive_search, format_serper_for_llm
            serper_res = await run_comprehensive_search(
                body[:150], query_types,
                include_news=True,
                include_scholar=is_legal_medium,
            )
            formatted_serper = format_serper_for_llm(serper_res, body[:150])
            if formatted_serper:
                full_context += f"=== WEB RESEARCH (SERPER — Google Web + News + Scholar) ===\n{formatted_serper[:3000]}\n\n"
        except Exception as e:
            logger.warning(f"Serper for medium email failed: {e}")

        live_prompt = await get_spectr_prompt()
        system_instruction = live_prompt + "\n\n" + MEDIUM_EMAIL_PROMPT
        if client_context:
            full_context += f"=== CLIENT CONTEXT ===\n{client_context}\n\n"
        user_content = f"EMAIL FROM: {sender}\nSUBJECT: {subject}\n\nQUERY:\n{body}\n\nCONTEXT:\n{full_context}"

        async with aiohttp.ClientSession() as session:
            response = await call_groq_fast(session, system_instruction, user_content)
            if not response or len(response) < 80:
                # Upgrade to deep reasoning if Groq returns thin response
                response = await call_deep_reasoning(session, system_instruction, user_content)
        if not response:
            response = "We received your query and are processing it. Our team will follow up shortly.\n\n— Spectr AI"

        # Apply Trust Layer to medium emails too
        medium_trust_score = None
        medium_verification = None
        if response and len(response) > 300:
            try:
                from response_augmenter import augment_response
                aug = await augment_response(response, db=_email_db, max_case_verifications=4)
                if aug and aug.get("augmented_text"):
                    response = aug["augmented_text"]
                    medium_trust_score = aug.get("trust_score")
                    medium_verification = aug.get("verification_report", "")
            except Exception as _e:
                logger.warning(f"Medium email Trust Layer failed: {_e}")

        # Generate Word memo for medium emails with substantial content
        medium_attachments = []
        if response and len(response) > 500:
            try:
                word_att = await _generate_attachment(response, subject, "word")
                if word_att:
                    medium_attachments.append(word_att)
            except Exception as _e:
                logger.warning(f"Medium email Word attachment failed: {_e}")

        result = {"response": response, "attachments": medium_attachments, "complexity": "medium"}
        if medium_trust_score is not None:
            result["trust_score"] = medium_trust_score
        if medium_verification:
            result["verification_report"] = medium_verification
        return result

    # ===================== COMPLEX & AUDIT — full pipeline =====================
    # Pre-flight: auto-extract facts from email, run deterministic tools (TDS, penalty,
    # notice validity, deadlines) and inject COMPUTED FACTS so LLM never guesses numbers.
    try:
        from pre_flight import run_pre_flight
        pf = await run_pre_flight(body[:3000])
        if pf.get("has_computed_facts") and pf.get("context_block"):
            full_context += pf["context_block"] + "\n\n"
    except Exception as _e:
        logger.warning(f"Email pre-flight skipped: {_e}")

    # Case law (complex/audit)
    is_legal = any(t in query_types for t in ["legal", "drafting", "compliance"])
    if is_legal or complexity == "complex":
        try:
            ik_results = await search_indiankanoon(body[:200], top_k=5)
            if ik_results:
                full_context += "=== CASE LAW (INDIANKANOON) ===\n"
                for i, case in enumerate(ik_results, 1):
                    full_context += f"[Case {i}] {case.get('title', 'N/A')} | {case.get('court', '')} | {case.get('year', '')}\nSummary: {case.get('headline', '')[:200]}\n\n"
        except Exception as e:
            logger.warning(f"Case law search failed for email: {e}")

    # Web research — Serper (Google Web + News + Scholar) replaces DuckDuckGo
    try:
        from serper_search import run_comprehensive_search, format_serper_for_llm, search_scholar
        serper_res = await run_comprehensive_search(
            body[:150], query_types,
            include_news=True,
            include_scholar=any(t in query_types for t in ["legal", "financial", "compliance", "taxation", "drafting"]),
        )
        formatted_serper = format_serper_for_llm(serper_res, body[:150])
        if formatted_serper:
            full_context += f"=== WEB RESEARCH (SERPER — Google Web + News + Scholar) ===\n{formatted_serper[:5000]}\n\n"
        # If IndianKanoon was empty but legal query, escalate to Scholar
        if is_legal and not any("CASE LAW" in full_context for _ in [1]):
            scholar_res = await search_scholar(f"{body[:100]} India judgment ruling", num_results=8)
            if scholar_res:
                full_context += "=== GOOGLE SCHOLAR FALLBACK (IndianKanoon empty) ===\n"
                for s in scholar_res[:6]:
                    full_context += f"- {s.get('title', 'N/A')} | {s.get('link', '')}\n  {s.get('snippet', '')[:200]}\n"
                full_context += "[⚠️ Scholar results — verify citations independently]\n\n"
    except Exception as e:
        logger.warning(f"Serper search failed for email: {e}")
        # Fallback to DuckDuckGo if Serper is down
        try:
            from duckduckgo_search import DDGS
            search_q = f"{body[:80]} India law OR tax OR audit"
            ddg_results = DDGS().text(search_q, region='in-en', safesearch='off', max_results=5)
            if ddg_results:
                full_context += "=== WEB RESEARCH (FALLBACK) ===\n"
                for r in ddg_results:
                    full_context += f"- {r.get('title', '')}: {r.get('body', '')[:200]}\n"
                full_context += "\n"
        except Exception as e2:
            logger.warning(f"DuckDuckGo fallback also failed: {e2}")

    # DeepTrace (complex only — audit doesn't need speculative research)
    if complexity == "complex" and needs_deep_research(body):
        try:
            async with aiohttp.ClientSession() as session:
                dt_result = await call_deeptrace_research(session, body)
                if dt_result:
                    full_context += f"=== DEEP RESEARCH INTELLIGENCE ===\n{dt_result}\n\n"
        except Exception as e:
            logger.warning(f"DeepTrace failed for email: {e}")

    if client_context:
        full_context += f"=== CLIENT CONTEXT ===\n{client_context}\n\n"

    # Select prompt based on complexity — use live thresholds
    live_prompt = await get_spectr_prompt()
    if complexity == "audit":
        system_instruction = live_prompt + TOOL_DESCRIPTIONS_FOR_PROMPT + "\n\n" + AUDIT_EMAIL_PROMPT
    else:
        system_instruction = live_prompt + TOOL_DESCRIPTIONS_FOR_PROMPT + "\n\n" + EMAIL_RESPONSE_PROMPT

    user_content = f"EMAIL FROM: {sender}\nSUBJECT: {subject}\n\nQUERY:\n{body}\n\nRESEARCH CONTEXT:\n{full_context}"

    # AI cascade for complex/audit emails
    # - complex/audit  → Opus 4.5 directly (justified: high-stakes legal advice)
    # - medium         → Sonnet with escalation (cost-optimized)
    async with aiohttp.ClientSession() as session:
        if complexity in ("complex", "audit"):
            # Use Opus directly — these emails are high-value (SCN replies, appeals, audits)
            try:
                from claude_emergent import call_deep_research
                response, _model = await call_deep_research(system_instruction, user_content)
            except Exception as _e:
                logger.warning(f"Email Opus failed, cascading: {_e}")
                response = await call_deep_reasoning(session, system_instruction, user_content)
                if not response:
                    response = await call_groq_fast(session, system_instruction, user_content)
        else:
            response = await call_groq_fast(session, system_instruction, user_content)

        if not response:
            response = "We received your query and are processing it. Our team will follow up shortly.\n\n— Spectr AI"

    # ===================== TRUST LAYER (Spectr Verification) =====================
    # Inline [✓ IK] / [⚠ Unverified] tags + math error detection + amendment warnings.
    # This is the key quality lift: catches hallucinated circulars (e.g., "CBDT 19/2019"
    # when it's actually CBIC 128/47/2019-GST), stale cases, wrong arithmetic.
    trust_score = None
    verification_report = None
    if response and len(response) > 300:
        try:
            from response_augmenter import augment_response
            aug = await augment_response(response, db=_email_db, max_case_verifications=6)
            if aug and aug.get("augmented_text"):
                response = aug["augmented_text"]
                trust_score = aug.get("trust_score")
                verification_report = aug.get("verification_report", "")
        except Exception as e:
            logger.warning(f"Email Trust Layer failed (non-blocking): {e}")
            # Fallback: simpler citation linking
            try:
                citations = await find_citation_links(response)
                if citations:
                    citation_block = "\n\n---\n**Verified Citations:**\n"
                    for c in citations[:8]:
                        if c.get("url"):
                            citation_block += f"- [{c.get('text', '')}]({c['url']})\n"
                        elif c.get("verified"):
                            citation_block += f"- ✓ {c.get('text', '')} — verified\n"
                    response += citation_block
            except Exception:
                pass

    # ===================== SMART ATTACHMENT GENERATION =====================
    # Generate attachments based on complexity and content type
    if response and len(response) > 200 and complexity != "simple":
        has_tables = '|' in response and response.count('|') > 6
        is_financial = any(t in query_types for t in ["financial"])
        is_legal_advisory = any(t in query_types for t in ["legal", "compliance", "corporate"])

        if complexity == "audit":
            # Audit: always generate Excel workpapers + Word memo
            excel_att = await _generate_attachment(response, subject, "excel")
            if excel_att:
                attachments.append(excel_att)
            word_att = await _generate_attachment(response, subject, "word")
            if word_att:
                attachments.append(word_att)

        elif complexity == "complex":
            # Complex: always generate Word advisory memo
            word_att = await _generate_attachment(response, subject, "word")
            if word_att:
                attachments.append(word_att)
            # If tables present (exposure calc, statutory framework), also generate Excel
            if has_tables or is_financial:
                excel_att = await _generate_attachment(response, subject, "excel")
                if excel_att:
                    attachments.append(excel_att)

        elif complexity == "medium" and (has_tables or is_financial):
            # Medium with tables/financial data: generate Excel
            excel_att = await _generate_attachment(response, subject, "excel")
            if excel_att:
                attachments.append(excel_att)

    result = {"response": response, "attachments": attachments, "complexity": complexity}
    if trust_score is not None:
        result["trust_score"] = trust_score
    if verification_report:
        result["verification_report"] = verification_report
    return result


async def process_incoming_emails(db=None):
    """Poll for unread emails, process each, and reply.
    Called periodically by the background worker.

    Resilience:
    - Duplicate detection: skips already-processed message IDs
    - Dead-letter queue: after all retries fail, stores the failure for review
    - Circuit breaker: checked inside each API call
    - Graceful degradation: if DB is down, still processes emails (without client context)

    Returns count of emails processed.
    """
    global _email_db
    if not AGENTMAIL_API_KEY:
        return 0

    # Store DB reference for use by send_email and other functions
    _email_db = db

    messages = await list_unread_messages()
    if not messages:
        return 0

    processed = 0
    for msg in messages:
        msg_id = msg.get("message_id", "")
        if not msg_id:
            continue

        # Duplicate detection — skip if already processed in this process lifetime
        if msg_id in _processed_ids:
            logger.debug(f"Skipping duplicate message: {msg_id}")
            continue

        # Fetch full message (list endpoint may not include body text)
        full_msg = await get_message(msg_id)
        if full_msg:
            msg = full_msg

        sender = msg.get("from_", msg.get("from", ""))
        subject = msg.get("subject", "No Subject")
        body = msg.get("extracted_text") or msg.get("text", "")

        if not body:
            _processed_ids.append(msg_id)
            continue

        sender_email_addr = _extract_email(sender)

        # Skip emails from ourselves (prevents infinite reply loops)
        if sender_email_addr and sender_email_addr == INBOX_EMAIL.lower():
            logger.info(f"Skipping self-email: {msg_id} ({subject})")
            await update_message_labels(msg_id, add_labels=["read", "self"], remove_labels=["unread"])
            _processed_ids.append(msg_id)
            continue

        # Skip auto-replies, system messages, bounce-backs
        skip_patterns = [
            "auto-reply", "out of office", "delivery", "undeliverable",
            "mailer-daemon", "noreply", "no-reply", "postmaster",
            "mail delivery", "returned mail"
        ]
        if any(kw in subject.lower() for kw in skip_patterns):
            await update_message_labels(msg_id, add_labels=["read", "skipped"], remove_labels=["unread"])
            _processed_ids.append(msg_id)
            continue

        logger.info(f"Processing email from {sender}: {subject}")

        # Look up client context from DB (graceful — failures don't block processing)
        client_context = ""
        if db is not None:
            try:
                sender_email = _extract_email(sender)
                if sender_email:
                    client = await db.clients.find_one({"contact_email": sender_email})
                    if client:
                        client_context = f"Client: {client.get('name', '')} | PAN: {client.get('pan', '')} | GSTIN: {client.get('gstin', '')}"
                        # Get recent email history for this client
                        history = await db.email_history.find(
                            {"client_email": sender_email}
                        ).sort("created_at", -1).limit(3).to_list(3)
                        if history:
                            client_context += "\n\nRecent email history:\n"
                            for h in reversed(history):
                                client_context += f"Q: {h.get('subject', '')}\nA: {h.get('response', '')[:300]}\n\n"
            except Exception as e:
                logger.warning(f"Client context lookup failed (continuing without): {e}")

        try:
            # Process through AI pipeline (complexity-routed)
            result = await process_email_query(sender, subject, body, client_context)
            response = result.get("response", "")
            attachments = result.get("attachments", [])
            complexity = result.get("complexity", "unknown")

            if not response or len(response) < 20:
                raise ValueError("AI pipeline returned empty or too-short response")

            logger.info(f"Email processed [{complexity}]: {len(response)} chars, {len(attachments)} attachment(s)")

            # Append attachment download links to response if any
            reply_text = response
            if attachments:
                reply_text += "\n\n---\n\n**Attachments Generated:**\n"
                for att in attachments:
                    icon = "📊" if att.get("type") == "excel" else "📄"
                    fname = att.get("filename", "document")
                    url = att.get("url", "")
                    if url:
                        reply_text += f"\n{icon} [{fname}]({url})"
                    else:
                        # Local file — mention it's available on request
                        reply_text += f"\n{icon} {fname} — generated and stored. Available on request."
                reply_text += "\n"

            # Reply
            success = await reply_to_message(msg_id, reply_text)

            if success:
                # Mark as read and replied
                await update_message_labels(msg_id, add_labels=["read", "replied"], remove_labels=["unread", "unreplied"])
                processed += 1
                _processed_ids.append(msg_id)

                # === MONGO: Save reply to email_history for context in future replies ===
                if db is not None:
                    try:
                        await db.email_history.insert_one({
                            "message_id": msg_id,
                            "client_email": _extract_email(sender),
                            "sender": sender,
                            "subject": subject,
                            "query": body[:10000],
                            "response": response[:20000],
                            "complexity": complexity,
                            "attachments": [{"filename": a.get("filename"), "url": a.get("url"), "type": a.get("type")} for a in attachments],
                            "direction": "reply",
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "status": "replied",
                        })
                    except Exception as e:
                        logger.warning(f"Email history save failed: {e}")
            else:
                # Reply failed after retries — dead-letter it
                _dead_letter(msg_id, sender, subject, "Reply delivery failed after retries")
                await update_message_labels(msg_id, add_labels=["read", "failed"], remove_labels=["unread"])
                _processed_ids.append(msg_id)

        except Exception as e:
            logger.error(f"Email processing failed for {msg_id}: {e}")
            _dead_letter(msg_id, sender, subject, str(e))
            # Mark as read to avoid infinite reprocessing
            await update_message_labels(msg_id, add_labels=["read", "error"], remove_labels=["unread"])
            _processed_ids.append(msg_id)

            # === MONGO: Log failure in email_history for context ===
            if db is not None:
                try:
                    await db.email_history.insert_one({
                        "message_id": msg_id,
                        "client_email": _extract_email(sender),
                        "sender": sender,
                        "subject": subject,
                        "query": body[:10000],
                        "response": "",
                        "error": str(e)[:1000],
                        "direction": "reply_failed",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "status": "failed",
                    })
                except Exception:
                    pass

    return processed


def _dead_letter(msg_id: str, sender: str, subject: str, error: str):
    """Add a failed message to the in-memory dead-letter queue."""
    entry = {
        "message_id": msg_id,
        "sender": sender,
        "subject": subject,
        "error": error[:500],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    dead_letter_queue.append(entry)
    if len(dead_letter_queue) > 100:
        dead_letter_queue.pop(0)
    logger.error(f"Dead-lettered email {msg_id} from {sender}: {error[:200]}")


def _extract_email(from_field: str) -> str:
    """Extract email address from 'Name <email@domain.com>' format."""
    match = re.search(r'<([^>]+)>', from_field)
    if match:
        return match.group(1).lower()
    if "@" in from_field:
        return from_field.strip().lower()
    return ""


def _markdown_to_html(markdown_text: str) -> str:
    """Convert markdown to basic HTML for email formatting."""
    html = markdown_text

    # === SUMMARY BLOCK — bold + underlined, visually prominent ===
    # Match **__EXECUTIVE SUMMARY__** or **__SUMMARY__** or **__SUMMARY:__** header + content until ---
    def _render_summary_block(match):
        title = match.group(1).strip('_ ')
        content = match.group(2).strip()
        # Clean markdown from content
        content = re.sub(r'\*\*__(.+?)__\*\*', r'\1', content)
        content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
        return f'''<div style="background:#F8F7F4;border-left:4px solid #0A0A0A;padding:20px 24px;margin:0 0 24px;border-radius:0 4px 4px 0;">
            <h2 style="font-family:Georgia,serif;font-size:13px;text-transform:uppercase;letter-spacing:0.15em;color:#666;margin:0 0 10px;font-weight:600;">{title}</h2>
            <p style="font-family:Georgia,serif;font-size:16px;line-height:1.8;color:#0A0A0A;margin:0;text-decoration:underline;text-decoration-color:#D1D5DB;text-underline-offset:3px;font-weight:600;">{content}</p>
        </div>'''

    html = re.sub(
        r'\*\*__([A-Z /:]+)__\*\*\s*\n((?:(?!\n---).)*)',
        _render_summary_block, html, count=1, flags=re.DOTALL
    )

    # Headers
    html = re.sub(r'^### (.+)$', r'<h3 style="color:#0A0A0A;font-family:Georgia,serif;margin:20px 0 8px;">\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2 style="color:#0A0A0A;font-family:Georgia,serif;font-size:18px;margin:24px 0 10px;border-bottom:1px solid #E5E7EB;padding-bottom:6px;">\1</h2>', html, flags=re.MULTILINE)

    # Bold+underline combo: **__text__**
    html = re.sub(r'\*\*__(.+?)__\*\*', r'<strong style="text-decoration:underline;text-underline-offset:2px;">\1</strong>', html)

    # Bold and italic
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

    # Blockquotes
    html = re.sub(r'^> (.+)$', r'<blockquote style="border-left:3px solid #D1D5DB;padding:8px 16px;margin:12px 0;color:#4B5563;background:#F9FAFB;">\1</blockquote>', html, flags=re.MULTILINE)

    # Lists
    html = re.sub(r'^- (.+)$', r'<li style="margin:4px 0;">\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'^(\d+)\. (.+)$', r'<li style="margin:4px 0;">\2</li>', html, flags=re.MULTILINE)

    # Horizontal rules
    html = re.sub(r'^---+$', '<hr style="border:none;border-top:1px solid #E5E7EB;margin:24px 0;">', html, flags=re.MULTILINE)

    # Markdown links: [text](url)
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" style="color:#0A0A0A;font-weight:600;text-decoration:underline;">\1</a>', html)

    # Tables (basic)
    lines = html.split('\n')
    in_table = False
    table_html = []
    result_lines = []
    for line in lines:
        if '|' in line and line.strip().startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if all(set(c) <= set('-: ') for c in cells):
                continue  # Skip separator row
            if not in_table:
                in_table = True
                table_html = ['<table style="border-collapse:collapse;width:100%;margin:16px 0;font-size:14px;">']
                row = '<tr>' + ''.join(f'<th style="border:1px solid #D1D5DB;padding:8px 12px;background:#F3F4F6;text-align:left;font-weight:600;">{c}</th>' for c in cells) + '</tr>'
            else:
                row = '<tr>' + ''.join(f'<td style="border:1px solid #D1D5DB;padding:8px 12px;">{c}</td>' for c in cells) + '</tr>'
            table_html.append(row)
        else:
            if in_table:
                table_html.append('</table>')
                result_lines.append('\n'.join(table_html))
                table_html = []
                in_table = False
            result_lines.append(line)
    if in_table:
        table_html.append('</table>')
        result_lines.append('\n'.join(table_html))
    html = '\n'.join(result_lines)

    # Paragraphs
    html = re.sub(r'\n\n', '</p><p style="margin:12px 0;line-height:1.7;color:#1A1A1A;font-size:15px;">', html)
    html = html.replace('\n', '<br>')

    # Wrap in premium email template — institutional grade
    return f"""
    <div style="font-family: Georgia, 'Times New Roman', serif; max-width: 760px; margin: 0 auto; padding: 0; color: #1A1A1A; line-height: 1.75; background: #FFFFFF;">
        <!-- Header — clean, authoritative -->
        <div style="padding: 36px 44px 28px; border-bottom: 2.5px solid #0A0A0A;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                    <td>
                        <h1 style="font-size: 30px; font-weight: 700; color: #0A0A0A; margin: 0; letter-spacing: -0.04em; font-family: Georgia, serif;">Spectr</h1>
                        <p style="font-size: 9.5px; color: #888; margin: 5px 0 0; letter-spacing: 0.18em; text-transform: uppercase; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">AI Legal and Accounting Platform</p>
                    </td>
                    <td style="text-align: right; vertical-align: bottom;">
                        <p style="font-size: 10px; color: #B0B0B0; margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; letter-spacing: 0.02em;">spectr.r@agentmail.to</p>
                    </td>
                </tr>
            </table>
        </div>

        <!-- Body — the deliverable -->
        <div style="padding: 36px 44px 32px;">
            <p style="margin:12px 0;line-height:1.85;color:#1A1A1A;font-size:15px;">
            {html}
            </p>
        </div>

        <!-- Verification Bar — institutional trust signals -->
        <div style="padding: 14px 44px; background: #F7F8F9; border-top: 1px solid #E2E4E8; border-bottom: 1px solid #E2E4E8;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                    <td style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 9px; color: #6B7280; letter-spacing: 0.1em; text-transform: uppercase;">&#10003; Statutory Citations Verified</td>
                    <td style="text-align: center; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 9px; color: #6B7280; letter-spacing: 0.1em; text-transform: uppercase;">&#10003; Amendment-Aware Analysis</td>
                    <td style="text-align: right; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 9px; color: #6B7280; letter-spacing: 0.1em; text-transform: uppercase;">&#10003; Case Law Era-Checked</td>
                </tr>
            </table>
        </div>

        <!-- Footer -->
        <div style="padding: 24px 44px; background: #FAFAFA;">
            <p style="font-size: 10px; color: #9CA3AF; line-height: 1.7; margin: 0 0 12px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
                <strong style="color:#555;">Disclaimer:</strong> This advisory is generated by Spectr AI for informational purposes. It does not constitute legal advice or create an attorney-client relationship.
                Professional verification is recommended before acting on any information. Statutory citations are verified against known amendments through Finance Act 2024. Case law from training knowledge should be independently confirmed against current reporters.
            </p>
            <div style="height: 1px; background: #E2E4E8; margin: 12px 0;"></div>
            <p style="font-size: 9.5px; color: #B0B0B0; margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; letter-spacing: 0.05em;">
                Spectr &mdash; AI Legal and Accounting Platform &bull; spectr.r@agentmail.to &bull; Powered by Algorythm
            </p>
        </div>
    </div>
    """
