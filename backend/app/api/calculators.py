"""Gold trading calculators — pure math endpoints, minimal DB for live price."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, Price

router = APIRouter(prefix="/api/calculators", tags=["calculators"])


async def _get_latest_gold_price(session: AsyncSession) -> float:
    """Fetch the latest gold close price from the DB, fallback to 2900."""
    result = await session.execute(
        select(Price).order_by(desc(Price.timestamp)).limit(1)
    )
    price = result.scalar_one_or_none()
    return price.close if price and price.close else 2900.0


@router.get("/pip-value")
async def pip_value(
    lot_size: float = Query(1.0, ge=0.01, le=100, description="Lot size (1 lot = 100 oz)"),
):
    """Calculate XAUUSD pip value. 1 pip = $0.01/oz, 1 lot = 100 oz."""
    contract_size = 100  # 1 lot = 100 troy ounces
    pip_size = 0.01  # $0.01 per oz
    pip_value_usd = lot_size * contract_size * pip_size
    return {
        "lot_size": lot_size,
        "contract_size_oz": contract_size,
        "pip_size_usd": pip_size,
        "pip_value_usd": round(pip_value_usd, 2),
        "ten_pip_value_usd": round(pip_value_usd * 10, 2),
        "one_dollar_move_usd": round(lot_size * contract_size * 1.0, 2),
    }


@router.get("/lot-size")
async def lot_size(
    account_balance: float = Query(..., ge=0, description="Account balance in USD"),
    risk_pct: float = Query(2.0, ge=0.1, le=100, description="Risk percentage"),
    stop_loss_pips: float = Query(..., ge=1, description="Stop loss distance in pips"),
    session: AsyncSession = Depends(get_session),
):
    """Calculate optimal lot size based on risk management."""
    contract_size = 100
    pip_size = 0.01
    gold_price = await _get_latest_gold_price(session)
    risk_amount = account_balance * (risk_pct / 100)
    pip_value_per_lot = contract_size * pip_size  # $1.00 per pip per lot
    lot_size = risk_amount / (stop_loss_pips * pip_value_per_lot) if stop_loss_pips > 0 else 0
    return {
        "account_balance": account_balance,
        "risk_pct": risk_pct,
        "risk_amount_usd": round(risk_amount, 2),
        "stop_loss_pips": stop_loss_pips,
        "recommended_lot_size": round(lot_size, 2),
        "position_value_usd": round(lot_size * contract_size * gold_price, 2),
        "gold_price_used": gold_price,
    }


@router.get("/margin")
async def margin(
    lot_size: float = Query(1.0, ge=0.01, le=100),
    leverage: int = Query(100, ge=1, le=2000),
    gold_price: float = Query(2900.0, ge=100),
):
    """Calculate required margin for XAUUSD position."""
    contract_size = 100
    position_value = lot_size * contract_size * gold_price
    required_margin = position_value / leverage
    return {
        "lot_size": lot_size,
        "leverage": f"1:{leverage}",
        "gold_price": gold_price,
        "position_value_usd": round(position_value, 2),
        "required_margin_usd": round(required_margin, 2),
        "contract_size_oz": contract_size,
    }


@router.get("/pnl")
async def pnl(
    entry_price: float = Query(..., ge=100),
    exit_price: float = Query(..., ge=100),
    lot_size: float = Query(1.0, ge=0.01, le=100),
    direction: str = Query("buy", pattern="^(buy|sell)$"),
):
    """Calculate trade P&L for XAUUSD."""
    contract_size = 100
    if direction == "buy":
        pnl_per_oz = exit_price - entry_price
    else:
        pnl_per_oz = entry_price - exit_price
    total_pnl = pnl_per_oz * lot_size * contract_size
    pips = abs(exit_price - entry_price) / 0.01
    return {
        "entry_price": entry_price,
        "exit_price": exit_price,
        "direction": direction,
        "lot_size": lot_size,
        "pnl_usd": round(total_pnl, 2),
        "pnl_pips": round(pips, 1),
        "pnl_per_oz": round(pnl_per_oz, 2),
    }


@router.get("/weight-convert")
async def weight_convert(
    amount: float = Query(1.0, ge=0),
    from_unit: str = Query("troy_oz", pattern="^(troy_oz|gram|kg|tola|tael|baht)$"),
):
    """Convert between gold weight units."""
    # All factors are relative to grams
    to_grams = {
        "troy_oz": 31.1035,
        "gram": 1.0,
        "kg": 1000.0,
        "tola": 11.6638,
        "tael": 37.429,
        "baht": 15.244,
    }
    base_grams = amount * to_grams[from_unit]
    conversions = {unit: round(base_grams / factor, 6) for unit, factor in to_grams.items()}
    return {
        "amount": amount,
        "from_unit": from_unit,
        "base_grams": round(base_grams, 4),
        "conversions": conversions,
    }


@router.get("/melt-value")
async def melt_value(
    weight_oz: float = Query(1.0, ge=0),
    karat: int = Query(24, ge=8, le=24),
    spot_price: float = Query(2900.0, ge=100),
):
    """Calculate gold melt value based on weight and purity."""
    purity_map = {
        24: 0.999, 22: 0.9167, 21: 0.875, 18: 0.75,
        14: 0.5833, 12: 0.5, 10: 0.4167, 9: 0.375, 8: 0.333,
    }
    purity = purity_map.get(karat, karat / 24.0)
    pure_gold_oz = weight_oz * purity
    melt_val = pure_gold_oz * spot_price
    return {
        "weight_oz": weight_oz,
        "karat": karat,
        "purity_pct": round(purity * 100, 1),
        "pure_gold_oz": round(pure_gold_oz, 4),
        "spot_price": spot_price,
        "melt_value_usd": round(melt_val, 2),
    }
