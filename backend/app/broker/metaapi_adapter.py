"""MetaApi MT4/MT5 broker adapter (stub).

This adapter will provide integration with MetaTrader 4 and 5 brokers
via the MetaApi cloud SDK. Currently a stub that returns placeholder
responses — the real implementation requires the `metaapi-cloud-sdk`
package and valid MetaApi credentials.

Installation (when ready):
    pip install metaapi-cloud-sdk

Configuration:
    config = {
        "token": "your-metaapi-token",
        "account_id": "your-mt-account-id",
    }
"""
import logging
from typing import Optional

from app.broker.connection import BrokerConnection

logger = logging.getLogger(__name__)

_NOT_CONFIGURED_MSG = (
    "MetaApi adapter not configured. Install metaapi-cloud-sdk and "
    "provide valid credentials to enable live trading."
)


class MetaApiBrokerAdapter(BrokerConnection):
    """MetaApi MT4/MT5 broker adapter (stub -- requires metaapi-cloud-sdk).

    All methods log a warning and return a "not configured" response.
    Replace the stub implementations with real MetaApi SDK calls when
    the dependency is available.
    """

    def __init__(self) -> None:
        self._connected: bool = False
        self._account_id: Optional[str] = None

    async def connect(self, config: dict) -> bool:
        """Connect to MetaApi (stub)."""
        logger.warning(_NOT_CONFIGURED_MSG)
        return False

    async def disconnect(self) -> bool:
        """Disconnect from MetaApi (stub)."""
        logger.warning(_NOT_CONFIGURED_MSG)
        self._connected = False
        return False

    async def get_account_info(self) -> dict:
        """Get account info from MetaApi (stub)."""
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
        """Place order via MetaApi (stub)."""
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
        """Modify order via MetaApi (stub)."""
        logger.warning(_NOT_CONFIGURED_MSG)
        return {
            "error": _NOT_CONFIGURED_MSG,
            "position_id": position_id,
            "status": "not_configured",
        }

    async def close_position(
        self, position_id: str, lot_size: Optional[float] = None
    ) -> dict:
        """Close position via MetaApi (stub)."""
        logger.warning(_NOT_CONFIGURED_MSG)
        return {
            "error": _NOT_CONFIGURED_MSG,
            "pnl": 0.0,
            "exit_price": 0.0,
            "status": "not_configured",
        }

    async def get_positions(self) -> list[dict]:
        """Get open positions via MetaApi (stub)."""
        logger.warning(_NOT_CONFIGURED_MSG)
        return []

    async def get_price(self, symbol: str = "XAUUSD") -> dict:
        """Get price via MetaApi (stub)."""
        logger.warning(_NOT_CONFIGURED_MSG)
        return {
            "error": _NOT_CONFIGURED_MSG,
            "bid": 0.0,
            "ask": 0.0,
            "spread": 0.0,
            "timestamp": None,
        }
