from fastapi import FastAPI
from app.api.upload import router as upload_router
from app.api.summary import router as summary_router
from app.api.chat import router as chat_router

app = FastAPI(title="Research Assistant Backend")

app.include_router(upload_router, prefix="/upload", tags=["upload"])
app.include_router(summary_router, prefix="/summary", tags=["summary"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])

@app.get("/health")
def health():
    return {"status": "ok"}
