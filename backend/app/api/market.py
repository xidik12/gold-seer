import logging
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import func as sa_func

from app.database import get_session, Price, MacroData, IndicatorSnapshot, CentralBankGold
from app.collectors.market import GoldMarketCollector as MarketCollector
from app.collectors.macro import MacroCollector

logger = logging.getLogger(__name__)

# ── Simple TTL cache for expensive endpoints ──
_cache: dict[str, tuple[dict, float]] = {}


def _get_cached(key: str) -> dict | None:
    if key in _cache:
        data, expires = _cache[key]
        if time.monotonic() < expires:
            return data
        del _cache[key]
    return None


def _set_cache(key: str, data, ttl: int) -> None:
    _cache[key] = (data, time.monotonic() + ttl)


async def _get_macro_trio(session: AsyncSession):
    """Fetch latest, 1h-ago, and 24h-ago MacroData rows with shared cache."""
    cached = _get_cached("_macro_trio")
    if cached is not None:
        return cached

    result = await session.execute(
        select(MacroData).order_by(desc(MacroData.timestamp)).limit(1)
    )
    macro = result.scalar_one_or_none()
    if not macro:
        return None, None, None

    prev_result = await session.execute(
        select(MacroData)
        .where(MacroData.timestamp <= macro.timestamp - timedelta(minutes=50))
        .order_by(desc(MacroData.timestamp))
        .limit(1)
    )
    prev_macro = prev_result.scalar_one_or_none()

    daily_result = await session.execute(
        select(MacroData)
        .where(MacroData.timestamp <= macro.timestamp - timedelta(hours=23))
        .order_by(desc(MacroData.timestamp))
        .limit(1)
    )
    daily_macro = daily_result.scalar_one_or_none()

    _set_cache("_macro_trio", (macro, prev_macro, daily_macro), 120)
    return macro, prev_macro, daily_macro


router = APIRouter(prefix="/api/market", tags=["market"])

# Shared collectors for live API fallback
_market_collector = MarketCollector()
_macro_collector = MacroCollector()

# Minimum candles needed per timeframe to consider local data sufficient
_MIN_CANDLES = {"1m": 2, "5m": 2, "15m": 2, "1h": 5, "4h": 5, "1d": 10, "1w": 20, "1mo": 20, "1y": 50, "all": 50}

# Yahoo Finance interval + limit for each timeframe (used as API fallback)
_API_FALLBACK = {
    "1d": ("1h", 24),
    "1w": ("1h", 168),
    "1mo": ("4h", 180),
    "1y": ("1d", 365),
    "all": ("1d", 1000),
}


@router.get("/price")
async def get_current_price(session: AsyncSession = Depends(get_session)):
    """Get latest gold price data."""
    result = await session.execute(
        select(Price).order_by(desc(Price.timestamp)).limit(1)
    )
    price = result.scalar_one_or_none()

    if not price:
        return {"price": None, "message": "No price data available"}

    # Get 24h ago price for change calculation
    yesterday = price.timestamp - timedelta(hours=24)
    result_24h = await session.execute(
        select(Price)
        .where(Price.timestamp <= yesterday)
        .order_by(desc(Price.timestamp))
        .limit(1)
    )
    price_24h = result_24h.scalar_one_or_none()

    change_24h = None
    change_24h_pct = None
    if price_24h and price_24h.close:
        change_24h = price.close - price_24h.close
        change_24h_pct = (change_24h / price_24h.close) * 100

    return {
        "price": price.close,
        "open": price.open,
        "high": price.high,
        "low": price.low,
        "volume": price.volume,
        "change_24h": round(change_24h, 2) if change_24h is not None else None,
        "change_24h_pct": round(change_24h_pct, 2) if change_24h_pct is not None else None,
        "timestamp": price.timestamp.isoformat(),
    }


@router.get("/stats")
async def get_price_stats(
    timeframe: str = Query("1d", pattern="^(1m|5m|15m|1h|4h|1d|1w|1mo|1y|all)$"),
    session: AsyncSession = Depends(get_session),
):
    """Get price statistics for a specific timeframe.

    Timeframes: 1m, 5m, 15m, 1h, 4h, 1d (day), 1w (week), 1mo (month), 1y (year), all (lifetime)
    """
    cached = _get_cached(f"stats:{timeframe}")
    if cached is not None:
        return cached

    # Map timeframe to timedelta
    timeframe_map = {
        "1m": timedelta(minutes=1),
        "5m": timedelta(minutes=5),
        "15m": timedelta(minutes=15),
        "1h": timedelta(hours=1),
        "4h": timedelta(hours=4),
        "1d": timedelta(days=1),
        "1w": timedelta(weeks=1),
        "1mo": timedelta(days=30),
        "1y": timedelta(days=365),
        "all": None,  # All time
    }

    # Get current price
    result_current = await session.execute(
        select(Price).order_by(desc(Price.timestamp)).limit(1)
    )
    current = result_current.scalar_one_or_none()

    if not current:
        return {"error": "No price data available"}

    # Get historical data for timeframe
    delta = timeframe_map[timeframe]
    if delta:
        since = current.timestamp - delta
        result_historical = await session.execute(
            select(Price)
            .where(Price.timestamp >= since)
            .order_by(Price.timestamp)
        )
    else:
        # All time — cap at 8640 rows (6 days of 1-min candles) to avoid unbounded scan
        result_historical = await session.execute(
            select(Price).order_by(desc(Price.timestamp)).limit(8640)
        )

    prices = result_historical.scalars().all()

    # "all" query uses DESC+LIMIT, reverse to ascending order for downstream code
    if not delta and prices:
        prices = list(reversed(prices))

    min_needed = _MIN_CANDLES.get(timeframe, 5)

    # Fallback to Yahoo Finance API if local data is insufficient
    if len(prices) < min_needed and timeframe in _API_FALLBACK:
        logger.info(f"Stats: Local data insufficient ({len(prices)} candles) for {timeframe}, fetching from Yahoo Finance")
        try:
            api_interval, api_limit = _API_FALLBACK[timeframe]
            klines = await _market_collector.get_historical_klines(
                interval=api_interval, limit=api_limit
            )
            if klines and len(klines) > min_needed:
                current_price = current.close
                first_k = klines[0]
                open_price = first_k["open"]
                high_price = max(k["high"] for k in klines)
                low_price = min(k["low"] for k in klines)
                total_volume = sum(k["volume"] for k in klines)
                last_k = klines[-1]

                price_change = last_k["close"] - open_price
                price_change_pct = (price_change / open_price * 100) if open_price else 0

                max_candles = 500
                step = max(1, len(klines) // max_candles)
                candles = [
                    {
                        "timestamp": k["timestamp"].isoformat() if hasattr(k["timestamp"], "isoformat") else str(k["timestamp"]),
                        "open": k["open"],
                        "high": k["high"],
                        "low": k["low"],
                        "close": k["close"],
                        "volume": k["volume"],
                    }
                    for k in klines[::step]
                ]

                result = {
                    "timeframe": timeframe,
                    "current_price": current_price,
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "volume": total_volume,
                    "change": round(price_change, 2),
                    "change_pct": round(price_change_pct, 2),
                    "num_candles": len(klines),
                    "candles": candles,
                    "timestamp": current.timestamp.isoformat(),
                    "period_start": candles[0]["timestamp"],
                    "period_end": candles[-1]["timestamp"],
                    "source": "yahoo_finance_api",
                }
                _set_cache(f"stats:{timeframe}", result, 30)
                return result
        except Exception as e:
            logger.warning(f"Yahoo Finance fallback failed: {e}")

    if not prices:
        return {"error": "No historical data available"}

    # Calculate stats from local DB data
    first_price = prices[0]
    current_price = current.close
    open_price = first_price.close
    high_price = max(p.high for p in prices)
    low_price = min(p.low for p in prices)
    total_volume = sum(p.volume for p in prices)

    price_change = current_price - open_price
    price_change_pct = (price_change / open_price * 100) if open_price else 0

    # Get candle data for chart (limit to reasonable number of points)
    max_candles = 1000
    step = max(1, len(prices) // max_candles)
    candles = [
        {
            "timestamp": p.timestamp.isoformat(),
            "open": p.open,
            "high": p.high,
            "low": p.low,
            "close": p.close,
            "volume": p.volume,
        }
        for p in prices[::step]
    ]

    result = {
        "timeframe": timeframe,
        "current_price": current_price,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "volume": total_volume,
        "change": round(price_change, 2),
        "change_pct": round(price_change_pct, 2),
        "num_candles": len(prices),
        "candles": candles,
        "timestamp": current.timestamp.isoformat(),
        "period_start": first_price.timestamp.isoformat(),
        "period_end": current.timestamp.isoformat(),
    }
    _set_cache(f"stats:{timeframe}", result, 30)
    return result


@router.get("/indicators")
async def get_indicators(
    session: AsyncSession = Depends(get_session),
):
    """Get current technical indicators calculated from recent price data."""
    cached = _get_cached("indicators")
    if cached is not None:
        return cached

    import pandas as pd
    from app.features.technical import TechnicalFeatures

    # Need at least 350 candles for long SMAs
    since = datetime.utcnow() - timedelta(hours=400)
    result = await session.execute(
        select(Price).where(Price.timestamp >= since).order_by(Price.timestamp)
    )
    prices = result.scalars().all()

    if len(prices) < 30:
        return {"error": "Not enough price data for indicators", "candle_count": len(prices)}

    df = pd.DataFrame([
        {"open": p.open, "high": p.high, "low": p.low, "close": p.close, "volume": p.volume}
        for p in prices
    ])

    import asyncio
    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(None, TechnicalFeatures.calculate_all, df)

    # Get latest row
    latest = df.iloc[-1]

    def safe(val):
        if pd.isna(val):
            return None
        return round(float(val), 4)

    current_price = safe(latest["close"])

    # Gold market context placeholder
    gold_market_ctx = None

    result = {
        "timestamp": prices[-1].timestamp.isoformat(),
        "current_price": current_price,
        "candle_count": len(prices),
        "gold_market_context": gold_market_ctx,
        "moving_averages": {
            "ema_9": safe(latest.get("ema_9")),
            "ema_21": safe(latest.get("ema_21")),
            "ema_50": safe(latest.get("ema_50")),
            "ema_200": safe(latest.get("ema_200")),
            "sma_20": safe(latest.get("sma_20")),
            "sma_111": safe(latest.get("sma_111")),
            "sma_200": safe(latest.get("sma_200")),
            "sma_350": safe(latest.get("sma_350")),
        },
        "momentum": {
            "rsi": safe(latest.get("rsi")),
            "rsi_7": safe(latest.get("rsi_7")),
            "rsi_30": safe(latest.get("rsi_30")),
            "macd": safe(latest.get("macd")),
            "macd_signal": safe(latest.get("macd_signal")),
            "macd_histogram": safe(latest.get("macd_hist")),
            "adx": safe(latest.get("adx")),
            "momentum_10": safe(latest.get("momentum_10")),
            "momentum_20": safe(latest.get("momentum_20")),
            "roc_1": safe(latest.get("roc_1")),
            "roc_6": safe(latest.get("roc_6")),
            "roc_12": safe(latest.get("roc_12")),
            "roc_24": safe(latest.get("roc_24")),
        },
        "volatility": {
            "bb_upper": safe(latest.get("bb_upper")),
            "bb_middle": safe(latest.get("bb_middle")),
            "bb_lower": safe(latest.get("bb_lower")),
            "bb_width": safe(latest.get("bb_width")),
            "bb_position": safe(latest.get("bb_position")),
            "atr": safe(latest.get("atr")),
            "volatility_24h": safe(latest.get("volatility_24h")),
        },
        "volume": {
            "obv": safe(latest.get("obv")),
            "vwap": safe(latest.get("vwap")),
            "volume_sma_20": safe(latest.get("volume_sma_20")),
            "volume_ratio": safe(latest.get("volume_ratio")),
        },
        "levels": {
            "pivot": safe(latest.get("pivot")),
            "support_1": safe(latest.get("support_1")),
            "resistance_1": safe(latest.get("resistance_1")),
        },
        "advanced": {
            "mayer_multiple": safe(latest.get("mayer_multiple")),
            "pi_cycle_ratio": safe(latest.get("pi_cycle_ratio")),
            "ema_cross": safe(latest.get("ema_cross")),
            "zscore_20": safe(latest.get("zscore_20")),
            "price_vs_ema9": safe(latest.get("price_vs_ema9")),
            "price_vs_ema21": safe(latest.get("price_vs_ema21")),
            "price_vs_ema50": safe(latest.get("price_vs_ema50")),
        },
        "candle": {
            "body_size": safe(latest.get("body_size")),
            "upper_shadow": safe(latest.get("upper_shadow")),
            "lower_shadow": safe(latest.get("lower_shadow")),
        },
        "stochastic_rsi": {
            "k": safe(latest.get("stoch_rsi_k")),
            "d": safe(latest.get("stoch_rsi_d")),
        },
        "williams_r": safe(latest.get("williams_r")),
        "ichimoku": {
            "tenkan": safe(latest.get("ichimoku_tenkan")),
            "kijun": safe(latest.get("ichimoku_kijun")),
            "senkou_a": safe(latest.get("ichimoku_senkou_a")),
            "senkou_b": safe(latest.get("ichimoku_senkou_b")),
        },
        "candlestick_patterns": {
            "doji": int(latest.get("candle_doji", 0)),
            "hammer": int(latest.get("candle_hammer", 0)),
            "inverted_hammer": int(latest.get("candle_inverted_hammer", 0)),
            "bullish_engulfing": int(latest.get("candle_bullish_engulfing", 0)),
            "bearish_engulfing": int(latest.get("candle_bearish_engulfing", 0)),
            "morning_star": int(latest.get("candle_morning_star", 0)),
            "evening_star": int(latest.get("candle_evening_star", 0)),
        },
        "trend": {
            "short_term": int(latest.get("trend_short", 0)),
            "medium_term": int(latest.get("trend_medium", 0)),
            "long_term": int(latest.get("trend_long", 0)),
        },
    }
    _set_cache("indicators", result, 60)
    return result


@router.get("/candles")
async def get_candles(
    hours: int = Query(168, ge=1, le=720),
    session: AsyncSession = Depends(get_session),
):
    """Get historical candle data with automatic downsampling."""
    cached = _get_cached(f"candles:{hours}")
    if cached is not None:
        return cached

    since = datetime.utcnow() - timedelta(hours=hours)

    result = await session.execute(
        select(Price)
        .where(Price.timestamp >= since)
        .order_by(Price.timestamp)
    )
    prices = result.scalars().all()

    # Downsample to max 500 candles to keep response fast
    max_candles = 500
    step = max(1, len(prices) // max_candles)
    candles = [
        {
            "timestamp": p.timestamp.isoformat(),
            "open": p.open,
            "high": p.high,
            "low": p.low,
            "close": p.close,
            "volume": p.volume,
        }
        for p in prices[::step]
    ]

    result_data = {
        "count": len(candles),
        "total_raw": len(prices),
        "candles": candles,
    }
    _set_cache(f"candles:{hours}", result_data, 60)
    return result_data


def build_macro_item(current_val, prev_val, daily_val):
    """Build macro item with price and change data."""
    if current_val is None:
        return None
    item = {"price": current_val}
    if prev_val and prev_val > 0:
        item["change_1h"] = round((current_val - prev_val) / prev_val * 100, 4)
    if daily_val and daily_val > 0:
        item["change_24h"] = round((current_val - daily_val) / daily_val * 100, 4)
    return item


@router.get("/macro")
async def get_macro_data(session: AsyncSession = Depends(get_session)):
    """Get latest macro market data with price changes."""
    cached = _get_cached("macro")
    if cached is not None:
        return cached

    try:
        macro, prev_macro, daily_macro = await _get_macro_trio(session)
    except Exception as e:
        logger.warning(f"Macro DB query failed: {e}")
        macro = None

    if not macro:
        # Live fallback: fetch directly from APIs when DB is empty
        try:
            live = await _macro_collector.collect()
            return {
                "dxy": live.get("dxy"),
                "gold": live.get("gold"),
                "sp500": live.get("sp500"),
                "treasury_10y": live.get("treasury_10y"),
                "nasdaq": live.get("nasdaq"),
                "vix": live.get("vix"),
                "eurusd": live.get("eurusd"),
                "fear_greed_index": None,
                "fear_greed_label": None,
                "timestamp": live.get("timestamp"),
            }
        except Exception as e:
            logger.warning(f"Live macro fallback failed: {e}")
            return {
                "dxy": None, "gold": None, "sp500": None, "treasury_10y": None,
                "nasdaq": None, "vix": None, "eurusd": None,
                "fear_greed_index": None, "fear_greed_label": None, "timestamp": None,
            }

    # Build all macro items using getattr for dynamic key access
    all_macro_keys = [
        "dxy", "gold", "sp500", "treasury_10y", "nasdaq", "vix", "eurusd",
        "gbpusd", "usdjpy", "usdchf", "audusd", "usdcad", "nzdusd",
        "wti_oil", "silver", "copper", "natural_gas", "platinum", "palladium",
        "dow_jones", "russell_2000", "dax", "nikkei_225", "ftse_100",
        "treasury_2y", "treasury_5y", "treasury_30y",
    ]
    result = {}
    for key in all_macro_keys:
        result[key] = build_macro_item(
            getattr(macro, key, None),
            getattr(prev_macro, key, None) if prev_macro else None,
            getattr(daily_macro, key, None) if daily_macro else None,
        )
    result["fear_greed_index"] = macro.fear_greed_index
    result["fear_greed_label"] = macro.fear_greed_label
    result["timestamp"] = macro.timestamp.isoformat()

    _set_cache("macro", result, 300)
    return result


@router.get("/fear-greed")
async def get_fear_greed(
    session: AsyncSession = Depends(get_session),
):
    """Gold composite sentiment index (0-100). Replaces crypto Fear & Greed.

    Factors:
    - VIX: High VIX = safe-haven demand = gold bullish (weight: 30%)
    - Real Yield: Negative real yield = inflation fear = gold bullish (weight: 30%)
    - DXY Strength: Weak dollar = gold bullish (weight: 20%)
    - Gold Momentum: Recent price trend (weight: 20%)
    """
    cached = _get_cached("fear_greed_gold")
    if cached is not None:
        return cached

    try:
        macro, prev_macro, daily_macro = await _get_macro_trio(session)
    except Exception:
        macro = None

    # Default neutral
    score = 50
    components = {}

    if macro:
        total_weight = 0
        weighted_score = 0

        # VIX component (30%): High VIX = fear in equities = gold bullish
        if macro.vix is not None:
            vix = macro.vix
            if vix >= 35:
                vix_score = 85  # Extreme fear in equities -> strong gold demand
            elif vix >= 25:
                vix_score = 70
            elif vix >= 18:
                vix_score = 50
            elif vix >= 12:
                vix_score = 30
            else:
                vix_score = 15  # Extreme complacency -> less gold demand
            components["vix"] = {"value": vix, "score": vix_score, "weight": 30}
            weighted_score += vix_score * 30
            total_weight += 30

        # Real Yield component (30%): Negative real yield = gold bullish
        real_yield = getattr(macro, 'real_yield_10y', None)
        if real_yield is None and macro.treasury_10y is not None:
            # Approximate: 10Y nominal - assumed 2.5% inflation
            real_yield = macro.treasury_10y - 2.5
        if real_yield is not None:
            if real_yield < -1.0:
                ry_score = 90  # Deeply negative = very gold bullish
            elif real_yield < 0:
                ry_score = 70
            elif real_yield < 1.0:
                ry_score = 50
            elif real_yield < 2.0:
                ry_score = 30
            else:
                ry_score = 10  # High real yields = gold bearish
            components["real_yield"] = {"value": round(real_yield, 2), "score": ry_score, "weight": 30}
            weighted_score += ry_score * 30
            total_weight += 30

        # DXY component (20%): Weak dollar = gold bullish
        if macro.dxy is not None and daily_macro and daily_macro.dxy:
            dxy_change = ((macro.dxy - daily_macro.dxy) / daily_macro.dxy) * 100
            if dxy_change < -0.5:
                dxy_score = 80  # Dollar weakening -> gold bullish
            elif dxy_change < -0.1:
                dxy_score = 65
            elif dxy_change < 0.1:
                dxy_score = 50
            elif dxy_change < 0.5:
                dxy_score = 35
            else:
                dxy_score = 20  # Dollar strengthening -> gold bearish
            components["dxy"] = {"value": round(macro.dxy, 2), "change_24h": round(dxy_change, 2), "score": dxy_score, "weight": 20}
            weighted_score += dxy_score * 20
            total_weight += 20

        # Gold Momentum (20%): Recent price trend
        if macro.gold is not None and daily_macro and daily_macro.gold:
            gold_change = ((macro.gold - daily_macro.gold) / daily_macro.gold) * 100
            if gold_change > 2.0:
                mom_score = 90  # Strong rally
            elif gold_change > 0.5:
                mom_score = 70
            elif gold_change > -0.5:
                mom_score = 50
            elif gold_change > -2.0:
                mom_score = 30
            else:
                mom_score = 10  # Sharp selloff
            components["momentum"] = {"value": round(macro.gold, 2), "change_24h": round(gold_change, 2), "score": mom_score, "weight": 20}
            weighted_score += mom_score * 20
            total_weight += 20

        if total_weight > 0:
            score = round(weighted_score / total_weight)

    # Label
    if score >= 80:
        label = "Extreme Greed"
    elif score >= 60:
        label = "Greed"
    elif score >= 40:
        label = "Neutral"
    elif score >= 20:
        label = "Fear"
    else:
        label = "Extreme Fear"

    result = {
        "current": {
            "value": score,
            "label": label,
            "timestamp": int(datetime.utcnow().timestamp()),
        },
        "components": components,
        "source": "gold_composite",
        "history": [],  # TODO: store historical values
    }
    _set_cache("fear_greed_gold", result, 300)
    return result


@router.get("/indicator-history")
async def get_indicator_history(
    hours: int = Query(168, ge=1, le=720),
    session: AsyncSession = Depends(get_session),
):
    """Get historical indicator snapshots for trend analysis."""
    cached = _get_cached(f"indicator_history:{hours}")
    if cached is not None:
        return cached

    since = datetime.utcnow() - timedelta(hours=hours)

    result = await session.execute(
        select(IndicatorSnapshot)
        .where(IndicatorSnapshot.timestamp >= since)
        .order_by(IndicatorSnapshot.timestamp)
    )
    snapshots = result.scalars().all()

    if not snapshots:
        return {"snapshots": [], "count": 0}

    data = {
        "snapshots": [
            {
                "timestamp": s.timestamp.isoformat(),
                "price": s.price,
                "indicators": s.indicators,
            }
            for s in snapshots
        ],
        "count": len(snapshots),
    }
    _set_cache(f"indicator_history:{hours}", data, 300)
    return data


@router.get("/supply")
async def get_gold_supply():
    """Get gold supply data: above-ground stock, annual mine production, central bank reserves."""
    cached = _get_cached("supply")
    if cached is not None:
        return cached

    # World Gold Council estimates (updated annually)
    TOTAL_ABOVE_GROUND = 212_582  # tonnes (WGC 2024 estimate)
    ANNUAL_MINE_PRODUCTION = 3_644  # tonnes per year
    CENTRAL_BANK_RESERVES = 36_699  # tonnes held by central banks
    ANNUAL_GROWTH_PCT = 1.7  # supply growth rate

    result = {
        "total_above_ground_tonnes": TOTAL_ABOVE_GROUND,
        "annual_mine_production_tonnes": ANNUAL_MINE_PRODUCTION,
        "annual_growth_pct": ANNUAL_GROWTH_PCT,
        "central_bank_reserves_tonnes": CENTRAL_BANK_RESERVES,
        "central_bank_pct": round(CENTRAL_BANK_RESERVES / TOTAL_ABOVE_GROUND * 100, 1),
        "supply_breakdown": {
            "jewellery": {"tonnes": 95_547, "pct": 44.9},
            "investment": {"tonnes": 47_435, "pct": 22.3},
            "central_banks": {"tonnes": CENTRAL_BANK_RESERVES, "pct": 17.3},
            "technology": {"tonnes": 29_808, "pct": 14.0},
            "other": {"tonnes": 3_093, "pct": 1.5},
        },
        "top_producers": [
            {"country": "China", "tonnes_annual": 370},
            {"country": "Australia", "tonnes_annual": 310},
            {"country": "Russia", "tonnes_annual": 310},
            {"country": "Canada", "tonnes_annual": 200},
            {"country": "USA", "tonnes_annual": 170},
        ],
        "top_central_bank_holders": [
            {"country": "USA", "tonnes": 8_133},
            {"country": "Germany", "tonnes": 3_352},
            {"country": "Italy", "tonnes": 2_452},
            {"country": "France", "tonnes": 2_437},
            {"country": "Russia", "tonnes": 2_333},
            {"country": "China", "tonnes": 2_264},
        ],
        "source": "World Gold Council 2024",
    }
    _set_cache("supply", result, 600)
    return result


# ── New TradingView-style endpoints ──

NEW_MACRO_KEYS = [
    "gbpusd", "usdjpy", "usdchf", "audusd", "usdcad", "nzdusd",
    "wti_oil", "silver", "copper", "natural_gas",
    "dow_jones", "russell_2000", "dax", "nikkei_225", "ftse_100",
    "treasury_2y", "treasury_5y", "treasury_30y",
]


@router.get("/forex")
async def get_forex_data(session: AsyncSession = Depends(get_session)):
    """Get forex pairs with price and changes."""
    cached = _get_cached("forex")
    if cached is not None:
        return cached

    forex_keys = ["eurusd", "gbpusd", "usdjpy", "usdchf", "audusd", "usdcad", "nzdusd"]

    macro, prev_macro, daily_macro = await _get_macro_trio(session)
    if not macro:
        return {k: None for k in forex_keys}

    data = {}
    for key in forex_keys:
        data[key] = build_macro_item(
            getattr(macro, key, None),
            getattr(prev_macro, key, None) if prev_macro else None,
            getattr(daily_macro, key, None) if daily_macro else None,
        )

    data["timestamp"] = macro.timestamp.isoformat()
    _set_cache("forex", data, 300)
    return data


@router.get("/commodities")
async def get_commodities_data(session: AsyncSession = Depends(get_session)):
    """Get commodities with price and changes."""
    cached = _get_cached("commodities")
    if cached is not None:
        return cached

    commodity_keys = ["gold", "wti_oil", "silver", "copper", "natural_gas", "platinum", "palladium"]

    macro, prev_macro, daily_macro = await _get_macro_trio(session)
    if not macro:
        return {k: None for k in commodity_keys}

    data = {}
    for key in commodity_keys:
        data[key] = build_macro_item(
            getattr(macro, key, None),
            getattr(prev_macro, key, None) if prev_macro else None,
            getattr(daily_macro, key, None) if daily_macro else None,
        )

    data["timestamp"] = macro.timestamp.isoformat()
    _set_cache("commodities", data, 300)
    return data


@router.get("/yields")
async def get_yield_curve(session: AsyncSession = Depends(get_session)):
    """Get treasury yield curve (2Y, 5Y, 10Y, 30Y) with 30-day history."""
    cached = _get_cached("yields")
    if cached is not None:
        return cached

    yield_keys = ["treasury_2y", "treasury_5y", "treasury_10y", "treasury_30y"]

    macro, _, _ = await _get_macro_trio(session)

    current = {}
    if macro:
        for key in yield_keys:
            val = getattr(macro, key, None)
            current[key] = val

    # 30-day history for chart
    history_result = await session.execute(
        select(MacroData)
        .where(MacroData.timestamp >= datetime.utcnow() - timedelta(days=30))
        .order_by(MacroData.timestamp)
    )
    history_rows = history_result.scalars().all()

    history = []
    for row in history_rows:
        entry = {"timestamp": row.timestamp.isoformat()}
        for key in yield_keys:
            entry[key] = getattr(row, key, None)
        history.append(entry)

    # Inversion detection
    t2y = current.get("treasury_2y")
    t10y = current.get("treasury_10y")
    inverted = t2y is not None and t10y is not None and t2y > t10y

    data = {
        "current": current,
        "inverted": inverted,
        "history": history,
        "timestamp": macro.timestamp.isoformat() if macro else None,
    }
    _set_cache("yields", data, 300)
    return data


@router.get("/ta-summary")
async def get_ta_summary(session: AsyncSession = Depends(get_session)):
    """Get TradingView-style TA summary rating."""
    cached = _get_cached("ta_summary")
    if cached is not None:
        return cached

    from app.features.ta_summary import TASummaryRating

    # Reuse the indicators endpoint logic internally
    try:
        indicators = await get_indicators(session)
    except Exception as e:
        logger.error(f"TA summary indicator fetch error: {e}")
        return {"error": "Failed to compute TA summary"}

    result = TASummaryRating.compute(indicators)
    _set_cache("ta_summary", result, 60)
    return result


@router.get("/silver")
async def get_silver_data(session: AsyncSession = Depends(get_session)):
    """Get current silver price, 24h change, and gold/silver ratio."""
    cached = _get_cached("silver")
    if cached is not None:
        return cached

    try:
        macro, prev_macro, daily_macro = await _get_macro_trio(session)
    except Exception as e:
        logger.warning(f"Silver data query failed: {e}")
        macro = None

    if not macro or macro.silver is None:
        return {
            "silver_price": None,
            "change_24h": None,
            "change_24h_pct": None,
            "gold_price": None,
            "gold_silver_ratio": None,
            "ratio_signal": None,
            "ratio_interpretation": None,
            "timestamp": None,
        }

    silver_price = macro.silver
    gold_price = macro.gold

    # 24h change
    change_24h = None
    change_24h_pct = None
    if daily_macro and daily_macro.silver and daily_macro.silver > 0:
        change_24h = round(silver_price - daily_macro.silver, 4)
        change_24h_pct = round((change_24h / daily_macro.silver) * 100, 2)

    # Gold/Silver ratio
    ratio = None
    if gold_price and silver_price and silver_price > 0:
        ratio = round(gold_price / silver_price, 2)

    # 24h ratio change
    ratio_prev = None
    ratio_change = None
    if daily_macro and daily_macro.gold and daily_macro.silver and daily_macro.silver > 0:
        ratio_prev = round(daily_macro.gold / daily_macro.silver, 2)
        if ratio is not None:
            ratio_change = round(ratio - ratio_prev, 2)

    # Signal interpretation based on historical gold/silver ratio
    # Historical range: ~15 (all-time low) to ~130 (2020 peak), average ~65
    ratio_signal = "neutral"
    ratio_interpretation = "Gold/silver ratio is within normal range"
    if ratio is not None:
        if ratio > 90:
            ratio_signal = "silver_very_undervalued"
            ratio_interpretation = "Extreme ratio — silver is historically very undervalued vs gold. Mean-reversion favors silver."
        elif ratio > 80:
            ratio_signal = "silver_undervalued"
            ratio_interpretation = "High ratio — silver appears undervalued relative to gold. Historically tends to revert."
        elif ratio > 70:
            ratio_signal = "slightly_high"
            ratio_interpretation = "Ratio above average — slight silver undervaluation signal."
        elif ratio > 55:
            ratio_signal = "neutral"
            ratio_interpretation = "Gold/silver ratio near historical average (~65). No strong directional signal."
        elif ratio > 50:
            ratio_signal = "slightly_low"
            ratio_interpretation = "Ratio below average — slight silver overvaluation signal."
        else:
            ratio_signal = "silver_overvalued"
            ratio_interpretation = "Low ratio — silver is relatively expensive vs gold. Could mean-revert downward."

    result = {
        "silver_price": silver_price,
        "change_24h": change_24h,
        "change_24h_pct": change_24h_pct,
        "gold_price": gold_price,
        "gold_silver_ratio": ratio,
        "ratio_change_24h": ratio_change,
        "ratio_signal": ratio_signal,
        "ratio_interpretation": ratio_interpretation,
        "timestamp": macro.timestamp.isoformat(),
    }
    _set_cache("silver", result, 120)
    return result


@router.get("/correlations")
async def get_correlations(session: AsyncSession = Depends(get_session)):
    """Get rolling 30-day correlations between gold and key macro variables."""
    cached = _get_cached("correlations")
    if cached is not None:
        return cached

    import numpy as np

    # Get 30 days of macro data
    result = await session.execute(
        select(MacroData)
        .where(MacroData.timestamp >= datetime.utcnow() - timedelta(days=30))
        .order_by(MacroData.timestamp)
    )
    rows = result.scalars().all()

    if len(rows) < 10:
        return {"error": "Not enough macro data for correlation analysis", "count": len(rows)}

    def _corr(gold_vals, other_vals):
        """Compute Pearson correlation between two series, ignoring None pairs."""
        pairs = [(g, o) for g, o in zip(gold_vals, other_vals) if g is not None and o is not None]
        if len(pairs) < 5:
            return None
        g = np.array([p[0] for p in pairs])
        o = np.array([p[1] for p in pairs])
        if np.std(g) == 0 or np.std(o) == 0:
            return None
        return float(np.corrcoef(g, o)[0, 1])

    def _label(corr):
        if corr is None:
            return "insufficient_data"
        if corr > 0.7:
            return "strong_positive"
        if corr > 0.3:
            return "moderate_positive"
        if corr > -0.3:
            return "weak"
        if corr > -0.7:
            return "moderate_negative"
        return "strong_negative"

    gold_prices = [r.gold for r in rows]

    pairs = {
        "dxy": {"values": [r.dxy for r in rows], "expected": "inverse"},
        "treasury_10y": {"values": [r.treasury_10y for r in rows], "expected": "inverse"},
        "vix": {"values": [r.vix for r in rows], "expected": "positive"},
        "silver": {"values": [r.silver for r in rows], "expected": "positive"},
        "sp500": {"values": [r.sp500 for r in rows], "expected": "weak"},
    }

    correlations = {}
    for key, info in pairs.items():
        corr = _corr(gold_prices, info["values"])
        correlations[key] = {
            "correlation": round(corr, 3) if corr is not None else None,
            "label": _label(corr),
            "expected_direction": info["expected"],
            "data_points": sum(1 for g, o in zip(gold_prices, info["values"]) if g is not None and o is not None),
        }

    data = {
        "correlations": correlations,
        "period_days": 30,
        "total_data_points": len(rows),
        "timestamp": rows[-1].timestamp.isoformat() if rows else None,
    }
    _set_cache("correlations", data, 300)
    return data


@router.get("/central-bank")
async def get_central_bank_data(session: AsyncSession = Depends(get_session)):
    """Get central bank gold purchase data: net purchases, trend, history, top buyers."""
    cached = _get_cached("central_bank")
    if cached is not None:
        return cached

    # Last 12 months of CentralBankGold data
    twelve_months_ago = datetime.utcnow() - timedelta(days=365)

    result = await session.execute(
        select(CentralBankGold)
        .where(CentralBankGold.report_date >= twelve_months_ago)
        .order_by(CentralBankGold.report_date)
    )
    rows = result.scalars().all()

    if not rows:
        return {
            "cb_net_purchases": 0,
            "cb_trend": "neutral",
            "cb_history": [],
            "top_buyers": [],
            "timestamp": datetime.utcnow().isoformat(),
        }

    # Net purchases: sum of monthly_change_tonnes
    cb_net_purchases = sum(
        r.monthly_change_tonnes for r in rows if r.monthly_change_tonnes is not None
    )

    # Trend from last 3 months of aggregated monthly changes
    three_months_ago = datetime.utcnow() - timedelta(days=90)
    recent_rows = [r for r in rows if r.report_date >= three_months_ago]
    recent_net = sum(
        r.monthly_change_tonnes for r in recent_rows if r.monthly_change_tonnes is not None
    )
    if recent_net > 5:
        cb_trend = "buying"
    elif recent_net < -5:
        cb_trend = "selling"
    else:
        cb_trend = "neutral"

    # History: aggregate monthly_change_tonnes by month for sparkline
    monthly_agg: dict[str, float] = {}
    for r in rows:
        month_key = r.report_date.strftime("%Y-%m")
        if r.monthly_change_tonnes is not None:
            monthly_agg[month_key] = monthly_agg.get(month_key, 0) + r.monthly_change_tonnes
    cb_history = [
        {"date": k, "value": round(v, 2)} for k, v in sorted(monthly_agg.items())
    ]

    # Top buyers: top 5 countries by total_tonnes (latest record per country)
    country_latest: dict[str, float] = {}
    for r in rows:
        if r.total_tonnes is not None:
            # Keep the latest record per country (rows are ordered by date)
            country_latest[r.country] = r.total_tonnes
    top_buyers = sorted(
        [{"country": c, "total_tonnes": round(t, 2)} for c, t in country_latest.items()],
        key=lambda x: x["total_tonnes"],
        reverse=True,
    )[:5]

    data = {
        "cb_net_purchases": round(cb_net_purchases, 2),
        "cb_trend": cb_trend,
        "cb_history": cb_history,
        "top_buyers": top_buyers,
        "timestamp": rows[-1].report_date.isoformat() if rows else datetime.utcnow().isoformat(),
    }
    _set_cache("central_bank", data, 600)
    return data


@router.get("/forward-curve")
async def get_forward_curve():
    """Get gold futures forward curve from CME via Yahoo Finance.

    Fetches GC=F (front month) and further-dated contracts to determine
    contango/backwardation and the term structure of gold futures.
    """
    cached = _get_cached("forward_curve")
    if cached is not None:
        return cached

    import aiohttp
    import ssl
    import certifi

    ssl_ctx = ssl.create_default_context(cafile=certifi.where())

    # CME gold futures tickers on Yahoo Finance
    contracts = [
        {"ticker": "GC=F", "label": "Front Month", "expiry_approx": "2026-04"},
        {"ticker": "GCJ26.CMX", "label": "Apr 2026", "expiry_approx": "2026-04"},
        {"ticker": "GCK26.CMX", "label": "May 2026", "expiry_approx": "2026-05"},
        {"ticker": "GCM26.CMX", "label": "Jun 2026", "expiry_approx": "2026-06"},
        {"ticker": "GCQ26.CMX", "label": "Aug 2026", "expiry_approx": "2026-08"},
        {"ticker": "GCZ26.CMX", "label": "Dec 2026", "expiry_approx": "2026-12"},
        {"ticker": "GCG27.CMX", "label": "Feb 2027", "expiry_approx": "2027-02"},
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }

    async def _fetch_yahoo_v8_price(session: aiohttp.ClientSession, symbol: str) -> float | None:
        """Fetch price for a single ticker via Yahoo v8 chart API."""
        try:
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {"interval": "1d", "range": "2d"}
            async with session.get(url, params=params, headers=headers, ssl=ssl_ctx, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if data and "chart" in data:
                    results = data["chart"].get("result", [])
                    if results:
                        meta = results[0].get("meta", {})
                        price = meta.get("regularMarketPrice")
                        if price:
                            return float(price)
        except Exception as e:
            logger.debug(f"Forward curve: Failed to fetch {symbol}: {e}")
        return None

    spot_price = None
    forwards = []

    try:
        connector = aiohttp.TCPConnector(ssl=ssl_ctx)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Fetch spot (front month) first
            spot_price = await _fetch_yahoo_v8_price(session, "GC=F")

            if spot_price is None:
                return {"error": "Could not fetch gold spot price", "timestamp": datetime.utcnow().isoformat()}

            # Fetch each forward contract
            for contract in contracts:
                price = await _fetch_yahoo_v8_price(session, contract["ticker"])
                if price is not None:
                    forwards.append({
                        "contract": contract["label"],
                        "ticker": contract["ticker"],
                        "price": round(price, 2),
                        "expiry_approx": contract["expiry_approx"],
                    })

    except Exception as e:
        logger.warning(f"Forward curve fetch error: {e}")

    # If we got no forward data, synthesize from spot with typical forward points
    if len(forwards) <= 1 and spot_price:
        # Typical gold contango: ~0.3-0.5% per month (storage + interest carry)
        synthetic_months = [
            ("Apr 2026", "2026-04", 0),
            ("May 2026", "2026-05", 1),
            ("Jun 2026", "2026-06", 2),
            ("Aug 2026", "2026-08", 4),
            ("Dec 2026", "2026-12", 8),
            ("Feb 2027", "2027-02", 10),
        ]
        forwards = []
        for label, expiry, months_out in synthetic_months:
            fwd_price = round(spot_price * (1 + 0.004 * months_out), 2)
            forwards.append({
                "contract": label,
                "ticker": "synthetic",
                "price": fwd_price,
                "expiry_approx": expiry,
            })

    # Determine curve shape
    curve_shape = "flat"
    spread_pct = 0.0
    if forwards and spot_price:
        farthest_price = forwards[-1]["price"]
        if farthest_price > spot_price * 1.001:
            curve_shape = "contango"
        elif farthest_price < spot_price * 0.999:
            curve_shape = "backwardation"
        spread_pct = round(((farthest_price - spot_price) / spot_price) * 100, 3)

    result = {
        "spot": round(spot_price, 2) if spot_price else None,
        "forwards": forwards,
        "curve_shape": curve_shape,
        "spread_pct": spread_pct,
        "timestamp": datetime.utcnow().isoformat(),
    }
    _set_cache("forward_curve", result, 300)  # 5 min TTL
    return result


# ── Macro Regime Detector ──────────────────────────────────────────

# Historical average gold returns by regime (annualized %, approximate)
_REGIME_GOLD_RETURNS = {
    "RISK_OFF": 12.5,       # Flight to safety benefits gold
    "RISK_ON": -2.0,        # Risk appetite reduces gold demand
    "STAGFLATION": 18.0,    # Inflation + stagnation = gold's best environment
    "DEFLATION": 3.0,       # Mild positive — safe haven but deflationary pressure
    "REFLATION": 8.0,       # Central bank easing supports gold
    "NEUTRAL": 5.0,         # Long-term average gold return
}

_REGIME_DESCRIPTIONS = {
    "RISK_OFF": "Elevated volatility with weakening dollar. Flight to safety favors gold as a hedge.",
    "RISK_ON": "Low volatility and rising equities. Risk appetite reduces demand for safe havens like gold.",
    "STAGFLATION": "Rising inflation amid slowing growth. Historically gold's strongest environment.",
    "DEFLATION": "Falling prices and declining yields. Gold acts as a store of value but faces headwinds from deflation.",
    "REFLATION": "Moderate volatility with gold outperforming. Central banks likely easing, supporting gold.",
    "NEUTRAL": "No strong macro signal. Gold tracking long-term average returns.",
}


@router.get("/regime")
async def get_macro_regime(session: AsyncSession = Depends(get_session)):
    """Classify the current macro regime and its implications for gold.

    Regimes:
    - RISK_OFF: VIX > 25 AND DXY dropping
    - RISK_ON: VIX < 15 AND SP500 rising
    - STAGFLATION: CPI rising AND GDP slowing
    - DEFLATION: CPI falling AND yields falling
    - REFLATION: VIX 15-25 AND gold rising
    - NEUTRAL: Default
    """
    cached = _get_cached("macro_regime")
    if cached is not None:
        return cached

    try:
        macro, prev_macro, daily_macro = await _get_macro_trio(session)
    except Exception as e:
        logger.warning(f"Regime: macro query failed: {e}")
        macro = None

    if not macro:
        return {
            "regime": "NEUTRAL",
            "confidence": 0,
            "description": _REGIME_DESCRIPTIONS["NEUTRAL"],
            "gold_historical_avg_return": _REGIME_GOLD_RETURNS["NEUTRAL"],
            "components": {"vix": None, "dxy": None, "cpi": None, "real_yield": None},
            "timestamp": datetime.utcnow().isoformat(),
        }

    # Extract component values
    vix = macro.vix
    dxy = getattr(macro, "dxy", None)
    dxy_prev = getattr(daily_macro, "dxy", None) if daily_macro else None
    sp500 = getattr(macro, "sp500", None)
    sp500_prev = getattr(daily_macro, "sp500", None) if daily_macro else None
    gold = getattr(macro, "gold", None)
    gold_prev = getattr(daily_macro, "gold", None) if daily_macro else None
    cpi = getattr(macro, "cpi_yoy", None)
    real_yield = getattr(macro, "real_yield_10y", None)
    treasury_10y = macro.treasury_10y
    treasury_10y_prev = getattr(daily_macro, "treasury_10y", None) if daily_macro else None

    # Compute directional changes
    dxy_dropping = False
    if dxy is not None and dxy_prev is not None and dxy_prev > 0:
        dxy_change_pct = ((dxy - dxy_prev) / dxy_prev) * 100
        dxy_dropping = dxy_change_pct < -0.1

    sp500_rising = False
    if sp500 is not None and sp500_prev is not None and sp500_prev > 0:
        sp500_change_pct = ((sp500 - sp500_prev) / sp500_prev) * 100
        sp500_rising = sp500_change_pct > 0.1

    gold_rising = False
    if gold is not None and gold_prev is not None and gold_prev > 0:
        gold_change_pct = ((gold - gold_prev) / gold_prev) * 100
        gold_rising = gold_change_pct > 0.1

    yields_falling = False
    if treasury_10y is not None and treasury_10y_prev is not None:
        yields_falling = treasury_10y < treasury_10y_prev - 0.02

    # CPI signals
    cpi_rising = cpi is not None and cpi > 3.0
    cpi_falling = cpi is not None and cpi < 2.0

    # GDP slowing proxy: SP500 declining as proxy for growth slowdown
    gdp_slowing = False
    if sp500 is not None and sp500_prev is not None and sp500_prev > 0:
        gdp_slowing = ((sp500 - sp500_prev) / sp500_prev) * 100 < -0.5

    # Classify regime with confidence scoring
    regime = "NEUTRAL"
    confidence = 30  # Base confidence

    if vix is not None and vix > 25 and dxy_dropping:
        regime = "RISK_OFF"
        confidence = min(90, 50 + int((vix - 25) * 3))
    elif vix is not None and vix < 15 and sp500_rising:
        regime = "RISK_ON"
        confidence = min(85, 50 + int((15 - vix) * 5))
    elif cpi_rising and gdp_slowing:
        regime = "STAGFLATION"
        confidence = 65 if cpi is not None and cpi > 4.0 else 50
    elif cpi_falling and yields_falling:
        regime = "DEFLATION"
        confidence = 55
    elif vix is not None and 15 <= vix <= 25 and gold_rising:
        regime = "REFLATION"
        confidence = 55

    # Build component snapshot
    components = {
        "vix": round(vix, 2) if vix is not None else None,
        "dxy": round(dxy, 2) if dxy is not None else None,
        "cpi": round(cpi, 2) if cpi is not None else None,
        "real_yield": round(real_yield, 4) if real_yield is not None else None,
    }

    data = {
        "regime": regime,
        "confidence": confidence,
        "description": _REGIME_DESCRIPTIONS[regime],
        "gold_historical_avg_return": _REGIME_GOLD_RETURNS[regime],
        "components": components,
        "timestamp": macro.timestamp.isoformat(),
    }
    _set_cache("macro_regime", data, 300)
    return data


# ── Gold Miners Endpoint ──────────────────────────────────────────

@router.get("/miners")
async def get_gold_miners():
    """Get gold miner stocks with prices, changes, and GDX/GLD ratio (leading indicator)."""
    cached = _get_cached("gold_miners")
    if cached is not None:
        return cached

    from app.collectors.gold_miners import GoldMinersCollector

    collector = GoldMinersCollector()
    try:
        data = await collector.collect()
    except Exception as e:
        logger.error(f"Gold miners collector error: {e}")
        return {
            "miners": [],
            "gdx_gld_ratio": None,
            "gld_price": None,
            "ratio_signal": "unknown",
            "timestamp": datetime.utcnow().isoformat(),
        }
    finally:
        await collector.close()

    _set_cache("gold_miners", data, 120)
    return data


# ── Intraday Heatmap Endpoint ─────────────────────────────────────

@router.get("/intraday-patterns")
async def get_intraday_patterns(session: AsyncSession = Depends(get_session)):
    """Get 24x7 intraday return heatmap from last 30 days of hourly data.

    Returns average return, positive rate, and trade count for each
    (hour_of_day, day_of_week) combination.
    """
    cached = _get_cached("intraday_patterns")
    if cached is not None:
        return cached

    since = datetime.utcnow() - timedelta(days=30)

    result = await session.execute(
        select(Price)
        .where(Price.timestamp >= since)
        .order_by(Price.timestamp)
    )
    prices = result.scalars().all()

    if len(prices) < 50:
        return {
            "heatmap": [],
            "timestamp": datetime.utcnow().isoformat(),
            "error": "Not enough data for intraday patterns",
            "candle_count": len(prices),
        }

    # Compute return vs previous candle
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    # Accumulator: (hour, day_of_week) -> list of returns
    from collections import defaultdict
    buckets: dict[tuple[int, int], list[float]] = defaultdict(list)

    for i in range(1, len(prices)):
        prev_close = prices[i - 1].close
        curr_close = prices[i].close
        if prev_close and prev_close > 0 and curr_close:
            ret = ((curr_close - prev_close) / prev_close) * 100
            hour = prices[i].timestamp.hour
            dow = prices[i].timestamp.weekday()  # 0=Monday
            buckets[(hour, dow)].append(ret)

    # Build heatmap
    heatmap = []
    for key in sorted(buckets.keys(), key=lambda k: (k[1], k[0])):
        hour, dow = key
        rets = buckets[key]
        if not rets:
            continue
        avg_return = sum(rets) / len(rets)
        positive_count = sum(1 for r in rets if r > 0)
        positive_rate = positive_count / len(rets)

        # Standard deviation
        mean = avg_return
        variance = sum((r - mean) ** 2 for r in rets) / len(rets) if len(rets) > 1 else 0
        std_dev = variance ** 0.5

        heatmap.append({
            "hour": hour,
            "day_of_week": dow,
            "day_name": day_names[dow],
            "avg_return": round(avg_return, 6),
            "std_dev": round(std_dev, 6),
            "positive_rate": round(positive_rate, 4),
            "trade_count": len(rets),
        })

    # Sort by day then hour
    heatmap.sort(key=lambda x: (x["day_of_week"], x["hour"]))

    data = {
        "heatmap": heatmap,
        "timestamp": datetime.utcnow().isoformat(),
        "period_days": 30,
        "total_candles": len(prices),
    }
    _set_cache("intraday_patterns", data, 300)
    return data


# ── Physical Gold Premium (SGE) Endpoint ──────────────────────────

@router.get("/physical-premium")
async def get_physical_premium():
    """Get estimated SGE physical gold premium over spot.

    Uses CNY/USD rate to estimate the Shanghai Gold Exchange premium.
    Signal: GREEN (<2%), YELLOW (2-4%), RED (>4%).
    """
    cached = _get_cached("physical_premium")
    if cached is not None:
        return cached

    from app.collectors.physical_premium import PhysicalPremiumCollector

    collector = PhysicalPremiumCollector()
    try:
        data = await collector.collect()
    except Exception as e:
        logger.error(f"Physical premium collector error: {e}")
        return {
            "spot_usd": None,
            "cny_usd_rate": None,
            "estimated_sge_premium_pct": None,
            "signal": "unknown",
            "timestamp": datetime.utcnow().isoformat(),
        }
    finally:
        await collector.close()

    _set_cache("physical_premium", data, 300)
    return data