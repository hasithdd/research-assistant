from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.utils.chunking import section_aware_chunks, split_to_sections

_model: Optional[SentenceTransformer] = None
_client: Optional[QdrantClient] = None

_inmem_index: Dict[str, Dict[str, Any]] = {}


def _collection_name(paper_id: str) -> str:
    return f"paper_{paper_id}"


def _get_model() -> SentenceTransformer:
    """Load embedding model lazily."""
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    return _model


def _get_client() -> Optional[QdrantClient]:
    """Return Qdrant client if available; otherwise None."""
    global _client
    if _client is None:
        try:
            _client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
            )
        except Exception:
            _client = None
    return _client


def ingest_document(
    paper_id: str,
    text: str,
    sections: Optional[Dict[str, str]] = None,
) -> None:
    """
    Ingest chunks with section metadata.
    - Splits text into sections
    - Creates chunks per section
    - Embeds chunks
    - Stores in Qdrant or in-memory fallback
    """

    client = _get_client()
    model = _get_model()

    if sections is None:
        sections = split_to_sections(text)

    sec_chunks = section_aware_chunks(sections)
    texts = [c["text"] for c in sec_chunks]
    metas = [
        {"section": c["section"], "paper_id": paper_id, "length": len(c["text"])}
        for c in sec_chunks
    ]

    embeddings = model.encode(texts, show_progress_bar=False)
    emb_dim = int(embeddings.shape[1])

    coll = _collection_name(paper_id)

    if client:
        try:
            client.recreate_collection(
                collection_name=coll,
                vectors_config=rest.VectorParams(
                    size=emb_dim,
                    distance=rest.Distance.COSINE,
                ),
            )

            points = []
            for idx, (vec, txt, meta) in enumerate(zip(embeddings, texts, metas)):
                payload = {"text": txt, **meta}
                points.append(
                    rest.PointStruct(
                        id=idx,
                        vector=vec.tolist(),
                        payload=payload,
                    )
                )

            client.upsert(collection_name=coll, points=points)
            return

        except Exception:
            pass

    _inmem_index[coll] = {
        "embs": np.array(embeddings),
        "texts": texts,
        "meta": metas,
    }


def query(paper_id: str, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Section-aware semantic search.
    Returns list of:
        {
            "text": str,
            "section": str,
            "score": float
        }
    """

    client = _get_client()
    model = _get_model()
    coll = _collection_name(paper_id)

    q_emb = model.encode([query_text])[0]

    if client:
        try:
            results = client.search(
                collection_name=coll,
                query_vector=q_emb.tolist(),
                limit=top_k,
            )
            out = []
            for hit in results:
                payload = hit.payload or {}
                out.append(
                    {
                        "text": payload.get("text", ""),
                        "section": payload.get("section", "unknown"),
                        "score": float(getattr(hit, "score", 1.0)),
                    }
                )
            return out
        except Exception:
            pass

    if coll not in _inmem_index:
        return []

    idx_data = _inmem_index[coll]
    embs = idx_data["embs"]
    texts = idx_data["texts"]
    metas = idx_data["meta"]

    q_norm = q_emb / np.linalg.norm(q_emb)
    emb_norm = embs / np.linalg.norm(embs, axis=1, keepdims=True)

    sims = emb_norm @ q_norm
    top_idx = sims.argsort()[::-1][:top_k]

    results = []
    for i in top_idx:
        meta = metas[i]
        results.append(
            {
                "text": texts[i],
                "section": meta.get("section", "unknown"),
                "score": float(sims[i]),
            }
        )

    return results
