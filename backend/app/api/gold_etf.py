"""Gold ETF flows API."""
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter
from sqlalchemy import select, desc

from app.database import async_session, GoldETFFlow, Price

logger = logging.getLogger(__name__)

# ── Simple TTL cache for ETF endpoints ──
_etf_cache: dict[str, tuple[dict, float]] = {}


def _get_etf_cached(key: str) -> dict | None:
    if key in _etf_cache:
        data, expires = _etf_cache[key]
        if time.monotonic() < expires:
            return data
        del _etf_cache[key]
    return None


def _set_etf_cache(key: str, data, ttl: int) -> None:
    _etf_cache[key] = (data, time.monotonic() + ttl)

router = APIRouter(prefix="/api/gold-etf", tags=["gold_etf"])


@router.get("/latest")
async def get_latest_etf():
    async with async_session() as session:
        # Fetch last 60 rows (up to 15 dates × 4 tickers)
        result = await session.execute(
            select(GoldETFFlow).order_by(GoldETFFlow.date.desc()).limit(60)
        )
        rows = result.scalars().all()

        if not rows:
            return {
                "etfs": [],
                "daily_flows": [],
                "holdings_trend": [],
                "flow_vs_price": [],
            }

        # All rows as plain dicts
        raw = [
            {
                "id": r.id,
                "date": r.date,
                "ticker": r.ticker,
                "holdings_tonnes": r.holdings_tonnes,
                "holdings_usd": r.holdings_usd,
                "daily_change_tonnes": r.daily_change_tonnes,
                "daily_change_usd": r.daily_change_usd,
                "volume": r.volume,
                "price": r.price,
            }
            for r in rows
        ]

        # ── etfs: latest record per ticker ────────────────────────────────
        latest_by_ticker: dict[str, dict] = {}
        for r in raw:
            ticker = r["ticker"]
            if ticker not in latest_by_ticker:
                latest_by_ticker[ticker] = r

        etfs = []
        for ticker, r in latest_by_ticker.items():
            holdings = r["holdings_tonnes"] or 0.0
            daily_flow = r["daily_change_tonnes"] or 0.0
            # Sum all historical flows for net_flow
            net_flow = sum(
                (x["daily_change_tonnes"] or 0.0)
                for x in raw
                if x["ticker"] == ticker
            )
            aum = r["holdings_usd"] or 0.0
            etfs.append({
                "ticker": ticker,
                "holdings": holdings,
                "daily_flow": daily_flow,
                "net_flow": round(net_flow, 4),
                "aum": aum,
            })

        # Sort by AUM descending
        etfs.sort(key=lambda x: x["aum"], reverse=True)

        # ── daily_flows: aggregate all tickers by date ─────────────────────
        flow_by_date: dict[str, float] = defaultdict(float)
        for r in raw:
            flow_by_date[r["date"]] += r["daily_change_tonnes"] or 0.0

        daily_flows = sorted(
            [{"date": d, "flow": round(v, 4)} for d, v in flow_by_date.items()],
            key=lambda x: x["date"],
        )

        # ── holdings_trend: total holdings across all tickers by date ──────
        holdings_by_date: dict[str, float] = defaultdict(float)
        for r in raw:
            holdings_by_date[r["date"]] += r["holdings_tonnes"] or 0.0

        holdings_trend = sorted(
            [{"date": d, "holdings": round(v, 4)} for d, v in holdings_by_date.items()],
            key=lambda x: x["date"],
        )

        # ── flow_vs_price: join with gold prices ───────────────────────────
        # Collect the dates we have flow data for
        all_dates = sorted(flow_by_date.keys())
        price_by_date: dict[str, float | None] = {d: None for d in all_dates}

        try:
            # Try to get gold close prices for these dates from Price table
            # Price.timestamp is a DateTime — we compare by date string prefix
            price_result = await session.execute(
                select(Price).order_by(Price.timestamp.asc())
            )
            price_rows = price_result.scalars().all()
            for pr in price_rows:
                d = pr.timestamp.strftime("%Y-%m-%d")
                if d in price_by_date:
                    price_by_date[d] = pr.close
        except Exception as e:
            logger.warning(f"Could not fetch price data for flow_vs_price: {e}")

        flow_vs_price = [
            {
                "date": d,
                "flow": round(flow_by_date[d], 4),
                "price": price_by_date.get(d),
            }
            for d in all_dates
        ]

        return {
            "etfs": etfs,
            "daily_flows": daily_flows,
            "holdings_trend": holdings_trend,
            "flow_vs_price": flow_vs_price,
        }


@router.get("/momentum")
async def get_etf_momentum():
    """Get enhanced ETF flow momentum analysis.

    Computes 30-day cumulative flow, 5-day momentum, and a directional signal.
    Signals:
    - STRONG_INFLOW: 5d momentum > +5 tonnes
    - INFLOW: 5d momentum > +1 tonne
    - OUTFLOW: 5d momentum < -1 tonne
    - STRONG_OUTFLOW: 5d momentum < -5 tonnes
    - NEUTRAL: otherwise
    """
    cached = _get_etf_cached("etf_momentum")
    if cached is not None:
        return cached

    async with async_session() as session:
        # Query last 30 days of GoldETFFlow data
        cutoff_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")

        result = await session.execute(
            select(GoldETFFlow)
            .where(GoldETFFlow.date >= cutoff_date)
            .order_by(GoldETFFlow.date.asc())
        )
        rows = result.scalars().all()

        if not rows:
            return {
                "momentum_5d": 0,
                "cumulative_30d": 0,
                "signal": "NEUTRAL",
                "daily_flows": [],
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Aggregate daily flows across all tickers by date
        flow_by_date: dict[str, float] = defaultdict(float)
        for r in rows:
            flow_by_date[r.date] += r.daily_change_tonnes or 0.0

        # Sorted daily flows
        sorted_dates = sorted(flow_by_date.keys())
        daily_flows = [
            {"date": d, "flow": round(flow_by_date[d], 4)}
            for d in sorted_dates
        ]

        # 30-day cumulative flow
        cumulative_30d = sum(flow_by_date[d] for d in sorted_dates)

        # 5-day momentum (sum of last 5 days of flows)
        last_5_dates = sorted_dates[-5:] if len(sorted_dates) >= 5 else sorted_dates
        momentum_5d = sum(flow_by_date[d] for d in last_5_dates)

        # Classify signal based on 5-day momentum (in tonnes)
        if momentum_5d > 5.0:
            signal = "STRONG_INFLOW"
        elif momentum_5d > 1.0:
            signal = "INFLOW"
        elif momentum_5d < -5.0:
            signal = "STRONG_OUTFLOW"
        elif momentum_5d < -1.0:
            signal = "OUTFLOW"
        else:
            signal = "NEUTRAL"

        data = {
            "momentum_5d": round(momentum_5d, 4),
            "cumulative_30d": round(cumulative_30d, 4),
            "signal": signal,
            "daily_flows": daily_flows,
            "timestamp": datetime.utcnow().isoformat(),
        }
        _set_etf_cache("etf_momentum", data, 300)
        return data
