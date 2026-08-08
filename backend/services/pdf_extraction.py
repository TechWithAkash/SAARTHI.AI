"""
Shared PDF text extraction — column-aware, noise-filtered.

WHY THIS IS ITS OWN MODULE
----------------------------
Originally written once, inline, in backend/scripts/build_guideline_corpus.py
to clean up the 4 research papers seeding the clinical RAG corpus. The exact
same problem then showed up again in doc_rag_service.py's document-upload
feature — plain pdfplumber.extract_text() on a two-column academic PDF
interleaves both columns' lines by vertical position, e.g. "Diabetes is a
chronic metabolic disorder char- Data source and study population" — and a
user uploading one of those same 4 papers got exactly that garbled text
staring back at them in the "document loaded" preview. Fixing it only in the
corpus-builder script would have left doc_rag_service.py broken; this module
exists so both callers share one fix instead of drifting again.

THE COLUMN-DETECTION APPROACH
-------------------------------
A hard 50/50-width crop correctly separates real two-column body text, but
wrongly slices centered single-column content (title pages, wide abstracts)
in half mid-word — verified by an earlier version of this exact code
producing "Machine learning predicts dia" / "populations: analysis of Natio".
Instead of guessing from text length, this measures the actual structural
signal: a histogram of each word's horizontal center. Two real columns leave
a visibly empty gutter around the page midpoint; single/centered content has
words continuously spanning across it. Only crop when a real gutter exists.
"""

import re

# A real two-column gutter is empty across at least this fraction of page
# width around the midpoint — i.e. very few word centers fall within it.
GUTTER_HALF_WIDTH_FRAC = 0.03    # +/- 3% of page width around the midpoint
MAX_WORDS_IN_GUTTER_FRAC = 0.04  # >4% of words straddling the midpoint = not a real gutter
MIN_WORDS_FOR_DECISION = 20      # too few words on a page to judge reliably -> fall back

# Lines matching these are typically running headers/footers/watermarks that
# repeat on every page and add noise without real content.
NOISE_LINE_PATTERNS = [
    re.compile(r"^\s*\d+\s*$"),                 # bare page numbers
    re.compile(r"^\s*Downloaded from\b", re.I),
    re.compile(r"^\s*http[s]?://\S+\s*$"),        # bare URLs (DOI lines duplicated as headers)
    re.compile(r"^\s*©\s*\d{4}", re.I),           # copyright lines
]

# Small-font sidebar/footer text (author contributions, funding statements,
# copyright/license boilerplate) sometimes extracts with NO spaces between
# words — pdfplumber's space-inference relies on gap width, which breaks down
# at small kerning: "betteroriginalpublicationinthisjournaliscited" instead
# of real prose. Never legitimate content; dropped outright rather than
# passed through as noise, since it reads as broken if it ever surfaces.
RUN_ON_TEXT = re.compile(r"[A-Za-z]{25,}")


def _has_real_column_gutter(page) -> bool:
    """Structural test: does this page actually have two columns, or would a
    hard 50/50 crop slice single/centered content mid-word?"""
    words = page.extract_words()
    if len(words) < MIN_WORDS_FOR_DECISION:
        return False

    mid = page.width / 2
    gutter_lo = mid - page.width * GUTTER_HALF_WIDTH_FRAC
    gutter_hi = mid + page.width * GUTTER_HALF_WIDTH_FRAC

    in_gutter = sum(
        1 for w in words
        if gutter_lo <= (w["x0"] + w["x1"]) / 2 <= gutter_hi
    )
    return (in_gutter / len(words)) <= MAX_WORDS_IN_GUTTER_FRAC


def extract_page_text(page) -> str:
    """Column-aware extraction, only when the page structurally has one."""
    if _has_real_column_gutter(page):
        left = page.crop((0, 0, page.width / 2, page.height))
        right = page.crop((page.width / 2, 0, page.width, page.height))
        left_text = (left.extract_text() or "").strip()
        right_text = (right.extract_text() or "").strip()
        if left_text or right_text:
            return left_text + "\n\n" + right_text

    # No real gutter detected (title page, centered abstract, wide table/
    # figure) — plain full-page extraction reads it correctly as-is.
    return (page.extract_text() or "").strip()


def clean_extracted_text(text: str) -> str:
    lines = text.split("\n")
    kept = []
    for line in lines:
        if any(pat.match(line) for pat in NOISE_LINE_PATTERNS):
            continue
        if RUN_ON_TEXT.search(line):
            continue
        kept.append(line)
    cleaned = "\n".join(kept)

    # Rejoin hyphenated line-wraps: "char-\nacterized" -> "characterized".
    # Conservative: only joins lowercase word fragments on both sides, so
    # real end-of-sentence hyphens or acronyms aren't merged.
    cleaned = re.sub(r"([a-z])-\n([a-z])", r"\1\2", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def extract_pdf_text(data: bytes) -> str:
    """
    Full pipeline: raw PDF bytes -> clean text. Tables are extracted
    separately per page (pdfplumber's table detection already handles
    layout correctly for tabular data — medical labs are often tabular).
    """
    import io
    import pdfplumber

    text_parts = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    clean = [str(c).strip() if c else "" for c in row]
                    if any(clean):
                        text_parts.append(" | ".join(clean))

            page_text = extract_page_text(page)
            if page_text.strip():
                text_parts.append(clean_extracted_text(page_text))

    return "\n\n".join(text_parts)
