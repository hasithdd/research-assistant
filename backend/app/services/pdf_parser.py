import time
from io import BytesIO
from pathlib import Path

import fitz
import pdfplumber
import pytesseract
from PIL import Image

from app.core.config import settings
from app.utils.logger import (
    log_operation_end,
    log_operation_start,
    log_performance,
    logger,
)


def _extract_with_pdfplumber(file_path: Path) -> str:
    """Extract text using pdfplumber page-by-page."""
    start_time = time.time()
    pages = []
    with pdfplumber.open(file_path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(text)

    result = "\n".join(pages)
    duration = (time.time() - start_time) * 1000

    log_performance(
        "_extract_with_pdfplumber",
        duration,
        success=True,
        metadata={
            "file_path": str(file_path),
            "pages": page_count,
            "text_length": len(result),
        },
    )

    return result


def extract_pages(file_path: Path) -> list[str]:
    """Extract text page-by-page using pdfplumber.

    This is a lightweight helper for higher-level LLM logic that
    needs page granularity (e.g., page-wise summaries and section
    assignment). It is intentionally simple and does not perform
    any validation beyond returning one string per page.
    """
    texts: list[str] = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                texts.append((page.extract_text() or "").strip())
        logger.info("extract_pages: extracted %d pages from %s", len(texts), file_path)
    except Exception as e:
        logger.warning("extract_pages failed for %s: %s", file_path, e)
    return texts


def _extract_with_pymupdf(file_path: Path) -> str:
    """Extract text using PyMuPDF."""
    start_time = time.time()
    doc = fitz.open(file_path)
    texts = []
    page_count = len(doc)
    for page in doc:
        texts.append(page.get_text("text") or "")

    result = "\n".join(texts)
    duration = (time.time() - start_time) * 1000

    log_performance(
        "_extract_with_pymupdf",
        duration,
        success=True,
        metadata={
            "file_path": str(file_path),
            "pages": page_count,
            "text_length": len(result),
        },
    )

    return result


def _heuristic_metadata_from_text(text: str) -> dict:
    """Extract title (first non-empty line) and authors (second)."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
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
    overall_start = time.time()
    log_operation_start(
        "extract_text_and_metadata", metadata={"file_path": str(file_path)}
    )

    t1 = _extract_with_pdfplumber(file_path)
    t2 = _extract_with_pymupdf(file_path)

    best = t1 if len(t1) > len(t2) else t2
    logger.info(
        f"Initial extraction: pdfplumber={len(t1)} chars, pymupdf={len(t2)} chars, "
        f"using={'pdfplumber' if len(t1) > len(t2) else 'pymupdf'}"
    )

    if not best.strip():
        logger.warning("No text extracted with standard methods, trying OCR")
        best = _ocr_fallback(file_path)

    heur = _heuristic_validate_structure(best)
    llm = _llm_quick_validate(best)

    combined = {k: heur[k] or llm[k] for k in heur.keys()}
    logger.info(f"Structure validation: {combined}")

    valid = sum(combined.values()) >= 3

    if not valid:
        logger.warning("Document structure invalid, trying OCR fallback")
        ocr_text = _ocr_fallback(file_path)
        heur = _heuristic_validate_structure(ocr_text)
        llm = _llm_quick_validate(ocr_text)
        combined = {k: heur[k] or llm[k] for k in heur.keys()}
        valid = sum(combined.values()) >= 3

        if not valid:
            logger.error(f"PDF structure invalid even after OCR fallback: {combined}")
            raise ValueError("PDF structure invalid even after OCR fallback")

        best = ocr_text
        logger.info("OCR fallback succeeded")

    metadata = _heuristic_metadata_from_text(best)

    overall_duration = (time.time() - overall_start) * 1000
    log_operation_end(
        "extract_text_and_metadata",
        overall_duration,
        metadata={
            "file_path": str(file_path),
            "text_length": len(best),
            "valid_sections": sum(combined.values()),
            "title": metadata.get("title", "")[:100],
        },
    )

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
    start_time = time.time()
    logger.info(f"Starting OCR fallback for {file_path}")

    doc = fitz.open(file_path)
    ocr_texts = []
    page_count = len(doc)

    for page_num, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        image = Image.open(BytesIO(img_bytes))
        text = pytesseract.image_to_string(image)
        ocr_texts.append(text)

        if page_num % 5 == 0:
            logger.info(f"OCR progress: {page_num + 1}/{page_count} pages")

    result = "\n".join(ocr_texts).strip()
    duration = (time.time() - start_time) * 1000

    log_performance(
        "_ocr_fallback",
        duration,
        success=True,
        metadata={
            "file_path": str(file_path),
            "pages": page_count,
            "text_length": len(result),
        },
    )

    logger.info(
        f"OCR completed: {page_count} pages, {len(result)} chars in {duration:.0f}ms"
    )

    return result
