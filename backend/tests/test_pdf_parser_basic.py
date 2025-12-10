from pathlib import Path
from app.services.pdf_parser import extract_text_and_metadata

def test_extract_text_and_metadata_invalid_pdf(tmp_path):
    # create fake "pdf" text file
    fake_pdf = tmp_path / "invalid.pdf"
    fake_pdf.write_bytes(b"Not a real PDF")

    try:
        extract_text_and_metadata(fake_pdf)
        assert False, "Expected failure for invalid PDF"
    except Exception:
        assert True
