"""Broker account and positions API."""
from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/api/broker", tags=["broker"])


@router.get("/account")
async def get_broker_account():
    if not settings.broker_enabled:
        return {"connected": False, "message": "Broker not enabled"}
    return {"connected": False, "message": "Connect via Telegram /connect command"}


@router.get("/positions")
async def get_positions():
    return {"positions": [], "message": "No active positions"}
