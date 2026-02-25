"""Griffin Gold — Gold-specific Quant Theory Predictor.

16 indicators across 3 tiers optimized for XAUUSD price prediction.

Tier 1 — Primary drivers (45%):
  real_yield_zscore, dxy_correlation, cot_positioning,
  inflation_surprise, fed_policy_deviation

Tier 2 — High reliability (35%):
  etf_flow_momentum, gold_silver_ratio, central_bank_buying,
  vix_regime, tips_breakeven_momentum

Tier 3 — Supplementary (20%):
  london_fix_premium, seasonal_pattern, atr_regime,
  round_number_psychology, mining_equity_ratio, session_momentum
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Monthly gold seasonality scores (empirical averages from 20+ years)
# Positive = historically bullish month, negative = bearish
GOLD_SEASONALITY = {
    1: +30,   # January — strong start, portfolio rebalancing
    2: +10,   # February — mild continuation
    3: 0,     # March — flat, quarter-end flows
    4: -10,   # April — tax selling, mild weakness
    5: -10,   # May — "sell in May" spill-over
    6: -20,   # June — weakest month, summer doldrums begin
    7: -20,   # July — continued summer weakness
    8: +10,   # August — Indian buying season starts
    9: +30,   # September — strong, Indian festival demand
    10: +20,  # October — continued festival demand
    11: +30,  # November — wedding season, year-end positioning
    12: +10,  # December — holiday buying, mild strength
}


class GoldQuantPredictor:
    """Quantitative gold predictor using 16 gold-specific indicators.

    Each indicator produces a standardised result dict:
        score:     float in [-100, +100] (positive = bullish gold)
        signal:    "bullish" | "bearish" | "neutral"
        reasoning: human-readable explanation
        data:      dict of raw values used in the calculation

    The composite ``predict()`` method runs all 16, applies tier-based
    weights, and produces directional forecasts for 1 h / 4 h / 24 h / 1 w.
    """

    # ── Indicator weights by tier ─────────────────────────
    INDICATORS = {
        # Tier 1 — Primary drivers (45%)
        "real_yield_zscore":       {"weight": 0.10, "tier": 1},
        "dxy_correlation":         {"weight": 0.09, "tier": 1},
        "cot_positioning":         {"weight": 0.09, "tier": 1},
        "inflation_surprise":      {"weight": 0.09, "tier": 1},
        "fed_policy_deviation":    {"weight": 0.08, "tier": 1},
        # Tier 2 — High reliability (35%)
        "etf_flow_momentum":       {"weight": 0.07, "tier": 2},
        "gold_silver_ratio":       {"weight": 0.07, "tier": 2},
        "central_bank_buying":     {"weight": 0.07, "tier": 2},
        "vix_regime":              {"weight": 0.07, "tier": 2},
        "tips_breakeven_momentum": {"weight": 0.07, "tier": 2},
        # Tier 3 — Supplementary (20%)
        "london_fix_premium":      {"weight": 0.04, "tier": 3},
        "seasonal_pattern":        {"weight": 0.04, "tier": 3},
        "atr_regime":              {"weight": 0.04, "tier": 3},
        "round_number_psychology": {"weight": 0.04, "tier": 3},
        "mining_equity_ratio":     {"weight": 0.02, "tier": 3},
        "session_momentum":        {"weight": 0.02, "tier": 3},
    }

    # Dispatch table: indicator name -> method name
    _DISPATCH = {
        "real_yield_zscore":       "_calc_real_yield_zscore",
        "dxy_correlation":         "_calc_dxy_correlation",
        "cot_positioning":         "_calc_cot_positioning",
        "inflation_surprise":      "_calc_inflation_surprise",
        "fed_policy_deviation":    "_calc_fed_policy_deviation",
        "etf_flow_momentum":       "_calc_etf_flow_momentum",
        "gold_silver_ratio":       "_calc_gold_silver_ratio",
        "central_bank_buying":     "_calc_central_bank_buying",
        "vix_regime":              "_calc_vix_regime",
        "tips_breakeven_momentum": "_calc_tips_breakeven_momentum",
        "london_fix_premium":      "_calc_london_fix_premium",
        "seasonal_pattern":        "_calc_seasonal_pattern",
        "atr_regime":              "_calc_atr_regime",
        "round_number_psychology": "_calc_round_number_psychology",
        "mining_equity_ratio":     "_calc_mining_equity_ratio",
        "session_momentum":        "_calc_session_momentum",
    }

    # ─────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────

    @staticmethod
    def _clamp(value: float, lo: float = -100.0, hi: float = 100.0) -> float:
        """Clamp *value* into [lo, hi]."""
        return max(lo, min(hi, value))

    @staticmethod
    def _label(score: float, threshold: float = 10.0) -> str:
        """Convert a numeric score to a directional label."""
        if score > threshold:
            return "bullish"
        elif score < -threshold:
            return "bearish"
        return "neutral"

    @staticmethod
    def _neutral(reason: str) -> dict:
        """Convenience: return a neutral / no-data result."""
        return {
            "score": 0.0,
            "signal": "neutral",
            "reasoning": reason,
            "data": {},
        }

    @staticmethod
    def _safe_array(raw, key: str = "closes") -> Optional[np.ndarray]:
        """Extract a numeric array from *raw* (list, ndarray, or None).

        Returns None when the data is missing or has fewer than 2 elements.
        """
        val = raw.get(key) if isinstance(raw, dict) else None
        if val is None:
            return None
        arr = np.asarray(val, dtype=float)
        if arr.ndim == 0 or len(arr) < 2:
            return None
        return arr

    # ─────────────────────────────────────────────────────
    # 1. Real Yield Z-Score
    # ─────────────────────────────────────────────────────

    def _calc_real_yield_zscore(self, md: dict) -> dict:
        """Z-score of 10-Year TIPS real yield (DFII10) over trailing 1 year.

        Negative real yields are bullish for gold because gold's zero-yield
        becomes relatively attractive.  A z-score > +1 (high real yields) is
        bearish; z-score < -1 (deeply negative real yields) is bullish.

        Expected keys in *md*:
            real_yields: list[float]  — daily 10Y TIPS yields, newest last
        """
        series = self._safe_array(md, "real_yields")
        if series is None or len(series) < 30:
            return self._neutral("Insufficient real-yield data for Z-score")

        # Use up to 252 trading days (1 year)
        lookback = min(252, len(series))
        window = series[-lookback:]
        current = window[-1]
        mean = float(np.mean(window))
        std = float(np.std(window))

        if std < 1e-6:
            return self._neutral("Real-yield variance near zero")

        z = (current - mean) / std

        # Mapping: z > +1 → bearish gold (high real yield)
        #          z < -1 → bullish gold (deeply negative real yield)
        # Linear interpolation in [-2, +2] range → [-80, +80] inverted
        score = self._clamp(-z * 40, -80, 80)

        return {
            "score": round(score, 1),
            "signal": self._label(score),
            "reasoning": (
                f"10Y TIPS real yield {current:.3f}% "
                f"(z={z:+.2f} over {lookback}d). "
                f"{'Negative real yield supports gold' if z < 0 else 'High real yield pressures gold'}."
            ),
            "data": {
                "current_yield": round(current, 4),
                "mean_1y": round(mean, 4),
                "std_1y": round(std, 4),
                "z_score": round(z, 3),
            },
        }

    # ─────────────────────────────────────────────────────
    # 2. DXY Correlation
    # ─────────────────────────────────────────────────────

    def _calc_dxy_correlation(self, md: dict) -> dict:
        """20-day rolling correlation between DXY and gold, multiplied by
        recent DXY momentum.

        Gold and the dollar are inversely correlated (~-0.80 over long
        periods).  A falling dollar with strong negative correlation is
        bullish for gold.

        Expected keys:
            dxy_prices:  list[float] — daily DXY closes, newest last
            gold_prices: list[float] — daily gold closes, newest last
        """
        dxy = self._safe_array(md, "dxy_prices")
        gold = self._safe_array(md, "gold_prices")

        if dxy is None or gold is None:
            return self._neutral("Missing DXY or gold price series")

        min_len = min(len(dxy), len(gold))
        if min_len < 22:
            return self._neutral("Need 22+ days for DXY correlation")

        dxy = dxy[-min_len:]
        gold = gold[-min_len:]

        # 20-day rolling correlation (use last 20 returns)
        dxy_ret = np.diff(np.log(dxy[-21:]))
        gold_ret = np.diff(np.log(gold[-21:]))

        if len(dxy_ret) < 20 or len(gold_ret) < 20:
            return self._neutral("Insufficient return data for correlation")

        corr = float(np.corrcoef(dxy_ret, gold_ret)[0, 1])
        if np.isnan(corr):
            corr = 0.0

        # DXY 5-day momentum (percent change)
        dxy_mom = (dxy[-1] / dxy[-6] - 1) if len(dxy) >= 6 and dxy[-6] > 0 else 0.0

        # Strong negative correlation + falling DXY → bullish gold
        # Multiply momentum direction by abs(correlation) for strength
        raw = -dxy_mom * abs(corr) * 100  # invert: DXY down → positive score
        score = self._clamp(raw * 40, -80, 80)

        return {
            "score": round(score, 1),
            "signal": self._label(score),
            "reasoning": (
                f"DXY 20d corr with gold: {corr:.2f}, "
                f"DXY 5d momentum: {dxy_mom:+.2%}. "
                f"{'Falling dollar supports gold' if dxy_mom < 0 else 'Rising dollar pressures gold'}."
            ),
            "data": {
                "correlation_20d": round(corr, 3),
                "dxy_momentum_5d": round(dxy_mom, 4),
                "dxy_latest": round(float(dxy[-1]), 2),
            },
        }

    # ─────────────────────────────────────────────────────
    # 3. COT Positioning
    # ─────────────────────────────────────────────────────

    def _calc_cot_positioning(self, md: dict) -> dict:
        """Managed-money net positioning as a percentile of a 3-year range.

        Contrarian at extremes: >90th percentile = crowded long = bearish;
        <10th percentile = washed-out = contrarian bullish.

        Expected keys:
            cot_net_positions: list[float] — weekly net contracts, newest last
        """
        series = self._safe_array(md, "cot_net_positions")
        if series is None or len(series) < 26:
            return self._neutral("Insufficient COT data (need 26+ weeks)")

        # Use up to 156 weeks (~3 years)
        lookback = min(156, len(series))
        window = series[-lookback:]
        current = float(window[-1])
        pmin = float(np.min(window))
        pmax = float(np.max(window))

        if pmax - pmin < 1e-6:
            return self._neutral("COT range is flat — no signal")

        percentile = (current - pmin) / (pmax - pmin) * 100

        # Contrarian mapping
        if percentile > 90:
            score = -60.0
            reason = f"COT {percentile:.0f}th pctl — crowded long, contrarian bearish"
        elif percentile > 75:
            score = -30.0
            reason = f"COT {percentile:.0f}th pctl — elevated long positioning"
        elif percentile < 10:
            score = +60.0
            reason = f"COT {percentile:.0f}th pctl — washed out, contrarian bullish"
        elif percentile < 25:
            score = +30.0
            reason = f"COT {percentile:.0f}th pctl — light positioning, room for longs"
        else:
            score = 0.0
            reason = f"COT {percentile:.0f}th pctl — neutral positioning"

        return {
            "score": round(score, 1),
            "signal": self._label(score),
            "reasoning": reason,
            "data": {
                "net_contracts": round(current, 0),
                "percentile_3y": round(percentile, 1),
                "range_min": round(pmin, 0),
                "range_max": round(pmax, 0),
            },
        }

    # ─────────────────────────────────────────────────────
    # 4. Inflation Surprise
    # ─────────────────────────────────────────────────────

    def _calc_inflation_surprise(self, md: dict) -> dict:
        """CPI / PCE actual vs expectation.

        Positive surprise (actual > forecast) is bullish for gold because
        it increases real-asset demand.  Falls back to YoY trend if
        forecast data is unavailable.

        Expected keys:
            cpi_actual:   float — latest CPI reading (YoY %)
            cpi_forecast: float — consensus forecast (YoY %)
            cpi_previous: float — previous release (YoY %)
            pce_actual:   float (optional fallback)
            pce_forecast: float (optional)
        """
        actual = md.get("cpi_actual")
        forecast = md.get("cpi_forecast")
        previous = md.get("cpi_previous")

        # Fallback to PCE if CPI missing
        if actual is None:
            actual = md.get("pce_actual")
            forecast = md.get("pce_forecast")
            previous = md.get("pce_previous")

        if actual is None:
            return self._neutral("No CPI/PCE data available")

        surprise = None
        if forecast is not None:
            surprise = actual - forecast
        elif previous is not None:
            surprise = actual - previous
        else:
            # Only have the absolute value — neutral
            return self._neutral(f"CPI at {actual}% but no forecast/previous for comparison")

        # Scale: each 0.1pp surprise ~ 20 points, capped
        score = self._clamp(surprise * 200, -80, 80)

        direction = "above" if surprise > 0 else "below"
        ref = forecast if forecast is not None else previous
        label = "forecast" if forecast is not None else "previous"

        return {
            "score": round(score, 1),
            "signal": self._label(score),
            "reasoning": (
                f"Inflation {actual:.2f}% vs {label} {ref:.2f}% "
                f"(surprise {surprise:+.2f}pp). "
                f"{'Hot inflation supports gold' if surprise > 0 else 'Cool inflation pressures gold'}."
            ),
            "data": {
                "actual": actual,
                "forecast": forecast,
                "previous": previous,
                "surprise_pp": round(surprise, 3),
            },
        }

    # ─────────────────────────────────────────────────────
    # 5. Fed Policy Deviation
    # ─────────────────────────────────────────────────────

    def _calc_fed_policy_deviation(self, md: dict) -> dict:
        """Gap between current fed-funds rate and market-implied expectations.

        If the market prices in more cuts than the current rate, that is
        bullish for gold (lower rates ahead → lower opportunity cost).

        Expected keys:
            fed_funds_rate:    float — current effective FFR (e.g. 5.33)
            fed_funds_implied: float — 12-month fed-funds future rate
        """
        current = md.get("fed_funds_rate")
        implied = md.get("fed_funds_implied")

        if current is None or implied is None:
            return self._neutral("Missing fed-funds rate or implied rate data")

        # Deviation: current - implied. Positive = market expects cuts = bullish gold
        deviation = current - implied

        # Each 25 bps of expected cuts ~ +25 score, capped at +/- 75
        score = self._clamp(deviation * 100, -75, 75)

        if deviation > 0:
            cuts_bp = deviation * 100
            reason = (
                f"Market prices {cuts_bp:.0f}bp of cuts "
                f"(FFR {current:.2f}% vs implied {implied:.2f}%). "
                f"Easing expectations bullish for gold."
            )
        elif deviation < 0:
            hikes_bp = abs(deviation) * 100
            reason = (
                f"Market prices {hikes_bp:.0f}bp of hikes "
                f"(FFR {current:.2f}% vs implied {implied:.2f}%). "
                f"Tightening expectations bearish for gold."
            )
        else:
            reason = f"FFR {current:.2f}% matches implied — no deviation."

        return {
            "score": round(score, 1),
            "signal": self._label(score),
            "reasoning": reason,
            "data": {
                "fed_funds_rate": current,
                "fed_funds_implied": implied,
                "deviation_pct": round(deviation, 4),
            },
        }

    # ─────────────────────────────────────────────────────
    # 6. ETF Flow Momentum
    # ─────────────────────────────────────────────────────

    def _calc_etf_flow_momentum(self, md: dict) -> dict:
        """5-day vs 20-day moving-average crossover of daily gold-ETF flows.

        Rising short-term flows crossing above the longer-term average
        signal institutional accumulation (bullish).

        Expected keys:
            etf_flows: list[float] — daily net flows in tonnes, newest last
        """
        flows = self._safe_array(md, "etf_flows")
        if flows is None or len(flows) < 20:
            return self._neutral("Insufficient ETF flow data (need 20+ days)")

        ma5 = float(np.mean(flows[-5:]))
        ma20 = float(np.mean(flows[-20:]))
        net_5d = float(np.sum(flows[-5:]))

        diff = ma5 - ma20

        # Scale: each 1 tonne/day diff ~ 10 points
        score = self._clamp(diff * 10, -70, 70)

        return {
            "score": round(score, 1),
            "signal": self._label(score),
            "reasoning": (
                f"ETF flow MA5={ma5:.1f}t/d vs MA20={ma20:.1f}t/d "
                f"(diff {diff:+.1f}). Net 5d: {net_5d:+.1f}t. "
                f"{'Positive crossover = institutional buying' if diff > 0 else 'Negative crossover = outflows'}."
            ),
            "data": {
                "ma5_flow": round(ma5, 2),
                "ma20_flow": round(ma20, 2),
                "crossover_diff": round(diff, 2),
                "net_5d_tonnes": round(net_5d, 2),
            },
        }

    # ─────────────────────────────────────────────────────
    # 7. Gold/Silver Ratio
    # ─────────────────────────────────────────────────────

    def _calc_gold_silver_ratio(self, md: dict) -> dict:
        """Gold/silver ratio mean-reversion signal.

        Historical mean ~ 80.  Above 90 indicates gold is expensive
        relative to silver (potential mean reversion down = bearish gold
        relative).  Below 70 indicates gold is cheap relative to silver
        (bullish gold relative).

        Uses deviation from 200-day MA when available, otherwise raw level.

        Expected keys:
            gold_silver_ratio: list[float] — daily ratio, newest last
              OR
            gold_prices:  list[float]
            silver_prices: list[float]
        """
        ratio_series = self._safe_array(md, "gold_silver_ratio")

        # Build from gold/silver if direct ratio unavailable
        if ratio_series is None:
            gold = self._safe_array(md, "gold_prices")
            silver = self._safe_array(md, "silver_prices")
            if gold is not None and silver is not None:
                min_len = min(len(gold), len(silver))
                gold = gold[-min_len:]
                silver = silver[-min_len:]
                with np.errstate(divide="ignore", invalid="ignore"):
                    ratio_series = np.where(silver > 0, gold / silver, np.nan)
                ratio_series = ratio_series[~np.isnan(ratio_series)]
                if len(ratio_series) < 2:
                    ratio_series = None

        if ratio_series is None or len(ratio_series) < 5:
            return self._neutral("Insufficient gold/silver ratio data")

        current = float(ratio_series[-1])

        # 200-day MA if enough data, else use available
        lookback = min(200, len(ratio_series))
        ma200 = float(np.mean(ratio_series[-lookback:]))

        deviation = current - ma200

        # Mapping: above 90 (overvalued gold vs silver) = bearish tilt
        #          below 70 (undervalued gold vs silver) = bullish tilt
        level_score = 0.0
        if current > 95:
            level_score = -40
        elif current > 90:
            level_score = -25
        elif current > 85:
            level_score = -10
        elif current < 65:
            level_score = +40
        elif current < 70:
            level_score = +25
        elif current < 75:
            level_score = +10

        # MA deviation score: above MA = bearish tilt for gold
        ma_score = self._clamp(-deviation * 3, -30, 30)

        score = self._clamp(level_score + ma_score, -70, 70)

        return {
            "score": round(score, 1),
            "signal": self._label(score),
            "reasoning": (
                f"Gold/Silver ratio {current:.1f} "
                f"(200d MA {ma200:.1f}, dev {deviation:+.1f}). "
                f"{'Elevated ratio — gold relatively expensive' if current > 85 else 'Low ratio — gold relatively cheap' if current < 75 else 'Ratio near fair value'}."
            ),
            "data": {
                "current_ratio": round(current, 2),
                "ma200": round(ma200, 2),
                "deviation_from_ma": round(deviation, 2),
            },
        }

    # ─────────────────────────────────────────────────────
    # 8. Central Bank Buying
    # ─────────────────────────────────────────────────────

    def _calc_central_bank_buying(self, md: dict) -> dict:
        """Rolling 3-month net central-bank gold purchases.

        Central banks have been structural buyers since 2010. Heavy buying
        (>200 t/quarter) provides strong price support.

        Expected keys:
            cb_purchases_quarterly: float — tonnes in the latest quarter
              OR
            cb_purchases_monthly: list[float] — monthly purchases, newest last
        """
        quarterly = md.get("cb_purchases_quarterly")

        if quarterly is None:
            monthly = self._safe_array(md, "cb_purchases_monthly")
            if monthly is not None and len(monthly) >= 3:
                quarterly = float(np.sum(monthly[-3:]))
            else:
                return self._neutral("No central-bank purchase data available")

        if quarterly > 200:
            score = 70.0
            reason = f"Central banks bought {quarterly:.0f}t this quarter — very strong structural support"
        elif quarterly > 100:
            score = 40.0
            reason = f"Central banks bought {quarterly:.0f}t this quarter — moderate support"
        elif quarterly > 50:
            score = 15.0
            reason = f"Central banks bought {quarterly:.0f}t this quarter — mild support"
        elif quarterly > 0:
            score = 0.0
            reason = f"Central banks bought {quarterly:.0f}t this quarter — minimal impact"
        elif quarterly > -50:
            score = -15.0
            reason = f"Central banks net sold {abs(quarterly):.0f}t — mild headwind"
        else:
            score = -40.0
            reason = f"Central banks net sold {abs(quarterly):.0f}t — significant selling pressure"

        return {
            "score": round(score, 1),
            "signal": self._label(score),
            "reasoning": reason,
            "data": {
                "quarterly_tonnes": round(quarterly, 1),
            },
        }

    # ─────────────────────────────────────────────────────
    # 9. VIX Regime
    # ─────────────────────────────────────────────────────

    def _calc_vix_regime(self, md: dict) -> dict:
        """VIX-based safe-haven signal.

        Gold benefits from elevated volatility as investors seek safety.

        Expected keys:
            vix: float — latest VIX close
        """
        vix = md.get("vix")
        if vix is None:
            return self._neutral("No VIX data available")

        vix = float(vix)

        if vix > 35:
            score = 70.0
            reason = f"VIX {vix:.1f} — crisis mode, strong safe-haven demand for gold"
        elif vix > 25:
            score = 50.0
            reason = f"VIX {vix:.1f} — elevated fear, gold attracts safe-haven flows"
        elif vix > 15:
            score = 20.0
            reason = f"VIX {vix:.1f} — moderate uncertainty, slight gold tailwind"
        elif vix > 12:
            score = 0.0
            reason = f"VIX {vix:.1f} — calm markets, no safe-haven premium"
        else:
            score = -10.0
            reason = f"VIX {vix:.1f} — extreme complacency, risk-on favours equities over gold"

        return {
            "score": round(score, 1),
            "signal": self._label(score),
            "reasoning": reason,
            "data": {"vix": round(vix, 2)},
        }

    # ─────────────────────────────────────────────────────
    # 10. TIPS Breakeven Momentum
    # ─────────────────────────────────────────────────────

    def _calc_tips_breakeven_momentum(self, md: dict) -> dict:
        """Rate of change of 10-Year breakeven inflation (T10YIE).

        Rising breakeven = market expects more inflation = bullish gold.
        Falling breakeven = disinflation expectations = bearish gold.

        Expected keys:
            breakeven_rates: list[float] — daily T10YIE, newest last
        """
        series = self._safe_array(md, "breakeven_rates")
        if series is None or len(series) < 22:
            return self._neutral("Insufficient breakeven-rate data (need 22+ days)")

        current = float(series[-1])
        prev_5d = float(series[-6]) if len(series) >= 6 else float(series[0])
        prev_20d = float(series[-21]) if len(series) >= 21 else float(series[0])

        roc_5d = current - prev_5d
        roc_20d = current - prev_20d

        # Combined score: 5d (fast) + 20d (trend)
        raw = roc_5d * 150 + roc_20d * 100
        score = self._clamp(raw, -70, 70)

        return {
            "score": round(score, 1),
            "signal": self._label(score),
            "reasoning": (
                f"Breakeven inflation {current:.3f}% "
                f"(5d chg {roc_5d:+.3f}pp, 20d chg {roc_20d:+.3f}pp). "
                f"{'Rising inflation expectations support gold' if roc_20d > 0 else 'Falling inflation expectations pressure gold'}."
            ),
            "data": {
                "current_breakeven": round(current, 4),
                "roc_5d_pp": round(roc_5d, 4),
                "roc_20d_pp": round(roc_20d, 4),
            },
        }

    # ─────────────────────────────────────────────────────
    # 11. London Fix Premium
    # ─────────────────────────────────────────────────────

    def _calc_london_fix_premium(self, md: dict) -> dict:
        """AM-vs-PM London fix differential proxy.

        When the PM fix is consistently above the AM fix, physical demand
        is strong (bullish).  Uses session open/close as proxy if intraday
        fix data is unavailable.

        Expected keys (preferred):
            london_am_fix: list[float] — daily AM fixes, newest last
            london_pm_fix: list[float] — daily PM fixes, newest last
        Fallback:
            session_open:  list[float]
            session_close: list[float]
        """
        am = self._safe_array(md, "london_am_fix")
        pm = self._safe_array(md, "london_pm_fix")

        if am is None or pm is None:
            am = self._safe_array(md, "session_open")
            pm = self._safe_array(md, "session_close")

        if am is None or pm is None:
            return self._neutral("No London fix or session open/close data")

        min_len = min(len(am), len(pm))
        if min_len < 5:
            return self._neutral("Need 5+ days for London fix premium")

        am = am[-min_len:]
        pm = pm[-min_len:]

        # Average premium over last 5 days
        premiums = pm[-5:] - am[-5:]
        avg_premium = float(np.mean(premiums))
        latest_premium = float(premiums[-1])

        # Each $1 premium ~ 10 points
        score = self._clamp(avg_premium * 10, -40, 40)

        return {
            "score": round(score, 1),
            "signal": self._label(score),
            "reasoning": (
                f"London fix 5d avg premium ${avg_premium:+.2f} "
                f"(latest ${latest_premium:+.2f}). "
                f"{'PM > AM = physical demand strength' if avg_premium > 0 else 'AM > PM = weak physical demand'}."
            ),
            "data": {
                "avg_premium_5d": round(avg_premium, 2),
                "latest_premium": round(latest_premium, 2),
            },
        }

    # ─────────────────────────────────────────────────────
    # 12. Seasonal Pattern
    # ─────────────────────────────────────────────────────

    def _calc_seasonal_pattern(self, md: dict) -> dict:
        """Monthly seasonality factor based on 20+ years of gold returns.

        Uses the GOLD_SEASONALITY lookup table defined at module level.

        Expected keys: (none required — uses current date)
        """
        now = md.get("timestamp")
        if now is None or not isinstance(now, datetime):
            now = datetime.utcnow()

        month = now.month
        score = float(GOLD_SEASONALITY.get(month, 0))
        month_name = now.strftime("%B")

        return {
            "score": round(score, 1),
            "signal": self._label(score),
            "reasoning": (
                f"Month: {month_name} — historical seasonal score {score:+.0f}. "
                f"{'Seasonally bullish period' if score > 0 else 'Seasonally weak period' if score < 0 else 'Seasonally neutral'}."
            ),
            "data": {
                "month": month,
                "month_name": month_name,
                "seasonal_score": score,
            },
        }

    # ─────────────────────────────────────────────────────
    # 13. ATR Regime
    # ─────────────────────────────────────────────────────

    def _calc_atr_regime(self, md: dict) -> dict:
        """ATR percentile over 1 year to detect volatility regimes.

        Low ATR (<20th pctl) indicates compression — expect breakout
        (slight bullish bias).  High ATR (>80th pctl) indicates potential
        exhaustion / reversion.

        Expected keys:
            highs:  list[float] — daily highs, newest last
            lows:   list[float] — daily lows, newest last
            closes: list[float] — daily closes, newest last
        """
        highs = self._safe_array(md, "highs")
        lows = self._safe_array(md, "lows")
        closes = self._safe_array(md, "closes")

        if highs is None or lows is None or closes is None:
            return self._neutral("Missing OHLC data for ATR calculation")

        min_len = min(len(highs), len(lows), len(closes))
        if min_len < 15:
            return self._neutral("Need 15+ days for ATR regime")

        highs = highs[-min_len:]
        lows = lows[-min_len:]
        closes = closes[-min_len:]

        # True Range
        n = len(closes)
        tr = np.empty(n - 1)
        for i in range(1, n):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i - 1])
            lc = abs(lows[i] - closes[i - 1])
            tr[i - 1] = max(hl, hc, lc)

        if len(tr) < 14:
            return self._neutral("Not enough true-range values for ATR")

        # 14-period ATR for each day
        atrs = []
        for i in range(13, len(tr)):
            atrs.append(float(np.mean(tr[i - 13 : i + 1])))

        if len(atrs) < 5:
            return self._neutral("ATR history too short for regime detection")

        atrs = np.array(atrs)
        current_atr = float(atrs[-1])

        # Percentile over available history (up to 252)
        lookback = min(252, len(atrs))
        window = atrs[-lookback:]
        percentile = float(np.sum(window <= current_atr) / len(window) * 100)

        if percentile < 20:
            score = 30.0
            reason = (
                f"ATR {current_atr:.2f} at {percentile:.0f}th pctl — "
                f"volatility compression, potential breakout ahead"
            )
        elif percentile > 80:
            score = -20.0
            reason = (
                f"ATR {current_atr:.2f} at {percentile:.0f}th pctl — "
                f"high volatility, potential exhaustion/reversion"
            )
        else:
            score = 0.0
            reason = f"ATR {current_atr:.2f} at {percentile:.0f}th pctl — normal volatility regime"

        return {
            "score": round(score, 1),
            "signal": self._label(score),
            "reasoning": reason,
            "data": {
                "current_atr": round(current_atr, 2),
                "atr_percentile_1y": round(percentile, 1),
            },
        }

    # ─────────────────────────────────────────────────────
    # 14. Round Number Psychology
    # ─────────────────────────────────────────────────────

    def _calc_round_number_psychology(self, md: dict) -> dict:
        """Proximity to $100 gold-price increments.

        Gold traders watch round $100 levels ($1900, $2000, $2100...).
        Within $10: acts as support (if approaching from above) or
        resistance (if approaching from below).

        Expected keys:
            current_price: float — latest XAUUSD price
            closes:        list[float] — recent closes for trend detection
        """
        price = md.get("current_price")
        if price is None:
            closes = self._safe_array(md, "closes")
            if closes is not None and len(closes) > 0:
                price = float(closes[-1])
            else:
                return self._neutral("No current gold price available")

        price = float(price)

        # Nearest $100 levels
        lower_round = math.floor(price / 100) * 100
        upper_round = lower_round + 100

        dist_to_lower = price - lower_round
        dist_to_upper = upper_round - price

        # Determine trend (last 5 days)
        closes = self._safe_array(md, "closes")
        trending_up = True  # default assumption
        if closes is not None and len(closes) >= 5:
            trending_up = float(closes[-1]) > float(closes[-5])

        # Within $10 of a round number
        if dist_to_upper <= 10:
            if trending_up:
                score = -25.0
                reason = (
                    f"Price ${price:,.1f} within ${dist_to_upper:.1f} of "
                    f"resistance at ${upper_round:,} — potential rejection"
                )
            else:
                score = 15.0
                reason = (
                    f"Price ${price:,.1f} pulling back near ${upper_round:,} — "
                    f"may consolidate before breakout"
                )
        elif dist_to_lower <= 10:
            if not trending_up:
                score = 25.0
                reason = (
                    f"Price ${price:,.1f} within ${dist_to_lower:.1f} of "
                    f"support at ${lower_round:,} — potential bounce"
                )
            else:
                score = -15.0
                reason = (
                    f"Price ${price:,.1f} near ${lower_round:,} — "
                    f"recently broke above, may retest"
                )
        else:
            score = 0.0
            reason = (
                f"Price ${price:,.1f} between ${lower_round:,} and "
                f"${upper_round:,} — no round-number influence"
            )

        return {
            "score": round(score, 1),
            "signal": self._label(score),
            "reasoning": reason,
            "data": {
                "price": round(price, 2),
                "nearest_support": lower_round,
                "nearest_resistance": upper_round,
                "dist_to_support": round(dist_to_lower, 2),
                "dist_to_resistance": round(dist_to_upper, 2),
            },
        }

    # ─────────────────────────────────────────────────────
    # 15. Mining Equity Ratio
    # ─────────────────────────────────────────────────────

    def _calc_mining_equity_ratio(self, md: dict) -> dict:
        """GDX/GLD ratio trend as a leading indicator.

        When miners (GDX) outperform physical gold (GLD), it signals
        improving expectations for gold prices (bullish divergence).
        Declining ratio = bearish divergence.

        Expected keys:
            gdx_prices: list[float] — daily GDX closes, newest last
            gld_prices: list[float] — daily GLD closes, newest last
        """
        gdx = self._safe_array(md, "gdx_prices")
        gld = self._safe_array(md, "gld_prices")

        if gdx is None or gld is None:
            return self._neutral("Missing GDX or GLD data for mining-equity ratio")

        min_len = min(len(gdx), len(gld))
        if min_len < 22:
            return self._neutral("Need 22+ days for mining-equity ratio")

        gdx = gdx[-min_len:]
        gld = gld[-min_len:]

        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(gld > 0, gdx / gld, np.nan)
        ratio = ratio[~np.isnan(ratio)]

        if len(ratio) < 22:
            return self._neutral("Not enough valid ratio data points")

        current = float(ratio[-1])
        ratio_5d = float(ratio[-6]) if len(ratio) >= 6 else float(ratio[0])
        ratio_20d = float(ratio[-21]) if len(ratio) >= 21 else float(ratio[0])

        chg_5d = (current / ratio_5d - 1) if ratio_5d > 0 else 0
        chg_20d = (current / ratio_20d - 1) if ratio_20d > 0 else 0

        # Rising ratio = miners outperforming = bullish gold
        raw = chg_5d * 200 + chg_20d * 150
        score = self._clamp(raw, -50, 50)

        return {
            "score": round(score, 1),
            "signal": self._label(score),
            "reasoning": (
                f"GDX/GLD ratio {current:.4f} "
                f"(5d chg {chg_5d:+.2%}, 20d chg {chg_20d:+.2%}). "
                f"{'Miners outperforming — bullish gold lead' if chg_20d > 0 else 'Miners lagging — bearish divergence'}."
            ),
            "data": {
                "current_ratio": round(current, 4),
                "change_5d_pct": round(chg_5d * 100, 2),
                "change_20d_pct": round(chg_20d * 100, 2),
            },
        }

    # ─────────────────────────────────────────────────────
    # 16. Session Momentum
    # ─────────────────────────────────────────────────────

    def _calc_session_momentum(self, md: dict) -> dict:
        """Agreement across Asian / London / NY sessions.

        When all three sessions move in the same direction, the signal
        is strong.  Mixed sessions = neutral.

        Expected keys:
            session_changes: dict with keys "asian", "london", "ny"
                each value: float (session % change)
        """
        sc = md.get("session_changes")
        if not isinstance(sc, dict):
            return self._neutral("No session-change data available")

        asian = sc.get("asian")
        london = sc.get("london")
        ny = sc.get("ny")

        available = {
            k: v for k, v in {"asian": asian, "london": london, "ny": ny}.items()
            if v is not None
        }

        if len(available) < 2:
            return self._neutral("Need at least 2 session changes for momentum")

        values = list(available.values())
        signs = [1 if v > 0 else (-1 if v < 0 else 0) for v in values]

        all_up = all(s > 0 for s in signs)
        all_down = all(s < 0 for s in signs)
        avg_change = sum(values) / len(values)

        if all_up:
            score = min(50.0, abs(avg_change) * 500)
            reason = (
                f"All sessions positive ({', '.join(f'{k} {v:+.2f}%' for k, v in available.items())})"
                f" — strong bullish agreement"
            )
        elif all_down:
            score = max(-50.0, -abs(avg_change) * 500)
            reason = (
                f"All sessions negative ({', '.join(f'{k} {v:+.2f}%' for k, v in available.items())})"
                f" — strong bearish agreement"
            )
        else:
            # Mixed — scale by average
            score = self._clamp(avg_change * 200, -25, 25)
            reason = (
                f"Mixed sessions ({', '.join(f'{k} {v:+.2f}%' for k, v in available.items())})"
                f" — no clear directional agreement"
            )

        return {
            "score": round(score, 1),
            "signal": self._label(score),
            "reasoning": reason,
            "data": {
                "sessions": {k: round(v, 3) for k, v in available.items()},
                "avg_change_pct": round(avg_change, 3),
                "unanimous": all_up or all_down,
            },
        }

    # ═════════════════════════════════════════════════════
    # Main prediction entry point
    # ═════════════════════════════════════════════════════

    async def predict(self, market_data: dict) -> dict:
        """Run all 16 indicators and produce a composite gold prediction.

        Parameters
        ----------
        market_data : dict
            Consolidated market data bundle.  Individual indicators
            document which keys they require; missing keys produce
            neutral (0) scores rather than errors.

        Returns
        -------
        dict
            composite_score : float  (-100 to +100)
            direction       : str    ("bullish" / "bearish" / "neutral")
            confidence      : float  (0-100 %)
            action          : str    (STRONG_BUY / BUY / LEAN_BULLISH /
                                      NEUTRAL / LEAN_BEARISH / SELL /
                                      STRONG_SELL)
            signal_breakdown : dict[str, dict]
            active_signals   : int
            bullish_signals  : int
            bearish_signals  : int
            agreement_ratio  : float (0-1)
            pred_1h_*  / pred_4h_* / pred_24h_* / pred_1w_* : price targets
        """
        if market_data is None:
            market_data = {}

        current_price = market_data.get("current_price")
        if current_price is None:
            closes = self._safe_array(market_data, "closes")
            if closes is not None and len(closes) > 0:
                current_price = float(closes[-1])
            else:
                current_price = 0.0

        # ── Run every indicator ───────────────────────────
        results: dict[str, dict] = {}
        for name, method_name in self._DISPATCH.items():
            try:
                method = getattr(self, method_name)
                results[name] = method(market_data)
            except Exception as exc:
                logger.warning("Indicator %s failed: %s", name, exc, exc_info=True)
                results[name] = self._neutral(f"Error: {exc}")

        # ── Composite score (weighted) ────────────────────
        weighted_sum = 0.0
        total_weight = 0.0

        for name, res in results.items():
            weight = self.INDICATORS.get(name, {}).get("weight", 0.02)
            score = res.get("score", 0.0)
            weighted_sum += weight * score
            total_weight += weight

        composite_score = (weighted_sum / total_weight) if total_weight > 0 else 0.0
        composite_score = self._clamp(composite_score, -100, 100)

        # ── Signal counts ─────────────────────────────────
        active_signals = 0
        bullish_signals = 0
        bearish_signals = 0

        for res in results.values():
            sig = res.get("signal", "neutral")
            if sig != "neutral":
                active_signals += 1
            if sig == "bullish":
                bullish_signals += 1
            elif sig == "bearish":
                bearish_signals += 1

        total_directional = bullish_signals + bearish_signals
        agreement_ratio = (
            max(bullish_signals, bearish_signals) / total_directional
            if total_directional > 0 else 0.0
        )

        # ── Direction / confidence ────────────────────────
        direction = self._label(composite_score, threshold=5)

        base_conf = min(abs(composite_score) / 100, 1.0)
        agreement_bonus = 0.12 if agreement_ratio > 0.75 else (-0.08 if agreement_ratio < 0.40 else 0.0)
        coverage_factor = min(active_signals / 16, 1.0)
        confidence = float(np.clip(
            base_conf * 0.60 + agreement_bonus + coverage_factor * 0.25 + 0.10,
            0.15,
            0.95,
        )) * 100

        # ── Action label ──────────────────────────────────
        if composite_score > 60:
            action = "STRONG_BUY"
        elif composite_score > 30:
            action = "BUY"
        elif composite_score > 10:
            action = "LEAN_BULLISH"
        elif composite_score > -10:
            action = "NEUTRAL"
        elif composite_score > -30:
            action = "LEAN_BEARISH"
        elif composite_score > -60:
            action = "SELL"
        else:
            action = "STRONG_SELL"

        # ── Price targets ─────────────────────────────────
        # Gold typical daily range ~$20-40 (~1-2% of ~$2000).
        # Use composite_score to scale expected move.
        timeframes = {
            "1h":  0.00003,   # composite_score * 0.003% of price
            "4h":  0.00008,   # composite_score * 0.008% of price
            "24h": 0.0002,    # composite_score * 0.02% of price
            "1w":  0.0005,    # composite_score * 0.05% of price
        }

        predictions = {}
        for tf, multiplier in timeframes.items():
            pct_change = composite_score * multiplier * 100  # as percentage
            pred_price = current_price * (1 + composite_score * multiplier) if current_price > 0 else 0.0
            predictions[tf] = {
                "direction": direction,
                "predicted_price": round(pred_price, 2),
                "predicted_change_pct": round(pct_change, 4),
                "confidence": round(confidence, 1),
            }

        # ── Signal breakdown ──────────────────────────────
        signal_breakdown = {}
        for name, res in results.items():
            meta = self.INDICATORS.get(name, {})
            signal_breakdown[name] = {
                "score": res.get("score", 0),
                "signal": res.get("signal", "neutral"),
                "reasoning": res.get("reasoning", ""),
                "data": res.get("data", {}),
                "weight": meta.get("weight", 0.02),
                "tier": meta.get("tier", 3),
            }

        return {
            "composite_score": round(float(composite_score), 1),
            "direction": direction,
            "confidence": round(float(confidence), 1),
            "action": action,
            "signal_breakdown": signal_breakdown,
            "active_signals": active_signals,
            "total_signals": len(results),
            "bullish_signals": bullish_signals,
            "bearish_signals": bearish_signals,
            "agreement_ratio": round(float(agreement_ratio), 2),
            "predictions": predictions,
            "pred_1h_price": predictions["1h"]["predicted_price"],
            "pred_1h_change_pct": predictions["1h"]["predicted_change_pct"],
            "pred_4h_price": predictions["4h"]["predicted_price"],
            "pred_4h_change_pct": predictions["4h"]["predicted_change_pct"],
            "pred_24h_price": predictions["24h"]["predicted_price"],
            "pred_24h_change_pct": predictions["24h"]["predicted_change_pct"],
            "pred_1w_price": predictions["1w"]["predicted_price"],
            "pred_1w_change_pct": predictions["1w"]["predicted_change_pct"],
            "current_price": current_price,
            "timestamp": datetime.utcnow().isoformat(),
        }


# ── Backward-compatible alias ─────────────────────────
# domain_ml.py imports `QuantPredictor`; keep that working during migration.
QuantPredictor = GoldQuantPredictor
