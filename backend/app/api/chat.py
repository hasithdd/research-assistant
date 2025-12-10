from fastapi import APIRouter, HTTPException

from app.models.schemas import ChatRequest, ChatResponse
from app.services.rag_engine import answer_query

router = APIRouter()


@router.post("/", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        result = answer_query(req.paper_id, req.query)
        return ChatResponse(answer=result["answer"], sources=result["sources"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
