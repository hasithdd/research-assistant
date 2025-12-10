import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime
from typing import Any, Dict, Optional
import traceback

# Create logs directory
LOG_DIR = Path("/app/logs")  # Inside container
LOG_DIR.mkdir(exist_ok=True)

# Configure root logger
logger = logging.getLogger("research_assistant")
logger.setLevel(logging.INFO)

if not logger.handlers:
    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    
    # File handler - main application log (rotating)
    app_log_file = LOG_DIR / "app.log"
    app_file_handler = RotatingFileHandler(
        app_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    app_file_handler.setFormatter(console_formatter)
    app_file_handler.setLevel(logging.INFO)
    logger.addHandler(app_file_handler)
    
    # File handler - error log
    error_log_file = LOG_DIR / "error.log"
    error_file_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=3,
        encoding="utf-8"
    )
    error_file_handler.setFormatter(console_formatter)
    error_file_handler.setLevel(logging.ERROR)
    logger.addHandler(error_file_handler)

# Specialized loggers
llm_logger = logging.getLogger("research_assistant.llm")
api_logger = logging.getLogger("research_assistant.api")
perf_logger = logging.getLogger("research_assistant.performance")

# Structured log files (JSON format)
llm_log_file = LOG_DIR / "llm_calls.jsonl"
api_log_file = LOG_DIR / "api_requests.jsonl"
performance_log_file = LOG_DIR / "performance.jsonl"


def log_llm_call(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    success: bool,
    error: str = None,
    latency_ms: float = 0.0
):
    """Log LLM API calls in structured JSON format."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "provider": provider,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "success": success,
        "error": error,
        "latency_ms": latency_ms,
    }
    
    with open(llm_log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    llm_logger.info(
        f"{provider}/{model}: {prompt_tokens + completion_tokens} tokens, "
        f"latency={latency_ms:.0f}ms, success={success}"
    )


def log_api_request(
    request_id: str,
    method: str,
    path: str,
    status_code: int,
    latency_ms: float,
    request_body: Optional[Dict[str, Any]] = None,
    response_body: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Log API requests in structured JSON format with detailed context."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id,
        "method": method,
        "path": path,
        "status_code": status_code,
        "latency_ms": round(latency_ms, 2),
        "request_body": request_body,
        "response_body": response_body,
        "error": error,
        "metadata": metadata or {},
    }
    
    with open(api_log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    level = "ERROR" if status_code >= 500 else "WARNING" if status_code >= 400 else "INFO"
    getattr(api_logger, level.lower())(
        f"{method} {path} - {status_code} ({latency_ms:.0f}ms) [req_id={request_id}]"
    )


def log_performance(
    operation: str,
    duration_ms: float,
    success: bool,
    metadata: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
):
    """Log performance metrics for critical operations."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "operation": operation,
        "duration_ms": round(duration_ms, 2),
        "success": success,
        "metadata": metadata or {},
        "error": error,
    }
    
    with open(performance_log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    perf_logger.info(
        f"{operation}: {duration_ms:.0f}ms, success={success}"
        + (f", error={error}" if error else "")
    )


def log_operation_start(operation: str, metadata: Optional[Dict[str, Any]] = None):
    """Log the start of a critical operation."""
    meta_str = f" {metadata}" if metadata else ""
    logger.info(f"START: {operation}{meta_str}")


def log_operation_end(operation: str, duration_ms: float, metadata: Optional[Dict[str, Any]] = None):
    """Log the end of a critical operation."""
    meta_str = f" {metadata}" if metadata else ""
    logger.info(f"END: {operation} ({duration_ms:.0f}ms){meta_str}")


def log_error_with_trace(operation: str, error: Exception, metadata: Optional[Dict[str, Any]] = None):
    """Log error with full traceback."""
    trace = traceback.format_exc()
    meta_str = f" | Metadata: {metadata}" if metadata else ""
    logger.error(
        f"ERROR in {operation}: {str(error)}{meta_str}\n{trace}"
    )


def log_file_operation(
    operation: str,
    file_path: str,
    success: bool,
    file_size_bytes: Optional[int] = None,
    error: Optional[str] = None
):
    """Log file I/O operations."""
    meta = {
        "file_path": file_path,
        "file_size_bytes": file_size_bytes,
    }
    if error:
        logger.error(f"File {operation} FAILED: {file_path} - {error}")
    else:
        size_str = f", size={file_size_bytes} bytes" if file_size_bytes else ""
        logger.info(f"File {operation}: {file_path}{size_str}")


def log_db_operation(
    operation: str,
    collection: str,
    record_count: Optional[int] = None,
    duration_ms: Optional[float] = None,
    success: bool = True,
    error: Optional[str] = None
):
    """Log database/vector store operations."""
    parts = [f"DB {operation}: {collection}"]
    if record_count is not None:
        parts.append(f"{record_count} records")
    if duration_ms is not None:
        parts.append(f"({duration_ms:.0f}ms)")
    if error:
        logger.error(f"{' '.join(parts)} - FAILED: {error}")
    else:
        logger.info(" ".join(parts))


