"""
Cross-dialect column types.

Production is Postgres (+pgvector). The local/e2e profile runs on SQLite so
the full product can be exercised without a Docker daemon. These types
render as the native pgvector `vector(n)` on Postgres and degrade to a JSON
list on anything else — semantic search then ranks in Python (fine for the
dev dataset; pgvector's HNSW index takes over at scale).
"""

from __future__ import annotations

import json

from sqlalchemy.types import JSON, TypeDecorator, UserDefinedType


class _PgVector(UserDefinedType):
    cache_ok = True

    def __init__(self, dim: int):
        self.dim = dim

    def get_col_spec(self, **kw):  # noqa: ARG002
        return f"vector({self.dim})"

    def bind_processor(self, dialect):  # noqa: ARG002
        def process(value):
            if value is None:
                return None
            return "[" + ",".join(f"{float(v):.8f}" for v in value) + "]"

        return process

    def result_processor(self, dialect, coltype):  # noqa: ARG002
        def process(value):
            if value is None:
                return None
            if isinstance(value, str):
                return [float(v) for v in value.strip("[]").split(",") if v]
            return list(value)

        return process


class EmbeddingVector(TypeDecorator):
    impl = JSON
    cache_ok = True

    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_PgVector(self.dim))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return [float(v) for v in value]

    def process_result_value(self, value, dialect):  # noqa: ARG002
        if value is None:
            return None
        if isinstance(value, str):
            return json.loads(value)
        return list(value)
