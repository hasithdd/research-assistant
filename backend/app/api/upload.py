from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.file_manager import (
    create_paper_folder,
    save_pdf_file,
    save_summary,
)
from app.models.schemas import UploadResponse
import uuid

router = APIRouter()


@router.post("/pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    paper_id = str(uuid.uuid4())
    folder = create_paper_folder(paper_id)

    save_pdf_file(folder, file.file)

    placeholder_summary = {
        "title": "Placeholder Title",
        "authors": "Unknown",
        "abstract": "No abstract yet.",
        "problem_statement": "Not extracted.",
        "methodology": "Not extracted.",
        "key_results": "Not extracted.",
        "conclusion": "Not extracted.",
    }

    save_summary(folder, placeholder_summary)

    return UploadResponse(paper_id=paper_id, summary=placeholder_summary)
