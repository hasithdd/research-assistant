import heapq
import re
import time
from typing import Any, Dict, List

from app.core.config import settings
from app.services.file_manager import load_summary
from app.services.vectorstore import _inmem_index
from app.services.vectorstore import query as vector_query
from app.utils.cache import rag_query_cache_key, rag_ttl_cache
from app.utils.llm_client import call_llm
from app.utils.logger import (
    logger,
    log_performance,
    log_operation_start,
    log_operation_end,
)

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
    overall_start = time.time()
    log_operation_start(
        "answer_query",
        metadata={
            "paper_id": paper_id,
            "question_length": len(question),
            "top_k": top_k,
        }
    )
    
    # Check cache
    cache_key = rag_query_cache_key(paper_id, question)
    cached = rag_ttl_cache.get(cache_key)
    if cached:
        duration = (time.time() - overall_start) * 1000
        logger.info(f"Cache HIT for query on paper {paper_id} ({duration:.0f}ms)")
        return cached
    
    logger.info(f"Cache MISS for query on paper {paper_id}, performing retrieval")

    # Vector retrieval
    step_start = time.time()
    vec_hits = vector_query(paper_id, question, top_k=top_k)
    vec_duration = (time.time() - step_start) * 1000
    logger.info(f"Vector search: {len(vec_hits)} hits in {vec_duration:.0f}ms")

    # Keyword retrieval
    step_start = time.time()
    kw_hits = _keyword_retrieve_by_section(paper_id, question, top_k=top_k)
    kw_duration = (time.time() - step_start) * 1000
    logger.info(f"Keyword search: {len(kw_hits)} hits in {kw_duration:.0f}ms")

    # Normalize and merge
    step_start = time.time()
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
    merge_duration = (time.time() - step_start) * 1000
    
    logger.info(
        f"Merged and ranked: {len(merged)} unique chunks -> {len(top_chunks)} final "
        f"({merge_duration:.0f}ms)"
    )

    # Load summary for use in both normal and fallback paths
    step_start = time.time()
    summary = load_summary(paper_id) or {}
    overall = summary.get("overall_summary", "")
    sec_summaries = summary.get("section_summaries", {})

    if not top_chunks:
        # Fallback: answer based purely on summaries when retrieval finds nothing.
        if not overall and not sec_summaries:
            result = {
                "answer": "No relevant information found in the document.",
                "sources": [],
            }
            logger.warning(
                f"No relevant chunks or summaries found for query on paper {paper_id}"
            )
            return result

        prompt = f"""
You are a research assistant. Use ONLY the provided summaries of the paper.

Overall summary:
{overall}

Section summaries:
{sec_summaries}

Question: {question}

Answer clearly and concisely:
"""

        messages = [{"role": "user", "content": prompt}]
        llm_start = time.time()
        answer = call_llm(messages, max_tokens=350, temperature=0.0)
        llm_duration = (time.time() - llm_start) * 1000

        logger.info(
            f"LLM summary-only answer generated in {llm_duration:.0f}ms, length: {len(answer)} chars"
        )

        result = {"answer": answer, "sources": []}

        rag_ttl_cache.set(cache_key, result)

        overall_duration = (time.time() - overall_start) * 1000
        log_operation_end(
            "answer_query",
            overall_duration,
            metadata={
                "paper_id": paper_id,
                "chunks_retrieved": 0,
                "answer_length": len(answer),
                "sources_count": 0,
            },
        )

        logger.info(
            f"RAG summary-only query completed for paper {paper_id}: 0 chunks, "
            f"{len(answer)} chars answer, total {overall_duration:.0f}ms"
        )

        return result

    # Build context-aware prompt using retrieved chunks and summaries
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

    messages = [{"role": "user", "content": prompt}]
    llm_start = time.time()
    answer = call_llm(messages, max_tokens=350, temperature=0.0)
    llm_duration = (time.time() - llm_start) * 1000
    
    logger.info(f"LLM answer generated in {llm_duration:.0f}ms, length: {len(answer)} chars")
    
    result = {
        "answer": answer,
        "sources": [f"{c['section']}:{i}" for i, c in enumerate(top_chunks)],
    }
    
    # Cache result
    rag_ttl_cache.set(cache_key, result)
    
    overall_duration = (time.time() - overall_start) * 1000
    log_operation_end(
        "answer_query",
        overall_duration,
        metadata={
            "paper_id": paper_id,
            "chunks_retrieved": len(top_chunks),
            "answer_length": len(answer),
            "sources_count": len(result["sources"]),
        }
    )
    
    logger.info(
        f"RAG query completed for paper {paper_id}: {len(top_chunks)} chunks, "
        f"{len(answer)} chars answer, total {overall_duration:.0f}ms"
    )
    
    return result
