"""Broker account, positions, and order management API.

Wires FastAPI endpoints to the broker module (BrokerConnection ABC,
SignalExecutor, PositionManager, RiskManager).  State is held at
module level and lazily initialised on the first /connect call.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.api.admin import _verify_telegram_init_data
from app.broker.connection import BrokerConnection, create_broker
from app.broker.executor import SignalExecutor
from app.broker.position_manager import PositionManager
from app.broker.risk_manager import RiskManager
from app.config import settings
from app.dependencies import standard_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/broker",
    tags=["broker"],
    dependencies=[Depends(standard_rate_limit)],
)

# ---------------------------------------------------------------------------
# Module-level broker state (lazily initialised via /connect)
# ---------------------------------------------------------------------------

_broker_state: dict = {
    "broker": None,         # BrokerConnection instance
    "executor": None,       # SignalExecutor instance
    "position_manager": None,  # PositionManager instance
    "risk_manager": None,   # RiskManager instance
    "connected": False,
}


def _get_broker() -> BrokerConnection:
    """Return the active broker or raise 400 if not connected."""
    broker: Optional[BrokerConnection] = _broker_state.get("broker")
    if broker is None or not _broker_state.get("connected"):
        raise HTTPException(400, "Broker not connected. Call POST /api/broker/connect first.")
    return broker


def _get_risk_manager() -> RiskManager:
    rm = _broker_state.get("risk_manager")
    if rm is None:
        rm = RiskManager()
        _broker_state["risk_manager"] = rm
    return rm


# ---------------------------------------------------------------------------
# Auth helper (mirrors alerts.py pattern)
# ---------------------------------------------------------------------------

def _get_user_data(request: Request) -> int:
    """Extract and verify the Telegram user from initData header."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Missing initData")
    user_data = _verify_telegram_init_data(init_data, max_age=86400)
    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(400, "Invalid user data")
    return telegram_id


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------

class OrderRequest(BaseModel):
    symbol: str = "XAUUSD"
    direction: str          # "buy" or "sell"
    lot_size: float = 0.01
    sl: Optional[float] = None
    tp: Optional[float] = None


class ModifyRequest(BaseModel):
    sl: Optional[float] = None
    tp: Optional[float] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/connect")
async def connect_broker(request: Request):
    """Initialise the broker connection.

    Creates the adapter via ``create_broker(settings.default_broker)``,
    connects with the appropriate config, and stores the live instances
    in module state.
    """
    _get_user_data(request)

    if not settings.broker_enabled:
        raise HTTPException(400, "Broker integration is not enabled in server config.")

    # Already connected — return current account info
    if _broker_state.get("connected") and _broker_state.get("broker"):
        try:
            account_info = await _broker_state["broker"].get_account_info()
            return {"connected": True, "account": account_info, "message": "Already connected."}
        except Exception:
            # Connection went stale — reconnect below
            pass

    try:
        broker = create_broker(settings.default_broker)

        # Build config dict from settings
        # Keys match what each adapter's connect() expects
        config: dict = {
            "token": settings.metaapi_token,
            "account_id": settings.metaapi_account_id,
            "default_lot_size": settings.default_lot_size,
            "max_daily_loss_pct": settings.max_daily_loss_pct,
            "max_open_positions": settings.max_open_positions,
        }

        success = await broker.connect(config)
        if not success:
            raise HTTPException(502, "Broker connection failed.")

        risk_manager = RiskManager()
        executor = SignalExecutor(risk_manager=risk_manager)
        position_manager = PositionManager()

        _broker_state.update({
            "broker": broker,
            "executor": executor,
            "position_manager": position_manager,
            "risk_manager": risk_manager,
            "connected": True,
        })

        account_info = await broker.get_account_info()
        logger.info("Broker connected: %s (type=%s)", account_info, settings.default_broker)
        return {"connected": True, "account": account_info}

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to connect broker: %s", exc)
        raise HTTPException(502, f"Broker connection error: {exc}") from exc


@router.post("/disconnect")
async def disconnect_broker(request: Request):
    """Disconnect from the broker and clear module state."""
    _get_user_data(request)

    broker: Optional[BrokerConnection] = _broker_state.get("broker")
    if broker is None or not _broker_state.get("connected"):
        return {"connected": False, "message": "Not connected."}

    try:
        await broker.disconnect()
    except Exception as exc:
        logger.warning("Error during broker disconnect: %s", exc)

    _broker_state.update({
        "broker": None,
        "executor": None,
        "position_manager": None,
        "risk_manager": None,
        "connected": False,
    })
    logger.info("Broker disconnected.")
    return {"connected": False, "message": "Disconnected."}


@router.get("/account")
async def get_broker_account(request: Request):
    """Return current broker account information."""
    _get_user_data(request)

    if not settings.broker_enabled:
        return {"connected": False, "message": "Broker not enabled"}

    broker = _get_broker()
    try:
        account_info = await broker.get_account_info()
        return {"connected": True, "account": account_info}
    except Exception as exc:
        logger.exception("Failed to get account info: %s", exc)
        raise HTTPException(502, f"Failed to get account info: {exc}") from exc


@router.get("/positions")
async def get_positions(request: Request):
    """Return all open positions from the connected broker."""
    _get_user_data(request)

    broker = _get_broker()
    try:
        positions = await broker.get_positions()
        return {"positions": positions, "count": len(positions)}
    except Exception as exc:
        logger.exception("Failed to get positions: %s", exc)
        raise HTTPException(502, f"Failed to get positions: {exc}") from exc


@router.get("/price")
async def get_price(request: Request, symbol: str = "XAUUSD"):
    """Return the current bid/ask price for a symbol (default XAUUSD)."""
    _get_user_data(request)

    broker = _get_broker()
    try:
        price_data = await broker.get_price(symbol)
        if "error" in price_data:
            raise HTTPException(502, price_data["error"])
        return price_data
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get price: %s", exc)
        raise HTTPException(502, f"Failed to get price: {exc}") from exc


@router.post("/order")
async def place_order(body: OrderRequest, request: Request):
    """Place a market order after running risk checks.

    The order goes through RiskManager.check_trade() first. If the risk
    check rejects it, the endpoint returns 400 with the rejection reason.
    If approved (possibly with an adjusted lot size), the order is placed
    via the broker adapter.
    """
    _get_user_data(request)

    broker = _get_broker()
    risk_manager = _get_risk_manager()

    if body.direction.lower() not in ("buy", "sell"):
        raise HTTPException(400, "direction must be 'buy' or 'sell'")

    try:
        # Gather data for risk check
        account_info = await broker.get_account_info()
        positions = await broker.get_positions()
        price_data = await broker.get_price(body.symbol)
        if "error" in price_data:
            raise HTTPException(502, price_data["error"])

        entry_price = (
            price_data["ask"] if body.direction.lower() == "buy" else price_data["bid"]
        )

        trade_plan = {
            "symbol": body.symbol,
            "direction": body.direction.lower(),
            "lot_size": body.lot_size,
            "entry_price": entry_price,
            "sl": body.sl,
            "tp": body.tp,
        }

        risk_config = {
            "max_daily_loss_pct": settings.max_daily_loss_pct,
            "max_open_positions": settings.max_open_positions,
        }

        risk_result = await risk_manager.check_trade(
            account_info=account_info,
            trade_plan=trade_plan,
            positions=positions,
            config=risk_config,
        )

        if not risk_result["approved"]:
            raise HTTPException(400, {
                "message": f"Risk check rejected: {risk_result['reason']}",
                "risk_result": risk_result,
            })

        # Use risk-adjusted lot size if the manager capped it
        lot_size = risk_result.get("adjusted_lot_size") or body.lot_size

        order_result = await broker.place_order(
            symbol=body.symbol,
            direction=body.direction.lower(),
            lot_size=lot_size,
            sl=body.sl,
            tp=body.tp,
        )

        logger.info(
            "Order placed: %s %s %.2f lots — %s",
            body.direction.upper(),
            body.symbol,
            lot_size,
            order_result,
        )
        return {
            "order": order_result,
            "risk_result": risk_result,
            "lot_size_used": lot_size,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to place order: %s", exc)
        raise HTTPException(502, f"Failed to place order: {exc}") from exc


@router.post("/close/{position_id}")
async def close_position(position_id: str, request: Request):
    """Close an open position by its ID."""
    _get_user_data(request)

    broker = _get_broker()
    try:
        result = await broker.close_position(position_id)
        logger.info("Position %s closed: %s", position_id, result)
        return {"result": result}
    except Exception as exc:
        logger.exception("Failed to close position %s: %s", position_id, exc)
        raise HTTPException(502, f"Failed to close position: {exc}") from exc


@router.post("/modify/{position_id}")
async def modify_position(position_id: str, body: ModifyRequest, request: Request):
    """Modify stop-loss and/or take-profit on an open position."""
    _get_user_data(request)

    if body.sl is None and body.tp is None:
        raise HTTPException(400, "At least one of sl or tp must be provided.")

    broker = _get_broker()
    try:
        result = await broker.modify_order(position_id, sl=body.sl, tp=body.tp)
        logger.info(
            "Position %s modified (sl=%s, tp=%s): %s",
            position_id, body.sl, body.tp, result,
        )
        return {"result": result}
    except Exception as exc:
        logger.exception("Failed to modify position %s: %s", position_id, exc)
        raise HTTPException(502, f"Failed to modify position: {exc}") from exc
