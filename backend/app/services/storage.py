"""
Object storage.

Production: MinIO — an S3-API-compatible, self-hosted store. Every call
uses the same shape the AWS S3 SDK would, but talks to infrastructure you
run yourself. No AWS account or service required.

Local profile: a directory on disk, with the "pre-signed URL" pointing at
the API's own PUT endpoint (see api/ingestion.upload_content). Same
contract for the browser — request an upload target, PUT the bytes there,
then notify — so the frontend code is identical in both profiles.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from app.config import get_settings

settings = get_settings()

_client = None


def _minio():
    global _client
    if _client is None:
        from minio import Minio

        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _client


def _local_path(object_name: str) -> Path:
    root = Path(settings.local_storage_dir).expanduser().resolve()
    target = (root / object_name).resolve()
    if root not in target.parents:
        raise ValueError("Invalid object name")
    return target


def ensure_bucket() -> None:
    if settings.storage_backend == "local":
        Path(settings.local_storage_dir).expanduser().mkdir(parents=True, exist_ok=True)
        return
    client = _minio()
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


def presigned_upload_url(object_name: str, expires_minutes: int = 15) -> str:
    """
    The client uploads directly to this URL — the file's bytes never pass
    through the FastAPI process in production. See docs/architecture.md §1.
    """

    if settings.storage_backend == "local":
        return f"{settings.api_base_url}/documents/upload-content/{object_name}"
    return _minio().presigned_put_object(
        settings.minio_bucket, object_name, expires=timedelta(minutes=expires_minutes)
    )


def presigned_download_url(object_name: str, expires_minutes: int = 15) -> str:
    if settings.storage_backend == "local":
        return f"{settings.api_base_url}/documents/upload-content/{object_name}"
    return _minio().presigned_get_object(
        settings.minio_bucket, object_name, expires=timedelta(minutes=expires_minutes)
    )


def put_object(object_name: str, data: bytes) -> None:
    if settings.storage_backend == "local":
        path = _local_path(object_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return
    from io import BytesIO

    _minio().put_object(settings.minio_bucket, object_name, BytesIO(data), length=len(data))


def object_exists(object_name: str) -> bool:
    if settings.storage_backend == "local":
        return _local_path(object_name).exists()
    try:
        _minio().stat_object(settings.minio_bucket, object_name)
        return True
    except Exception:  # noqa: BLE001
        return False


def download_object(object_name: str) -> bytes:
    """
    Direct server-side download — used by pipeline workers, which read the
    document's bytes themselves rather than following a presigned URL.
    """

    if settings.storage_backend == "local":
        return _local_path(object_name).read_bytes()

    response = _minio().get_object(settings.minio_bucket, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()
