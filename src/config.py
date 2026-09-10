from pathlib import Path
import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    DATA_DIR: str = "./data"
    SQLITE_DB_PATH: str = "./data/slate.db"
    
    # Target models (strict, no silent fallback)
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    RERANKER_MODEL_NAME: str = "BAAI/bge-reranker-v2-m3"
    CLIP_MODEL_NAME: str = "clip-ViT-B-32"
    
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K: int = 4
    SIMILARITY_THRESHOLD: float = 0.5

    # LLM API Keys
    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # LangSmith Observability & Tracking
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_PROJECT: str = "Slate"
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def ensure_directories(self) -> None:
        Path(self.DATA_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.SQLITE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    def configure_langsmith(self) -> None:
        """Sets environment variables for LangChain/LangSmith tracing."""
        if self.LANGCHAIN_API_KEY:
            os.environ["LANGCHAIN_TRACING_V2"] = str(self.LANGCHAIN_TRACING_V2).lower()
            os.environ["LANGCHAIN_PROJECT"] = self.LANGCHAIN_PROJECT
            os.environ["LANGCHAIN_API_KEY"] = self.LANGCHAIN_API_KEY
            os.environ["LANGCHAIN_ENDPOINT"] = self.LANGCHAIN_ENDPOINT


settings = Settings()
settings.ensure_directories()
settings.configure_langsmith()
