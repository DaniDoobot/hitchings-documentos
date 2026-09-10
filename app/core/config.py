from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Google Gemini Configuration
    GEMINI_API_KEY: str = ""
    GEMINI_TRANSCRIPTION_MODEL: str = "gemini-3.5-transcribe"
    GEMINI_ANALYSIS_MODEL: str = "gemini-3.8-flash"
    GEMINI_ANALYSIS_THINKING_LEVEL: Literal["low", "medium", "high"] = "medium"
    GEMINI_TIMEOUT_SECONDS: int = 300
    GEMINI_MAX_RETRIES: int = 2

    # Processing Limits
    MAX_DOCUMENT_SIZE_MB: int = 25
    MAX_AUDIO_SIZE_MB: int = 200
    MAX_TEXT_CHARACTERS: int = 5000000
    MAX_ANALYSIS_INPUT_TOKENS: int = 900000
    MAX_EXPORT_CHARACTERS: int = 2000000

    # Database & Session Configuration
    DATABASE_URL: str = "postgresql+psycopg://hitchings_user:hitchings_pass@postgres:5432/hitchings_docs"
    SESSION_COOKIE_NAME: str = "hyg_session"
    SESSION_TTL_HOURS: int = 12
    SESSION_COOKIE_SECURE: bool | None = None

    # CORS Configuration
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173"

    @property
    def is_cookie_secure(self) -> bool:
        if self.SESSION_COOKIE_SECURE is not None:
            return self.SESSION_COOKIE_SECURE
        return self.APP_ENV.lower() == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def max_document_size_bytes(self) -> int:
        return self.MAX_DOCUMENT_SIZE_MB * 1024 * 1024

    @property
    def max_audio_size_bytes(self) -> int:
        return self.MAX_AUDIO_SIZE_MB * 1024 * 1024


settings = Settings()
