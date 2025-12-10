from pathlib import Path


def create_paper_folder(paper_id: str) -> Path:
    return Path("storage") / f"paper_{paper_id}"


def save_pdf_file(*args, **kwargs):
    pass
