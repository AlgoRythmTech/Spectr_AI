"""
Smart Query Router — decides which engine handles each query.

Three engines:
  1. ADVISORY (war_room_engine) — "What's my defense on this SCN?", "Analyze this notice"
  2. FILE_AUTOMATION (code_executor) — "Reconcile this GSTR", "Build advance tax tracker"
  3. HYBRID — "Research cases on X and draft a reply" (advisory → then file automation)

Routing signals:
  - File uploads present → likely automation
  - "draft", "generate", "create", "build" + Excel/Word/PDF → automation
  - "analyze", "research", "what's my position", "case law" → advisory
  - Playbook detected → automation (with playbook prompt)
"""

import re
from typing import Optional
from playbooks import detect_playbook_intent, get_playbook


# Strong signals for FILE_AUTOMATION
_AUTOMATION_STRONG = [
    r'\b(reconcile|reconciliation|reco)\b',
    r'\b(ageing|aging)\s+schedule\b',
    r'\btracker\b',
    r'\b(workpaper|work\s*paper|workbook)\b',
    r'\bexcel\b.{0,20}\b(create|build|generate|make)\b',
    r'\b(create|build|generate|make)\b.{0,20}\b(excel|xlsx|spreadsheet|workbook)\b',
    r'\b(word|docx)\s+(document|doc|file)\b.{0,20}\b(create|build|draft|generate|make)\b',
    r'\b(create|draft|build|generate|make)\b.{0,40}\b(word|docx)\s+(document|doc|file)\b',
    r'\b(tds|gst|payroll|bank|pf|esi|pt)\s+reconciliation\b',
    r'\b(compute|calculate)\s+.{0,50}\s+(ratio|ratios)\b',
    r'\b(build|create|generate)\s+.{0,30}\s+(chronology|timeline|matrix|summary)\b',
    r'\b(extract|parse)\s+.{0,30}\s+from\s+.{0,20}\s+(pdf|excel|documents)\b',
    r'\bconvert\s+.{0,30}\s+(to\s+excel|to\s+word|to\s+pdf)\b',
    r'\b(redlin|mark\s*up|annotate)\s+(this|the)\s+(contract|agreement|document)\b',
    r'\b(draft|prepare)\s+(a|an|the)\s+(nda|spa|sha|jv|agreement|contract|deed|petition|reply|appeal)\b',
    r'\b(advance\s+tax|income\s+tax|tds|gst)\s+(tracker|computation|calculation)\b',
    r'\buse\s+formulas?\b',
    r'\bsumif\b',
    r'\b(with|using)\s+excel\s+formulas?\b',
]

# Strong signals for ADVISORY
_ADVISORY_STRONG = [
    r'\b(what.?s\s+my\s+defense|strategy|what\s+should\s+i\s+do|legal\s+position|legal\s+analysis)\b',
    r'\b(case\s+law|precedent|judgment|ruling)\b',
    r'\b(analy[sz]e|assess|evaluate)\s+.{0,40}\s+(notice|order|appeal|contract|risk)\b',
    r'\b(opinion|advisory|opine)\b',
    r'\b(pros?\s+and\s+cons?|risks?\s+and\s+benefits?|advantages?)\b',
    r'\bwill\s+(i|we|this)\s+(win|lose|be\s+liable)\b',
    r'\b(explain|clarify|what\s+is)\s+.{0,50}(section|provision|rule|act)\b',
    r'\bdifference\s+between\s+.{0,40}(act|section|provision)\b',
]

# Hybrid signals (need BOTH advisory research + file output)
_HYBRID_SIGNALS = [
    r'\b(research|find\s+cases|analyze)\s+.{0,50}\s+and\s+(draft|prepare|generate|create)\b',
    r'\b(draft\s+.{0,20}\s+reply|draft\s+.{0,20}\s+notice).{0,40}\s+(based\s+on|with|including)\s+.{0,30}\s+case\s+law\b',
    r'\b(prepare\s+grounds\s+of\s+appeal|draft\s+statement\s+of\s+facts)\b.{0,100}\b(with|including)\s+.{0,30}\s+(case\s+law|precedent)\b',
]


def score_automation(query: str) -> int:
    """Higher score = more likely file automation task."""
    score = 0
    for pat in _AUTOMATION_STRONG:
        if re.search(pat, query, re.IGNORECASE):
            score += 3
    # File-format mentions
    for fmt in ['excel', 'xlsx', 'word', 'docx', 'pdf', 'jpg', 'png', 'csv']:
        if re.search(rf'\b{fmt}\b', query, re.IGNORECASE):
            score += 1
    # Action verbs suggesting output files
    for verb in ['create', 'build', 'generate', 'make', 'produce', 'prepare', 'construct']:
        if re.search(rf'\b{verb}\b', query, re.IGNORECASE):
            score += 1
    return score


def score_advisory(query: str) -> int:
    """Higher score = more likely advisory task."""
    score = 0
    for pat in _ADVISORY_STRONG:
        if re.search(pat, query, re.IGNORECASE):
            score += 3
    # Question words / analysis words
    for word in ['what', 'why', 'how', 'explain', 'analyze', 'assess', 'evaluate', 'opinion', 'position']:
        if re.search(rf'\b{word}\b', query, re.IGNORECASE):
            score += 1
    return score


def has_hybrid_signal(query: str) -> bool:
    for pat in _HYBRID_SIGNALS:
        if re.search(pat, query, re.IGNORECASE):
            return True
    return False


def route_query(
    user_query: str,
    has_uploaded_files: bool = False,
    force: Optional[str] = None,
) -> dict:
    """Route a query to the appropriate engine.

    Args:
      user_query: the user's prompt
      has_uploaded_files: True if request has file uploads
      force: optional forced routing ("advisory" / "automation" / "hybrid")

    Returns:
      {
        "engine": "advisory" | "automation" | "hybrid",
        "playbook_id": "nda" | "redlining" | ... | "",
        "automation_score": int,
        "advisory_score": int,
        "reason": str,
        "system_prompt_addon": str (playbook content if detected),
      }
    """
    if force and force in ("advisory", "automation", "hybrid"):
        playbook_id = detect_playbook_intent(user_query)
        return {
            "engine": force,
            "playbook_id": playbook_id,
            "automation_score": 0,
            "advisory_score": 0,
            "reason": f"Forced by caller to '{force}'",
            "system_prompt_addon": get_playbook(playbook_id) if playbook_id else "",
        }

    # Detect playbook FIRST (strong signal for automation with domain content)
    playbook_id = detect_playbook_intent(user_query)
    system_prompt_addon = get_playbook(playbook_id) if playbook_id else ""

    # Hybrid check
    if has_hybrid_signal(user_query):
        return {
            "engine": "hybrid",
            "playbook_id": playbook_id,
            "automation_score": 0,
            "advisory_score": 0,
            "reason": "Query asks for BOTH research and a file deliverable",
            "system_prompt_addon": system_prompt_addon,
        }

    # Score-based routing
    a_score = score_automation(user_query)
    ad_score = score_advisory(user_query)

    # File uploads → strong automation signal
    if has_uploaded_files:
        a_score += 5

    # Playbook detected → strong automation signal
    if playbook_id:
        a_score += 5

    # Decision
    if a_score > ad_score and a_score >= 3:
        engine = "automation"
        reason = f"File automation signals (score {a_score} vs advisory {ad_score})"
    elif ad_score > a_score and ad_score >= 3:
        engine = "advisory"
        reason = f"Advisory/analysis signals (score {ad_score} vs automation {a_score})"
    elif a_score == 0 and ad_score == 0:
        # Ambiguous — default to advisory (safer, existing behavior)
        engine = "advisory"
        reason = "Ambiguous query — defaulting to advisory"
    else:
        # Tie or low scores — prefer advisory unless files uploaded
        engine = "automation" if has_uploaded_files else "advisory"
        reason = f"Tie broken by file presence (a={a_score}, ad={ad_score}, files={has_uploaded_files})"

    return {
        "engine": engine,
        "playbook_id": playbook_id,
        "automation_score": a_score,
        "advisory_score": ad_score,
        "reason": reason,
        "system_prompt_addon": system_prompt_addon,
    }


# === QUICK SELF-TEST ===

if __name__ == "__main__":
    tests = [
        ("Reconcile this GSTR-2A with my Tally books", True, "automation"),
        ("What's my defense if I get a S.74 GST SCN?", False, "advisory"),
        ("Draft an NDA between ABC Ltd and XYZ Corp", False, "automation"),
        ("Build an advance tax tracker for AY 2026-27", False, "automation"),
        ("Research cases on ITC denial and draft a reply", False, "hybrid"),
        ("Explain Section 148A procedure", False, "advisory"),
        ("Redline this contract", True, "automation"),
        ("Generate a chronology from these order copies", True, "automation"),
    ]
    for q, has_files, expected in tests:
        result = route_query(q, has_files)
        status = "OK" if result["engine"] == expected else "MISS"
        print(f"[{status}] {q[:50]}... → {result['engine']} (expected {expected}) | playbook={result['playbook_id']} | reason={result['reason']}")
