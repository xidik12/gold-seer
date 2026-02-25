"""Gold ETF flows API."""
from fastapi import APIRouter
from sqlalchemy import select

from app.database import async_session, GoldETFFlow

router = APIRouter(prefix="/api/gold-etf", tags=["gold_etf"])


@router.get("/latest")
async def get_latest_etf():
    async with async_session() as session:
        result = await session.execute(
            select(GoldETFFlow).order_by(GoldETFFlow.date.desc()).limit(20)
        )
        rows = result.scalars().all()
        return {
            "flows": [
                {c.name: getattr(r, c.name) for c in GoldETFFlow.__table__.columns}
                for r in rows
            ]
        }
