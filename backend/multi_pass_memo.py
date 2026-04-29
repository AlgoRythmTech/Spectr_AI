"""
multi_pass_memo.py — generate 10,000+ word legal memos by chaining Claude calls.

Why this exists
---------------
The Emergent proxy has a HARD 60-second timeout on first byte. Claude Sonnet
4.6 generates ~40 tokens/sec, so in 55 seconds it can safely output ~2,200
tokens ≈ 1,400-1,500 words. To match the Claude.ai demo of 10,000-15,000
word memos, we MUST chain multiple calls.

Calibration (23 Apr 2026, verified live):
  - 25K sys + 2,400 max_tokens = 49s total, ~1,400 words — SWEET SPOT
  - 40K sys + 2,400 max_tokens = 52s total, ~1,360 words — safe
  - 15K sys + 2,400 max_tokens = 56s total, ~1,520 words — tight

Architecture (7 passes × ~1,400 words = ~9,800 words total memo):

  Pass 1 — "HEADER" (Bottom Line + Issues Framed + Governing Framework).
           Sets the memo's architecture. Target: 1,300 words.

  Pass 2 — "ANALYSIS A" (Analysis subheadings 1-3). Leads with procedural
           kill-shots (limitation, DIN, jurisdiction). Target: 1,400 words.

  Pass 3 — "ANALYSIS B" (Analysis subheadings 4-6). Exemption tests and
           merits. Target: 1,400 words.

  Pass 4 — "ANALYSIS C" (Analysis subheadings 7-9 + Definitive Stance).
           Constitutional overlay, precedent synthesis, kill-shot restated.
           Target: 1,400 words.

  Pass 5 — "ADVERSARIAL" (What They'll Argue — 5-7 counters). Full war-
           gaming, each counter with named authority + destroying fact.
           Target: 1,400 words.

  Pass 6 — "OPERATIONS" (Risk Matrix + Action Items). Quantified table
           + dated items with if-missed consequences. Target: 1,200 words.

  Pass 7 — "AUTHORITIES" (Authorities Relied On + Research Provenance +
           AI Research Notice). Consolidates citations, transparency
           footer. Target: 700 words.

Total: ~8,800 visible words, 7 passes × 50s = ~6 minutes for a full memo.

Sonnet 4.6 is used for all passes (cost-efficient, ~$0.03 per memo).
Opus 4.6 can optionally reinforce Pass 2-4 (merits) when user explicitly
requested deep research. Default: all Sonnet.
"""
import asyncio
import logging
import os
import time
from typing import Optional, AsyncGenerator

logger = logging.getLogger("multi_pass_memo")


# Per-pass instructions — each tight, focused, under 60s budget.
DEPTH_INJECTION = """\
═══════════════════════════════════════════════════════════════════════
CRITICAL INSTRUCTION — READ EVERY LINE.

You are generating output that will be benchmarked against Claude.ai,
GPT-5, and Harvey.ai. Your output MUST match or EXCEED those products'
depth, detail, and analytical rigor on Indian law and tax topics.

Our client is a paying Senior Tax Partner at Zepto / Murthy & Kanth /
similar tier-1 firm. They have seen Claude.ai and GPT-5 responses.
They have REJECTED responses under 1,200 words per pass as "thin."
Every pass MUST deliver dense, pincited, Indian-specific output that
demonstrates:

1. NAMED CITATIONS ONLY. Every case has: party names in italics, full
   reporter citation, paragraph pincite. Not "SC has held" — "*Bharti
   Airtel Ltd. v. UoI*, (2021) SCC OnLine SC 1029, ¶47-52".

2. INDIAN-SPECIFIC. BNS 2023 not IPC 1860. BNSS not CrPC. BSA not IEA.
   Finance Act 2024/2025 amendments. Current GST notifications. CBIC
   circulars with numbers and dates. Not generic legal theory.

3. QUANTIFICATION. Every rupee figure, every date, every interest
   calculation. If the number isn't in the facts, SAY "unknown, ask
   client" — don't approximate or invent.

4. DOCTRINAL LANDMINES. Surface the specific proviso / carve-out /
   post-amendment shift that a 5-year associate would miss. This is
   what separates Harvey-grade from textbook.

5. PROCEDURAL KILL-SHOTS FIRST. Limitation, DIN, sanction, natural
   justice, jurisdiction — before any merits analysis. Senior counsel
   wins cases on procedure; juniors lose them on merits.

6. EXEMPTION-FIRST DOCTRINE. Test every proviso / exemption / carve-out
   BEFORE asserting the rule applies. *"Section 54F exempts LTCG unless
   the assessee owns >1 residential property on transfer date — he does
   not; therefore the exemption applies"* — not the other way around.

7. PRE-EMPT THE OPPOSITION. Name what they'll argue, cite the case they
   rely on, destroy it with the distinguishing fact or contrary ratio.

8. LENGTH FLOOR. This pass MUST produce ≥ 1,100 words of dense prose.
   Filler, padding, restating the question = FAILURE. Every sentence
   earns its place or gets cut.

9. NO HEDGING. Banned words: "may", "might", "could", "arguably",
   "possibly", "it depends" (without immediate resolution). State the
   position. Own it.

10. NO PLACEHOLDERS. "XYZ", "ABC", "[Case Name]", "[Date TBD]" = instant
    failure. If you don't have the real citation, say "see IndianKanoon
    live lookup" and continue.

YOU ARE COMPETING AGAINST CLAUDE.AI ON QUALITY. Every paragraph must
teach the reader something a Big Four senior partner would miss. If you
can't, the paragraph doesn't belong in the memo.
═══════════════════════════════════════════════════════════════════════

"""


PASS_1 = DEPTH_INJECTION + """\
This is PASS 1 of a multi-pass partner memo. Write ONLY the HEADER sections.
Subsequent passes will write the Analysis sub-headings, opposition counters,
risk matrix, action items, and authorities.

WRITE, IN ORDER:

1. `## Bottom Line` — 3 sentences, ≤55 words. Verdict + exposure + move.
   First word is the answer. No "Based on the facts" preamble.

2. `> **THE KILL-SHOT:** [one sentence, ≤25 words, naming the controlling
   section/case/fact that ends the argument in the client's favour].`

3. `## Issues Framed` — 4-6 numbered questions, 30-50 words each, naming
   the specific section/rule/fact that makes it a real question (not a
   textbook one).

4. `## Governing Framework` — 700-900 words. For each controlling provision:
   - Full section reference (e.g. Section 74(10) of the CGST Act, 2017)
   - Quote the operative sub-clause verbatim in a blockquote
   - Effective date / Finance Act version
   Then cite 4-6 leading cases with full citation + pincite paragraph +
   one-sentence ratio statement. End with one `> **KEY:**` callout
   summarising the framework in one sentence.

TARGET: ~1,300 words total.
DO NOT write Analysis, Opposition, Risk Matrix, Action Items, or Authorities
— those are later passes.

End with: `<!-- PASS 1 COMPLETE -->`
"""


PASS_2 = """\
This is PASS 2. Pass 1 wrote the Bottom Line, Kill-Shot, Issues Framed, and
Governing Framework (in <PASS_1> below).

NOW WRITE `## Analysis` AND the FIRST 3 `###` topic-specific sub-headings.

Each sub-heading is a doctrinal STATEMENT or NAMED MOVE, not generic
"Issue 1/2/3". Examples:
  - `### The Limitation Bar Under §74(10) CGST Act`
  - `### The Fraud/Suppression Threshold`
  - `### Procedural Defects in DIN Compliance`
  - `### The Exemption-First Test`
  - `### The Proviso to §74(2)`

Senior-partner sequence: LEAD with procedural kill-shots (limitation, DIN,
jurisdiction, natural justice, sanction). If any lands, you never reach
merits. Then exemption-first tests. Only then substantive merits.

Each `###` sub-section delivers 400-500 words:
  1. One-line verdict for the sub-issue
  2. Controlling statute quoted verbatim (blockquote) OR summarised with
     section + sub-clause + act + year
  3. Leading authority with full citation + pincite paragraph
  4. Application to the specific facts of this query
  5. The opposition's counter (1-2 sentences) + why it fails
  6. `> **KEY:**` callout — one sentence naming a section, case, or number

TARGET: ~1,400 words total for Pass 2.

End with: `<!-- PASS 2 COMPLETE -->`
"""


PASS_3 = """\
This is PASS 3. Passes 1-2 are in <PASS_1> and <PASS_2> below. Pass 2 wrote
the first 3 Analysis sub-headings.

NOW WRITE 3 MORE `###` topic-specific sub-headings in `## Analysis`
(continuing where Pass 2 left off). Pick doctrinal angles that COMPLEMENT
Pass 2's sub-headings — do not repeat.

Typical Pass 3 angles (pick whichever fit the query):
  - Substantive merits (`### The Bharti Airtel ITC Defence`)
  - Post-amendment edge (`### Post-Finance Act 2024 §16(4) Extension`)
  - Cross-jurisdiction (`### Kerala HC vs Bombay HC — The Split`)
  - Constitutional hook (`### The Article 14 Challenge`)
  - Precedent-driven defence (`### The Mohit Minerals Override`)
  - Alternative remedy (`### The Art. 226 Writ Strategy`)

Each sub-section: 400-500 words, CREAC structure, named cases with pincites,
opposition pre-empted, `> **KEY:**` callout.

TARGET: ~1,400 words.

End with: `<!-- PASS 3 COMPLETE -->`
"""


PASS_4 = """\
This is PASS 4. Passes 1-3 in <PASS_1>, <PASS_2>, <PASS_3> below.

NOW WRITE 2-3 MORE `###` Analysis sub-headings continuing the flow, THEN
close with `### Definitive Stance`.

Pass 4 typical sub-headings (complementary to what's already written):
  - Constitutional supremacy (`### The Doctrine of Constitutional Supremacy`)
  - Distinguishing (`### Distinguishing Testimonials from Material Evidence`)
  - Authority synthesis (`### The Puttaswamy Reinforcement`)
  - High-stakes doctrinal landmine (if IBC-PMLA: `### Section 32A Clean
    Slate`; if tax-criminal: `### The §279(1) Sanction Defect`)

`### Definitive Stance` — 300-400 words. The summary doctrinal position.
State where the law actually stands after all the analysis. Restate the
kill-shot explicitly. This closes the Analysis section.

TARGET: ~1,400 words.

End with: `<!-- PASS 4 COMPLETE -->`
"""


PASS_5 = """\
This is PASS 5. Passes 1-4 in <PRIOR_PASSES> below. The full Analysis is
written.

NOW WRITE the `## What the Department / Opponent Will Argue` section ONLY.

Write 5-7 counter-argument paragraphs, EACH 180-240 words. Do NOT write
one-liners. Each counter:

1. Opens with: "**The Department will argue [specific argument X] under
   [exact section Y], relying on *[Case Name + full citation + pincite
   paragraph]*.**"
2. Describes their theory of the case in 2-3 sentences.
3. Destroys it: "That fails because [specific distinguishing fact, contrary
   ratio, post-amendment carve-out, or procedural bar with named citation]."
4. Closes: "If they escalate to [next forum — HC writ / CESTAT / Supreme
   Court SLP], our position is strengthened by [2-3 authorities or doctrinal
   reasons]."

Reference specific Analysis sub-headings from Passes 1-4 where relevant.
Each counter must ANSWER a specific argument the Analysis built.

TARGET: ~1,400 words.

End with: `<!-- PASS 5 COMPLETE -->`
"""


PASS_6 = """\
This is PASS 6. Passes 1-5 in <PRIOR_PASSES> below.

NOW WRITE two sections in order:

1. `## Risk Matrix` — table with EXACTLY 6-8 rows. Columns:
   | Risk | Likelihood (L/M/H with %) | Exposure (₹) | Horizon | Mitigation |
   Below each row, a 1-2 sentence rationale explaining the likelihood
   figure. Use specific rupee amounts from the query (no "substantial").
   Use calendar dates (no "soon"). Mitigation must be a specific filing
   or action, not generic "legal strategy".

2. `## Action Items` — 6-10 numbered items. Format:
   `[CRITICAL|URGENT|KEY] Verb — what — by [DD Month YYYY] — owner: [role].
    If missed: [specific consequence naming the statute/rule].`
   At most 2 CRITICAL items (true filing-today-or-lose-the-case).
   The rest: URGENT or KEY. Dated, owned, with consequence.

TARGET: ~1,200 words.

End with: `<!-- PASS 6 COMPLETE -->`
"""


PASS_7 = """\
This is PASS 7 — the CLOSING. Passes 1-6 in <PRIOR_PASSES> below.

NOW WRITE the final three sections:

1. `## Authorities Relied On` — hierarchical list. Extract EVERY statute,
   rule, notification, circular, and case cited anywhere in Passes 1-6.
   Order:
     - Constitution of India (articles engaged)
     - Statutes (section + act + year)
     - Rules
     - Notifications / CBIC, CBDT circulars (with dates)
     - Cases (Supreme Court → High Court → Tribunal, newest first, every
       case pincited)
   Every citation tagged: `[✓ IK]`, `[✓ Statute DB]`, `[From training —
   verify]`. Target: 500-600 words.

2. `## Research Provenance` — 2-3 sentence blockquoted footer:
   > *Research run: N IndianKanoon live lookups · M web sources checked
   > · [any post-training 2024-2026 development surfaced] · cutoff: today.*

3. `## AI Research Notice` — the exact disclaimer:
   > *AI-assisted research. Not legal advice, CA advice, or a professional
   > opinion. Verify every statute, case, and number independently before
   > filing, advising, or relying. Spectr & Co. holds no professional licence.*

TARGET: ~800 words total for Pass 7.

End with: `<!-- PASS 7 COMPLETE -->`
"""


PASS_3B = """\
This is PASS 3B of the deep memo. Passes 1-3 already in context.

NOW WRITE 2 MORE `###` Analysis sub-headings (continuing from where Pass 3
left off). Pick angles Pass 3 didn't cover.

Typical: procedural deep-dive, cross-jurisdictional comparison, post-
amendment impact, alternative remedy paths, notification-level carve-outs.

Each sub-section: 600-700 words, CREAC, pincited, opposition pre-empted,
KEY callout.

TARGET: ~1,400 words.
End with: `<!-- PASS 3B COMPLETE -->`
"""

PASS_4B = """\
This is PASS 4B. Passes 1-4 in context.

WRITE 2 MORE `###` Analysis sub-headings covering doctrinal angles not yet
touched. Examples: constitutional supremacy, distinguishing material vs
testimonial evidence, proviso analysis, notification timing, fraud mens
rea threshold, cross-regime intersection risks (IT/GST/PMLA/BNS collisions).

Each sub-section: 600-700 words with named authorities and pincites.

TARGET: ~1,400 words.
End with: `<!-- PASS 4B COMPLETE -->`
"""

PASS_4C = """\
This is PASS 4C. Passes 1-4B in context.

WRITE 2 MORE `###` Analysis sub-headings finishing out the Analysis
section. Include `### Definitive Stance` (300-400 words) as your final
sub-heading — the summary doctrinal position restating the kill-shot.

TARGET: ~1,400 words.
End with: `<!-- PASS 4C COMPLETE -->`
"""

PASS_5B = """\
This is PASS 5B. Passes 1-5 in context. Pass 5 wrote some opposition counters.

WRITE 3 MORE counter-argument paragraphs that Pass 5 didn't cover, each
230-280 words. Complete the opposition war-gaming. Include at least ONE
escalation scenario (what happens if they take it to HC writ / Supreme
Court SLP) and ONE nuclear counter — the argument they'll save for last.

TARGET: ~1,400 words.
End with: `<!-- PASS 5B COMPLETE -->`
"""

PASS_STRATEGIC = """\
This is the STRATEGIC PLAYBOOK pass. Prior passes are in context.

WRITE a new section: `## Strategic Playbook & Timeline`

Include 4-6 topic-specific `###` sub-headings covering:
  - `### Pre-emptive Moves` — 300-400 words on what to file / prepare BEFORE
    the department moves. Specific forms, specific deadlines.
  - `### Phase-Wise Litigation Plan` — 300-400 words. If department
    escalates, which forum do we go to first? Writ HC vs adjudication vs
    appellate authority. Named tribunal / bench preferences.
  - `### Settlement / Negotiation Levers` — 200-300 words. What does the
    department want? What can we concede cheaply in exchange for dropping
    major demand? Named officials / jurisdictions if relevant.
  - `### Parallel Proceedings Coordination` — 200-300 words. If GST + PMLA
    + criminal are in play, the order of operations matters. Which proceeding
    do we resolve first to gain leverage in the others?

TARGET: ~1,400 words.
End with: `<!-- PASS STRATEGIC COMPLETE -->`
"""

PASS_HYPOTHETICALS = """\
This is the HYPOTHETICALS pass. Prior passes are in context.

WRITE a new section: `## "What If" Scenario Mapping`

Map 4-6 "what if" branches to prepare the client for every evolution of the
dispute. Each branch is a `###` sub-heading, 250-350 words. Examples:
  - `### What If the Department Amends the SCN` — what their path looks
    like + our counter
  - `### What If We File Writ First` — our timeline advantage + risk
  - `### What If the Tribunal Rejects Limitation` — merits fallback plan
  - `### What If the Supreme Court Grants Stay` — leverage created
  - `### What If Vendor X Settles Separately` — impact on our position
  - `### What If New CBIC Circular Issues Mid-Proceedings` — how to adapt

Each branch: probability estimate (L/M/H), specific action trigger, named
authorities to deploy.

TARGET: ~1,500 words.
End with: `<!-- PASS HYPOTHETICALS COMPLETE -->`
"""


# Prepend DEPTH_INJECTION to every non-Pass-1 instruction so inferior
# models (GPT-4.1, GPT-4o-mini) get the "BEAT CLAUDE" directive on every
# call. Pass 1 already has it embedded above.
PASS_INSTRUCTIONS = [
    ("HEADER",        PASS_1),
    ("ANALYSIS-A",    DEPTH_INJECTION + PASS_2),
    ("ANALYSIS-B",    DEPTH_INJECTION + PASS_3),
    ("ANALYSIS-B2",   DEPTH_INJECTION + PASS_3B),
    ("ANALYSIS-C",    DEPTH_INJECTION + PASS_4),
    ("ANALYSIS-D",    DEPTH_INJECTION + PASS_4B),
    ("ANALYSIS-E",    DEPTH_INJECTION + PASS_4C),
    ("ADVERSARIAL",   DEPTH_INJECTION + PASS_5),
    ("ADVERSARIAL-B", DEPTH_INJECTION + PASS_5B),
    ("STRATEGIC",     DEPTH_INJECTION + PASS_STRATEGIC),
    ("HYPOTHETICALS", DEPTH_INJECTION + PASS_HYPOTHETICALS),
    ("OPERATIONS",    DEPTH_INJECTION + PASS_6),
    ("AUTHORITIES",   DEPTH_INJECTION + PASS_7),
]


async def _call_direct_openai(system_prompt: str, user_content: str, model: str, timeout: int = 90, max_tokens: int = 2000) -> str:
    """Direct HTTP call to OpenAI API (bypasses Emergent proxy).

    Used for the fine-tuned SyntaxAI model + gpt-4.1 family. Saves
    Emergent credits entirely for the common research path.
    """
    import aiohttp, os
    key = os.environ.get("OPENAI_KEY", "")
    if not key:
        return ""
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.post(
                url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            ) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    logger.warning(f"OpenAI direct {model} HTTP {resp.status}: {err[:200]}")
                    return ""
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
    except asyncio.TimeoutError:
        logger.warning(f"OpenAI direct {model} timed out after {timeout}s")
        return ""
    except Exception as e:
        logger.warning(f"OpenAI direct {model} error: {e}")
        return ""


async def _call_direct_emergent(system_prompt: str, user_content: str, model: str, timeout: int = 90, max_tokens: int = 2000) -> str:
    """Direct HTTP call to Emergent proxy. Bypasses the SDK fallback chain.

    Uses cache_control for Claude models (90% savings on repeat system).
    For GPT models, plain system string (no cache_control on non-Anthropic).
    """
    import aiohttp, os
    key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not key:
        return ""
    url = "https://integrations.emergentagent.com/llm/v1/chat/completions"
    is_claude = "claude" in model.lower()

    if is_claude:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": [
                    {"type": "text", "text": system_prompt,
                     "cache_control": {"type": "ephemeral"}}
                ]},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
    else:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.post(
                url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            ) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    logger.warning(f"Emergent {model} HTTP {resp.status}: {err[:200]}")
                    return ""
                data = await resp.json()
                usage = data.get("usage") or {}
                cr = usage.get("cache_read_input_tokens", 0)
                cw = usage.get("cache_creation_input_tokens", 0)
                if cr:
                    logger.info(f"  prompt cache HIT: {cr:,} tokens (~90% saved)")
                elif cw:
                    logger.info(f"  prompt cache WARM: {cw:,} tokens written")
                return data["choices"][0]["message"]["content"]
    except asyncio.TimeoutError:
        logger.warning(f"Emergent {model} timed out after {timeout}s")
        return ""
    except Exception as e:
        logger.warning(f"Emergent {model} error: {e}")
        return ""


SYNTAXAI_MODEL = "ft:gpt-4.1-2025-04-14:algorythm-technologies:syntaxai:CdHNxlU8"


async def _call_sonnet(system_prompt: str, user_content: str, max_tokens: int = 2000, timeout: int = 95) -> str:
    """Budget-efficient cascade (23 Apr 2026):
      Tier 1: Fine-tuned SyntaxAI (ft:gpt-4.1 — Algorythm Technologies's own
              Indian-legal-trained model, CHEAPEST quality option, OpenAI direct)
      Tier 2: gpt-4.1 (OpenAI direct, strong general)
      Tier 3: gpt-4.1-mini (OpenAI direct, very cheap fallback)
      Tier 4: gpt-4o-mini (OpenAI direct, cheapest)
      Tier 5: Claude Sonnet 4.6 via Emergent (EXPENSIVE — save credits,
              only use when OpenAI cascade fails entirely)

    Why this order: Emergent balance is down to $77. A 16K-word memo costs
    ~$0.30 on fine-tuned GPT-4.1 vs ~$0.15 on Sonnet cached vs ~$1.50 on
    plain GPT-5. Fine-tuned model is pre-trained on Indian legal so
    delivers Claude-grade quality at GPT-4.1 price.

    All tiers get the full SPECTR depth-forcing prompt. Depth floor applies
    regardless of which tier answers.
    """
    # Tier 1: Fine-tuned SyntaxAI — primary (OpenAI direct, cheap, trained on Indian legal)
    resp = await _call_direct_openai(system_prompt, user_content, SYNTAXAI_MODEL, timeout=timeout, max_tokens=max_tokens)
    if resp and len(resp.split()) >= 200 and not resp.startswith("Error:"):
        return resp

    # Tier 2: gpt-4.1 — strong OpenAI direct
    logger.info("SyntaxAI thin/failed, trying gpt-4.1...")
    resp = await _call_direct_openai(system_prompt, user_content, "gpt-4.1", timeout=timeout, max_tokens=max_tokens)
    if resp and len(resp.split()) >= 200 and not resp.startswith("Error:"):
        return resp

    # Tier 3: gpt-4.1-mini
    logger.info("gpt-4.1 thin/failed, trying gpt-4.1-mini...")
    resp = await _call_direct_openai(system_prompt, user_content, "gpt-4.1-mini", timeout=timeout, max_tokens=max_tokens)
    if resp and len(resp.split()) >= 200 and not resp.startswith("Error:"):
        return resp

    # Tier 4: gpt-4o-mini — cheapest OpenAI
    logger.info("gpt-4.1-mini thin/failed, trying gpt-4o-mini...")
    resp = await _call_direct_openai(system_prompt, user_content, "gpt-4o-mini", timeout=timeout, max_tokens=max_tokens)
    if resp and len(resp.split()) >= 200 and not resp.startswith("Error:"):
        return resp

    # Tier 5: Claude Sonnet 4.6 via Emergent — EXPENSIVE last resort
    logger.warning("ALL OpenAI tiers failed — falling to Emergent Sonnet (burns credits)")
    resp = await _call_direct_emergent(system_prompt, user_content, "claude-sonnet-4-6", timeout=timeout, max_tokens=max_tokens)
    return resp or ""


async def generate_multi_pass_memo(
    system_prompt: str,
    user_query: str,
    research_context: str = "",
    on_pass_complete=None,
    num_passes: int = 7,
) -> dict:
    """Generate a 9,000+ word partner memo via 7-pass Claude chaining.

    Args:
      system_prompt: SPECTR_SYSTEM_PROMPT (trimmed to 30K for per-pass speed)
      user_query: the user's legal question
      research_context: injected context (statute DB hits, IK cases, sandbox)
      on_pass_complete: optional async callback(pass_num, label, partial_text)
                        for streaming each pass as it completes (SSE)
      num_passes: 1-7. Default 7 = full memo. 4 = chat-style medium depth.

    Returns:
      dict:
        - "full_text": stitched memo (~8,800+ words at 7 passes)
        - "pass_texts": list of pass outputs
        - "pass_timings": seconds per pass
        - "total_words": int
        - "total_time": float
        - "aborted": bool — True if an early pass failed
    """
    # Trim to 15K — Sonnet 4.6 via Emergent proxy calibration (23 Apr 2026):
    # 15K sys + 2K max_tokens lands in 49s (under 60s proxy timeout).
    # Passes 2+ hit the prompt cache at 10% cost. Lossless: first 15K
    # contains identity + response shape + 5-phase reasoning + BEAST_MODE
    # + few-shot example. Downstream doctrinal extensions are redundant
    # with Sonnet's training at this size.
    sys_trimmed = system_prompt[:15000]

    user_block = (
        f"USER QUERY:\n{user_query}\n\n"
        + (f"RESEARCH CONTEXT:\n{research_context[:15000]}\n\n" if research_context else "")
    )

    pass_texts = []
    pass_timings = []
    pass_labels = []
    t_overall = time.time()

    instructions_to_run = PASS_INSTRUCTIONS[:num_passes]

    for i, (label, instruction) in enumerate(instructions_to_run, start=1):
        logger.info(f"Multi-pass memo — Pass {i}/{num_passes} ({label})")
        t = time.time()

        # Build context from prior passes
        if i == 1:
            prior_context = ""
        elif i <= 4:
            # Analysis passes get verbatim prior passes
            prior_tags = []
            for j, prev in enumerate(pass_texts, start=1):
                prior_tags.append(f"<PASS_{j}>\n{prev}\n</PASS_{j}>")
            prior_context = "\n\n".join(prior_tags) + "\n\n"
        else:
            # Later passes — prior output compressed to essential references
            combined = "\n\n".join(pass_texts)
            prior_context = f"<PRIOR_PASSES>\n{combined[:35000]}\n</PRIOR_PASSES>\n\n"

        pass_user = user_block + prior_context + instruction

        try:
            text = await _call_sonnet(sys_trimmed, pass_user)
        except Exception as e:
            logger.error(f"Pass {i} raised: {e}")
            text = ""

        elapsed = time.time() - t
        pass_timings.append(elapsed)
        pass_texts.append(text)
        pass_labels.append(label)

        words = len(text.split()) if text else 0
        logger.info(f"Pass {i} ({label}): {words:,} words in {elapsed:.1f}s")

        if on_pass_complete:
            try:
                await on_pass_complete(i, label, text)
            except Exception as e:
                logger.warning(f"on_pass_complete callback failed (non-blocking): {e}")

        # If the first pass failed, abort — no point chaining
        if i == 1 and (not text or len(text) < 200):
            logger.warning("Pass 1 failed — aborting multi-pass")
            return {
                "full_text": text or "",
                "pass_texts": pass_texts,
                "pass_timings": pass_timings,
                "pass_labels": pass_labels,
                "total_words": words,
                "total_time": time.time() - t_overall,
                "aborted": True,
            }

    # Stitch — strip <!-- PASS N COMPLETE --> markers, join with blank lines
    import re
    stripped = []
    for p in pass_texts:
        if not p:
            continue
        cleaned = re.sub(r"<!--\s*PASS\s*\d+\s*COMPLETE\s*-->", "", p).strip()
        stripped.append(cleaned)

    full_text = "\n\n".join(stripped)
    total_words = len(full_text.split())
    total_time = time.time() - t_overall

    logger.info(
        f"Multi-pass memo COMPLETE: {total_words:,} words across {len(pass_texts)} passes, "
        f"total {total_time:.1f}s (avg {total_time/max(1,len(pass_texts)):.1f}s/pass)"
    )

    return {
        "full_text": full_text,
        "pass_texts": pass_texts,
        "pass_timings": pass_timings,
        "pass_labels": pass_labels,
        "total_words": total_words,
        "total_time": total_time,
        "aborted": False,
    }
