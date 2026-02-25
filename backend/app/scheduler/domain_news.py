"""News collection jobs: news, event classification."""

import logging
from datetime import datetime, timedelta

from sqlalchemy import select, desc

from app.database import (
    async_session, Price, News, EventImpact,
)
from app.collectors import (
    NewsCollector, RedditCollector,
)
from app.features.sentiment import SentimentAnalyzer
from app.models.event_memory import EventClassifier

logger = logging.getLogger(__name__)

# Global instances (initialized once)
news_collector = NewsCollector()
reddit_collector = RedditCollector()
event_classifier = EventClassifier()


async def collect_news_data():
    """Collect news from ALL sources: RSS feeds, Reddit.

    Runs every 2 minutes. De-duplicates by title to avoid storing the same
    headline twice within a 6-hour window.
    """
    try:
        # -- Gather news from all collectors in parallel-ish fashion --
        all_items: list[dict] = []

        # 1. RSS feeds (gold/macro news)
        rss_data = await news_collector.collect()
        all_items.extend(rss_data.get("news", []))

        # 2. Reddit posts
        try:
            reddit_data = await reddit_collector.collect()
            for post in reddit_data.get("posts", []):
                all_items.append({
                    "source": f"reddit_{post.get('subreddit', 'unknown')}",
                    "title": post.get("title", ""),
                    "url": post.get("url", ""),
                    "published": "",
                    "sentiment_score": None,
                    "raw_sentiment": None,
                })
        except Exception as e:
            logger.debug(f"Reddit collection failed: {e}")

        if not all_items:
            return

        # -- De-duplicate: skip titles already stored in the last 6 hours --
        async with async_session() as session:
            since = datetime.utcnow() - timedelta(hours=6)
            result = await session.execute(
                select(News.title).where(News.timestamp >= since)
            )
            existing_titles = {row[0].lower().strip() for row in result.all()}

        analyzer = SentimentAnalyzer()
        analyzer.load_multilingual()
        new_count = 0

        async with async_session() as session:
            for item in all_items:
                title = item.get("title", "").strip()
                if not title:
                    continue

                # Skip duplicates
                if title.lower() in existing_titles:
                    continue
                existing_titles.add(title.lower())

                # Detect language (from hint or auto-detect)
                language = item.get("language")
                if not language:
                    language = analyzer.detect_language(title)

                # Score sentiment with language awareness
                sentiment = analyzer.analyze_text(title, language=language)
                score = sentiment["combined_score"]

                news = News(
                    timestamp=datetime.utcnow(),
                    source=item.get("source", "unknown"),
                    title=title,
                    url=item.get("url", ""),
                    sentiment_score=score,
                    raw_sentiment=item.get("raw_sentiment"),
                    language=language,
                )
                session.add(news)
                new_count += 1

            await session.commit()

        logger.info(f"News: {len(all_items)} fetched, {new_count} new (deduped)")

    except Exception as e:
        logger.error(f"News collection error: {e}")


async def classify_news_events():
    """Classify recent news into event categories and record them (runs every 5 min).

    This is the 'learning' step -- it identifies significant events and starts
    tracking their price impact. Over time, this builds a historical memory
    of how different event types affect gold prices.
    """
    try:
        async with async_session() as session:
            # Get news from last 10 minutes that haven't been classified yet
            since = datetime.utcnow() - timedelta(minutes=10)
            result = await session.execute(
                select(News).where(News.timestamp >= since)
            )
            recent_news = result.scalars().all()

            # Get already-classified news IDs (from last hour to avoid re-processing)
            since_1h = datetime.utcnow() - timedelta(hours=1)
            result = await session.execute(
                select(EventImpact.news_id).where(
                    EventImpact.timestamp >= since_1h
                )
            )
            already_classified = {row[0] for row in result.all() if row[0]}

            # Get current gold price
            result = await session.execute(
                select(Price).order_by(desc(Price.timestamp)).limit(1)
            )
            current_price_row = result.scalar_one_or_none()
            if not current_price_row:
                return
            current_price = current_price_row.close

        new_events = 0

        async with async_session() as session:
            for news_item in recent_news:
                if news_item.id in already_classified:
                    continue

                classification = event_classifier.classify(
                    news_item.title,
                    sentiment_score=news_item.sentiment_score or 0.0,
                )

                if classification is None:
                    continue  # Not a significant event

                event = EventImpact(
                    timestamp=news_item.timestamp,
                    news_id=news_item.id,
                    title=news_item.title,
                    source=news_item.source,
                    category=classification["category"],
                    subcategory=classification["subcategory"],
                    keywords=classification["keywords"],
                    severity=classification["severity"],
                    sentiment_score=news_item.sentiment_score,
                    price_at_event=current_price,
                )
                session.add(event)
                new_events += 1

            await session.commit()

        if new_events > 0:
            logger.info(f"Event memory: {new_events} new events classified")

    except Exception as e:
        logger.error(f"Event classification error: {e}")


async def evaluate_event_impacts():
    """Measure actual gold price impact of past events (runs every 30 min).

    For each event that hasn't been fully evaluated, check if enough time has
    passed and record the actual price change. This builds the historical
    'memory' that the pattern matcher uses.

    After evaluation, triggers event post-mortem for newly-evaluated events.
    """
    from app.scheduler.domain_ml import _get_price_at

    try:
        newly_evaluated_1h = 0

        async with async_session() as session:
            # Get events that need evaluation
            result = await session.execute(
                select(EventImpact).where(
                    (EventImpact.evaluated_1h == False) |
                    (EventImpact.evaluated_4h == False) |
                    (EventImpact.evaluated_24h == False) |
                    (EventImpact.evaluated_7d == False)
                )
            )
            events = result.scalars().all()

            if not events:
                return

            now = datetime.utcnow()
            evaluated_count = 0

            for event in events:
                base_price = event.price_at_event
                if not base_price:
                    continue

                # Evaluate 1h impact
                if not event.evaluated_1h and now >= event.timestamp + timedelta(hours=1):
                    price_1h = await _get_price_at(session, event.timestamp + timedelta(hours=1))
                    if price_1h:
                        event.price_1h = price_1h
                        event.change_pct_1h = round((price_1h - base_price) / base_price * 100, 4)
                        event.evaluated_1h = True
                        evaluated_count += 1
                        newly_evaluated_1h += 1

                        # Check if sentiment was predictive for 1h
                        if event.sentiment_score is not None:
                            sent_predicted_up = event.sentiment_score > 0
                            actually_went_up = event.change_pct_1h > 0
                            event.sentiment_was_predictive = (sent_predicted_up == actually_went_up)

                # Evaluate 4h impact
                if not event.evaluated_4h and now >= event.timestamp + timedelta(hours=4):
                    price_4h = await _get_price_at(session, event.timestamp + timedelta(hours=4))
                    if price_4h:
                        event.price_4h = price_4h
                        event.change_pct_4h = round((price_4h - base_price) / base_price * 100, 4)
                        event.evaluated_4h = True
                        evaluated_count += 1

                # Evaluate 24h impact
                if not event.evaluated_24h and now >= event.timestamp + timedelta(hours=24):
                    price_24h = await _get_price_at(session, event.timestamp + timedelta(hours=24))
                    if price_24h:
                        event.price_24h = price_24h
                        event.change_pct_24h = round((price_24h - base_price) / base_price * 100, 4)
                        event.evaluated_24h = True
                        evaluated_count += 1

                # Evaluate 7d impact
                if not event.evaluated_7d and now >= event.timestamp + timedelta(days=7):
                    price_7d = await _get_price_at(session, event.timestamp + timedelta(days=7))
                    if price_7d:
                        event.price_7d = price_7d
                        event.change_pct_7d = round((price_7d - base_price) / base_price * 100, 4)
                        event.evaluated_7d = True
                        evaluated_count += 1

            await session.commit()

        if evaluated_count > 0:
            logger.info(f"Event memory: evaluated {evaluated_count} impact measurements")

        # Run post-mortem for newly evaluated events (learn from results)
        if newly_evaluated_1h > 0:
            try:
                from app.models.event_learner import run_event_post_mortem
                await run_event_post_mortem()
            except Exception as e:
                logger.debug(f"Event post-mortem after evaluation: {e}")

    except Exception as e:
        logger.error(f"Event impact evaluation error: {e}")
