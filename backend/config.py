import os
from pathlib import Path
from typing import List, Union
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Parent Folder (InstantOCR root)
ROOT_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "InstantOCR Engine"
    
    # Hugging Face Settings (supports both HF_API_TOKEN and HF_KEY aliases)
    HF_API_TOKEN: str = Field(default="", validation_alias="HF_API_TOKEN")
    HF_KEY: str = Field(default="", validation_alias="HF_KEY")
    HF_MODEL: str = Field(default="microsoft/trocr-base-stage1", validation_alias="HF_MODEL")
    HF_MODEL_URL: str = Field(default="", validation_alias="HF_MODEL_URL")
    
    # Upload and Limits
    UPLOAD_DIR: Path = ROOT_DIR / "app" / "project" / "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    
    # CORS Origins
    CORS_ORIGINS: Union[str, List[str]] = "http://127.0.0.1:8000,http://localhost:8000"
    
    # Server Binding
    FASTAPI_HOST: str = "127.0.0.1"
    FASTAPI_PORT: int = 8001

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def effective_hf_token(self) -> str:
        return self.HF_API_TOKEN or self.HF_KEY or ""

    @property
    def effective_hf_model_url(self) -> str:
        model = self.HF_MODEL_URL or self.HF_MODEL or ""
        if model and not (model.startswith("http://") or model.startswith("https://")):
            return f"https://api-inference.huggingface.co/models/{model}"
        return model

    @property
    def parsed_cors_origins(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()
# Ensure upload directory exists
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
