"""COT (Commitments of Traders) data API."""
from fastapi import APIRouter
from sqlalchemy import select

from app.database import async_session, COTData

router = APIRouter(prefix="/api/cot", tags=["cot"])


def _row_to_dict(row: COTData) -> dict:
    return {c.name: getattr(row, c.name) for c in COTData.__table__.columns}


@router.get("/latest")
async def get_latest_cot():
    async with async_session() as session:
        # Latest single row for the 'latest' key
        latest_result = await session.execute(
            select(COTData).order_by(COTData.report_date.desc()).limit(1)
        )
        latest_row = latest_result.scalar_one_or_none()

        if not latest_row:
            return {"latest": None, "history": [], "message": "No COT data available yet"}

        latest = _row_to_dict(latest_row)

        # Add convenience alias: frontend accesses net_percentile OR mm_net_percentile
        latest["net_percentile"] = latest.get("mm_net_percentile")

        # History: last 20 weekly reports (newest first)
        history_result = await session.execute(
            select(COTData).order_by(COTData.report_date.desc()).limit(20)
        )
        history_rows = history_result.scalars().all()
        history = [_row_to_dict(r) for r in history_rows]
        for h in history:
            h["net_percentile"] = h.get("mm_net_percentile")

        return {
            "latest": latest,
            "history": history,
        }
