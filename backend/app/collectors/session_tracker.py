"""Gold trading session tracker.

Tracks per-session OHLCV for the three major gold trading sessions:
- Asian:   00:00 – 09:00 UTC
- London:  07:00 – 16:00 UTC
- New York: 13:00 – 22:00 UTC

Maintains in-memory session state that resets when a session ends.
Uses GoldPriceCollector internally to get the current spot price.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

# Session definitions (UTC hours)
SESSION_DEFINITIONS = [
    {"name": "asian", "start_hour": 0, "end_hour": 9},
    {"name": "london", "start_hour": 7, "end_hour": 16},
    {"name": "new_york", "start_hour": 13, "end_hour": 22},
]


class _SessionState:
    """In-memory OHLC state for a single trading session."""

    __slots__ = ("name", "open", "high", "low", "close", "date_key", "is_active")

    def __init__(self, name: str):
        self.name = name
        self.open: Optional[float] = None
        self.high: Optional[float] = None
        self.low: Optional[float] = None
        self.close: Optional[float] = None
        self.date_key: Optional[str] = None  # YYYY-MM-DD to detect day rollover
        self.is_active: bool = False

    def reset(self):
        self.open = None
        self.high = None
        self.low = None
        self.close = None
        self.date_key = None
        self.is_active = False

    def update(self, price: float, date_key: str):
        """Update OHLC with a new price tick."""
        # If the date changed, reset the session
        if self.date_key != date_key:
            self.reset()
            self.date_key = date_key

        if self.open is None:
            self.open = price
        self.close = price

        if self.high is None or price > self.high:
            self.high = price
        if self.low is None or price < self.low:
            self.low = price

        self.is_active = True

    def to_dict(self) -> dict:
        return {
            "session_name": self.name,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "is_active": self.is_active,
        }


class SessionTracker(BaseCollector):
    """Tracks per-session OHLCV for Asian, London, and New York gold sessions."""

    def __init__(self):
        super().__init__()
        self._sessions = {
            defn["name"]: _SessionState(defn["name"])
            for defn in SESSION_DEFINITIONS
        }
        self._gold_price_collector = None

    def _get_gold_price_collector(self):
        """Lazy import to avoid circular dependency."""
        if self._gold_price_collector is None:
            from app.collectors.gold_price import GoldPriceCollector
            self._gold_price_collector = GoldPriceCollector()
        return self._gold_price_collector

    async def collect(self) -> dict:
        """Collect current session data.

        Returns:
            Dict with:
            - active_sessions: list of currently active session names
            - session_data: list of per-session OHLC dicts
            - current_price: the latest gold price used for the update
            - timestamp: ISO timestamp
        """
        now = datetime.now(timezone.utc)
        hour = now.hour
        date_key = now.strftime("%Y-%m-%d")

        # Fetch current gold price
        collector = self._get_gold_price_collector()
        current_price = await collector.get_current_price()

        active_session_names = []

        for defn in SESSION_DEFINITIONS:
            name = defn["name"]
            state = self._sessions[name]

            is_in_session = defn["start_hour"] <= hour < defn["end_hour"]

            # Check if market is open (Mon-Fri, Fri closes at 22:00 UTC)
            weekday = now.weekday()
            market_open = weekday < 5 or (weekday == 4 and hour < 22)

            if is_in_session and market_open:
                if current_price is not None:
                    state.update(current_price, date_key)
                active_session_names.append(name)
            else:
                # Mark session as inactive (but preserve OHLC data for the day)
                state.is_active = False

        session_data = [
            self._sessions[defn["name"]].to_dict()
            for defn in SESSION_DEFINITIONS
        ]

        return {
            "active_sessions": active_session_names,
            "session_data": session_data,
            "current_price": current_price,
            "timestamp": now.isoformat(),
        }

    def get_session_state(self, session_name: str) -> dict | None:
        """Get the current state of a specific session."""
        state = self._sessions.get(session_name)
        if state:
            return state.to_dict()
        return None

    async def close(self):
        """Close both this collector and the internal GoldPriceCollector."""
        if self._gold_price_collector:
            await self._gold_price_collector.close()
        await super().close()
