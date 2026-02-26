"""Gold ETF flows API."""
import logging
from collections import defaultdict

from fastapi import APIRouter
from sqlalchemy import select

from app.database import async_session, GoldETFFlow, Price

logger = logging.getLogger(__name__)

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
