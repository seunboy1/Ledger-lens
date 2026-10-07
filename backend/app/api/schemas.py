import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from app.db.models import RouteKind


def as_utc(value: datetime) -> str:
    """Every stored datetime is UTC; SQLite returns them naive, so tag them."""

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


UtcDateTime = Annotated[datetime, PlainSerializer(as_utc, return_type=str)]


class UploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)


class UploadResponse(BaseModel):
    document_id: uuid.UUID
    upload_url: str
    storage_path: str


class DocumentStatusResponse(BaseModel):
    document_id: uuid.UUID
    status: str
    reconciliation_score: float | None
    page_count: int | None


class DocumentSummary(BaseModel):
    id: uuid.UUID
    filename: str
    bank_name: str | None
    status: str
    page_count: int | None
    reconciliation_score: float | None
    transaction_count: int
    period_start: UtcDateTime | None
    period_end: UtcDateTime | None
    error: str | None
    created_at: UtcDateTime


class ProofOut(BaseModel):
    opening: float | None
    closing_printed: float | None
    closing_computed: float | None
    total_credits: float
    total_debits: float
    rows_total: int
    rows_verified: int
    document_check_ok: bool | None
    pending_ai_repairs: int


class LayoutOut(BaseModel):
    fingerprint: str
    amount_convention: str | None
    date_format: str | None
    induced_by: str | None
    times_reused: int
    columns: dict


class ChunkProgress(BaseModel):
    done: int
    failed: int
    total: int


class TxnOut(BaseModel):
    id: uuid.UUID
    date: UtcDateTime
    description: str
    amount: float
    type: str
    raw_label: str
    bank: str
    balance_after: float | None
    expected_balance: float | None
    reconciled: bool
    repair_source: str | None
    page_number: int | None


class DocumentDetail(DocumentSummary):
    proof: ProofOut
    layout: LayoutOut | None
    chunks: ChunkProgress
    failing_rows: list[TxnOut]


class TxnPage(BaseModel):
    total: int
    items: list[TxnOut]


class RowCorrection(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    transaction_type: Literal["credit", "debit"] | None = None


class ReviewDecision(BaseModel):
    action: Literal["accept", "reject"]


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", max_length=255)


class ConversationRename(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    updated_at: UtcDateTime


class EvidenceRowOut(BaseModel):
    id: uuid.UUID
    date: str
    amount: str
    type: str
    raw_label: str
    bank: str
    description: str
    focused: bool = False


class LineageStep(BaseModel):
    title: str
    detail: str


class KpiOut(BaseModel):
    label: str
    value: str
    tone: Literal["credit", "debit", "neutral"] = "neutral"


class EvidenceOut(BaseModel):
    summary_title: str
    summary_subtitle: str
    lineage: list[LineageStep]
    rows: list[EvidenceRowOut]
    total_rows: int
    isolation_note: str


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    route_kind: RouteKind | None
    created_at: UtcDateTime
    kpis: list[KpiOut] = []
    source_summary: str | None = None
    evidence: EvidenceOut | None = None
    is_helpful: bool | None = None
    engine: Literal["agent", "deterministic"] | None = None


class SendMessageOut(BaseModel):
    conversation: ConversationOut
    user_message: MessageOut
    assistant_message: MessageOut


class FeedbackIn(BaseModel):
    helpful: bool
