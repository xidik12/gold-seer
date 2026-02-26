"""MetaApi MT4/MT5 broker adapter.

Provides real broker integration with MetaTrader 4 and 5 via the MetaApi
Cloud SDK. Supports live and demo MT accounts for XAUUSD (gold) trading.

Installation:
    pip install metaapi-cloud-sdk

Configuration:
    config = {
        "token": "your-metaapi-token",
        "account_id": "your-mt-account-id",
    }
"""
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.broker.connection import BrokerConnection

logger = logging.getLogger(__name__)

# Conditional import — SDK may not be installed in dev/CI environments
try:
    from metaapi_cloud_sdk import MetaApi

    METAAPI_AVAILABLE = True
except ImportError:
    MetaApi = None  # type: ignore[assignment, misc]
    METAAPI_AVAILABLE = False


class MetaApiBrokerAdapter(BrokerConnection):
    """MetaApi MT4/MT5 broker adapter.

    Connects to a MetaTrader account via the MetaApi cloud service and
    exposes the unified BrokerConnection interface for live/demo trading.

    Lifecycle:
        1. connect(config) — authenticate, deploy account, open streaming connection
        2. place_order / modify_order / close_position / get_price / ...
        3. disconnect() — close connection, optionally undeploy account
    """

    def __init__(self) -> None:
        self._connected: bool = False
        self._api: Any = None           # MetaApi instance
        self._account: Any = None       # MetaTrader account object
        self._connection: Any = None    # Streaming (RPC) connection
        self._account_id: Optional[str] = None

    # ------------------------------------------------------------------
    # BrokerConnection implementation
    # ------------------------------------------------------------------

    async def connect(self, config: dict) -> bool:
        """Connect to a MetaTrader account via MetaApi.

        Args:
            config: Must contain ``token`` (MetaApi API token) and
                ``account_id`` (MetaTrader account provisioned in MetaApi).

        Returns:
            True if the connection and synchronization succeeded.
        """
        if not METAAPI_AVAILABLE:
            logger.error(
                "metaapi-cloud-sdk is not installed. "
                "Run `pip install metaapi-cloud-sdk` to enable live trading."
            )
            return False

        token = config.get("token")
        account_id = config.get("account_id")

        if not token or not account_id:
            logger.error(
                "MetaApi connect() requires 'token' and 'account_id' in config"
            )
            return False

        try:
            # 1. Create the MetaApi instance
            self._api = MetaApi(token)
            self._account_id = account_id

            # 2. Get the provisioned account
            self._account = (
                await self._api.metatrader_account_api.get_account(account_id)
            )
            logger.info(
                "MetaApi account retrieved: %s (state=%s)",
                account_id,
                self._account.state,
            )

            # 3. Deploy the account if it is not already deployed
            if self._account.state not in ("DEPLOYING", "DEPLOYED"):
                logger.info("Deploying MetaApi account %s ...", account_id)
                await self._account.deploy()

            # 4. Wait until the account is connected to the broker
            await self._account.wait_connected()
            logger.info("MetaApi account %s is connected to broker", account_id)

            # 5. Open a streaming (RPC) connection
            self._connection = self._account.get_streaming_connection()
            await self._connection.connect()

            # 6. Wait for terminal state synchronization
            await self._connection.wait_synchronized()
            logger.info(
                "MetaApi streaming connection synchronized for account %s",
                account_id,
            )

            self._connected = True
            return True

        except Exception:
            logger.exception(
                "Failed to connect to MetaApi account %s", account_id
            )
            self._connected = False
            return False

    async def disconnect(self) -> bool:
        """Disconnect from MetaApi and optionally undeploy the account.

        Returns:
            True if disconnected cleanly.
        """
        if not self._connected:
            logger.warning("disconnect() called but adapter is not connected")
            return True

        try:
            # Close the streaming connection
            if self._connection is not None:
                await self._connection.close()
                logger.info("MetaApi streaming connection closed")

            # Undeploy the account to free cloud resources
            if self._account is not None:
                await self._account.undeploy()
                logger.info(
                    "MetaApi account %s undeployed", self._account_id
                )

            self._connected = False
            self._connection = None
            self._account = None
            self._api = None
            self._account_id = None
            return True

        except Exception:
            logger.exception("Error during MetaApi disconnect")
            self._connected = False
            return False

    async def get_account_info(self) -> dict:
        """Retrieve live account information from the MetaTrader terminal.

        Returns:
            Dict with balance, equity, margin, free_margin, leverage,
            currency, and status.
        """
        if not self._connected or self._connection is None:
            return {"error": "Not connected", "status": "disconnected"}

        try:
            info = self._connection.terminal_state.account_information
            if info is None:
                return {"error": "Account info not yet synchronized", "status": "syncing"}

            return {
                "balance": float(info.get("balance", 0.0)),
                "equity": float(info.get("equity", 0.0)),
                "margin": float(info.get("margin", 0.0)),
                "free_margin": float(info.get("freeMargin", 0.0)),
                "leverage": int(info.get("leverage", 0)),
                "currency": str(info.get("currency", "USD")),
                "status": "connected",
            }

        except Exception:
            logger.exception("Failed to retrieve MetaApi account info")
            return {"error": "Failed to get account info", "status": "error"}

    async def place_order(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> dict:
        """Place a market order via MetaApi.

        Args:
            symbol: Trading symbol (e.g. "XAUUSD").
            direction: "buy" or "sell".
            lot_size: Position size in lots.
            sl: Stop-loss price (optional).
            tp: Take-profit price (optional).

        Returns:
            Dict with order_id, entry_price, and status.
        """
        if not self._connected or self._connection is None:
            return {"error": "Not connected", "status": "rejected"}

        direction = direction.lower()
        if direction not in ("buy", "sell"):
            return {
                "error": f"Invalid direction: {direction}",
                "status": "rejected",
            }

        if lot_size <= 0:
            return {"error": "Lot size must be positive", "status": "rejected"}

        try:
            # Build keyword arguments for optional SL/TP
            kwargs: dict[str, Any] = {}
            if sl is not None:
                kwargs["stopLoss"] = float(sl)
            if tp is not None:
                kwargs["takeProfit"] = float(tp)

            if direction == "buy":
                result = await self._connection.create_market_buy_order(
                    symbol.upper(), lot_size, **kwargs
                )
            else:
                result = await self._connection.create_market_sell_order(
                    symbol.upper(), lot_size, **kwargs
                )

            order_id = result.get("orderId") or result.get("positionId", "")
            entry_price = float(result.get("price", 0.0))
            status = result.get("stringCode", "filled")

            logger.info(
                "MetaApi order placed: %s %s %.2f lots @ $%.2f [SL=%s TP=%s] -> %s",
                direction.upper(),
                symbol,
                lot_size,
                entry_price,
                sl,
                tp,
                order_id,
            )

            return {
                "order_id": str(order_id),
                "entry_price": entry_price,
                "status": "filled" if "TRADE_RETCODE_DONE" in str(status) else str(status),
            }

        except Exception:
            logger.exception(
                "Failed to place %s %s order via MetaApi",
                direction, symbol,
            )
            return {"error": "Order execution failed", "status": "rejected"}

    async def modify_order(
        self,
        position_id: str,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> dict:
        """Modify the SL/TP of an open position.

        Args:
            position_id: The MetaTrader position identifier.
            sl: New stop-loss price (None = unchanged).
            tp: New take-profit price (None = unchanged).

        Returns:
            Dict with position_id, sl, tp, and status.
        """
        if not self._connected or self._connection is None:
            return {"error": "Not connected", "status": "rejected"}

        if sl is None and tp is None:
            return {
                "error": "At least one of sl or tp must be provided",
                "status": "rejected",
            }

        try:
            # Build modification kwargs — only pass values that were provided
            kwargs: dict[str, Any] = {}
            if sl is not None:
                kwargs["stopLoss"] = float(sl)
            if tp is not None:
                kwargs["takeProfit"] = float(tp)

            result = await self._connection.modify_position(
                position_id, **kwargs
            )

            status = result.get("stringCode", "modified") if result else "modified"

            logger.info(
                "MetaApi position %s modified: SL=%s, TP=%s",
                position_id, sl, tp,
            )

            return {
                "position_id": position_id,
                "sl": sl,
                "tp": tp,
                "status": "modified" if "TRADE_RETCODE_DONE" in str(status) else str(status),
            }

        except Exception:
            logger.exception(
                "Failed to modify MetaApi position %s", position_id
            )
            return {
                "error": f"Failed to modify position {position_id}",
                "position_id": position_id,
                "status": "rejected",
            }

    async def close_position(
        self, position_id: str, lot_size: Optional[float] = None
    ) -> dict:
        """Close an open position (fully or partially).

        Args:
            position_id: The MetaTrader position identifier.
            lot_size: Volume to close. None = close entire position.

        Returns:
            Dict with pnl, exit_price, and status.
        """
        if not self._connected or self._connection is None:
            return {"error": "Not connected", "status": "rejected"}

        try:
            if lot_size is not None and lot_size > 0:
                # Partial close
                result = await self._connection.close_position_partially(
                    position_id, lot_size
                )
                is_partial = True
            else:
                # Full close
                result = await self._connection.close_position(position_id)
                is_partial = False

            exit_price = float(result.get("price", 0.0)) if result else 0.0
            pnl = float(result.get("profit", 0.0)) if result else 0.0
            status_code = result.get("stringCode", "") if result else ""

            logger.info(
                "MetaApi position %s %s: exit=$%.2f, PnL=$%.2f",
                position_id,
                "partially closed" if is_partial else "closed",
                exit_price,
                pnl,
            )

            return {
                "pnl": pnl,
                "exit_price": exit_price,
                "status": (
                    "partial_close" if is_partial else "closed"
                ) if "TRADE_RETCODE_DONE" in str(status_code) else str(status_code or ("partial_close" if is_partial else "closed")),
            }

        except Exception:
            logger.exception(
                "Failed to close MetaApi position %s", position_id
            )
            return {
                "error": f"Failed to close position {position_id}",
                "pnl": 0.0,
                "exit_price": 0.0,
                "status": "rejected",
            }

    async def get_positions(self) -> list[dict]:
        """Retrieve all open positions from the MetaTrader terminal.

        Returns:
            List of position dicts with position_id, symbol, direction,
            lot_size, entry_price, sl, tp, pnl, and open_time.
        """
        if not self._connected or self._connection is None:
            return []

        try:
            positions = self._connection.terminal_state.positions
            if positions is None:
                return []

            result = []
            for pos in positions:
                result.append({
                    "position_id": str(pos.get("id", "")),
                    "symbol": str(pos.get("symbol", "")),
                    "direction": str(pos.get("type", "")).lower().replace(
                        "position_type_", ""
                    ),
                    "lot_size": float(pos.get("volume", 0.0)),
                    "entry_price": float(pos.get("openPrice", 0.0)),
                    "sl": pos.get("stopLoss"),
                    "tp": pos.get("takeProfit"),
                    "pnl": float(pos.get("profit", 0.0)),
                    "open_time": str(pos.get("time", "")),
                })

            return result

        except Exception:
            logger.exception("Failed to retrieve MetaApi positions")
            return []

    async def get_price(self, symbol: str = "XAUUSD") -> dict:
        """Get the current bid/ask price for a symbol.

        Args:
            symbol: Trading symbol. Defaults to "XAUUSD".

        Returns:
            Dict with bid, ask, spread, and timestamp.
        """
        if not self._connected or self._connection is None:
            return {"error": "Not connected"}

        try:
            price = await self._connection.get_symbol_price(symbol.upper())

            bid = float(price.get("bid", 0.0))
            ask = float(price.get("ask", 0.0))
            spread = round(ask - bid, 5) if bid and ask else 0.0
            timestamp = price.get("time")

            # Normalize timestamp to ISO string
            if isinstance(timestamp, datetime):
                timestamp = timestamp.isoformat()
            elif timestamp is None:
                timestamp = datetime.now(timezone.utc).isoformat()
            else:
                timestamp = str(timestamp)

            return {
                "bid": bid,
                "ask": ask,
                "spread": spread,
                "timestamp": timestamp,
            }

        except Exception:
            logger.exception(
                "Failed to get MetaApi price for %s", symbol
            )
            return {
                "error": f"Failed to get price for {symbol}",
                "bid": 0.0,
                "ask": 0.0,
                "spread": 0.0,
                "timestamp": None,
            }
