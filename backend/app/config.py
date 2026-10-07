from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Environment-driven settings. Two profiles matter:

    * **full** — Postgres+pgvector, MinIO, RabbitMQ and a Prefect worker
      (see infra/docker-compose.yml). Every default below points at that stack.
    * **local** — set ``LEDGER_LENS_PROFILE=local`` to run the whole product on
      one machine with no Docker daemon: SQLite instead of Postgres, a local
      directory instead of MinIO, and an in-process background task instead
      of RabbitMQ. The extraction, reconciliation and retrieval code paths are
      identical; only the infrastructure adapters change.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    profile: Literal["full", "local"] = Field(
        default="full", validation_alias=AliasChoices("LEDGER_LENS_PROFILE", "PROFILE")
    )

    # Postgres (full) or SQLite (local)
    database_url: str = "postgresql+asyncpg://ledgerlens:ledgerlens@localhost:5432/ledgerlens"

    # Object storage — MinIO (S3-compatible, self-hosted — no AWS) or a local directory
    storage_backend: Literal["minio", "local"] = "minio"
    local_storage_dir: str = ".ledgerlens/storage"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "ledgerlens"
    minio_secret_key: str = "ledgerlens-secret"
    minio_bucket: str = "statements"
    minio_secure: bool = False

    # Queue — RabbitMQ (self-hosted broker — no SQS) or an in-process background task
    queue_backend: Literal["rabbitmq", "inline"] = "rabbitmq"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    ingest_queue: str = "ledgerlens.ingest"
    chunk_queue: str = "ledgerlens.chunks"

    # LLM inference — open-weight models via a managed provider or self-hosted vLLM/Ollama.
    # Optional: with no key, spec induction uses deterministic header heuristics and
    # chat answers are templated from the SQL result rather than phrased by a model.
    llm_provider_base_url: str = "https://api.groq.com/openai/v1"
    llm_provider_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"

    # Ask: "auto" runs the LangGraph agent when an LLM key is configured and the
    # deterministic planner otherwise; "on"/"off" force it. Either way every
    # figure comes from SQL tools, and the agent's reply must pass a grounding check.
    agent_mode: Literal["auto", "on", "off"] = "auto"

    # MCP server: which workspace the tools read (local profile defaults to the demo).
    mcp_tenant_id: str = "6f1c2a52-8d0e-4c1b-9a51-3e7d2c9b0a11"

    # Embeddings for the semantic path (sentence-transformers, CPU). Optional — when
    # disabled the semantic path uses lexical (full-text / trigram-style) ranking.
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embeddings_enabled: bool = False

    # Chunking
    pages_per_chunk: int = 40

    # Public base URL of this API (used for the local-storage upload target)
    api_base_url: str = "http://localhost:8000"
    frontend_origin: str = "http://localhost:3000"

    # Seed a demo workspace with reconciled multi-bank data on startup (dev only)
    dev_seed: bool = False

    jwt_secret: str = "change-me-in-production"

    def model_post_init(self, __context) -> None:
        if self.profile == "local":
            # Only override values still at their "full stack" defaults so an
            # explicit env var always wins.
            fields = Settings.model_fields
            if self.database_url == fields["database_url"].default:
                self.database_url = "sqlite+aiosqlite:///./.ledgerlens/ledgerlens.db"
            if self.storage_backend == fields["storage_backend"].default:
                self.storage_backend = "local"
            if self.queue_backend == fields["queue_backend"].default:
                self.queue_backend = "inline"
            if self.dev_seed == fields["dev_seed"].default:
                self.dev_seed = True

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")


@lru_cache
def get_settings() -> Settings:
    return Settings()
