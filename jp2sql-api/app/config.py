from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    gemini_temperature: float = float(os.getenv("GEMINI_TEMPERATURE", "0.2"))
    gemini_max_output_tokens: int = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "1024"))
    max_limit: int = int(os.getenv("MAX_LIMIT", "1000"))
    schemas: list[str] = tuple(
        s.strip() for s in os.getenv("SCHEMAS", "public").split(",") if s.strip()
    )

    # セキュリティ関連（拡張用）
    allow_experimental_functions: bool = False

settings = Settings()
