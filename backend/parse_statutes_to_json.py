"""
parse_statutes_to_json.py — turn bare-act PDFs into uploader-ready JSON.

READS FROM: C:\\Associate\\Firestore Data\\*.pdf   (never modifies source)
WRITES TO:  backend/seed_data/statutes/*.json     (one file per act)

Strategy
--------
1. For each PDF, extract every page's text with PyMuPDF (preserves Unicode).
2. Strip page-header/footer noise (page numbers, repeated act titles).
3. Find section boundaries using the reliable marker:
     "^N. Title.—..."  where the em-dash (U+2014) follows the title period.
   TOC entries end with just "." so we avoid false hits there.
4. For each section capture: section_number, section_title, section_text (full
   body up to the next section header, verbatim — nothing dropped).
5. Auto-generate `keywords` from title + early body text (lowercased nouns,
   statute cross-references, dates, section numbers). Keywords are additive;
   preserves the user's ability to hand-edit later.
6. Write one JSON file per act, list of section objects, matching the schema
   in seed_data/statutes/_SCHEMA.json so seed_statutes_to_firestore.py picks
   them up directly.

Running
-------
    python parse_statutes_to_json.py           # parse everything
    python parse_statutes_to_json.py --only "Bharatiya Nyaya"   # just one act
    python parse_statutes_to_json.py --dry     # parse but don't write files
    python parse_statutes_to_json.py --verbose # show every parsed section

The script does NOT upload to Firestore. Run
`python seed_statutes_to_firestore.py --commit` after parsing is clean.
"""
import os
import re
import sys
import json
import argparse
from pathlib import Path
from collections import Counter

import fitz  # PyMuPDF

SRC_DIR = Path(r"C:\Associate\Firestore Data")
OUT_DIR = Path(__file__).parent / "seed_data" / "statutes"

# Normalise dash variants to ASCII for regex ease, but keep them in output.
EM_DASH = "\u2014"   # —
EN_DASH = "\u2013"   # –
DASHES = f"[{EM_DASH}{EN_DASH}-]"  # matches any of them

# ────────────────────────────────────────────────────────────────────────
# File name → canonical act name mapping. Retrieval uses act_name verbatim,
# so these strings must match the triggers in server.py:ACT_MAP.
# ────────────────────────────────────────────────────────────────────────
FILENAME_TO_ACT = {
    "The Banking Regulation Act, 1949.pdf":
        "Banking Regulation Act, 1949",
    "THE BHARATIYA NAGARIK SURAKSHA SANHITA, 2023.pdf":
        "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
    "The Bharatiya Nyaya Sanhita, 2023.pdf":
        "Bharatiya Nyaya Sanhita, 2023 (BNS)",
    "The Bharatiya Sakshya Adhiniyam, 2023.pdf":
        "Bharatiya Sakshya Adhiniyam, 2023 (BSA)",
    "The Central Goods and Services Tax Act, 2017.pdf":
        "Central Goods and Services Tax Act, 2017 (CGST)",
    "THE COMPANIES ACT, 2013.pdf":
        "Companies Act, 2013",
    "THE FOREIGN EXCHANGE MANAGEMENT ACT, 1999.pdf":
        "Foreign Exchange Management Act, 1999 (FEMA)",
    "THE GOODS AND SERVICES TAX (COMPENSATION TO STATES).pdf":
        "Goods and Services Tax (Compensation to States) Act, 2017",
    "THE INCOME-TAX ACT, 1961.pdf":
        "Income Tax Act, 1961",
    "THE INDIAN PARTNERSHIP ACT, 1932.pdf":
        "Indian Partnership Act, 1932",
    "The Integrated Goods and Services Tax Act, 2017.pdf":
        "Integrated Goods and Services Tax Act, 2017 (IGST)",
    "THE LIMITED LIABILITY PARTNERSHIP ACT, 2008.pdf":
        "Limited Liability Partnership Act, 2008 (LLP)",
    "THE RESERVE BANK OF INDIA ACT, 1934.pdf":
        "Reserve Bank of India Act, 1934 (RBI Act)",
    "The Securities and Exchange Board of India Act, 1992.pdf":
        "Securities and Exchange Board of India Act, 1992 (SEBI Act)",
    "THE UNION TERRITORY GOODS AND SERVICES TAX ACT, 2017.pdf":
        "Union Territory Goods and Services Tax Act, 2017 (UTGST)",
    "the_arbitration_and_conciliation_act,_1996_act_no._26_of_1996.pdf":
        "Arbitration and Conciliation Act, 1996",
    "the_insolvency_and_bankruptcy_code,_2016.pdf":
        "Insolvency and Bankruptcy Code, 2016 (IBC)",
}

# ────────────────────────────────────────────────────────────────────────
# Stopwords for keyword generation — drop from auto-extracted tokens.
# ────────────────────────────────────────────────────────────────────────
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "for", "on", "by",
    "with", "as", "is", "was", "be", "are", "were", "been", "being",
    "this", "that", "these", "those", "it", "its", "any", "all", "such",
    "shall", "may", "will", "would", "could", "should", "must", "has",
    "have", "had", "do", "does", "did", "done", "so", "than", "then",
    "if", "not", "no", "but", "from", "at", "into", "out", "up", "down",
    "under", "over", "upon", "before", "after", "during", "until",
    "against", "between", "among", "which", "who", "whom", "whose",
    "whoever", "where", "when", "what", "why", "how", "section",
    "subsection", "clause", "provided", "providing", "provision",
    "provisions", "provides", "including", "include", "includes",
    "act", "person", "persons", "case", "cases", "other", "another",
    "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten",
}


# ────────────────────────────────────────────────────────────────────────
# Text extraction
# ────────────────────────────────────────────────────────────────────────
def extract_full_text(pdf_path: Path) -> str:
    """Concat every page's text, preserving characters verbatim.
    Strips page-top numbers ('\\n5 \\n') so section-start regex isn't confused.
    """
    doc = fitz.open(pdf_path)
    parts = []
    for page in doc:
        t = page.get_text()
        # PyMuPDF preserves Unicode em-dash, right-single-quote, etc. No transforms.
        parts.append(t)
    doc.close()
    full = "\n".join(parts)

    # Strip standalone page numbers on their own line (common: "  5 \n")
    full = re.sub(r"^\s*\d{1,4}\s*$\n", "", full, flags=re.MULTILINE)
    return full


# ────────────────────────────────────────────────────────────────────────
# Section parsing
# ────────────────────────────────────────────────────────────────────────
# Matches a section header like:
#   "1. Short title, extent and commencement.—(1) ..."
#   "194T. Payments to partners.—"
#   "43B. Certain deductions to be only on actual payment.—"
#   "10. Punishment of person guilty of one of several offences,\n
#        judgment stating that it is doubtful of which group he is guilty.—"
#
# Indian bare-act PDFs wrap long titles across lines. The title may span up
# to ~300 chars across 3 lines. The em-dash AFTER a title-ending period is
# the distinguishing marker vs TOC lines (which end with just "." + newline).
#
# We allow newlines inside the title but bound total title length to 300
# chars to avoid runaway matches. TOC entries can't match because TOC lines
# have no em-dash anywhere — they end with just "." followed by the next TOC
# entry or a chapter heading.
SECTION_HEADER = re.compile(
    # Title body: any character, non-greedy, up to 350 chars, EXCEPT we stop
    # if we hit a line that starts with "N. SomeTitle" (next section header)
    # or a CHAPTER heading. The final `\.\s*DASH` terminator captures the
    # title end. Non-greedy matching finds the earliest valid terminator so
    # embedded periods like "etc." inside the title don't trip us up.
    rf"^\s*(\d+[A-Z]{{0,3}})\.\s+([A-Z](?:(?!\n\s*(?:CHAPTER|\d+[A-Z]{{0,3}}\.\s+[A-Z])).){{2,350}}?)\.\s*{DASHES}",
    re.MULTILINE | re.DOTALL,
)

# Fallback pattern for short GST-family acts (UTGST, GST Compensation) that
# omit section titles and go directly from "1." to "(1) This Act...". These
# sections have no title — body starts right after the period.
SECTION_HEADER_NO_TITLE = re.compile(
    r"^\s*(\d+[A-Z]{0,3})\.\s+(?=\(1\))",
    re.MULTILINE,
)


def parse_sections(full_text: str, act_name: str) -> list[dict]:
    """Split the full document text into one dict per section.

    The em-dash after the title is the distinguishing feature vs TOC lines —
    TOC prints 'N. Title.' while the real section prints 'N. Title.—body'.

    We collect every (start, end, number, title) match, then extract the
    body as full_text[header_end : next_header_start].
    """
    matches = list(SECTION_HEADER.finditer(full_text))

    # If the primary pattern found almost nothing, try the no-title fallback
    # for short GST-family acts (UTGST, GST Compensation) that skip titles.
    if len(matches) < 5:
        fb = list(SECTION_HEADER_NO_TITLE.finditer(full_text))
        if len(fb) > len(matches):
            # Synthesize two-group matches (number, empty title) for downstream
            # compatibility. We wrap fb matches in a simple shim class.
            class _Shim:
                def __init__(self, m):
                    self._m = m
                def group(self, i):
                    if i == 1: return self._m.group(1)
                    if i == 2: return ""  # no title
                    return self._m.group(i)
                def start(self): return self._m.start()
                def end(self): return self._m.end()
            matches = [_Shim(m) for m in fb]

    if not matches:
        return []

    # De-duplicate: the same section number can appear in TOC OR in amendments.
    # We want the LONGEST body — the real section occurrence, not a cross-ref.
    # Strategy: iterate matches in order, for each number keep the occurrence
    # whose body is longest (likely the actual section text, not a mention).
    sections_by_num: dict[str, dict] = {}
    for i, m in enumerate(matches):
        number = m.group(1).strip()
        title = m.group(2).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        body = full_text[body_start:body_end].strip()

        # Skip obviously broken matches (tiny bodies = probably header fragments)
        if len(body) < 15:
            continue

        # Section body should start where the em-dash would be — re-attach the
        # punctuation so quotes in the output read like the act itself.
        # m.group(0) ends with the dash; we keep body starting just after dash.
        # Remove leading dashes/whitespace from body
        body = re.sub(rf"^\s*{DASHES}\s*", "", body)

        existing = sections_by_num.get(number)
        if existing is None or len(body) > len(existing["_body_len"]):
            sections_by_num[number] = {
                "act_name": act_name,
                "section_number": number,
                "section_title": _clean_title(title),
                "section_text": body,
                "_body_len": body,  # internal for longest-match selection
            }

    # Drop internal field and sort by numeric order (1, 2, ..., 194, 194A, 194T)
    out = []
    for number, s in sections_by_num.items():
        s.pop("_body_len", None)
        out.append(s)
    out.sort(key=_sort_key)
    return out


def _clean_title(t: str) -> str:
    """Normalise whitespace but preserve every character."""
    return re.sub(r"\s+", " ", t).strip()


def _sort_key(section: dict):
    """Sort sections so '1 < 2 < 43 < 43A < 43B < 44 < 194 < 194A < 194T'."""
    num = section["section_number"]
    m = re.match(r"^(\d+)([A-Z]*)$", num)
    if m:
        return (int(m.group(1)), m.group(2))
    return (10**9, num)


# ────────────────────────────────────────────────────────────────────────
# Keyword generation
# ────────────────────────────────────────────────────────────────────────
def generate_keywords(section: dict, act_name: str) -> list[str]:
    """Build a keywords array from title + first 300 words of body.

    We want terms a user would actually type in a query. So:
      - the section number itself (e.g. "103", "194T")
      - the act abbreviation if present ("BNS", "BNSS", "CGST")
      - meaningful content words from title (lower-cased, stopwords removed)
      - cross-references to other sections (e.g. "section 45", "73", "74")
      - notable years / amounts
      - capitalised multi-word phrases (probably proper nouns / defined terms)
    """
    title = section["section_title"]
    body = section["section_text"][:3000]
    number = section["section_number"]

    tokens = set()

    # Section number itself — exact-match search is the #1 retrieval path.
    tokens.add(number.lower())

    # Act abbreviation
    abbr = re.search(r"\(([A-Z]{2,6})\)", act_name)
    if abbr:
        tokens.add(abbr.group(1).lower())

    # Title words (alpha only, ≥4 chars, non-stopword)
    for w in re.findall(r"[A-Za-z][A-Za-z\-]+", title):
        wl = w.lower()
        if len(wl) >= 4 and wl not in STOPWORDS:
            tokens.add(wl)

    # Body: capture capitalised phrases (likely defined/proper terms)
    for phrase in re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b", body):
        ph = phrase.lower()
        if len(ph) <= 50 and ph not in STOPWORDS:
            tokens.add(ph)

    # Body: cross-references to sections ("section 73", "under section 194T")
    for ref in re.findall(r"section\s+(\d+[A-Z]{0,3})", body, flags=re.IGNORECASE):
        tokens.add(ref.lower())

    # Body: rupee amounts ("one lakh rupees", "₹50,000")
    if re.search(r"rupees|\u20b9", body, re.IGNORECASE):
        tokens.add("rupees")
    if re.search(r"\blakh\b", body, re.IGNORECASE):
        tokens.add("lakh")
    if re.search(r"\bcrore\b", body, re.IGNORECASE):
        tokens.add("crore")

    # Body-heavy content words (take top 20 most frequent non-stopword words)
    word_counts = Counter(
        w.lower() for w in re.findall(r"[A-Za-z][A-Za-z\-]+", body)
        if len(w) >= 5 and w.lower() not in STOPWORDS
    )
    for w, _ in word_counts.most_common(15):
        tokens.add(w)

    # Cap total length, prefer shorter + more specific terms
    result = sorted(tokens, key=lambda t: (len(t), t))[:25]
    return result


# ────────────────────────────────────────────────────────────────────────
# Output
# ────────────────────────────────────────────────────────────────────────
def act_to_filename(act_name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", act_name).strip("_").lower()
    return f"{slug}.json"


def save_act(act_name: str, sections: list[dict], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    fp = out_dir / act_to_filename(act_name)
    # Final enrich: add keywords + trim internals
    enriched = []
    for s in sections:
        s["keywords"] = generate_keywords(s, act_name)
        s.setdefault("effective_from", "")
        s.setdefault("amendment_note", "")
        enriched.append(s)
    fp.write_text(json.dumps(enriched, indent=2, ensure_ascii=False), encoding="utf-8")
    return fp


# ────────────────────────────────────────────────────────────────────────
# Driver
# ────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=str, default=None,
                    help="Parse only PDFs whose filename contains this substring")
    ap.add_argument("--dry", action="store_true",
                    help="Parse but don't write JSON files")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if not SRC_DIR.exists():
        print(f"ERROR: source directory not found: {SRC_DIR}")
        sys.exit(1)

    print(f"Source: {SRC_DIR}")
    print(f"Output: {OUT_DIR}")
    print()

    pdfs = sorted(SRC_DIR.glob("*.pdf"))
    if args.only:
        pdfs = [p for p in pdfs if args.only.lower() in p.name.lower()]
    if not pdfs:
        print("No PDFs match.")
        sys.exit(1)

    total_sections = 0
    summary = []

    for pdf in pdfs:
        act_name = FILENAME_TO_ACT.get(pdf.name)
        if not act_name:
            print(f"  [SKIP] no act_name mapping for: {pdf.name}")
            continue
        print(f"  [PARSE] {pdf.name}")
        full = extract_full_text(pdf)
        sections = parse_sections(full, act_name)
        print(f"          -> extracted {len(sections)} sections ({len(full)/1024:.0f} KB of text)")

        if args.verbose and sections:
            # Show first, a middle one, and last for spot check
            idxs = [0, len(sections)//2, len(sections)-1]
            for i in idxs:
                s = sections[i]
                body_preview = s['section_text'][:160].replace('\n', ' ')
                print(f"            §{s['section_number']}  {s['section_title'][:60]}")
                print(f"              body: {body_preview}...")

        if not args.dry and sections:
            fp = save_act(act_name, sections, OUT_DIR)
            print(f"          -> wrote {fp.name}")

        total_sections += len(sections)
        summary.append((act_name, len(sections)))

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for act, n in summary:
        print(f"  {n:5d}  {act}")
    print(f"  {'-'*5}")
    print(f"  {total_sections:5d}  TOTAL sections")
    if args.dry:
        print()
        print("DRY RUN — no files written. Drop --dry to emit JSON.")


if __name__ == "__main__":
    main()
