from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str | None = None
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    OPENAI_API_KEY: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()
