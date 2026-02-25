"""Central bank gold reserves collector.

Provides a curated list of the top-20 central bank gold holders with
known reserve data. Attempts to fetch updated data from public sources,
falling back to the static baseline (sourced from World Gold Council data,
updated periodically).

Reserve data changes slowly (quarterly at most), so the static fallback
is usually sufficient between manual updates.
"""
import logging

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

# Static baseline: Top-20 central bank gold holders (tonnes)
# Source: World Gold Council / IMF IFS data (as of Q4 2025 estimates)
STATIC_RESERVES = [
    {"country": "United States", "total_tonnes": 8133.5, "rank": 1},
    {"country": "Germany", "total_tonnes": 3352.3, "rank": 2},
    {"country": "Italy", "total_tonnes": 2451.8, "rank": 3},
    {"country": "France", "total_tonnes": 2436.9, "rank": 4},
    {"country": "Russia", "total_tonnes": 2332.7, "rank": 5},
    {"country": "China", "total_tonnes": 2264.9, "rank": 6},
    {"country": "Switzerland", "total_tonnes": 1040.0, "rank": 7},
    {"country": "India", "total_tonnes": 854.7, "rank": 8},
    {"country": "Japan", "total_tonnes": 846.0, "rank": 9},
    {"country": "Netherlands", "total_tonnes": 612.5, "rank": 10},
    {"country": "Turkey", "total_tonnes": 585.2, "rank": 11},
    {"country": "ECB", "total_tonnes": 506.5, "rank": 12},
    {"country": "Taiwan", "total_tonnes": 422.4, "rank": 13},
    {"country": "Poland", "total_tonnes": 398.7, "rank": 14},
    {"country": "Uzbekistan", "total_tonnes": 371.2, "rank": 15},
    {"country": "Portugal", "total_tonnes": 382.6, "rank": 16},
    {"country": "Saudi Arabia", "total_tonnes": 323.1, "rank": 17},
    {"country": "United Kingdom", "total_tonnes": 310.3, "rank": 18},
    {"country": "Kazakhstan", "total_tonnes": 304.2, "rank": 19},
    {"country": "Lebanon", "total_tonnes": 286.8, "rank": 20},
]

# World Gold Council public data endpoints (may require scraping)
WGC_RESERVE_URL = "https://www.gold.org/goldhub/data/gold-reserves-by-country"


class CentralBankGoldCollector(BaseCollector):
    """Collects central bank gold reserve data."""

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        reraise=True,
    )
    async def collect(self) -> list[dict]:
        """Fetch central bank gold reserves.

        Attempts to fetch updated data from public APIs. Falls back to the
        static baseline if no live data is available.

        Returns:
            List of dicts: {country, total_tonnes, rank, source}
        """
        # Try to fetch live data
        live_data = await self._fetch_live_reserves()
        if live_data:
            logger.info(f"Fetched live central bank gold data: {len(live_data)} countries")
            return live_data

        # Fall back to static data
        logger.info("Using static central bank gold reserve data")
        return [
            {
                "country": entry["country"],
                "total_tonnes": entry["total_tonnes"],
                "rank": entry["rank"],
                "source": "static_baseline_q4_2025",
            }
            for entry in STATIC_RESERVES
        ]

    async def _fetch_live_reserves(self) -> list[dict] | None:
        """Attempt to fetch updated reserve data from public sources.

        The World Gold Council website requires JavaScript rendering,
        so we try alternative structured data sources first.
        """
        # Try Wikipedia/IMF data via a simple API if available
        try:
            # DBnomics aggregates IMF IFS data including gold reserves
            data = await self.fetch_json(
                "https://api.db.nomics.world/v22/series",
                params={
                    "provider_code": "IMF",
                    "dataset_code": "IFS",
                    "series_code": "Q..RAXG_USD..?",
                    "limit": 30,
                    "observations": 1,
                    "format": "json",
                },
            )
            if data and "series" in data and "docs" in data["series"]:
                reserves = []
                for doc in data["series"]["docs"]:
                    country = doc.get("dimensions", {}).get("REF_AREA", "Unknown")
                    periods = doc.get("period", [])
                    values = doc.get("value", [])
                    if periods and values and values[-1] is not None:
                        reserves.append({
                            "country": country,
                            "total_tonnes": round(float(values[-1]), 1),
                            "rank": None,
                            "source": "imf_ifs_dbnomics",
                        })

                if reserves:
                    # Sort by tonnes descending and assign ranks
                    reserves.sort(key=lambda x: x["total_tonnes"], reverse=True)
                    for i, entry in enumerate(reserves):
                        entry["rank"] = i + 1
                    return reserves[:20]

        except Exception as e:
            logger.debug(f"DBnomics IMF reserve fetch error: {e}")

        return None

    def get_total_central_bank_tonnes(self) -> float:
        """Return total tonnes held by top-20 central banks (static estimate)."""
        return sum(entry["total_tonnes"] for entry in STATIC_RESERVES)
