import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.schemas import UploadResponse
from app.services.file_manager import (
    create_paper_folder,
    save_pdf_file,
    save_summary,
)
from app.services.pdf_parser import extract_text_and_metadata
from app.services.summarizer import generate_structured_summary

router = APIRouter()


@router.post("/pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    paper_id = str(uuid.uuid4())
    folder = create_paper_folder(paper_id)
    pdf_path = save_pdf_file(folder, file.file)

    try:
        text, metadata = extract_text_and_metadata(pdf_path)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    summary = generate_structured_summary(text, metadata)
    save_summary(folder, summary)

    return UploadResponse(paper_id=paper_id, summary=summary)
