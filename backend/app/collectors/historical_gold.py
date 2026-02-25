"""Historical XAUUSD OHLCV data collector.

Backfills 5+ years of daily gold futures (GC=F) data from Yahoo Finance v8 chart API.
Used for training ML models and computing long-term technical indicators.
"""
import logging
from datetime import datetime, timezone

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


class HistoricalGoldCollector(BaseCollector):
    """Backfills 5+ years of daily XAUUSD OHLCV from Yahoo Finance."""

    YAHOO_CHART_URL = "https://query2.finance.yahoo.com/v8/finance/chart/GC=F"

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def collect(self) -> list[dict]:
        """Fetch 5 years of daily OHLCV for XAUUSD (GC=F).

        Returns:
            List of dicts with keys: timestamp, open, high, low, close, volume.
        """
        return await self._fetch_daily_history(range_str="5y", interval="1d")

    async def collect_range(self, range_str: str = "5y", interval: str = "1d") -> list[dict]:
        """Fetch historical OHLCV with custom range and interval.

        Args:
            range_str: Yahoo range string (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, max).
            interval: Candle interval (1m, 5m, 15m, 1h, 1d, 1wk, 1mo).

        Returns:
            List of OHLCV dicts.
        """
        return await self._fetch_daily_history(range_str=range_str, interval=interval)

    async def _fetch_daily_history(self, range_str: str, interval: str) -> list[dict]:
        """Internal method to fetch historical candles from Yahoo Finance v8."""
        try:
            data = await self.fetch_json(
                self.YAHOO_CHART_URL,
                params={"interval": interval, "range": range_str},
                headers=YAHOO_HEADERS,
            )
            if not data or "chart" not in data:
                logger.warning("Yahoo Finance returned empty response for historical data")
                return []

            results = data["chart"].get("result", [])
            if not results:
                logger.warning("Yahoo Finance chart result is empty")
                return []

            result = results[0]
            timestamps = result.get("timestamp", [])
            indicators = result.get("indicators", {})
            quotes = indicators.get("quote", [{}])
            quote = quotes[0] if quotes else {}

            opens = quote.get("open", [])
            highs = quote.get("high", [])
            lows = quote.get("low", [])
            closes = quote.get("close", [])
            volumes = quote.get("volume", [])

            candles = []
            for i, ts in enumerate(timestamps):
                # Skip candles with missing data
                o = opens[i] if i < len(opens) else None
                h = highs[i] if i < len(highs) else None
                lo = lows[i] if i < len(lows) else None
                c = closes[i] if i < len(closes) else None
                v = volumes[i] if i < len(volumes) else None

                if o is None or h is None or lo is None or c is None:
                    continue

                candles.append({
                    "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                    "open": float(o),
                    "high": float(h),
                    "low": float(lo),
                    "close": float(c),
                    "volume": int(v) if v is not None else 0,
                })

            logger.info(f"Fetched {len(candles)} historical gold candles ({range_str}/{interval})")
            return candles

        except Exception as e:
            logger.error(f"Historical gold data fetch error: {e}")
            return []
