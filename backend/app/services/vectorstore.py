from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

_model = None
_client = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model


def get_client() -> QdrantClient | None:
    global _client
    if _client is None:
        try:
            _client = QdrantClient(url="http://localhost:6333")
        except Exception:
            _client = None
    return _client
