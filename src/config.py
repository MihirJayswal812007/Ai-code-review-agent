"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # LLM
    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    llm_model: str = Field("llama-3.3-70b-versatile", env="LLM_MODEL")

    # GitHub — support both App and PAT auth
    github_token: Optional[str] = Field(None, env="GITHUB_TOKEN")
    github_app_id: Optional[str] = Field(None, env="GITHUB_APP_ID")
    github_private_key_path: Optional[str] = Field(None, env="GITHUB_PRIVATE_KEY_PATH")
    github_webhook_secret: Optional[str] = Field(None, env="GITHUB_WEBHOOK_SECRET")

    # Server
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    log_level: str = Field("info", env="LOG_LEVEL")

    # Review limits
    max_files_per_review: int = Field(20, env="MAX_FILES_PER_REVIEW")
    max_diff_lines: int = Field(500, env="MAX_DIFF_LINES")
    review_languages: str = Field(
        "python,javascript,typescript,java,go,rust,ruby,cpp,c,csharp",
        env="REVIEW_LANGUAGES"
    )

    @property
    def supported_languages(self) -> list[str]:
        return [lang.strip() for lang in self.review_languages.split(",")]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


def get_settings() -> Settings:
    return Settings()
