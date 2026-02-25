"""Gold-specific news collector with sentiment scoring.

Sources (RSS feeds):
- Kitco News (gold.xml)
- Mining.com
- BullionVault Gold News

Sentiment is scored using VADER (Valence Aware Dictionary and sEntiment Reasoner)
if the vaderSentiment package is available; otherwise sentiment_score is None.
"""
import logging
from datetime import datetime

import aiohttp
import feedparser

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

# Gold-focused RSS feeds
GOLD_RSS_FEEDS = {
    "kitco": "https://www.kitco.com/rss/gold.xml",
    "mining_com": "https://www.mining.com/feed/",
    "bullionvault": "https://www.bullionvault.com/gold-news/rss",
}

# Extended gold-relevant feeds
EXTENDED_GOLD_FEEDS = {
    "google_gold": "https://news.google.com/rss/search?q=gold+price+OR+XAUUSD+OR+gold+market&hl=en-US&gl=US&ceid=US:en",
    "google_gold_demand": "https://news.google.com/rss/search?q=gold+demand+OR+gold+reserve+OR+central+bank+gold&hl=en-US&gl=US&ceid=US:en",
    "google_precious_metals": "https://news.google.com/rss/search?q=precious+metals+OR+gold+silver+platinum&hl=en-US&gl=US&ceid=US:en",
}

# Try to import VADER for sentiment analysis
_vader_analyzer = None
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _vader_analyzer = SentimentIntensityAnalyzer()
    logger.info("VADER sentiment analyzer loaded")
except ImportError:
    logger.debug("vaderSentiment not installed — sentiment scoring disabled")


def _score_sentiment(text: str) -> float | None:
    """Score text sentiment using VADER. Returns compound score [-1, 1] or None."""
    if _vader_analyzer is None or not text:
        return None
    try:
        scores = _vader_analyzer.polarity_scores(text)
        return round(scores["compound"], 4)
    except Exception:
        return None


class GoldNewsCollector(BaseCollector):
    """Collects gold-specific news from RSS feeds with optional sentiment scoring."""

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def collect(self) -> list[dict]:
        """Fetch gold news from all RSS sources.

        Returns:
            List of dicts: {title, url, source, published_at, sentiment_score}
        """
        all_feeds = {**GOLD_RSS_FEEDS, **EXTENDED_GOLD_FEEDS}
        all_news = []

        for source, url in all_feeds.items():
            articles = await self._fetch_feed(source, url)
            all_news.extend(articles)

        logger.info(f"Collected {len(all_news)} gold news articles from {len(all_feeds)} feeds")
        return all_news

    async def _fetch_feed(self, source: str, url: str) -> list[dict]:
        """Fetch and parse a single RSS feed."""
        articles = []
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; GoldSeer/1.0; +https://goldseer.app)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        }

        try:
            session = await self.get_session()
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status != 200:
                    logger.debug(f"RSS {source} returned HTTP {resp.status}")
                    return []
                content = await resp.text()

            feed = feedparser.parse(content)

            for entry in feed.entries[:15]:  # Max 15 per source
                title = entry.get("title", "").strip()
                link = entry.get("link", "")

                published_at = ""
                if hasattr(entry, "published"):
                    published_at = entry.published
                elif hasattr(entry, "updated"):
                    published_at = entry.updated

                # Score sentiment on the title
                sentiment_score = _score_sentiment(title)

                articles.append({
                    "title": title,
                    "url": link,
                    "source": source,
                    "published_at": published_at,
                    "sentiment_score": sentiment_score,
                })

        except Exception as e:
            logger.debug(f"Error parsing gold RSS feed {source}: {e}")

        return articles
