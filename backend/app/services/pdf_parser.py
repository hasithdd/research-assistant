from pathlib import Path

import fitz
import pdfplumber


def _extract_with_pdfplumber(file_path: Path) -> str:
    """Extract text using pdfplumber page-by-page."""
    pages = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(text)
    return "\n".join(pages)


def _extract_with_pymupdf(file_path: Path) -> str:
    """Extract text using PyMuPDF."""
    doc = fitz.open(file_path)
    texts = []
    for page in doc:
        texts.append(page.get_text("text") or "")
    return "\n".join(texts)


def _heuristic_metadata_from_text(text: str) -> dict:
    """Guess title and authors from the first lines of the PDF."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    title = lines[0] if len(lines) > 0 else ""
    authors = lines[1] if len(lines) > 1 else ""

    return {"title": title, "authors": authors}
