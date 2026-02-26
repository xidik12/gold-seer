import logging
from datetime import datetime, timedelta

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.filters.command import CommandObject
from aiogram.types import Message
from sqlalchemy import select, desc

from app.config import settings
from app.database import (
    async_session, BotUser, Prediction, Signal, News,
    PortfolioState, TradeAdvice, TradeResult, Price, ApiKey, ApiUsageLog,
    SupportTicket, MacroData, COTData, EconomicEvent, GoldSessionData,
)
from app.bot.keyboards import main_keyboard, settings_keyboard, back_keyboard, advisor_keyboard, trade_close_keyboard, subscribe_keyboard
from app.bot.subscription import require_premium, is_premium, get_status_text, grant_trial
from app.bot.referral import parse_referral_code, process_referral, get_or_create_referral_code
from app.bot.partner_referral import parse_partner_code, process_partner_referral, try_link_partner_telegram
from app.signals.generator import DISCLAIMER

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    """Handle /start command — subscribe, process referrals, show main menu."""
    is_new = False
    referral_info = None
    partner_info = None

    # Parse start parameter — check for partner_ first, then ref_
    start_param = command.args
    partner_code = parse_partner_code(start_param)
    referral_code = parse_referral_code(start_param) if not partner_code else None

    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = BotUser(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                subscribed=False,
            )
            session.add(user)
            await session.flush()
            is_new = True

            # Grant free trial for new users
            if settings.subscription_enabled:
                await grant_trial(user, session)
            else:
                await session.commit()

            # Process partner referral or user referral for new users only
            if partner_code:
                partner_info = await process_partner_referral(user, partner_code, session)
            elif referral_code:
                referral_info = await process_referral(user, referral_code, session)
        else:
            # Auto-link partner telegram_id if existing user clicks their own partner link
            if partner_code:
                await try_link_partner_telegram(partner_code, message.from_user.id, session)

            # Grant trial to existing users who missed it during beta
            if settings.subscription_enabled:
                await grant_trial(user, session)
            await session.commit()

    # Check if user is banned
    if user.is_banned:
        ban_msg = "Your account has been suspended."
        if user.ban_reason:
            ban_msg += f"\nReason: {user.ban_reason}"
        await message.answer(ban_msg)
        return

    # Build status line
    status_line = ""
    if settings.subscription_enabled:
        status = get_status_text(user)
        if is_new and user.trial_end:
            status_line = f"\n\nYou have {settings.trial_days} days of free Premium access!"
        else:
            status_line = f"\n\nStatus: <b>{status}</b>"

    # Referral bonus message
    referral_line = ""
    if referral_info:
        ref_user = referral_info.get("referrer_username") or "a friend"
        bonus = referral_info["bonus_days"]
        referral_line = f"\n\n🎁 Referred by @{ref_user} — you both got +{bonus} days Premium!"
    elif partner_info:
        referral_line = f"\n\n🤝 Joined via partner: {partner_info['partner_name']}"

    name = message.from_user.first_name or "there"

    await message.answer(
        f"Hey {name}, welcome to <b>Griffin Gold</b>!\n\n"
        "I'm your AI-powered gold (XAUUSD) analyst. I crunch 60+ data points "
        "every hour — macro news, institutional flows, market structure, "
        "central bank moves — and turn them into clear, actionable predictions.\n\n"
        "<b>Here's how to get started:</b>\n"
        "/predict — see the latest gold price predictions\n"
        "/signal — get a trading signal with entry, target & stop-loss\n"
        "/advisor — open the AI trading advisor\n"
        "/news — browse real-time gold & macro news with sentiment\n"
        "/accuracy — check my prediction track record\n"
        "/settings — choose your alert frequency\n\n"
        "Or just tap the buttons below to explore."
        f"{status_line}"
        f"{referral_line}\n\n"
        f"<i>{DISCLAIMER}</i>",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


@router.message(Command("predict"))
@require_premium
async def cmd_predict(message: Message):
    """Handle /predict command — show current prediction."""
    async with async_session() as session:
        result = await session.execute(
            select(Prediction)
            .order_by(desc(Prediction.timestamp))
            .limit(3)
        )
        predictions = result.scalars().all()

    if not predictions:
        await message.answer("⏳ No predictions available yet. Data is being collected...")
        return

    lines = ["🔮 <b>Current Predictions</b>\n"]

    direction_emoji = {"bullish": "🟢 ▲", "bearish": "🔴 ▼", "neutral": "🟡 ◄►"}

    for p in predictions:
        emoji = direction_emoji.get(p.direction, "⚪")
        lines.append(
            f"<b>{p.timeframe.upper()}</b>: {emoji} {p.direction.title()} "
            f"({p.confidence:.0f}% conf)\n"
            f"   Price: ${p.current_price:,.0f}"
        )
        if p.predicted_change_pct:
            lines.append(f"   Expected: {p.predicted_change_pct:+.2f}%")
        lines.append("")

    lines.append(f"<i>{DISCLAIMER}</i>")

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=main_keyboard())


@router.message(Command("signal"))
@require_premium
async def cmd_signal(message: Message):
    """Handle /signal command — show current trading signal."""
    async with async_session() as session:
        result = await session.execute(
            select(Signal)
            .order_by(desc(Signal.timestamp))
            .limit(1)
        )
        signal = result.scalar_one_or_none()

    if not signal:
        await message.answer("⏳ No signals available yet.")
        return

    action_emoji = {
        "strong_buy": "🟢🟢",
        "buy": "🟢",
        "hold": "🟡",
        "sell": "🔴",
        "strong_sell": "🔴🔴",
    }

    emoji = action_emoji.get(signal.action, "⚪")
    risk_bar = "█" * signal.risk_rating + "░" * (10 - signal.risk_rating)

    text = (
        f"📈 <b>Trading Signal ({signal.timeframe.upper()})</b>\n\n"
        f"{emoji} <b>{signal.action.replace('_', ' ').upper()}</b>\n\n"
        f"💰 Entry: <code>${signal.entry_price:,.0f}</code>\n"
        f"🎯 Target: <code>${signal.target_price:,.0f}</code>\n"
        f"🛑 Stop-Loss: <code>${signal.stop_loss:,.0f}</code>\n\n"
        f"📊 Confidence: {signal.confidence:.0f}%\n"
        f"⚠️ Risk: {risk_bar} ({signal.risk_rating}/10)\n\n"
        f"💡 {signal.reasoning}\n\n"
        f"<i>{DISCLAIMER}</i>"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=main_keyboard())


@router.message(Command("news"))
@require_premium
async def cmd_news(message: Message):
    """Handle /news command — show latest news summary."""
    async with async_session() as session:
        result = await session.execute(
            select(News)
            .order_by(desc(News.timestamp))
            .limit(5)
        )
        news = result.scalars().all()

    if not news:
        await message.answer("📰 No news collected yet.")
        return

    lines = ["📰 <b>Latest Gold & Macro News</b>\n"]

    for n in news:
        sentiment = ""
        if n.sentiment_score is not None:
            if n.sentiment_score > 0.1:
                sentiment = "🟢"
            elif n.sentiment_score < -0.1:
                sentiment = "🔴"
            else:
                sentiment = "🟡"

        title = n.title[:80] + "..." if len(n.title) > 80 else n.title
        lines.append(f"{sentiment} {title}")
        lines.append(f"   <i>{n.source}</i>")
        lines.append("")

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=back_keyboard())


@router.message(Command("accuracy"))
@require_premium
async def cmd_accuracy(message: Message):
    """Handle /accuracy command — show prediction track record."""
    async with async_session() as session:
        result = await session.execute(
            select(Prediction).where(Prediction.was_correct.isnot(None))
        )
        predictions = result.scalars().all()

    if not predictions:
        await message.answer("🎯 No evaluated predictions yet. Check back in 24+ hours.")
        return

    total = len(predictions)
    correct = sum(1 for p in predictions if p.was_correct)
    accuracy = correct / total * 100

    # By timeframe
    tf_stats = {}
    for tf in ["1h", "4h", "24h"]:
        tf_preds = [p for p in predictions if p.timeframe == tf]
        tf_correct = sum(1 for p in tf_preds if p.was_correct)
        tf_total = len(tf_preds)
        if tf_total > 0:
            tf_stats[tf] = f"{tf_correct}/{tf_total} ({tf_correct / tf_total * 100:.0f}%)"

    text = (
        f"🎯 <b>Prediction Accuracy</b>\n\n"
        f"Overall: <b>{correct}/{total} ({accuracy:.1f}%)</b>\n\n"
    )

    for tf, stat in tf_stats.items():
        text += f"  {tf.upper()}: {stat}\n"

    text += f"\n<i>Based on {total} evaluated predictions</i>"

    await message.answer(text, parse_mode="HTML", reply_markup=back_keyboard())


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Handle /settings command — alert preferences."""
    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

    interval = user.alert_interval if user else "1h"

    await message.answer(
        "⚙️ <b>Alert Settings</b>\n\n"
        "Choose how often you want to receive prediction alerts:",
        parse_mode="HTML",
        reply_markup=settings_keyboard(interval),
    )


# ────────────────────────────────────────────────────────────────
#  ADVISOR COMMANDS
# ────────────────────────────────────────────────────────────────

@router.message(Command("advisor"))
@require_premium
async def cmd_advisor(message: Message):
    """Show advisor status, balance, open trades, and $10K progress."""
    from app.advisor.portfolio import get_or_create_portfolio, get_stats

    telegram_id = message.from_user.id
    portfolio = await get_or_create_portfolio(telegram_id)
    stats = await get_stats(telegram_id)

    # Open trades count
    async with async_session() as session:
        result = await session.execute(
            select(TradeAdvice).where(
                TradeAdvice.telegram_id == telegram_id,
                TradeAdvice.status.in_(["opened", "partial_tp"]),
            )
        )
        open_trades = result.scalars().all()

    # Progress bar
    progress = stats.get("progress_to_10k", 0)
    bar_filled = int(progress / 5)  # 20 chars total
    bar = "█" * bar_filled + "░" * (20 - bar_filled)

    cooldown = ""
    if stats.get("cooldown_until"):
        cooldown = f"\nCooldown active until {stats['cooldown_until']}"

    text = (
        f"<b>Trading Advisor</b>\n\n"
        f"<b>Balance:</b> ${stats['balance']:.2f}\n"
        f"<b>Total PnL:</b> ${stats['total_pnl']:+.2f} ({stats['total_pnl_pct']:+.1f}%)\n\n"
        f"<b>Trades:</b> {stats['total_trades']} total | "
        f"{stats['winning_trades']}W / {stats['losing_trades']}L\n"
        f"<b>Win Rate:</b> {stats['win_rate']:.1f}%\n"
        f"<b>Profit Factor:</b> {stats['profit_factor']:.2f}\n\n"
        f"<b>Open Trades:</b> {len(open_trades)}\n"
        f"<b>Streak:</b> {stats['consecutive_wins']}W / {stats['consecutive_losses']}L\n\n"
        f"<b>$10K Progress:</b> {progress:.1f}%\n"
        f"[{bar}]\n"
        f"${stats['balance']:.2f} / $10,000.00"
        f"{cooldown}"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=advisor_keyboard())


@router.message(Command("balance"))
@require_premium
async def cmd_balance(message: Message):
    """Show balance and PnL summary."""
    from app.advisor.portfolio import get_or_create_portfolio, get_stats

    telegram_id = message.from_user.id
    stats = await get_stats(telegram_id)

    if stats.get("error"):
        await get_or_create_portfolio(telegram_id)
        stats = await get_stats(telegram_id)

    text = (
        f"<b>Portfolio Balance</b>\n\n"
        f"Balance: <code>${stats['balance']:.4f}</code>\n"
        f"Initial: <code>${stats['initial_balance']:.2f}</code>\n\n"
        f"Total PnL: <code>${stats['total_pnl']:+.4f}</code>\n"
        f"Total PnL %: <code>{stats['total_pnl_pct']:+.2f}%</code>\n\n"
        f"Best Trade: <code>${stats.get('best_trade', 0):+.4f}</code>\n"
        f"Worst Trade: <code>${stats.get('worst_trade', 0):+.4f}</code>\n"
        f"Avg Win: <code>${stats.get('avg_win', 0):+.4f}</code>\n"
        f"Avg Loss: <code>${stats.get('avg_loss', 0):+.4f}</code>"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=back_keyboard())


@router.message(Command("setbalance"))
@require_premium
async def cmd_setbalance(message: Message):
    """Set balance manually: /setbalance <amount>"""
    from app.advisor.portfolio import update_balance

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /setbalance <amount>\nExample: /setbalance 25.50")
        return

    try:
        amount = float(parts[1])
    except ValueError:
        await message.answer("Invalid amount. Use a number like: /setbalance 25.50")
        return

    if amount < 0:
        await message.answer("Amount must be positive.")
        return

    portfolio = await update_balance(message.from_user.id, amount)

    await message.answer(
        f"Balance updated to <code>${portfolio.balance_usdt:.4f}</code>",
        parse_mode="HTML",
        reply_markup=back_keyboard(),
    )


@router.message(Command("trades"))
@require_premium
async def cmd_trades(message: Message):
    """Show open trade advices with current status."""
    telegram_id = message.from_user.id

    async with async_session() as session:
        result = await session.execute(
            select(TradeAdvice).where(
                TradeAdvice.telegram_id == telegram_id,
                TradeAdvice.status.in_(["pending", "opened", "partial_tp"]),
            ).order_by(desc(TradeAdvice.timestamp))
        )
        trades = result.scalars().all()

        # Get current price
        result = await session.execute(
            select(Price).order_by(desc(Price.timestamp)).limit(1)
        )
        price_row = result.scalar_one_or_none()

    if not trades:
        await message.answer("No open trades.", reply_markup=advisor_keyboard())
        return

    current_price = price_row.close if price_row else 0

    lines = ["<b>Open Trades</b>\n"]
    for t in trades:
        if t.direction == "LONG":
            pnl_pct = ((current_price - t.entry_price) / t.entry_price * 100) * t.leverage
        else:
            pnl_pct = ((t.entry_price - current_price) / t.entry_price * 100) * t.leverage

        emoji = "🟢" if pnl_pct >= 0 else "🔴"
        lines.append(
            f"#{t.id} {t.direction} {t.leverage}x | {t.status}\n"
            f"   Entry: ${t.entry_price:,.0f} | Now: ${current_price:,.0f}\n"
            f"   {emoji} PnL: {pnl_pct:+.2f}%\n"
            f"   SL: ${t.stop_loss:,.0f} | TP1: ${t.take_profit_1:,.0f}\n"
        )

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=advisor_keyboard())


@router.message(Command("history"))
@require_premium
async def cmd_history(message: Message):
    """Show trade result history with W/L stats."""
    telegram_id = message.from_user.id

    async with async_session() as session:
        result = await session.execute(
            select(TradeResult)
            .where(TradeResult.telegram_id == telegram_id)
            .order_by(desc(TradeResult.timestamp))
            .limit(10)
        )
        results = result.scalars().all()

    if not results:
        await message.answer("No trade history yet.", reply_markup=advisor_keyboard())
        return

    lines = ["<b>Trade History (last 10)</b>\n"]
    for r in results:
        emoji = "✅" if r.was_winner else "❌"
        lines.append(
            f"{emoji} #{r.trade_advice_id} {r.direction} {r.leverage}x\n"
            f"   ${r.entry_price:,.0f} -> ${r.exit_price:,.0f}\n"
            f"   PnL: ${r.pnl_usdt:+.4f} ({r.pnl_pct_leveraged:+.2f}%)\n"
            f"   {r.close_reason} | {r.duration_minutes}min\n"
        )

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=advisor_keyboard())


# ────────────────────────────────────────────────────────────────
#  API KEY COMMANDS
# ────────────────────────────────────────────────────────────────

@router.message(Command("apikey"))
async def cmd_apikey(message: Message):
    """Generate a free-tier API key for the user."""
    import secrets
    from app.middleware.auth import hash_api_key
    from sqlalchemy import func

    telegram_id = message.from_user.id

    async with async_session() as session:
        # Check if user already has an active key
        result = await session.execute(
            select(ApiKey).where(
                ApiKey.telegram_id == telegram_id,
                ApiKey.is_active == True,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            await message.answer(
                f"<b>Your API Key</b>\n\n"
                f"Prefix: <code>{existing.key_prefix}...</code>\n"
                f"Tier: <b>{existing.tier}</b>\n"
                f"Rate limit: {existing.rate_limit} req/hr\n\n"
                "<i>You already have an active key. Use /revokekey to revoke and generate a new one.</i>",
                parse_mode="HTML",
            )
            return

        # Generate new key
        raw_key = f"bto_{secrets.token_urlsafe(32)}"
        key_hash = hash_api_key(raw_key)
        key_prefix = raw_key[:12]

        api_key = ApiKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            owner=message.from_user.username or str(telegram_id),
            telegram_id=telegram_id,
            tier="free",
            rate_limit=60,
            is_active=True,
        )
        session.add(api_key)
        await session.commit()

    await message.answer(
        f"<b>Your API Key (FREE tier)</b>\n\n"
        f"<code>{raw_key}</code>\n\n"
        f"Rate limit: 60 requests/hour\n"
        f"Endpoints: Price, Power Law\n\n"
        f"Use with:\n"
        f"<code>curl -H 'X-API-Key: {raw_key}' https://your-domain/api/v1/price</code>\n\n"
        f"<b>Save this key now!</b> It won't be shown again.",
        parse_mode="HTML",
    )


@router.message(Command("revokekey"))
async def cmd_revokekey(message: Message):
    """Revoke the user's active API key."""
    telegram_id = message.from_user.id

    async with async_session() as session:
        result = await session.execute(
            select(ApiKey).where(
                ApiKey.telegram_id == telegram_id,
                ApiKey.is_active == True,
            )
        )
        key = result.scalar_one_or_none()

        if not key:
            await message.answer("You don't have an active API key. Use /apikey to generate one.")
            return

        key.is_active = False
        await session.commit()

    await message.answer(
        "API key revoked. Use /apikey to generate a new one.",
        parse_mode="HTML",
    )


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    """Show subscription tier options."""
    if not settings.subscription_enabled:
        await message.answer(
            "All features are currently <b>free</b> during beta!",
            parse_mode="HTML",
        )
        return

    # Check current status
    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

    status = get_status_text(user) if user else "Free"

    from app.bot.keyboards import subscription_tiers_keyboard

    await message.answer(
        "<b>Griffin Gold Premium</b>\n\n"
        "Unlock AI gold predictions, trading signals, advisor & alerts.\n\n"
        f"Current status: <b>{status}</b>\n\n"
        "Choose your plan:",
        parse_mode="HTML",
        reply_markup=subscription_tiers_keyboard(),
    )


@router.message(Command("usage"))
async def cmd_usage(message: Message):
    """Show API usage stats for the user's key."""
    from sqlalchemy import func
    from datetime import timedelta

    telegram_id = message.from_user.id

    async with async_session() as session:
        result = await session.execute(
            select(ApiKey).where(
                ApiKey.telegram_id == telegram_id,
                ApiKey.is_active == True,
            )
        )
        key = result.scalar_one_or_none()

        if not key:
            await message.answer("No active API key. Use /apikey to generate one.")
            return

        # Count usage
        from datetime import datetime
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        day_ago = datetime.utcnow() - timedelta(hours=24)

        result_1h = await session.execute(
            select(func.count(ApiUsageLog.id))
            .where(ApiUsageLog.api_key_id == key.id)
            .where(ApiUsageLog.timestamp >= hour_ago)
        )
        result_24h = await session.execute(
            select(func.count(ApiUsageLog.id))
            .where(ApiUsageLog.api_key_id == key.id)
            .where(ApiUsageLog.timestamp >= day_ago)
        )
        result_total = await session.execute(
            select(func.count(ApiUsageLog.id))
            .where(ApiUsageLog.api_key_id == key.id)
        )

    requests_1h = result_1h.scalar() or 0
    requests_24h = result_24h.scalar() or 0
    requests_total = result_total.scalar() or 0

    await message.answer(
        f"<b>API Usage Stats</b>\n\n"
        f"Tier: <b>{key.tier}</b>\n"
        f"Rate limit: {key.rate_limit} req/hr\n\n"
        f"Last hour: {requests_1h}/{key.rate_limit}\n"
        f"Last 24h: {requests_24h}\n"
        f"All time: {requests_total}\n\n"
        f"Key prefix: <code>{key.key_prefix}...</code>",
        parse_mode="HTML",
    )


@router.message(Command("close"))
@require_premium
async def cmd_close(message: Message):
    """Record trade close: /close <trade_id> <exit_price>"""
    from app.advisor.portfolio import record_trade_result

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Usage: /close <trade_id> <exit_price>\nExample: /close 5 98500")
        return

    try:
        trade_id = int(parts[1])
        exit_price = float(parts[2])
    except ValueError:
        await message.answer("Invalid arguments. Example: /close 5 98500")
        return

    result = await record_trade_result(
        telegram_id=message.from_user.id,
        trade_id=trade_id,
        exit_price=exit_price,
        reason="manual_close",
    )

    if not result:
        await message.answer("Trade not found or already closed.")
        return

    emoji = "✅" if result.was_winner else "❌"
    text = (
        f"{emoji} <b>Trade #{trade_id} Closed</b>\n\n"
        f"PnL: <code>${result.pnl_usdt:+.4f}</code> ({result.pnl_pct_leveraged:+.2f}%)\n"
        f"Balance: ${result.balance_before:.4f} -> ${result.balance_after:.4f}"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=advisor_keyboard())


# ────────────────────────────────────────────────────────────────
#  REFERRAL COMMAND
# ────────────────────────────────────────────────────────────────

@router.message(Command("referral"))
@require_premium
async def cmd_referral(message: Message):
    """Show user's referral link."""
    async with async_session() as session:
        result = await session.execute(
            select(BotUser).where(BotUser.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("Please use /start first.")
            return
        code = await get_or_create_referral_code(user, session)
    link = f"https://t.me/{settings.bot_username}?start=ref_{code}"
    await message.answer(
        f"Your referral link:\n<code>{link}</code>\n\n"
        f"Share it -- you both get +{settings.referral_bonus_days} days Premium!\n"
        f"Total referrals: {user.referral_count or 0}",
        parse_mode="HTML",
    )


# ────────────────────────────────────────────────────────────────
#  FAQ & SUPPORT COMMANDS
# ────────────────────────────────────────────────────────────────

FAQ_ANSWERS = {
    "what_is": (
        "<b>What is Griffin Gold?</b>\n\n"
        "Griffin Gold is an AI-powered gold (XAUUSD) trading intelligence platform. We analyze 60+ market signals "
        "every hour — macro news sentiment, institutional flows, central bank activity, technical indicators, "
        "and economic data — to generate price predictions and trading signals.\n\n"
        "Try /predict to see our latest prediction."
    ),
    "accuracy": (
        "<b>How accurate is Griffin Gold?</b>\n\n"
        "Our AI tracks its own accuracy transparently. Use /accuracy to see our real-time "
        "track record broken down by timeframe (1h, 4h, 24h).\n\n"
        "We're honest about both wins and misses — that's what sets us apart."
    ),
    "subscribe": (
        "<b>How to subscribe?</b>\n\n"
        "Use /subscribe to see our Premium plans. We accept Telegram Stars.\n\n"
        "Plans: Monthly, 3 Months (save 17%), or Yearly (save 25%).\n"
        "All plans include: AI predictions, trading signals, advisor, alerts, and priority support."
    ),
    "trial": (
        "<b>Free trial</b>\n\n"
        "Every new user gets a 7-day free trial of Premium features. "
        "No payment required — just /start the bot and you're in.\n\n"
        "After the trial, you can subscribe or continue with limited free features."
    ),
    "advisor": (
        "<b>AI Trading Advisor</b>\n\n"
        "The advisor generates trade plans with entry, target, and stop-loss levels. "
        "It manages risk automatically (position sizing, leverage, daily loss limits).\n\n"
        "Start with /advisor to see your portfolio and open trades."
    ),
    "data": (
        "<b>Data sources</b>\n\n"
        "Griffin Gold processes data from:\n"
        "\u2022 GoldAPI / Oanda (real-time XAUUSD price & volume)\n"
        "\u2022 FRED / central bank feeds (interest rates, CPI, NFP)\n"
        "\u2022 News APIs (macro news, RSS feeds)\n"
        "\u2022 Institutional flow data (ETF flows, COMEX, COT reports)\n"
        "\u2022 Social sentiment (Twitter influencers, Reddit)\n"
        "\u2022 Macro indicators (DXY, US yields, S&P 500, VIX)"
    ),
    "referral": (
        "<b>Referral program</b>\n\n"
        "Share your referral link and both you and your friend get +7 days of Premium!\n\n"
        "Use /referral to get your unique link. No limit on referrals."
    ),
    "disclaimer": (
        "<b>Not financial advice</b>\n\n"
        "Griffin Gold is for educational and informational purposes only. "
        "Our predictions and signals are not financial advice. "
        "Always do your own research and never invest more than you can afford to lose.\n\n"
        "Past performance does not guarantee future results."
    ),
}


@router.message(Command("faq"))
async def cmd_faq(message: Message):
    """Show FAQ topics."""
    from app.bot.keyboards import faq_keyboard
    await message.answer(
        "<b>Frequently Asked Questions</b>\n\n"
        "Tap a topic below to learn more:",
        parse_mode="HTML",
        reply_markup=faq_keyboard(),
    )


@router.message(Command("report"))
async def cmd_report(message: Message):
    """Create a support ticket: /report <description>"""
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "Usage: /report <description>\n\n"
            "Example: /report Predictions not loading after update\n\n"
            "Our team will review your report and follow up.",
        )
        return

    description = parts[1].strip()

    async with async_session() as session:
        from app.database import SupportTicket
        ticket = SupportTicket(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            category="bug",
            description=description,
        )
        session.add(ticket)
        await session.flush()
        ticket_id = ticket.id
        await session.commit()

    # Notify admin
    if settings.admin_telegram_id:
        try:
            from aiogram import Bot
            bot = Bot(token=settings.telegram_bot_token)
            await bot.send_message(
                settings.admin_telegram_id,
                f"\U0001f3ab <b>New Support Ticket #{ticket_id}</b>\n\n"
                f"From: @{message.from_user.username or 'unknown'} ({message.from_user.id})\n"
                f"Description: {description[:500]}",
                parse_mode="HTML",
            )
            await bot.session.close()
        except Exception as e:
            logger.error(f"Failed to notify admin about ticket: {e}")

    await message.answer(
        f"\u2705 <b>Ticket #{ticket_id} created</b>\n\n"
        f"We've received your report and will look into it.\n"
        f"You'll be notified when there's an update.",
        parse_mode="HTML",
        reply_markup=main_keyboard(),
    )


# ────────────────────────────────────────────────────────────────
#  GOLD-SPECIFIC MARKET COMMANDS
# ────────────────────────────────────────────────────────────────


@router.message(Command("alert"))
@require_premium
async def cmd_alert(message: Message):
    """Manage price alerts: /alert [price] [above|below] [repeat]"""
    from app.database import PriceAlert
    from app.bot.keyboards import alert_list_keyboard

    telegram_id = message.from_user.id
    parts = (message.text or "").split()

    # /alert with no args — show active alerts
    if len(parts) <= 1:
        async with async_session() as session:
            result = await session.execute(
                select(PriceAlert)
                .where(PriceAlert.telegram_id == telegram_id, PriceAlert.is_active == True)
                .order_by(desc(PriceAlert.created_at))
            )
            alerts = result.scalars().all()

        if not alerts:
            await message.answer(
                "🔔 <b>Price Alerts</b>\n\nNo active alerts.\n\n"
                "Create one:\n<code>/alert 100000 above</code>\n<code>/alert 90000 below repeat</code>",
                parse_mode="HTML",
                reply_markup=back_keyboard(),
            )
            return

        lines = ["🔔 <b>Active Price Alerts</b>\n"]
        for a in alerts:
            emoji = "📈" if a.direction == "above" else "📉"
            repeat = " 🔄" if a.is_repeating else ""
            lines.append(f"{emoji} {a.asset_id.upper()[:6]} {'above' if a.direction == 'above' else 'below'} ${a.target_price:,.0f}{repeat}")

        await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=alert_list_keyboard(alerts))
        return

    # /alert <price> <direction> [repeat]
    try:
        target_price = float(parts[1].replace(",", ""))
    except ValueError:
        await message.answer("Usage: /alert <price> <above|below> [repeat]")
        return

    direction = parts[2].lower() if len(parts) > 2 else "above"
    if direction not in ("above", "below"):
        await message.answer("Direction must be 'above' or 'below'")
        return

    is_repeating = "repeat" in (p.lower() for p in parts[3:])

    async with async_session() as session:
        from sqlalchemy import func as sqlfunc
        result = await session.execute(
            select(sqlfunc.count(PriceAlert.id))
            .where(PriceAlert.telegram_id == telegram_id, PriceAlert.is_active == True)
        )
        count = result.scalar() or 0
        if count >= 10:
            await message.answer("You have 10 active alerts (max). Delete one first.")
            return

        alert = PriceAlert(
            telegram_id=telegram_id,
            target_price=target_price,
            direction=direction,
            is_repeating=is_repeating,
        )
        session.add(alert)
        await session.commit()

    repeat_label = " (repeating)" if is_repeating else ""
    await message.answer(
        f"✅ Alert created: Gold {'above' if direction == 'above' else 'below'} ${target_price:,.2f}{repeat_label}",
        parse_mode="HTML",
        reply_markup=back_keyboard(),
    )


@router.message(Command("game"))
async def cmd_game(message: Message):
    """Prediction game: /game to play or see status."""
    from app.database import UserPrediction, GameProfile
    from app.bot.keyboards import game_keyboard

    telegram_id = message.from_user.id
    today = datetime.utcnow().strftime("%Y-%m-%d")

    async with async_session() as session:
        # Check for existing prediction today
        result = await session.execute(
            select(UserPrediction).where(
                UserPrediction.telegram_id == telegram_id,
                UserPrediction.round_date == today,
                UserPrediction.timeframe == "24h",
                UserPrediction.status == "pending",
            )
        )
        current = result.scalar_one_or_none()

        # Get profile
        result = await session.execute(
            select(GameProfile).where(GameProfile.telegram_id == telegram_id)
        )
        profile = result.scalar_one_or_none()

        # Get current price
        result = await session.execute(
            select(Price).order_by(desc(Price.timestamp)).limit(1)
        )
        price_row = result.scalar_one_or_none()
        gold_price = price_row.close if price_row else 0

    if current:
        emoji = "🟢" if current.direction == "up" else "🔴"
        text = (
            f"🎮 <b>Prediction Game</b>\n\n"
            f"Today's prediction: {emoji} <b>{current.direction.upper()}</b>\n"
            f"Lock price: ${current.lock_price:,.2f}\n"
            f"Current: ${gold_price:,.2f}\n\n"
        )
    else:
        text = (
            f"🎮 <b>Prediction Game</b>\n\n"
            f"XAUUSD: <b>${gold_price:,.2f}</b>\n\n"
            f"Will Gold go UP or DOWN in the next 24h?\n"
            f"Tap below to make your prediction!\n\n"
        )

    if profile:
        streak_emoji = "🔥" if profile.current_streak >= 3 else ""
        text += (
            f"📊 Points: <b>{profile.total_points}</b> | "
            f"Streak: <b>{profile.current_streak}</b> {streak_emoji}\n"
            f"Accuracy: {profile.accuracy_pct:.0f}% ({profile.correct_predictions}/{profile.total_predictions})"
        )

    await message.answer(text, parse_mode="HTML", reply_markup=game_keyboard())


@router.message(Command("macro"))
@require_premium
async def cmd_macro(message: Message):
    """Show current macro dashboard — gold, DXY, yields, VIX, silver."""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(MacroData)
                .order_by(desc(MacroData.timestamp))
                .limit(1)
            )
            macro = result.scalar_one_or_none()

        if not macro:
            await message.answer(
                "⏳ No macro data available yet. Data is being collected...",
                reply_markup=back_keyboard(),
            )
            return

        # Gold/silver ratio
        gs_ratio = ""
        if macro.gold and macro.silver and macro.silver > 0:
            ratio = macro.gold / macro.silver
            gs_ratio = f"\n⚖️ Gold/Silver Ratio: <b>{ratio:.1f}</b>"

        # Format optional values
        gold_line = f"💰 Gold: <b>${macro.gold:,.2f}</b>" if macro.gold else "💰 Gold: N/A"
        dxy_line = f"💵 DXY: <b>{macro.dxy:.2f}</b>" if macro.dxy else "💵 DXY: N/A"
        yield_line = f"📊 10Y Yield: <b>{macro.treasury_10y:.2f}%</b>" if macro.treasury_10y else "📊 10Y Yield: N/A"
        vix_line = f"📈 VIX: <b>{macro.vix:.1f}</b>" if macro.vix else "📈 VIX: N/A"
        silver_line = f"🥈 Silver: <b>${macro.silver:.2f}</b>" if macro.silver else "🥈 Silver: N/A"

        # Extra context
        extras = []
        if macro.sp500:
            extras.append(f"📉 S&P 500: {macro.sp500:,.0f}")
        if macro.wti_oil:
            extras.append(f"🛢️ WTI Oil: ${macro.wti_oil:.2f}")
        if macro.eurusd:
            extras.append(f"💱 EUR/USD: {macro.eurusd:.4f}")
        extras_text = "\n".join(extras)
        if extras_text:
            extras_text = f"\n\n{extras_text}"

        age = datetime.utcnow() - macro.timestamp
        age_minutes = int(age.total_seconds() / 60)
        if age_minutes < 60:
            age_text = f"{age_minutes}m ago"
        else:
            age_text = f"{age_minutes // 60}h {age_minutes % 60}m ago"

        text = (
            f"🌍 <b>Macro Dashboard</b>\n\n"
            f"{gold_line}\n"
            f"{dxy_line}\n"
            f"{yield_line}\n"
            f"{vix_line}\n"
            f"{silver_line}"
            f"{gs_ratio}"
            f"{extras_text}\n\n"
            f"<i>Updated {age_text}</i>"
        )

        await message.answer(text, parse_mode="HTML", reply_markup=back_keyboard())

    except Exception as e:
        logger.error(f"cmd_macro error: {e}", exc_info=True)
        await message.answer("Failed to fetch macro data. Try again later.")


@router.message(Command("cot"))
@require_premium
async def cmd_cot(message: Message):
    """Show latest COT (Commitments of Traders) positioning data."""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(COTData)
                .order_by(desc(COTData.report_date))
                .limit(1)
            )
            cot = result.scalar_one_or_none()

        if not cot:
            await message.answer(
                "⏳ No COT data available yet. CFTC data is collected weekly.",
                reply_markup=back_keyboard(),
            )
            return

        # Signal interpretation
        if cot.mm_net is not None:
            if cot.mm_net > 0:
                signal = "🟢 Managed Money NET LONG — bullish positioning"
            elif cot.mm_net < 0:
                signal = "🔴 Managed Money NET SHORT — bearish positioning"
            else:
                signal = "🟡 Managed Money FLAT — neutral positioning"
        else:
            signal = "⚪ Positioning data unavailable"

        # Format values with fallbacks
        mm_long = f"{cot.mm_long:,}" if cot.mm_long is not None else "N/A"
        mm_short = f"{cot.mm_short:,}" if cot.mm_short is not None else "N/A"
        mm_net_val = f"{cot.mm_net:+,}" if cot.mm_net is not None else "N/A"
        mm_change = f" ({cot.mm_net_change:+,} chg)" if cot.mm_net_change is not None else ""

        comm_long = f"{cot.commercial_long:,}" if cot.commercial_long is not None else "N/A"
        comm_short = f"{cot.commercial_short:,}" if cot.commercial_short is not None else "N/A"
        comm_net_val = f"{cot.commercial_net:+,}" if cot.commercial_net is not None else "N/A"

        oi_val = f"{cot.open_interest:,}" if cot.open_interest is not None else "N/A"
        oi_change = f" ({cot.oi_change:+,})" if cot.oi_change is not None else ""

        # Percentile info
        percentile_text = ""
        if cot.mm_net_percentile is not None:
            percentile_text += f"\n📏 MM Net Percentile (3yr): {cot.mm_net_percentile:.0f}%"
        if cot.oi_percentile is not None:
            percentile_text += f"\n📏 OI Percentile (3yr): {cot.oi_percentile:.0f}%"

        report_date = cot.report_date.strftime("%b %d, %Y")

        text = (
            f"📋 <b>COT Report — Gold (COMEX)</b>\n"
            f"<i>Report date: {report_date}</i>\n\n"
            f"<b>Managed Money (Hedge Funds)</b>\n"
            f"  Long: {mm_long} | Short: {mm_short}\n"
            f"  Net: <b>{mm_net_val}</b>{mm_change}\n\n"
            f"<b>Commercials (Producers)</b>\n"
            f"  Long: {comm_long} | Short: {comm_short}\n"
            f"  Net: <b>{comm_net_val}</b>\n\n"
            f"<b>Open Interest:</b> {oi_val}{oi_change}"
            f"{percentile_text}\n\n"
            f"{signal}"
        )

        await message.answer(text, parse_mode="HTML", reply_markup=back_keyboard())

    except Exception as e:
        logger.error(f"cmd_cot error: {e}", exc_info=True)
        await message.answer("Failed to fetch COT data. Try again later.")


@router.message(Command("calendar"))
@require_premium
async def cmd_calendar(message: Message):
    """Show upcoming high-impact economic events."""
    try:
        now = datetime.utcnow()

        async with async_session() as session:
            # Get upcoming events (today and future), prioritize high impact
            result = await session.execute(
                select(EconomicEvent)
                .where(EconomicEvent.event_date >= now - timedelta(hours=6))
                .order_by(EconomicEvent.event_date)
                .limit(20)
            )
            events = result.scalars().all()

        if not events:
            await message.answer(
                "📅 <b>Economic Calendar</b>\n\nNo upcoming events found.",
                parse_mode="HTML",
                reply_markup=back_keyboard(),
            )
            return

        # Filter to show high/medium impact first, cap at 10
        high = [e for e in events if e.importance == "high"]
        medium = [e for e in events if e.importance == "medium"]
        low = [e for e in events if e.importance == "low"]
        sorted_events = (high + medium + low)[:10]

        lines = ["📅 <b>Economic Calendar</b>\n"]

        impact_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}

        for e in sorted_events:
            emoji = impact_emoji.get(e.importance, "⚪")
            date_str = e.event_date.strftime("%b %d %H:%M")
            country = f"[{e.country}]" if e.country else ""

            line = f"{emoji} <b>{date_str}</b> {country}\n   {e.event_name}"

            # Show forecast/previous if available
            details = []
            if e.forecast:
                details.append(f"Exp: {e.forecast}")
            if e.previous:
                details.append(f"Prev: {e.previous}")
            if e.actual:
                details.append(f"Act: {e.actual}")
            if details:
                line += f"\n   <i>{' | '.join(details)}</i>"

            lines.append(line)
            lines.append("")

        lines.append("🔴 High  🟡 Medium  🟢 Low impact")

        await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=back_keyboard())

    except Exception as e:
        logger.error(f"cmd_calendar error: {e}", exc_info=True)
        await message.answer("Failed to fetch calendar data. Try again later.")


@router.message(Command("sessions"))
@require_premium
async def cmd_sessions(message: Message):
    """Show current trading session info (Asian/London/NY)."""
    try:
        now = datetime.utcnow()
        hour = now.hour

        # Determine active sessions based on UTC time
        # Asian:  00:00 - 08:00 UTC
        # London: 08:00 - 16:00 UTC
        # NY:     13:00 - 21:00 UTC
        # Overlap (London/NY): 13:00 - 16:00 UTC

        active_sessions = []
        if 0 <= hour < 8:
            active_sessions.append(("🌏 Asian", "asian", 8 - hour))
        if 8 <= hour < 16:
            active_sessions.append(("🇬🇧 London", "london", 16 - hour))
        if 13 <= hour < 21:
            active_sessions.append(("🇺🇸 New York", "new_york", 21 - hour))

        # Check for overlap
        is_overlap = 13 <= hour < 16

        if not active_sessions:
            # After 21:00 UTC — markets winding down, Asian opens at midnight
            hours_to_asian = (24 - hour) % 24
            active_sessions.append(("💤 Off-Hours", "off", hours_to_asian))

        # Volatility expectations
        volatility_map = {
            "asian": "Low",
            "london": "Medium-High",
            "new_york": "High",
            "off": "Very Low",
        }

        lines = [
            f"🕐 <b>Trading Sessions</b>\n"
            f"<i>UTC: {now.strftime('%H:%M')}</i>\n"
        ]

        if is_overlap:
            lines.append("⚡ <b>London/NY Overlap — Peak Volatility</b>\n")

        for label, key, hours_left in active_sessions:
            vol = volatility_map.get(key, "Unknown")
            minutes_left = hours_left * 60 - now.minute
            h, m = divmod(minutes_left, 60)
            time_str = f"{h}h {m}m" if h > 0 else f"{m}m"

            lines.append(
                f"{label}\n"
                f"   ⏳ Closes in: {time_str}\n"
                f"   📊 Typical volatility: <b>{vol}</b>"
            )

        # Try to get today's session data from DB
        today = now.strftime("%Y-%m-%d")
        async with async_session() as session:
            result = await session.execute(
                select(GoldSessionData)
                .where(GoldSessionData.date == today)
                .order_by(desc(GoldSessionData.session_start))
            )
            session_data = result.scalars().all()

        if session_data:
            lines.append("\n<b>Today's Session Stats</b>")
            for sd in session_data:
                dir_emoji = {"up": "🟢", "down": "🔴", "flat": "🟡"}.get(sd.direction, "⚪")
                name = sd.session_name.replace("_", " ").title()
                range_text = f" | Range: ${sd.range_usd:.0f}" if sd.range_usd else ""
                lines.append(
                    f"  {dir_emoji} {name}: ${sd.open_price:,.0f} → "
                    f"${sd.close_price:,.0f}{range_text}" if sd.close_price else
                    f"  {dir_emoji} {name}: ${sd.open_price:,.0f} (active)"
                )

        await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=back_keyboard())

    except Exception as e:
        logger.error(f"cmd_sessions error: {e}", exc_info=True)
        await message.answer("Failed to fetch session data. Try again later.")
