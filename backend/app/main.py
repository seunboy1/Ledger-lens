import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, ingestion, workspace
from app.config import get_settings
from app.db.models import Base
from app.db.session import engine

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience only. In production apply migrations/ (schema + RLS
    # policies) with Alembic instead of create_all.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    if settings.queue_backend == "inline":
        # Same extraction flow the RabbitMQ consumer runs, executed in-process.
        from ledger_lens_pipelines.flows.extract_statement import run_ingest_job

        from app.services.queue import register_inline_handler

        register_inline_handler(run_ingest_job)

    if settings.dev_seed:
        from app.dev.seed import ensure_demo_workspace

        await ensure_demo_workspace()
    yield


app = FastAPI(title="Ledger Lens API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion.router)
app.include_router(ingestion.transactions_router)
app.include_router(chat.router)
app.include_router(workspace.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "profile": settings.profile}
