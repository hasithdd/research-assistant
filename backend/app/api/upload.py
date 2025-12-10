import uuid
import time

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.schemas import UploadResponse
from app.services.file_manager import (
    create_paper_folder,
    save_pdf_file,
    save_summary,
)
from app.services.pdf_parser import extract_text_and_metadata
from app.services.summarizer import generate_structured_summary
from app.services.vectorstore import ingest_document
from app.utils.logger import (
    logger,
    log_operation_start,
    log_operation_end,
    log_performance,
    log_error_with_trace,
)

router = APIRouter()


@router.post("/pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    overall_start = time.time()
    paper_id = str(uuid.uuid4())
    
    log_operation_start(
        "upload_pdf",
        metadata={
            "paper_id": paper_id,
            "filename": file.filename,
            "content_type": file.content_type,
        }
    )
    
    # Validate file type
    if file.content_type != "application/pdf":
        logger.warning(f"Invalid file type: {file.content_type} for file {file.filename}")
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    # Create folder and save PDF
    try:
        step_start = time.time()
        folder = create_paper_folder(paper_id)
        pdf_path = save_pdf_file(folder, file.file)
        file_size = pdf_path.stat().st_size
        step_duration = (time.time() - step_start) * 1000
        
        log_performance(
            "save_pdf_file",
            step_duration,
            success=True,
            metadata={
                "paper_id": paper_id,
                "file_size_bytes": file_size,
                "filename": file.filename,
            }
        )
        logger.info(f"PDF saved: {file.filename} ({file_size} bytes) for paper {paper_id}")
        
    except Exception as e:
        log_error_with_trace("save_pdf_file", e, {"paper_id": paper_id})
        raise HTTPException(status_code=500, detail=f"Failed to save PDF: {e}")

    # Extract text and metadata
    try:
        step_start = time.time()
        text, metadata = extract_text_and_metadata(pdf_path)
        step_duration = (time.time() - step_start) * 1000
        
        log_performance(
            "extract_text_and_metadata",
            step_duration,
            success=True,
            metadata={
                "paper_id": paper_id,
                "text_length": len(text),
                "extracted_title": metadata.get("title", "")[:100],
            }
        )
        logger.info(
            f"Text extracted for paper {paper_id}: {len(text)} chars, "
            f"title: {metadata.get('title', 'N/A')[:50]}"
        )
        
    except Exception as e:
        log_error_with_trace("extract_text_and_metadata", e, {"paper_id": paper_id})
        raise HTTPException(status_code=422, detail=f"PDF parsing failed: {e}")

    # Ingest document into vector store
    try:
        step_start = time.time()
        ingest_document(paper_id, text)
        step_duration = (time.time() - step_start) * 1000
        
        log_performance(
            "ingest_document",
            step_duration,
            success=True,
            metadata={
                "paper_id": paper_id,
                "text_length": len(text),
            }
        )
        logger.info(f"Document ingested to vector store for paper {paper_id}")
        
    except Exception as e:
        log_error_with_trace("ingest_document", e, {"paper_id": paper_id})
        raise HTTPException(status_code=500, detail=f"Vector store ingestion failed: {e}")

    # Generate summary
    try:
        step_start = time.time()
        summary = generate_structured_summary(text, metadata)
        step_duration = (time.time() - step_start) * 1000
        
        log_performance(
            "generate_structured_summary",
            step_duration,
            success=True,
            metadata={
                "paper_id": paper_id,
                "sections_summarized": len(summary.get("section_summaries", {})),
            }
        )
        logger.info(
            f"Summary generated for paper {paper_id}: "
            f"{len(summary.get('section_summaries', {}))} sections"
        )
        
    except Exception as e:
        log_error_with_trace("generate_structured_summary", e, {"paper_id": paper_id})
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {e}")

    # Save summary
    try:
        save_summary(folder, summary)
        logger.info(f"Summary saved for paper {paper_id}")
    except Exception as e:
        log_error_with_trace("save_summary", e, {"paper_id": paper_id})
        # Non-critical, don't fail the request

    overall_duration = (time.time() - overall_start) * 1000
    log_operation_end(
        "upload_pdf",
        overall_duration,
        metadata={
            "paper_id": paper_id,
            "filename": file.filename,
            "file_size_bytes": file_size,
            "text_length": len(text),
        }
    )
    
    logger.info(
        f"PDF upload completed successfully for paper {paper_id} in {overall_duration:.0f}ms"
    )

    return UploadResponse(paper_id=paper_id, summary=summary)
