"""Community Trade Sharing — Share trades, leaderboard, social features."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, desc, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, SharedTrade
from app.api.admin import _verify_telegram_init_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/community", tags=["community"])


def _get_user(request: Request) -> tuple[int, str | None]:
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(401, "Missing initData")
    user_data = _verify_telegram_init_data(init_data, max_age=86400)
    telegram_id = user_data.get("id")
    if not telegram_id:
        raise HTTPException(400, "Invalid user data")
    return int(telegram_id), user_data.get("username")


class ShareTradeRequest(BaseModel):
    direction: str  # long / short
    entry_price: float
    target_price: float | None = None
    stop_loss: float | None = None
    reasoning: str | None = None


class CloseTradeRequest(BaseModel):
    pnl: float


@router.get("/trades")
async def get_shared_trades(
    session: AsyncSession = Depends(get_session),
):
    """Get latest 50 shared trades (public, no auth)."""
    result = await session.execute(
        select(SharedTrade)
        .order_by(desc(SharedTrade.created_at))
        .limit(50)
    )
    trades = result.scalars().all()

    return {
        "trades": [
            {
                "id": t.id,
                "telegram_id": t.telegram_id,
                "username": t.username,
                "direction": t.direction,
                "entry_price": t.entry_price,
                "target_price": t.target_price,
                "stop_loss": t.stop_loss,
                "pnl": t.pnl,
                "status": t.status,
                "reasoning": t.reasoning,
                "likes": t.likes,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "closed_at": t.closed_at.isoformat() if t.closed_at else None,
            }
            for t in trades
        ],
        "count": len(trades),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/trades")
async def share_trade(
    req: ShareTradeRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Share a trade (auth via X-Telegram-Init-Data header)."""
    telegram_id, username = _get_user(request)

    if req.direction not in ("long", "short"):
        raise HTTPException(status_code=400, detail="Direction must be 'long' or 'short'")

    if req.entry_price <= 0:
        raise HTTPException(status_code=400, detail="Entry price must be positive")

    trade = SharedTrade(
        telegram_id=telegram_id,
        username=username,
        direction=req.direction,
        entry_price=req.entry_price,
        target_price=req.target_price,
        stop_loss=req.stop_loss,
        reasoning=req.reasoning,
        status="open",
        likes=0,
    )
    session.add(trade)
    await session.commit()
    await session.refresh(trade)

    logger.info(f"Community trade shared: {req.direction} @ {req.entry_price} by user {telegram_id}")

    return {
        "id": trade.id,
        "status": "open",
        "message": "Trade shared successfully",
        "created_at": trade.created_at.isoformat() if trade.created_at else None,
    }


@router.get("/leaderboard")
async def get_leaderboard(
    session: AsyncSession = Depends(get_session),
):
    """Top 10 users by total PnL from closed shared trades."""
    # Aggregate PnL per user from closed trades
    result = await session.execute(
        select(
            SharedTrade.telegram_id,
            SharedTrade.username,
            sa_func.sum(SharedTrade.pnl).label("total_pnl"),
            sa_func.count(SharedTrade.id).label("trade_count"),
            sa_func.sum(
                sa_func.case(
                    (SharedTrade.pnl > 0, 1),
                    else_=0,
                )
            ).label("winning_trades"),
        )
        .where(SharedTrade.status == "closed")
        .where(SharedTrade.pnl.isnot(None))
        .group_by(SharedTrade.telegram_id, SharedTrade.username)
        .order_by(desc("total_pnl"))
        .limit(10)
    )
    rows = result.all()

    leaderboard = []
    for rank, row in enumerate(rows, 1):
        trade_count = row.trade_count or 0
        winning = row.winning_trades or 0
        win_rate = (winning / trade_count * 100) if trade_count > 0 else 0.0

        leaderboard.append({
            "rank": rank,
            "telegram_id": row.telegram_id,
            "username": row.username,
            "total_pnl": round(float(row.total_pnl or 0), 2),
            "trade_count": trade_count,
            "winning_trades": winning,
            "win_rate": round(win_rate, 1),
        })

    return {
        "leaderboard": leaderboard,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/trades/{trade_id}/like")
async def like_trade(
    trade_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Increment likes on a shared trade."""
    result = await session.execute(
        select(SharedTrade).where(SharedTrade.id == trade_id)
    )
    trade = result.scalar_one_or_none()

    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    trade.likes = (trade.likes or 0) + 1
    await session.commit()

    return {
        "id": trade.id,
        "likes": trade.likes,
        "message": "Liked!",
    }
