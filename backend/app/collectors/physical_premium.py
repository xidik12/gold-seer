"""Physical gold premium (SGE) collector.

Estimates the Shanghai Gold Exchange premium over spot by:
1. Fetching CNY/USD exchange rate from Yahoo Finance
2. Getting latest gold spot price from internal data
3. Computing estimated SGE premium percentage
"""
import logging
from datetime import datetime

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

# SGE AU9999 typically trades at a premium of 1-5% above international spot
# We estimate this from the CNY/USD rate spread and market conditions


class PhysicalPremiumCollector(BaseCollector):
    """Computes estimated SGE physical gold premium over spot."""

    async def collect(self) -> dict:
        """Fetch CNY/USD rate and compute estimated SGE premium."""
        # Step 1: Fetch CNY/USD exchange rate from Yahoo Finance
        cny_usd_rate = await self._fetch_cny_usd_rate()

        # Step 2: Get latest gold spot price from internal DB
        spot_usd = await self._get_latest_spot_price()

        # Step 3: Compute estimated SGE premium
        # The SGE premium is driven by Chinese demand, import restrictions,
        # and capital controls. We estimate it from the rate spread.
        estimated_premium_pct = None
        signal = "unknown"

        if cny_usd_rate and spot_usd:
            # Base premium estimation:
            # When CNY is weak (high USD/CNY), Chinese buyers pay more -> higher premium
            # Historical SGE premium correlates with USD/CNY rate deviations
            # Normal USD/CNY ~ 7.1-7.3; above 7.3 = capital flight pressure = higher premium
            usd_cny = 1.0 / cny_usd_rate if cny_usd_rate > 0 else 7.2

            # Base premium of 1.5% + adjustment for rate deviation
            base_premium = 1.5
            # Every 0.1 above 7.2 adds ~0.5% premium
            rate_deviation = max(0, usd_cny - 7.2)
            premium_adjustment = rate_deviation * 5.0  # 0.1 deviation = 0.5% premium
            estimated_premium_pct = round(base_premium + premium_adjustment, 2)

            # Signal based on premium level
            if estimated_premium_pct < 2.0:
                signal = "GREEN"
            elif estimated_premium_pct < 4.0:
                signal = "YELLOW"
            else:
                signal = "RED"

        return {
            "spot_usd": spot_usd,
            "cny_usd_rate": round(cny_usd_rate, 6) if cny_usd_rate else None,
            "estimated_sge_premium_pct": estimated_premium_pct,
            "signal": signal,
            "timestamp": self.now().isoformat(),
        }

    async def _fetch_cny_usd_rate(self) -> float | None:
        """Fetch CNY/USD exchange rate via Yahoo Finance v8 chart API."""
        # Try multiple symbols for CNY/USD
        symbols = ["CNYUSD=X", "CNY=X"]

        for symbol in symbols:
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
                        if price and price > 0:
                            return float(price)

            except Exception as e:
                logger.debug(f"Yahoo Finance v8 error for {symbol}: {e}")

        # Fallback: use a reasonable estimate
        logger.warning("PhysicalPremium: Could not fetch CNY/USD rate, using fallback")
        return 0.137  # ~1 CNY = 0.137 USD (USD/CNY ~ 7.3)

    async def _get_latest_spot_price(self) -> float | None:
        """Get latest gold spot price from the Price table."""
        try:
            from app.database import async_session, Price
            from sqlalchemy import select, desc

            async with async_session() as session:
                result = await session.execute(
                    select(Price).order_by(desc(Price.timestamp)).limit(1)
                )
                price = result.scalar_one_or_none()
                if price:
                    return float(price.close)
        except Exception as e:
            logger.warning(f"PhysicalPremium: Could not fetch spot price: {e}")

        return None
