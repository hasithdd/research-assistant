from __future__ import annotations

from typing import Any, Dict, List, Optional
import time

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.utils.chunking import section_aware_chunks, split_to_sections
from app.utils.logger import (
    logger,
    log_performance,
    log_db_operation,
    log_operation_start,
    log_operation_end,
    log_error_with_trace,
)

_model: Optional[SentenceTransformer] = None
_client: Optional[QdrantClient] = None

_inmem_index: Dict[str, Dict[str, Any]] = {}


def _collection_name(paper_id: str) -> str:
    return f"paper_{paper_id}"


def _get_model() -> SentenceTransformer:
    """Load embedding model lazily."""
    global _model
    if _model is None:
        start_time = time.time()
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME}")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        duration = (time.time() - start_time) * 1000
        log_performance(
            "load_embedding_model",
            duration,
            success=True,
            metadata={"model_name": settings.EMBEDDING_MODEL_NAME}
        )
        logger.info(f"Embedding model loaded in {duration:.0f}ms")
    return _model


def _get_client() -> Optional[QdrantClient]:
    """Return Qdrant client if available; otherwise None."""
    global _client
    if _client is None:
        try:
            start_time = time.time()
            logger.info(f"Connecting to Qdrant at {settings.QDRANT_URL}")
            _client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
            )
            duration = (time.time() - start_time) * 1000
            logger.info(f"Qdrant client connected in {duration:.0f}ms")
        except Exception as e:
            logger.warning(f"Failed to connect to Qdrant: {e}, using in-memory fallback")
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
    overall_start = time.time()
    log_operation_start(
        "ingest_document",
        metadata={"paper_id": paper_id, "text_length": len(text)}
    )

    client = _get_client()
    model = _get_model()

    # Split into sections
    step_start = time.time()
    if sections is None:
        sections = split_to_sections(text)
    sec_chunks = section_aware_chunks(sections)
    step_duration = (time.time() - step_start) * 1000
    
    logger.info(
        f"Document chunking for {paper_id}: {len(sec_chunks)} chunks "
        f"from {len(sections)} sections ({step_duration:.0f}ms)"
    )

    texts = [c["text"] for c in sec_chunks]
    metas = [
        {"section": c["section"], "paper_id": paper_id, "length": len(c["text"])}
        for c in sec_chunks
    ]

    # Generate embeddings
    step_start = time.time()
    embeddings = model.encode(texts, show_progress_bar=False)
    emb_dim = int(embeddings.shape[1])
    step_duration = (time.time() - step_start) * 1000
    
    log_performance(
        "generate_embeddings",
        step_duration,
        success=True,
        metadata={
            "paper_id": paper_id,
            "chunk_count": len(texts),
            "embedding_dim": emb_dim,
        }
    )

    coll = _collection_name(paper_id)

    # Store in Qdrant if available
    if client:
        try:
            step_start = time.time()
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
            step_duration = (time.time() - step_start) * 1000
            
            log_db_operation(
                "upsert",
                coll,
                record_count=len(points),
                duration_ms=step_duration,
                success=True
            )
            
            overall_duration = (time.time() - overall_start) * 1000
            log_operation_end(
                "ingest_document",
                overall_duration,
                metadata={"paper_id": paper_id, "chunks": len(texts), "storage": "qdrant"}
            )
            
            return

        except Exception as e:
            log_error_with_trace(
                "qdrant_upsert",
                e,
                metadata={"paper_id": paper_id, "collection": coll}
            )
            logger.warning(f"Qdrant upsert failed, falling back to in-memory: {e}")

    # Fallback to in-memory storage
    _inmem_index[coll] = {
        "embs": np.array(embeddings),
        "texts": texts,
        "meta": metas,
    }
    
    log_db_operation(
        "store_inmemory",
        coll,
        record_count=len(texts),
        success=True
    )
    
    overall_duration = (time.time() - overall_start) * 1000
    log_operation_end(
        "ingest_document",
        overall_duration,
        metadata={"paper_id": paper_id, "chunks": len(texts), "storage": "in-memory"}
    )


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
    start_time = time.time()
    log_operation_start(
        "vectorstore_query",
        metadata={"paper_id": paper_id, "query_length": len(query_text), "top_k": top_k}
    )

    client = _get_client()
    model = _get_model()
    coll = _collection_name(paper_id)

    # Generate query embedding
    emb_start = time.time()
    q_emb = model.encode([query_text])[0]
    emb_duration = (time.time() - emb_start) * 1000
    
    log_performance(
        "query_embedding",
        emb_duration,
        success=True,
        metadata={"query_length": len(query_text)}
    )

    # Try Qdrant first
    if client:
        try:
            search_start = time.time()
            results = client.search(
                collection_name=coll,
                query_vector=q_emb.tolist(),
                limit=top_k,
            )
            search_duration = (time.time() - search_start) * 1000
            
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
            
            log_db_operation(
                "search",
                coll,
                record_count=len(out),
                duration_ms=search_duration,
                success=True
            )
            
            overall_duration = (time.time() - start_time) * 1000
            log_operation_end(
                "vectorstore_query",
                overall_duration,
                metadata={
                    "paper_id": paper_id,
                    "results_count": len(out),
                    "storage": "qdrant"
                }
            )
            
            return out
        except Exception as e:
            log_error_with_trace(
                "qdrant_search",
                e,
                metadata={"paper_id": paper_id, "collection": coll}
            )
            logger.warning(f"Qdrant search failed, trying in-memory: {e}")

    # Fallback to in-memory search
    if coll not in _inmem_index:
        logger.warning(f"Collection {coll} not found in in-memory index")
        return []

    idx_data = _inmem_index[coll]
    embs = idx_data["embs"]
    texts = idx_data["texts"]
    metas = idx_data["meta"]

    search_start = time.time()
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
    
    search_duration = (time.time() - search_start) * 1000
    log_performance(
        "inmemory_search",
        search_duration,
        success=True,
        metadata={"paper_id": paper_id, "results_count": len(results)}
    )

    overall_duration = (time.time() - start_time) * 1000
    log_operation_end(
        "vectorstore_query",
        overall_duration,
        metadata={
            "paper_id": paper_id,
            "results_count": len(results),
            "storage": "in-memory"
        }
    )

    return results


def preload_embeddings_model() -> None:
    """Eagerly download and cache the embedding model for startup warmup."""
    logger.info("Preloading embeddings model...")
    _get_model()
    logger.info("Embeddings model preloaded")
