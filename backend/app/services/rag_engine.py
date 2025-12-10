import heapq
import re
from typing import Any, Dict, List

from app.core.config import settings
from app.services.file_manager import load_summary
from app.services.vectorstore import _inmem_index
from app.services.vectorstore import query as vector_query
from app.utils.cache import rag_query_cache_key, rag_ttl_cache

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


def _normalize_scores(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize score values into 0–1 range for stable ranking."""
    if not entries:
        return entries

    scores = [e["score"] for e in entries]
    min_s, max_s = min(scores), max(scores)

    if max_s == min_s:
        for e in entries:
            e["score"] = 1.0
        return entries

    for e in entries:
        e["score"] = (e["score"] - min_s) / (max_s - min_s)

    return entries


def _compress_text(text: str, max_chars: int = 600) -> str:
    """
    Compress context text while keeping the beginning and end.
    """
    if len(text) <= max_chars:
        return text

    half = max_chars // 2
    return text[:half] + "\n...\n" + text[-half:]


def _keyword_retrieve_by_section(
    paper_id: str, query: str, top_k: int = 5
) -> List[Dict[str, Any]]:
    coll = f"paper_{paper_id}"

    if coll in _inmem_index:
        texts = _inmem_index[coll]["texts"]
        metas = _inmem_index[coll]["meta"]
    else:
        summary = load_summary(paper_id) or {}
        abstract = summary.get("abstract", "")
        if not abstract.strip():
            return []

        texts = [p.strip() for p in abstract.split("\n\n") if len(p.strip()) > 20]
        metas = [{"section": "abstract"} for _ in texts]

    q_tokens = set(re.findall(r"\w+", query.lower()))
    scored = []

    for txt, meta in zip(texts, metas):
        t_tokens = set(re.findall(r"\w+", txt.lower()))
        overlap = len(q_tokens & t_tokens)
        if overlap > 0:
            scored.append((overlap, txt, meta.get("section", "unknown")))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        {"text": text, "section": section, "score": float(score)}
        for score, text, section in scored[:top_k]
    ]


def _section_boost(section: str, question: str) -> float:
    sec = section.lower()
    weight = SECTION_WEIGHTS.get(sec, 1.0)
    q = question.lower()

    if any(w in q for w in ["method", "approach", "dataset", "experiment"]):
        if sec in ("method", "methodology", "experiments"):
            weight += 0.25

    if any(w in q for w in ["result", "finding", "accuracy", "performance"]):
        if sec in ("results", "findings"):
            weight += 0.25

    return weight


def answer_query(paper_id: str, question: str, top_k: int = 5) -> Dict[str, Any]:
    cache_key = rag_query_cache_key(paper_id, question)
    cached = rag_ttl_cache.get(cache_key)
    if cached:
        return cached

    vec_hits = vector_query(paper_id, question, top_k=top_k)
    kw_hits = _keyword_retrieve_by_section(paper_id, question, top_k=top_k)

    vec_hits = _normalize_scores(vec_hits)
    kw_hits = _normalize_scores(kw_hits)

    merged: Dict[str, Dict[str, Any]] = {}

    for hit in vec_hits:
        t = hit["text"].strip()
        merged[t] = {
            "text": t,
            "section": hit.get("section", "unknown"),
            "score": float(hit.get("score", 1.0)),
        }

    for hit in kw_hits:
        t = hit["text"].strip()
        if t in merged:
            merged[t]["score"] = max(merged[t]["score"], hit["score"] + 0.01)
        else:
            merged[t] = {
                "text": t,
                "section": hit.get("section", "unknown"),
                "score": float(hit["score"]),
            }

    ranked = []
    for entry in merged.values():
        boosted = entry["score"] * _section_boost(entry["section"], question)
        ranked.append((boosted, entry))

    top_ranked = heapq.nlargest(top_k, ranked, key=lambda x: x[0])
    top_chunks = [entry for score, entry in top_ranked]

    if not top_chunks:
        result = {
            "answer": "No relevant information found in the document.",
            "sources": [],
        }
        return result

    summary = load_summary(paper_id) or {}
    overall = summary.get("overall_summary", "")
    sec_summaries = summary.get("section_summaries", {})

    context_parts = [
        f"[{i}] ({c['section']}) {_compress_text(c['text'], 1000)}"
        for i, c in enumerate(top_chunks)
    ]
    context = "\n\n".join(context_parts)

    prompt = f"""
You are a research assistant. Use ONLY the provided context and summaries.

Overall summary:
{overall}

Section summaries:
{sec_summaries}

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
                max_tokens=350,
                temperature=0.0,
            )
            answer = resp["choices"][0]["message"]["content"].strip()
            result = {
                "answer": answer,
                "sources": [f"{c['section']}:{i}" for i, c in enumerate(top_chunks)],
            }
            return result
        except Exception:
            pass

    combined = " ".join([c["text"][:500] for c in top_chunks])
    result = {
        "answer": f"Relevant excerpts: {combined}",
        "sources": [f"{c['section']}:{i}" for i, c in enumerate(top_chunks)],
    }

    rag_ttl_cache.set(cache_key, result)
    return result
