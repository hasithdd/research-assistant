import heapq
import re

from app.core.config import settings
from app.services.file_manager import load_summary
from app.services.vectorstore import _inmem_index
from app.services.vectorstore import query as vector_query

SECTION_WEIGHTS = {
    "method": 1.2,
    "methodology": 1.2,
    "experiments": 1.2,
    "results": 1.1,
    "findings": 1.1,
    "discussion": 1.0,
    "conclusion": 1.0,
    "introduction": 1.0,
    "abstract": 0.9,
    "unknown": 1.0,
}


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


def _section_boost(section: str, question: str) -> float:
    sec = section.lower()
    w = SECTION_WEIGHTS.get(sec, 1.0)

    q = question.lower()

    if any(k in q for k in ["method", "approach", "dataset", "experiment"]) and sec in (
        "method",
        "methodology",
        "experiments",
    ):
        w += 0.25

    if any(
        k in q for k in ["result", "finding", "accuracy", "performance"]
    ) and sec in ("results", "findings"):
        w += 0.25

    return w


def answer_query(paper_id: str, question: str, top_k: int = 5) -> dict:
    vec_hits = vector_query(paper_id, question, top_k=top_k)

    kw_hits = _keyword_retrieve_by_section(paper_id, question, top_k=top_k)

    merged: dict[str, dict] = {}

    for h in vec_hits:
        text = h["text"].strip()
        merged[text] = {"text": text, "section": h["section"], "score": h["score"]}

    for h in kw_hits:
        text = h["text"].strip()
        if text in merged:
            merged[text]["score"] = max(merged[text]["score"], h["score"] + 0.01)
        else:
            merged[text] = {"text": text, "section": h["section"], "score": h["score"]}

    ranked = []
    for entry in merged.values():
        boosted = entry["score"] * _section_boost(entry["section"], question)
        ranked.append((boosted, entry))

    ranked_top = heapq.nlargest(top_k, ranked, key=lambda x: x[0])
    top_chunks = [entry for score, entry in ranked_top]

    if not top_chunks:
        return {
            "answer": "The paper does not contain relevant information.",
            "sources": [],
        }

    summary = load_summary(paper_id) or {}
    overall = summary.get("overall_summary", "")
    section_sums = summary.get("section_summaries", {})

    context_parts = []
    for i, c in enumerate(top_chunks):
        context_parts.append(f"[{i}] ({c['section']}) {c['text'][:1000]}")

    context = "\n\n".join(context_parts)

    prompt = f"""
You are a research assistant. Use ONLY the provided context and summaries.

Overall summary:
{overall}

Section summaries:
{section_sums}

Context:
{context}

Question: {question}

Answer clearly and concisely:
"""

    if settings.OPENAI_API_KEY:
        try:
            import openai

            openai.api_key = settings.OPENAI_API_KEY

            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.0,
            )
            answer = resp["choices"][0]["message"]["content"]
            return {
                "answer": answer,
                "sources": [f"{c['section']}:{i}" for i, c in enumerate(top_chunks)],
            }
        except Exception:
            pass

    combined = " ".join([c["text"][:500] for c in top_chunks])
    return {
        "answer": f"Relevant excerpts: {combined}",
        "sources": [f"{c['section']}:{i}" for i, c in enumerate(top_chunks)],
    }
