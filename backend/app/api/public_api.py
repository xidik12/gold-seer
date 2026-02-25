"""Public versioned API endpoints (/api/v1/).

Clean, documented endpoints for external consumers.
Auth handled by APIKeyMiddleware (when enabled).
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import (
    get_session, Price, Prediction, QuantPrediction,
    MacroData, ApiKey, ApiUsageLog,
)
# Power law model removed (crypto-specific) — gold uses simple fair value placeholder
def _gold_fair_value(dt):
    """Placeholder fair value model for gold."""
    return None

def _get_valuation_label(dev_pct):
    if dev_pct > 20: return "Overvalued"
    if dev_pct > 10: return "Above Fair Value"
    if dev_pct > -10: return "Fair Value"
    if dev_pct > -20: return "Below Fair Value"
    return "Undervalued"

# GLD ETF launch date (Nov 18, 2004) — used as the reference epoch for gold model
GLD_LAUNCH = datetime(2004, 11, 18)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["public-api-v1"])


# ── Price ──────────────────────────────────────────────────────

@router.get("/price")
async def get_price(session: AsyncSession = Depends(get_session)):
    """Get current gold price."""
    result = await session.execute(
        select(Price).order_by(desc(Price.timestamp)).limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        return {"error": "No price data available"}

    return {
        "price": row.close,
        "high_24h": row.high,
        "low_24h": row.low,
        "volume": row.volume,
        "timestamp": row.timestamp.isoformat(),
    }


@router.get("/price/history")
async def get_price_history(
    hours: int = Query(24, ge=1, le=720),
    session: AsyncSession = Depends(get_session),
):
    """Get historical gold prices."""
    since = datetime.utcnow() - timedelta(hours=hours)
    result = await session.execute(
        select(Price)
        .where(Price.timestamp >= since)
        .order_by(Price.timestamp)
    )
    prices = result.scalars().all()

    return {
        "count": len(prices),
        "prices": [
            {
                "timestamp": p.timestamp.isoformat(),
                "open": p.open,
                "high": p.high,
                "low": p.low,
                "close": p.close,
                "volume": p.volume,
            }
            for p in prices
        ],
    }


# ── Predictions ────────────────────────────────────────────────

@router.get("/predictions/current")
async def get_predictions(session: AsyncSession = Depends(get_session)):
    """Get current AI predictions for all timeframes."""
    result = await session.execute(
        select(Prediction)
        .order_by(desc(Prediction.timestamp))
        .limit(5)
    )
    predictions = result.scalars().all()

    return {
        "predictions": [
            {
                "timeframe": p.timeframe,
                "direction": p.direction,
                "confidence": p.confidence,
                "predicted_price": p.predicted_price,
                "predicted_change_pct": p.predicted_change_pct,
                "current_price": p.current_price,
                "timestamp": p.timestamp.isoformat(),
            }
            for p in predictions
        ],
    }


@router.get("/predictions/quant")
async def get_quant_prediction(session: AsyncSession = Depends(get_session)):
    """Get latest quant theory prediction."""
    result = await session.execute(
        select(QuantPrediction).order_by(desc(QuantPrediction.timestamp)).limit(1)
    )
    qp = result.scalar_one_or_none()
    if not qp:
        return {"prediction": None}

    return {
        "prediction": {
            "direction": qp.direction,
            "action": qp.action,
            "composite_score": qp.composite_score,
            "confidence": qp.confidence,
            "current_price": qp.current_price,
            "predictions": {
                "1h": {"predicted_price": qp.pred_1h_price, "predicted_change_pct": qp.pred_1h_change_pct},
                "4h": {"predicted_price": qp.pred_4h_price, "predicted_change_pct": qp.pred_4h_change_pct},
                "24h": {"predicted_price": qp.pred_24h_price, "predicted_change_pct": qp.pred_24h_change_pct},
                "1w": {"predicted_price": qp.pred_1w_price, "predicted_change_pct": qp.pred_1w_change_pct},
                "1mo": {"predicted_price": qp.pred_1mo_price, "predicted_change_pct": qp.pred_1mo_change_pct},
            },
            "active_signals": qp.active_signals,
            "bullish_signals": qp.bullish_signals,
            "bearish_signals": qp.bearish_signals,
            "agreement_ratio": qp.agreement_ratio,
            "timestamp": qp.timestamp.isoformat(),
        },
    }


# ── Market ─────────────────────────────────────────────────────

@router.get("/market/macro")
async def get_macro(session: AsyncSession = Depends(get_session)):
    """Get latest macro market data (DXY, Gold, S&P500, Fear & Greed)."""
    result = await session.execute(
        select(MacroData).order_by(desc(MacroData.timestamp)).limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        return {"error": "No macro data available"}

    return {
        "dxy": row.dxy,
        "gold": row.gold,
        "sp500": row.sp500,
        "treasury_10y": row.treasury_10y,
        "fear_greed_index": row.fear_greed_index,
        "fear_greed_label": row.fear_greed_label,
        "timestamp": row.timestamp.isoformat(),
    }


@router.get("/market/onchain")
async def get_onchain(session: AsyncSession = Depends(get_session)):
    """Get latest on-chain data — not available for gold trading."""
    return {"error": "On-chain data is not available for gold trading"}


# ── Power Law ──────────────────────────────────────────────────

@router.get("/powerlaw")
async def get_power_law(session: AsyncSession = Depends(get_session)):
    """Gold fair value model — placeholder (power law is BTC-specific)."""
    result = await session.execute(
        select(Price).order_by(desc(Price.timestamp)).limit(1)
    )
    price_row = result.scalar_one_or_none()
    current_price = price_row.close if price_row else None

    return {
        "current_price": current_price,
        "fair_value": None,
        "deviation_pct": 0,
        "valuation": "N/A",
        "corridor": {},
        "days_since_gld_launch": (datetime.utcnow() - GLD_LAUNCH).days,
        "timestamp": datetime.utcnow().isoformat(),
        "note": "Power law model is not applicable for gold. Use quant predictor instead.",
    }


# ── Usage ──────────────────────────────────────────────────────

@router.get("/usage")
async def get_usage(
    session: AsyncSession = Depends(get_session),
    request=None,
):
    """Get API usage stats for the current API key."""
    from fastapi import Request
    from starlette.requests import Request as StarletteRequest

    # Get API key ID from request state (set by middleware)
    api_key_id = getattr(getattr(request, 'state', None), 'api_key_id', None) if request else None

    if not api_key_id:
        return {"error": "API key required to view usage stats"}

    # Get key info
    result = await session.execute(
        select(ApiKey).where(ApiKey.id == api_key_id)
    )
    key = result.scalar_one_or_none()
    if not key:
        return {"error": "API key not found"}

    # Count usage in last hour and last 24h
    hour_ago = datetime.utcnow() - timedelta(hours=1)
    day_ago = datetime.utcnow() - timedelta(hours=24)

    from sqlalchemy import func
    result_1h = await session.execute(
        select(func.count(ApiUsageLog.id))
        .where(ApiUsageLog.api_key_id == api_key_id)
        .where(ApiUsageLog.timestamp >= hour_ago)
    )
    result_24h = await session.execute(
        select(func.count(ApiUsageLog.id))
        .where(ApiUsageLog.api_key_id == api_key_id)
        .where(ApiUsageLog.timestamp >= day_ago)
    )

    return {
        "tier": key.tier,
        "rate_limit": key.rate_limit,
        "requests_last_hour": result_1h.scalar() or 0,
        "requests_last_24h": result_24h.scalar() or 0,
        "is_active": key.is_active,
        "created_at": key.created_at.isoformat() if key.created_at else None,
        "expires_at": key.expires_at.isoformat() if key.expires_at else None,
    }
