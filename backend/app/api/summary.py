from fastapi import APIRouter

router = APIRouter()


@router.get("/{paper_id}")
async def get_summary(paper_id: str):
    return {"summary": "summary placeholder"}
