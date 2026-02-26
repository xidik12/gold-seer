"""Market data collection jobs: gold price, macro, indicators, backfill."""

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy import select, desc

from app.config import settings
from app.database import (
    async_session, Price, MacroData, IndicatorSnapshot,
)
from app.collectors import (
    GoldMarketCollector, MacroCollector,
)
from app.features.builder import FeatureBuilder

logger = logging.getLogger(__name__)

# Global instances (initialized once)
market_collector = GoldMarketCollector()
macro_collector = MacroCollector()
feature_builder = FeatureBuilder()


async def backfill_historical_prices():
    """Backfill historical gold (XAUUSD) price data on startup.

    Uses HistoricalGoldCollector to fetch historical candles so that
    charts have data for all timeframes immediately.
    Only runs if the DB has less than 7 days of data.
    """
    try:
        from app.collectors.historical_gold import HistoricalGoldCollector

        # Check how much data we already have
        async with async_session() as session:
            result = await session.execute(
                select(Price).order_by(Price.timestamp).limit(1)
            )
            oldest = result.scalar_one_or_none()

            result = await session.execute(
                select(Price).order_by(desc(Price.timestamp)).limit(1)
            )
            newest = result.scalar_one_or_none()

        # If we already have >7 days of data, skip backfill
        if oldest and newest:
            span = (newest.timestamp - oldest.timestamp).total_seconds()
            if span > 7 * 86400:
                logger.info(f"Backfill: DB already has {span / 86400:.1f} days of data, skipping")
                return

        logger.info("Backfill: Starting historical gold price data fetch...")

        collector = HistoricalGoldCollector()
        try:
            all_prices = await collector.fetch_all_historical()
        finally:
            await collector.close()

        if not all_prices:
            logger.warning("Backfill: No historical prices fetched")
            return

        # Insert into Price table, skipping existing dates
        async with async_session() as session:
            if all_prices:
                min_date = min(p["timestamp"] for p in all_prices) - timedelta(days=1)
                max_date = max(p["timestamp"] for p in all_prices) + timedelta(days=1)
                result = await session.execute(
                    select(Price.timestamp).where(
                        Price.timestamp.between(min_date, max_date)
                    )
                )
            else:
                result = await session.execute(select(Price.timestamp))
            existing_dates = set()
            for row in result.all():
                existing_dates.add(row[0].strftime("%Y-%m-%d"))

            inserted = 0
            for p in all_prices:
                day_key = p["timestamp"].strftime("%Y-%m-%d")
                if day_key in existing_dates:
                    continue

                price = Price(
                    timestamp=p["timestamp"],
                    open=p["open"],
                    high=p["high"],
                    low=p["low"],
                    close=p["close"],
                    volume=p["volume"],
                    source="gold_historical_backfill",
                )
                session.add(price)
                existing_dates.add(day_key)
                inserted += 1

            await session.commit()

        logger.info(f"Backfill: Inserted {inserted} historical gold price records")

        # Trigger ML retrain with extended features after backfill
        if inserted > 100:
            try:
                from app.models.trainer import ModelTrainer
                trainer = ModelTrainer()
                result = await trainer.train_all()
                logger.info(f"Backfill: Post-backfill retrain result: {result.get('status')}")
            except Exception as e:
                logger.warning(f"Backfill: Post-backfill retrain failed (non-critical): {e}")

    except Exception as e:
        logger.error(f"Backfill error: {e}", exc_info=True)


async def _insert_klines(klines: list[dict], source: str = "gold_backfill"):
    """Insert kline data into the Price table, skipping duplicates by timestamp."""
    if not klines:
        return 0
    async with async_session() as session:
        # Compute time range of incoming klines for bounded dedup query
        kline_timestamps = []
        for k in klines:
            ts = k["timestamp"]
            if hasattr(ts, 'tzinfo') and ts.tzinfo is not None:
                ts = ts.replace(tzinfo=None)
            kline_timestamps.append(ts)
        min_ts = min(kline_timestamps) - timedelta(minutes=1)
        max_ts = max(kline_timestamps) + timedelta(minutes=1)

        # Only load existing timestamps within the kline range (not full table)
        result = await session.execute(
            select(Price.timestamp).where(
                Price.timestamp.between(min_ts, max_ts)
            )
        )
        existing_ts_minutes = set()
        for row in result.all():
            existing_ts_minutes.add(row[0].replace(second=0, microsecond=0))

        inserted = 0
        for k in klines:
            ts = k["timestamp"]
            # Make naive UTC if timezone-aware
            if hasattr(ts, 'tzinfo') and ts.tzinfo is not None:
                ts = ts.replace(tzinfo=None)

            ts_minute = ts.replace(second=0, microsecond=0)
            if ts_minute in existing_ts_minutes:
                continue

            price = Price(
                timestamp=ts,
                open=k["open"],
                high=k["high"],
                low=k["low"],
                close=k["close"],
                volume=k["volume"],
                source=source,
            )
            session.add(price)
            existing_ts_minutes.add(ts_minute)
            inserted += 1

        await session.commit()
        return inserted


async def collect_price_data():
    """Collect and store gold (XAUUSD) price data (runs every minute).

    Uses GoldMarketCollector to fetch the latest gold price candle.
    """
    try:
        price_data = await market_collector.collect()

        if not price_data:
            logger.warning("No gold price data received")
            return

        async with async_session() as session:
            price = Price(
                timestamp=datetime.utcnow(),
                open=float(price_data.get("open", 0)),
                high=float(price_data.get("high", 0)),
                low=float(price_data.get("low", 0)),
                close=float(price_data.get("close", 0)),
                volume=float(price_data.get("volume", 0)),
                source="gold_market",
            )
            session.add(price)
            await session.commit()

        logger.info(f"Gold price collected: ${price_data.get('close', 'N/A')}")

    except Exception as e:
        logger.error(f"Gold price collection error: {e}")


async def collect_macro_data():
    """Collect and store macro market data (runs every hour)."""
    try:
        macro_data = await macro_collector.collect()

        def _price(key):
            val = macro_data.get(key)
            return val.get("price") if isinstance(val, dict) else None

        dxy = _price("dxy")
        gold = _price("gold")
        sp500 = _price("sp500")
        treasury_10y = _price("treasury_10y")
        nasdaq = _price("nasdaq")
        vix = _price("vix")
        eurusd = _price("eurusd")
        # New forex
        gbpusd = _price("gbpusd")
        usdjpy = _price("usdjpy")
        usdchf = _price("usdchf")
        audusd = _price("audusd")
        usdcad = _price("usdcad")
        nzdusd = _price("nzdusd")
        # New commodities
        wti_oil = _price("wti_oil")
        silver = _price("silver")
        copper = _price("copper")
        natural_gas = _price("natural_gas")
        # Gold mining/ETF equities
        gdx = _price("gdx")
        gld = _price("gld")
        # New indices
        dow_jones = _price("dow_jones")
        russell_2000 = _price("russell_2000")
        dax = _price("dax")
        nikkei_225 = _price("nikkei_225")
        ftse_100 = _price("ftse_100")

        # Don't save a row where ALL values are None
        all_prices = [dxy, gold, sp500, treasury_10y, nasdaq, vix, eurusd,
                      gbpusd, usdjpy, usdchf, audusd, usdcad, nzdusd,
                      wti_oil, silver, copper, natural_gas,
                      gdx, gld,
                      dow_jones, russell_2000, dax, nikkei_225, ftse_100]
        if all(v is None for v in all_prices):
            logger.warning("Macro collection returned all None values, skipping DB save")
            return

        # Fetch M2 money supply
        m2_supply = None
        try:
            m2_supply = await macro_collector.fetch_m2_supply()
        except Exception as e:
            logger.debug(f"M2 supply fetch error: {e}")

        # Fetch treasury yields from FRED
        treasury_yields = {}
        try:
            treasury_yields = await macro_collector.fetch_treasury_yields()
        except Exception as e:
            logger.debug(f"Treasury yields fetch error: {e}")

        async with async_session() as session:
            macro = MacroData(
                timestamp=datetime.utcnow(),
                dxy=dxy,
                gold=gold,
                sp500=sp500,
                treasury_10y=treasury_10y,
                nasdaq=nasdaq,
                vix=vix,
                eurusd=eurusd,
                m2_supply=m2_supply,
                # New forex
                gbpusd=gbpusd,
                usdjpy=usdjpy,
                usdchf=usdchf,
                audusd=audusd,
                usdcad=usdcad,
                nzdusd=nzdusd,
                # New commodities
                wti_oil=wti_oil,
                silver=silver,
                copper=copper,
                natural_gas=natural_gas,
                # Gold mining/ETF equities
                gdx=gdx,
                gld=gld,
                # New indices
                dow_jones=dow_jones,
                russell_2000=russell_2000,
                dax=dax,
                nikkei_225=nikkei_225,
                ftse_100=ftse_100,
                # Treasury yields from FRED
                treasury_2y=treasury_yields.get("treasury_2y"),
                treasury_5y=treasury_yields.get("treasury_5y"),
                treasury_30y=treasury_yields.get("treasury_30y"),
            )
            session.add(macro)
            await session.commit()

        logger.info(f"Macro data collected: DXY={dxy}, Gold={gold}, SP500={sp500}, 10Y={treasury_10y}, VIX={vix}, Silver={silver}")

    except Exception as e:
        logger.error(f"Macro collection error: {e}")


async def save_indicator_snapshot():
    """Compute and persist a full technical indicator snapshot (runs every hour).

    This saves the complete indicator state so historical indicator values
    are available for backtesting, model training, and trend analysis.
    """
    try:
        from app.features.technical import TechnicalFeatures

        async with async_session() as session:
            since = datetime.utcnow() - timedelta(hours=400)
            result = await session.execute(
                select(Price).where(Price.timestamp >= since).order_by(Price.timestamp)
            )
            prices = result.scalars().all()

        if len(prices) < 30:
            logger.debug(f"Not enough price data for indicator snapshot ({len(prices)} candles)")
            return

        df = pd.DataFrame([
            {"open": p.open, "high": p.high, "low": p.low, "close": p.close, "volume": p.volume}
            for p in prices
        ])

        import asyncio
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, TechnicalFeatures.calculate_all, df)
        latest = df.iloc[-1]

        def safe(val):
            if pd.isna(val):
                return None
            v = float(val)
            return round(v, 6) if abs(v) < 1e12 else v

        indicators = {
            # Moving averages
            "ema_9": safe(latest.get("ema_9")),
            "ema_21": safe(latest.get("ema_21")),
            "ema_50": safe(latest.get("ema_50")),
            "ema_200": safe(latest.get("ema_200")),
            "sma_20": safe(latest.get("sma_20")),
            "sma_111": safe(latest.get("sma_111")),
            "sma_200": safe(latest.get("sma_200")),
            "sma_350": safe(latest.get("sma_350")),
            # Momentum
            "rsi": safe(latest.get("rsi")),
            "rsi_7": safe(latest.get("rsi_7")),
            "rsi_30": safe(latest.get("rsi_30")),
            "macd": safe(latest.get("macd")),
            "macd_signal": safe(latest.get("macd_signal")),
            "macd_hist": safe(latest.get("macd_hist")),
            "adx": safe(latest.get("adx")),
            "stoch_rsi_k": safe(latest.get("stoch_rsi_k")),
            "stoch_rsi_d": safe(latest.get("stoch_rsi_d")),
            "williams_r": safe(latest.get("williams_r")),
            "momentum_10": safe(latest.get("momentum_10")),
            "momentum_20": safe(latest.get("momentum_20")),
            # Volatility
            "bb_upper": safe(latest.get("bb_upper")),
            "bb_middle": safe(latest.get("bb_middle")),
            "bb_lower": safe(latest.get("bb_lower")),
            "bb_width": safe(latest.get("bb_width")),
            "bb_position": safe(latest.get("bb_position")),
            "atr": safe(latest.get("atr")),
            "volatility_24h": safe(latest.get("volatility_24h")),
            # Volume
            "obv": safe(latest.get("obv")),
            "vwap": safe(latest.get("vwap")),
            "volume_sma_20": safe(latest.get("volume_sma_20")),
            "volume_ratio": safe(latest.get("volume_ratio")),
            # Levels
            "pivot": safe(latest.get("pivot")),
            "support_1": safe(latest.get("support_1")),
            "resistance_1": safe(latest.get("resistance_1")),
            # Advanced
            "mayer_multiple": safe(latest.get("mayer_multiple")),
            "ema_cross": safe(latest.get("ema_cross")),
            "zscore_20": safe(latest.get("zscore_20")),
            # Ichimoku
            "ichimoku_tenkan": safe(latest.get("ichimoku_tenkan")),
            "ichimoku_kijun": safe(latest.get("ichimoku_kijun")),
            "ichimoku_senkou_a": safe(latest.get("ichimoku_senkou_a")),
            "ichimoku_senkou_b": safe(latest.get("ichimoku_senkou_b")),
            # Trend
            "trend_short": int(latest.get("trend_short", 0)),
            "trend_medium": int(latest.get("trend_medium", 0)),
            "trend_long": int(latest.get("trend_long", 0)),
            # ROC
            "roc_1": safe(latest.get("roc_1")),
            "roc_6": safe(latest.get("roc_6")),
            "roc_12": safe(latest.get("roc_12")),
            "roc_24": safe(latest.get("roc_24")),
            # Candlestick patterns
            "candle_doji": int(latest.get("candle_doji", 0)),
            "candle_hammer": int(latest.get("candle_hammer", 0)),
            "candle_inverted_hammer": int(latest.get("candle_inverted_hammer", 0)),
            "candle_bullish_engulfing": int(latest.get("candle_bullish_engulfing", 0)),
            "candle_bearish_engulfing": int(latest.get("candle_bearish_engulfing", 0)),
            "candle_morning_star": int(latest.get("candle_morning_star", 0)),
            "candle_evening_star": int(latest.get("candle_evening_star", 0)),
        }

        current_price = float(prices[-1].close)

        async with async_session() as session:
            snapshot = IndicatorSnapshot(
                timestamp=datetime.utcnow(),
                price=current_price,
                indicators=indicators,
            )
            session.add(snapshot)
            await session.commit()

        logger.info(f"Indicator snapshot saved (RSI={indicators.get('rsi')}, MACD={indicators.get('macd')})")

    except Exception as e:
        logger.error(f"Indicator snapshot error: {e}")


async def collect_cot_data():
    """Collect CFTC Commitments of Traders data for gold (runs every 6h)."""
    try:
        from app.collectors.cot import COTCollector
        from app.database import async_session, COTData
        from sqlalchemy import select

        collector = COTCollector()
        data = await collector.collect()
        if not data:
            logger.info("COT: No new data returned")
            return

        async with async_session() as session:
            # Upsert by report_date
            for record in (data if isinstance(data, list) else [data]):
                report_date = record.get("report_date")
                if not report_date:
                    continue
                existing = await session.execute(
                    select(COTData).where(COTData.report_date == report_date)
                )
                if existing.scalar_one_or_none():
                    continue  # Already have this week's data
                cot = COTData(
                    report_date=report_date,
                    mm_long=record.get("mm_long"),
                    mm_short=record.get("mm_short"),
                    mm_net=record.get("mm_net"),
                    mm_net_change=record.get("mm_net_change"),
                    commercial_long=record.get("commercial_long"),
                    commercial_short=record.get("commercial_short"),
                    commercial_net=record.get("commercial_net"),
                    noncommercial_long=record.get("noncommercial_long"),
                    noncommercial_short=record.get("noncommercial_short"),
                    noncommercial_net=record.get("noncommercial_net"),
                    open_interest=record.get("open_interest"),
                    oi_change=record.get("oi_change"),
                    mm_net_percentile=record.get("mm_net_percentile"),
                    oi_percentile=record.get("oi_percentile"),
                )
                session.add(cot)
            await session.commit()

        logger.info(f"COT data collected successfully")
    except Exception as e:
        logger.error(f"COT collection error: {e}")


async def collect_fred_data():
    """Collect FRED economic data series (runs every 6h)."""
    try:
        from app.collectors.fred import FREDCollector
        from app.database import async_session, FREDSeries
        from sqlalchemy import select

        collector = FREDCollector()
        data = await collector.collect()
        if not data:
            logger.info("FRED: No new data returned")
            return

        async with async_session() as session:
            for record in (data if isinstance(data, list) else [data]):
                series_id = record.get("series_id")
                date = record.get("date")
                if not series_id or not date:
                    continue
                # Upsert by series_id + date
                existing = await session.execute(
                    select(FREDSeries).where(
                        FREDSeries.series_id == series_id,
                        FREDSeries.date == date,
                    )
                )
                if existing.scalar_one_or_none():
                    continue
                fred = FREDSeries(
                    series_id=series_id,
                    date=date,
                    value=record.get("value", 0),
                    previous_value=record.get("previous_value"),
                    change=record.get("change"),
                )
                session.add(fred)
            await session.commit()

        logger.info(f"FRED data collected successfully")
    except Exception as e:
        logger.error(f"FRED collection error: {e}")


async def collect_etf_flows():
    """Collect gold ETF flow data (runs every hour)."""
    try:
        from app.collectors.gold_etf import GoldETFFlowCollector
        from app.database import async_session, GoldETFFlow
        from sqlalchemy import select

        collector = GoldETFFlowCollector()
        data = await collector.collect()
        if not data:
            logger.info("ETF: No new flow data returned")
            return

        async with async_session() as session:
            for record in (data if isinstance(data, list) else [data]):
                ticker = record.get("ticker")
                date = record.get("date")
                if not ticker or not date:
                    continue
                # Upsert by ticker + date
                existing = await session.execute(
                    select(GoldETFFlow).where(
                        GoldETFFlow.ticker == ticker,
                        GoldETFFlow.date == date,
                    )
                )
                if existing.scalar_one_or_none():
                    continue
                etf = GoldETFFlow(
                    date=date,
                    ticker=ticker,
                    holdings_tonnes=record.get("holdings_tonnes"),
                    holdings_usd=record.get("holdings_usd"),
                    daily_change_tonnes=record.get("daily_change_tonnes"),
                    daily_change_usd=record.get("daily_change_usd"),
                    volume=record.get("volume"),
                    price=record.get("price"),
                )
                session.add(etf)
            await session.commit()

        count = len(data) if isinstance(data, list) else 1
        logger.info(f"ETF flow data collected: {count} records")
    except Exception as e:
        logger.error(f"ETF flow collection error: {e}")


async def collect_session_info():
    """Collect gold trading session data (runs every 5 minutes)."""
    try:
        from app.collectors.session_tracker import SessionTracker

        tracker = SessionTracker()
        data = await tracker.collect()
        if data:
            logger.info(f"Session data collected: {data.get('session_name', 'unknown')}")
    except Exception as e:
        logger.error(f"Session collection error: {e}")


async def collect_central_bank_gold():
    """Collect central bank gold purchase data (runs every 24h)."""
    try:
        from app.collectors.central_bank import CentralBankGoldCollector
        from app.database import async_session, CentralBankGold
        from sqlalchemy import select

        collector = CentralBankGoldCollector()
        data = await collector.collect()
        if not data:
            logger.info("Central bank: No new data returned")
            return

        async with async_session() as session:
            for record in (data if isinstance(data, list) else [data]):
                report_date = record.get("report_date")
                country = record.get("country")
                if not report_date or not country:
                    continue
                existing = await session.execute(
                    select(CentralBankGold).where(
                        CentralBankGold.report_date == report_date,
                        CentralBankGold.country == country,
                    )
                )
                if existing.scalar_one_or_none():
                    continue
                cb = CentralBankGold(
                    report_date=report_date,
                    country=country,
                    total_tonnes=record.get("total_tonnes"),
                    monthly_change_tonnes=record.get("monthly_change_tonnes"),
                    source=record.get("source", "wgc"),
                )
                session.add(cb)
            await session.commit()

        count = len(data) if isinstance(data, list) else 1
        logger.info(f"Central bank gold data collected: {count} records")
    except Exception as e:
        logger.error(f"Central bank gold collection error: {e}")
