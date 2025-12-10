import re


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
