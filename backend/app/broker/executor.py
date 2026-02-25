"""Signal executor — converts AI signals into broker orders.

The SignalExecutor sits between the AI advisor (which produces trade
signals) and the broker connection (which executes orders). It supports
three execution modes:

- manual_approve: Returns an execution plan for human review. No order placed.
- semi_auto: Places the order but requires confirmation for exits/modifications.
- fully_auto: Places and manages orders without human intervention.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.broker.connection import BrokerConnection
from app.broker.lot_calculator import GoldLotCalculator
from app.broker.risk_manager import RiskManager

logger = logging.getLogger(__name__)


class SignalExecutor:
    """Converts AI trading signals into executable broker orders.

    A signal dict is expected to contain:
        - direction: "buy" or "sell"
        - symbol: "XAUUSD" (default)
        - entry_price: suggested entry (market if not specified)
        - sl: stop-loss price
        - tp: take-profit price (or tp1/tp2/tp3 for multi-target)
        - confidence: 0.0-1.0 AI confidence score
        - risk_pct: account risk percentage (default from config)
    """

    def __init__(self, risk_manager: Optional[RiskManager] = None) -> None:
        self._risk_manager = risk_manager or RiskManager()
        self._execution_log: list[dict] = []

    async def execute_signal(
        self,
        signal: dict,
        broker: BrokerConnection,
        execution_mode: str = "manual_approve",
    ) -> dict:
        """Execute an AI trading signal through the broker.

        Args:
            signal: AI signal dict with direction, sl, tp, confidence, etc.
            broker: Connected BrokerConnection instance.
            execution_mode: One of "manual_approve", "semi_auto", "fully_auto".

        Returns:
            Dict with execution result: plan (manual), order details (auto),
            or rejection reason.
        """
        if execution_mode not in ("manual_approve", "semi_auto", "fully_auto"):
            return {
                "error": f"Invalid execution_mode: {execution_mode}",
                "status": "rejected",
            }

        # 1. Build the execution plan
        plan = await self._build_plan(signal, broker)
        if plan.get("status") == "rejected":
            return plan

        # 2. Run risk checks
        account_info = await broker.get_account_info()
        positions = await broker.get_positions()
        risk_config = signal.get("risk_config", {})

        risk_result = await self._risk_manager.check_trade(
            account_info=account_info,
            trade_plan=plan,
            positions=positions,
            config=risk_config,
        )

        if not risk_result["approved"]:
            logger.warning("Risk check rejected signal: %s", risk_result["reason"])
            return {
                "status": "rejected",
                "reason": risk_result["reason"],
                "plan": plan,
                "risk_result": risk_result,
            }

        # Use risk-adjusted lot size if provided
        if risk_result.get("adjusted_lot_size"):
            plan["lot_size"] = risk_result["adjusted_lot_size"]

        # 3. Execute based on mode
        if execution_mode == "manual_approve":
            return await self._manual_approve(plan, risk_result)
        elif execution_mode == "semi_auto":
            return await self._semi_auto(plan, broker, risk_result)
        else:
            return await self._fully_auto(plan, broker, risk_result)

    async def _build_plan(self, signal: dict, broker: BrokerConnection) -> dict:
        """Build an execution plan from the signal."""
        symbol = signal.get("symbol", "XAUUSD")
        direction = signal.get("direction", "").lower()

        if direction not in ("buy", "sell"):
            return {"status": "rejected", "error": f"Invalid direction: {direction}"}

        # Get current price
        price_data = await broker.get_price(symbol)
        if "error" in price_data:
            return {"status": "rejected", "error": price_data["error"]}

        entry_price = (
            price_data["ask"] if direction == "buy" else price_data["bid"]
        )

        sl = signal.get("sl")
        tp = signal.get("tp")
        tp1 = signal.get("tp1")
        tp2 = signal.get("tp2")
        tp3 = signal.get("tp3")

        # Calculate SL distance in pips for lot sizing
        sl_pips = 0.0
        if sl:
            sl_pips = abs(entry_price - sl) / GoldLotCalculator.PIP_SIZE

        # Calculate lot size
        account_info = await broker.get_account_info()
        risk_pct = signal.get("risk_pct", 1.0)  # Default 1% risk

        lot_size = signal.get("lot_size")
        if not lot_size and sl_pips > 0:
            lot_size = GoldLotCalculator.calculate_lot_size(
                balance=account_info.get("balance", 0),
                risk_pct=risk_pct,
                sl_pips=sl_pips,
                leverage=account_info.get("leverage", 100),
            )
        elif not lot_size:
            lot_size = 0.01  # Minimum micro lot fallback

        # Risk/reward calculation
        rr_ratio = None
        if sl and tp:
            risk_distance = abs(entry_price - sl)
            reward_distance = abs(tp - entry_price)
            if risk_distance > 0:
                rr_ratio = round(reward_distance / risk_distance, 2)

        confidence = signal.get("confidence", 0.0)

        plan = {
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "lot_size": round(lot_size, 2),
            "sl": sl,
            "tp": tp,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "sl_pips": round(sl_pips, 1),
            "risk_pct": risk_pct,
            "rr_ratio": rr_ratio,
            "confidence": confidence,
            "potential_loss": round(
                GoldLotCalculator.pips_to_usd(sl_pips, lot_size), 2
            ) if sl_pips > 0 else None,
            "potential_profit": round(
                GoldLotCalculator.pips_to_usd(
                    abs(tp - entry_price) / GoldLotCalculator.PIP_SIZE, lot_size
                ),
                2,
            ) if tp else None,
            "spread": price_data.get("spread", 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "planned",
        }
        return plan

    async def _manual_approve(self, plan: dict, risk_result: dict) -> dict:
        """Manual approve mode: return the plan for human review."""
        logger.info(
            "Signal plan ready for approval: %s %s %.2f lots @ $%.2f",
            plan["direction"].upper(),
            plan["symbol"],
            plan["lot_size"],
            plan["entry_price"],
        )
        return {
            "status": "pending_approval",
            "plan": plan,
            "risk_result": risk_result,
            "message": "Trade plan ready for manual approval.",
        }

    async def _semi_auto(
        self, plan: dict, broker: BrokerConnection, risk_result: dict
    ) -> dict:
        """Semi-auto mode: place entry, require confirmation for exits."""
        result = await self._place_order_from_plan(plan, broker)
        result["risk_result"] = risk_result
        result["mode"] = "semi_auto"
        result["note"] = "Order placed. Exits require manual confirmation."
        return result

    async def _fully_auto(
        self, plan: dict, broker: BrokerConnection, risk_result: dict
    ) -> dict:
        """Fully automatic mode: place entry and manage autonomously."""
        result = await self._place_order_from_plan(plan, broker)
        result["risk_result"] = risk_result
        result["mode"] = "fully_auto"
        result["note"] = "Order placed and will be managed automatically."
        return result

    async def _place_order_from_plan(
        self, plan: dict, broker: BrokerConnection
    ) -> dict:
        """Place a broker order from an execution plan."""
        try:
            order_result = await broker.place_order(
                symbol=plan["symbol"],
                direction=plan["direction"],
                lot_size=plan["lot_size"],
                sl=plan.get("sl"),
                tp=plan.get("tp"),
            )

            execution_record = {
                "plan": plan,
                "result": order_result,
                "executed_at": datetime.now(timezone.utc).isoformat(),
            }
            self._execution_log.append(execution_record)

            if order_result.get("status") == "filled":
                logger.info(
                    "Order executed: %s %s %.2f lots @ $%.2f → order %s",
                    plan["direction"].upper(),
                    plan["symbol"],
                    plan["lot_size"],
                    order_result.get("entry_price", 0),
                    order_result.get("order_id"),
                )
            else:
                logger.warning("Order failed: %s", order_result)

            return {
                "status": order_result.get("status", "error"),
                "order": order_result,
                "plan": plan,
            }

        except Exception as exc:
            logger.exception("Failed to execute order: %s", exc)
            return {
                "status": "error",
                "error": str(exc),
                "plan": plan,
            }

    @property
    def execution_log(self) -> list[dict]:
        """Return the execution history log."""
        return list(self._execution_log)
