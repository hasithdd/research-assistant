from app.core.config import settings
from app.utils.chunking import split_to_sections


def _call_llm_for_summary(text: str) -> str:
    """
    Placeholder stub for future LLM summarization.
    Currently returns the first 500 characters.
    """
    return text[:500].strip()


def _llm_summarize_section(sec_name: str, sec_text: str) -> str:
    """
    Summarize a section into 2–4 sentences using LLM, if available.
    """
    if not settings.OPENAI_API_KEY:
        return sec_text[:400]

    import openai

    openai.api_key = settings.OPENAI_API_KEY

    prompt = f"""
    Summarize the following section from a research paper.
    Section: {sec_name}

    Produce 2-4 precise sentences.

    Text:
    {sec_text[:6000]}
    """

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0,
        )
        return resp["choices"][0]["message"]["content"].strip()
    except Exception:
        return sec_text[:400]


def _llm_global_summary(section_summaries: dict) -> str:
    if not settings.OPENAI_API_KEY:
        combined = " ".join(section_summaries.values())
        return combined[:600]

    import openai

    openai.api_key = settings.OPENAI_API_KEY

    combined = "\n".join([f"{k}: {v}" for k, v in section_summaries.items()])

    prompt = f"""
    Based on the following section summaries from a research paper,
    produce a clear 4–6 sentence global summary.

    Section Summaries:
    {combined}
    """

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=250,
        )
        return resp["choices"][0]["message"]["content"].strip()
    except Exception:
        return combined[:600]


def _extract_first_n_sentences(text: str, n: int = 3) -> str:
    """Naive sentence splitter."""
    import re

    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:n]).strip()


def generate_structured_summary(text: str, metadata: dict) -> dict:
    sections = split_to_sections(text)

    section_summaries = {}
    for sec_name, sec_text in sections.items():
        section_summaries[sec_name] = _llm_summarize_section(sec_name, sec_text)

    global_summary = _llm_global_summary(section_summaries)

    required = {
        "title": metadata.get("title", ""),
        "authors": metadata.get("authors", ""),
        "abstract": section_summaries.get("abstract", global_summary),
        "problem_statement": section_summaries.get("introduction", global_summary),
        "methodology": section_summaries.get("method")
        or section_summaries.get("methodology")
        or "",
        "key_results": section_summaries.get("results")
        or section_summaries.get("findings")
        or "",
        "conclusion": section_summaries.get("conclusion", ""),
        "overall_summary": global_summary,
        "section_summaries": section_summaries,
    }

    return required
