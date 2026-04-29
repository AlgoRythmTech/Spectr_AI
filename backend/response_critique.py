"""
Response Critique Module — Adversarial Self-Review Pass for Spectr.

After a response is generated, this module runs an adversarial critique that:
1. Checks if the response found loopholes a competent practitioner would miss
2. Verifies structural quality (BLUF, citations, quantification, deadlines)
3. Identifies missed counter-arguments
4. Flags hallucinated citations
5. Ensures the response passes the "Big 4 Partner Review" standard

This is what separates good output from god-tier output.
"""
import re
import logging
import aiohttp
from typing import Optional

logger = logging.getLogger("response_critique")


CRITIQUE_PROMPT = """You are the Senior Managing Partner reviewing an associate's work product before it goes to a ₹100 crore client. You have 30 years of practice at the highest level. You miss nothing.

Your job: identify every weakness in this draft response and tell me EXACTLY what needs to be fixed.

## REVIEW CHECKLIST (BE RUTHLESS)

### A. THE LOOPHOLE TEST
1. Did the response identify ALL procedural defects? (DIN, limitation, jurisdiction, natural justice)
2. Did it find ANY argument the competent practitioner would miss?
3. Did it exhaust ALL constitutional challenges where applicable?
4. Did it identify conflicting authorities?
5. Did it quantify cascade impacts (S.50 interest, S.270A penalty, S.43B disallowance, etc.)?

### B. THE QUANTIFICATION TEST
1. Is every exposure calculated to the exact rupee?
2. Are all deadlines given as EXACT DATES (not "within 30 days")?
3. Are probabilities assigned to each strategy?
4. Is the cost-benefit of each move explicit?

### C. THE CITATION TEST
1. Is every case citation real and verifiable? (Flag suspicious citations)
2. Is every section number correct and current? (Flag amendment-stale citations)
3. Are source tags present on every legal claim? ([MongoDB Statute DB], [IndianKanoon], [From training], [Serper])
4. Are any cited cases actually SUPERSEDED by amendments? (e.g., CIT v. Smifs Securities post-AY 2021-22)

### D. THE ADVERSARIAL TEST
1. What's the BEST argument opposing counsel would make?
2. Has the response pre-empted that argument?
3. What's the weakest link in our position?
4. Has the response acknowledged it honestly?

### E. THE STRUCTURAL TEST
1. Does it start with BLUF (Bottom Line Up Front)?
2. Is there a clear strategic recommendation?
3. Are next steps SPECIFIC (form numbers, portals, deadlines)?
4. Is the risk_analysis block present and populated?

## OUTPUT FORMAT

Output your critique as:

CRITIQUE_SCORE: [1-10]
TOP_WEAKNESSES:
- [weakness 1 with specific fix]
- [weakness 2 with specific fix]
- [weakness 3 with specific fix]
MISSING_ARGUMENTS:
- [argument 1 that should be added]
- [argument 2]
HALLUCINATION_FLAGS:
- [citation that looks suspicious — verify]
ACTION: [APPROVE | REVISE | MAJOR_REWRITE]

If APPROVE: the response is institutional-grade and ready to ship.
If REVISE: specific minor improvements needed.
If MAJOR_REWRITE: fundamental flaws require a full redraft.

Be brutal. If this goes to a client with weaknesses, my name and this firm's reputation are on the line."""


# ==================== STRUCTURAL VERIFICATION ====================

# Quality signals — responses missing these score lower
_REQUIRED_QUANTIFICATION_TRIGGERS = [
    r'\b(penalty|exposure|demand|tax|interest|fine)\b',
    r'\b(crore|lakh|rupee|₹|rs\.?)\b',
]

_REQUIRED_DEADLINE_TRIGGERS = [
    r'\b(notice|appeal|file|filing|return|assessment|limitation|deadline)\b',
]

# Patterns that indicate solid response quality
_QUALITY_SIGNALS = {
    "has_bluf": [
        r'(?i)^\s*\*\*(bottom line|executive summary|conclusion)\*\*',
        r'(?i)^\s*(The notice|The position|The answer|The law)',
    ],
    "has_citations": [
        r'\[Source:',
        r'\[From training',
        r'\(SC\)|\(HC\)|\(ITAT|\(CESTAT|\(NCLT',
        r'Section\s+\d+',
    ],
    "has_quantification": [
        r'₹\s*[\d,]+',
        r'Rs\.?\s*[\d,]+',
        r'\d+\s*%',
        r'[\d,]+\s*(crore|lakh)',
    ],
    "has_strategy": [
        r'(?i)strateg(y|ies)',
        r'(?i)(move|action|step)',
        r'(?i)(recommend|suggest|advise)',
    ],
    "has_opposing_anticipation": [
        r'(?i)opposing\s*(counsel|party|side|argument)',
        r'(?i)(revenue|department).*(argue|contend|claim)',
        r'(?i)(counter|contra|adverse).*(argument|position|view)',
        r'(?i)(distinguish|overrule|distinguished)',
    ],
    "has_risk_analysis_block": [
        r'<risk_analysis>',
        r'EXPOSURE:',
        r'WIN_PROBABILITY',
        r'STRATEGY_[A-C]',
    ],
    "has_deadlines": [
        r'\b(\d{1,2}[\-\s](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))',
        r'\b(\d{4}[\-/]\d{2}[\-/]\d{2})',
        r'(?i)by\s+\d+',
        r'(?i)before\s+(\d|the)',
    ],
}


def structural_score(response: str) -> dict:
    """Compute a structural quality score for a response.

    Returns a dict with:
      - score: 0-100
      - signals: dict of signal_name -> bool
      - missing: list of missing signals
      - recommendations: list of improvement suggestions
    """
    if not response or len(response) < 100:
        return {
            "score": 0,
            "signals": {k: False for k in _QUALITY_SIGNALS},
            "missing": list(_QUALITY_SIGNALS.keys()),
            "recommendations": ["Response too short — provide substantive analysis"],
        }

    signals = {}
    for signal_name, patterns in _QUALITY_SIGNALS.items():
        signals[signal_name] = any(re.search(p, response) for p in patterns)

    # Score calculation — each signal is worth up to ~14 points
    signal_weights = {
        "has_bluf": 10,
        "has_citations": 20,
        "has_quantification": 15,
        "has_strategy": 15,
        "has_opposing_anticipation": 15,
        "has_risk_analysis_block": 15,
        "has_deadlines": 10,
    }
    score = sum(weight for sig, weight in signal_weights.items() if signals.get(sig))

    # Context-aware checks — only penalize if the response should have these
    needs_quant = any(re.search(p, response, re.IGNORECASE) for p in _REQUIRED_QUANTIFICATION_TRIGGERS)
    needs_deadline = any(re.search(p, response, re.IGNORECASE) for p in _REQUIRED_DEADLINE_TRIGGERS)

    missing = [k for k, v in signals.items() if not v]
    recommendations = []

    if not signals["has_bluf"]:
        recommendations.append("Add BLUF (Bottom Line Up Front) — state conclusion in first 2 sentences")
    if not signals["has_citations"] or len(re.findall(r'Section\s+\d+', response)) < 2:
        recommendations.append("Cite more statutory provisions with section numbers")
    if needs_quant and not signals["has_quantification"]:
        recommendations.append("Query involves financial exposure — quantify in ₹ to exact amount")
        score -= 10
    if needs_deadline and not signals["has_deadlines"]:
        recommendations.append("Query involves notice/filing — provide exact deadline dates")
        score -= 10
    if not signals["has_opposing_anticipation"]:
        recommendations.append("Pre-empt opposing counsel's counter-argument")
    if not signals["has_risk_analysis_block"]:
        recommendations.append("Add <risk_analysis> block with exposure, probability, strategy comparison")
    if not signals["has_strategy"]:
        recommendations.append("Include specific strategic moves — not just legal analysis")

    return {
        "score": max(0, min(100, score)),
        "signals": signals,
        "missing": missing,
        "recommendations": recommendations,
        "needs_quantification": needs_quant,
        "needs_deadline": needs_deadline,
    }


# ==================== HALLUCINATION DETECTION ====================

# Citations that look like real SC cases should follow a pattern
_CASE_CITATION_PATTERN = re.compile(
    r'([A-Z][a-zA-Z\s&.]+?)\s+v(?:s?|\.)\s+([A-Z][a-zA-Z\s&.]+?)[,\s]+(?:\(|\[)?(\d{4})(?:\)|\])?'
)

# Known POST-AMENDMENT cases where the holding is narrowed/superseded
_KNOWN_SUPERSEDED = {
    r'smifs\s+securities': 'PARTIALLY SUPERSEDED — Finance Act 2021 excluded goodwill from S.32 depreciation w.e.f. AY 2021-22',
    r'vodafone\s+international': 'RETROSPECTIVELY OVERRIDDEN — Finance Act 2012 Explanation 5 to S.9(1)(i), then repealed 2021',
    r'larsen\s+(&|and)\s+toubro\s+(ltd\.?)?\s*\(2014\)': 'PRE-GST — For GST, cite S.7 CGST Act, 2017 for barter/exchange',
    r'gkn\s+driveshafts': 'Still good law but check S.148A (Finance Act 2021) procedural requirements',
}


def detect_hallucination_risks(response: str) -> list[dict]:
    """Scan response for citations that may be hallucinated or stale.

    Returns list of flags, each with: {type, match, concern, suggestion}
    """
    flags = []

    # Check for POST-AMENDMENT superseded cases cited without the amendment note
    for pattern, note in _KNOWN_SUPERSEDED.items():
        if re.search(pattern, response, re.IGNORECASE):
            # Was the amendment caveat mentioned?
            if not re.search(r'(?i)(superseded|overruled|amended|finance act|narrowed|distinguished)', response):
                flags.append({
                    "type": "superseded_citation",
                    "match": pattern,
                    "concern": note,
                    "suggestion": "Add the amendment caveat to avoid misleading the client",
                })

    # Check for citations without source tags
    case_cites = _CASE_CITATION_PATTERN.findall(response)
    source_tags = re.findall(r'\[Source:[^\]]+\]|\[From training[^\]]*\]', response)
    if len(case_cites) > 2 and len(source_tags) < 2:
        flags.append({
            "type": "missing_source_tags",
            "match": f"{len(case_cites)} case citations, {len(source_tags)} source tags",
            "concern": "Case citations lack source tags — cannot verify which are from training vs DB",
            "suggestion": "Add [Source: IndianKanoon — Live API] or [From training — verify] after each citation",
        })

    # Check for stale Rule 36(4) language
    if re.search(r'rule\s*36\(4\).*(removed|abolished|deleted)', response, re.IGNORECASE):
        flags.append({
            "type": "stale_rule_36_4",
            "match": "Rule 36(4)",
            "concern": "Rule 36(4) was AMENDED (not removed) — it now restricts ITC to 100% of GSTR-2B",
            "suggestion": "Correct the statement — Rule 36(4) is STRICTER now, not absent",
        })

    # Check for old regime slabs for AY 2026-27+ queries
    if re.search(r'(?i)(AY\s*2026|FY\s*2025).*?(5|10|15|20|30)\s*%.*?(?:lakh|₹|rs)', response):
        if not re.search(r'new\s*regime|115BAC|87A\s*rebate.*60,000|12,?00,?000', response, re.IGNORECASE):
            flags.append({
                "type": "possibly_stale_slabs",
                "match": "tax slab discussion for AY 2026-27+",
                "concern": "New regime slabs (Finance Act 2025): 0-4L nil, 4-8L 5%, 8-12L 10%, 12-16L 15%, 16-20L 20%, 20-24L 25%, 24L+ 30%",
                "suggestion": "Verify slabs match Finance Act 2025 new regime",
            })

    return flags


async def run_critique_pass(
    session: aiohttp.ClientSession,
    original_response: str,
    query: str,
    groq_key: str,
    timeout: int = 20,
) -> Optional[dict]:
    """Run an adversarial critique pass using Groq for speed.

    Returns dict with:
      - critique_text: the partner review
      - score: extracted CRITIQUE_SCORE
      - action: APPROVE / REVISE / MAJOR_REWRITE
      - weaknesses: list of weaknesses
    """
    if not original_response or len(original_response) < 200 or not groq_key:
        return None

    # Truncate original response for critique (we only need the gist)
    snippet = original_response[:6000]
    user_content = f"QUERY:\n{query[:500]}\n\n---\n\nDRAFT RESPONSE TO REVIEW:\n{snippet}"

    try:
        async with session.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": CRITIQUE_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.2,
                "max_tokens": 1200,
            },
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            if resp.status != 200:
                logger.warning(f"Critique pass failed: {resp.status}")
                return None
            data = await resp.json()
            critique_text = data["choices"][0]["message"]["content"]

        # Extract score
        score_match = re.search(r'CRITIQUE_SCORE:\s*(\d+)', critique_text)
        score = int(score_match.group(1)) if score_match else 7

        # Extract action
        action_match = re.search(r'ACTION:\s*(APPROVE|REVISE|MAJOR_REWRITE)', critique_text, re.IGNORECASE)
        action = action_match.group(1).upper() if action_match else "REVISE"

        # Extract weaknesses
        weaknesses = re.findall(r'(?<=TOP_WEAKNESSES:\s).+?(?=(?:MISSING_ARGUMENTS|HALLUCINATION|ACTION|$))',
                                critique_text, re.IGNORECASE | re.DOTALL)
        weaknesses_list = []
        if weaknesses:
            weaknesses_list = [line.strip("- ").strip() for line in weaknesses[0].splitlines() if line.strip().startswith("-")]

        return {
            "critique_text": critique_text,
            "score": score,
            "action": action,
            "weaknesses": weaknesses_list,
        }
    except Exception as e:
        logger.warning(f"Critique pass exception: {e}")
        return None


def format_critique_feedback(critique: dict, structural: dict, hallucinations: list) -> str:
    """Format critique output as internal feedback the LLM can use to improve."""
    parts = ["=== INTERNAL QUALITY REVIEW (for revision) ==="]
    if structural:
        parts.append(f"Structural score: {structural['score']}/100")
        if structural['recommendations']:
            parts.append("Structural fixes needed:")
            for r in structural['recommendations'][:5]:
                parts.append(f"  - {r}")

    if hallucinations:
        parts.append("Citation risks:")
        for h in hallucinations[:3]:
            parts.append(f"  - {h['concern']} → {h['suggestion']}")

    if critique:
        parts.append(f"Partner review score: {critique['score']}/10 — ACTION: {critique['action']}")
        if critique['weaknesses']:
            parts.append("Partner feedback:")
            for w in critique['weaknesses'][:3]:
                parts.append(f"  - {w}")

    return "\n".join(parts)
