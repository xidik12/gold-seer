"""Pre-trade risk management for gold (XAUUSD) trading.

Enforces risk limits before any order reaches the broker. All checks
run server-side regardless of execution mode.
"""
import logging
from datetime import datetime, timezone

from app.broker.lot_calculator import GoldLotCalculator

logger = logging.getLogger(__name__)


class RiskManager:
    """Pre-trade risk gate for XAUUSD positions.

    Gold-specific constants:
        Pip size:  $0.01 (one cent movement in gold price)
        Pip value: $1.00 per standard lot (100 troy ounces)
    """

    PIP_SIZE: float = 0.01
    PIP_VALUE_PER_LOT: float = 1.0

    # Default risk parameters (can be overridden via config)
    DEFAULT_MAX_DAILY_LOSS_PCT: float = 5.0      # 5% of balance
    DEFAULT_MAX_OPEN_POSITIONS: int = 5
    DEFAULT_MAX_LOT_SIZE: float = 5.0             # 5 standard lots
    DEFAULT_MIN_LOT_SIZE: float = 0.01            # 1 micro lot
    DEFAULT_MAX_RISK_PER_TRADE_PCT: float = 2.0   # 2% per trade
    DEFAULT_MIN_FREE_MARGIN_PCT: float = 50.0     # 50% margin level

    async def check_trade(
        self,
        account_info: dict,
        trade_plan: dict,
        positions: list,
        config: dict,
    ) -> dict:
        """Run all pre-trade risk checks.

        Args:
            account_info: Current account state (balance, equity, margin, etc.).
            trade_plan: Proposed trade (direction, lot_size, sl, tp, etc.).
            positions: List of currently open positions.
            config: Risk configuration overrides.

        Returns:
            Dict with:
                approved (bool): Whether the trade passes all checks.
                reason (str): Explanation if rejected (empty string if approved).
                adjusted_lot_size (float): Possibly reduced lot size to fit limits.
                checks (list): Details of each check performed.
        """
        checks: list[dict] = []
        lot_size = trade_plan.get("lot_size", 0.01)
        balance = account_info.get("balance", 0)
        equity = account_info.get("equity", 0)
        free_margin = account_info.get("free_margin", 0)
        leverage = account_info.get("leverage", 100)

        # ----- Check 1: Market hours -----
        market_open = self.is_market_open()
        checks.append({
            "check": "market_hours",
            "passed": market_open,
            "detail": "Gold market open" if market_open else "Gold market closed (weekend)",
        })
        if not market_open:
            return self._reject("Market is closed. Gold trades Mon 00:00 - Fri 22:00 UTC.", checks)

        # ----- Check 2: Lot size limits -----
        max_lot = config.get("max_lot_size", self.DEFAULT_MAX_LOT_SIZE)
        min_lot = config.get("min_lot_size", self.DEFAULT_MIN_LOT_SIZE)

        if lot_size < min_lot:
            checks.append({
                "check": "lot_size_min",
                "passed": False,
                "detail": f"Lot size {lot_size} below minimum {min_lot}",
            })
            return self._reject(f"Lot size {lot_size} is below minimum {min_lot}.", checks)

        if lot_size > max_lot:
            lot_size = max_lot
            checks.append({
                "check": "lot_size_max",
                "passed": True,
                "detail": f"Lot size capped to maximum {max_lot}",
            })
        else:
            checks.append({
                "check": "lot_size",
                "passed": True,
                "detail": f"Lot size {lot_size} within limits [{min_lot}, {max_lot}]",
            })

        # ----- Check 3: Max open positions -----
        max_positions = config.get("max_open_positions", self.DEFAULT_MAX_OPEN_POSITIONS)
        current_count = len(positions)
        position_ok = current_count < max_positions
        checks.append({
            "check": "max_positions",
            "passed": position_ok,
            "detail": f"{current_count}/{max_positions} positions open",
        })
        if not position_ok:
            return self._reject(
                f"Maximum open positions reached ({current_count}/{max_positions}).",
                checks,
            )

        # ----- Check 4: Per-trade risk limit -----
        max_risk_pct = config.get("max_risk_per_trade_pct", self.DEFAULT_MAX_RISK_PER_TRADE_PCT)
        sl = trade_plan.get("sl")
        entry_price = trade_plan.get("entry_price", 0)

        if sl and balance > 0:
            sl_pips = abs(entry_price - sl) / self.PIP_SIZE
            risk_usd = GoldLotCalculator.pips_to_usd(sl_pips, lot_size)
            risk_pct_actual = (risk_usd / balance) * 100.0

            if risk_pct_actual > max_risk_pct:
                # Reduce lot size to fit within risk limit
                max_risk_usd = balance * (max_risk_pct / 100.0)
                if sl_pips > 0:
                    adjusted_lot = max_risk_usd / (sl_pips * self.PIP_VALUE_PER_LOT)
                    lot_size = round(max(adjusted_lot, min_lot), 2)

                checks.append({
                    "check": "per_trade_risk",
                    "passed": True,
                    "detail": (
                        f"Risk {risk_pct_actual:.1f}% exceeds {max_risk_pct}%. "
                        f"Lot size adjusted to {lot_size}"
                    ),
                })
            else:
                checks.append({
                    "check": "per_trade_risk",
                    "passed": True,
                    "detail": f"Risk {risk_pct_actual:.1f}% within {max_risk_pct}% limit",
                })
        else:
            checks.append({
                "check": "per_trade_risk",
                "passed": True,
                "detail": "No SL set or zero balance — risk check skipped",
            })

        # ----- Check 5: Margin requirement -----
        min_free_margin_pct = config.get(
            "min_free_margin_pct", self.DEFAULT_MIN_FREE_MARGIN_PCT
        )
        margin_required = GoldLotCalculator.calculate_margin_required(
            price=entry_price, lot_size=lot_size, leverage=leverage
        )
        margin_after = free_margin - margin_required
        margin_level_after = 0.0
        total_margin = account_info.get("margin", 0) + margin_required
        if total_margin > 0:
            margin_level_after = (equity / total_margin) * 100.0

        margin_ok = margin_after > 0 and (
            margin_level_after >= min_free_margin_pct or total_margin == 0
        )
        checks.append({
            "check": "margin_requirement",
            "passed": margin_ok,
            "detail": (
                f"Margin required: ${margin_required:.2f}, "
                f"free margin after: ${margin_after:.2f}, "
                f"margin level: {margin_level_after:.1f}%"
            ),
        })
        if not margin_ok:
            return self._reject(
                f"Insufficient margin. Required: ${margin_required:.2f}, "
                f"available: ${free_margin:.2f}.",
                checks,
            )

        # ----- Check 6: Daily loss limit -----
        max_daily_loss_pct = config.get(
            "max_daily_loss_pct", self.DEFAULT_MAX_DAILY_LOSS_PCT
        )
        daily_pnl = self._calculate_daily_pnl(positions)
        daily_loss_pct = abs(min(daily_pnl, 0)) / balance * 100.0 if balance > 0 else 0.0

        daily_loss_ok = daily_loss_pct < max_daily_loss_pct
        checks.append({
            "check": "daily_loss_limit",
            "passed": daily_loss_ok,
            "detail": (
                f"Daily PnL: ${daily_pnl:.2f} ({daily_loss_pct:.1f}% loss), "
                f"limit: {max_daily_loss_pct}%"
            ),
        })
        if not daily_loss_ok:
            return self._reject(
                f"Daily loss limit reached ({daily_loss_pct:.1f}% >= {max_daily_loss_pct}%).",
                checks,
            )

        # All checks passed
        logger.info("Risk checks passed: %d checks, lot_size=%.2f", len(checks), lot_size)
        return {
            "approved": True,
            "reason": "",
            "adjusted_lot_size": lot_size,
            "checks": checks,
        }

    def calculate_lot_size(
        self, account_balance: float, risk_pct: float, sl_pips: float
    ) -> float:
        """Calculate lot size based on account risk.

        Formula: risk_amount / (sl_pips * pip_value_per_lot)

        Args:
            account_balance: Account balance in USD.
            risk_pct: Percentage of balance to risk (e.g. 1.0 = 1%).
            sl_pips: Stop-loss distance in pips.

        Returns:
            Lot size rounded to 2 decimal places, minimum 0.01.
        """
        if sl_pips <= 0 or account_balance <= 0:
            return 0.01

        risk_amount = account_balance * (risk_pct / 100.0)
        lot_size = risk_amount / (sl_pips * self.PIP_VALUE_PER_LOT)
        return max(round(lot_size, 2), 0.01)

    def is_market_open(self) -> bool:
        """Check if the gold market is currently open.

        Gold (XAUUSD) trades from Monday 00:00 UTC to Friday 22:00 UTC.
        Weekday numbering: Monday=0, Sunday=6.

        Returns:
            True if market is open, False if it's the weekend.
        """
        now = datetime.now(timezone.utc)
        weekday = now.weekday()  # Mon=0, Sun=6

        # Saturday (5) — always closed
        if weekday == 5:
            return False

        # Sunday (6) — always closed
        if weekday == 6:
            return False

        # Friday — closes at 22:00 UTC
        if weekday == 4 and now.hour >= 22:
            return False

        return True

    @staticmethod
    def _calculate_daily_pnl(positions: list) -> float:
        """Sum PnL of positions opened today."""
        today = datetime.now(timezone.utc).date()
        daily_pnl = 0.0
        for pos in positions:
            open_time_str = pos.get("open_time", "")
            if open_time_str:
                try:
                    open_time = datetime.fromisoformat(open_time_str)
                    if open_time.date() == today:
                        daily_pnl += pos.get("pnl", 0.0)
                except (ValueError, TypeError):
                    pass
            else:
                # If no open_time, include it conservatively
                daily_pnl += pos.get("pnl", 0.0)
        return daily_pnl

    @staticmethod
    def _reject(reason: str, checks: list) -> dict:
        """Build a rejection response."""
        logger.warning("Trade rejected: %s", reason)
        return {
            "approved": False,
            "reason": reason,
            "adjusted_lot_size": 0.0,
            "checks": checks,
        }
