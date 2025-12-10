from fastapi import APIRouter, HTTPException

from app.models.schemas import ChatRequest, ChatResponse, ChatSource
from app.services.rag_engine import answer_query

router = APIRouter()


@router.post("/", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        result = answer_query(req.paper_id, req.query)

        sources: list[ChatSource] = []
        for s in result.get("sources", []):
            if isinstance(s, str) and ":" in s:
                section, idx = s.split(":", 1)
                sources.append(ChatSource(section=section, index=int(idx)))
            else:
                sources.append(ChatSource(raw=str(s)))

        return ChatResponse(answer=result["answer"], sources=sources)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
