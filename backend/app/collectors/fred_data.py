"""FRED (Federal Reserve Economic Data) collector for gold-relevant macro indicators.

Fetches multiple FRED series critical for gold price analysis:
- Real yields (TIPS), breakeven inflation, nominal yields
- USD index, M2 money supply, CPI, PCE
- Fed funds rate, VIX, London gold fix
"""
import logging

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)

# FRED series IDs mapped to human-readable names
SERIES = {
    "DFII10": "real_yield_10y",       # 10Y real yield (TIPS)
    "T10YIE": "tips_breakeven",       # 10Y breakeven inflation
    "DGS10": "treasury_10y",          # 10Y nominal yield
    "DGS2": "treasury_2y",            # 2Y nominal yield
    "DTWEXBGS": "dxy",                # Trade-weighted USD index
    "M2SL": "m2_supply",              # M2 money supply (billions)
    "CPIAUCSL": "cpi",                # CPI for all urban consumers
    "PCEPI": "pce",                   # PCE price index
    "FEDFUNDS": "fed_funds_rate",     # Effective federal funds rate
    "VIXCLS": "vix",                  # CBOE VIX close
    "GOLDAMGBD228NLBM": "london_fix", # London gold fixing price (USD/oz)
}

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


class FREDCollector(BaseCollector):
    """Collects multiple macro data series from the FRED API."""

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def collect(self) -> dict:
        """Fetch all configured FRED series.

        Returns:
            Dict keyed by series name, each containing:
            {value, previous, change, date}
        """
        if not settings.fred_api_key:
            logger.warning("FRED API key not set — skipping all FRED series")
            return {"error": "fred_api_key not configured", "timestamp": self.now().isoformat()}

        result = {}
        for series_id, name in SERIES.items():
            series_data = await self._fetch_series(series_id)
            if series_data is not None:
                result[name] = series_data
            else:
                result[name] = None

        result["timestamp"] = self.now().isoformat()
        return result

    async def fetch_single(self, series_id: str, limit: int = 5) -> dict | None:
        """Fetch a single FRED series (public helper for ad-hoc queries)."""
        return await self._fetch_series(series_id, limit=limit)

    async def _fetch_series(self, series_id: str, limit: int = 5) -> dict | None:
        """Fetch observations for a single FRED series.

        Returns:
            Dict with {value, previous, change, date} or None on failure.
        """
        try:
            data = await self.fetch_json(
                FRED_BASE_URL,
                params={
                    "series_id": series_id,
                    "api_key": settings.fred_api_key,
                    "sort_order": "desc",
                    "limit": limit,
                    "file_type": "json",
                },
            )
            if not data or "observations" not in data:
                logger.debug(f"FRED {series_id}: no observations returned")
                return None

            observations = data["observations"]
            if not observations:
                return None

            # Find first valid (non-".") value
            current_value = None
            current_date = None
            previous_value = None

            for i, obs in enumerate(observations):
                val_str = obs.get("value", "")
                if val_str and val_str != ".":
                    if current_value is None:
                        current_value = float(val_str)
                        current_date = obs.get("date")
                    elif previous_value is None:
                        previous_value = float(val_str)
                        break

            if current_value is None:
                return None

            change = None
            if previous_value is not None and previous_value != 0:
                change = round(current_value - previous_value, 6)

            return {
                "value": current_value,
                "previous": previous_value,
                "change": change,
                "date": current_date,
            }

        except Exception as e:
            logger.warning(f"FRED {series_id} fetch error: {e}")
            return None
