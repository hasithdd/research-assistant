import time
from fastapi import APIRouter, HTTPException

from app.models.schemas import ChatRequest, ChatResponse, ChatSource
from app.services.rag_engine import answer_query
from app.utils.logger import (
    logger,
    log_operation_start,
    log_operation_end,
    log_performance,
    log_error_with_trace,
)

router = APIRouter()


@router.post("/", response_model=ChatResponse)
def chat(req: ChatRequest):
    start_time = time.time()
    
    log_operation_start(
        "chat_query",
        metadata={
            "paper_id": req.paper_id,
            "query_length": len(req.query),
            "query_preview": req.query[:100],
        }
    )
    
    try:
        step_start = time.time()
        result = answer_query(req.paper_id, req.query)
        query_duration = (time.time() - step_start) * 1000
        
        log_performance(
            "answer_query",
            query_duration,
            success=True,
            metadata={
                "paper_id": req.paper_id,
                "query_length": len(req.query),
                "answer_length": len(result.get("answer", "")),
                "sources_count": len(result.get("sources", [])),
            }
        )

        sources: list[ChatSource] = []
        for s in result.get("sources", []):
            if isinstance(s, str) and ":" in s:
                section, idx = s.split(":", 1)
                sources.append(ChatSource(section=section, index=int(idx)))
            else:
                sources.append(ChatSource(raw=str(s)))

        duration = (time.time() - start_time) * 1000
        log_operation_end(
            "chat_query",
            duration,
            metadata={
                "paper_id": req.paper_id,
                "sources_count": len(sources),
                "answer_length": len(result["answer"]),
            }
        )
        
        logger.info(
            f"Chat query completed for paper {req.paper_id}: "
            f"{len(sources)} sources, {len(result['answer'])} chars answer"
        )

        return ChatResponse(answer=result["answer"], sources=sources)

    except Exception as e:
        duration = (time.time() - start_time) * 1000
        log_error_with_trace(
            "chat_query",
            e,
            metadata={
                "paper_id": req.paper_id,
                "query": req.query,
                "duration_ms": duration,
            }
        )
        raise HTTPException(status_code=400, detail=str(e))
