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


def _basic_chunk(text: str, chunk_size: int = 500) -> list[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
    return chunks


def ingest_document(paper_id: str, text: str):
    client = get_client()
    model = _get_model()

    chunks = _basic_chunk(text)
    embeddings = model.encode(chunks)

    collection = f"paper_{paper_id}"

    if client:
        client.recreate_collection(
            collection_name=collection,
            vectors_config={"size": len(embeddings[0]), "distance": "Cosine"},
        )

        points = []
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            points.append({"id": i, "vector": emb.tolist(), "payload": {"text": chunk}})

        client.upsert(collection_name=collection, points=points)

    else:
        global _inmem_store
        if "_inmem_store" not in globals():
            globals()["_inmem_store"] = {}
        globals()["_inmem_store"][paper_id] = {
            "chunks": chunks,
            "embeddings": embeddings,
        }
