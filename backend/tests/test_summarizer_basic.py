from app.services.summarizer import generate_structured_summary

def test_generate_structured_summary_basic():
    fake_text = (
        "This is a test abstract. "
        "This describes the problem. "
        "Methodology begins here. "
        "Key results are summarized. "
        "Conclusion of the paper."
    )

    metadata = {"title": "Test Title", "authors": "Author A"}

    summary = generate_structured_summary(fake_text, metadata)

    assert summary["title"] == "Test Title"
    assert summary["authors"] == "Author A"
    assert "test abstract" in summary["abstract"].lower()
    assert "conclusion" in summary["conclusion"].lower()
