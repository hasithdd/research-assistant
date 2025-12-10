import concurrent.futures
import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from app.utils.chunking import split_to_sections
from app.utils.llm_client import call_llm
from app.utils.logger import (
    log_operation_end,
    log_operation_start,
    log_performance,
    logger,
)


def _call_llm_for_summary(text: str) -> str:
    """
    Placeholder stub for future LLM summarization.
    Currently returns the first 500 characters.
    """
    return text[:500].strip()


_PAGE_SECTION_LABELS = [
    "title_page",
    "abstract",
    "introduction",
    "related_work",
    "background",
    "methodology",
    "experiments",
    "results",
    "discussion",
    "conclusion",
    "other",
]


def _canonical_section_label(raw: str) -> str:
    r = (raw or "").strip().lower().replace(" ", "_")
    if r in _PAGE_SECTION_LABELS:
        return r
    if r in {"methods", "materials_and_methods"}:
        return "methodology"
    if r in {"result"}:
        return "results"
    if r in {"intro"}:
        return "introduction"
    if r in {"relate_work", "related-works"}:
        return "related_work"
    if r in {"discusion"}:
        return "discussion"
    return "other"


def _llm_summarize_section(sec_name: str, sec_text: str) -> str:
    """
    Summarize a section into 2–4 sentences using LLM.
    """
    start_time = time.time()

    prompt = f"""
    Summarize the following section from a research paper.
    Section: {sec_name}

    Produce 2-4 precise sentences.

    Text:
    {sec_text[:6000]}
    """

    messages = [{"role": "user", "content": prompt}]
    result = call_llm(messages, max_tokens=250, temperature=0.0)

    duration = (time.time() - start_time) * 1000
    log_performance(
        f"summarize_section_{sec_name}",
        duration,
        success=True,
        metadata={
            "section": sec_name,
            "input_length": len(sec_text),
            "output_length": len(result),
        },
    )

    logger.info(
        f"Section '{sec_name}' summarized: {len(sec_text)} -> {len(result)} chars"
    )

    return result


def _summarize_section_wrapper(args):
    """Wrapper for parallel execution."""
    sec_name, sec_text = args
    return sec_name, _llm_summarize_section(sec_name, sec_text)


def _llm_label_page_and_summarize(page_index: int, page_text: str) -> Tuple[str, str]:
    if not page_text or not page_text.strip():
        return "other", ""

    prompt = f"""
You will label and briefly summarize a single page from a research paper.

Return ONLY valid JSON with this exact schema:
{{
  "section_label": one of [{', '.join(repr(x) for x in _PAGE_SECTION_LABELS)}],
    "summary": string
}}

The section_label should reflect what this page most likely belongs to.

Page index (0-based): {page_index}

Page text:
{page_text[:2500]}
"""

    messages = [{"role": "user", "content": prompt}]
    raw = call_llm(messages, max_tokens=220, temperature=0.0)

    try:
        start = raw.find("{")
        end = raw.rfind("}")
        raw_json = (
            raw[start : end + 1] if start != -1 and end != -1 and end > start else raw
        )
        data = json.loads(raw_json)
        label = _canonical_section_label(data.get("section_label", "other"))
        summary = str(data.get("summary", "")).strip()
        return label, summary
    except Exception as e:
        logger.warning(
            "Page labeling JSON parse failed for page %d: %s; raw=%.200s",
            page_index,
            e,
            raw,
        )
        return "other", ""


def _llm_global_summary(section_summaries: dict) -> str:
    start_time = time.time()

    combined = "\n".join([f"{k}: {v}" for k, v in section_summaries.items()])

    prompt = f"""
    Based on the following section summaries from a research paper,
    produce a clear 4–6 sentence global summary.

    Section Summaries:
    {combined}
    """

    messages = [{"role": "user", "content": prompt}]
    result = call_llm(messages, max_tokens=250, temperature=0.0)

    duration = (time.time() - start_time) * 1000
    log_performance(
        "global_summary",
        duration,
        success=True,
        metadata={
            "sections_count": len(section_summaries),
            "output_length": len(result),
        },
    )

    return result


def _extract_first_n_sentences(text: str, n: int = 3) -> str:
    """Naive sentence splitter."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:n]).strip()


_BAD_FIELD_PATTERNS = [
    "you are a research assistant",
    "you are an ai",
    "as an ai language model",
    "as a language model",
    "summarize the following",
    "use only the provided context",
    "no response available from the language model",
    "no relevant information found in the document",
]


def _looks_like_meta_or_placeholder(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    for pat in _BAD_FIELD_PATTERNS:
        if pat in lowered:
            return True
    if lowered.startswith("you are "):
        return True
    return False


def _clean_string_field(value: Any) -> str:
    """Clean a candidate string field and drop obvious meta/prompt text."""
    if not isinstance(value, str):
        return value
    cleaned = value.strip()
    if not cleaned:
        return ""
    if _looks_like_meta_or_placeholder(cleaned):
        return ""
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _flatten_entities_for_logging(entities: Dict[str, list] | None) -> str:
    if not entities:
        return ""
    parts: list[str] = []
    for k, v in entities.items():
        if not isinstance(v, list):
            continue
        if not v:
            continue
        joined = ", ".join(str(x) for x in v if str(x).strip())
        if joined:
            parts.append(f"{k}: {joined}")
    return " | ".join(parts)


def _llm_extract_section_entities(
    sec_name: str, sec_summary: str
) -> Dict[str, List[str]]:
    if not sec_summary or not sec_summary.strip():
        return {}

    prompt = f"""
You are extracting key technical entities from a research paper section summary.

Section name: {sec_name}

Given the section summary below, identify the most important items and
return ONLY valid JSON with this exact schema:
{{
  "methods": string[],
  "models": string[],
  "datasets": string[],
  "metrics": string[],
  "tasks": string[],
  "domains": string[],
  "other_terms": string[]
}}

Rules:
- Use short noun phrases (e.g. "convolutional neural network", "ImageNet").
- If a category has no clear items, use an empty list [].
- Do NOT include explanations, comments, markdown, or backticks.

Section summary:
{sec_summary[:2000]}
"""

    messages = [{"role": "user", "content": prompt}]
    raw = call_llm(messages, max_tokens=300, temperature=0.0)

    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw_json = raw[start : end + 1]
        else:
            raw_json = raw

        data = json.loads(raw_json)
        if not isinstance(data, dict):
            return {}

        # Normalise to expected shape with list values only.
        fields = [
            "methods",
            "models",
            "datasets",
            "metrics",
            "tasks",
            "domains",
            "other_terms",
        ]
        out: Dict[str, List[str]] = {}
        for f in fields:
            val = data.get(f, [])
            if isinstance(val, list):
                cleaned_list = [
                    str(x).strip()
                    for x in val
                    if isinstance(x, (str, int, float)) and str(x).strip()
                ]
                out[f] = cleaned_list
            elif isinstance(val, (str, int, float)) and str(val).strip():
                out[f] = [str(val).strip()]
            else:
                out[f] = []

        logger.info(
            "Entities extracted for section '%s': %s",
            sec_name,
            _flatten_entities_for_logging(out),
        )
        return out
    except Exception as e:
        logger.warning(
            "Entity extraction JSON parse failed for section '%s': %s; raw=%.200s",
            sec_name,
            e,
            raw,
        )
        return {}


def _llm_structured_summary(
    section_summaries: dict, global_summary: str, metadata: dict
) -> dict:
    prompt = f"""
You are an expert research assistant. Using ONLY the provided section summaries
and global summary of a research paper, produce a concise structured summary.

Return ONLY valid JSON with this exact schema:
{{
  "title": string,
  "authors": string | string[],
  "abstract": string,
  "problem_statement": string,
  "methodology": string,
  "key_results": string,
  "conclusion": string
}}

Rules:
- Use 1–3 sentences per field.
- If information is not available, use an empty string "".
- Do NOT include any explanation, comments, markdown, or backticks.
- Do NOT include keys other than the ones specified.

Metadata (may be noisy, use only if helpful):
{json.dumps({
    "title": metadata.get("title", ""),
    "authors": metadata.get("authors", ""),
})}

Section summaries:
{json.dumps(section_summaries)[:6000]}

Global summary:
{global_summary[:2000]}
"""

    messages = [{"role": "user", "content": prompt}]
    raw = call_llm(messages, max_tokens=400, temperature=0.0)

    # Try to robustly extract JSON from the response.
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw_json = raw[start : end + 1]
        else:
            raw_json = raw

        data = json.loads(raw_json)
        if isinstance(data, dict):
            return data
    except Exception as e:
        logger.warning(f"Structured summary JSON parse failed: {e}; raw=\n{raw[:300]}")

    return {}


def _llm_validate_structured_summary(
    section_summaries: dict,
    global_summary: str,
    metadata: dict,
    candidate: dict,
) -> dict:
    safe_sections = json.dumps(section_summaries)[:4000]
    safe_global = global_summary[:1500]
    safe_meta = json.dumps(
        {
            "title": metadata.get("title", "")[:200],
            "authors": metadata.get("authors", ""),
        }
    )

    prompt = f"""
You are validating a structured summary of a research paper.

Your task:
- For each field, ensure it contains only factual information about the paper.
- Remove or fix any meta text, prompts, or placeholders like
  "No response available from the language model." or "Summarize the following".
- Use the section summaries and global summary as your only source of truth.

Return ONLY valid JSON with this exact schema:
{{
  "title": string,
  "authors": string | string[],
  "abstract": string,
  "problem_statement": string,
  "methodology": string,
  "key_results": string,
  "conclusion": string
}}

Rules:
- If you cannot infer a field from the summaries, use an empty string "".
- Do NOT invent specific author names, numbers, or results not supported by the summaries.
- Use at most 1–2 sentences per non-empty field.
- Do NOT include any explanation, comments, markdown, or backticks.

Metadata (may be noisy, use only if helpful):
{safe_meta}

Section summaries:
{safe_sections}

Global summary:
{safe_global}

Current structured summary candidate:
{json.dumps(candidate)}
"""

    messages = [{"role": "user", "content": prompt}]
    raw = call_llm(messages, max_tokens=400, temperature=0.0)

    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            raw_json = raw[start : end + 1]
        else:
            raw_json = raw

        data = json.loads(raw_json)
        if isinstance(data, dict):
            return data
    except Exception as e:
        logger.warning(
            f"Structured summary validation JSON parse failed: {e}; raw=\n{raw[:300]}"
        )

    return {}


def _sections_from_pages(
    page_texts: List[str],
) -> Tuple[Dict[str, str], Dict[int, Dict[str, str]]]:
    sections: Dict[str, List[str]] = {}
    page_summaries: Dict[int, Dict[str, str]] = {}

    for idx, text in enumerate(page_texts):
        label, summary = _llm_label_page_and_summarize(idx, text)
        page_summaries[idx] = {"section_label": label, "summary": summary}
        sections.setdefault(label, []).append(text)

    merged_sections: Dict[str, str] = {
        name: "\n\n".join(parts).strip() for name, parts in sections.items() if parts
    }

    logger.info(
        "Page-based sections built: %s",
        {k: len(v.splitlines()) for k, v in merged_sections.items()},
    )

    return merged_sections, page_summaries


def generate_structured_summary(
    text: str,
    metadata: dict,
    page_texts: Optional[List[str]] = None,
) -> dict:
    overall_start = time.time()
    log_operation_start(
        "generate_structured_summary",
        metadata={
            "text_length": len(text),
            "title": metadata.get("title", "")[:100],
        },
    )

    step_start = time.time()
    sections: Dict[str, str] = {}
    page_summaries: Dict[int, Dict[str, str]] = {}
    if page_texts:
        try:
            sections, page_summaries = _sections_from_pages(page_texts)
        except Exception as e:
            logger.warning(
                "Falling back to heading-based sections due to page error: %s", e
            )
            sections = split_to_sections(text)
    else:
        sections = split_to_sections(text)
    step_duration = (time.time() - step_start) * 1000
    logger.info(f"Document split into {len(sections)} sections ({step_duration:.0f}ms)")

    parallel_start = time.time()
    section_summaries = {}

    max_workers = min(4, len(sections))
    logger.info(f"Starting parallel summarization with {max_workers} workers")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_section = {
            executor.submit(_llm_summarize_section, sec_name, sec_text): sec_name
            for sec_name, sec_text in sections.items()
        }

        for future in concurrent.futures.as_completed(future_to_section):
            sec_name = future_to_section[future]
            try:
                result = future.result()
                section_summaries[sec_name] = result
            except Exception as e:
                logger.error(f"Section summarization failed for '{sec_name}': {e}")
                section_summaries[sec_name] = ""

    parallel_duration = (time.time() - parallel_start) * 1000
    log_performance(
        "parallel_section_summarization",
        parallel_duration,
        success=True,
        metadata={
            "sections_count": len(sections),
            "workers": max_workers,
        },
    )
    logger.info(
        "Parallel summarization completed in %sms for %s sections",
        f"{parallel_duration:.0f}",
        len(sections),
    )

    global_summary = _llm_global_summary(section_summaries)

    section_entities: Dict[str, Dict[str, List[str]]] = {}
    for sec_name, sec_summary in section_summaries.items():
        try:
            ents = _llm_extract_section_entities(sec_name, sec_summary)
            if ents:
                section_entities[sec_name] = ents
        except Exception as e:
            logger.warning("Entity extraction failed for section '%s': %s", sec_name, e)

    llm_structured_raw = _llm_structured_summary(
        section_summaries, global_summary, metadata
    )

    title = _clean_string_field(llm_structured_raw.get("title")) or metadata.get(
        "title", ""
    )

    authors_val = llm_structured_raw.get("authors") or metadata.get("authors", "")
    authors: Any
    if isinstance(authors_val, list):
        authors = [
            _clean_string_field(a)
            for a in authors_val
            if isinstance(a, str) and _clean_string_field(a)
        ]
    else:
        authors = _clean_string_field(authors_val)

    abstract = _clean_string_field(llm_structured_raw.get("abstract", ""))
    if not abstract:
        abstract = metadata.get("abstract") or _extract_first_n_sentences(
            section_summaries.get("abstract", global_summary), 3
        )

    problem_statement = _clean_string_field(
        llm_structured_raw.get("problem_statement", "")
    )
    if not problem_statement:
        problem_statement = metadata.get(
            "problem_statement"
        ) or _extract_first_n_sentences(
            section_summaries.get("introduction", global_summary), 3
        )

    methodology = _clean_string_field(llm_structured_raw.get("methodology", ""))
    if not methodology:
        methodology = (
            metadata.get("methodology")
            or metadata.get("methods")
            or _extract_first_n_sentences(
                section_summaries.get("method")
                or section_summaries.get("methodology")
                or global_summary,
                3,
            )
        )

    key_results = _clean_string_field(llm_structured_raw.get("key_results", ""))
    if not key_results:
        key_results = metadata.get("key_results") or _extract_first_n_sentences(
            section_summaries.get("results")
            or section_summaries.get("findings")
            or global_summary,
            3,
        )

    conclusion = _clean_string_field(llm_structured_raw.get("conclusion", ""))
    if not conclusion:
        conclusion = metadata.get("conclusion") or _extract_first_n_sentences(
            section_summaries.get("conclusion", global_summary), 3
        )

    required = {
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "problem_statement": problem_statement,
        "methodology": methodology,
        "key_results": key_results,
        "conclusion": conclusion,
        "overall_summary": global_summary,
        "section_summaries": section_summaries,
        "section_entities": section_entities,
    }

    candidate_for_validation = {
        k: required[k]
        for k in [
            "title",
            "authors",
            "abstract",
            "problem_statement",
            "methodology",
            "key_results",
            "conclusion",
        ]
    }

    validated = _llm_validate_structured_summary(
        section_summaries=section_summaries,
        global_summary=global_summary,
        metadata=metadata,
        candidate=candidate_for_validation,
    )

    if validated:
        for key in candidate_for_validation.keys():
            if key not in validated:
                continue
            val = validated[key]
            if isinstance(val, str):
                val = _clean_string_field(val)
            if key == "authors" and isinstance(val, list):
                val = [
                    _clean_string_field(a)
                    for a in val
                    if isinstance(a, str) and _clean_string_field(a)
                ]
            if val:
                required[key] = val

    overall_duration = (time.time() - overall_start) * 1000
    log_operation_end(
        "generate_structured_summary",
        overall_duration,
        metadata={
            "text_length": len(text),
            "sections_count": len(sections),
            "summary_fields": len(required),
        },
    )

    logger.info(
        f"Structured summary generated: {len(sections)} sections, "
        f"{len(global_summary)} chars global summary"
    )

    if page_summaries:
        required["page_summaries"] = page_summaries

    return required
