from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import re


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://honeymind:honeymind_lab_only_change_me@localhost:5432/honeymind"
    database_url_sync: str = "postgresql://honeymind:honeymind_lab_only_change_me@localhost:5432/honeymind"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    llm_provider: str = "none"
    llm_api_key: str = ""
    llm_model: str = ""
    llm_base_url: str = ""
    embedding_model: str = "hash"
    random_seed: int = 42
    rate_limit_per_minute: int = 120
    max_request_bytes: int = 65536
    honeymind_env: str = "lab"

    @field_validator("llm_api_key")
    @classmethod
    def reject_production_looking_keys(cls, v: str) -> str:
        # Containment: refuse keys that look like common cloud production patterns in lab docs.
        # Real lab keys may still be set deliberately; this blocks accidental paste of AWS-style material.
        if v and re.search(r"AKIA[0-9A-Z]{16}", v):
            raise ValueError("Refusing AWS-style access key material in HoneyMind configuration")
        return v


settings = Settings()
