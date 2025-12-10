from app.services.rag_engine import answer_query
from app.services.vectorstore import ingest_document


def test_rag_basic_retrieval(tmp_path, monkeypatch):
    text = "Machine learning improves results. Neural networks are powerful. Embeddings capture meaning."
    ingest_document("paper123", text)

    res = answer_query("paper123", "What improves results?")
    assert "improves" in res["answer"].lower()
    assert len(res["sources"]) > 0
