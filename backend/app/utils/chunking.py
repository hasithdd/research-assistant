SECTION_HEADERS = [
    r"abstract",
    r"introduction",
    r"related work",
    r"background",
    r"method",
    r"methodology",
    r"approach",
    r"materials and methods",
    r"experiments",
    r"results",
    r"findings",
    r"discussion",
    r"conclusion",
]


def split_to_sections(text: str) -> dict:
    """
    Splits PDF text into named sections based on common academic headings.
    Returns dict: {section_name: section_text}
    """

    lines = text.splitlines()
    sections: dict[str, list[str]] = {}
    current_section = "unknown"
    sections[current_section] = []

    for line in lines:
        lower = line.lower().strip()
        matches = [h for h in SECTION_HEADERS if lower.startswith(h)]
        if matches:
            current_section = matches[0]
            sections[current_section] = []
        sections[current_section].append(line)

    return {
        sec: "\n".join(content).strip() for sec, content in sections.items() if content
    }


def chunk_text_semantic(text: str, chunk_size: int = 500, overlap: int = 100):
    """Simple semantic-like chunker based on sentence boundaries."""
    import re

    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunks = []
    cur = []
    cur_len = 0

    for s in sentences:
        words = s.split()
        cur.append(s)
        cur_len += len(words)

        if cur_len >= chunk_size:
            chunks.append(" ".join(cur))
            cur = cur[-(overlap // 10) :]
            cur_len = sum(len(x.split()) for x in cur)

    if cur:
        chunks.append(" ".join(cur))

    return chunks


def section_aware_chunks(sections: dict, chunk_size=500, overlap=100):
    result = []
    for sec_name, sec_text in sections.items():
        chunks = chunk_text_semantic(sec_text, chunk_size, overlap)
        for c in chunks:
            result.append({"section": sec_name, "text": c})
    return result
