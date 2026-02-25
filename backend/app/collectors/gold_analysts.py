"""Institutional gold analyst forecast collector.

Returns a curated list of recent institutional gold price forecasts.
This collector uses hardcoded data that should be periodically updated
as new forecasts are published.

Forecasts are sourced from public research notes, media appearances,
and published reports from major investment banks and research firms.
"""
import logging

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

# Curated institutional gold forecasts (update periodically)
# Source: Public research notes and media coverage as of Q1 2026
FORECASTS = [
    {
        "institution": "Goldman Sachs",
        "target": 3000,
        "timeframe": "Year-end 2026",
        "direction": "bullish",
        "rationale": "Central bank buying and Fed rate cuts",
    },
    {
        "institution": "JPMorgan",
        "target": 2800,
        "timeframe": "Q2 2026",
        "direction": "bullish",
        "rationale": "Geopolitical risk premium and dedollarization",
    },
    {
        "institution": "UBS",
        "target": 2900,
        "timeframe": "Year-end 2026",
        "direction": "bullish",
        "rationale": "Portfolio hedge demand and real yield decline",
    },
    {
        "institution": "Citi",
        "target": 3000,
        "timeframe": "H2 2026",
        "direction": "bullish",
        "rationale": "Strong ETF inflows and emerging market demand",
    },
    {
        "institution": "Bank of America",
        "target": 3000,
        "timeframe": "2026",
        "direction": "bullish",
        "rationale": "Fiscal deficit concerns and inflation hedge",
    },
    {
        "institution": "Deutsche Bank",
        "target": 2750,
        "timeframe": "Mid-2026",
        "direction": "bullish",
        "rationale": "Monetary easing cycle supports gold",
    },
    {
        "institution": "Morgan Stanley",
        "target": 2700,
        "timeframe": "Q1 2026",
        "direction": "neutral",
        "rationale": "Rate cuts priced in; limited upside near-term",
    },
    {
        "institution": "ANZ Research",
        "target": 2850,
        "timeframe": "Year-end 2026",
        "direction": "bullish",
        "rationale": "Strong Asian physical demand",
    },
]


class GoldAnalystCollector(BaseCollector):
    """Returns curated institutional gold price forecasts."""

    async def collect(self) -> list[dict]:
        """Return the latest institutional gold forecasts.

        Returns:
            List of dicts: {institution, target, timeframe, direction, rationale}
        """
        logger.debug(f"Returning {len(FORECASTS)} institutional gold forecasts")
        return [
            {
                "institution": f["institution"],
                "target": f["target"],
                "timeframe": f["timeframe"],
                "direction": f["direction"],
                "rationale": f.get("rationale", ""),
                "timestamp": self.now().isoformat(),
            }
            for f in FORECASTS
        ]

    @staticmethod
    def get_consensus_target() -> float:
        """Calculate the average consensus target price."""
        targets = [f["target"] for f in FORECASTS]
        return round(sum(targets) / len(targets), 2) if targets else 0.0

    @staticmethod
    def get_bullish_ratio() -> float:
        """Calculate the ratio of bullish forecasts (0.0 to 1.0)."""
        if not FORECASTS:
            return 0.0
        bullish_count = sum(1 for f in FORECASTS if f["direction"] == "bullish")
        return round(bullish_count / len(FORECASTS), 4)
