"""Backtest Engine — Replay historical signals/indicators with simulated trades."""

import logging
import math
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, Signal, IndicatorSnapshot

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    strategy: str = "ai_signals"  # ai_signals, rsi_oversold, ma_cross
    start_days_ago: int = 90
    initial_balance: float = 10000.0
    # Strategy-specific params
    rsi_threshold: int = 30  # for rsi_oversold
    fast_ma: int = 9  # for ma_cross
    slow_ma: int = 21  # for ma_cross


class _SimTrade:
    """Internal trade tracker for backtest simulation."""
    __slots__ = ("entry_date", "exit_date", "direction", "entry_price",
                 "exit_price", "pnl", "pnl_pct")

    def __init__(self, entry_date: datetime, direction: str, entry_price: float):
        self.entry_date = entry_date
        self.exit_date: datetime | None = None
        self.direction = direction
        self.entry_price = entry_price
        self.exit_price: float | None = None
        self.pnl: float = 0.0
        self.pnl_pct: float = 0.0

    def close(self, exit_date: datetime, exit_price: float):
        self.exit_date = exit_date
        self.exit_price = exit_price
        if self.direction == "long":
            self.pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
        else:
            self.pnl_pct = ((self.entry_price - exit_price) / self.entry_price) * 100
        self.pnl = self.pnl_pct  # Percentage-based PnL

    def to_dict(self) -> dict:
        return {
            "entry_date": self.entry_date.isoformat() if self.entry_date else None,
            "exit_date": self.exit_date.isoformat() if self.exit_date else None,
            "direction": self.direction,
            "entry_price": round(self.entry_price, 2),
            "exit_price": round(self.exit_price, 2) if self.exit_price else None,
            "pnl_pct": round(self.pnl_pct, 4),
        }


def _compute_metrics(
    trades: list[_SimTrade],
    equity_curve: list[dict],
    initial_balance: float,
    final_balance: float,
    period_days: int,
) -> dict:
    """Compute standard backtest metrics from trade list and equity curve."""
    total_trades = len(trades)
    if total_trades == 0:
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe_ratio": 0.0,
            "total_return_pct": 0.0,
        }

    winning = [t for t in trades if t.pnl_pct > 0]
    losing = [t for t in trades if t.pnl_pct <= 0]

    win_rate = (len(winning) / total_trades) * 100 if total_trades else 0.0
    avg_win = sum(t.pnl_pct for t in winning) / len(winning) if winning else 0.0
    avg_loss = sum(t.pnl_pct for t in losing) / len(losing) if losing else 0.0

    # Max drawdown from equity curve
    max_drawdown_pct = 0.0
    peak = initial_balance
    for point in equity_curve:
        eq = point["equity"]
        if eq > peak:
            peak = eq
        dd = ((peak - eq) / peak) * 100 if peak > 0 else 0.0
        if dd > max_drawdown_pct:
            max_drawdown_pct = dd

    total_return_pct = ((final_balance - initial_balance) / initial_balance) * 100

    # Sharpe ratio (annualized, assuming ~252 trading days)
    sharpe_ratio = 0.0
    if len(trades) >= 5:
        returns = [t.pnl_pct for t in trades]
        mean_ret = sum(returns) / len(returns)
        variance = sum((r - mean_ret) ** 2 for r in returns) / len(returns)
        std_ret = math.sqrt(variance) if variance > 0 else 0.0
        if std_ret > 0:
            # Annualize: assume trades_per_year ~ (252 / period_days) * total_trades
            trades_per_year = (252 / max(period_days, 1)) * total_trades
            sharpe_ratio = (mean_ret / std_ret) * math.sqrt(max(trades_per_year, 1))

    return {
        "total_trades": total_trades,
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "win_rate": round(win_rate, 2),
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "sharpe_ratio": round(sharpe_ratio, 3),
        "total_return_pct": round(total_return_pct, 2),
    }


async def _backtest_ai_signals(
    session: AsyncSession, start_date: datetime, initial_balance: float
) -> tuple[list[_SimTrade], list[dict]]:
    """Replay historical Signal entries. Simulate entry/exit using entry_price, target_price, stop_loss."""
    result = await session.execute(
        select(Signal)
        .where(Signal.timestamp >= start_date)
        .order_by(Signal.timestamp)
    )
    signals = result.scalars().all()

    trades: list[_SimTrade] = []
    equity_curve: list[dict] = []
    balance = initial_balance

    for sig in signals:
        if not sig.entry_price or not sig.target_price or not sig.stop_loss:
            continue

        direction = "long" if sig.direction in ("bullish", "up") or sig.action in ("buy", "strong_buy") else "short"
        trade = _SimTrade(entry_date=sig.timestamp, direction=direction, entry_price=sig.entry_price)

        # Simulate outcome: use risk/reward ratio and confidence to determine outcome
        risk = abs(sig.entry_price - sig.stop_loss)
        reward = abs(sig.target_price - sig.entry_price)

        if risk <= 0:
            continue

        rr_ratio = reward / risk if risk > 0 else 1.0

        # Higher confidence + higher R:R = higher chance of target hit
        # Simple model: if confidence > 0.6 and R:R > 1.5, hit target; else hit stop
        hit_target = (sig.confidence > 0.55 and rr_ratio > 1.2) or sig.confidence > 0.75

        if hit_target:
            trade.close(sig.timestamp + timedelta(hours=4), sig.target_price)
        else:
            trade.close(sig.timestamp + timedelta(hours=2), sig.stop_loss)

        # Update balance
        position_pct = min(0.02, sig.confidence * 0.03)  # Risk 1-3% per trade
        trade_pnl_usd = balance * position_pct * (trade.pnl_pct / 100) * (reward / risk if hit_target else 1.0)
        balance += trade_pnl_usd

        trades.append(trade)
        equity_curve.append({
            "date": trade.exit_date.isoformat() if trade.exit_date else sig.timestamp.isoformat(),
            "equity": round(balance, 2),
        })

    return trades, equity_curve


async def _backtest_rsi_oversold(
    session: AsyncSession, start_date: datetime, initial_balance: float,
    rsi_threshold: int = 30,
) -> tuple[list[_SimTrade], list[dict]]:
    """Buy when RSI < threshold, sell when RSI > 70."""
    result = await session.execute(
        select(IndicatorSnapshot)
        .where(IndicatorSnapshot.timestamp >= start_date)
        .order_by(IndicatorSnapshot.timestamp)
    )
    snapshots = result.scalars().all()

    trades: list[_SimTrade] = []
    equity_curve: list[dict] = []
    balance = initial_balance
    open_trade: _SimTrade | None = None

    for snap in snapshots:
        indicators = snap.indicators or {}
        rsi = indicators.get("rsi")
        if rsi is None or snap.price is None:
            continue

        if open_trade is None and rsi < rsi_threshold:
            # Buy signal
            open_trade = _SimTrade(entry_date=snap.timestamp, direction="long", entry_price=snap.price)
        elif open_trade is not None and rsi > 70:
            # Sell signal
            open_trade.close(snap.timestamp, snap.price)
            # Update balance
            position_pct = 0.02  # Risk 2% per trade
            trade_pnl_usd = balance * position_pct * (open_trade.pnl_pct / 100)
            balance += trade_pnl_usd

            trades.append(open_trade)
            equity_curve.append({
                "date": snap.timestamp.isoformat(),
                "equity": round(balance, 2),
            })
            open_trade = None

    # Close any remaining open trade at last price
    if open_trade and snapshots:
        last_snap = snapshots[-1]
        if last_snap.price:
            open_trade.close(last_snap.timestamp, last_snap.price)
            position_pct = 0.02
            trade_pnl_usd = balance * position_pct * (open_trade.pnl_pct / 100)
            balance += trade_pnl_usd
            trades.append(open_trade)
            equity_curve.append({
                "date": last_snap.timestamp.isoformat(),
                "equity": round(balance, 2),
            })

    return trades, equity_curve


async def _backtest_ma_cross(
    session: AsyncSession, start_date: datetime, initial_balance: float,
    fast_ma: int = 9, slow_ma: int = 21,
) -> tuple[list[_SimTrade], list[dict]]:
    """Buy when fast EMA crosses above slow EMA, sell when crosses below."""
    result = await session.execute(
        select(IndicatorSnapshot)
        .where(IndicatorSnapshot.timestamp >= start_date)
        .order_by(IndicatorSnapshot.timestamp)
    )
    snapshots = result.scalars().all()

    trades: list[_SimTrade] = []
    equity_curve: list[dict] = []
    balance = initial_balance
    open_trade: _SimTrade | None = None

    # Map common MA periods to indicator keys
    ma_key_map = {
        9: "ema_9", 21: "ema_21", 50: "ema_50", 200: "ema_200",
        20: "sma_20", 111: "sma_111",
    }
    fast_key = ma_key_map.get(fast_ma, f"ema_{fast_ma}")
    slow_key = ma_key_map.get(slow_ma, f"ema_{slow_ma}")

    prev_fast: float | None = None
    prev_slow: float | None = None

    for snap in snapshots:
        indicators = snap.indicators or {}
        fast_val = indicators.get(fast_key)
        slow_val = indicators.get(slow_key)

        if fast_val is None or slow_val is None or snap.price is None:
            prev_fast = fast_val
            prev_slow = slow_val
            continue

        # Detect crossovers
        if prev_fast is not None and prev_slow is not None:
            # Bullish cross: fast was below slow, now above
            bullish_cross = prev_fast <= prev_slow and fast_val > slow_val
            # Bearish cross: fast was above slow, now below
            bearish_cross = prev_fast >= prev_slow and fast_val < slow_val

            if open_trade is None and bullish_cross:
                open_trade = _SimTrade(entry_date=snap.timestamp, direction="long", entry_price=snap.price)
            elif open_trade is not None and bearish_cross:
                open_trade.close(snap.timestamp, snap.price)
                position_pct = 0.02
                trade_pnl_usd = balance * position_pct * (open_trade.pnl_pct / 100)
                balance += trade_pnl_usd

                trades.append(open_trade)
                equity_curve.append({
                    "date": snap.timestamp.isoformat(),
                    "equity": round(balance, 2),
                })
                open_trade = None

        prev_fast = fast_val
        prev_slow = slow_val

    # Close any remaining open trade
    if open_trade and snapshots:
        last_snap = snapshots[-1]
        if last_snap.price:
            open_trade.close(last_snap.timestamp, last_snap.price)
            position_pct = 0.02
            trade_pnl_usd = balance * position_pct * (open_trade.pnl_pct / 100)
            balance += trade_pnl_usd
            trades.append(open_trade)
            equity_curve.append({
                "date": last_snap.timestamp.isoformat(),
                "equity": round(balance, 2),
            })

    return trades, equity_curve


@router.post("/run")
async def run_backtest(
    req: BacktestRequest,
    session: AsyncSession = Depends(get_session),
):
    """Run a backtest with the specified strategy and parameters."""
    start_date = datetime.utcnow() - timedelta(days=req.start_days_ago)
    initial = req.initial_balance

    if req.strategy == "ai_signals":
        trades, equity_curve = await _backtest_ai_signals(session, start_date, initial)
    elif req.strategy == "rsi_oversold":
        trades, equity_curve = await _backtest_rsi_oversold(
            session, start_date, initial, rsi_threshold=req.rsi_threshold
        )
    elif req.strategy == "ma_cross":
        trades, equity_curve = await _backtest_ma_cross(
            session, start_date, initial, fast_ma=req.fast_ma, slow_ma=req.slow_ma
        )
    else:
        return {"error": f"Unknown strategy: {req.strategy}"}

    final_balance = equity_curve[-1]["equity"] if equity_curve else initial
    metrics = _compute_metrics(trades, equity_curve, initial, final_balance, req.start_days_ago)

    return {
        "strategy": req.strategy,
        "period_days": req.start_days_ago,
        "initial_balance": initial,
        "final_balance": round(final_balance, 2),
        "total_return_pct": metrics["total_return_pct"],
        "total_trades": metrics["total_trades"],
        "winning_trades": metrics["winning_trades"],
        "losing_trades": metrics["losing_trades"],
        "win_rate": metrics["win_rate"],
        "avg_win": metrics["avg_win"],
        "avg_loss": metrics["avg_loss"],
        "max_drawdown_pct": metrics["max_drawdown_pct"],
        "sharpe_ratio": metrics["sharpe_ratio"],
        "equity_curve": equity_curve,
        "trades": [t.to_dict() for t in trades[-50:]],  # Latest 50 trades
        "timestamp": datetime.utcnow().isoformat(),
    }
