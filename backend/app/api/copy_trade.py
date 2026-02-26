"""Copy trading API.

Subscribers can register to have AI advisor signals automatically copied to
their broker accounts with configurable lot scaling and risk limits.

Storage is in-memory for now — DB persistence will be added later.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.admin import _verify_telegram_init_data
from app.broker.copy_trade import CopyTradeManager
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/copy-trade", tags=["copy_trade"])

# ---------------------------------------------------------------------------
# In-memory stores (keyed by telegram_id as str)
# ---------------------------------------------------------------------------

# subscriber_id → subscriber profile
_subscribers: dict[str, dict] = {}

# telegram_id → subscriber_id  (1-to-1 mapping for now)
_user_to_subscriber: dict[str, str] = {}

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


def _get_telegram_id(request: Request) -> str:
    """Verify X-Telegram-Init-Data header and return the telegram_id as str."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Missing X-Telegram-Init-Data header")
    user_data = _verify_telegram_init_data(init_data, max_age=86400)
    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(400, "No user ID in initData")
    return str(telegram_id)


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

    active_subscribers = [s for s in _subscribers.values() if s.get("enabled", True)]

    # Aggregate today's stats across all subscribers
    total_trades_today = 0
    today = datetime.now(timezone.utc).date().isoformat()
    for sub in active_subscribers:
        sid = sub["subscriber_id"]
        state = _manager.get_subscriber_stats(sid)
        if state and state.get("last_reset_date") == today:
            total_trades_today += state.get("trades_today", 0)

    return {
        "enabled": True,
        "connected_subscribers": len(active_subscribers),
        "today": {
            "total_trades": total_trades_today,
            "active_subscribers": len(active_subscribers),
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

    # Idempotent — return existing profile if already subscribed
    if telegram_id in _user_to_subscriber:
        subscriber_id = _user_to_subscriber[telegram_id]
        profile = _subscribers[subscriber_id]
        return {
            "subscriber_id": subscriber_id,
            "already_subscribed": True,
            "config": _profile_config(profile),
        }

    subscriber_id = str(uuid.uuid4())
    profile = {
        "subscriber_id": subscriber_id,
        "telegram_id": telegram_id,
        "lot_multiplier": body.lot_multiplier,
        "max_lot_size": body.max_lot_size,
        "max_daily_trades": body.max_daily_trades,
        "max_daily_loss_usd": body.max_daily_loss_usd,
        "enabled": True,
        "subscribed_at": datetime.now(timezone.utc).isoformat(),
    }

    _subscribers[subscriber_id] = profile
    _user_to_subscriber[telegram_id] = subscriber_id

    logger.info("New copy trade subscriber: telegram_id=%s subscriber_id=%s", telegram_id, subscriber_id)

    return {
        "subscriber_id": subscriber_id,
        "already_subscribed": False,
        "config": _profile_config(profile),
    }


@router.post("/unsubscribe")
async def unsubscribe(request: Request):
    """Unsubscribe the authenticated user from copy trading.

    Removes the subscriber profile. Future signals will not be copied.
    """
    telegram_id = _get_telegram_id(request)

    if telegram_id not in _user_to_subscriber:
        raise HTTPException(404, "You are not subscribed to copy trading")

    subscriber_id = _user_to_subscriber.pop(telegram_id)
    _subscribers.pop(subscriber_id, None)

    logger.info("Copy trade unsubscribe: telegram_id=%s subscriber_id=%s", telegram_id, subscriber_id)

    return {"unsubscribed": True, "subscriber_id": subscriber_id}


@router.get("/stats")
async def get_stats(request: Request):
    """Get today's copy trade statistics for the authenticated subscriber.

    Returns the daily trade count, running PnL, and a filtered slice of the
    copy log for trades that belong to this subscriber.
    """
    telegram_id = _get_telegram_id(request)

    if telegram_id not in _user_to_subscriber:
        raise HTTPException(404, "You are not subscribed to copy trading")

    subscriber_id = _user_to_subscriber[telegram_id]
    profile = _subscribers[subscriber_id]

    # Pull live daily stats from the manager
    state = _manager.get_subscriber_stats(subscriber_id)
    today = datetime.now(timezone.utc).date().isoformat()

    if state is None or state.get("last_reset_date") != today:
        # No activity yet today
        trades_today = 0
        daily_pnl = 0.0
    else:
        trades_today = state.get("trades_today", 0)
        daily_pnl = state.get("daily_pnl", 0.0)

    # Filter copy log to this subscriber (most recent 50)
    subscriber_log = [
        entry for entry in _manager.copy_log
        if entry.get("subscriber_id") == subscriber_id
    ]
    recent_log = subscriber_log[-50:]

    return {
        "subscriber_id": subscriber_id,
        "enabled": profile.get("enabled", True),
        "today": {
            "trades": trades_today,
            "pnl_usd": round(daily_pnl, 2),
            "remaining_trades": max(0, profile["max_daily_trades"] - trades_today),
            "remaining_loss_budget_usd": round(
                max(0.0, profile["max_daily_loss_usd"] - abs(min(daily_pnl, 0.0))), 2
            ),
        },
        "config": _profile_config(profile),
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

    if telegram_id not in _user_to_subscriber:
        raise HTTPException(404, "You are not subscribed to copy trading")

    subscriber_id = _user_to_subscriber[telegram_id]
    profile = _subscribers[subscriber_id]

    update_fields = body.model_dump(exclude_none=True)
    if not update_fields:
        raise HTTPException(400, "No fields to update")

    allowed = {"lot_multiplier", "max_lot_size", "max_daily_trades", "max_daily_loss_usd", "enabled"}
    for key, value in update_fields.items():
        if key in allowed:
            profile[key] = value

    profile["updated_at"] = datetime.now(timezone.utc).isoformat()

    logger.info(
        "Copy trade settings updated: telegram_id=%s fields=%s",
        telegram_id,
        list(update_fields.keys()),
    )

    return {
        "subscriber_id": subscriber_id,
        "updated_fields": list(update_fields.keys()),
        "config": _profile_config(profile),
    }


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _profile_config(profile: dict) -> dict:
    """Return the user-facing config subset from a subscriber profile."""
    return {
        "lot_multiplier": profile["lot_multiplier"],
        "max_lot_size": profile["max_lot_size"],
        "max_daily_trades": profile["max_daily_trades"],
        "max_daily_loss_usd": profile["max_daily_loss_usd"],
        "enabled": profile.get("enabled", True),
        "subscribed_at": profile.get("subscribed_at"),
    }
