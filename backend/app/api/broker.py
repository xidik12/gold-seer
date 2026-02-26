"""Broker account, positions, and order management API.

Wires FastAPI endpoints to the broker module (BrokerConnection ABC,
SignalExecutor, PositionManager, RiskManager).  Per-user broker state
is stored in-memory via ``_user_connections`` and persisted in the
``broker_accounts`` DB table.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.api.admin import _verify_telegram_init_data
from app.broker.connection import BrokerConnection, create_broker
from app.broker.executor import SignalExecutor
from app.broker.position_manager import PositionManager
from app.broker.risk_manager import RiskManager
from app.config import settings
from app.database import async_session, BrokerAccount
from app.dependencies import standard_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/broker",
    tags=["broker"],
    dependencies=[Depends(standard_rate_limit)],
)

# ---------------------------------------------------------------------------
# Per-user broker connections (keyed by telegram_id)
# ---------------------------------------------------------------------------

_user_connections: dict[int, dict] = {}
"""
Per-user broker state dict.  Each entry looks like:
{
    "broker": BrokerConnection,
    "executor": SignalExecutor,
    "position_manager": PositionManager,
    "risk_manager": RiskManager,
    "connected": bool,
}
"""


def _get_user_broker(telegram_id: int) -> BrokerConnection:
    """Return the active broker for *telegram_id* or raise 400."""
    state = _user_connections.get(telegram_id)
    if state is None or not state.get("connected"):
        raise HTTPException(400, "Broker not connected. Call POST /api/broker/connect first.")
    broker: Optional[BrokerConnection] = state.get("broker")
    if broker is None:
        raise HTTPException(400, "Broker not connected. Call POST /api/broker/connect first.")
    return broker


def _get_user_risk_manager(telegram_id: int) -> RiskManager:
    """Return (or lazily create) the user's RiskManager."""
    state = _user_connections.get(telegram_id, {})
    rm = state.get("risk_manager")
    if rm is None:
        rm = RiskManager()
        if telegram_id in _user_connections:
            _user_connections[telegram_id]["risk_manager"] = rm
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
    return int(telegram_id)


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------

class BrokerSettingsRequest(BaseModel):
    broker_type: str = "demo"
    metaapi_token: Optional[str] = None
    account_id: Optional[str] = None
    login: Optional[str] = None
    server: Optional[str] = None
    execution_mode: str = "manual_approve"


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
# Broker settings CRUD endpoints
# ---------------------------------------------------------------------------

@router.get("/settings")
async def get_broker_settings(request: Request):
    """Return the user's saved broker settings (never exposes the token)."""
    telegram_id = _get_user_data(request)

    async with async_session() as session:
        result = await session.execute(
            select(BrokerAccount).where(BrokerAccount.telegram_id == telegram_id)
        )
        account = result.scalar_one_or_none()

    if account is None:
        return {
            "broker_type": "demo",
            "account_id": None,
            "server": None,
            "login": None,
            "is_connected": False,
            "execution_mode": "manual_approve",
        }

    return {
        "broker_type": account.broker_type,
        "account_id": account.account_id,
        "server": account.server,
        "login": account.login,
        "is_connected": account.is_connected,
        "execution_mode": account.execution_mode,
    }


@router.post("/settings")
async def save_broker_settings(body: BrokerSettingsRequest, request: Request):
    """Create or update broker settings for the authenticated user."""
    telegram_id = _get_user_data(request)

    if body.broker_type not in ("demo", "metaapi"):
        raise HTTPException(400, "broker_type must be 'demo' or 'metaapi'")

    async with async_session() as session:
        result = await session.execute(
            select(BrokerAccount).where(BrokerAccount.telegram_id == telegram_id)
        )
        account = result.scalar_one_or_none()

        if account is None:
            account = BrokerAccount(telegram_id=telegram_id)
            session.add(account)

        account.broker_type = body.broker_type
        if body.metaapi_token is not None:
            account.metaapi_token = body.metaapi_token
        if body.account_id is not None:
            account.account_id = body.account_id
        if body.login is not None:
            account.login = body.login
        if body.server is not None:
            account.server = body.server
        account.execution_mode = body.execution_mode

        await session.commit()

    logger.info("Broker settings saved for user %s (type=%s)", telegram_id, body.broker_type)
    return {"ok": True, "message": "Broker settings saved."}


@router.delete("/settings")
async def delete_broker_settings(request: Request):
    """Delete broker settings and disconnect if connected."""
    telegram_id = _get_user_data(request)

    # Disconnect if active
    state = _user_connections.pop(telegram_id, None)
    if state and state.get("broker"):
        try:
            await state["broker"].disconnect()
        except Exception as exc:
            logger.warning("Error disconnecting during settings delete for %s: %s", telegram_id, exc)

    async with async_session() as session:
        result = await session.execute(
            select(BrokerAccount).where(BrokerAccount.telegram_id == telegram_id)
        )
        account = result.scalar_one_or_none()
        if account:
            await session.delete(account)
            await session.commit()

    logger.info("Broker settings deleted for user %s", telegram_id)
    return {"ok": True, "message": "Broker settings deleted."}


# ---------------------------------------------------------------------------
# Connect / Disconnect endpoints
# ---------------------------------------------------------------------------

@router.post("/connect")
async def connect_broker(request: Request):
    """Initialise the per-user broker connection.

    Looks up the user's BrokerAccount from the DB and uses those
    credentials to connect.  Falls back to demo if broker_type is
    'demo' or no record exists.
    """
    telegram_id = _get_user_data(request)

    if not settings.broker_enabled:
        raise HTTPException(400, "Broker integration is not enabled in server config.")

    # Already connected — return current account info
    state = _user_connections.get(telegram_id)
    if state and state.get("connected") and state.get("broker"):
        try:
            account_info = await state["broker"].get_account_info()
            return {"connected": True, "account": account_info, "message": "Already connected."}
        except Exception:
            # Connection went stale — reconnect below
            pass

    # Load user's broker settings from DB
    async with async_session() as session:
        result = await session.execute(
            select(BrokerAccount).where(BrokerAccount.telegram_id == telegram_id)
        )
        db_account = result.scalar_one_or_none()

    broker_type = db_account.broker_type if db_account else "demo"

    try:
        broker = create_broker(broker_type)

        # Build config from per-user DB settings
        if broker_type == "metaapi" and db_account:
            config: dict = {
                "token": db_account.metaapi_token,
                "account_id": db_account.account_id,
                "default_lot_size": settings.default_lot_size,
                "max_daily_loss_pct": settings.max_daily_loss_pct,
                "max_open_positions": settings.max_open_positions,
            }
        else:
            # Demo or no DB record — use server defaults (if any)
            config = {
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

        _user_connections[telegram_id] = {
            "broker": broker,
            "executor": executor,
            "position_manager": position_manager,
            "risk_manager": risk_manager,
            "connected": True,
        }

        # Mark connected in DB
        if db_account:
            async with async_session() as session:
                result = await session.execute(
                    select(BrokerAccount).where(BrokerAccount.telegram_id == telegram_id)
                )
                acct = result.scalar_one_or_none()
                if acct:
                    acct.is_connected = True
                    await session.commit()

        account_info = await broker.get_account_info()
        logger.info("Broker connected for user %s: %s (type=%s)", telegram_id, account_info, broker_type)
        return {"connected": True, "account": account_info}

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to connect broker for user %s: %s", telegram_id, exc)
        raise HTTPException(502, f"Broker connection error: {exc}") from exc


@router.post("/disconnect")
async def disconnect_broker(request: Request):
    """Disconnect the user's broker and clear their in-memory state."""
    telegram_id = _get_user_data(request)

    state = _user_connections.get(telegram_id)
    if state is None or not state.get("connected"):
        return {"connected": False, "message": "Not connected."}

    broker: Optional[BrokerConnection] = state.get("broker")
    if broker:
        try:
            await broker.disconnect()
        except Exception as exc:
            logger.warning("Error during broker disconnect for user %s: %s", telegram_id, exc)

    _user_connections.pop(telegram_id, None)

    # Mark disconnected in DB
    try:
        async with async_session() as session:
            result = await session.execute(
                select(BrokerAccount).where(BrokerAccount.telegram_id == telegram_id)
            )
            acct = result.scalar_one_or_none()
            if acct:
                acct.is_connected = False
                await session.commit()
    except Exception as exc:
        logger.warning("Failed to update DB on disconnect for user %s: %s", telegram_id, exc)

    logger.info("Broker disconnected for user %s", telegram_id)
    return {"connected": False, "message": "Disconnected."}


# ---------------------------------------------------------------------------
# Account / market data endpoints
# ---------------------------------------------------------------------------

@router.get("/account")
async def get_broker_account(request: Request):
    """Return current broker account information."""
    telegram_id = _get_user_data(request)

    if not settings.broker_enabled:
        return {"connected": False, "message": "Broker not enabled"}

    broker = _get_user_broker(telegram_id)
    try:
        account_info = await broker.get_account_info()
        return {"connected": True, "account": account_info}
    except Exception as exc:
        logger.exception("Failed to get account info for user %s: %s", telegram_id, exc)
        raise HTTPException(502, f"Failed to get account info: {exc}") from exc


@router.get("/positions")
async def get_positions(request: Request):
    """Return all open positions from the connected broker."""
    telegram_id = _get_user_data(request)

    broker = _get_user_broker(telegram_id)
    try:
        positions = await broker.get_positions()
        return {"positions": positions, "count": len(positions)}
    except Exception as exc:
        logger.exception("Failed to get positions for user %s: %s", telegram_id, exc)
        raise HTTPException(502, f"Failed to get positions: {exc}") from exc


@router.get("/price")
async def get_price(request: Request, symbol: str = "XAUUSD"):
    """Return the current bid/ask price for a symbol (default XAUUSD)."""
    telegram_id = _get_user_data(request)

    broker = _get_user_broker(telegram_id)
    try:
        price_data = await broker.get_price(symbol)
        if "error" in price_data:
            raise HTTPException(502, price_data["error"])
        return price_data
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get price for user %s: %s", telegram_id, exc)
        raise HTTPException(502, f"Failed to get price: {exc}") from exc


# ---------------------------------------------------------------------------
# Trading endpoints
# ---------------------------------------------------------------------------

@router.post("/order")
async def place_order(body: OrderRequest, request: Request):
    """Place a market order after running risk checks.

    The order goes through RiskManager.check_trade() first. If the risk
    check rejects it, the endpoint returns 400 with the rejection reason.
    If approved (possibly with an adjusted lot size), the order is placed
    via the broker adapter.
    """
    telegram_id = _get_user_data(request)

    broker = _get_user_broker(telegram_id)
    risk_manager = _get_user_risk_manager(telegram_id)

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
            "Order placed for user %s: %s %s %.2f lots — %s",
            telegram_id,
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
        logger.exception("Failed to place order for user %s: %s", telegram_id, exc)
        raise HTTPException(502, f"Failed to place order: {exc}") from exc


@router.post("/close/{position_id}")
async def close_position(position_id: str, request: Request):
    """Close an open position by its ID."""
    telegram_id = _get_user_data(request)

    broker = _get_user_broker(telegram_id)
    try:
        result = await broker.close_position(position_id)
        logger.info("Position %s closed for user %s: %s", position_id, telegram_id, result)
        return {"result": result}
    except Exception as exc:
        logger.exception("Failed to close position %s for user %s: %s", position_id, telegram_id, exc)
        raise HTTPException(502, f"Failed to close position: {exc}") from exc


@router.post("/modify/{position_id}")
async def modify_position(position_id: str, body: ModifyRequest, request: Request):
    """Modify stop-loss and/or take-profit on an open position."""
    telegram_id = _get_user_data(request)

    if body.sl is None and body.tp is None:
        raise HTTPException(400, "At least one of sl or tp must be provided.")

    broker = _get_user_broker(telegram_id)
    try:
        result = await broker.modify_order(position_id, sl=body.sl, tp=body.tp)
        logger.info(
            "Position %s modified for user %s (sl=%s, tp=%s): %s",
            position_id, telegram_id, body.sl, body.tp, result,
        )
        return {"result": result}
    except Exception as exc:
        logger.exception("Failed to modify position %s for user %s: %s", position_id, telegram_id, exc)
        raise HTTPException(502, f"Failed to modify position: {exc}") from exc
