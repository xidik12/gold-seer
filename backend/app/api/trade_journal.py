"""Trade journal entries API — full CRUD."""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, delete

from app.database import async_session, TradeJournalEntry
from app.api.admin import _verify_telegram_init_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trade-journal", tags=["trade_journal"])


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------


def _get_telegram_id(request: Request) -> int:
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Missing initData")
    user_data = _verify_telegram_init_data(init_data, max_age=86400)
    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(400, "Invalid user data")
    return int(telegram_id)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class JournalEntryCreate(BaseModel):
    broker_trade_id: Optional[int] = None
    trade_advice_id: Optional[int] = None
    notes: Optional[str] = None
    emotion: Optional[str] = Field(default=None, max_length=30)
    self_rating: Optional[int] = Field(default=None, ge=1, le=5)
    lessons: Optional[str] = None
    direction: Optional[str] = Field(default=None, max_length=10)
    symbol: Optional[str] = Field(default="XAUUSD", max_length=20)
    open_price: Optional[float] = None
    exit_price: Optional[float] = None
    lot_size: Optional[float] = None
    pnl: Optional[float] = None
    open_date: Optional[datetime] = None
    close_date: Optional[datetime] = None
    status: Optional[str] = Field(default="open", max_length=20)


class JournalEntryUpdate(BaseModel):
    broker_trade_id: Optional[int] = None
    trade_advice_id: Optional[int] = None
    notes: Optional[str] = None
    emotion: Optional[str] = Field(default=None, max_length=30)
    self_rating: Optional[int] = Field(default=None, ge=1, le=5)
    ai_entry_quality: Optional[float] = None
    lessons: Optional[str] = None
    direction: Optional[str] = Field(default=None, max_length=10)
    symbol: Optional[str] = Field(default=None, max_length=20)
    open_price: Optional[float] = None
    exit_price: Optional[float] = None
    lot_size: Optional[float] = None
    pnl: Optional[float] = None
    open_date: Optional[datetime] = None
    close_date: Optional[datetime] = None
    status: Optional[str] = Field(default=None, max_length=20)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _entry_to_dict(entry: TradeJournalEntry) -> dict:
    """Serialize a TradeJournalEntry to a dict."""
    return {c.name: getattr(entry, c.name) for c in TradeJournalEntry.__table__.columns}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/entries")
async def get_journal_entries(
    telegram_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
):
    """Get trade journal entries, optionally filtered by telegram_id and status."""
    async with async_session() as session:
        query = select(TradeJournalEntry).order_by(TradeJournalEntry.created_at.desc())

        if telegram_id is not None:
            query = query.where(TradeJournalEntry.telegram_id == telegram_id)
        if status is not None:
            query = query.where(TradeJournalEntry.status == status)

        query = query.limit(limit)
        result = await session.execute(query)
        entries = result.scalars().all()

        return {
            "entries": [_entry_to_dict(e) for e in entries],
            "count": len(entries),
        }


@router.post("/entries", status_code=201)
async def create_journal_entry(body: JournalEntryCreate, request: Request):
    """Create a new trade journal entry."""
    telegram_id = _get_telegram_id(request)
    async with async_session() as session:
        entry = TradeJournalEntry(
            telegram_id=telegram_id,
            broker_trade_id=body.broker_trade_id,
            trade_advice_id=body.trade_advice_id,
            notes=body.notes,
            emotion=body.emotion,
            self_rating=body.self_rating,
            lessons=body.lessons,
            direction=body.direction,
            symbol=body.symbol,
            open_price=body.open_price,
            exit_price=body.exit_price,
            lot_size=body.lot_size,
            pnl=body.pnl,
            open_date=body.open_date,
            close_date=body.close_date,
            status=body.status,
        )
        session.add(entry)
        await session.commit()
        await session.refresh(entry)

        logger.info(
            "Trade journal entry created: id=%d telegram_id=%d symbol=%s direction=%s",
            entry.id, entry.telegram_id, entry.symbol, entry.direction,
        )

        return {
            "entry": _entry_to_dict(entry),
            "created": True,
        }


@router.put("/entries/{entry_id}")
async def update_journal_entry(entry_id: int, body: JournalEntryUpdate):
    """Update an existing trade journal entry. Only provided fields are updated."""
    async with async_session() as session:
        result = await session.execute(
            select(TradeJournalEntry).where(TradeJournalEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()

        if not entry:
            raise HTTPException(status_code=404, detail=f"Journal entry {entry_id} not found")

        update_data = body.model_dump(exclude_none=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        for key, value in update_data.items():
            setattr(entry, key, value)

        await session.commit()
        await session.refresh(entry)

        logger.info(
            "Trade journal entry updated: id=%d fields=%s",
            entry_id, list(update_data.keys()),
        )

        return {
            "entry": _entry_to_dict(entry),
            "updated_fields": list(update_data.keys()),
        }


@router.delete("/entries/{entry_id}")
async def delete_journal_entry(entry_id: int):
    """Delete a trade journal entry by ID."""
    async with async_session() as session:
        result = await session.execute(
            select(TradeJournalEntry).where(TradeJournalEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()

        if not entry:
            raise HTTPException(status_code=404, detail=f"Journal entry {entry_id} not found")

        await session.delete(entry)
        await session.commit()

        logger.info("Trade journal entry deleted: id=%d", entry_id)

        return {
            "deleted": True,
            "entry_id": entry_id,
        }
