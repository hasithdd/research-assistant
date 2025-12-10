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


def _heuristic_validate_structure(text: str) -> dict:
    """Return dict of detected sections."""
    lower = text.lower()

    sections = {
        "abstract": "abstract" in lower,
        "introduction": "introduction" in lower,
        "methodology": any(k in lower for k in ["methodology", "methods", "approach"]),
        "results": any(k in lower for k in ["results", "findings"]),
        "conclusion": "conclusion" in lower,
    }

    return sections


def extract_text_and_metadata(file_path: Path) -> tuple[str, dict]:
    """Main PDF extraction pipeline: try both engines, pick best, validate."""

    text1 = _extract_with_pdfplumber(file_path)
    text2 = _extract_with_pymupdf(file_path)

    best_text = text1 if len(text1) > len(text2) else text2

    if len(best_text.strip()) == 0:
        raise ValueError("Unable to extract text from PDF")

    is_valid = _heuristic_validate_structure(best_text)
    if not is_valid:
        raise ValueError("PDF structure invalid: missing scientific sections")

    metadata = _heuristic_metadata_from_text(best_text)

    return best_text, metadata
