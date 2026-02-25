import logging
from datetime import datetime

import numpy as np
import pandas as pd

from app.features.technical import TechnicalFeatures
from app.features.sentiment import SentimentAnalyzer
from app.features.macro import MacroFeatures

logger = logging.getLogger(__name__)


class FeatureBuilder:
    """Combines all features into a unified feature vector for ML models."""

    # ═══════════════════════════════════════════════════════════
    #  FEATURE LISTS
    # ═══════════════════════════════════════════════════════════

    TECHNICAL_FEATURES = [
        # ── Original 30 (indices 0-29) ──
        "ema_9", "ema_21", "ema_50", "ema_200", "sma_20",
        "rsi", "macd", "macd_signal", "macd_hist",
        "bb_upper", "bb_lower", "bb_width", "bb_position",
        "atr", "obv", "vwap",
        "roc_1", "roc_6", "roc_12", "roc_24",
        "momentum_10", "momentum_20",
        "volume_ratio", "volatility_24h",
        "price_vs_ema9", "price_vs_ema21", "price_vs_ema50",
        "body_size", "upper_shadow", "lower_shadow",
        # ── Promoted already-computed indicators (27) ──
        "sma_111", "sma_200", "sma_350",
        "rsi_7", "rsi_30",
        "adx", "momentum_30", "mayer_multiple",
        "ema_cross", "zscore_20",
        "stoch_rsi_k", "stoch_rsi_d", "williams_r",
        "ichimoku_tenkan", "ichimoku_kijun",
        "ichimoku_senkou_a", "ichimoku_senkou_b", "ichimoku_chikou",
        "candle_doji", "candle_hammer", "candle_inverted_hammer",
        "candle_bullish_engulfing", "candle_bearish_engulfing",
        "candle_morning_star", "candle_evening_star",
        "trend_short", "trend_medium", "trend_long",
        # ── pandas-ta indicators (45) ──
        "ao", "cci_20", "cmo_14", "fisher_9", "fisher_signal",
        "kst", "kst_signal", "ppo", "ppo_signal", "ppo_hist",
        "stoch_k", "stoch_d", "tsi", "uo",
        "aroon_osc", "chop_14", "dpo_20", "supertrend_dir",
        "vortex_diff", "mass_index", "plus_di", "minus_di",
        "donchian_upper", "donchian_lower", "donchian_mid", "donchian_width",
        "kc_upper", "kc_lower", "kc_position", "natr", "ui",
        "ad", "cmf", "efi_13", "mfi", "nvi", "pvi",
        "entropy_10", "kurtosis_20", "skew_20", "variance_20",
        "zscore_14", "stdev_20", "linreg_slope", "linreg_r2",
        # ── Advanced quantitative indicators (36) ──
        # Adaptive MAs (3)
        "kama_10", "t3_10", "dema_21",
        # Additional momentum (4)
        "trix_14", "bop", "psar", "psar_dir",
        # Additional candlestick patterns (7)
        "candle_three_white", "candle_three_black", "candle_dark_cloud",
        "candle_piercing", "candle_harami", "candle_kicking", "candle_three_line_strike",
        # Price transforms (3)
        "typical_price", "weighted_close", "median_price",
        # Return-based statistics (6)
        "return_1h", "return_skew_24", "return_kurtosis_24",
        "return_autocorr_1", "return_autocorr_6", "return_autocorr_24",
        # Hurst exponent (1)
        "hurst_exponent",
        # GARCH volatility (2)
        "garch_vol_forecast", "vol_risk_premium",
        # Wavelet features (3)
        "wavelet_trend", "wavelet_detail_1", "wavelet_detail_2",
        # Calendar features (4)
        "hour_sin", "hour_cos", "day_of_week_sin", "day_of_week_cos",
        # Cross-feature interactions (3)
        "rsi_macd_divergence", "volume_price_trend", "atr_ratio_50_14",
    ]

    SENTIMENT_FEATURES = [
        "news_sentiment_1h", "news_sentiment_4h", "news_sentiment_24h",
        "news_volume_1h", "news_bullish_pct", "news_bearish_pct",
        "reddit_sentiment", "reddit_volume",
        "social_sentiment_1h", "social_volume_1h",
        "social_bullish_pct", "social_bearish_pct",
        "fear_greed_value",
    ]

    MACRO_FEATURES = [
        "dxy_change_1h", "dxy_change_24h",
        "gold_change_1h", "gold_change_24h",
        "sp500_change_1h", "sp500_change_24h",
        "treasury_10y", "treasury_change_1h",
    ]

    EVENT_MEMORY_FEATURES = [
        "event_expected_impact_1h",
        "event_expected_impact_4h",
        "event_expected_impact_24h",
        "event_memory_confidence",
        "event_severity",
        "event_sentiment_predictive",
        "active_event_count",
    ]

    PHRASE_FEATURES = [
        "top_bullish_phrase_score",
        "top_bearish_phrase_score",
        "phrase_sentiment_signal",
    ]

    # ── Gold-Specific Feature Categories ──

    GOLD_SESSION_FEATURES = [
        "session_asian_active",
        "session_london_active",
        "session_ny_active",
    ]

    GOLD_COT_FEATURES = [
        "cot_mm_net",
        "cot_mm_net_percentile",
        "cot_oi",
        "cot_oi_change",
    ]

    GOLD_YIELD_FEATURES = [
        "real_yield_10y",
        "tips_breakeven",
    ]

    GOLD_ETF_FEATURES = [
        "etf_total_volume",
        "etf_net_flow",
    ]

    GOLD_RATIO_FEATURES = [
        "gold_silver_ratio",
    ]

    LONG_TERM_FEATURES = [
        "sma_200d_ratio",
        "high_52w_distance",
        "low_52w_distance",
        "log_price_zscore_365d",
        "yearly_return_pct",
    ]

    ALL_FEATURES = (
        TECHNICAL_FEATURES + SENTIMENT_FEATURES + MACRO_FEATURES
        + EVENT_MEMORY_FEATURES + PHRASE_FEATURES
        + GOLD_SESSION_FEATURES + GOLD_COT_FEATURES
        + GOLD_YIELD_FEATURES + GOLD_ETF_FEATURES
        + GOLD_RATIO_FEATURES + LONG_TERM_FEATURES
    )

    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()

    def build_features(
        self,
        price_df: pd.DataFrame,
        news_data: list[dict] = None,
        reddit_data: list[dict] = None,
        influencer_data: list[dict] = None,
        macro_data: dict = None,
        fear_greed: dict = None,
        event_memory: dict = None,
        phrase_data: dict = None,
        # Gold-specific data sources
        market_data: dict = None,
    ) -> dict:
        """Build complete feature vector from all data sources."""

        features = {}
        if market_data is None:
            market_data = {}

        # Technical features from price data
        if price_df is not None and not price_df.empty:
            tech_df = TechnicalFeatures.calculate_all(price_df)
            latest = tech_df.iloc[-1]
            for feat in self.TECHNICAL_FEATURES:
                val = latest.get(feat)
                features[feat] = float(val) if val is not None and not pd.isna(val) else 0.0

            # Add current price info
            features["current_price"] = float(latest["close"])
            features["current_volume"] = float(latest["volume"])

        # Sentiment features (news + reddit + influencer social media)
        features.update(self._build_sentiment_features(news_data, reddit_data, influencer_data))

        # Macro features
        if macro_data:
            macro_feats = MacroFeatures.calculate_features(macro_data)
            for feat in self.MACRO_FEATURES:
                features[feat] = macro_feats.get(feat, 0.0) or 0.0

        # Fear & Greed
        if fear_greed:
            features["fear_greed_value"] = fear_greed.get("value", 50)

        # Event memory features
        if event_memory:
            features["event_expected_impact_1h"] = event_memory.get("expected_1h", 0.0)
            features["event_expected_impact_4h"] = event_memory.get("expected_4h", 0.0)
            features["event_expected_impact_24h"] = event_memory.get("expected_24h", 0.0)
            features["event_memory_confidence"] = event_memory.get("confidence", 0.0)
            features["event_severity"] = event_memory.get("severity", 0.0)
            features["event_sentiment_predictive"] = event_memory.get("avg_sentiment_predictive", 0.5)
            features["active_event_count"] = event_memory.get("active_event_count", 0.0)

        # Phrase correlation features
        if phrase_data:
            features["top_bullish_phrase_score"] = float(phrase_data.get("top_bullish_score", 0))
            features["top_bearish_phrase_score"] = float(phrase_data.get("top_bearish_score", 0))
            features["phrase_sentiment_signal"] = float(phrase_data.get("net_signal", 0))

        # ─── Gold-Specific Features ───────────────────────────────────
        # Session features
        if "session_info" in market_data:
            si = market_data["session_info"]
            features["session_asian_active"] = 1.0 if "asian" in si.get("active_sessions", []) else 0.0
            features["session_london_active"] = 1.0 if "london" in si.get("active_sessions", []) else 0.0
            features["session_ny_active"] = 1.0 if "new_york" in si.get("active_sessions", []) else 0.0

        # COT features
        if "cot" in market_data and market_data["cot"]:
            cot = market_data["cot"]
            features["cot_mm_net"] = float(cot.get("mm_net", 0))
            features["cot_mm_net_percentile"] = float(cot.get("mm_net_percentile", 50))
            features["cot_oi"] = float(cot.get("open_interest", 0))
            features["cot_oi_change"] = float(cot.get("oi_change", 0))

        # Real yield features
        if "fred" in market_data and market_data["fred"]:
            fred = market_data["fred"]
            ry = fred.get("real_yield_10y", {})
            features["real_yield_10y"] = float(ry.get("value", 0)) if isinstance(ry, dict) else float(ry or 0)
            tb = fred.get("tips_breakeven", {})
            features["tips_breakeven"] = float(tb.get("value", 0)) if isinstance(tb, dict) else float(tb or 0)

        # ETF flow features
        if "etf_flows" in market_data and market_data["etf_flows"]:
            total_volume = sum(e.get("volume", 0) or 0 for e in market_data["etf_flows"])
            features["etf_total_volume"] = float(total_volume)
            total_change = sum(e.get("daily_change", 0) or 0 for e in market_data["etf_flows"])
            features["etf_net_flow"] = float(total_change)

        # Gold/silver ratio
        if "macro" in market_data and market_data["macro"]:
            macro = market_data["macro"]
            gold_p = macro.get("gold", {})
            silver_p = macro.get("silver", {})
            gp = gold_p.get("price") if isinstance(gold_p, dict) else gold_p
            sp = silver_p.get("price") if isinstance(silver_p, dict) else silver_p
            if gp and sp and sp > 0:
                features["gold_silver_ratio"] = float(gp) / float(sp)

        # ── Long-term price features ──
        current_price = features.get("current_price", 0)
        if current_price > 0 and macro_data:
            # Price history-based features (set defaults, overridden by extended dataset)
            features.setdefault("sma_200d_ratio", 0)
            features.setdefault("high_52w_distance", 0)
            features.setdefault("low_52w_distance", 0)
            features.setdefault("log_price_zscore_365d", 0)
            features.setdefault("yearly_return_pct", 0)

        # Set defaults for any missing features
        for feat in self.ALL_FEATURES:
            features.setdefault(feat, 0.0)

        # Normalize features
        features = self._normalize(features)

        return features

    def _build_sentiment_features(
        self,
        news_data: list[dict] = None,
        reddit_data: list[dict] = None,
        influencer_data: list[dict] = None,
    ) -> dict:
        """Build sentiment features from news, reddit, and influencer social media.

        Uses time-windowed sentiment: filters news by timestamp for 1h/4h/24h windows
        so that each window reflects its actual time period.
        """
        from datetime import timedelta

        result = {feat: 0.0 for feat in self.SENTIMENT_FEATURES}
        now = datetime.utcnow()

        if news_data:
            # Separate news into time windows using timestamps
            def _filter_by_window(items, hours):
                cutoff = now - timedelta(hours=hours)
                filtered = []
                for n in items:
                    ts_str = n.get("timestamp")
                    if ts_str:
                        try:
                            ts = datetime.fromisoformat(ts_str)
                            if ts >= cutoff:
                                filtered.append(n)
                                continue
                        except (ValueError, TypeError):
                            pass
                    # No timestamp — include in all windows (backward compat)
                    filtered.append(n)
                return filtered

            # Window-specific title lists
            news_1h = _filter_by_window(news_data, 1)
            news_4h = _filter_by_window(news_data, 4)
            news_24h = news_data  # All news (already limited to ~50 recent)

            titles_1h = [n.get("title", "") for n in news_1h if n.get("title")]
            titles_4h = [n.get("title", "") for n in news_4h if n.get("title")]
            titles_24h = [n.get("title", "") for n in news_24h if n.get("title")]

            # 1h sentiment
            if titles_1h:
                agg_1h = self.sentiment_analyzer.get_aggregate_sentiment(titles_1h)
                result["news_sentiment_1h"] = agg_1h["mean_score"]
                result["news_volume_1h"] = float(agg_1h["volume"])
            # 4h sentiment
            if titles_4h:
                agg_4h = self.sentiment_analyzer.get_aggregate_sentiment(titles_4h)
                result["news_sentiment_4h"] = agg_4h["mean_score"]
            # 24h sentiment (use for bullish/bearish pct as it has most data)
            if titles_24h:
                agg_24h = self.sentiment_analyzer.get_aggregate_sentiment(titles_24h)
                result["news_sentiment_24h"] = agg_24h["mean_score"]
                result["news_bullish_pct"] = agg_24h["bullish_pct"]
                result["news_bearish_pct"] = agg_24h["bearish_pct"]

        if reddit_data:
            posts = reddit_data if isinstance(reddit_data, list) else reddit_data.get("posts", [])
            titles = [p.get("title", "") for p in posts if p.get("title")]

            if titles:
                agg = self.sentiment_analyzer.get_aggregate_sentiment(titles)
                result["reddit_sentiment"] = agg["mean_score"]
                result["reddit_volume"] = float(agg["volume"])

        if influencer_data:
            texts = [t.get("text", "") for t in influencer_data if t.get("text")]

            if texts:
                agg = self.sentiment_analyzer.get_aggregate_sentiment(texts)
                result["social_sentiment_1h"] = agg["mean_score"]
                result["social_volume_1h"] = float(agg["volume"])
                result["social_bullish_pct"] = agg["bullish_pct"]
                result["social_bearish_pct"] = agg["bearish_pct"]

        return result

    def _normalize(self, features: dict) -> dict:
        """Basic feature normalization."""
        normalized = {}
        for key, val in features.items():
            if val is None or (isinstance(val, float) and np.isnan(val)):
                normalized[key] = 0.0
            else:
                normalized[key] = float(val)
        return normalized

    def features_to_array(self, features: dict) -> np.ndarray:
        """Convert feature dict to ordered numpy array for ML input."""
        return np.array([features.get(f, 0.0) for f in self.ALL_FEATURES], dtype=np.float32)

    def build_sequence(self, feature_history: list[dict], lookback: int = 168) -> np.ndarray:
        """Build a sequence of feature vectors for LSTM input."""
        if len(feature_history) < lookback:
            padding = [
                {f: 0.0 for f in self.ALL_FEATURES}
                for _ in range(lookback - len(feature_history))
            ]
            feature_history = padding + feature_history

        recent = feature_history[-lookback:]
        matrix = np.array(
            [[entry.get(f, 0.0) for f in self.ALL_FEATURES] for entry in recent],
            dtype=np.float32,
        )
        return matrix
