from fastapi import FastAPI

app = FastAPI(title="Research Assistant Backend")


@app.get("/health")
def health():
    return {"status": "ok"}
