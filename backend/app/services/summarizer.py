from app.core.config import settings


def _call_llm_for_summary(text: str) -> str:
    """
    Placeholder stub for future LLM summarization.
    Currently returns the first 500 characters.
    """
    return text[:500].strip()


def _extract_first_n_sentences(text: str, n: int = 3) -> str:
    """Naive sentence splitter."""
    import re

    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:n]).strip()


def generate_structured_summary(text: str, metadata: dict) -> dict:
    """
    Baseline summarizer: no LLM, no semantic logic.
    Extracts simple chunks from text and fills in required schema.
    """

    title = metadata.get("title", "")
    authors = metadata.get("authors", "")

    abstract = text[:800].strip()
    problem_statement = _extract_first_n_sentences(text, 2)
    methodology = text[1000:1500].strip()
    key_results = text[1500:2000].strip()
    conclusion = text[-700:].strip()

    return {
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "problem_statement": problem_statement,
        "methodology": methodology or "Not available.",
        "key_results": key_results or "Not available.",
        "conclusion": conclusion or "Not available.",
    }


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
