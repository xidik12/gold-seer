"""Gold ETF flow and holdings tracker.

Tracks the major physically-backed gold ETFs:
- GLD  (SPDR Gold Shares — largest, ~900t)
- IAU  (iShares Gold Trust)
- SGOL (Aberdeen Standard Physical Gold Shares)
- GLDM (SPDR Gold MiniShares — lower expense ratio)

Uses Yahoo Finance v8 chart API for price/volume data.
Holdings in tonnes are estimated from AUM and current gold price.
"""
import logging

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# Gold ETF tickers and approximate total shares outstanding (for AUM estimation)
# These are rough estimates; real-time shares outstanding would require a premium data source.
GOLD_ETFS = [
    {"ticker": "GLD", "name": "SPDR Gold Shares", "oz_per_share": 0.0926},
    {"ticker": "IAU", "name": "iShares Gold Trust", "oz_per_share": 0.00969},
    {"ticker": "SGOL", "name": "Aberdeen Physical Gold", "oz_per_share": 0.0949},
    {"ticker": "GLDM", "name": "SPDR Gold MiniShares", "oz_per_share": 0.00929},
]

# Troy ounces per metric tonne
OZ_PER_TONNE = 32150.7


class GoldETFFlowCollector(BaseCollector):
    """Tracks gold ETF prices, volumes, and estimated holdings."""

    YAHOO_CHART_BASE = "https://query2.finance.yahoo.com/v8/finance/chart"

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def collect(self) -> list[dict]:
        """Fetch data for all tracked gold ETFs.

        Returns:
            List of dicts: {ticker, name, price, volume, prev_close,
                           daily_change, daily_change_pct, estimated_holdings_tonnes}
        """
        results = []
        for etf in GOLD_ETFS:
            data = await self._fetch_etf_data(etf["ticker"])
            if data:
                # Estimate holdings in tonnes from volume * oz_per_share
                # Note: This is the daily *traded* volume, not total AUM.
                # For a rough AUM-based holdings estimate, we'd need shares outstanding.
                data["name"] = etf["name"]
                data["oz_per_share"] = etf["oz_per_share"]
                results.append(data)
            else:
                results.append({
                    "ticker": etf["ticker"],
                    "name": etf["name"],
                    "price": None,
                    "volume": None,
                    "prev_close": None,
                    "daily_change": None,
                    "daily_change_pct": None,
                    "estimated_holdings_tonnes": None,
                })

        return results

    async def _fetch_etf_data(self, ticker: str) -> dict | None:
        """Fetch a single gold ETF via Yahoo Finance v8 chart API."""
        try:
            url = f"{self.YAHOO_CHART_BASE}/{ticker}"
            data = await self.fetch_json(
                url,
                params={"interval": "1d", "range": "5d"},
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

            # Get the latest volume from indicators
            indicators = results[0].get("indicators", {})
            quotes = indicators.get("quote", [{}])
            quote = quotes[0] if quotes else {}
            volumes = quote.get("volume", [])
            latest_volume = None
            if volumes:
                # Use the last non-None volume
                for v in reversed(volumes):
                    if v is not None:
                        latest_volume = int(v)
                        break

            daily_change = None
            daily_change_pct = None
            if prev_close and prev_close > 0:
                daily_change = round(price - prev_close, 4)
                daily_change_pct = round(((price - prev_close) / prev_close) * 100, 4)

            # Rough holdings estimate: for ETFs like GLD, each share represents
            # a fraction of an ounce. AUM / gold_price = total ounces.
            # Without shares outstanding data, we leave this as None.
            estimated_holdings_tonnes = None

            return {
                "ticker": ticker,
                "price": float(price),
                "volume": latest_volume,
                "prev_close": float(prev_close) if prev_close else None,
                "daily_change": daily_change,
                "daily_change_pct": daily_change_pct,
                "estimated_holdings_tonnes": estimated_holdings_tonnes,
            }

        except Exception as e:
            logger.warning(f"Yahoo Finance ETF error for {ticker}: {e}")
            return None
