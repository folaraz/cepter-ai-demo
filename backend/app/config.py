"""Settings from the environment (or a .env file), and the repo paths the app reads."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent

SCHEMA_SQL = BACKEND_DIR / "schema.sql"
ASK_YAML = BACKEND_DIR / "ask.yaml"
RECORDINGS_DIR = BACKEND_DIR / "fixtures" / "llm"
DATAROOM_DIR = REPO_ROOT / "data" / "dataroom"

LLMMode = Literal["replay", "record", "live"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://lens:lens@localhost:5432/lens"
    llm_mode: LLMMode = "replay"
    llm_model: str = "claude-sonnet-5"
    anthropic_api_key: str | None = None
    ask_live: bool = False
    embedding_cache_dir: Path = Path("./.models")
    cookie_secure: bool = False
    eval_gate: float = Field(default=0.90, ge=0.0, le=1.0)
    # Model prices are in USD; llm_calls stores GBP. Placeholder rate: confirm before
    # quoting costs.
    gbp_per_usd: float = Field(default=0.75, gt=0.0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
