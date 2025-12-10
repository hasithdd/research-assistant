from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.summary import router as summary_router
from app.api.upload import router as upload_router
from app.middleware.error import exception_middleware
from app.services.vectorstore import preload_embeddings_model

app = FastAPI(title="Research Assistant Backend")

# Allow frontend to call the backend from a different origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(exception_middleware)

app.include_router(upload_router, prefix="/upload", tags=["upload"])
app.include_router(summary_router, prefix="/summary", tags=["summary"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])


@app.on_event("startup")
async def warmup_embeddings():
    preload_embeddings_model()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/live")
def live():
    return {"status": "alive"}


@app.get("/ready")
def ready():
    return {"status": "ready"}
