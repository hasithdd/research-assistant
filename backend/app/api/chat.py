from fastapi import APIRouter, HTTPException

from app.models.schemas import ChatRequest, ChatResponse
from app.services.rag_engine import answer_query

router = APIRouter()


@router.post("/", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        result = answer_query(req.paper_id, req.query)
        formatted_sources = []
        for s in result.get("sources", []):
            if isinstance(s, str) and ":" in s:
                section, idx = s.split(":", 1)
                formatted_sources.append({"section": section, "index": int(idx)})
            else:
                formatted_sources.append({"raw": s})

        return {
            "answer": result["answer"],
            "sources": formatted_sources,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
