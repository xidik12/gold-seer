"""FIX 4.4 protocol broker adapter (stub).

This adapter will provide integration with brokers supporting the
FIX (Financial Information eXchange) 4.4 protocol for institutional-grade
order execution. Currently a stub -- the real implementation requires
a FIX engine such as `quickfix` or `simplefix`.

Installation (when ready):
    pip install quickfix  # or simplefix

Configuration:
    config = {
        "host": "fix.broker.com",
        "port": 5001,
        "sender_comp_id": "GRIFFIN_GOLD",
        "target_comp_id": "BROKER",
        "username": "...",
        "password": "...",
        "fix_version": "FIX.4.4",
    }
"""
import logging
from typing import Optional

from app.broker.connection import BrokerConnection

logger = logging.getLogger(__name__)

_NOT_CONFIGURED_MSG = (
    "FIX adapter not configured. Install a FIX engine (quickfix) and "
    "provide valid FIX session credentials to enable institutional trading."
)


class FixBrokerAdapter(BrokerConnection):
    """FIX 4.4 protocol broker adapter (stub -- requires quickfix).

    All methods log a warning and return a "not configured" response.
    Replace the stub implementations with real FIX session management
    and message handling when the dependency is available.
    """

    def __init__(self) -> None:
        self._connected: bool = False
        self._session_id: Optional[str] = None

    async def connect(self, config: dict) -> bool:
        """Establish FIX session (stub)."""
        logger.warning(_NOT_CONFIGURED_MSG)
        return False

    async def disconnect(self) -> bool:
        """Terminate FIX session (stub)."""
        logger.warning(_NOT_CONFIGURED_MSG)
        self._connected = False
        return False

    async def get_account_info(self) -> dict:
        """Get account info via FIX (stub)."""
        logger.warning(_NOT_CONFIGURED_MSG)
        return {
            "error": _NOT_CONFIGURED_MSG,
            "status": "not_configured",
            "balance": 0.0,
            "equity": 0.0,
            "margin": 0.0,
            "free_margin": 0.0,
            "leverage": 0,
            "currency": "USD",
        }

    async def place_order(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> dict:
        """Send NewOrderSingle via FIX (stub)."""
        logger.warning(_NOT_CONFIGURED_MSG)
        return {
            "error": _NOT_CONFIGURED_MSG,
            "order_id": None,
            "entry_price": 0.0,
            "status": "not_configured",
        }

    async def modify_order(
        self,
        position_id: str,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> dict:
        """Send OrderCancelReplaceRequest via FIX (stub)."""
        logger.warning(_NOT_CONFIGURED_MSG)
        return {
            "error": _NOT_CONFIGURED_MSG,
            "position_id": position_id,
            "status": "not_configured",
        }

    async def close_position(
        self, position_id: str, lot_size: Optional[float] = None
    ) -> dict:
        """Close position via FIX (stub)."""
        logger.warning(_NOT_CONFIGURED_MSG)
        return {
            "error": _NOT_CONFIGURED_MSG,
            "pnl": 0.0,
            "exit_price": 0.0,
            "status": "not_configured",
        }

    async def get_positions(self) -> list[dict]:
        """Request open positions via FIX (stub)."""
        logger.warning(_NOT_CONFIGURED_MSG)
        return []

    async def get_price(self, symbol: str = "XAUUSD") -> dict:
        """Request market data via FIX (stub)."""
        logger.warning(_NOT_CONFIGURED_MSG)
        return {
            "error": _NOT_CONFIGURED_MSG,
            "bid": 0.0,
            "ask": 0.0,
            "spread": 0.0,
            "timestamp": None,
        }
