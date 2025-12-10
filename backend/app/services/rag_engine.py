import re

from app.services.file_manager import load_summary
from app.services.vectorstore import query as vector_query


def _keyword_score(text: str, query: str) -> int:
    q_tokens = set(re.findall(r"\w+", query.lower()))
    t_tokens = set(re.findall(r"\w+", text.lower()))
    return len(q_tokens.intersection(t_tokens))


def _keyword_retrieve(chunks: list[str], query: str, top_k: int = 3) -> list[str]:
    scored = []
    for c in chunks:
        score = _keyword_score(c, query)
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


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
            return {
                "answer": f"I could not find exact matches, but here's something relevant: {text[:300]}...",
                "sources": [],
            }
        return {
            "answer": "No relevant information found in the document.",
            "sources": [],
        }

    combined = " ".join(chunks)
    snippet = combined[:500].strip()

    return {
        "answer": f"Based on the document, here's what I found: {snippet}",
        "sources": [f"chunk_{i}" for i in range(len(chunks))],
    }
