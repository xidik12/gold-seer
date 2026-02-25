"""Gold ETF flow data collector.

Sources:
- Yahoo Finance API for gold ETF price/volume data (GLD, IAU, SGOL, GLDM)
- Fallback: yfinance library
"""
import logging
from datetime import datetime

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

# Major gold ETFs to track
GOLD_ETF_TICKERS = ["GLD", "IAU", "SGOL", "GLDM"]


class ETFCollector(BaseCollector):
    """Collects gold ETF flow data (GLD, IAU, SGOL, GLDM) from Yahoo Finance."""

    # Yahoo Finance quote API (public, no auth required)
    YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=2d&interval=1d"

    async def collect(self) -> dict:
        """Collect latest gold ETF flow data."""
        result = {
            "net_flow_usd": 0.0,        # Daily net inflow/outflow in USD (estimated)
            "total_holdings_oz": 0.0,    # Total gold ounces held by all ETFs
            "gld_flow": 0.0,            # SPDR Gold Trust daily flow
            "iau_flow": 0.0,            # iShares Gold Trust daily flow
            "sgol_flow": 0.0,           # Aberdeen Standard Gold ETF daily flow
            "gldm_flow": 0.0,           # SPDR Gold MiniShares daily flow
            "etf_volume_usd": 0.0,      # Daily ETF trading volume
            "timestamp": self.now().isoformat(),
        }

        # Fetch gold ETF data from Yahoo Finance
        data = await self._get_yahoo_finance()
        if data:
            result.update(data)
            return result

        # Fallback: try yfinance library
        data = await self._get_yfinance_fallback()
        if data:
            result.update(data)

        return result

    async def _get_yahoo_finance(self) -> dict | None:
        """Fetch gold ETF data from Yahoo Finance public API."""
        try:
            total_volume = 0.0
            flows_by_ticker = {}

            for ticker in GOLD_ETF_TICKERS:
                url = self.YAHOO_QUOTE_URL.format(ticker=ticker)
                data = await self.fetch_json(url)
                if not data:
                    continue

                chart = data.get("chart", {})
                results = chart.get("result", [])
                if not results:
                    continue

                result = results[0]
                indicators = result.get("indicators", {})
                quotes = indicators.get("quote", [{}])[0]
                meta = result.get("meta", {})

                volumes = quotes.get("volume", [])
                closes = quotes.get("close", [])

                if volumes and closes:
                    # Get the latest day's volume and price
                    latest_volume = volumes[-1] or 0
                    latest_close = closes[-1] or 0
                    volume_usd = latest_volume * latest_close
                    total_volume += volume_usd

                    # Estimate flow from volume and price change
                    if len(closes) >= 2 and closes[-2]:
                        price_change_pct = (closes[-1] - closes[-2]) / closes[-2]
                        # Rough flow estimate: positive price change = inflow
                        estimated_flow = volume_usd * price_change_pct
                        flows_by_ticker[ticker] = estimated_flow
                    else:
                        flows_by_ticker[ticker] = 0.0

            if not flows_by_ticker:
                return None

            net_flow = sum(flows_by_ticker.values())

            return {
                "net_flow_usd": round(net_flow, 2),
                "gld_flow": round(flows_by_ticker.get("GLD", 0.0), 2),
                "iau_flow": round(flows_by_ticker.get("IAU", 0.0), 2),
                "sgol_flow": round(flows_by_ticker.get("SGOL", 0.0), 2),
                "gldm_flow": round(flows_by_ticker.get("GLDM", 0.0), 2),
                "etf_volume_usd": round(total_volume, 2),
            }
        except Exception as e:
            logger.debug(f"Yahoo Finance ETF error: {e}")
            return None

    async def _get_yfinance_fallback(self) -> dict | None:
        """Fallback: try yfinance library for gold ETF data."""
        try:
            import yfinance as yf

            total_volume = 0.0
            flows_by_ticker = {}

            for ticker in GOLD_ETF_TICKERS:
                etf = yf.Ticker(ticker)
                hist = etf.history(period="2d")
                if hist.empty:
                    continue

                latest = hist.iloc[-1]
                volume_usd = latest["Volume"] * latest["Close"]
                total_volume += volume_usd

                if len(hist) >= 2:
                    prev = hist.iloc[-2]
                    price_change_pct = (latest["Close"] - prev["Close"]) / prev["Close"]
                    flows_by_ticker[ticker] = volume_usd * price_change_pct
                else:
                    flows_by_ticker[ticker] = 0.0

            if not flows_by_ticker:
                return None

            return {
                "net_flow_usd": round(sum(flows_by_ticker.values()), 2),
                "gld_flow": round(flows_by_ticker.get("GLD", 0.0), 2),
                "iau_flow": round(flows_by_ticker.get("IAU", 0.0), 2),
                "sgol_flow": round(flows_by_ticker.get("SGOL", 0.0), 2),
                "gldm_flow": round(flows_by_ticker.get("GLDM", 0.0), 2),
                "etf_volume_usd": round(total_volume, 2),
            }
        except ImportError:
            logger.debug("yfinance not installed — ETF fallback unavailable")
        except Exception as e:
            logger.debug(f"ETF yfinance fallback error: {e}")
        return None
