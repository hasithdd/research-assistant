from app.services.vectorstore import ingest_document, query

def test_vectorstore_fallback():
    text = "This is a test document about machine learning and embeddings"
    ingest_document("test", text)

    results = query("test", "embeddings", top_k=3)

    assert len(results) > 0
    assert "embeddings" in " ".join(results)
