import logging
from datetime import datetime

from aiogram import Bot
from sqlalchemy import select, or_, and_, desc

from app.database import async_session, BotUser, Price, Prediction, Signal, AlertLog, PriceAlert, DailyBriefing
from app.config import settings
from app.signals.generator import DISCLAIMER
from app.bot.subscription import is_premium

logger = logging.getLogger(__name__)

# Track which intervals have been sent this cycle
_last_sent: dict[str, datetime] = {}


class AlertSender:
    """Sends prediction alerts to subscribed Telegram users."""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def _log_alert(self, telegram_id: int, alert_type: str, status: str, error: str = None):
        """Log an alert send attempt to the database."""
        try:
            async with async_session() as session:
                log = AlertLog(
                    timestamp=datetime.utcnow(),
                    telegram_id=telegram_id,
                    alert_type=alert_type,
                    status=status,
                    error=error,
                )
                session.add(log)
                await session.commit()
        except Exception as e:
            logger.debug(f"Failed to log alert: {e}")

    async def send_alerts(self):
        """Send prediction alerts to subscribed users based on their chosen interval.

        Called every hour. Determines which intervals are due and sends accordingly:
        - 1h: every call
        - 4h: every 4th call (hours 0, 4, 8, 12, 16, 20 UTC)
        - 24h: once daily (hour 0 UTC)
        """
        now = datetime.utcnow()
        current_hour = now.hour

        # Determine which intervals are due this hour
        due_intervals = ["1h"]
        if current_hour % 4 == 0:
            due_intervals.append("4h")
        if current_hour == 0:
            due_intervals.append("24h")

        async with async_session() as session:
            # Get current price
            price_result = await session.execute(
                select(Price).order_by(desc(Price.timestamp)).limit(1)
            )
            current_price_row = price_result.scalar_one_or_none()

            # Get latest prediction for each timeframe
            predictions_by_tf = {}
            for tf in ["1h", "4h", "24h"]:
                result = await session.execute(
                    select(Prediction)
                    .where(Prediction.timeframe == tf)
                    .order_by(desc(Prediction.timestamp))
                    .limit(1)
                )
                pred = result.scalar_one_or_none()
                if pred:
                    predictions_by_tf[tf] = pred

            # Get latest signal
            result = await session.execute(
                select(Signal).order_by(desc(Signal.timestamp)).limit(1)
            )
            signal = result.scalar_one_or_none()

            if not predictions_by_tf:
                logger.warning("No predictions available for alerts")
                return

            # Get subscribed users whose interval is due, filtered by premium status
            query = (
                select(BotUser)
                .where(BotUser.subscribed == True)
                .where(BotUser.alert_interval.in_(due_intervals))
            )
            # When subscription is enabled, filter premium users in SQL
            if settings.subscription_enabled:
                now = datetime.utcnow()
                query = query.where(
                    or_(
                        and_(
                            BotUser.subscription_tier == "premium",
                            BotUser.subscription_end > now,
                        ),
                        BotUser.trial_end > now,
                    )
                )
            result = await session.execute(query)
            users = result.scalars().all()

        if not users:
            logger.info(f"No users due for alerts (intervals: {due_intervals})")
            return

        logger.info(f"Sending alerts to {len(users)} users (intervals: {due_intervals})")

        current_price = current_price_row.close if current_price_row else None
        predictions = list(predictions_by_tf.values())
        message = self._format_alert(predictions, signal, current_price)

        sent = 0
        failed = 0
        for user in users:
            try:
                await self.bot.send_message(
                    user.telegram_id,
                    message,
                    parse_mode="HTML",
                )
                sent += 1
                await self._log_alert(user.telegram_id, f"alert_{user.alert_interval}", "sent")
            except Exception as e:
                logger.error(f"Failed to send alert to {user.telegram_id}: {e}")
                failed += 1
                await self._log_alert(user.telegram_id, f"alert_{user.alert_interval}", "failed", str(e))

        logger.info(f"Alerts sent (due: {due_intervals}): {sent} success, {failed} failed")

    # Keep old name as alias for backward compat with scheduler
    async def send_hourly_alerts(self):
        await self.send_alerts()

    async def send_breaking_alert(self, title: str, sentiment: float, analysis: str):
        """Send breaking news alert to all subscribed users."""
        emoji = "🟢" if sentiment > 0.3 else "🔴" if sentiment < -0.3 else "🟡"

        message = (
            f"🚨 <b>Breaking News Alert</b>\n\n"
            f"{emoji} {title}\n\n"
            f"Sentiment: {sentiment:+.2f}\n"
            f"Analysis: {analysis}\n\n"
            f"<i>{DISCLAIMER}</i>"
        )

        async with async_session() as session:
            result = await session.execute(
                select(BotUser).where(BotUser.subscribed == True)
            )
            users = result.scalars().all()

        users = [u for u in users if is_premium(u)]

        for user in users:
            try:
                await self.bot.send_message(user.telegram_id, message, parse_mode="HTML")
                await self._log_alert(user.telegram_id, "breaking", "sent")
            except Exception as e:
                logger.error(f"Failed to send breaking alert to {user.telegram_id}: {e}")
                await self._log_alert(user.telegram_id, "breaking", "failed", str(e))

    async def check_price_alerts(self):
        """Check all active price alerts against current prices. Runs every 30s."""
        try:
            async with async_session() as session:
                # Get all active alerts
                result = await session.execute(
                    select(PriceAlert).where(PriceAlert.is_active == True)
                )
                alerts = result.scalars().all()

                if not alerts:
                    return

                # Get current gold price
                result = await session.execute(
                    select(Price).order_by(desc(Price.timestamp)).limit(1)
                )
                gold_price_row = result.scalar_one_or_none()
                gold_price = gold_price_row.close if gold_price_row else None

                # Get latest coin prices for alerts
                coin_prices = {}
                if gold_price:
                    coin_prices["gold"] = gold_price

                # Note: Multi-coin price alerts are not available for gold trading.
                # Only gold alerts are supported.

                triggered = 0
                for alert in alerts:
                    current = coin_prices.get(alert.asset_id)
                    if current is None:
                        continue

                    crossed = (
                        (alert.direction == "above" and current >= alert.target_price) or
                        (alert.direction == "below" and current <= alert.target_price)
                    )
                    if not crossed:
                        continue

                    # Trigger the alert
                    alert.triggered_at = datetime.utcnow()
                    alert.triggered_price = current
                    if not alert.is_repeating:
                        alert.is_active = False

                    # Send notification
                    symbol = alert.asset_id.upper()[:6]
                    dir_emoji = "📈" if alert.direction == "above" else "📉"
                    note_line = f"\n📝 {alert.note}" if alert.note else ""
                    msg = (
                        f"🔔 <b>Price Alert Triggered!</b>\n\n"
                        f"{dir_emoji} <b>{symbol}</b> is now {'above' if alert.direction == 'above' else 'below'} "
                        f"${alert.target_price:,.2f}\n"
                        f"Current: <b>${current:,.2f}</b>"
                        f"{note_line}\n\n"
                        f"{'🔄 Repeating alert — still active.' if alert.is_repeating else '✅ One-shot alert — deactivated.'}"
                    )

                    try:
                        await self.bot.send_message(alert.telegram_id, msg, parse_mode="HTML")
                        triggered += 1
                    except Exception as e:
                        logger.error(f"Failed to send price alert to {alert.telegram_id}: {e}")

                await session.commit()
                if triggered:
                    logger.info(f"Price alerts triggered: {triggered}")

        except Exception as e:
            logger.error(f"check_price_alerts error: {e}", exc_info=True)

    async def send_daily_briefing(self):
        """Send daily briefing to subscribed premium users. Runs at 08:00 UTC."""
        try:
            async with async_session() as session:
                # Get latest briefing
                result = await session.execute(
                    select(DailyBriefing).order_by(desc(DailyBriefing.date)).limit(1)
                )
                briefing = result.scalar_one_or_none()

                if not briefing:
                    logger.warning("No briefing to send")
                    return

                # Get premium subscribed users
                now = datetime.utcnow()
                from sqlalchemy import or_, and_
                query = (
                    select(BotUser)
                    .where(BotUser.subscribed == True)
                )
                if settings.subscription_enabled:
                    query = query.where(
                        or_(
                            and_(
                                BotUser.subscription_tier == "premium",
                                BotUser.subscription_end > now,
                            ),
                            BotUser.trial_end > now,
                        )
                    )
                result = await session.execute(query)
                users = result.scalars().all()

            if not users:
                return

            # Truncate for Telegram's 4096 char limit
            text = briefing.summary_text[:3900]
            if len(briefing.summary_text) > 3900:
                text += "\n\n... Open Griffin Gold for the full briefing."

            sent = 0
            for user in users:
                try:
                    await self.bot.send_message(user.telegram_id, text, parse_mode="HTML")
                    sent += 1
                except Exception as e:
                    logger.debug(f"Briefing send failed for {user.telegram_id}: {e}")

            logger.info(f"Daily briefing sent to {sent}/{len(users)} users")

        except Exception as e:
            logger.error(f"send_daily_briefing error: {e}", exc_info=True)

    def _format_alert(self, predictions: list, signal, current_price: float = None) -> str:
        """Format prediction alert message."""
        direction_emoji = {"bullish": "🟢 ▲", "bearish": "🔴 ▼", "neutral": "🟡 ◄►"}

        lines = ["🔮 <b>Griffin Gold — Update</b>\n"]

        price = current_price or (predictions[0].current_price if predictions else None)
        if price:
            lines.append(f"💰 XAUUSD: <code>${price:,.2f}</code>\n")

        for p in predictions:
            emoji = direction_emoji.get(p.direction, "⚪")
            lines.append(
                f"<b>{p.timeframe.upper()}</b>: {emoji} {p.direction.title()} ({p.confidence:.0f}%)"
            )

        if signal:
            action_emoji = {
                "strong_buy": "🟢🟢", "buy": "🟢", "hold": "🟡",
                "sell": "🔴", "strong_sell": "🔴🔴",
            }
            emoji = action_emoji.get(signal.action, "⚪")
            lines.append(f"\n📈 Signal: {emoji} <b>{signal.action.replace('_', ' ').upper()}</b>")
            lines.append(f"   Entry: ${signal.entry_price:,.0f} | Target: ${signal.target_price:,.0f}")
            lines.append(f"   Stop: ${signal.stop_loss:,.0f} | Risk: {signal.risk_rating}/10")

        lines.append(f"\n<i>{DISCLAIMER}</i>")

        return "\n".join(lines)
