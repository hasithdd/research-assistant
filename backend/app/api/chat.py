from fastapi import APIRouter

router = APIRouter()


@router.post("/")
async def chat():
    return {"answer": "chat placeholder"}
