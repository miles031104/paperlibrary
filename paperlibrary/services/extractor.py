from pathlib import Path

import fitz  # PyMuPDF


def extract_text(
    pdf_path: Path | str,
    max_pages: int = 6,
    max_chars: int = 6000,
) -> str:
    doc = fitz.open(str(pdf_path))
    pages_to_read = min(max_pages, len(doc))

    raw = ""
    for i in range(pages_to_read):
        raw += doc[i].get_text()
    doc.close()

    if not raw.strip():
        return ""

    # Move abstract section to front so LLM sees it first
    lower = raw.lower()
    idx = lower.find("abstract")
    if idx > 0:
        raw = raw[idx:] + "\n" + raw[:idx]

    return raw[:max_chars]
