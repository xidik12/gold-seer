"""COT (Commitments of Traders) data API."""
from fastapi import APIRouter
from sqlalchemy import select

from app.database import async_session, COTData

router = APIRouter(prefix="/api/cot", tags=["cot"])


@router.get("/latest")
async def get_latest_cot():
    async with async_session() as session:
        result = await session.execute(
            select(COTData).order_by(COTData.report_date.desc()).limit(1)
        )
        row = result.scalar_one_or_none()
        if not row:
            return {"message": "No COT data available yet"}
        return {c.name: getattr(row, c.name) for c in COTData.__table__.columns}
