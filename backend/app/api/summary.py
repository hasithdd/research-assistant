import time

from fastapi import APIRouter, HTTPException

from app.services.file_manager import load_summary
from app.utils.logger import (
    log_operation_end,
    log_operation_start,
    log_performance,
    logger,
)

router = APIRouter()


@router.get("/{paper_id}")
def get_summary(paper_id: str):
    start_time = time.time()

    log_operation_start("get_summary", metadata={"paper_id": paper_id})

    summary = load_summary(paper_id)

    if summary is None:
        duration = (time.time() - start_time) * 1000
        logger.warning(f"Summary not found for paper {paper_id} ({duration:.0f}ms)")
        raise HTTPException(status_code=404, detail="Summary not found")

    duration = (time.time() - start_time) * 1000
    log_performance(
        "get_summary",
        duration,
        success=True,
        metadata={
            "paper_id": paper_id,
            "sections_count": len(summary.get("section_summaries", {})),
        },
    )

    log_operation_end("get_summary", duration, metadata={"paper_id": paper_id})
    logger.info(f"Summary retrieved for paper {paper_id}")

    return summary
