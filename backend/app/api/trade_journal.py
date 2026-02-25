"""Trade journal entries API."""
from fastapi import APIRouter
from sqlalchemy import select

from app.database import async_session, TradeJournalEntry

router = APIRouter(prefix="/api/trade-journal", tags=["trade_journal"])


@router.get("/entries")
async def get_journal_entries():
    async with async_session() as session:
        result = await session.execute(
            select(TradeJournalEntry)
            .order_by(TradeJournalEntry.created_at.desc())
            .limit(50)
        )
        entries = result.scalars().all()
        return {
            "entries": [
                {c.name: getattr(e, c.name) for c in TradeJournalEntry.__table__.columns}
                for e in entries
            ]
        }
