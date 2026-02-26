"""Gold miner stocks collector via Yahoo Finance v8 API."""
import logging
from datetime import datetime

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

# Gold miner tickers: NEM (Newmont), GOLD (Barrick), AEM (Agnico Eagle),
# KGC (Kinross), WPM (Wheaton), FNV (Franco-Nevada), GDX (Miners ETF), GDXJ (Junior Miners ETF)
GOLD_MINERS = {
    "NEM": "Newmont Corporation",
    "GOLD": "Barrick Gold",
    "AEM": "Agnico Eagle Mines",
    "KGC": "Kinross Gold",
    "WPM": "Wheaton Precious Metals",
    "FNV": "Franco-Nevada",
    "GDX": "VanEck Gold Miners ETF",
    "GDXJ": "VanEck Junior Gold Miners ETF",
}

# GLD ticker for computing GDX/GLD ratio
GLD_TICKER = "GLD"


class GoldMinersCollector(BaseCollector):
    """Fetches gold miner stock data via Yahoo Finance v8 chart API."""

    async def collect(self) -> dict:
        """Collect all gold miner stock data and compute GDX/GLD ratio."""
        miners = []
        gdx_price = None
        gld_price = None

        for ticker, name in GOLD_MINERS.items():
            data = await self._fetch_yahoo_v8(ticker)
            if data:
                entry = {
                    "ticker": ticker,
                    "name": name,
                    "price": data["price"],
                    "change_pct": data["change_pct"],
                    "market_cap_approx": data.get("market_cap"),
                }
                miners.append(entry)

                if ticker == "GDX":
                    gdx_price = data["price"]

        # Fetch GLD for ratio calculation
        gld_data = await self._fetch_yahoo_v8(GLD_TICKER)
        if gld_data:
            gld_price = gld_data["price"]

        # Compute GDX/GLD ratio (leading indicator)
        gdx_gld_ratio = None
        ratio_signal = "neutral"
        if gdx_price and gld_price and gld_price > 0:
            gdx_gld_ratio = round(gdx_price / gld_price, 4)
            # Historical GDX/GLD ratio context:
            # High ratio (>0.20) = miners outperforming = bullish gold outlook
            # Low ratio (<0.12) = miners underperforming = bearish or lagging
            if gdx_gld_ratio > 0.20:
                ratio_signal = "bullish"
            elif gdx_gld_ratio > 0.15:
                ratio_signal = "neutral"
            elif gdx_gld_ratio > 0.12:
                ratio_signal = "cautious"
            else:
                ratio_signal = "bearish"

        return {
            "miners": miners,
            "gdx_gld_ratio": gdx_gld_ratio,
            "gld_price": gld_price,
            "ratio_signal": ratio_signal,
            "timestamp": self.now().isoformat(),
        }

    async def _fetch_yahoo_v8(self, symbol: str) -> dict | None:
        """Fetch a quote via Yahoo Finance v8 chart API (same pattern as MacroCollector)."""
        try:
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
            params = {"interval": "1d", "range": "2d"}
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            }

            data = await self.fetch_json(url, params=params, headers=headers)

            if data and "chart" in data:
                results = data["chart"].get("result", [])
                if results:
                    meta = results[0].get("meta", {})
                    price = meta.get("regularMarketPrice")
                    prev_close = meta.get("chartPreviousClose")

                    if price:
                        change_pct = 0.0
                        if prev_close and prev_close > 0:
                            change_pct = round(((price - prev_close) / prev_close) * 100, 4)

                        # Approximate market cap from price (rough estimate)
                        # Yahoo v8 doesn't always provide market cap directly in chart API
                        market_cap = None
                        volume = meta.get("regularMarketVolume")

                        return {
                            "price": float(price),
                            "change_pct": change_pct,
                            "market_cap": market_cap,
                            "volume": volume,
                        }

        except Exception as e:
            logger.debug(f"Yahoo Finance v8 error for {symbol}: {e}")

        return None
