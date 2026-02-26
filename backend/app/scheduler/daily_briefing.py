"""Daily Briefing Generator — template-based market summary (zero API cost)."""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select, func, desc

from app.database import (
    async_session, DailyBriefing, Price, Prediction, Signal, QuantPrediction,
    MacroData, News,
)

logger = logging.getLogger(__name__)


def _sentiment_label(score: float) -> str:
    if score > 0.3:
        return "bullish"
    elif score < -0.3:
        return "bearish"
    return "neutral"


def _direction_emoji(direction: str) -> str:
    return {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡"}.get(direction, "⚪")


async def generate_daily_briefing():
    """Generate a template-based daily market briefing from existing data."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    now = datetime.utcnow()
    cutoff_24h = now - timedelta(hours=24)

    try:
        async with async_session() as session:
            # Check if already generated
            result = await session.execute(
                select(DailyBriefing).where(DailyBriefing.date == today)
            )
            if result.scalar_one_or_none():
                logger.info(f"Briefing already exists for {today}")
                return

            # 1. Price data
            result = await session.execute(
                select(Price).order_by(desc(Price.timestamp)).limit(1)
            )
            price_row = result.scalar_one_or_none()
            gold_price = price_row.close if price_row else 0

            result = await session.execute(
                select(Price).where(Price.timestamp >= cutoff_24h).order_by(Price.timestamp).limit(1)
            )
            price_24h_ago = result.scalar_one_or_none()
            gold_24h_change = 0
            if price_24h_ago and price_24h_ago.close:
                gold_24h_change = ((gold_price - price_24h_ago.close) / price_24h_ago.close) * 100

            # 2. Latest predictions
            preds = {}
            for tf in ["1h", "4h", "24h"]:
                result = await session.execute(
                    select(Prediction).where(Prediction.timeframe == tf)
                    .order_by(desc(Prediction.timestamp)).limit(1)
                )
                p = result.scalar_one_or_none()
                if p:
                    preds[tf] = p

            # 3. Latest signal
            result = await session.execute(
                select(Signal).order_by(desc(Signal.timestamp)).limit(1)
            )
            signal = result.scalar_one_or_none()

            # 4. Quant prediction
            result = await session.execute(
                select(QuantPrediction).order_by(desc(QuantPrediction.timestamp)).limit(1)
            )
            quant = result.scalar_one_or_none()

            # 5. Macro data
            result = await session.execute(
                select(MacroData).order_by(desc(MacroData.timestamp)).limit(1)
            )
            macro = result.scalar_one_or_none()

            # 6. News sentiment (24h average)
            result = await session.execute(
                select(func.avg(News.sentiment_score))
                .where(News.timestamp >= cutoff_24h)
                .where(News.sentiment_score.isnot(None))
            )
            news_sentiment_avg = result.scalar() or 0

            # 7. Prediction accuracy (recent)
            result = await session.execute(
                select(Prediction)
                .where(Prediction.was_correct.isnot(None))
                .order_by(desc(Prediction.timestamp))
                .limit(50)
            )
            recent_preds = result.scalars().all()
            total_eval = len(recent_preds)
            correct_eval = sum(1 for p in recent_preds if p.was_correct)
            accuracy = (correct_eval / total_eval * 100) if total_eval else 0

            # Determine overall sentiment
            bullish_signals = 0
            bearish_signals = 0
            for p in preds.values():
                if p.direction == "bullish":
                    bullish_signals += 1
                elif p.direction == "bearish":
                    bearish_signals += 1
            if quant and quant.direction == "bullish":
                bullish_signals += 1
            elif quant and quant.direction == "bearish":
                bearish_signals += 1

            if bullish_signals > bearish_signals:
                overall_sentiment = "bullish"
            elif bearish_signals > bullish_signals:
                overall_sentiment = "bearish"
            else:
                overall_sentiment = "neutral"

            confidence = max((p.confidence for p in preds.values()), default=50)

            # Build sections
            change_emoji = "🟢" if gold_24h_change > 0 else "🔴" if gold_24h_change < 0 else "🟡"
            sent_emoji = _direction_emoji(overall_sentiment)

            # HTML version
            html_parts = []
            html_parts.append(f"<h3>{sent_emoji} Daily Market Briefing — {today}</h3>")

            # Price Action
            html_parts.append(f"<b>💰 Price Action</b>")
            html_parts.append(f"XAUUSD: <b>${gold_price:,.2f}</b> {change_emoji} ({gold_24h_change:+.2f}% 24h)")

            # AI Predictions
            html_parts.append(f"\n<b>🔮 AI Predictions</b>")
            for tf, p in preds.items():
                emoji = _direction_emoji(p.direction)
                html_parts.append(f"{tf.upper()}: {emoji} {p.direction.title()} ({p.confidence:.0f}%)")
            if quant:
                q_emoji = _direction_emoji(quant.direction)
                html_parts.append(f"Quant: {q_emoji} {quant.action} ({quant.confidence:.0f}%)")

            # Signal
            if signal:
                html_parts.append(f"\n<b>📈 Trading Signal</b>")
                html_parts.append(f"{signal.action.replace('_', ' ').upper()} | Entry: ${signal.entry_price:,.0f} | TP: ${signal.target_price:,.0f} | SL: ${signal.stop_loss:,.0f}")

            # Market Sentiment
            html_parts.append(f"\n<b>📊 Market Sentiment</b>")
            if macro and macro.fear_greed_index is not None:
                html_parts.append(f"Fear & Greed: {macro.fear_greed_index}/100 ({macro.fear_greed_label or ''})")
            html_parts.append(f"News Sentiment: {news_sentiment_avg:+.2f} ({_sentiment_label(news_sentiment_avg)})")

            # Macro Context (gold-relevant drivers)
            if macro:
                macro_lines = []
                if macro.dxy is not None:
                    macro_lines.append(f"DXY: {macro.dxy:.2f}")
                if macro.treasury_10y is not None:
                    macro_lines.append(f"10Y Yield: {macro.treasury_10y:.2f}%")
                if macro.vix is not None:
                    macro_lines.append(f"VIX: {macro.vix:.1f}")
                if macro.silver is not None:
                    macro_lines.append(f"Silver: ${macro.silver:.2f}")
                if macro_lines:
                    html_parts.append(f"\n<b>🌍 Macro Context</b>")
                    html_parts.append(" | ".join(macro_lines))

            # Accuracy Report
            if total_eval > 0:
                html_parts.append(f"\n<b>🎯 Accuracy</b>")
                html_parts.append(f"Recent: {correct_eval}/{total_eval} ({accuracy:.0f}%)")

            summary_html = "\n".join(html_parts)
            summary_text = summary_html.replace("<b>", "").replace("</b>", "").replace("<h3>", "").replace("</h3>", "").replace("\n\n", "\n")

            data_snapshot = {
                "gold_price": gold_price,
                "gold_24h_change": gold_24h_change,
                "predictions": {tf: {"direction": p.direction, "confidence": p.confidence} for tf, p in preds.items()},
                "signal": {"action": signal.action, "entry": signal.entry_price} if signal else None,
                "fear_greed": macro.fear_greed_index if macro else None,
                "news_sentiment": news_sentiment_avg,
                "dxy": macro.dxy if macro else None,
                "treasury_10y": macro.treasury_10y if macro else None,
                "vix": macro.vix if macro else None,
                "accuracy": accuracy,
                "overall_sentiment": overall_sentiment,
            }

            briefing = DailyBriefing(
                date=today,
                summary_html=summary_html,
                summary_text=summary_text,
                data_snapshot=data_snapshot,
                btc_price=gold_price,
                btc_24h_change=gold_24h_change,
                overall_sentiment=overall_sentiment,
                confidence=confidence,
                generation_method="template",
            )
            session.add(briefing)
            await session.commit()

            logger.info(f"Daily briefing generated for {today}")

    except Exception as e:
        logger.error(f"Failed to generate daily briefing: {e}", exc_info=True)
