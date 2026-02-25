"""Position management — automated rules for open gold positions.

Runs periodic management logic against open positions to enforce
profit-taking, trailing stops, and time-based cleanup rules.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.broker.connection import BrokerConnection
from app.broker.lot_calculator import GoldLotCalculator

logger = logging.getLogger(__name__)


class PositionManager:
    """Manages open XAUUSD positions with automated rules.

    Rules applied (in order):
        1. Breakeven: Move SL to entry when price moves 1.5x SL distance in profit.
        2. Partial close: Close 50% at TP1 (first take-profit target).
        3. Trailing stop: After TP1 hit, trail SL at 2x ATR ($6 default).
        4. Time-based close: Close stale positions (>48h with < $5 PnL).
    """

    # Default parameters
    DEFAULT_BREAKEVEN_MULTIPLIER: float = 1.5
    DEFAULT_PARTIAL_CLOSE_PCT: float = 0.50       # 50% at TP1
    DEFAULT_TRAILING_STOP_USD: float = 6.00       # 2x ATR default for gold
    DEFAULT_MAX_POSITION_HOURS: int = 48
    DEFAULT_STALE_PNL_THRESHOLD: float = 5.00     # $5 PnL threshold

    def __init__(
        self,
        breakeven_multiplier: float = DEFAULT_BREAKEVEN_MULTIPLIER,
        partial_close_pct: float = DEFAULT_PARTIAL_CLOSE_PCT,
        trailing_stop_usd: float = DEFAULT_TRAILING_STOP_USD,
        max_position_hours: int = DEFAULT_MAX_POSITION_HOURS,
        stale_pnl_threshold: float = DEFAULT_STALE_PNL_THRESHOLD,
    ) -> None:
        self.breakeven_multiplier = breakeven_multiplier
        self.partial_close_pct = partial_close_pct
        self.trailing_stop_usd = trailing_stop_usd
        self.max_position_hours = max_position_hours
        self.stale_pnl_threshold = stale_pnl_threshold

        # Track which positions have had TP1 hit (partial close done)
        self._tp1_hit: set[str] = set()

    async def manage_positions(
        self, broker: BrokerConnection, positions: list
    ) -> list[dict]:
        """Run all position management rules.

        Args:
            broker: Connected BrokerConnection instance.
            positions: List of open position dicts from broker.get_positions().

        Returns:
            List of action dicts describing what was done (or attempted).
        """
        actions: list[dict] = []

        for pos in positions:
            position_id = pos.get("position_id", "unknown")

            try:
                price_data = await broker.get_price(pos.get("symbol", "XAUUSD"))
                if "error" in price_data:
                    continue

                current_price = (
                    price_data["bid"]
                    if pos.get("direction") == "buy"
                    else price_data["ask"]
                )

                # Rule 1: Breakeven
                action = await self._check_breakeven(broker, pos, current_price)
                if action:
                    actions.append(action)

                # Rule 2: Partial close at TP1
                action = await self._check_partial_close(broker, pos, current_price)
                if action:
                    actions.append(action)

                # Rule 3: Trailing stop (after TP1)
                action = await self._check_trailing_stop(broker, pos, current_price)
                if action:
                    actions.append(action)

                # Rule 4: Time-based close
                action = await self._check_time_based_close(broker, pos)
                if action:
                    actions.append(action)

            except Exception as exc:
                logger.exception(
                    "Error managing position %s: %s", position_id, exc
                )
                actions.append({
                    "position_id": position_id,
                    "action": "error",
                    "detail": str(exc),
                })

        if actions:
            logger.info(
                "Position manager completed: %d actions on %d positions",
                len(actions),
                len(positions),
            )

        return actions

    async def _check_breakeven(
        self, broker: BrokerConnection, pos: dict, current_price: float
    ) -> Optional[dict]:
        """Rule 1: Move SL to breakeven when price moves 1.5x SL distance in profit.

        Only triggers once per position (when SL is still below entry for buys,
        or above entry for sells).
        """
        position_id = pos["position_id"]
        entry_price = pos.get("entry_price", 0)
        sl = pos.get("sl")
        direction = pos.get("direction", "")

        if not sl or not entry_price:
            return None

        sl_distance = abs(entry_price - sl)
        breakeven_distance = sl_distance * self.breakeven_multiplier

        if direction == "buy":
            # SL already at or above entry = breakeven already done
            if sl >= entry_price:
                return None
            profit_distance = current_price - entry_price
            if profit_distance >= breakeven_distance:
                # Move SL to entry + 1 pip (small buffer)
                new_sl = round(entry_price + GoldLotCalculator.PIP_SIZE, 2)
                result = await broker.modify_order(position_id, sl=new_sl)
                logger.info(
                    "Breakeven triggered for %s: SL moved to $%.2f",
                    position_id,
                    new_sl,
                )
                return {
                    "position_id": position_id,
                    "action": "breakeven",
                    "new_sl": new_sl,
                    "result": result,
                }

        elif direction == "sell":
            # SL already at or below entry = breakeven already done
            if sl <= entry_price:
                return None
            profit_distance = entry_price - current_price
            if profit_distance >= breakeven_distance:
                new_sl = round(entry_price - GoldLotCalculator.PIP_SIZE, 2)
                result = await broker.modify_order(position_id, sl=new_sl)
                logger.info(
                    "Breakeven triggered for %s: SL moved to $%.2f",
                    position_id,
                    new_sl,
                )
                return {
                    "position_id": position_id,
                    "action": "breakeven",
                    "new_sl": new_sl,
                    "result": result,
                }

        return None

    async def _check_partial_close(
        self, broker: BrokerConnection, pos: dict, current_price: float
    ) -> Optional[dict]:
        """Rule 2: Close 50% at TP1 (first take-profit target).

        TP1 is typically set as the 'tp' field or a dedicated 'tp1' field.
        Only triggers once per position (tracked via _tp1_hit set).
        """
        position_id = pos["position_id"]

        # Skip if already partially closed
        if position_id in self._tp1_hit:
            return None

        tp1 = pos.get("tp1") or pos.get("tp")
        if not tp1:
            return None

        direction = pos.get("direction", "")
        lot_size = pos.get("lot_size", 0)
        hit = False

        if direction == "buy" and current_price >= tp1:
            hit = True
        elif direction == "sell" and current_price <= tp1:
            hit = True

        if hit:
            close_lots = round(lot_size * self.partial_close_pct, 2)
            close_lots = max(close_lots, 0.01)  # Minimum micro lot

            result = await broker.close_position(position_id, lot_size=close_lots)
            self._tp1_hit.add(position_id)
            logger.info(
                "TP1 partial close for %s: closed %.2f lots at $%.2f",
                position_id,
                close_lots,
                current_price,
            )
            return {
                "position_id": position_id,
                "action": "partial_close_tp1",
                "closed_lots": close_lots,
                "price": current_price,
                "result": result,
            }

        return None

    async def _check_trailing_stop(
        self, broker: BrokerConnection, pos: dict, current_price: float
    ) -> Optional[dict]:
        """Rule 3: After TP1 hit, apply trailing stop at 2x ATR ($6 default).

        The trailing stop follows price in the profitable direction but
        never moves backward.
        """
        position_id = pos["position_id"]

        # Only trail after TP1 has been hit
        if position_id not in self._tp1_hit:
            return None

        sl = pos.get("sl")
        direction = pos.get("direction", "")

        if direction == "buy":
            ideal_sl = round(current_price - self.trailing_stop_usd, 2)
            if sl is None or ideal_sl > sl:
                result = await broker.modify_order(position_id, sl=ideal_sl)
                logger.info(
                    "Trailing stop for %s: SL moved to $%.2f (price $%.2f)",
                    position_id,
                    ideal_sl,
                    current_price,
                )
                return {
                    "position_id": position_id,
                    "action": "trailing_stop",
                    "new_sl": ideal_sl,
                    "current_price": current_price,
                    "result": result,
                }

        elif direction == "sell":
            ideal_sl = round(current_price + self.trailing_stop_usd, 2)
            if sl is None or ideal_sl < sl:
                result = await broker.modify_order(position_id, sl=ideal_sl)
                logger.info(
                    "Trailing stop for %s: SL moved to $%.2f (price $%.2f)",
                    position_id,
                    ideal_sl,
                    current_price,
                )
                return {
                    "position_id": position_id,
                    "action": "trailing_stop",
                    "new_sl": ideal_sl,
                    "current_price": current_price,
                    "result": result,
                }

        return None

    async def _check_time_based_close(
        self, broker: BrokerConnection, pos: dict
    ) -> Optional[dict]:
        """Rule 4: Close positions older than 48h with small PnL (< $5).

        Frees up margin and avoids positions that are going nowhere.
        """
        position_id = pos["position_id"]
        open_time_str = pos.get("open_time", "")
        pnl = pos.get("pnl", 0.0)

        if not open_time_str:
            return None

        try:
            open_time = datetime.fromisoformat(open_time_str)
        except (ValueError, TypeError):
            return None

        now = datetime.now(timezone.utc)
        # Ensure open_time is timezone-aware
        if open_time.tzinfo is None:
            open_time = open_time.replace(tzinfo=timezone.utc)

        hours_open = (now - open_time).total_seconds() / 3600.0

        if hours_open >= self.max_position_hours and abs(pnl) < self.stale_pnl_threshold:
            result = await broker.close_position(position_id)
            logger.info(
                "Time-based close for %s: open %.1fh, PnL=$%.2f",
                position_id,
                hours_open,
                pnl,
            )
            return {
                "position_id": position_id,
                "action": "time_based_close",
                "hours_open": round(hours_open, 1),
                "pnl": pnl,
                "result": result,
            }

        return None

    def reset_tracking(self) -> None:
        """Reset internal state (e.g. after all positions are closed)."""
        self._tp1_hit.clear()
