"""Copy trading API.

Subscribers can register to have AI advisor signals automatically copied to
their broker accounts with configurable lot scaling and risk limits.

Storage uses the CopyTradeSubscription DB model for persistence.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func as sa_func

from app.api.admin import _verify_telegram_init_data
from app.broker.copy_trade import CopyTradeManager
from app.config import settings
from app.database import async_session, CopyTradeSubscription

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/copy-trade", tags=["copy_trade"])

# Shared CopyTradeManager instance
_manager = CopyTradeManager()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class SubscribeRequest(BaseModel):
    lot_multiplier: float = Field(default=1.0, ge=0.01, le=100.0, description="Lot scaling factor vs the signal lot size")
    max_lot_size: float = Field(default=5.0, ge=0.01, le=500.0, description="Hard cap on lot size per copied trade")
    max_daily_trades: int = Field(default=10, ge=1, le=200, description="Maximum copy trades allowed per day")
    max_daily_loss_usd: float = Field(default=500.0, ge=1.0, description="Daily loss limit in USD before copying is paused")


class UpdateSettingsRequest(BaseModel):
    lot_multiplier: Optional[float] = Field(default=None, ge=0.01, le=100.0)
    max_lot_size: Optional[float] = Field(default=None, ge=0.01, le=500.0)
    max_daily_trades: Optional[int] = Field(default=None, ge=1, le=200)
    max_daily_loss_usd: Optional[float] = Field(default=None, ge=1.0)
    enabled: Optional[bool] = None


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------


def _get_telegram_id(request: Request) -> int:
    """Verify X-Telegram-Init-Data header and return the telegram_id as int."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Missing X-Telegram-Init-Data header")
    user_data = _verify_telegram_init_data(init_data, max_age=86400)
    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(400, "No user ID in initData")
    return int(telegram_id)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _sub_config(sub: CopyTradeSubscription) -> dict:
    """Return the user-facing config subset from a CopyTradeSubscription row."""
    return {
        "lot_multiplier": sub.lot_multiplier,
        "max_lot_size": sub.max_lot_size,
        "max_daily_trades": sub.daily_trade_limit,
        "max_daily_loss_usd": sub.daily_loss_limit_usd,
        "enabled": sub.is_active,
        "subscribed_at": sub.created_at.isoformat() if sub.created_at else None,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/status")
async def get_copy_trade_status():
    """Return overall copy trade system status.

    Reports whether copy trading is available, how many subscribers are
    currently active, and an aggregate of today's copy activity.
    """
    if not settings.broker_enabled:
        return {
            "enabled": False,
            "message": "Copy trading is not enabled on this server",
            "connected_subscribers": 0,
            "today": {
                "total_trades": 0,
                "active_subscribers": 0,
            },
        }

    async with async_session() as session:
        # Count active subscribers
        result = await session.execute(
            select(sa_func.count()).select_from(CopyTradeSubscription).where(
                CopyTradeSubscription.is_active == True  # noqa: E712
            )
        )
        active_count = result.scalar() or 0

        # Sum today's trades across active subscribers
        result = await session.execute(
            select(sa_func.sum(CopyTradeSubscription.trades_today)).where(
                CopyTradeSubscription.is_active == True  # noqa: E712
            )
        )
        total_trades_today = result.scalar() or 0

    return {
        "enabled": True,
        "connected_subscribers": active_count,
        "today": {
            "total_trades": total_trades_today,
            "active_subscribers": active_count,
        },
    }


@router.post("/subscribe", status_code=201)
async def subscribe(request: Request, body: SubscribeRequest):
    """Subscribe the authenticated user to copy trading.

    Creates a subscriber profile with the provided risk parameters.
    If the user is already subscribed, returns the existing profile unchanged.

    Returns the subscriber_id and the full configuration that was stored.
    """
    telegram_id = _get_telegram_id(request)

    async with async_session() as session:
        # Idempotent -- return existing if already subscribed
        result = await session.execute(
            select(CopyTradeSubscription).where(
                CopyTradeSubscription.telegram_id == telegram_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return {
                "subscriber_id": existing.id,
                "already_subscribed": True,
                "config": _sub_config(existing),
            }

        sub = CopyTradeSubscription(
            telegram_id=telegram_id,
            is_active=True,
            lot_multiplier=body.lot_multiplier,
            max_lot_size=body.max_lot_size,
            daily_trade_limit=body.max_daily_trades,
            daily_loss_limit_usd=body.max_daily_loss_usd,
        )
        session.add(sub)
        await session.commit()
        await session.refresh(sub)

        logger.info(
            "New copy trade subscriber: telegram_id=%d subscriber_id=%d",
            telegram_id, sub.id,
        )

        return {
            "subscriber_id": sub.id,
            "already_subscribed": False,
            "config": _sub_config(sub),
        }


@router.post("/unsubscribe")
async def unsubscribe(request: Request):
    """Unsubscribe the authenticated user from copy trading.

    Sets is_active=False instead of deleting the row, preserving history.
    """
    telegram_id = _get_telegram_id(request)

    async with async_session() as session:
        result = await session.execute(
            select(CopyTradeSubscription).where(
                CopyTradeSubscription.telegram_id == telegram_id
            )
        )
        sub = result.scalar_one_or_none()

        if not sub:
            raise HTTPException(404, "You are not subscribed to copy trading")

        sub.is_active = False
        await session.commit()

        logger.info(
            "Copy trade unsubscribe: telegram_id=%d subscriber_id=%d",
            telegram_id, sub.id,
        )

        return {"unsubscribed": True, "subscriber_id": sub.id}


@router.get("/stats")
async def get_stats(request: Request):
    """Get today's copy trade statistics for the authenticated subscriber.

    Returns the daily trade count, running PnL, and a filtered slice of the
    copy log for trades that belong to this subscriber.
    """
    telegram_id = _get_telegram_id(request)

    async with async_session() as session:
        result = await session.execute(
            select(CopyTradeSubscription).where(
                CopyTradeSubscription.telegram_id == telegram_id
            )
        )
        sub = result.scalar_one_or_none()

        if not sub:
            raise HTTPException(404, "You are not subscribed to copy trading")

        trades_today = sub.trades_today or 0
        daily_pnl = sub.loss_today_usd or 0.0

        # Pull copy log from the manager for this subscriber
        subscriber_log = [
            entry for entry in _manager.copy_log
            if entry.get("subscriber_id") == str(sub.id)
        ]
        recent_log = subscriber_log[-50:]

        return {
            "subscriber_id": sub.id,
            "enabled": sub.is_active,
            "today": {
                "trades": trades_today,
                "pnl_usd": round(daily_pnl, 2),
                "remaining_trades": max(0, sub.daily_trade_limit - trades_today),
                "remaining_loss_budget_usd": round(
                    max(0.0, sub.daily_loss_limit_usd - abs(min(daily_pnl, 0.0))), 2
                ),
            },
            "lifetime": {
                "total_copied_trades": sub.total_copied_trades or 0,
                "total_pnl_usd": round(sub.total_pnl_usd or 0.0, 2),
            },
            "config": _sub_config(sub),
            "trade_history": [
                {
                    "timestamp": entry["timestamp"],
                    "symbol": entry["original_signal"].get("symbol"),
                    "direction": entry["original_signal"].get("direction"),
                    "original_lot_size": entry["original_signal"].get("lot_size"),
                    "subscriber_lot_size": entry["subscriber_lot_size"],
                    "multiplier": entry["lot_multiplier"],
                    "status": entry["order_result"].get("status"),
                    "order_id": entry["order_result"].get("order_id"),
                }
                for entry in recent_log
            ],
        }


@router.put("/settings")
async def update_settings(request: Request, body: UpdateSettingsRequest):
    """Update copy trade settings for the authenticated subscriber.

    Only the fields provided in the request body are updated; omitted fields
    retain their current values.
    """
    telegram_id = _get_telegram_id(request)

    async with async_session() as session:
        result = await session.execute(
            select(CopyTradeSubscription).where(
                CopyTradeSubscription.telegram_id == telegram_id
            )
        )
        sub = result.scalar_one_or_none()

        if not sub:
            raise HTTPException(404, "You are not subscribed to copy trading")

        update_fields = body.model_dump(exclude_none=True)
        if not update_fields:
            raise HTTPException(400, "No fields to update")

        # Map Pydantic field names to DB column names
        field_map = {
            "lot_multiplier": "lot_multiplier",
            "max_lot_size": "max_lot_size",
            "max_daily_trades": "daily_trade_limit",
            "max_daily_loss_usd": "daily_loss_limit_usd",
            "enabled": "is_active",
        }

        updated_keys = []
        for key, value in update_fields.items():
            db_col = field_map.get(key)
            if db_col:
                setattr(sub, db_col, value)
                updated_keys.append(key)

        await session.commit()
        await session.refresh(sub)

        logger.info(
            "Copy trade settings updated: telegram_id=%d fields=%s",
            telegram_id, updated_keys,
        )

        return {
            "subscriber_id": sub.id,
            "updated_fields": updated_keys,
            "config": _sub_config(sub),
        }
