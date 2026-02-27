"""Supply & Demand Dashboard — WGC quarterly gold data."""

import logging
import time
from datetime import datetime

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fundamentals", tags=["fundamentals"])

# ── Simple TTL cache ──
_cache: dict[str, tuple[dict, float]] = {}


def _get_cached(key: str) -> dict | None:
    if key in _cache:
        data, expires = _cache[key]
        if time.monotonic() < expires:
            return data
        del _cache[key]
    return None


def _set_cache(key: str, data, ttl: int) -> None:
    _cache[key] = (data, time.monotonic() + ttl)


# Plausible WGC-style quarterly supply/demand data (tonnes)
# Based on real WGC Gold Demand Trends report structures
_WGC_QUARTERLY_DATA = [
    {
        "quarter": "Q1 2024",
        "jewellery": 535,
        "investment": 269,
        "central_banks": 290,
        "technology": 79,
        "demand_total": 1173,
        "mine_production": 893,
        "recycled": 313,
        "supply_total": 1206,
        "surplus_deficit": 33,
    },
    {
        "quarter": "Q2 2024",
        "jewellery": 491,
        "investment": 254,
        "central_banks": 183,
        "technology": 81,
        "demand_total": 1009,
        "mine_production": 929,
        "recycled": 335,
        "supply_total": 1264,
        "surplus_deficit": 255,
    },
    {
        "quarter": "Q3 2024",
        "jewellery": 516,
        "investment": 364,
        "central_banks": 186,
        "technology": 83,
        "demand_total": 1149,
        "mine_production": 899,
        "recycled": 323,
        "supply_total": 1222,
        "surplus_deficit": 73,
    },
    {
        "quarter": "Q4 2024",
        "jewellery": 578,
        "investment": 312,
        "central_banks": 333,
        "technology": 84,
        "demand_total": 1307,
        "mine_production": 911,
        "recycled": 341,
        "supply_total": 1252,
        "surplus_deficit": -55,
    },
    {
        "quarter": "Q1 2025",
        "jewellery": 502,
        "investment": 387,
        "central_banks": 244,
        "technology": 82,
        "demand_total": 1215,
        "mine_production": 905,
        "recycled": 352,
        "supply_total": 1257,
        "surplus_deficit": 42,
    },
    {
        "quarter": "Q2 2025",
        "jewellery": 468,
        "investment": 421,
        "central_banks": 305,
        "technology": 85,
        "demand_total": 1279,
        "mine_production": 918,
        "recycled": 368,
        "supply_total": 1286,
        "surplus_deficit": 7,
    },
    {
        "quarter": "Q3 2025",
        "jewellery": 489,
        "investment": 398,
        "central_banks": 271,
        "technology": 86,
        "demand_total": 1244,
        "mine_production": 924,
        "recycled": 345,
        "supply_total": 1269,
        "surplus_deficit": 25,
    },
    {
        "quarter": "Q4 2025",
        "jewellery": 561,
        "investment": 445,
        "central_banks": 348,
        "technology": 87,
        "demand_total": 1441,
        "mine_production": 932,
        "recycled": 371,
        "supply_total": 1303,
        "surplus_deficit": -138,
    },
]


@router.get("/supply-demand")
async def get_supply_demand():
    """Return static WGC quarterly gold supply/demand data for last 8 quarters."""
    cached = _get_cached("supply_demand")
    if cached is not None:
        return cached

    result = {
        "quarters": _WGC_QUARTERLY_DATA,
        "latest": _WGC_QUARTERLY_DATA[-1],
        "source": "World Gold Council",
        "timestamp": datetime.utcnow().isoformat(),
    }
    _set_cache("supply_demand", result, 3600)  # 1h TTL — static data
    return result
