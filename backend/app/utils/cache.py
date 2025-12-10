import time
from typing import Tuple


def rag_query_cache_key(paper_id: str, question: str) -> Tuple[str, str]:
    return (paper_id, question)


class TTLCache:
    def __init__(self, ttl_seconds=600):
        self.ttl = ttl_seconds
        self.store = {}

    def get(self, key):
        value = self.store.get(key)
        if not value:
            return None
        expires, data = value
        if time.time() > expires:
            del self.store[key]
            return None
        return data

    def set(self, key, value):
        self.store[key] = (time.time() + self.ttl, value)


rag_ttl_cache = TTLCache()
