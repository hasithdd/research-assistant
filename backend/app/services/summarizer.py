import time
import concurrent.futures
import json
import re
from app.core.config import settings
from app.utils.chunking import split_to_sections
from app.utils.llm_client import call_llm
from app.utils.logger import (
    logger,
    log_performance,
    log_operation_start,
    log_operation_end,
)


def _call_llm_for_summary(text: str) -> str:
    """
    Placeholder stub for future LLM summarization.
    Currently returns the first 500 characters.
    """
    return text[:500].strip()


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
        }
    )
    
    logger.info(f"Section '{sec_name}' summarized: {len(sec_text)} -> {len(result)} chars")
    
    return result


def _summarize_section_wrapper(args):
    """Wrapper for parallel execution."""
    sec_name, sec_text = args
    return sec_name, _llm_summarize_section(sec_name, sec_text)


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
        }
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


def _clean_string_field(value: str) -> str:
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


def _llm_structured_summary(section_summaries: dict, global_summary: str, metadata: dict) -> dict:
    """Use the LLM once to produce a structured JSON summary.

    The model sees the section-level summaries and global summary and must
    return ONLY JSON with the fields we care about.
    """
    # Keep prompt compact: we pass summaries, not the full paper text.
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
{json.dumps({"title": metadata.get("title", ""), "authors": metadata.get("authors", "")})}

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
    """Ask the LLM to validate and clean a structured summary.

    The model receives the current candidate fields plus section/global summaries and
    must return ONLY JSON with the same schema, with obvious prompt/meta/placeholder
    content removed or replaced with concise factual text.
    """

    # Avoid sending huge payloads
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
        logger.warning(f"Structured summary validation JSON parse failed: {e}; raw=\n{raw[:300]}")

    return {}


def generate_structured_summary(text: str, metadata: dict) -> dict:
    overall_start = time.time()
    log_operation_start(
        "generate_structured_summary",
        metadata={
            "text_length": len(text),
            "title": metadata.get("title", "")[:100],
        }
    )
    
    # Split into sections
    step_start = time.time()
    sections = split_to_sections(text)
    step_duration = (time.time() - step_start) * 1000
    logger.info(f"Document split into {len(sections)} sections ({step_duration:.0f}ms)")

    # Summarize sections in parallel (up to 4 workers to avoid rate limits)
    parallel_start = time.time()
    section_summaries = {}
    
    # Use ThreadPoolExecutor for parallel LLM calls
    max_workers = min(4, len(sections))  # Limit to 4 to avoid overwhelming the LLM
    logger.info(f"Starting parallel summarization with {max_workers} workers")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all section summarization tasks
        future_to_section = {
            executor.submit(_llm_summarize_section, sec_name, sec_text): sec_name
            for sec_name, sec_text in sections.items()
        }
        
        # Collect results as they complete
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
        }
    )
    logger.info(f"Parallel summarization completed in {parallel_duration:.0f}ms for {len(sections)} sections")

    # Generate global summary
    global_summary = _llm_global_summary(section_summaries)

    # Ask the LLM once for a clean, semantic structured summary.
    llm_structured_raw = _llm_structured_summary(section_summaries, global_summary, metadata)

    # Prefer LLM-structured values, but fall back to metadata / section
    # snippets when needed. Clean obvious prompt/meta text locally first.
    title = _clean_string_field(llm_structured_raw.get("title")) or metadata.get("title", "")

    authors_val = llm_structured_raw.get("authors") or metadata.get("authors", "")
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

    problem_statement = _clean_string_field(llm_structured_raw.get("problem_statement", ""))
    if not problem_statement:
        problem_statement = metadata.get("problem_statement") or _extract_first_n_sentences(
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
    }

    # Second pass: LLM-based validation/cleanup of the semantic fields.
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
        }
    )
    
    logger.info(
        f"Structured summary generated: {len(sections)} sections, "
        f"{len(global_summary)} chars global summary"
    )

    return required
