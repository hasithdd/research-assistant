from io import BytesIO
from pathlib import Path

import fitz
import pdfplumber
import pytesseract
from PIL import Image

from app.core.config import settings


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
    """Extract title (first non-empty line) and authors (second)."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    title = lines[0] if lines else ""
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
    """
    Full extraction pipeline:
    - Try pdfplumber + pymupdf
    - Validate structure
    - If invalid → OCR fallback → LLM validate
    """

    t1 = _extract_with_pdfplumber(file_path)
    t2 = _extract_with_pymupdf(file_path)

    best = t1 if len(t1) > len(t2) else t2

    if not best.strip():
        best = _ocr_fallback(file_path)

    heur = _heuristic_validate_structure(best)
    llm = _llm_quick_validate(best)

    combined = {k: heur[k] or llm[k] for k in heur.keys()}

    valid = sum(combined.values()) >= 3

    if not valid:
        ocr_text = _ocr_fallback(file_path)
        heur = _heuristic_validate_structure(ocr_text)
        llm = _llm_quick_validate(ocr_text)
        combined = {k: heur[k] or llm[k] for k in heur.keys()}
        valid = sum(combined.values()) >= 3

        if not valid:
            raise ValueError("PDF structure invalid even after OCR fallback")

        best = ocr_text

    metadata = _heuristic_metadata_from_text(best)
    return best, metadata


def _llm_quick_validate(text: str) -> dict:
    """
    Ask a small LLM to check whether the required academic sections are present.
    Returns the same dict schema as heuristic validation.
    If no OPENAI_API_KEY configured, fallback to heuristic only.
    """
    if not settings.OPENAI_API_KEY:
        return _heuristic_validate_structure(text)

    import openai

    openai.api_key = settings.OPENAI_API_KEY

    prompt = (
        """
    Analyze the following research paper text and determine which sections exist.
    Return ONLY valid JSON with keys:
    abstract, introduction, methodology, results, conclusion
    Each value MUST be true or false.

    Text:
    """
        + text[:8000]
        + """
    """
    )

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=100,
        )
        j = resp["choices"][0]["message"]["content"]
        import json

        return json.loads(j)
    except Exception:
        return _heuristic_validate_structure(text)


def _ocr_fallback(file_path: Path) -> str:
    """Convert pages to images and OCR them."""
    doc = fitz.open(file_path)
    ocr_texts = []

    for page in doc:
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        image = Image.open(BytesIO(img_bytes))
        text = pytesseract.image_to_string(image)
        ocr_texts.append(text)

    return "\n".join(ocr_texts).strip()
