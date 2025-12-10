import time
import traceback
import uuid
import json

from app.utils.logger import logger, log_api_request, log_error_with_trace
from fastapi import Request
from fastapi.responses import JSONResponse


async def exception_middleware(request: Request, call_next):
    req_id = str(uuid.uuid4())
    start = time.time()
    request.state.req_id = req_id
    
    # Capture request details
    method = request.method
    path = request.url.path
    query_params = dict(request.query_params)
    
    # Attempt to capture request body (if JSON)
    request_body = None
    if method in ["POST", "PUT", "PATCH"]:
        try:
            # Read body and store it for later use
            body_bytes = await request.body()
            if body_bytes:
                request_body = json.loads(body_bytes.decode())
                # Re-create request with body for downstream handlers
                async def receive():
                    return {"type": "http.request", "body": body_bytes}
                request._receive = receive
        except Exception as e:
            logger.warning(f"Could not parse request body: {e}")
    
    logger.info(
        f"INCOMING REQUEST: {method} {path}",
        extra={
            "request_id": req_id,
            "query_params": query_params,
            "client": request.client.host if request.client else None,
        }
    )

    response = None
    response_body = None
    status_code = 500
    error = None
    
    try:
        response = await call_next(request)
        status_code = response.status_code
        
        # Capture response body for logging (if JSON and not too large)
        if hasattr(response, 'body'):
            try:
                response_body = json.loads(response.body.decode())
            except:
                pass
                
    except Exception as exc:
        error = str(exc)
        trace = traceback.format_exc()
        
        log_error_with_trace(
            operation=f"{method} {path}",
            error=exc,
            metadata={
                "request_id": req_id,
                "request_body": request_body,
                "query_params": query_params,
            }
        )
        
        response = JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(exc),
                "request_id": req_id,
            },
        )
        status_code = 500
    finally:
        duration_ms = (time.time() - start) * 1000
        
        # Log API request with full context
        log_api_request(
            request_id=req_id,
            method=method,
            path=path,
            status_code=status_code,
            latency_ms=duration_ms,
            request_body=request_body,
            response_body=response_body,
            error=error,
            metadata={
                "query_params": query_params,
                "client": request.client.host if request.client else None,
            }
        )
        
        logger.info(
            f"REQUEST COMPLETED: {method} {path} - {status_code} ({duration_ms:.0f}ms)",
            extra={
                "request_id": req_id,
                "duration_ms": duration_ms,
                "status_code": status_code,
            }
        )

    return response
