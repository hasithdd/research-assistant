from fastapi import APIRouter, HTTPException

from app.models.schemas import ChatRequest, ChatResponse
from app.services.rag_engine import answer_query

router = APIRouter()


@router.post("/", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        result = answer_query(req.paper_id, req.query)

        sources_out = []
        for s in result.get("sources", []):
            if isinstance(s, str) and ":" in s:
                section, idx = s.split(":", 1)
                sources_out.append({"section": section, "index": int(idx)})
            else:
                sources_out.append({"raw": s})

        return {"answer": result["answer"], "sources": sources_out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
