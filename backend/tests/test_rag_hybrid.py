from app.services.vectorstore import ingest_document
from app.services.rag_engine import answer_query


def test_hybrid_retrieval_merging():
    text = """
    ABSTRACT
    Short intro.

    METHODOLOGY
    We used a CNN-based approach.

    RESULTS
    Accuracy achieved was 90%.
    """

    ingest_document("hybrid1", text)

    res = answer_query("hybrid1", "What methodology did they use?")
    assert res["answer"]
    assert "cnn" in res["answer"].lower() or "method" in res["answer"].lower()
