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
