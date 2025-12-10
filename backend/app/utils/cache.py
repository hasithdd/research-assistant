from functools import lru_cache
from typing import Tuple


@lru_cache(maxsize=256)
def rag_query_cache_key(paper_id: str, question: str) -> Tuple[str, str]:
    return (paper_id, question)
