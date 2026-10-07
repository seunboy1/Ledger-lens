"""
SQLAlchemy models for Ledger Lens.

Every table that holds tenant data carries a tenant_id and is expected to be
protected by a Postgres row-level security policy (see migrations/) — the
ORM layer does not enforce isolation itself, the database does.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import Uuid as UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.db.types import EmbeddingVector

EMBEDDING_DIM = 384  # BGE-small


class Base(DeclarativeBase):
    pass


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TransactionType(str, enum.Enum):
    credit = "credit"
    debit = "debit"


class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    reconciled = "reconciled"
    needs_review = "needs_review"
    failed = "failed"


class ChunkStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    failed = "failed"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LayoutSpec(Base):
    """
    A parsing spec induced once per distinct bank-statement layout, then
    reused deterministically for every future document with that layout.
    This is what lets the LLM stay out of the per-document hot path.
    """

    __tablename__ = "layout_specs"

    id: Mapped[uuid.UUID] = uuid_pk()
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    bank_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    spec: Mapped[dict] = mapped_column(JSON)
    # e.g. {"header_row_index": 3, "columns": {...}, "date_format": "...",
    #       "credit_markers": ["CR"], "debit_markers": ["DR"], ...}
    validated: Mapped[bool] = mapped_column(Boolean, default=False)
    times_reused: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    storage_path: Mapped[str] = mapped_column(String(1024))
    original_filename: Mapped[str] = mapped_column(String(512))
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    layout_spec_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("layout_specs.id"), nullable=True
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.uploaded
    )
    reconciliation_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    # fraction of rows that satisfied balance[n] == balance[n-1] - debit[n] + credit[n]
    bank_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Balances printed on the statement itself; the document-level proof is
    # opening + credits - debits == closing, checked against these.
    opening_balance: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    closing_balance: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document")


class DocumentChunk(Base):
    """
    One page-range unit of a document. Chunk ids are deterministic
    (see services/chunking.py) so redelivery from the queue is a safe no-op.
    """

    __tablename__ = "document_chunks"
    __table_args__ = (UniqueConstraint("document_id", "page_start", "page_end"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), index=True)
    chunk_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    page_start: Mapped[int] = mapped_column(Integer)
    page_end: Mapped[int] = mapped_column(Integer)
    status: Mapped[ChunkStatus] = mapped_column(Enum(ChunkStatus, name="chunk_status"), default=ChunkStatus.pending)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped["Document"] = relationship(back_populates="chunks")


class RawExtractedRow(Base):
    """
    Immutable staging log — exactly what was extracted from a document,
    before promotion to the canonical table. Never overwritten; kept for
    audit even if a later reconciliation pass changes what's "canonical".
    """

    __tablename__ = "raw_extracted_rows"
    __table_args__ = (UniqueConstraint("document_id", "page_number", "row_index"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    row_index: Mapped[int] = mapped_column(Integer)
    raw_date: Mapped[str] = mapped_column(String(64))
    raw_description: Mapped[str] = mapped_column(Text)
    raw_amount: Mapped[str] = mapped_column(String(64))
    raw_type_label: Mapped[str] = mapped_column(String(64))  # e.g. "CR", "Credit", "Deposit"
    raw_balance: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Transaction(Base):
    """
    Canonical, normalized, reconciled transaction. This is the only table
    the analytics layer and the SQL retrieval path query against.
    """

    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_tenant_date", "tenant_id", "transaction_date"),
        Index("ix_transactions_tenant_type", "tenant_id", "transaction_type"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id"), index=True)
    bank_name: Mapped[str] = mapped_column(String(255))
    transaction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    description: Mapped[str] = mapped_column(Text)
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType, name="transaction_type"))
    raw_type_label: Mapped[str] = mapped_column(String(64))  # preserved for audit — e.g. original "CR"/"Deposit"
    balance_after: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    reconciled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Natural-language rendering + embedding for the semantic retrieval path.
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingVector(EMBEDDING_DIM), nullable=True)
    # Reconciliation detail for the review queue: what the running balance
    # *should* have been given the previous row, when this row failed.
    expected_balance: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    # Who last changed this row after extraction: None (as extracted),
    # "ai" (targeted repair, pending human confirmation) or "human".
    repair_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Position in the statement (page, row) so rows replay in printed order.
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = uuid_pk()
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), default="New chat")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", order_by="Message.created_at")


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"


class RouteKind(str, enum.Enum):
    sql = "sql"
    semantic = "semantic"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = uuid_pk()
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id"), index=True)
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole, name="message_role"))
    content: Mapped[str] = mapped_column(Text)
    route_kind: Mapped[RouteKind | None] = mapped_column(Enum(RouteKind, name="route_kind"), nullable=True)
    # The exact transaction ids that backed this answer — the evidence panel's source.
    evidence_transaction_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    # Structured answer payload rendered by the UI: KPI cards + query-plan lineage.
    answer_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_helpful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
