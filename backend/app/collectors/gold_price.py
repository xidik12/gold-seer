"""Primary XAUUSD price collector with multi-source fallback.

Sources (in priority order):
1. GoldAPI.io — real-time spot price with session metadata
2. Alpha Vantage — CURRENCY_EXCHANGE_RATE (XAU/USD)
3. Yahoo Finance — GC=F via v8 chart API
"""
import logging
from datetime import datetime, timezone

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)

# Gold market hours (forex-style, nearly 24/5):
#   Open:  Sunday 22:00 UTC  →  Friday 22:00 UTC
#   For simplicity: Mon 00:00 UTC – Fri 22:00 UTC
# Trading sessions (UTC):
#   Asian:  00:00 – 09:00
#   London: 07:00 – 16:00
#   New York: 13:00 – 22:00

SESSIONS = [
    {"name": "asian", "start_hour": 0, "end_hour": 9},
    {"name": "london", "start_hour": 7, "end_hour": 16},
    {"name": "new_york", "start_hour": 13, "end_hour": 22},
]

YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


class GoldPriceCollector(BaseCollector):
    """Collects real-time XAUUSD price from multiple sources with session awareness."""

    GOLDAPI_URL = "https://www.goldapi.io/api/XAU/USD"
    ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
    YAHOO_CHART_URL = "https://query2.finance.yahoo.com/v8/finance/chart/GC=F"

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def collect(self) -> dict:
        """Collect current XAUUSD price with fallback across 3 sources."""
        result = {
            "price": None,
            "open": None,
            "high": None,
            "low": None,
            "close": None,
            "volume": None,
            "change_24h": None,
            "timestamp": self.now().isoformat(),
            "source": None,
            "session_info": self.get_session_info(),
        }

        # Source 1: GoldAPI.io
        goldapi_data = await self._fetch_goldapi()
        if goldapi_data:
            result.update(goldapi_data)
            result["source"] = "goldapi"
            return result

        # Source 2: Alpha Vantage
        av_data = await self._fetch_alpha_vantage()
        if av_data:
            result.update(av_data)
            result["source"] = "alpha_vantage"
            return result

        # Source 3: Yahoo Finance
        yf_data = await self._fetch_yahoo()
        if yf_data:
            result.update(yf_data)
            result["source"] = "yahoo_finance"
            return result

        logger.warning("All XAUUSD price sources failed")
        return result

    async def get_current_price(self) -> float | None:
        """Get the current gold spot price (USD per troy ounce)."""
        data = await self.collect()
        return data.get("price")

    def get_session_info(self) -> dict:
        """Determine current trading session and market open/closed status.

        Returns:
            dict with keys: active_sessions (list), market_open (bool), current_utc (str)
        """
        now = datetime.now(timezone.utc)
        weekday = now.weekday()  # 0=Mon, 6=Sun
        hour = now.hour

        # Market closed on Saturday (5) and Sunday (6)
        # Friday market closes at 22:00 UTC
        market_open = True
        if weekday == 5:  # Saturday
            market_open = False
        elif weekday == 6:  # Sunday
            market_open = False
        elif weekday == 4 and hour >= 22:  # Friday after 22:00
            market_open = False

        active_sessions = []
        if market_open:
            for session in SESSIONS:
                if session["start_hour"] <= hour < session["end_hour"]:
                    active_sessions.append(session["name"])

        return {
            "active_sessions": active_sessions,
            "market_open": market_open,
            "current_utc": now.isoformat(),
        }

    # ------------------------------------------------------------------
    # Private source methods
    # ------------------------------------------------------------------

    async def _fetch_goldapi(self) -> dict | None:
        """Fetch from GoldAPI.io (requires API key)."""
        if not settings.goldapi_key:
            logger.debug("GoldAPI key not set, skipping")
            return None

        try:
            data = await self.fetch_json(
                self.GOLDAPI_URL,
                headers={"x-access-token": settings.goldapi_key, "Content-Type": "application/json"},
            )
            if not data or "price" not in data:
                return None

            return {
                "price": float(data["price"]),
                "open": float(data.get("open_price", 0) or 0),
                "high": float(data.get("high_price", 0) or 0),
                "low": float(data.get("low_price", 0) or 0),
                "close": float(data["price"]),
                "volume": None,  # GoldAPI does not provide volume
                "change_24h": float(data.get("ch", 0) or 0),
            }
        except Exception as e:
            logger.warning(f"GoldAPI fetch error: {e}")
            return None

    async def _fetch_alpha_vantage(self) -> dict | None:
        """Fetch from Alpha Vantage CURRENCY_EXCHANGE_RATE."""
        if not settings.alpha_vantage_api_key:
            logger.debug("Alpha Vantage API key not set, skipping")
            return None

        try:
            data = await self.fetch_json(
                self.ALPHA_VANTAGE_URL,
                params={
                    "function": "CURRENCY_EXCHANGE_RATE",
                    "from_currency": "XAU",
                    "to_currency": "USD",
                    "apikey": settings.alpha_vantage_api_key,
                },
            )
            if not data:
                return None

            rate_data = data.get("Realtime Currency Exchange Rate")
            if not rate_data:
                return None

            price = float(rate_data.get("5. Exchange Rate", 0))
            bid = float(rate_data.get("8. Bid Price", 0) or 0)
            ask = float(rate_data.get("9. Ask Price", 0) or 0)

            if price <= 0:
                return None

            return {
                "price": price,
                "open": None,
                "high": ask if ask > 0 else None,
                "low": bid if bid > 0 else None,
                "close": price,
                "volume": None,
                "change_24h": None,
            }
        except Exception as e:
            logger.warning(f"Alpha Vantage XAU/USD error: {e}")
            return None

    async def _fetch_yahoo(self) -> dict | None:
        """Fetch from Yahoo Finance v8 chart API for GC=F (gold futures)."""
        try:
            data = await self.fetch_json(
                self.YAHOO_CHART_URL,
                params={"interval": "1d", "range": "2d"},
                headers=YAHOO_HEADERS,
            )
            if not data or "chart" not in data:
                return None

            results = data["chart"].get("result", [])
            if not results:
                return None

            meta = results[0].get("meta", {})
            price = meta.get("regularMarketPrice")
            prev_close = meta.get("chartPreviousClose")

            if not price:
                return None

            change_24h = None
            if prev_close and prev_close > 0:
                change_24h = round(((price - prev_close) / prev_close) * 100, 4)

            # Extract OHLCV from indicators
            indicators = results[0].get("indicators", {})
            quotes = indicators.get("quote", [{}])
            quote = quotes[0] if quotes else {}

            opens = quote.get("open", [])
            highs = quote.get("high", [])
            lows = quote.get("low", [])
            closes = quote.get("close", [])
            volumes = quote.get("volume", [])

            return {
                "price": float(price),
                "open": float(opens[-1]) if opens and opens[-1] is not None else None,
                "high": float(highs[-1]) if highs and highs[-1] is not None else None,
                "low": float(lows[-1]) if lows and lows[-1] is not None else None,
                "close": float(price),
                "volume": int(volumes[-1]) if volumes and volumes[-1] is not None else None,
                "change_24h": change_24h,
            }
        except Exception as e:
            logger.warning(f"Yahoo Finance GC=F error: {e}")
            return None
