import re

from app.services.file_manager import load_summary
from app.services.vectorstore import _inmem_index
from app.services.vectorstore import query as vector_query


def _keyword_retrieve_by_section(
    paper_id: str, query: str, top_k: int = 5
) -> list[dict]:
    """
    Keyword retriever: returns [{"text":..., "section":..., "score":...}]
    Uses in-memory vectorstore if present, otherwise abstract summary fallback.
    """
    coll = f"paper_{paper_id}"

    if coll in _inmem_index:
        texts = _inmem_index[coll]["texts"]
        metas = _inmem_index[coll]["meta"]
    else:
        summary = load_summary(paper_id) or {}
        abstract = summary.get("abstract", "")
        if not abstract:
            return []

        texts = [p.strip() for p in abstract.split("\n\n") if len(p.strip()) > 20]
        metas = [{"section": "abstract"} for _ in texts]

    q_toks = set(re.findall(r"\w+", query.lower()))
    scored = []

    for text, meta in zip(texts, metas):
        t_toks = set(re.findall(r"\w+", text.lower()))
        overlap = len(q_toks & t_toks)
        if overlap > 0:
            scored.append((overlap, text, meta.get("section", "unknown")))

    scored.sort(key=lambda x: x[0], reverse=True)

    out = []
    for score, text, section in scored[:top_k]:
        out.append({"text": text, "section": section, "score": float(score)})

    return out


def answer_query(paper_id: str, question: str) -> dict:
    """
    Baseline RAG:
    - Retrieve top chunks via vectorstore
    - If none, try keyword fallback
    - Construct a basic answer (no LLM yet)
    """
    chunks = vector_query(paper_id, question, top_k=3)

    if not chunks:
        summary = load_summary(paper_id) or {}
        text = summary.get("abstract") or ""
        if text:
            snippet = text[:300]
            return {
                "answer": (
                    "I could not find exact matches, but here's something "
                    f"relevant: {snippet}..."
                ),
                "sources": [],
            }
        return {
            "answer": "No relevant information found in the document.",
            "sources": [],
        }

    combined = " ".join([c["text"] for c in chunks])
    snippet = combined[:500].strip()

    return {
        "answer": f"Based on the document, here's what I found: {snippet}",
        "sources": [f"chunk_{i}" for i in range(len(chunks))],
    }
