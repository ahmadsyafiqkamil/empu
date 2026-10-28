"""Runtime settings. The only module in empu that reads the environment or .env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True
    )

    meta_model_api_key: SecretStr | None = Field(default=None, validation_alias="META_MODEL_API_KEY")
    studio_key: SecretStr | None = Field(default=None, validation_alias="STUDIO_KEY")
    meta_base_url: str = Field(default="https://api.meta.ai/v1", validation_alias="META_BASE_URL")
    muse_model: str = Field(default="muse-spark-1.3", validation_alias="MUSE_MODEL")
    sam_model: str = Field(default="sam-3.1", validation_alias="SAM_MODEL")

    data_dir: Path = Field(default=REPO_ROOT / "data", validation_alias="EMPU_DATA_DIR")
    packs_dir: Path = Field(default=REPO_ROOT / "packs", validation_alias="EMPU_PACKS_DIR")
    testdata_dir: Path = Field(default=REPO_ROOT / "data-uji", validation_alias="EMPU_TESTDATA_DIR")
    db_url: str = Field(default="", validation_alias="EMPU_DB_URL")

    chunk_window_s: float = Field(default=75.0, validation_alias="EMPU_CHUNK_WINDOW_S")
    chunk_overlap_s: float = Field(default=10.0, validation_alias="EMPU_CHUNK_OVERLAP_S")
    analyze_concurrency: int = Field(default=3, validation_alias="EMPU_ANALYZE_CONCURRENCY")
    pipeline_mode: Literal["A", "B"] = Field(default="B", validation_alias="EMPU_PIPELINE_MODE")
    structured_output: bool = Field(default=True, validation_alias="EMPU_STRUCTURED_OUTPUT")
    structured_schema_variant: Literal["full", "stripped"] = Field(
        default="full", validation_alias="EMPU_STRUCTURED_SCHEMA_VARIANT"
    )
    sam_enabled: bool = Field(default=True, validation_alias="EMPU_SAM_ENABLED")
    transcribe_backend: Literal["muse", "whisper"] = Field(
        default="whisper", validation_alias="EMPU_TRANSCRIBE_BACKEND"
    )
    transcribe_model: str = Field(default="", validation_alias="EMPU_TRANSCRIBE_MODEL")

    max_upload_mb: int = Field(default=500, validation_alias="EMPU_MAX_UPLOAD_MB")
    max_duration_s: float = Field(default=1200.0, validation_alias="EMPU_MAX_DURATION_S")
    sandbox_max_duration_s: float = Field(default=180.0, validation_alias="EMPU_SANDBOX_MAX_DURATION_S")
    sandbox_daily_quota: int = Field(default=30, validation_alias="EMPU_SANDBOX_DAILY_QUOTA")

    @model_validator(mode="after")
    def _derive(self) -> Settings:
        if not self.db_url:
            self.db_url = f"sqlite:///{self.data_dir / 'empu.db'}"
        return self

    def require_api_key(self) -> str:
        if self.meta_model_api_key is None or not self.meta_model_api_key.get_secret_value():
            raise RuntimeError("META_MODEL_API_KEY is not set (see .env.example)")
        return self.meta_model_api_key.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    return Settings()
