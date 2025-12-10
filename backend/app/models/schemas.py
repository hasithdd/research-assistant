from typing import Any, Dict, List

from pydantic import BaseModel


class UploadResponse(BaseModel):
    paper_id: str
    summary: Dict[str, Any]


class ChatRequest(BaseModel):
    paper_id: str
    query: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
