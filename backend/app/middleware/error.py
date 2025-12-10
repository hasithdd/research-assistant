import traceback
import uuid

from app.utils.logger import logger
from fastapi import Request
from fastapi.responses import JSONResponse


async def exception_middleware(request: Request, call_next):
    req_id = str(uuid.uuid4())
    request.state.req_id = req_id

    try:
        response = await call_next(request)
        return response

    except Exception as exc:
        logger.error(
            "Unhandled Exception",
            extra={
                "request_id": req_id,
                "path": request.url.path,
                "method": request.method,
                "error": str(exc),
                "trace": traceback.format_exc(),
            },
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(exc),
                "request_id": req_id,
            },
        )
