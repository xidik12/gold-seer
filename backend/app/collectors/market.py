"""Gold market data collector — primary market data aggregator.

Replaces the original crypto/Binance MarketCollector with gold-specific sources.
Uses GoldPriceCollector for real-time XAUUSD price and Yahoo Finance for
historical klines (candlestick) data.

No Binance, no CoinGecko, no funding rates, no open interest, no dominance.
"""
import logging
from datetime import datetime, timezone

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.collectors.base import BaseCollector
from app.collectors.gold_price import GoldPriceCollector

logger = logging.getLogger(__name__)

YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# Yahoo Finance interval mapping
# Valid intervals: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
# Range constraints: 1m (max 7d), 5m (max 60d), 15m (max 60d), 1h (max 730d), 1d (max all)
YAHOO_INTERVAL_RANGE = {
    "1m": "1d",
    "5m": "5d",
    "15m": "5d",
    "30m": "5d",
    "1h": "30d",      # 168 candles = 7 days, but allow 30d for flexibility
    "1d": "1y",
    "1wk": "5y",
    "1mo": "10y",
}


class GoldMarketCollector(BaseCollector):
    """Collects gold market data from multiple sources.

    Primary collector for the Gold Seer platform. Aggregates real-time price
    data from GoldPriceCollector and historical candle data from Yahoo Finance.
    """

    YAHOO_CHART_URL = "https://query2.finance.yahoo.com/v8/finance/chart/GC=F"

    def __init__(self):
        super().__init__()
        self._price_collector = GoldPriceCollector()

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def collect(self) -> dict:
        """Collect current gold price and recent 1h candles.

        Returns:
            Dict with keys: price_data, klines, session_info, timestamp.
        """
        price_data = await self._price_collector.collect()
        klines = await self.get_klines(interval="1h", limit=168)  # 7 days

        return {
            "price_data": price_data,
            "klines": klines,
            "session_info": self._price_collector.get_session_info(),
            "timestamp": self.now().isoformat(),
        }

    async def get_current_price(self) -> float | None:
        """Get the current XAUUSD spot price."""
        return await self._price_collector.get_current_price()

    async def get_klines(self, interval: str = "1h", limit: int = 168) -> list[dict] | None:
        """Get historical klines (candlestick) data for GC=F.

        Args:
            interval: Candle interval (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo).
            limit: Maximum number of candles to return.

        Returns:
            List of OHLCV dicts or None on failure.
        """
        # Determine appropriate range for the interval
        range_str = YAHOO_INTERVAL_RANGE.get(interval, "30d")

        data = await self.fetch_json(
            self.YAHOO_CHART_URL,
            params={"interval": interval, "range": range_str},
            headers=YAHOO_HEADERS,
        )

        if not data or "chart" not in data:
            logger.warning(f"Yahoo Finance GC=F klines empty for {interval}")
            return None

        results = data["chart"].get("result", [])
        if not results:
            return None

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

        klines = []
        for i, ts in enumerate(timestamps):
            o = opens[i] if i < len(opens) else None
            h = highs[i] if i < len(highs) else None
            lo = lows[i] if i < len(lows) else None
            c = closes[i] if i < len(closes) else None
            v = volumes[i] if i < len(volumes) else None

            if o is None or h is None or lo is None or c is None:
                continue

            klines.append({
                "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                "open": float(o),
                "high": float(h),
                "low": float(lo),
                "close": float(c),
                "volume": int(v) if v is not None else 0,
            })

        # Trim to requested limit (Yahoo may return more than needed)
        if limit and len(klines) > limit:
            klines = klines[-limit:]

        return klines

    async def get_historical_klines(
        self,
        interval: str = "1h",
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 1000,
    ) -> list[dict] | None:
        """Get historical klines for training data.

        Args:
            interval: Candle interval.
            start_time: Unix timestamp (seconds) for range start.
            end_time: Unix timestamp (seconds) for range end.
            limit: Max candles to return.

        Returns:
            List of OHLCV dicts or None.
        """
        params = {"interval": interval}

        if start_time and end_time:
            params["period1"] = start_time
            params["period2"] = end_time
        else:
            # Use max range for the interval
            params["range"] = YAHOO_INTERVAL_RANGE.get(interval, "1y")

        data = await self.fetch_json(
            self.YAHOO_CHART_URL,
            params=params,
            headers=YAHOO_HEADERS,
        )

        if not data or "chart" not in data:
            return None

        results = data["chart"].get("result", [])
        if not results:
            return None

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

        klines = []
        for i, ts in enumerate(timestamps):
            o = opens[i] if i < len(opens) else None
            h = highs[i] if i < len(highs) else None
            lo = lows[i] if i < len(lows) else None
            c = closes[i] if i < len(closes) else None
            v = volumes[i] if i < len(volumes) else None

            if o is None or h is None or lo is None or c is None:
                continue

            klines.append({
                "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc),
                "open": float(o),
                "high": float(h),
                "low": float(lo),
                "close": float(c),
                "volume": int(v) if v is not None else 0,
            })

        if limit and len(klines) > limit:
            klines = klines[-limit:]

        return klines

    async def close(self):
        """Close both this collector and the internal GoldPriceCollector."""
        if self._price_collector:
            await self._price_collector.close()
        await super().close()
