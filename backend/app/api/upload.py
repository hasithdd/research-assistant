# Placeholder for upload endpoint
from fastapi import APIRouter

router = APIRouter()


@router.post("/pdf")
async def upload_pdf():
    return {"message": "upload placeholder"}
