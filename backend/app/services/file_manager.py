from pathlib import Path
from typing import Optional
import json

BASE_STORAGE = Path("storage")
BASE_STORAGE.mkdir(exist_ok=True)


def create_paper_folder(paper_id: str) -> Path:
    folder = BASE_STORAGE / f"paper_{paper_id}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def save_pdf_file(folder: Path, file_obj) -> Path:
    pdf_path = folder / "paper.pdf"
    with open(pdf_path, "wb") as f:
        f.write(file_obj.read())
    return pdf_path


def save_summary(folder: Path, summary: dict) -> Path:
    summary_path = folder / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return summary_path


def load_summary(paper_id: str) -> Optional[dict]:
    folder = BASE_STORAGE / f"paper_{paper_id}"
    summary_path = folder / "summary.json"

    if not summary_path.exists():
        return None

    with open(summary_path, "r", encoding="utf-8") as f:
        return json.load(f)
