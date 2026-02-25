"""Demo (paper trading) broker adapter.

Provides a fully functional in-memory broker for testing and paper trading.
No real money is involved. Prices are simulated with realistic random
fluctuations around gold spot price.
"""
import logging
import random
import time
from datetime import datetime, timezone
from typing import Optional

from app.broker.connection import BrokerConnection

logger = logging.getLogger(__name__)


class DemoBrokerAdapter(BrokerConnection):
    """Paper trading broker — all state lives in memory.

    Simulates a real broker with realistic account management, order
    execution, and PnL calculation. The mock price starts at $2650.00
    and fluctuates randomly by +/-$0.50 on each call.
    """

    def __init__(self) -> None:
        self._connected: bool = False
        self._account: dict = {
            "balance": 10_000.00,
            "equity": 10_000.00,
            "margin": 0.0,
            "free_margin": 10_000.00,
            "leverage": 100,
            "currency": "USD",
        }
        self._positions: list[dict] = []
        self._order_counter: int = 0
        self._closed_trades: list[dict] = []

        # Price simulation state
        self._base_price: float = 2650.00
        self._last_bid: float = 2650.00
        self._spread: float = 0.30  # $0.30 spread for gold

    # ------------------------------------------------------------------
    # Price simulation
    # ------------------------------------------------------------------

    def _simulate_price(self) -> dict:
        """Generate a realistic mock gold price tick.

        The price random-walks by up to +/-$0.50 from the previous bid,
        clamped to stay within a reasonable range of the base price.
        """
        fluctuation = random.uniform(-0.50, 0.50)
        self._last_bid = round(self._last_bid + fluctuation, 2)

        # Keep price within +/-$50 of the base so it doesn't drift wildly
        if self._last_bid > self._base_price + 50.0:
            self._last_bid = self._base_price + 50.0
        elif self._last_bid < self._base_price - 50.0:
            self._last_bid = self._base_price - 50.0

        ask = round(self._last_bid + self._spread, 2)
        return {
            "bid": self._last_bid,
            "ask": ask,
            "spread": self._spread,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Equity / margin recalculation
    # ------------------------------------------------------------------

    def _recalculate_equity(self) -> None:
        """Recalculate equity, margin, and free_margin based on open positions."""
        price_data = self._simulate_price()
        total_pnl = 0.0
        total_margin = 0.0

        for pos in self._positions:
            current_price = (
                price_data["bid"] if pos["direction"] == "buy" else price_data["ask"]
            )
            if pos["direction"] == "buy":
                pnl = (current_price - pos["entry_price"]) * pos["lot_size"] * 100.0
            else:
                pnl = (pos["entry_price"] - current_price) * pos["lot_size"] * 100.0

            pos["pnl"] = round(pnl, 2)
            total_pnl += pnl

            # Margin = (price * lot_size * 100 oz) / leverage
            margin = (
                pos["entry_price"] * pos["lot_size"] * 100.0
            ) / self._account["leverage"]
            total_margin += margin

        self._account["equity"] = round(self._account["balance"] + total_pnl, 2)
        self._account["margin"] = round(total_margin, 2)
        self._account["free_margin"] = round(
            self._account["equity"] - self._account["margin"], 2
        )

    # ------------------------------------------------------------------
    # BrokerConnection implementation
    # ------------------------------------------------------------------

    async def connect(self, config: dict) -> bool:
        """Connect to the demo broker (always succeeds)."""
        initial_balance = config.get("initial_balance", 10_000.00)
        leverage = config.get("leverage", 100)

        self._account["balance"] = float(initial_balance)
        self._account["equity"] = float(initial_balance)
        self._account["free_margin"] = float(initial_balance)
        self._account["leverage"] = int(leverage)
        self._connected = True

        logger.info(
            "Demo broker connected — balance=$%.2f, leverage=%d",
            initial_balance,
            leverage,
        )
        return True

    async def disconnect(self) -> bool:
        """Disconnect from the demo broker."""
        self._connected = False
        logger.info("Demo broker disconnected")
        return True

    async def get_account_info(self) -> dict:
        """Return current account state with live equity calculation."""
        if not self._connected:
            return {"error": "Not connected", "status": "disconnected"}

        self._recalculate_equity()
        return {**self._account, "status": "connected"}

    async def place_order(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> dict:
        """Place a paper-trade market order."""
        if not self._connected:
            return {"error": "Not connected", "status": "rejected"}

        direction = direction.lower()
        if direction not in ("buy", "sell"):
            return {"error": f"Invalid direction: {direction}", "status": "rejected"}

        if lot_size <= 0:
            return {"error": "Lot size must be positive", "status": "rejected"}

        price_data = self._simulate_price()
        entry_price = price_data["ask"] if direction == "buy" else price_data["bid"]

        # Margin check
        margin_required = (entry_price * lot_size * 100.0) / self._account["leverage"]
        self._recalculate_equity()
        if margin_required > self._account["free_margin"]:
            logger.warning(
                "Insufficient margin: required=$%.2f, available=$%.2f",
                margin_required,
                self._account["free_margin"],
            )
            return {
                "error": "Insufficient margin",
                "margin_required": round(margin_required, 2),
                "free_margin": self._account["free_margin"],
                "status": "rejected",
            }

        self._order_counter += 1
        position_id = f"DEMO-{self._order_counter:06d}"

        position = {
            "position_id": position_id,
            "symbol": symbol.upper(),
            "direction": direction,
            "lot_size": lot_size,
            "entry_price": entry_price,
            "sl": sl,
            "tp": tp,
            "pnl": 0.0,
            "open_time": datetime.now(timezone.utc).isoformat(),
        }
        self._positions.append(position)
        self._recalculate_equity()

        logger.info(
            "Order placed: %s %s %.2f lots @ $%.2f [SL=%s TP=%s]",
            direction.upper(),
            symbol,
            lot_size,
            entry_price,
            sl,
            tp,
        )
        return {
            "order_id": position_id,
            "entry_price": entry_price,
            "status": "filled",
        }

    async def modify_order(
        self,
        position_id: str,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
    ) -> dict:
        """Modify SL/TP on an open paper-trade position."""
        if not self._connected:
            return {"error": "Not connected", "status": "rejected"}

        for pos in self._positions:
            if pos["position_id"] == position_id:
                if sl is not None:
                    pos["sl"] = sl
                if tp is not None:
                    pos["tp"] = tp
                logger.info(
                    "Position %s modified: SL=%s, TP=%s",
                    position_id,
                    pos["sl"],
                    pos["tp"],
                )
                return {
                    "position_id": position_id,
                    "sl": pos["sl"],
                    "tp": pos["tp"],
                    "status": "modified",
                }

        return {"error": f"Position {position_id} not found", "status": "rejected"}

    async def close_position(
        self, position_id: str, lot_size: Optional[float] = None
    ) -> dict:
        """Close (fully or partially) a paper-trade position."""
        if not self._connected:
            return {"error": "Not connected", "status": "rejected"}

        for i, pos in enumerate(self._positions):
            if pos["position_id"] != position_id:
                continue

            price_data = self._simulate_price()
            exit_price = (
                price_data["bid"] if pos["direction"] == "buy" else price_data["ask"]
            )

            close_lots = lot_size if lot_size and lot_size < pos["lot_size"] else pos["lot_size"]
            is_partial = lot_size is not None and lot_size < pos["lot_size"]

            # PnL for closed portion: (price_diff) * lots * 100 oz
            if pos["direction"] == "buy":
                pnl = (exit_price - pos["entry_price"]) * close_lots * 100.0
            else:
                pnl = (pos["entry_price"] - exit_price) * close_lots * 100.0

            pnl = round(pnl, 2)

            if is_partial:
                # Reduce lot size, keep position open
                pos["lot_size"] = round(pos["lot_size"] - close_lots, 2)
                logger.info(
                    "Partial close %s: %.2f lots @ $%.2f, PnL=$%.2f (remaining=%.2f lots)",
                    position_id,
                    close_lots,
                    exit_price,
                    pnl,
                    pos["lot_size"],
                )
            else:
                # Full close
                self._positions.pop(i)
                logger.info(
                    "Position %s closed: %.2f lots @ $%.2f, PnL=$%.2f",
                    position_id,
                    close_lots,
                    exit_price,
                    pnl,
                )

            # Apply PnL to balance
            self._account["balance"] = round(self._account["balance"] + pnl, 2)
            self._recalculate_equity()

            closed_record = {
                "position_id": position_id,
                "exit_price": exit_price,
                "pnl": pnl,
                "close_lots": close_lots,
                "partial": is_partial,
                "close_time": datetime.now(timezone.utc).isoformat(),
            }
            self._closed_trades.append(closed_record)

            return {
                "pnl": pnl,
                "exit_price": exit_price,
                "status": "partial_close" if is_partial else "closed",
            }

        return {"error": f"Position {position_id} not found", "status": "rejected"}

    async def get_positions(self) -> list[dict]:
        """Return all open paper-trade positions with live PnL."""
        if not self._connected:
            return []

        self._recalculate_equity()
        return [dict(pos) for pos in self._positions]

    async def get_price(self, symbol: str = "XAUUSD") -> dict:
        """Get current simulated gold price."""
        if not self._connected:
            return {"error": "Not connected"}

        return self._simulate_price()
