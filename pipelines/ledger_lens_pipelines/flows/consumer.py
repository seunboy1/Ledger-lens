"""
Consumes ingest-job messages published by the backend API
(app/services/queue.py::publish_ingest_job) and triggers one flow run per
document. This is the pull-based worker described in docs/architecture.md
§1 — it only ever pulls one message at a time per worker process, which is
what makes the worker pool self-limiting rather than needing a separate
throttle.

Run with: python -m ledger_lens_pipelines.flows.consumer
"""

import asyncio
import json

import aio_pika

from app.config import get_settings
from ledger_lens_pipelines.flows.extract_statement import run_ingest_job

settings = get_settings()


async def _handle_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
    async with message.process(requeue=True):
        payload = json.loads(message.body.decode("utf-8"))
        # message.process(requeue=True) requeues on exception exit; Prefect's
        # task-level retries (see process_chunk) handle the common transient
        # cases before it ever gets here.
        await run_ingest_job(payload)


async def run_consumer() -> None:
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)  # pull one job at a time — see docstring above

        queue = await channel.declare_queue(settings.ingest_queue, durable=True)

        print(f"Ledger Lens extraction worker listening on '{settings.ingest_queue}'…")
        await queue.consume(_handle_message)

        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(run_consumer())
