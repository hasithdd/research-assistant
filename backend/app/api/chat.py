from fastapi import APIRouter
from app.models.schemas import ChatRequest, ChatResponse

router = APIRouter()

@router.post("/", response_model=ChatResponse)
def chat(request: ChatRequest):
    return ChatResponse(
        answer="RAG not implemented yet. This is a placeholder response.",
        sources=[]
    )
