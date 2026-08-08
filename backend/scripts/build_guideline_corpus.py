"""
One-time (re-runnable) corpus builder: research_papers/*.pdf -> guideline_corpus/*.md

WHY THIS EXISTS SEPARATELY FROM rag.py
----------------------------------------
rag.py's DocumentLoader only reads .md — per the explicit instruction to reuse
rag.py rather than rebuild it, this script does NOT touch rag.py at all. It's
a preprocessing step: extract clean text from the real PDFs supplied, write
markdown files where rag.py already knows to look (RAG_CORPUS_DIR /
guideline_corpus). Re-run this whenever a new PDF is added to research_papers/.

The actual column-aware, noise-filtered extraction logic lives in
backend/services/pdf_extraction.py, shared with doc_rag_service.py's document
upload feature — the same garbled-text problem this script originally fixed
(two-column academic PDFs interleaving by vertical position) showed up again
there when a user uploaded one of these same 4 papers directly. One fix,
two callers, so they can't drift apart again.

Run: /opt/anaconda3/envs/darpanai/bin/python3 backend/scripts/build_guideline_corpus.py
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

SRC_DIR = REPO_ROOT / "research_papers"
OUT_DIR = REPO_ROOT / "guideline_corpus"

from backend.services.pdf_extraction import extract_page_text, clean_extracted_text  # noqa: E402


def build_one(pdf_path: Path) -> Path:
    import pdfplumber

    print(f"Extracting: {pdf_path.name}")
    pages_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            raw = extract_page_text(page)
            if raw.strip():
                pages_text.append(clean_extracted_text(raw))
            if (i + 1) % 10 == 0:
                print(f"  ...{i + 1} pages")

    full_text = "\n\n".join(pages_text)

    # Title = first non-empty line of the extracted text (title pages
    # extract cleanly since they're usually not two-column).
    first_lines = [l.strip() for l in full_text.split("\n") if l.strip()]
    title = first_lines[0] if first_lines else pdf_path.stem

    slug = re.sub(r"[^a-z0-9]+", "_", pdf_path.stem.lower()).strip("_")
    out_path = OUT_DIR / f"{slug}.md"

    header = (
        f"# {title}\n\n"
        f"*Source file: {pdf_path.name} — extracted verbatim via pdfplumber, "
        f"column-aware extraction. Original PDF retained in research_papers/ "
        f"for verification.*\n\n---\n\n"
    )
    out_path.write_text(header + full_text, encoding="utf-8")
    print(f"  -> {out_path.relative_to(REPO_ROOT)} ({len(full_text):,} chars)\n")
    return out_path


def main() -> int:
    if not SRC_DIR.exists():
        print(f"No {SRC_DIR} directory found. Nothing to build.")
        return 1

    pdfs = sorted(SRC_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {SRC_DIR}.")
        return 1

    OUT_DIR.mkdir(exist_ok=True)
    print(f"Found {len(pdfs)} PDF(s) in {SRC_DIR.relative_to(REPO_ROOT)}\n")

    built = [build_one(p) for p in pdfs]

    print(f"Done. {len(built)} document(s) written to {OUT_DIR.relative_to(REPO_ROOT)}/")
    print("Restart the backend (or call ClinicalRAG.reload()) to pick these up.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
