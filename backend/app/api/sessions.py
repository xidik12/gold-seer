"""Gold trading sessions API (Asian/London/NY)."""
import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.collectors.gold_price import GoldPriceCollector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("/current")
async def get_current_sessions():
    collector = GoldPriceCollector()
    try:
        info = collector.get_session_info()
        return info
    except Exception as e:
        logger.error(f"Failed to get session info: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to retrieve session data", "detail": str(e)},
        )
    finally:
        await collector.close()
