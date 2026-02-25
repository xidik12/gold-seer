"""Copy trade manager — replicates AI advisor signals to subscriber accounts.

Allows Griffin Gold to operate as a signal provider where subscribers
(other trader accounts) can automatically receive and execute the same
trades as the AI advisor, with configurable lot scaling and limits.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.broker.connection import BrokerConnection
from app.broker.lot_calculator import GoldLotCalculator

logger = logging.getLogger(__name__)


class CopyTradeManager:
    """Copies AI advisor signals to subscriber broker accounts.

    Each subscriber has a profile dict:
        - subscriber_id: Unique identifier
        - lot_multiplier: Lot scaling factor (e.g. 0.5 = half the signal size)
        - max_lot_size: Maximum lot size per trade for this subscriber
        - max_daily_trades: Maximum number of copy trades per day
        - max_daily_loss_usd: Maximum daily loss allowed in USD
        - enabled: Whether copy trading is active
        - trades_today: Counter of trades placed today (managed internally)
        - daily_pnl: Running PnL for the day (managed internally)
    """

    def __init__(self) -> None:
        self._copy_log: list[dict] = []
        self._subscriber_state: dict[str, dict] = {}

    async def copy_signal(
        self,
        signal: dict,
        subscriber: dict,
        broker: BrokerConnection,
    ) -> dict:
        """Copy an AI advisor signal to a subscriber's broker account.

        Args:
            signal: The trade signal dict (direction, symbol, sl, tp, lot_size, etc.).
            subscriber: Subscriber profile dict.
            broker: Connected BrokerConnection for the subscriber's account.

        Returns:
            Dict with copy result: order details or rejection reason.
        """
        subscriber_id = subscriber.get("subscriber_id", "unknown")

        # Initialize subscriber state if needed
        if subscriber_id not in self._subscriber_state:
            self._subscriber_state[subscriber_id] = {
                "trades_today": 0,
                "daily_pnl": 0.0,
                "last_reset_date": datetime.now(timezone.utc).date().isoformat(),
            }

        state = self._subscriber_state[subscriber_id]

        # Reset daily counters if new day
        today = datetime.now(timezone.utc).date().isoformat()
        if state["last_reset_date"] != today:
            state["trades_today"] = 0
            state["daily_pnl"] = 0.0
            state["last_reset_date"] = today

        # ----- Pre-copy checks -----

        # Check 1: Subscriber enabled
        if not subscriber.get("enabled", True):
            return self._reject(subscriber_id, "Copy trading is disabled for this subscriber.")

        # Check 2: Daily trade limit
        max_daily_trades = subscriber.get("max_daily_trades", 10)
        if state["trades_today"] >= max_daily_trades:
            return self._reject(
                subscriber_id,
                f"Daily trade limit reached ({state['trades_today']}/{max_daily_trades}).",
            )

        # Check 3: Daily loss limit
        max_daily_loss = subscriber.get("max_daily_loss_usd", 500.0)
        if state["daily_pnl"] < 0 and abs(state["daily_pnl"]) >= max_daily_loss:
            return self._reject(
                subscriber_id,
                f"Daily loss limit reached (${abs(state['daily_pnl']):.2f} >= ${max_daily_loss:.2f}).",
            )

        # ----- Calculate subscriber lot size -----

        original_lot_size = signal.get("lot_size", 0.01)
        lot_multiplier = subscriber.get("lot_multiplier", 1.0)
        max_lot_size = subscriber.get("max_lot_size", 5.0)

        subscriber_lot_size = round(original_lot_size * lot_multiplier, 2)
        subscriber_lot_size = max(subscriber_lot_size, 0.01)  # Minimum micro lot
        subscriber_lot_size = min(subscriber_lot_size, max_lot_size)

        # Check 4: Margin check on subscriber account
        account_info = await broker.get_account_info()
        if account_info.get("status") == "not_configured" or "error" in account_info:
            return self._reject(subscriber_id, f"Broker not available: {account_info.get('error', 'unknown')}")

        entry_estimate = signal.get("entry_price", 2650.0)
        leverage = account_info.get("leverage", 100)
        margin_required = GoldLotCalculator.calculate_margin_required(
            price=entry_estimate,
            lot_size=subscriber_lot_size,
            leverage=leverage,
        )
        free_margin = account_info.get("free_margin", 0)

        if margin_required > free_margin:
            return self._reject(
                subscriber_id,
                f"Insufficient margin: required ${margin_required:.2f}, available ${free_margin:.2f}.",
            )

        # ----- Execute the copy trade -----

        symbol = signal.get("symbol", "XAUUSD")
        direction = signal.get("direction", "buy")
        sl = signal.get("sl")
        tp = signal.get("tp")

        try:
            result = await broker.place_order(
                symbol=symbol,
                direction=direction,
                lot_size=subscriber_lot_size,
                sl=sl,
                tp=tp,
            )
        except Exception as exc:
            logger.exception(
                "Copy trade failed for subscriber %s: %s", subscriber_id, exc
            )
            return {
                "subscriber_id": subscriber_id,
                "status": "error",
                "error": str(exc),
            }

        # Update subscriber state
        if result.get("status") == "filled":
            state["trades_today"] += 1
            logger.info(
                "Copy trade executed for %s: %s %s %.2f lots (original: %.2f lots, multiplier: %.1fx)",
                subscriber_id,
                direction.upper(),
                symbol,
                subscriber_lot_size,
                original_lot_size,
                lot_multiplier,
            )
        else:
            logger.warning(
                "Copy trade rejected by broker for %s: %s",
                subscriber_id,
                result.get("error", "unknown"),
            )

        copy_record = {
            "subscriber_id": subscriber_id,
            "original_signal": signal,
            "subscriber_lot_size": subscriber_lot_size,
            "lot_multiplier": lot_multiplier,
            "order_result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._copy_log.append(copy_record)

        return {
            "subscriber_id": subscriber_id,
            "status": result.get("status", "error"),
            "order_id": result.get("order_id"),
            "entry_price": result.get("entry_price"),
            "lot_size": subscriber_lot_size,
            "original_lot_size": original_lot_size,
            "multiplier": lot_multiplier,
        }

    def update_subscriber_pnl(self, subscriber_id: str, pnl: float) -> None:
        """Update a subscriber's daily PnL (called when a copy trade closes).

        Args:
            subscriber_id: The subscriber identifier.
            pnl: Realized PnL from the closed trade.
        """
        if subscriber_id in self._subscriber_state:
            self._subscriber_state[subscriber_id]["daily_pnl"] += pnl
            logger.info(
                "Subscriber %s daily PnL updated: +$%.2f (total: $%.2f)",
                subscriber_id,
                pnl,
                self._subscriber_state[subscriber_id]["daily_pnl"],
            )

    def get_subscriber_stats(self, subscriber_id: str) -> Optional[dict]:
        """Get current daily stats for a subscriber.

        Returns:
            Dict with trades_today, daily_pnl, last_reset_date, or None.
        """
        return self._subscriber_state.get(subscriber_id)

    @property
    def copy_log(self) -> list[dict]:
        """Return the full copy trade log."""
        return list(self._copy_log)

    def _reject(self, subscriber_id: str, reason: str) -> dict:
        """Build a copy trade rejection response."""
        logger.warning("Copy trade rejected for %s: %s", subscriber_id, reason)
        return {
            "subscriber_id": subscriber_id,
            "status": "rejected",
            "reason": reason,
        }
