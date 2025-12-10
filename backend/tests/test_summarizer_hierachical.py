from app.services.summarizer import generate_structured_summary


def test_hierarchical_summary_basic():
    text = """
    ABSTRACT
    This paper studies testing.

    INTRODUCTION
    The problem is X.

    METHODOLOGY
    We do Y.

    RESULTS
    The result is Z.

    CONCLUSION
    We conclude important things.
    """
    metadata = {"title": "Test Paper", "authors": "Author A"}

    summary = generate_structured_summary(text, metadata)

    assert summary["title"] == "Test Paper"
    assert "problem" in summary["problem_statement"].lower()
    assert "result" in summary["key_results"].lower()
    assert summary["overall_summary"]
    assert summary["section_summaries"]
