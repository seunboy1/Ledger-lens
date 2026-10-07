"""
Ingest-job publishing.

Production: RabbitMQ — the self-hosted replacement for SQS. Ingestion jobs
are published here and Prefect-orchestrated workers consume them
(pipelines/ledger_lens_pipelines/flows/consumer.py). See docs/architecture.md §1, §8.

Local profile: an in-process background task runs the very same extraction
flow directly, so an upload still goes upload → extract → reconcile without
a broker or a separate worker process.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable

from app.config import get_settings

settings = get_settings()
log = logging.getLogger(__name__)

_connection = None
_inline_handler: Callable[[dict], Awaitable[None]] | None = None
_inline_tasks: set[asyncio.Task] = set()
_inline_lock = asyncio.Lock()


async def drain_inline_jobs() -> None:
    """Wait for queued in-process jobs (used by tests and graceful shutdown)."""

    while _inline_tasks:
        await asyncio.gather(*list(_inline_tasks), return_exceptions=True)


def register_inline_handler(handler: Callable[[dict], Awaitable[None]]) -> None:
    """Called at startup by the API when queue_backend == 'inline'."""

    global _inline_handler
    _inline_handler = handler


async def get_connection():
    import aio_pika

    global _connection
    if _connection is None or _connection.is_closed:
        _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    return _connection


async def publish(queue_name: str, payload: dict) -> None:
    if settings.queue_backend == "inline":
        if _inline_handler is None:
            raise RuntimeError("Inline queue selected but no handler registered")

        async def _run() -> None:
            # One job at a time, like a consumer with prefetch_count=1.
            async with _inline_lock:
                try:
                    await _inline_handler(payload)
                except Exception:  # noqa: BLE001
                    log.exception("Inline ingest job failed: %s", payload)

        task = asyncio.create_task(_run())
        _inline_tasks.add(task)
        task.add_done_callback(_inline_tasks.discard)
        return

    import aio_pika

    connection = await get_connection()
    async with connection.channel() as channel:
        await channel.declare_queue(queue_name, durable=True)
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload).encode("utf-8"),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=queue_name,
        )


async def publish_ingest_job(document_id: str, tenant_id: str, storage_path: str) -> None:
    await publish(
        settings.ingest_queue,
        {"document_id": document_id, "tenant_id": tenant_id, "storage_path": storage_path},
    )
