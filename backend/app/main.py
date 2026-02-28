import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.database import init_db
from app.api import predictions, signals, news, market, history, events, quant, marketing
from app.api import charts as charts_api
from app.api import support as support_api
from app.api import advisor as advisor_api
from app.api import admin as admin_api
from app.api import public_api, elliott_wave, subscription, auth as auth_api, referral as referral_api
from app.api import partner_admin as partner_admin_api, partner_dashboard as partner_dashboard_api
from app.api import alerts as alerts_api, briefings as briefings_api, game as game_api
from app.api import websocket as websocket_api
from app.api import calendar as calendar_api
from app.api import dashboard as dashboard_api
from app.api import branding as branding_api
from app.api import cot as cot_api
from app.api import sessions as sessions_api
from app.api import broker as broker_api
from app.api import trade_journal as trade_journal_api
from app.api import gold_etf as gold_etf_api
from app.api import copy_trade as copy_trade_api
from app.api import calculators as calculators_api
from app.api import analysts as analysts_api
from app.api import fundamentals as fundamentals_api
from app.api import backtest as backtest_api
from app.api import community as community_api
from app.scheduler.jobs import (
    backfill_historical_prices,
    collect_price_data,
    collect_news_data,
    collect_macro_data,
    save_indicator_snapshot,
    collect_cot_data,
    collect_fred_data,
    collect_etf_flows,
    collect_session_info,
    collect_central_bank_gold,
    collect_economic_calendar,
    generate_prediction,
    generate_prediction_1h,
    generate_prediction_4h,
    generate_prediction_24h,
    deduplicate_predictions,
    generate_quant_prediction,
    generate_quant_prediction_1h,
    generate_quant_prediction_4h,
    generate_quant_prediction_24h,
    evaluate_predictions,
    evaluate_quant_predictions,
    classify_news_events,
    evaluate_event_impacts,
    cleanup_old_data,
    auto_retrain_models,
    run_advisor_check,
    run_trade_management,
    check_subscription_expiry,
    snapshot_daily_metrics,
    evaluate_game_predictions,
    reset_game_periods,
    check_central_bank_alerts,
    collect_analyst_forecasts,
)
from app.scheduler.daily_briefing import generate_daily_briefing
from app.advisor.feedback import run_training_feedback, run_adaptive_weight_learning
from app.models.phrase_analyzer import analyze_news_phrases
from app.models.continuous_learner import run_continuous_learning
from app.models.ab_tester import evaluate_candidates
from app.models.pattern_learner import run_pattern_discovery
from app.scheduler.backup import run_database_backup
from app.broker.position_manager import PositionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="utc")


_startup_error: str | None = None
_data_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    global _startup_error
    # Startup
    logger.info("Griffin Gold starting up...")

    bot = None
    dp = None
    bot_task = None

    try:
        # Resolve bot username from Telegram API
        if settings.telegram_bot_token and not settings.bot_username:
            import aiohttp
            try:
                async with aiohttp.ClientSession() as client:
                    async with client.get(f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        data = await resp.json()
                        if data.get("ok"):
                            settings.bot_username = data["result"]["username"]
                            logger.info(f"Bot username resolved: @{settings.bot_username}")
                        else:
                            logger.warning(f"Failed to resolve bot username: {data}")
            except Exception as e:
                logger.warning(f"Could not resolve bot username: {e}")

        if not settings.admin_telegram_id:
            logger.warning("ADMIN_TELEGRAM_ID not set — admin endpoints will be inaccessible")

        # Initialize database
        await init_db()
        logger.info("Database initialized")

        # Ensure model weights dir exists on persistent volume
        import shutil
        import os
        weights_dir = Path(settings.model_dir)
        bundled_weights = Path("app/models/weights")
        weights_dir.mkdir(parents=True, exist_ok=True)

        # Check if we should force retrain (env var FORCE_RETRAIN=1)
        force_retrain = os.getenv("FORCE_RETRAIN", "0") == "1"
        if force_retrain:
            logger.warning("FORCE_RETRAIN=1: Deleting existing model weights")
            for f in weights_dir.glob("*.pt"):
                f.unlink()
                logger.info(f"Deleted incompatible weight: {f.name}")

        # Copy bundled weights if persistent dir is empty
        if bundled_weights.exists() and not any(weights_dir.glob("*.pt")):
            for f in bundled_weights.iterdir():
                if f.is_file():
                    shutil.copy2(f, weights_dir / f.name)
                    logger.info(f"Copied bundled weight: {f.name} -> {weights_dir}")

        logger.info(f"Model weights dir: {weights_dir}")

        # Shared APScheduler kwargs — prevent job overlap and handle misfires
        _job_defaults = dict(max_instances=1, coalesce=True, misfire_grace_time=300)

        # Set up scheduled jobs
        # Data collection jobs
        scheduler.add_job(collect_price_data, "interval", seconds=60, id="collect_price", **_job_defaults)
        scheduler.add_job(collect_news_data, "interval", minutes=2, id="collect_news", **_job_defaults)
        scheduler.add_job(collect_macro_data, "interval", hours=1, id="collect_macro", **_job_defaults)
        scheduler.add_job(save_indicator_snapshot, "interval", hours=1, id="save_indicators", **_job_defaults)

        # Gold-specific collector jobs
        scheduler.add_job(collect_cot_data, "interval", hours=6, id="collect_cot", **_job_defaults)
        scheduler.add_job(collect_fred_data, "interval", hours=6, id="collect_fred", **_job_defaults)
        scheduler.add_job(collect_etf_flows, "interval", hours=1, id="collect_etf_flows", **_job_defaults)
        scheduler.add_job(collect_session_info, "interval", minutes=5, id="collect_sessions", **_job_defaults)
        scheduler.add_job(collect_central_bank_gold, "interval", hours=24, id="collect_cb_gold", **_job_defaults)
        scheduler.add_job(check_central_bank_alerts, "interval", hours=12, id="check_cb_alerts", **_job_defaults)
        scheduler.add_job(collect_economic_calendar, "interval", hours=6, id="collect_econ_calendar", **_job_defaults)
        scheduler.add_job(collect_analyst_forecasts, "interval", hours=24, id="collect_analyst_forecasts", **_job_defaults)

        # Prediction jobs — time-aligned cron schedules (UTC)
        # 1h: every hour at :00
        scheduler.add_job(generate_prediction_1h, "cron", minute=0, id="predict_1h", **_job_defaults)
        # 4h: at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 (minute 2)
        scheduler.add_job(generate_prediction_4h, "cron", hour="0,4,8,12,16,20", minute=2, id="predict_4h", **_job_defaults)
        # 24h: once daily at 00:04
        scheduler.add_job(generate_prediction_24h, "cron", hour=0, minute=4, id="predict_24h", **_job_defaults)

        # Quant predictions — offset by 1 minute from ML predictions
        scheduler.add_job(generate_quant_prediction_1h, "cron", minute=1, id="predict_quant_1h", **_job_defaults)
        scheduler.add_job(generate_quant_prediction_4h, "cron", hour="0,4,8,12,16,20", minute=3, id="predict_quant_4h", **_job_defaults)
        scheduler.add_job(generate_quant_prediction_24h, "cron", hour=0, minute=5, id="predict_quant_24h", **_job_defaults)

        # Evaluation jobs — time-aligned
        # 1h: evaluate at :05 every hour
        scheduler.add_job(evaluate_predictions, "cron", minute=5, kwargs={"timeframe_filter": "1h"}, id="evaluate_1h", **_job_defaults)
        # 4h: evaluate at :07 on 4h boundaries
        scheduler.add_job(evaluate_predictions, "cron", hour="0,4,8,12,16,20", minute=7, kwargs={"timeframe_filter": "4h"}, id="evaluate_4h", **_job_defaults)
        # 24h: evaluate at 00:09 daily
        scheduler.add_job(evaluate_predictions, "cron", hour=0, minute=9, kwargs={"timeframe_filter": "24h"}, id="evaluate_24h", **_job_defaults)
        scheduler.add_job(evaluate_quant_predictions, "interval", hours=1, id="evaluate_quant", **_job_defaults)
        scheduler.add_job(classify_news_events, "interval", minutes=5, id="classify_events", **_job_defaults)
        scheduler.add_job(evaluate_event_impacts, "interval", minutes=30, id="evaluate_events", **_job_defaults)

        # Cleanup
        scheduler.add_job(cleanup_old_data, "interval", hours=24, id="cleanup", **_job_defaults)

        # Auto-retrain: check every 6 hours if models need retraining (more frequent continuous learning)
        scheduler.add_job(auto_retrain_models, "interval", hours=6, id="auto_retrain", **_job_defaults)

        # Phrase analyzer: hourly news phrase correlation analysis
        scheduler.add_job(analyze_news_phrases, "interval", hours=1, id="analyze_phrases", **_job_defaults)

        # Continuous learner: adaptive ensemble weights + selective retrain (every 6h)
        scheduler.add_job(run_continuous_learning, "interval", hours=6, id="continuous_learning", **_job_defaults)

        # A/B testing: evaluate candidate models (every 6h)
        scheduler.add_job(evaluate_candidates, "interval", hours=6, id="ab_testing", **_job_defaults)

        # Pattern learning: discover accuracy patterns every 6h
        scheduler.add_job(run_pattern_discovery, "cron", hour="0,6,12,18", minute=30, id="pattern_learning", **_job_defaults)

        # Advisor jobs
        scheduler.add_job(run_advisor_check, "interval", minutes=30, id="advisor_check", **_job_defaults)
        scheduler.add_job(run_trade_management, "interval", minutes=10, id="trade_management", **_job_defaults)

        # Training feedback loop (daily)
        scheduler.add_job(run_training_feedback, "interval", hours=24, id="training_feedback", **_job_defaults)

        # Adaptive weight learning (daily, 1h after feedback)
        scheduler.add_job(run_adaptive_weight_learning, "interval", hours=24, id="adaptive_weights", **_job_defaults)

        # Subscription expiry check (daily)
        scheduler.add_job(check_subscription_expiry, "interval", hours=24, id="check_subs", **_job_defaults)

        # Daily metrics snapshot at 23:55 UTC
        scheduler.add_job(snapshot_daily_metrics, "cron", hour=23, minute=55, id="snapshot_metrics", **_job_defaults)

        # Database backup
        scheduler.add_job(run_database_backup, "interval", hours=settings.backup_interval_hours, id="database_backup", **_job_defaults)

        # Daily briefing generation (07:55 UTC)
        scheduler.add_job(generate_daily_briefing, "cron", hour=7, minute=55, id="generate_briefing", **_job_defaults)

        # Prediction game evaluation (every hour at :05)
        scheduler.add_job(evaluate_game_predictions, "cron", minute=5, id="evaluate_game", **_job_defaults)

        # Game leaderboard period reset (daily at 00:00)
        scheduler.add_job(reset_game_periods, "cron", hour=0, minute=0, id="reset_game_periods", **_job_defaults)

        # Broker position management (every 30 seconds, only if broker_enabled)
        if settings.broker_enabled:
            _position_manager = PositionManager()

            async def manage_broker_positions():
                """Run position management for all connected user brokers."""
                from app.bot.commands import _user_brokers

                if not _user_brokers:
                    return

                for telegram_id, broker in list(_user_brokers.items()):
                    try:
                        positions = await broker.get_positions()
                        if positions:
                            actions = await _position_manager.manage_positions(broker, positions)
                            if actions:
                                logger.info(
                                    "Position manager: %d actions for user %d",
                                    len(actions),
                                    telegram_id,
                                )
                    except Exception as e:
                        logger.error(
                            "Position management error for user %d: %s",
                            telegram_id,
                            e,
                        )

            scheduler.add_job(
                manage_broker_positions,
                "interval",
                seconds=30,
                id="manage_broker_positions",
                **_job_defaults,
            )
            logger.info("Broker position management job enabled (30s interval)")

        scheduler.start()
        logger.info("Scheduler started")

        # Start Telegram bot if token is set
        if settings.telegram_bot_token:
            from app.bot.bot import create_bot
            from app.bot.alerts import AlertSender

            bot, dp = create_bot()
            alert_sender = AlertSender(bot)

            # Add alert job
            scheduler.add_job(
                alert_sender.send_hourly_alerts,
                "interval",
                hours=1,
                id="send_alerts",
                **_job_defaults,
            )

            # Price alerts check (every 2 minutes)
            scheduler.add_job(
                alert_sender.check_price_alerts,
                "interval",
                minutes=2,
                id="check_price_alerts",
                **_job_defaults,
            )

            # Daily briefing delivery (08:00 UTC)
            scheduler.add_job(
                alert_sender.send_daily_briefing,
                "cron",
                hour=8,
                minute=0,
                id="send_briefing",
                **_job_defaults,
            )

            # Set bot description & command menu
            try:
                from aiogram.types import BotCommand

                await bot.set_my_description(
                    "Griffin Gold — AI-powered XAUUSD trading intelligence.\n\n"
                    "Hit /start to begin. I'll analyze 60+ market signals "
                    "every hour and give you clear gold price predictions, "
                    "trading signals, and real-time news sentiment.\n\n"
                    "Free 7-day trial included."
                )
                await bot.set_my_short_description(
                    "AI gold (XAUUSD) predictions, trading signals & market intelligence."
                )
                await bot.set_my_commands([
                    BotCommand(command="start", description="Start the bot & see the main menu"),
                    BotCommand(command="predict", description="Latest gold price predictions"),
                    BotCommand(command="signal", description="Trading signal with entry & stop-loss"),
                    BotCommand(command="advisor", description="AI trading advisor & portfolio"),
                    BotCommand(command="news", description="Real-time gold & macro news & sentiment"),
                    BotCommand(command="macro", description="Macro dashboard — Gold, DXY, yields, VIX"),
                    BotCommand(command="cot", description="COT positioning — hedge funds & commercials"),
                    BotCommand(command="calendar", description="Upcoming economic events & impact"),
                    BotCommand(command="sessions", description="Active trading sessions & volatility"),
                    BotCommand(command="connect", description="Connect to a broker (demo/live)"),
                    BotCommand(command="positions", description="View open broker positions"),
                    BotCommand(command="trade", description="Place a trade — /trade buy 0.01"),
                    BotCommand(command="accuracy", description="Prediction track record"),
                    BotCommand(command="faq", description="Frequently asked questions"),
                    BotCommand(command="report", description="Report a bug or issue"),
                    BotCommand(command="settings", description="Alert frequency preferences"),
                    BotCommand(command="subscribe", description="View subscription plans"),
                    BotCommand(command="alert", description="Manage price alerts"),
                    BotCommand(command="game", description="Prediction game — UP or DOWN?"),
                ])
                logger.info("Bot description & commands set")
            except Exception as e:
                logger.warning(f"set_my_description/commands failed: {e}")

            # Clear stale webhooks + pending updates before polling
            try:
                await bot.delete_webhook(drop_pending_updates=True)
                logger.info("Cleared webhook, starting polling")
            except Exception as e:
                logger.warning(f"delete_webhook failed: {e}")

            # Brief delay to let previous Railway instance shut down
            await asyncio.sleep(5)

            # Start polling in background with retry on conflict (deployment overlap)
            async def _run_bot_polling():
                retry_delay = 10
                max_retries = 12  # ~2 minutes of retrying
                for attempt in range(max_retries):
                    try:
                        logger.info("Bot polling starting... (attempt %d)", attempt + 1)
                        await dp.start_polling(bot)
                        break  # Clean exit
                    except Exception as e:
                        err_str = str(e).lower()
                        if "conflict" in err_str or "409" in err_str:
                            # Old instance still polling — wait and retry
                            logger.warning(
                                "Bot polling: 409 conflict (old instance still running), "
                                "retrying in %ds (attempt %d/%d)",
                                retry_delay, attempt + 1, max_retries,
                            )
                        else:
                            logger.error(
                                "Bot polling crashed: %s, retrying in %ds",
                                e, retry_delay,
                            )
                        await asyncio.sleep(retry_delay)
                        retry_delay = min(retry_delay * 1.5, 30)
                else:
                    logger.error("Bot polling: gave up after %d attempts", max_retries)

            bot_task = asyncio.create_task(_run_bot_polling())
            logger.info("Telegram bot started")
        else:
            logger.warning("TELEGRAM_BOT_TOKEN not set — bot disabled")

        # Backfill historical prices, then collect fresh data + predict
        async def _safe_run(coro, name):
            """Run a coroutine safely — log errors but don't kill the pipeline."""
            try:
                await coro
                logger.info(f"Startup: {name} completed")
            except Exception as e:
                logger.error(f"Startup: {name} failed: {e}", exc_info=True)

        async def startup_data_pipeline():
            # Step 1: Backfill historical gold price data
            await _safe_run(backfill_historical_prices(), "backfill_historical_prices")

            # Step 2: Critical data first (price, news, macro)
            await asyncio.gather(
                _safe_run(collect_price_data(), "collect_price_data"),
                _safe_run(collect_news_data(), "collect_news_data"),
                _safe_run(collect_macro_data(), "collect_macro_data"),
            )

            # Mark server ready after core data — predictions can finish in background
            global _data_ready
            _data_ready = True
            logger.info("Core data loaded — server ready")

            # Step 3: Clean up duplicate predictions
            await _safe_run(deduplicate_predictions(), "deduplicate_predictions")

            # Step 4: Generate predictions (data is already collected above)
            await asyncio.gather(
                _safe_run(generate_prediction(), "generate_prediction"),
                _safe_run(generate_quant_prediction(), "generate_quant_prediction"),
                _safe_run(classify_news_events(), "classify_news_events"),
                _safe_run(save_indicator_snapshot(), "save_indicator_snapshot"),
                _safe_run(collect_analyst_forecasts(), "collect_analyst_forecasts"),
            )

        async def _startup_wrapper():
            await startup_data_pipeline()
            logger.info("Full data pipeline complete")

        asyncio.create_task(_startup_wrapper())
        logger.info("Startup complete — server ready, data pipeline loading in background")

    except Exception as e:
        _startup_error = f"{type(e).__name__}: {e}"
        logger.error(f"STARTUP FAILED: {_startup_error}", exc_info=True)

    yield

    # Shutdown
    try:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
    except Exception:
        pass

    if bot_task:
        bot_task.cancel()
        await bot.session.close()
        logger.info("Telegram bot stopped")

    from app.redis_client import close_redis
    await close_redis()

    logger.info("Griffin Gold shut down")


class CachedStaticFiles(StaticFiles):
    """StaticFiles with immutable cache headers for hashed Vite assets."""

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, (FileResponse, Response)):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


app = FastAPI(
    title="Griffin Gold",
    description="Gold (XAUUSD) Trading Intelligence Platform with ML-powered signals",
    version="1.0.0",
    lifespan=lifespan,
)

# Sentry error tracking
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        environment="production" if not settings.debug else "development",
    )

# Prometheus metrics endpoint at /metrics
_instrumentator = Instrumentator()
_instrumentator.instrument(app)
if os.getenv("EXPOSE_METRICS"):
    _instrumentator.expose(app, endpoint="/metrics")

# GZip compression for all responses > 500 bytes
app.add_middleware(GZipMiddleware, minimum_size=500)

# CORS for Mini App
_cors_origins = [
    "https://web.telegram.org",
    "https://webk.telegram.org",
    "https://webz.telegram.org",
]
if settings.debug:
    _cors_origins.extend(["http://localhost:5173", "http://localhost:3000"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key authentication middleware (for /api/v1/ public endpoints)
from app.middleware.auth import APIKeyMiddleware
app.add_middleware(APIKeyMiddleware)

# Include API routers
app.include_router(predictions.router)
app.include_router(signals.router)
app.include_router(news.router)
app.include_router(market.router)
app.include_router(history.router)
app.include_router(events.router)
app.include_router(quant.router)
app.include_router(advisor_api.router)
app.include_router(admin_api.router)
app.include_router(elliott_wave.router)
app.include_router(subscription.router)
app.include_router(auth_api.router)
app.include_router(referral_api.router)
app.include_router(marketing.router)
app.include_router(charts_api.router)
app.include_router(support_api.router)
app.include_router(public_api.router)
app.include_router(partner_admin_api.router)
app.include_router(partner_dashboard_api.router)
app.include_router(alerts_api.router)
app.include_router(briefings_api.router)
app.include_router(game_api.router)
app.include_router(websocket_api.router)
app.include_router(calendar_api.router)
app.include_router(dashboard_api.router)
app.include_router(branding_api.router)
app.include_router(cot_api.router)
app.include_router(sessions_api.router)
app.include_router(broker_api.router)
app.include_router(trade_journal_api.router)
app.include_router(gold_etf_api.router)
app.include_router(copy_trade_api.router)
app.include_router(calculators_api.router)
app.include_router(analysts_api.router)
app.include_router(fundamentals_api.router)
app.include_router(backtest_api.router)
app.include_router(community_api.router)


@app.get("/health")
async def health():
    if _startup_error:
        return {"status": "degraded", "error": "Service startup issue. Check server logs."}
    if not _data_ready:
        return {"status": "warming_up"}
    return {"status": "ok"}


@app.get("/api/config/public")
async def public_config():
    """Public config for the frontend (bot username, etc.)."""
    return {"bot_username": settings.bot_username}


# Serve Mini App frontend (production build)
# Check both local dev path and Docker path
_local_dist = Path(__file__).parent.parent.parent / "webapp" / "dist"
_docker_dist = Path("/webapp/dist")
WEBAPP_DIST = _local_dist if _local_dist.exists() else _docker_dist

# Serve webapp
@app.get("/")
async def serve_root():
    """Serve the React SPA root or API info."""
    if WEBAPP_DIST.exists():
        return FileResponse(
            WEBAPP_DIST / "index.html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
    return {
        "name": "Griffin Gold",
        "version": "1.0.0",
        "status": "running",
        "description": "Gold (XAUUSD) Trading Intelligence Platform",
    }


if WEBAPP_DIST.exists():
    app.mount("/assets", CachedStaticFiles(directory=WEBAPP_DIST / "assets"), name="static")

    # Handle 404s by serving static files or the SPA (for client-side routing)
    @app.exception_handler(StarletteHTTPException)
    async def spa_404_handler(request: Request, exc: StarletteHTTPException):
        """Serve static files from dist root, or SPA for 404s on non-API routes."""
        if exc.status_code == 404 and not request.url.path.startswith("/api"):
            # Try to serve static file from dist root (images, etc.)
            static_file = (WEBAPP_DIST / request.url.path.lstrip("/")).resolve()
            if (
                static_file.exists()
                and static_file.is_file()
                and str(static_file).startswith(str(WEBAPP_DIST.resolve()))
            ):
                return FileResponse(static_file)
            return FileResponse(
                WEBAPP_DIST / "index.html",
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
            )
        # Re-raise the exception for API routes
        raise exc
