"""Abstract broker connection interface."""
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class BrokerConnection(ABC):
    """Abstract base class for broker connections.

    All broker adapters (demo, MetaApi, FIX, etc.) must implement this
    interface. Methods are async to support non-blocking I/O with real
    broker APIs.
    """

    @abstractmethod
    async def connect(self, config: dict) -> bool:
        """Connect to the broker.

        Args:
            config: Broker-specific configuration dict (credentials, server, etc.).

        Returns:
            True if connection was established successfully, False otherwise.
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the broker.

        Returns:
            True if disconnected cleanly, False otherwise.
        """
        pass

    @abstractmethod
    async def get_account_info(self) -> dict:
        """Retrieve current account information.

        Returns:
            Dict with keys: balance, equity, margin, free_margin, leverage, currency.
        """
        pass

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> dict:
        """Place a market order.

        Args:
            symbol: Trading symbol (e.g. "XAUUSD").
            direction: "buy" or "sell".
            lot_size: Position size in lots.
            sl: Stop-loss price (optional).
            tp: Take-profit price (optional).

        Returns:
            Dict with keys: order_id, entry_price, status.
        """
        pass

    @abstractmethod
    async def modify_order(
        self,
        position_id: str,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> dict:
        """Modify stop-loss and/or take-profit of an open position.

        Args:
            position_id: The position/order identifier.
            sl: New stop-loss price (None = unchanged).
            tp: New take-profit price (None = unchanged).

        Returns:
            Dict with keys: position_id, sl, tp, status.
        """
        pass

    @abstractmethod
    async def close_position(
        self, position_id: str, lot_size: Optional[float] = None
    ) -> dict:
        """Close an open position (fully or partially).

        Args:
            position_id: The position identifier.
            lot_size: Partial close size. None = close entire position.

        Returns:
            Dict with keys: pnl, exit_price, status.
        """
        pass

    @abstractmethod
    async def get_positions(self) -> list[dict]:
        """Retrieve all open positions.

        Returns:
            List of dicts, each with keys: position_id, symbol, direction,
            lot_size, entry_price, sl, tp, pnl, open_time.
        """
        pass

    @abstractmethod
    async def get_price(self, symbol: str = "XAUUSD") -> dict:
        """Get current bid/ask price for a symbol.

        Args:
            symbol: Trading symbol. Defaults to "XAUUSD".

        Returns:
            Dict with keys: bid, ask, spread, timestamp.
        """
        pass


def create_broker(broker_type: str) -> BrokerConnection:
    """Factory function to create a broker connection by type.

    Args:
        broker_type: One of "demo", "metaapi", "fix".

    Returns:
        A BrokerConnection instance.

    Raises:
        ValueError: If broker_type is not recognized.
    """
    if broker_type == "demo":
        from app.broker.demo_adapter import DemoBrokerAdapter

        return DemoBrokerAdapter()
    elif broker_type == "metaapi":
        from app.broker.metaapi_adapter import MetaApiBrokerAdapter

        return MetaApiBrokerAdapter()
    elif broker_type == "fix":
        from app.broker.fix_adapter import FixBrokerAdapter

        return FixBrokerAdapter()
    else:
        raise ValueError(f"Unknown broker type: {broker_type}")
