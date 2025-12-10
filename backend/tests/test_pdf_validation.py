from app.services.pdf_parser import _heuristic_validate_structure


def test_heuristic_validation():
    text = """
    ABSTRACT
    This paper describes...
    INTRODUCTION
    METHODS
    RESULTS
    CONCLUSION
    """
    result = _heuristic_validate_structure(text)
    assert result["abstract"]
    assert result["introduction"]
    assert result["methodology"]
    assert result["results"]
    assert result["conclusion"]
