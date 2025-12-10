from fastapi import APIRouter, HTTPException
from app.services.file_manager import load_summary

router = APIRouter()

@router.get("/{paper_id}")
def get_summary(paper_id: str):
    summary = load_summary(paper_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Summary not found")
    return summary
