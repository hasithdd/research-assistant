from typing import Any, Dict, List

from pydantic import BaseModel


class UploadResponse(BaseModel):
    paper_id: str
    summary: Dict[str, Any]


class ChatRequest(BaseModel):
    paper_id: str
    query: str


class ChatSource(BaseModel):
    section: str | None = None
    index: int | None = None
    raw: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[ChatSource]
