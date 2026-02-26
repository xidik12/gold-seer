"""Gold analyst forecasts API."""
import logging
from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import select, desc

from app.database import async_session, GoldAnalystForecast

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysts", tags=["analysts"])


@router.get("/forecasts")
async def get_analyst_forecasts():
    """Get gold analyst forecasts with consensus target.

    Returns the latest 50 forecasts ordered by publication date,
    plus a consensus object computed as the average target price
    of the most recent forecast per institution.
    """
    async with async_session() as session:
        # Fetch latest 50 forecasts
        result = await session.execute(
            select(GoldAnalystForecast)
            .order_by(desc(GoldAnalystForecast.published_at))
            .limit(50)
        )
        forecasts = result.scalars().all()

        if not forecasts:
            return {
                "forecasts": [],
                "consensus": {
                    "target": None,
                    "direction": "neutral",
                    "count": 0,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Serialize forecasts
        forecast_list = [
            {
                "id": f.id,
                "institution": f.institution,
                "analyst_name": f.analyst_name,
                "target_price": f.target_price,
                "timeframe": f.timeframe,
                "direction": f.direction,
                "reasoning": f.reasoning,
                "published_at": f.published_at.isoformat() if f.published_at else None,
                "gold_price_at_forecast": f.gold_price_at_forecast,
                "was_accurate": f.was_accurate,
                "source_url": f.source_url,
            }
            for f in forecasts
        ]

        # Consensus: average target of the latest forecast per institution
        latest_per_institution: dict[str, GoldAnalystForecast] = {}
        for f in forecasts:
            if f.institution not in latest_per_institution:
                latest_per_institution[f.institution] = f

        targets = [
            f.target_price
            for f in latest_per_institution.values()
            if f.target_price is not None
        ]

        consensus_target = round(sum(targets) / len(targets), 2) if targets else None

        # Determine consensus direction from individual directions
        directions = [
            f.direction
            for f in latest_per_institution.values()
            if f.direction is not None
        ]
        bullish_count = sum(1 for d in directions if d.lower() in ("bullish", "buy", "long", "up"))
        bearish_count = sum(1 for d in directions if d.lower() in ("bearish", "sell", "short", "down"))

        if bullish_count > bearish_count:
            consensus_direction = "bullish"
        elif bearish_count > bullish_count:
            consensus_direction = "bearish"
        else:
            consensus_direction = "neutral"

        return {
            "forecasts": forecast_list,
            "consensus": {
                "target": consensus_target,
                "direction": consensus_direction,
                "count": len(latest_per_institution),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
