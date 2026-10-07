"""
Orchestration shim.

On the full stack (RabbitMQ queue backend) flows and tasks are real Prefect
objects: retries, concurrency limits and per-chunk state live in Prefect.

On the local profile (inline queue backend) the same functions run as plain
coroutines with a small in-process retry loop. Starting Prefect's ephemeral
API server inside the web process just to run one document would add seconds
of startup and a second database for no benefit, and the extraction logic is
identical either way.
"""

from __future__ import annotations

import asyncio
import functools
import logging
from collections.abc import Callable

from app.config import get_settings

_USE_PREFECT = get_settings().queue_backend == "rabbitmq"

if _USE_PREFECT:  # pragma: no cover - exercised only against live infra
    from prefect import flow, get_run_logger, task  # noqa: F401
else:
    _log = logging.getLogger("ledger_lens.pipeline")

    def get_run_logger() -> logging.Logger:
        return _log

    def task(fn: Callable | None = None, *, retries: int = 0, retry_delay_seconds=None, **_):
        def decorate(f: Callable) -> Callable:
            @functools.wraps(f)
            async def wrapper(*args, **kwargs):
                attempt = 0
                while True:
                    try:
                        return await f(*args, **kwargs)
                    except Exception:
                        if attempt >= retries:
                            raise
                        attempt += 1
                        # Locally there is no transient infra to wait out, so
                        # retries are immediate; Prefect applies real backoff.
                        await asyncio.sleep(0)

            return wrapper

        return decorate(fn) if fn is not None else decorate

    def flow(fn: Callable | None = None, **_):
        def decorate(f: Callable) -> Callable:
            return f

        return decorate(fn) if fn is not None else decorate
