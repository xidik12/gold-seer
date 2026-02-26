"""Gold trading sessions API (Asian/London/NY)."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.database import async_session, GoldSessionData, Price

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# Session definitions (UTC hours, inclusive open / exclusive close)
SESSION_DEFS = {
    "asian":    {"label": "Asian (Tokyo)",  "open": 0,  "close": 9},
    "london":   {"label": "London",         "open": 8,  "close": 17},
    "new_york": {"label": "New York",       "open": 13, "close": 22},
}


def _compute_session_status(session_key: str, utc_hour: int) -> str:
    """Return 'active', 'closed', or 'upcoming' for a given UTC hour."""
    s = SESSION_DEFS[session_key]
    if s["open"] <= utc_hour < s["close"]:
        return "active"
    # Determine the closest future open to decide 'upcoming'
    minutes_until_open = (s["open"] - utc_hour) % 24
    if minutes_until_open <= 4:  # opens within 4 hours
        return "upcoming"
    return "closed"


@router.get("/current")
async def get_current_sessions():
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    utc_hour = now.hour

    # Determine overall market open status
    weekday = now.weekday()  # 0=Mon, 6=Sun
    market_open = True
    if weekday == 5:   # Saturday
        market_open = False
    elif weekday == 6:  # Sunday
        market_open = False
    elif weekday == 4 and utc_hour >= 22:  # Friday after 22:00
        market_open = False

    # Try to fetch latest OHLCV from DB for each session
    session_ohlcv: dict[str, dict | None] = {k: None for k in SESSION_DEFS}
    latest_price: float | None = None

    try:
        async with async_session() as db:
            # Fetch latest price for stats
            price_result = await db.execute(
                select(Price).order_by(Price.timestamp.desc()).limit(1)
            )
            price_row = price_result.scalar_one_or_none()
            if price_row:
                latest_price = price_row.close

            # Fetch today's session OHLCV rows
            sd_result = await db.execute(
                select(GoldSessionData)
                .where(GoldSessionData.date == today_str)
            )
            sd_rows = sd_result.scalars().all()
            for row in sd_rows:
                session_ohlcv[row.session_name] = {
                    "open": row.open_price,
                    "high": row.high_price,
                    "low": row.low_price,
                    "close": row.close_price,
                    "volume": row.volume,
                    "range_usd": row.range_usd,
                    "direction": row.direction,
                }
    except Exception as e:
        logger.warning(f"Could not fetch session OHLCV from DB: {e}")

    # Build per-session objects
    active_count = 0
    sessions_out: dict[str, dict] = {}
    for key, defn in SESSION_DEFS.items():
        status = _compute_session_status(key, utc_hour) if market_open else "closed"
        if status == "active":
            active_count += 1

        ohlcv = session_ohlcv.get(key) or {}
        sessions_out[key] = {
            "label": defn["label"],
            "open_hour": defn["open"],
            "close_hour": defn["close"],
            "status": status,
            "is_active": status == "active",
            "ohlcv": {
                "open": ohlcv.get("open"),
                "high": ohlcv.get("high"),
                "low": ohlcv.get("low"),
                "close": ohlcv.get("close"),
                "volume": ohlcv.get("volume"),
                "range_usd": ohlcv.get("range_usd"),
                "direction": ohlcv.get("direction"),
            },
        }

    stats = {
        "market_open": market_open,
        "active_sessions": active_count,
        "current_utc": now.isoformat(),
        "current_price": latest_price,
    }

    return {
        "sessions": sessions_out,
        "stats": stats,
    }
