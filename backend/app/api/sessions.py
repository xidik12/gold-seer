"""Gold trading sessions API (Asian/London/NY)."""
from fastapi import APIRouter

from app.collectors.gold_price import GoldPriceCollector

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("/current")
async def get_current_sessions():
    collector = GoldPriceCollector()
    try:
        info = collector.get_session_info()
        return info
    finally:
        await collector.close()
