"""Gold-specific lot size and PnL calculations.

All calculations are based on standard gold (XAUUSD) contract specs:
    1 standard lot = 100 troy ounces
    1 mini lot     = 10 troy ounces  (0.10 lots)
    1 micro lot    = 1 troy ounce    (0.01 lots)

    Pip size  = $0.01  (one cent movement in gold spot price)
    Pip value = $1.00  per standard lot ($0.01 * 100 oz)
               $0.10  per mini lot
               $0.01  per micro lot
"""
import logging

logger = logging.getLogger(__name__)


class GoldLotCalculator:
    """Gold-specific lot size and PnL calculator.

    All methods are static for convenience — no instance state needed.
    """

    # Gold contract constants
    CONTRACT_SIZE: float = 100.0      # 100 troy ounces per standard lot
    PIP_SIZE: float = 0.01            # $0.01 per pip
    PIP_VALUE_PER_LOT: float = 1.0    # $1.00 per pip per standard lot

    @staticmethod
    def calculate_lot_size(
        balance: float,
        risk_pct: float,
        sl_pips: float,
        leverage: int = 100,
    ) -> float:
        """Calculate optimal lot size for a gold trade.

        Uses the risk-based position sizing formula:
            lot_size = risk_amount / (sl_pips * pip_value_per_lot)

        The leverage parameter is used for margin validation but does not
        affect the risk-based lot size calculation.

        Args:
            balance: Account balance in USD.
            risk_pct: Percentage of balance to risk (e.g. 1.0 = 1%).
            sl_pips: Stop-loss distance in pips ($0.01 units).
            leverage: Account leverage (for margin awareness, default 100).

        Returns:
            Lot size rounded to 2 decimal places, minimum 0.01.

        Examples:
            # $10,000 account, 1% risk, 500 pip ($5.00) SL
            >>> GoldLotCalculator.calculate_lot_size(10000, 1.0, 500)
            0.2

            # $10,000 account, 2% risk, 1000 pip ($10.00) SL
            >>> GoldLotCalculator.calculate_lot_size(10000, 2.0, 1000)
            0.2
        """
        if sl_pips <= 0:
            logger.warning("SL pips must be positive, returning minimum lot size")
            return 0.01

        if balance <= 0:
            logger.warning("Balance must be positive, returning minimum lot size")
            return 0.01

        risk_amount = balance * (risk_pct / 100.0)
        lot_size = risk_amount / (sl_pips * GoldLotCalculator.PIP_VALUE_PER_LOT)

        # Clamp to reasonable range
        lot_size = max(lot_size, 0.01)   # Minimum micro lot
        lot_size = min(lot_size, 100.0)  # Sanity cap at 100 lots

        return round(lot_size, 2)

    @staticmethod
    def calculate_pnl(
        direction: str,
        entry_price: float,
        exit_price: float,
        lot_size: float,
    ) -> float:
        """Calculate PnL for a gold trade in USD.

        Formula:
            BUY:  (exit - entry) * lot_size * contract_size
            SELL: (entry - exit) * lot_size * contract_size

        Args:
            direction: "buy" or "sell".
            entry_price: Position entry price.
            exit_price: Position exit price.
            lot_size: Position size in lots.

        Returns:
            Profit/loss in USD (negative = loss).

        Examples:
            # Buy 0.1 lots at $2650, close at $2660 = +$100
            >>> GoldLotCalculator.calculate_pnl("buy", 2650.0, 2660.0, 0.1)
            100.0

            # Sell 0.1 lots at $2660, close at $2650 = +$100
            >>> GoldLotCalculator.calculate_pnl("sell", 2660.0, 2650.0, 0.1)
            100.0
        """
        direction = direction.lower()
        contract_size = GoldLotCalculator.CONTRACT_SIZE

        if direction == "buy":
            pnl = (exit_price - entry_price) * lot_size * contract_size
        elif direction == "sell":
            pnl = (entry_price - exit_price) * lot_size * contract_size
        else:
            logger.error("Invalid direction '%s', returning 0 PnL", direction)
            return 0.0

        return round(pnl, 2)

    @staticmethod
    def pips_to_usd(pips: float, lot_size: float) -> float:
        """Convert pips to USD for gold.

        Formula: pips * pip_value_per_lot * lot_size
        (Since pip_value_per_lot = $1.00, this simplifies to pips * lot_size)

        Args:
            pips: Number of pips (in $0.01 units).
            lot_size: Position size in lots.

        Returns:
            USD value.

        Examples:
            # 500 pips ($5.00 move) on 0.1 lots = $50
            >>> GoldLotCalculator.pips_to_usd(500, 0.1)
            50.0
        """
        return round(pips * GoldLotCalculator.PIP_VALUE_PER_LOT * lot_size, 2)

    @staticmethod
    def usd_to_pips(usd: float, lot_size: float) -> float:
        """Convert USD to pips for gold.

        Formula: usd / (pip_value_per_lot * lot_size)

        Args:
            usd: Dollar amount.
            lot_size: Position size in lots.

        Returns:
            Number of pips. Returns 0 if lot_size is zero.

        Examples:
            # $50 on 0.1 lots = 500 pips ($5.00 move)
            >>> GoldLotCalculator.usd_to_pips(50.0, 0.1)
            500.0
        """
        if lot_size <= 0:
            logger.warning("Lot size must be positive for USD-to-pips conversion")
            return 0.0

        return round(usd / (GoldLotCalculator.PIP_VALUE_PER_LOT * lot_size), 2)

    @staticmethod
    def calculate_margin_required(
        price: float,
        lot_size: float,
        leverage: int = 100,
    ) -> float:
        """Calculate margin required for a gold position.

        Formula: (price * lot_size * contract_size) / leverage

        Args:
            price: Current gold price (e.g. 2650.00).
            lot_size: Position size in lots.
            leverage: Account leverage (default 100).

        Returns:
            Required margin in USD.

        Examples:
            # 0.1 lots at $2650 with 100:1 leverage
            # = (2650 * 0.1 * 100) / 100 = $265.00
            >>> GoldLotCalculator.calculate_margin_required(2650.0, 0.1, 100)
            265.0

            # 1.0 lot at $2650 with 100:1 leverage
            # = (2650 * 1.0 * 100) / 100 = $2650.00
            >>> GoldLotCalculator.calculate_margin_required(2650.0, 1.0, 100)
            2650.0
        """
        if leverage <= 0:
            logger.warning("Leverage must be positive, using 1 (no leverage)")
            leverage = 1

        contract_size = GoldLotCalculator.CONTRACT_SIZE
        margin = (price * lot_size * contract_size) / leverage

        return round(margin, 2)

    @staticmethod
    def price_to_pips(price_distance: float) -> float:
        """Convert a gold price distance to pips.

        Args:
            price_distance: Absolute price difference in USD (e.g. $5.00).

        Returns:
            Number of pips (e.g. 500 for a $5.00 move).
        """
        return round(abs(price_distance) / GoldLotCalculator.PIP_SIZE, 1)

    @staticmethod
    def pips_to_price(pips: float) -> float:
        """Convert pips to gold price distance.

        Args:
            pips: Number of pips.

        Returns:
            Price distance in USD (e.g. $5.00 for 500 pips).
        """
        return round(abs(pips) * GoldLotCalculator.PIP_SIZE, 2)
