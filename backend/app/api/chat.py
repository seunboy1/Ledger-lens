"""
Conversation + retrieval API.

`POST /conversations/{id}/messages` is what the chat composer calls. The
question is routed and planned (services/answering.py), executed as SQL
over verified rows, and answered with a bounded, cited set of transaction
rows. This is the enforcement point for the architecture's central claim:
no model reads the corpus and no model computes a number.

Every route checks that the conversation belongs to the caller's tenant.
On Postgres, RLS enforces the same thing a second time underneath.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, get_tenant_db
from app.api.schemas import (
    ConversationCreate,
    ConversationOut,
    ConversationRename,
    EvidenceOut,
    EvidenceRowOut,
    FeedbackIn,
    MessageCreate,
    MessageOut,
    SendMessageOut,
)
from app.db.models import Conversation, Message, MessageRole, RouteKind as DbRouteKind, Transaction
from app.agent import respond
from app.services.answering import money
from app.services.router import RetrievalRoute

router = APIRouter(prefix="/conversations", tags=["chat"])

DEFAULT_TITLE = "New conversation"


async def _get_conversation(db: AsyncSession, tenant_id: uuid.UUID, conversation_id: uuid.UUID) -> Conversation:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None or conversation.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.post("", response_model=ConversationOut, status_code=201)
async def create_conversation(
    body: ConversationCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> Conversation:
    conversation = Conversation(tenant_id=tenant_id, title=body.title.strip() or DEFAULT_TITLE)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> list[Conversation]:
    result = await db.execute(
        select(Conversation).where(Conversation.tenant_id == tenant_id).order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


@router.patch("/{conversation_id}", response_model=ConversationOut)
async def rename_conversation(
    conversation_id: uuid.UUID,
    body: ConversationRename,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> Conversation:
    conversation = await _get_conversation(db, tenant_id, conversation_id)
    conversation.title = body.title.strip()
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> Response:
    conversation = await _get_conversation(db, tenant_id, conversation_id)
    await db.execute(delete(Message).where(Message.conversation_id == conversation.id))
    await db.delete(conversation)
    await db.commit()
    return Response(status_code=204)


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conversation_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> list[MessageOut]:
    await _get_conversation(db, tenant_id, conversation_id)
    result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at, Message.role)
    )
    return [await _to_message_out(m, db, tenant_id) for m in result.scalars().all()]


@router.post("/{conversation_id}/messages", response_model=SendMessageOut)
async def send_message(
    conversation_id: uuid.UUID,
    body: MessageCreate,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> SendMessageOut:
    conversation = await _get_conversation(db, tenant_id, conversation_id)
    question = body.content.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question is empty")

    now = datetime.now(timezone.utc)
    user_message = Message(conversation_id=conversation.id, role=MessageRole.user, content=question, created_at=now)
    db.add(user_message)

    answer = await respond(db, tenant_id, question)

    assistant_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.assistant,
        content=answer.content,
        route_kind=DbRouteKind.sql if answer.route == RetrievalRoute.sql else DbRouteKind.semantic,
        evidence_transaction_ids=[str(i) for i in answer.evidence_ids],
        answer_meta={
            "kpis": [k.__dict__ for k in answer.kpis],
            "lineage": answer.lineage,
            "summary_title": answer.summary_title,
            "summary_subtitle": answer.summary_subtitle,
            "source_summary": answer.source_summary,
            "focused_ids": [str(i) for i in answer.focused_ids],
            "matched_rows": answer.matched_rows,
            "engine": answer.engine,
        },
        created_at=datetime.now(timezone.utc),
    )
    db.add(assistant_message)

    if conversation.title == DEFAULT_TITLE:
        conversation.title = question[:80].rstrip("?. ") or DEFAULT_TITLE
    conversation.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(conversation)

    return SendMessageOut(
        conversation=ConversationOut.model_validate(conversation),
        user_message=await _to_message_out(user_message, db, tenant_id),
        assistant_message=await _to_message_out(assistant_message, db, tenant_id),
    )


@router.post("/{conversation_id}/messages/{message_id}/feedback", response_model=MessageOut)
async def message_feedback(
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    body: FeedbackIn,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> MessageOut:
    await _get_conversation(db, tenant_id, conversation_id)
    message = await db.get(Message, message_id)
    if message is None or message.conversation_id != conversation_id or message.role != MessageRole.assistant:
        raise HTTPException(status_code=404, detail="Message not found")
    message.is_helpful = body.helpful
    await db.commit()
    return await _to_message_out(message, db, tenant_id)


async def _to_message_out(message: Message, db: AsyncSession, tenant_id: uuid.UUID) -> MessageOut:
    meta = message.answer_meta or {}
    evidence = None

    if message.role == MessageRole.assistant and meta:
        rows: list[EvidenceRowOut] = []
        ids = [uuid.UUID(i) for i in (message.evidence_transaction_ids or [])]
        if ids:
            result = await db.execute(
                select(Transaction).where(Transaction.id.in_(ids), Transaction.tenant_id == tenant_id)
            )
            by_id = {t.id: t for t in result.scalars().all()}
            focused = set(meta.get("focused_ids", []))
            for i in ids:
                t = by_id.get(i)
                if t is None:
                    continue  # row removed since (e.g. statement re-processed)
                rows.append(
                    EvidenceRowOut(
                        id=t.id,
                        date=t.transaction_date.strftime("%d %b %Y"),
                        amount=money(t.amount),
                        type=t.transaction_type.value,
                        raw_label=t.raw_type_label,
                        bank=t.bank_name,
                        description=t.description,
                        focused=str(t.id) in focused,
                    )
                )
        evidence = EvidenceOut(
            summary_title=meta.get("summary_title") or f"{len(rows)} rows",
            summary_subtitle=meta.get("summary_subtitle") or "",
            lineage=meta.get("lineage", []),
            rows=rows,
            total_rows=meta.get("matched_rows", len(rows)),
            isolation_note=(
                "Every row above was read under this workspace's tenant scope. "
                "On Postgres, row-level security enforces it in the database."
            ),
        )

    return MessageOut(
        id=message.id,
        role=message.role.value,
        content=message.content,
        route_kind=message.route_kind,
        created_at=message.created_at or datetime.now(timezone.utc),
        kpis=meta.get("kpis", []),
        source_summary=meta.get("source_summary"),
        evidence=evidence,
        is_helpful=message.is_helpful,
        engine=meta.get("engine", "deterministic") if message.role == MessageRole.assistant else None,
    )
