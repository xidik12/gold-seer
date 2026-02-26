import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Text, Float, Integer, BigInteger, String, JSON, DateTime, Boolean, Index, UniqueConstraint, func, text, inspect
from sqlalchemy.sql import extract
from datetime import datetime

_db_logger = logging.getLogger(__name__)

from app.config import settings


def _create_engine():
    """Create async engine with dialect-appropriate settings."""
    url = settings.async_database_url
    if settings.is_postgres:
        _db_logger.info("Using PostgreSQL backend")
        return create_async_engine(
            url,
            echo=False,
            pool_size=20,
            max_overflow=40,
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_timeout=10,
            connect_args={"command_timeout": 30},
        )
    _db_logger.info("Using SQLite backend")
    return create_async_engine(url, echo=False)


engine = _create_engine()
async_session = async_sessionmaker(engine, expire_on_commit=False)


def timestamp_diff_order(column, target_time):
    """Return an ORDER BY expression for 'closest to target_time'.

    Uses EXTRACT(EPOCH ...) on PostgreSQL, julianday() on SQLite.
    """
    if settings.is_postgres:
        return func.abs(extract("epoch", column) - extract("epoch", target_time))
    return func.abs(func.julianday(column) - func.julianday(target_time))


class Base(DeclarativeBase):
    pass


class Price(Base):
    __tablename__ = "prices"
    __table_args__ = (
        UniqueConstraint("timestamp", name="uq_prices_timestamp"),
        Index("ix_prices_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(50), default="goldapi")


class News(Base):
    __tablename__ = "news"
    __table_args__ = (
        Index("ix_news_published_at", "timestamp"),
        Index("ix_news_asset_timestamp", "asset_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    source: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, nullable=True)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=True)
    raw_sentiment: Mapped[str] = mapped_column(String(20), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=True, default="en")
    asset_id: Mapped[str] = mapped_column(String(100), nullable=True, index=True)


class Feature(Base):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    feature_data: Mapped[dict] = mapped_column(JSON)


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        Index("ix_predictions_timestamp_timeframe", "timestamp", "timeframe"),
        Index("ix_predictions_timeframe_timestamp", "timeframe", "timestamp"),
        Index("ix_predictions_was_correct_timeframe", "was_correct", "timeframe"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    timeframe: Mapped[str] = mapped_column(String(10))  # 1h, 4h, 24h
    direction: Mapped[str] = mapped_column(String(20))  # bullish, bearish, neutral
    confidence: Mapped[float] = mapped_column(Float)
    predicted_price: Mapped[float] = mapped_column(Float, nullable=True)
    predicted_change_pct: Mapped[float] = mapped_column(Float, nullable=True)
    current_price: Mapped[float] = mapped_column(Float)
    actual_price: Mapped[float] = mapped_column(Float, nullable=True)
    actual_direction: Mapped[str] = mapped_column(String(20), nullable=True)
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=True)
    model_outputs: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Self-learning fields (auto-migrated)
    error_pct: Mapped[float] = mapped_column(Float, nullable=True)              # (actual - predicted) / predicted * 100
    volatility_regime: Mapped[str] = mapped_column(String(20), nullable=True)  # low, normal, high, extreme
    trend_state: Mapped[str] = mapped_column(String(20), nullable=True)        # trending_up, trending_down, ranging
    evaluation_notes: Mapped[dict] = mapped_column(JSON, nullable=True)        # analysis summary


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        Index("ix_signals_timestamp_timeframe", "timestamp", "timeframe"),
        Index("ix_signals_timeframe_timestamp", "timeframe", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    action: Mapped[str] = mapped_column(String(20))  # strong_buy, buy, hold, sell, strong_sell
    direction: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float] = mapped_column(Float)
    target_price: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    risk_rating: Mapped[int] = mapped_column(Integer)  # 1-10
    timeframe: Mapped[str] = mapped_column(String(10))
    reasoning: Mapped[str] = mapped_column(Text, nullable=True)


class MacroData(Base):
    __tablename__ = "macro_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    dxy: Mapped[float] = mapped_column(Float, nullable=True)
    gold: Mapped[float] = mapped_column(Float, nullable=True)
    sp500: Mapped[float] = mapped_column(Float, nullable=True)
    treasury_10y: Mapped[float] = mapped_column(Float, nullable=True)
    nasdaq: Mapped[float] = mapped_column(Float, nullable=True)
    vix: Mapped[float] = mapped_column(Float, nullable=True)
    eurusd: Mapped[float] = mapped_column(Float, nullable=True)
    fear_greed_index: Mapped[int] = mapped_column(Integer, nullable=True)
    fear_greed_label: Mapped[str] = mapped_column(String(30), nullable=True)
    m2_supply: Mapped[float] = mapped_column(Float, nullable=True)  # M2 money supply (trillions USD)
    # Forex pairs
    gbpusd: Mapped[float] = mapped_column(Float, nullable=True)
    usdjpy: Mapped[float] = mapped_column(Float, nullable=True)
    usdchf: Mapped[float] = mapped_column(Float, nullable=True)
    audusd: Mapped[float] = mapped_column(Float, nullable=True)
    usdcad: Mapped[float] = mapped_column(Float, nullable=True)
    nzdusd: Mapped[float] = mapped_column(Float, nullable=True)
    # Commodities
    wti_oil: Mapped[float] = mapped_column(Float, nullable=True)
    silver: Mapped[float] = mapped_column(Float, nullable=True)
    copper: Mapped[float] = mapped_column(Float, nullable=True)
    natural_gas: Mapped[float] = mapped_column(Float, nullable=True)
    platinum: Mapped[float] = mapped_column(Float, nullable=True)
    palladium: Mapped[float] = mapped_column(Float, nullable=True)
    # Indices
    dow_jones: Mapped[float] = mapped_column(Float, nullable=True)
    russell_2000: Mapped[float] = mapped_column(Float, nullable=True)
    dax: Mapped[float] = mapped_column(Float, nullable=True)
    nikkei_225: Mapped[float] = mapped_column(Float, nullable=True)
    ftse_100: Mapped[float] = mapped_column(Float, nullable=True)
    # Treasury yields
    treasury_2y: Mapped[float] = mapped_column(Float, nullable=True)
    treasury_5y: Mapped[float] = mapped_column(Float, nullable=True)
    treasury_30y: Mapped[float] = mapped_column(Float, nullable=True)
    # Gold-specific macro
    real_yield_10y: Mapped[float] = mapped_column(Float, nullable=True)  # DFII10
    tips_breakeven: Mapped[float] = mapped_column(Float, nullable=True)  # T10YIE
    real_yield_5y: Mapped[float] = mapped_column(Float, nullable=True)
    cpi_yoy: Mapped[float] = mapped_column(Float, nullable=True)
    pce_yoy: Mapped[float] = mapped_column(Float, nullable=True)
    fed_funds_rate: Mapped[float] = mapped_column(Float, nullable=True)
    m2_yoy_change: Mapped[float] = mapped_column(Float, nullable=True)
    gold_silver_ratio: Mapped[float] = mapped_column(Float, nullable=True)
    # Gold mining/ETF equities
    gdx: Mapped[float] = mapped_column(Float, nullable=True)  # VanEck Gold Miners ETF
    gld: Mapped[float] = mapped_column(Float, nullable=True)  # SPDR Gold Shares ETF


class EventImpact(Base):
    """Tracks how specific news events impacted gold price historically.

    This is the system's 'memory' -- it remembers what happened after similar events
    and uses that knowledge to improve predictions.
    """
    __tablename__ = "event_impacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    news_id: Mapped[int] = mapped_column(Integer, nullable=True)  # FK to news table
    title: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(100))

    # Event classification
    category: Mapped[str] = mapped_column(String(50), index=True)  # war, politics, regulation, etc.
    subcategory: Mapped[str] = mapped_column(String(50), nullable=True)
    keywords: Mapped[str] = mapped_column(Text, nullable=True)  # comma-separated matched keywords
    severity: Mapped[int] = mapped_column(Integer, default=5)  # 1-10

    # Sentiment at time of event
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=True)

    # Gold price at time of event
    price_at_event: Mapped[float] = mapped_column(Float)

    # Measured price impacts (filled in over time by evaluator)
    price_1h: Mapped[float] = mapped_column(Float, nullable=True)
    price_4h: Mapped[float] = mapped_column(Float, nullable=True)
    price_24h: Mapped[float] = mapped_column(Float, nullable=True)
    price_7d: Mapped[float] = mapped_column(Float, nullable=True)

    change_pct_1h: Mapped[float] = mapped_column(Float, nullable=True)
    change_pct_4h: Mapped[float] = mapped_column(Float, nullable=True)
    change_pct_24h: Mapped[float] = mapped_column(Float, nullable=True)
    change_pct_7d: Mapped[float] = mapped_column(Float, nullable=True)

    # Was the sentiment predictive of the direction?
    sentiment_was_predictive: Mapped[bool] = mapped_column(Boolean, nullable=True)

    # Evaluation status
    evaluated_1h: Mapped[bool] = mapped_column(Boolean, default=False)
    evaluated_4h: Mapped[bool] = mapped_column(Boolean, default=False)
    evaluated_24h: Mapped[bool] = mapped_column(Boolean, default=False)
    evaluated_7d: Mapped[bool] = mapped_column(Boolean, default=False)

    # Prediction attribution -- which prediction was active when this event occurred
    prediction_id: Mapped[int] = mapped_column(Integer, nullable=True)
    prediction_was_correct: Mapped[bool] = mapped_column(Boolean, nullable=True)

    # Category-level learning
    category_accuracy: Mapped[float] = mapped_column(Float, nullable=True)  # rolling accuracy for this category


class EventCausalChain(Base):
    """Causal reasoning log: event -> mechanism -> prediction -> outcome -> lesson.

    This is the system's 'thinking' record -- it logs WHY an event should move gold,
    what the prediction was, what actually happened, and what was learned.
    """
    __tablename__ = "event_causal_chains"
    __table_args__ = (
        Index("ix_ecc_category_ts", "category", "timestamp"),
        Index("ix_ecc_event_impact_id", "event_impact_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())

    # Link to event and prediction
    event_impact_id: Mapped[int] = mapped_column(Integer, index=True)
    prediction_id: Mapped[int] = mapped_column(Integer, nullable=True)

    # Event context
    category: Mapped[str] = mapped_column(String(50), index=True)
    subcategory: Mapped[str] = mapped_column(String(50), nullable=True)
    severity: Mapped[int] = mapped_column(Integer, default=5)
    event_title: Mapped[str] = mapped_column(Text)

    # Causal reasoning
    mechanism: Mapped[str] = mapped_column(Text)  # "War escalation -> risk-off -> gold rallies as safe haven"
    expected_direction: Mapped[str] = mapped_column(String(20))  # bullish / bearish / neutral
    expected_magnitude_pct: Mapped[float] = mapped_column(Float, nullable=True)  # predicted % move

    # What actually happened
    actual_direction: Mapped[str] = mapped_column(String(20), nullable=True)
    actual_change_1h: Mapped[float] = mapped_column(Float, nullable=True)
    actual_change_4h: Mapped[float] = mapped_column(Float, nullable=True)
    actual_change_24h: Mapped[float] = mapped_column(Float, nullable=True)

    # Assessment
    direction_correct: Mapped[bool] = mapped_column(Boolean, nullable=True)
    magnitude_error_pct: Mapped[float] = mapped_column(Float, nullable=True)
    lesson: Mapped[str] = mapped_column(Text, nullable=True)  # "War events with severity >7 cause larger gold rallies than expected"

    # Pattern strength (how many similar events confirm this pattern)
    similar_event_count: Mapped[int] = mapped_column(Integer, default=0)
    pattern_accuracy: Mapped[float] = mapped_column(Float, nullable=True)  # accuracy of predictions for this category+severity


class EventCategoryStats(Base):
    """Rolling statistics per event category -- the system's learned knowledge about each event type."""
    __tablename__ = "event_category_stats"
    __table_args__ = (
        UniqueConstraint("category", "timeframe", name="uq_event_cat_tf"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(50), index=True)
    timeframe: Mapped[str] = mapped_column(String(10), default="1h")  # 1h, 4h, 24h, 7d
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Impact statistics
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_impact_pct: Mapped[float] = mapped_column(Float, default=0.0)
    median_impact_pct: Mapped[float] = mapped_column(Float, default=0.0)
    std_impact_pct: Mapped[float] = mapped_column(Float, default=0.0)
    max_positive_pct: Mapped[float] = mapped_column(Float, default=0.0)
    max_negative_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Directional consistency
    bullish_ratio: Mapped[float] = mapped_column(Float, default=0.5)  # % of events that were bullish
    predictive_power: Mapped[float] = mapped_column(Float, default=0.0)  # 0=random, 1=perfectly predictable

    # Severity-weighted stats
    high_severity_avg: Mapped[float] = mapped_column(Float, nullable=True)  # avg impact for severity >= 7
    low_severity_avg: Mapped[float] = mapped_column(Float, nullable=True)   # avg impact for severity <= 4

    # Sentiment prediction accuracy for this category
    sentiment_predictive_ratio: Mapped[float] = mapped_column(Float, default=0.5)


class QuantPrediction(Base):
    """Quant Theory-based predictions (separate from ML ensemble)."""
    __tablename__ = "quant_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    current_price: Mapped[float] = mapped_column(Float)
    composite_score: Mapped[float] = mapped_column(Float)  # -100 to +100
    action: Mapped[str] = mapped_column(String(20))  # STRONG_BUY, BUY, LEAN_BULLISH, etc.
    direction: Mapped[str] = mapped_column(String(20))  # bullish / bearish
    confidence: Mapped[float] = mapped_column(Float)

    # Per-timeframe predictions
    pred_1h_price: Mapped[float] = mapped_column(Float, nullable=True)
    pred_1h_change_pct: Mapped[float] = mapped_column(Float, nullable=True)
    pred_4h_price: Mapped[float] = mapped_column(Float, nullable=True)
    pred_4h_change_pct: Mapped[float] = mapped_column(Float, nullable=True)
    pred_24h_price: Mapped[float] = mapped_column(Float, nullable=True)
    pred_24h_change_pct: Mapped[float] = mapped_column(Float, nullable=True)

    # Signal counts
    active_signals: Mapped[int] = mapped_column(Integer, nullable=True)
    bullish_signals: Mapped[int] = mapped_column(Integer, nullable=True)
    bearish_signals: Mapped[int] = mapped_column(Integer, nullable=True)
    agreement_ratio: Mapped[float] = mapped_column(Float, nullable=True)

    # Full breakdown stored as JSON
    signal_breakdown: Mapped[dict] = mapped_column(JSON, nullable=True)

    # 1-week and 1-month predictions
    pred_1w_price: Mapped[float] = mapped_column(Float, nullable=True)
    pred_1w_change_pct: Mapped[float] = mapped_column(Float, nullable=True)
    pred_1mo_price: Mapped[float] = mapped_column(Float, nullable=True)
    pred_1mo_change_pct: Mapped[float] = mapped_column(Float, nullable=True)

    # Evaluation (filled later)
    actual_price_1h: Mapped[float] = mapped_column(Float, nullable=True)
    actual_price_24h: Mapped[float] = mapped_column(Float, nullable=True)
    actual_price_1w: Mapped[float] = mapped_column(Float, nullable=True)
    actual_price_1mo: Mapped[float] = mapped_column(Float, nullable=True)
    was_correct_1h: Mapped[bool] = mapped_column(Boolean, nullable=True)
    was_correct_24h: Mapped[bool] = mapped_column(Boolean, nullable=True)
    was_correct_1w: Mapped[bool] = mapped_column(Boolean, nullable=True)
    was_correct_1mo: Mapped[bool] = mapped_column(Boolean, nullable=True)


class IndicatorSnapshot(Base):
    """Hourly snapshot of all computed technical indicators."""
    __tablename__ = "indicator_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    price: Mapped[float] = mapped_column(Float)
    indicators: Mapped[dict] = mapped_column(JSON)  # Full indicator dict


class AlertLog(Base):
    """Logs every alert sent to users for audit and debugging."""
    __tablename__ = "alert_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    alert_type: Mapped[str] = mapped_column(String(30))  # hourly, breaking
    status: Mapped[str] = mapped_column(String(20))  # sent, failed
    error: Mapped[str] = mapped_column(Text, nullable=True)


class ModelVersion(Base):
    """Tracks trained model versions, training metrics, and weights paths."""
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    model_type: Mapped[str] = mapped_column(String(30))  # tft, lstm, xgboost
    version: Mapped[int] = mapped_column(Integer)

    # Training metrics
    train_accuracy: Mapped[float] = mapped_column(Float, nullable=True)
    val_accuracy: Mapped[float] = mapped_column(Float, nullable=True)
    test_accuracy: Mapped[float] = mapped_column(Float, nullable=True)
    train_loss: Mapped[float] = mapped_column(Float, nullable=True)

    # Dataset info
    train_samples: Mapped[int] = mapped_column(Integer, nullable=True)
    feature_count: Mapped[int] = mapped_column(Integer, nullable=True)

    # Weights path
    weights_path: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    # Post-deployment accuracy (updated after running in prod)
    live_accuracy_1h: Mapped[float] = mapped_column(Float, nullable=True)
    live_accuracy_24h: Mapped[float] = mapped_column(Float, nullable=True)

    # A/B testing fields
    is_candidate: Mapped[bool] = mapped_column(Boolean, default=False)
    ab_test_accuracy: Mapped[float] = mapped_column(Float, nullable=True)
    ensemble_weight: Mapped[float] = mapped_column(Float, nullable=True)


class BotUser(Base):
    __tablename__ = "bot_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    subscribed: Mapped[bool] = mapped_column(Boolean, default=False)
    alert_interval: Mapped[str] = mapped_column(String(10), default="4h")  # 1h, 4h, 24h
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Subscription fields
    subscription_tier: Mapped[str] = mapped_column(String(20), nullable=True, default="free")
    trial_end: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    subscription_end: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    stars_payment_id: Mapped[str] = mapped_column(String(200), nullable=True)

    # Referral system
    referral_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=True, index=True)
    referred_by: Mapped[int] = mapped_column(BigInteger, nullable=True)
    referral_count: Mapped[int] = mapped_column(Integer, default=0)

    # Partner referral
    partner_code: Mapped[str] = mapped_column(String(50), nullable=True)

    # Activity tracking
    last_active: Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)

    # Admin / ban
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_reason: Mapped[str] = mapped_column(String(500), nullable=True)


class PaymentHistory(Base):
    """Logs every Telegram Stars payment for subscription tracking."""
    __tablename__ = "payment_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    tier: Mapped[str] = mapped_column(String(20))  # monthly, quarterly, yearly
    days: Mapped[int] = mapped_column(Integer)
    stars_amount: Mapped[int] = mapped_column(Integer)
    payment_id: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Referral(Base):
    """Tracks referral relationships and bonus grants."""
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referrer_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    referee_telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    referrer_bonus_days: Mapped[int] = mapped_column(Integer, default=7)
    referee_bonus_days: Mapped[int] = mapped_column(Integer, default=7)


class PortfolioState(Base):
    """Tracks user portfolio balance, risk settings, and trading stats."""
    __tablename__ = "portfolio_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Balance
    balance_usdt: Mapped[float] = mapped_column(Float, default=10.0)
    initial_balance: Mapped[float] = mapped_column(Float, default=10.0)
    total_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    total_pnl_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Risk settings
    max_risk_per_trade_pct: Mapped[float] = mapped_column(Float, default=10.0)
    max_leverage: Mapped[int] = mapped_column(Integer, default=20)
    max_open_trades: Mapped[int] = mapped_column(Integer, default=2)
    daily_max_loss_pct: Mapped[float] = mapped_column(Float, default=30.0)

    # Stats
    consecutive_losses: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_wins: Mapped[int] = mapped_column(Integer, default=0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)

    # Daily loss tracking & cooldown
    daily_loss_today: Mapped[float] = mapped_column(Float, default=0.0)
    daily_loss_date: Mapped[str] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    cooldown_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Broker integration
    balance_usd: Mapped[float] = mapped_column(Float, nullable=True)
    default_lot_size: Mapped[float] = mapped_column(Float, nullable=True, default=0.01)
    max_lot_size: Mapped[float] = mapped_column(Float, nullable=True, default=1.0)
    broker_account_id: Mapped[str] = mapped_column(String(100), nullable=True)


class TradeAdvice(Base):
    """A complete trade plan generated by the advisor."""
    __tablename__ = "trade_advices"
    __table_args__ = (
        Index("ix_trade_advices_telegram_status", "telegram_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())

    # Plan
    direction: Mapped[str] = mapped_column(String(10))  # LONG / SHORT
    entry_price: Mapped[float] = mapped_column(Float)
    entry_zone_low: Mapped[float] = mapped_column(Float, nullable=True)
    entry_zone_high: Mapped[float] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[float] = mapped_column(Float)
    take_profit_1: Mapped[float] = mapped_column(Float)
    take_profit_2: Mapped[float] = mapped_column(Float, nullable=True)
    take_profit_3: Mapped[float] = mapped_column(Float, nullable=True)

    # Sizing
    leverage: Mapped[int] = mapped_column(Integer)
    position_size_usdt: Mapped[float] = mapped_column(Float)
    position_size_pct: Mapped[float] = mapped_column(Float)
    risk_amount_usdt: Mapped[float] = mapped_column(Float)

    # Metrics
    risk_reward_ratio: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    risk_rating: Mapped[int] = mapped_column(Integer, nullable=True)

    # Context
    reasoning: Mapped[str] = mapped_column(Text, nullable=True)
    models_agreeing: Mapped[str] = mapped_column(Text, nullable=True)
    urgency: Mapped[str] = mapped_column(String(30), default="enter_now")  # enter_now, limit_order, wait_for_pullback
    timeframe: Mapped[str] = mapped_column(String(10), default="1h")

    # References
    prediction_id: Mapped[int] = mapped_column(Integer, nullable=True)
    signal_id: Mapped[int] = mapped_column(Integer, nullable=True)
    quant_prediction_id: Mapped[int] = mapped_column(Integer, nullable=True)

    # Lifecycle
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, opened, partial_tp, closed, cancelled, expired
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    close_reason: Mapped[str] = mapped_column(String(50), nullable=True)

    # Mock/Paper trading flag
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)

    # Alert flags
    breakeven_alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    partial_tp_alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    close_alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    # Broker execution
    broker_trade_id: Mapped[str] = mapped_column(String(100), nullable=True)
    lot_size: Mapped[float] = mapped_column(Float, nullable=True)
    pip_value: Mapped[float] = mapped_column(Float, nullable=True)
    execution_mode: Mapped[str] = mapped_column(String(20), nullable=True)  # manual_approve, semi_auto, fully_auto


class TradeResult(Base):
    """Final result of a completed trade."""
    __tablename__ = "trade_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_advice_id: Mapped[int] = mapped_column(Integer, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    direction: Mapped[str] = mapped_column(String(10))
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float] = mapped_column(Float)
    leverage: Mapped[int] = mapped_column(Integer)
    position_size_usdt: Mapped[float] = mapped_column(Float)

    pnl_usdt: Mapped[float] = mapped_column(Float)
    pnl_pct: Mapped[float] = mapped_column(Float)
    pnl_pct_leveraged: Mapped[float] = mapped_column(Float)
    was_winner: Mapped[bool] = mapped_column(Boolean)

    close_reason: Mapped[str] = mapped_column(String(50), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=True)
    balance_before: Mapped[float] = mapped_column(Float, nullable=True)
    balance_after: Mapped[float] = mapped_column(Float, nullable=True)


class PredictionContext(Base):
    """Full snapshot of features, news, macro at each prediction for exact replay."""
    __tablename__ = "prediction_contexts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    prediction_id: Mapped[int] = mapped_column(Integer, nullable=True)
    current_price: Mapped[float] = mapped_column(Float)
    features: Mapped[dict] = mapped_column(JSON, nullable=True)
    news_headlines: Mapped[dict] = mapped_column(JSON, nullable=True)
    analyst_forecast_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)
    macro_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)
    cot_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)
    etf_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)
    session_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)
    event_memory: Mapped[dict] = mapped_column(JSON, nullable=True)
    model_outputs: Mapped[dict] = mapped_column(JSON, nullable=True)


class NewsPriceCorrelation(Base):
    """Word/phrase-level tracking of headline correlations with price moves."""
    __tablename__ = "news_price_correlations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phrase: Mapped[str] = mapped_column(String(200), index=True)
    phrase_type: Mapped[str] = mapped_column(String(20))  # word, bigram, trigram
    occurrences: Mapped[int] = mapped_column(Integer, default=0)
    avg_change_1h: Mapped[float] = mapped_column(Float, default=0.0)
    avg_change_4h: Mapped[float] = mapped_column(Float, default=0.0)
    avg_change_24h: Mapped[float] = mapped_column(Float, default=0.0)
    bullish_ratio: Mapped[float] = mapped_column(Float, default=0.5)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    correlation_score: Mapped[float] = mapped_column(Float, default=0.0)


class ModelPerformanceLog(Base):
    """Per-model accuracy tracking per prediction."""
    __tablename__ = "model_performance_logs"
    __table_args__ = (
        Index("ix_model_perf_model_timeframe", "model_name", "timeframe"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    prediction_id: Mapped[int] = mapped_column(Integer, index=True)
    model_name: Mapped[str] = mapped_column(String(30), index=True)  # tft, lstm, xgboost, timesfm, ensemble
    timeframe: Mapped[str] = mapped_column(String(10))
    predicted_direction: Mapped[str] = mapped_column(String(20))
    predicted_prob: Mapped[float] = mapped_column(Float, nullable=True)
    actual_direction: Mapped[str] = mapped_column(String(20), nullable=True)
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=True)


class FeatureImportanceLog(Base):
    """Which features matter most, tracked over time."""
    __tablename__ = "feature_importance_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    model_type: Mapped[str] = mapped_column(String(30))
    feature_importances: Mapped[dict] = mapped_column(JSON)
    top_features: Mapped[dict] = mapped_column(JSON, nullable=True)


class ModelFeedback(Base):
    """Aggregated feedback from mock trade outcomes vs AI predictions."""
    __tablename__ = "model_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    period: Mapped[str] = mapped_column(String(20), default="daily")  # daily, weekly
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    direction_accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    avg_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    avg_predicted_rr: Mapped[float] = mapped_column(Float, default=0.0)
    avg_achieved_rr: Mapped[float] = mapped_column(Float, default=0.0)
    avg_pnl_pct: Mapped[float] = mapped_column(Float, default=0.0)
    feedback_json: Mapped[dict] = mapped_column(JSON, nullable=True)


class ApiKey(Base):
    """API keys for monetization."""
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(20))  # Prefix for identification
    owner: Mapped[str] = mapped_column(String(200))
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=True, index=True)
    tier: Mapped[str] = mapped_column(String(20), default="free")  # free, basic, pro, enterprise
    rate_limit: Mapped[int] = mapped_column(Integer, default=60)  # requests per hour
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class ApiUsageLog(Base):
    """Per-request API usage logging."""
    __tablename__ = "api_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    api_key_id: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    endpoint: Mapped[str] = mapped_column(String(200))
    method: Mapped[str] = mapped_column(String(10))
    status_code: Mapped[int] = mapped_column(Integer)
    response_time_ms: Mapped[float] = mapped_column(Float, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    tier: Mapped[str] = mapped_column(String(20), nullable=True)


class PredictionAnalysis(Base):
    """Detailed post-mortem for each evaluated prediction."""
    __tablename__ = "prediction_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    prediction_id: Mapped[int] = mapped_column(Integer, index=True)
    timeframe: Mapped[str] = mapped_column(String(10))

    # Error metrics
    error_pct: Mapped[float] = mapped_column(Float, nullable=True)
    abs_error_pct: Mapped[float] = mapped_column(Float, nullable=True)
    direction_correct: Mapped[bool] = mapped_column(Boolean, nullable=True)

    # Per-model breakdown
    per_model_results: Mapped[dict] = mapped_column(JSON, nullable=True)  # {model: {predicted, correct, prob}}

    # Market regime at prediction time
    volatility_regime: Mapped[str] = mapped_column(String(20), nullable=True)  # low, normal, high, extreme
    trend_state: Mapped[str] = mapped_column(String(20), nullable=True)        # trending_up, trending_down, ranging
    rsi_at_prediction: Mapped[float] = mapped_column(Float, nullable=True)

    # Feature analysis
    top_features: Mapped[dict] = mapped_column(JSON, nullable=True)  # most influential features

    # Model agreement
    model_agreement_score: Mapped[float] = mapped_column(Float, nullable=True)  # 0-1
    dissenting_models: Mapped[str] = mapped_column(Text, nullable=True)  # comma-separated


class SupportTicket(Base):
    """User bug reports and questions."""
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="general")  # bug, question, feature, billing, general
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open, in_progress, resolved, closed
    priority: Mapped[str] = mapped_column(String(20), default="normal")  # low, normal, high, urgent
    admin_notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class UserFeedback(Base):
    """Thumbs up/down on trades and predictions."""
    __tablename__ = "user_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    feedback_type: Mapped[str] = mapped_column(String(30))  # trade, prediction, signal, general
    reference_id: Mapped[int] = mapped_column(Integer, nullable=True)  # trade_id, prediction_id, etc.
    is_positive: Mapped[bool] = mapped_column(Boolean)
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())


class MarketingMetrics(Base):
    """Daily snapshot of all business KPIs."""
    __tablename__ = "marketing_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), unique=True, index=True)  # YYYY-MM-DD
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Users
    total_users: Mapped[int] = mapped_column(Integer, default=0)
    premium_users: Mapped[int] = mapped_column(Integer, default=0)
    trial_users: Mapped[int] = mapped_column(Integer, default=0)
    new_users_today: Mapped[int] = mapped_column(Integer, default=0)
    active_users_24h: Mapped[int] = mapped_column(Integer, default=0)

    # Revenue
    stars_revenue_today: Mapped[int] = mapped_column(Integer, default=0)
    trial_conversions_today: Mapped[int] = mapped_column(Integer, default=0)

    # Predictions
    predictions_made: Mapped[int] = mapped_column(Integer, default=0)
    predictions_correct: Mapped[int] = mapped_column(Integer, default=0)
    accuracy_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Signals
    signals_generated: Mapped[int] = mapped_column(Integer, default=0)
    signals_profitable: Mapped[int] = mapped_column(Integer, default=0)

    # Support
    tickets_opened: Mapped[int] = mapped_column(Integer, default=0)
    tickets_resolved: Mapped[int] = mapped_column(Integer, default=0)

    # Referrals
    referrals_today: Mapped[int] = mapped_column(Integer, default=0)
    total_referrals: Mapped[int] = mapped_column(Integer, default=0)

    # System
    api_requests: Mapped[int] = mapped_column(Integer, default=0)
    api_errors: Mapped[int] = mapped_column(Integer, default=0)


class GeneratedImage(Base):
    """PNG cache to avoid regenerating charts every request."""
    __tablename__ = "generated_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chart_type: Mapped[str] = mapped_column(String(50), index=True)  # prediction_card, price_chart, etc.
    params_hash: Mapped[str] = mapped_column(String(64), index=True)  # hash of generation params
    image_data: Mapped[bytes] = mapped_column(Text, nullable=True)  # base64 or path
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class Partner(Base):
    """Partner referral accounts for commission-based partnerships."""
    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    contact_email: Mapped[str] = mapped_column(String(200), nullable=True)
    contact_telegram: Mapped[str] = mapped_column(String(100), nullable=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=True, unique=True, index=True)
    commission_pct: Mapped[float] = mapped_column(Float, default=20.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    created_by: Mapped[int] = mapped_column(BigInteger, default=0)
    notes: Mapped[str] = mapped_column(Text, nullable=True)


class PartnerReferral(Base):
    """Tracks users referred by partners and their conversion/commission status."""
    __tablename__ = "partner_referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    partner_id: Mapped[int] = mapped_column(Integer, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    signed_up_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    subscribed: Mapped[bool] = mapped_column(Boolean, default=False)
    subscription_tier: Mapped[str] = mapped_column(String(20), nullable=True)
    subscription_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    stars_paid: Mapped[int] = mapped_column(Integer, nullable=True)
    commission_amount: Mapped[float] = mapped_column(Float, nullable=True)
    commission_paid: Mapped[bool] = mapped_column(Boolean, default=False)


class LearnedPattern(Base):
    """Patterns discovered from error analysis for self-learning."""
    __tablename__ = "learned_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Pattern definition
    pattern_type: Mapped[str] = mapped_column(String(50), index=True)  # model_disagreement, volatility_regime, feature_threshold, confidence_calibration, time_pattern
    timeframe: Mapped[str] = mapped_column(String(10), nullable=True)
    description: Mapped[str] = mapped_column(Text)

    # Machine-readable conditions
    conditions: Mapped[dict] = mapped_column(JSON)  # e.g. {"rsi_gt": 75, "direction": "bullish"}

    # Statistics
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    accuracy_when_pattern: Mapped[float] = mapped_column(Float, nullable=True)  # accuracy when pattern is active
    accuracy_when_not_pattern: Mapped[float] = mapped_column(Float, nullable=True)

    # Adjustments to apply
    confidence_modifier: Mapped[float] = mapped_column(Float, default=1.0)  # < 1.0 = reduce confidence
    direction_bias: Mapped[float] = mapped_column(Float, default=0.0)  # adjustment to bullish_prob

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PriceAlert(Base):
    """User-defined price alerts for XAUUSD."""
    __tablename__ = "price_alerts"
    __table_args__ = (
        Index("ix_price_alerts_user_active", "telegram_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    asset_id: Mapped[str] = mapped_column(String(100), default="xauusd")
    target_price: Mapped[float] = mapped_column(Float)
    direction: Mapped[str] = mapped_column(String(10))  # above, below
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_repeating: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    triggered_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    triggered_price: Mapped[float] = mapped_column(Float, nullable=True)


class DailyBriefing(Base):
    """AI-generated daily market briefing."""
    __tablename__ = "daily_briefings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), unique=True, index=True)  # YYYY-MM-DD
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    summary_html: Mapped[str] = mapped_column(Text)
    summary_text: Mapped[str] = mapped_column(Text)
    data_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)
    gold_price: Mapped[float] = mapped_column(Float, nullable=True)
    gold_24h_change: Mapped[float] = mapped_column(Float, nullable=True)
    overall_sentiment: Mapped[str] = mapped_column(String(20), nullable=True)  # bullish, bearish, neutral
    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    generation_method: Mapped[str] = mapped_column(String(30), default="template")
    session_summary: Mapped[str] = mapped_column(Text, nullable=True)
    cot_summary: Mapped[str] = mapped_column(Text, nullable=True)


class UserPrediction(Base):
    """User predictions for the prediction game."""
    __tablename__ = "user_predictions"
    __table_args__ = (
        UniqueConstraint("telegram_id", "round_date", "timeframe", name="uq_user_prediction_round"),
        Index("ix_user_pred_user_ts", "telegram_id", "timestamp"),
        Index("ix_user_pred_round", "round_date", "timeframe"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    round_date: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD
    timeframe: Mapped[str] = mapped_column(String(10), default="24h")  # 24h, 4h, 1h
    direction: Mapped[str] = mapped_column(String(10))  # up, down
    lock_price: Mapped[float] = mapped_column(Float)
    resolve_price: Mapped[float] = mapped_column(Float, nullable=True)
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=True)
    points_earned: Mapped[int] = mapped_column(Integer, nullable=True)
    streak_at_prediction: Mapped[int] = mapped_column(Integer, default=0)
    multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, resolved


class GameProfile(Base):
    """Leaderboard profile for the prediction game."""
    __tablename__ = "game_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    total_predictions: Mapped[int] = mapped_column(Integer, default=0)
    correct_predictions: Mapped[int] = mapped_column(Integer, default=0)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    best_streak: Mapped[int] = mapped_column(Integer, default=0)
    accuracy_pct: Mapped[float] = mapped_column(Float, default=0.0)
    weekly_points: Mapped[int] = mapped_column(Integer, default=0)
    monthly_points: Mapped[int] = mapped_column(Integer, default=0)
    weekly_reset_date: Mapped[str] = mapped_column(String(10), nullable=True)
    monthly_reset_date: Mapped[str] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class EconomicEvent(Base):
    __tablename__ = "economic_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    event_name: Mapped[str] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(5), default="US")
    importance: Mapped[str] = mapped_column(String(10), default="medium")  # low/medium/high
    actual: Mapped[str] = mapped_column(String(50), nullable=True)
    forecast: Mapped[str] = mapped_column(String(50), nullable=True)
    previous: Mapped[str] = mapped_column(String(50), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="scheduled")


# ──────────────────────────────────────────────────────────────
#  Gold-specific tables (Griffin Gold)
# ──────────────────────────────────────────────────────────────

class GoldSessionData(Base):
    """Per-session OHLCV data (Asian/London/NY)."""
    __tablename__ = "gold_session_data"
    __table_args__ = (
        Index("ix_gold_session_date_session", "date", "session_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD
    session_name: Mapped[str] = mapped_column(String(20))  # asian, london, new_york
    open_price: Mapped[float] = mapped_column(Float)
    high_price: Mapped[float] = mapped_column(Float)
    low_price: Mapped[float] = mapped_column(Float)
    close_price: Mapped[float] = mapped_column(Float, nullable=True)
    volume: Mapped[float] = mapped_column(Float, nullable=True)
    range_usd: Mapped[float] = mapped_column(Float, nullable=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=True)  # up, down, flat
    session_start: Mapped[datetime] = mapped_column(DateTime)
    session_end: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)


class COTData(Base):
    """Weekly CFTC Commitments of Traders data for gold (COMEX)."""
    __tablename__ = "cot_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_date: Mapped[datetime] = mapped_column(DateTime, unique=True, index=True)
    # Managed money (hedge funds)
    mm_long: Mapped[int] = mapped_column(Integer, nullable=True)
    mm_short: Mapped[int] = mapped_column(Integer, nullable=True)
    mm_net: Mapped[int] = mapped_column(Integer, nullable=True)
    mm_net_change: Mapped[int] = mapped_column(Integer, nullable=True)
    # Commercial (producers/merchants)
    commercial_long: Mapped[int] = mapped_column(Integer, nullable=True)
    commercial_short: Mapped[int] = mapped_column(Integer, nullable=True)
    commercial_net: Mapped[int] = mapped_column(Integer, nullable=True)
    # Non-commercial (large speculators)
    noncommercial_long: Mapped[int] = mapped_column(Integer, nullable=True)
    noncommercial_short: Mapped[int] = mapped_column(Integer, nullable=True)
    noncommercial_net: Mapped[int] = mapped_column(Integer, nullable=True)
    # Open interest
    open_interest: Mapped[int] = mapped_column(Integer, nullable=True)
    oi_change: Mapped[int] = mapped_column(Integer, nullable=True)
    # Percentile rankings (3-year)
    mm_net_percentile: Mapped[float] = mapped_column(Float, nullable=True)
    oi_percentile: Mapped[float] = mapped_column(Float, nullable=True)


class GoldETFFlow(Base):
    """Daily gold ETF holdings and flows."""
    __tablename__ = "gold_etf_flows"
    __table_args__ = (
        Index("ix_gold_etf_ticker_date", "ticker", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD
    ticker: Mapped[str] = mapped_column(String(10))  # GLD, IAU, SGOL, GLDM
    holdings_tonnes: Mapped[float] = mapped_column(Float, nullable=True)
    holdings_usd: Mapped[float] = mapped_column(Float, nullable=True)
    daily_change_tonnes: Mapped[float] = mapped_column(Float, nullable=True)
    daily_change_usd: Mapped[float] = mapped_column(Float, nullable=True)
    volume: Mapped[float] = mapped_column(Float, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=True)


class CentralBankGold(Base):
    """Monthly central bank gold purchases/sales."""
    __tablename__ = "central_bank_gold"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    country: Mapped[str] = mapped_column(String(100))
    total_tonnes: Mapped[float] = mapped_column(Float, nullable=True)
    monthly_change_tonnes: Mapped[float] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="wgc")  # wgc, imf


class FREDSeries(Base):
    """FRED economic data series snapshots."""
    __tablename__ = "fred_series"
    __table_args__ = (
        Index("ix_fred_series_id_date", "series_id", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_id: Mapped[str] = mapped_column(String(30), index=True)  # DFII10, T10YIE, DGS10, etc.
    date: Mapped[str] = mapped_column(String(10))  # YYYY-MM-DD
    value: Mapped[float] = mapped_column(Float)
    previous_value: Mapped[float] = mapped_column(Float, nullable=True)
    change: Mapped[float] = mapped_column(Float, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class BrokerAccount(Base):
    """User broker connections (MetaApi/demo)."""
    __tablename__ = "broker_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    broker_type: Mapped[str] = mapped_column(String(20), default="demo")  # demo, metaapi
    account_id: Mapped[str] = mapped_column(String(200), nullable=True)
    login: Mapped[str] = mapped_column(String(100), nullable=True)
    server: Mapped[str] = mapped_column(String(200), nullable=True)
    balance: Mapped[float] = mapped_column(Float, nullable=True)
    equity: Mapped[float] = mapped_column(Float, nullable=True)
    margin: Mapped[float] = mapped_column(Float, nullable=True)
    free_margin: Mapped[float] = mapped_column(Float, nullable=True)
    leverage: Mapped[int] = mapped_column(Integer, nullable=True)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    execution_mode: Mapped[str] = mapped_column(String(20), default="manual_approve")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class BrokerTrade(Base):
    """Live/demo broker trades."""
    __tablename__ = "broker_trades"
    __table_args__ = (
        Index("ix_broker_trades_user_status", "telegram_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    broker_order_id: Mapped[str] = mapped_column(String(100), nullable=True)
    symbol: Mapped[str] = mapped_column(String(20), default="XAUUSD")
    direction: Mapped[str] = mapped_column(String(10))  # BUY, SELL
    lot_size: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float] = mapped_column(Float, nullable=True)
    current_price: Mapped[float] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[float] = mapped_column(Float, nullable=True)
    take_profit: Mapped[float] = mapped_column(Float, nullable=True)
    take_profit_2: Mapped[float] = mapped_column(Float, nullable=True)
    take_profit_3: Mapped[float] = mapped_column(Float, nullable=True)
    pnl_usd: Mapped[float] = mapped_column(Float, nullable=True)
    pnl_pips: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, open, partial_close, closed
    close_reason: Mapped[str] = mapped_column(String(50), nullable=True)
    exit_price: Mapped[float] = mapped_column(Float, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    trade_advice_id: Mapped[int] = mapped_column(Integer, nullable=True)
    signal_id: Mapped[int] = mapped_column(Integer, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class TradeJournalEntry(Base):
    """Trade notes, emotions, self-rating."""
    __tablename__ = "trade_journal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    broker_trade_id: Mapped[int] = mapped_column(Integer, nullable=True)
    trade_advice_id: Mapped[int] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    emotion: Mapped[str] = mapped_column(String(30), nullable=True)  # confident, fearful, greedy, neutral, anxious
    self_rating: Mapped[int] = mapped_column(Integer, nullable=True)  # 1-5
    ai_entry_quality: Mapped[float] = mapped_column(Float, nullable=True)  # AI-assessed 0-100
    lessons: Mapped[str] = mapped_column(Text, nullable=True)
    # Trade details
    direction: Mapped[str] = mapped_column(String(10), nullable=True)  # buy/sell/long/short
    symbol: Mapped[str] = mapped_column(String(20), nullable=True, default="XAUUSD")
    open_price: Mapped[float] = mapped_column(Float, nullable=True)
    exit_price: Mapped[float] = mapped_column(Float, nullable=True)
    lot_size: Mapped[float] = mapped_column(Float, nullable=True)
    pnl: Mapped[float] = mapped_column(Float, nullable=True)
    open_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    close_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=True, default="open")  # open/closed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class GoldAnalystForecast(Base):
    """Institutional gold price targets."""
    __tablename__ = "gold_analyst_forecasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    institution: Mapped[str] = mapped_column(String(100))  # Goldman Sachs, JPMorgan, UBS, etc.
    analyst_name: Mapped[str] = mapped_column(String(200), nullable=True)
    target_price: Mapped[float] = mapped_column(Float)
    timeframe: Mapped[str] = mapped_column(String(20), nullable=True)  # Q1 2026, year-end 2026
    direction: Mapped[str] = mapped_column(String(20), nullable=True)
    reasoning: Mapped[str] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    gold_price_at_forecast: Mapped[float] = mapped_column(Float, nullable=True)
    was_accurate: Mapped[bool] = mapped_column(Boolean, nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=True)


class CopyTradeSubscription(Base):
    """Users copying AI advisor trades."""
    __tablename__ = "copy_trade_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    lot_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    max_lot_size: Mapped[float] = mapped_column(Float, default=0.1)
    daily_trade_limit: Mapped[int] = mapped_column(Integer, default=5)
    daily_loss_limit_usd: Mapped[float] = mapped_column(Float, default=100.0)
    trades_today: Mapped[int] = mapped_column(Integer, default=0)
    loss_today_usd: Mapped[float] = mapped_column(Float, default=0.0)
    total_copied_trades: Mapped[int] = mapped_column(Integer, default=0)
    total_pnl_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class WhiteLabelConfig(Base):
    """Broker white-label branding configuration."""
    __tablename__ = "whitelabel_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    broker_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    broker_name: Mapped[str] = mapped_column(String(200))
    logo_url: Mapped[str] = mapped_column(Text, nullable=True)
    primary_color: Mapped[str] = mapped_column(String(7), default="#D4AF37")
    secondary_color: Mapped[str] = mapped_column(String(7), default="#0f0f14")
    accent_color: Mapped[str] = mapped_column(String(7), default="#FFD700")
    bot_name: Mapped[str] = mapped_column(String(100), default="Griffin Gold")
    welcome_message: Mapped[str] = mapped_column(Text, nullable=True)
    broker_signup_url: Mapped[str] = mapped_column(Text, nullable=True)
    api_config: Mapped[dict] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class SharedTrade(Base):
    """Community shared trades for social trading / leaderboard."""
    __tablename__ = "shared_trades"
    __table_args__ = (
        Index("ix_shared_trades_telegram_id", "telegram_id"),
        Index("ix_shared_trades_created_at", "created_at"),
        Index("ix_shared_trades_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    direction: Mapped[str] = mapped_column(String(10))  # long/short
    entry_price: Mapped[float] = mapped_column(Float)
    target_price: Mapped[float] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[float] = mapped_column(Float, nullable=True)
    pnl: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open/closed
    reasoning: Mapped[str] = mapped_column(Text, nullable=True)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


# ──────────────────────────────────────────────────────────────
#  Database initialization
# ──────────────────────────────────────────────────────────────

def _add_missing_columns(connection):
    """Add any columns defined in models but missing from existing tables (works on both SQLite and PostgreSQL)."""
    inspector = inspect(connection)
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue  # Table doesn't exist yet — create_all will handle it
        existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
        for col in table.columns:
            if col.name not in existing_cols:
                col_type = col.type.compile(connection.dialect)
                if col.nullable:
                    nullable = "NULL"
                else:
                    # Use dialect-appropriate defaults for NOT NULL columns
                    type_str = str(col_type).upper()
                    if any(t in type_str for t in ("INT", "FLOAT", "REAL", "NUMERIC", "DOUBLE")):
                        nullable = "NOT NULL DEFAULT 0"
                    elif "BOOL" in type_str:
                        nullable = "NOT NULL DEFAULT false"
                    else:
                        nullable = "NOT NULL DEFAULT ''"
                try:
                    connection.execute(
                        text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {col_type} {nullable}')
                    )
                    _db_logger.info(f"Added missing column: {table.name}.{col.name} ({col_type})")
                except Exception as e:
                    _db_logger.warning(f"Column add skipped {table.name}.{col.name}: {e}")


def _drop_conflicting_indexes(connection):
    """Drop indexes that will conflict with create_all due to prior partial migrations."""
    inspector = inspect(connection)
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        existing_indexes = {idx["name"] for idx in inspector.get_indexes(table.name) if idx["name"]}
        for idx in table.indexes:
            if idx.name in existing_indexes:
                try:
                    connection.execute(text(f'DROP INDEX IF EXISTS "{idx.name}"'))
                    _db_logger.info(f"Dropped pre-existing index for re-creation: {idx.name}")
                except Exception:
                    pass


async def init_db():
    _db_logger.info(f"Connecting to database: {engine.url!s}")
    try:
        # First drop any conflicting indexes from prior partial migrations
        async with engine.begin() as conn:
            await conn.run_sync(_drop_conflicting_indexes)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # Run column migration in a separate transaction so the inspector
        # sees the freshly-committed tables/columns from create_all above.
        async with engine.begin() as conn:
            await conn.run_sync(_add_missing_columns)
        _db_logger.info("Database tables ready")
    except Exception as e:
        _db_logger.error(f"Database init failed: {e}", exc_info=True)
        raise


async def get_session() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
