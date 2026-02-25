import logging
from datetime import datetime

import aiohttp
import feedparser

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.collectors.base import BaseCollector
from app.config import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# RSS / Atom feeds — gold, commodities, forex & macro financial press
# ──────────────────────────────────────────────────────────────
RSS_FEEDS = {
    # ── Gold & commodities outlets ──
    "kitco": "https://www.kitco.com/rss/all.xml",
    "goldprice_org": "https://goldprice.org/feed",
    "mining_com": "https://www.mining.com/feed/",
    "bullionvault": "https://www.bullionvault.com/gold-news/rss",

    # ── Forex & macro finance ──
    "forexlive": "https://www.forexlive.com/feed",
    "fxstreet": "https://www.fxstreet.com/rss",
    "dailyfx": "https://www.dailyfx.com/feeds/all",
    "investing_com": "https://www.investing.com/rss/news_14.rss",

    # ── Mainstream finance ──
    "google_news_gold": "https://news.google.com/rss/search?q=gold+price+OR+XAUUSD+OR+gold+market&hl=en-US&gl=US&ceid=US:en",
    "google_news_macro": "https://news.google.com/rss/search?q=federal+reserve+OR+interest+rate+OR+inflation+OR+tariff+gold&hl=en-US&gl=US&ceid=US:en",
    "yahoo_commodities": "https://finance.yahoo.com/news/topic/commodities/.rss",

    # ── Central banks & gold reserves ──
    "google_news_central_bank_gold": "https://news.google.com/rss/search?q=central+bank+gold+OR+gold+reserve+OR+gold+purchases&hl=en-US&gl=US&ceid=US:en",

    # ── Politics, war, geopolitics (gold safe haven drivers) ──
    "google_news_war": "https://news.google.com/rss/search?q=war+OR+conflict+OR+military+OR+sanctions+gold+OR+safe+haven&hl=en-US&gl=US&ceid=US:en",
    "google_news_politics": "https://news.google.com/rss/search?q=congress+OR+senate+OR+regulation+gold+OR+commodities&hl=en-US&gl=US&ceid=US:en",
    "google_news_tariff": "https://news.google.com/rss/search?q=tariff+OR+trade+war+OR+sanctions+economy&hl=en-US&gl=US&ceid=US:en",

    # ── Fed & monetary policy ──
    "google_news_fed": "https://news.google.com/rss/search?q=federal+reserve+OR+rate+decision+OR+FOMC+OR+powell&hl=en-US&gl=US&ceid=US:en",

    # ── Stock market & corporate ──
    "google_news_stocks": "https://news.google.com/rss/search?q=stock+market+OR+S%26P+500+OR+nasdaq+crash+OR+rally&hl=en-US&gl=US&ceid=US:en",
    "google_news_mining": "https://news.google.com/rss/search?q=gold+mining+OR+barrick+OR+newmont+OR+gold+production&hl=en-US&gl=US&ceid=US:en",

    # ── Financial news outlets (gold coverage) ──
    "reuters_gold": "https://news.google.com/rss/search?q=site:reuters.com+gold+OR+commodities+OR+federal+reserve&hl=en-US&gl=US&ceid=US:en",
    "ft_gold": "https://news.google.com/rss/search?q=site:ft.com+gold+OR+commodities+OR+precious+metals&hl=en-US&gl=US&ceid=US:en",
    "bloomberg_gold": "https://news.google.com/rss/search?q=site:bloomberg.com+gold+OR+commodities+OR+precious+metals&hl=en-US&gl=US&ceid=US:en",

    # ── Russian gold/commodity news ──
    "google_news_gold_ru": "https://news.google.com/rss/search?q=%D0%B7%D0%BE%D0%BB%D0%BE%D1%82%D0%BE+%D1%86%D0%B5%D0%BD%D0%B0+OR+%D0%B7%D0%BE%D0%BB%D0%BE%D1%82%D0%BE+%D1%80%D1%8B%D0%BD%D0%BE%D0%BA&hl=ru&gl=RU&ceid=RU:ru",
    "google_news_rbc_gold_ru": "https://news.google.com/rss/search?q=site:rbc.ru+%D0%B7%D0%BE%D0%BB%D0%BE%D1%82%D0%BE+OR+%D0%B4%D1%80%D0%B0%D0%B3%D0%BC%D0%B5%D1%82%D0%B0%D0%BB%D0%BB%D1%8B&hl=ru&gl=RU&ceid=RU:ru",

    # ── Chinese gold news ──
    "google_news_gold_cn": "https://news.google.com/rss/search?q=%E9%BB%84%E9%87%91+%E4%BB%B7%E6%A0%BC+OR+%E9%BB%84%E9%87%91+%E5%B8%82%E5%9C%BA+OR+gold&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",

    # ── Spanish gold news ──
    "google_news_gold_es": "https://news.google.com/rss/search?q=oro+precio+OR+oro+mercado+OR+gold&hl=es&gl=ES&ceid=ES:es",

    # ── Arabic gold news ──
    "google_news_gold_ar": "https://news.google.com/rss/search?q=%D8%B0%D9%87%D8%A8+%D8%B3%D8%B9%D8%B1+OR+%D8%B0%D9%87%D8%A8+%D8%B3%D9%88%D9%82+OR+gold&hl=ar&gl=AE&ceid=AE:ar",

    # ── Japanese gold news ──
    "google_news_gold_jp": "https://news.google.com/rss/search?q=%E9%87%91%E4%BE%A1%E6%A0%BC+OR+%E3%82%B4%E3%83%BC%E3%83%AB%E3%83%89+OR+gold&hl=ja&gl=JP&ceid=JP:ja",

    # ── Korean gold news ──
    "google_news_gold_kr": "https://news.google.com/rss/search?q=%EA%B8%88+%EA%B0%80%EA%B2%A9+OR+%EA%B8%88+%EC%8B%9C%EC%9E%A5+OR+gold&hl=ko&gl=KR&ceid=KR:ko",

    # ── Turkish gold news ──
    "google_news_gold_tr": "https://news.google.com/rss/search?q=alt%C4%B1n+fiyat+OR+alt%C4%B1n+piyasa+OR+gold&hl=tr&gl=TR&ceid=TR:tr",

    # ── Portuguese / Brazilian gold news ──
    "google_news_gold_br": "https://news.google.com/rss/search?q=ouro+pre%C3%A7o+OR+ouro+mercado+OR+gold&hl=pt-BR&gl=BR&ceid=BR:pt-419",

    # ── Hindi / Indian gold news ──
    "google_news_gold_in": "https://news.google.com/rss/search?q=%E0%A4%B8%E0%A5%8B%E0%A4%A8%E0%A4%BE+%E0%A4%95%E0%A5%80%E0%A4%AE%E0%A4%A4+OR+gold+india&hl=hi&gl=IN&ceid=IN:hi",

    # ── Gold reserve / central bank gold (English, multi-region) ──
    "google_news_gold_reserve": "https://news.google.com/rss/search?q=gold+reserve+OR+central+bank+gold+OR+sovereign+gold+OR+gold+repatriation&hl=en-US&gl=US&ceid=US:en",
    "google_news_mideast_gold": "https://news.google.com/rss/search?q=gold+saudi+OR+uae+OR+qatar+OR+dubai+OR+bahrain+OR+israel+OR+commodities&hl=en-US&gl=US&ceid=US:en",
}

# Map feed source names to language codes
FEED_LANGUAGE_HINTS = {
    # Russian
    "google_news_gold_ru": "ru",
    "google_news_rbc_gold_ru": "ru",
    # Chinese
    "google_news_gold_cn": "zh-cn",
    # Spanish
    "google_news_gold_es": "es",
    # Arabic
    "google_news_gold_ar": "ar",
    # Japanese
    "google_news_gold_jp": "ja",
    # Korean
    "google_news_gold_kr": "ko",
    # Turkish
    "google_news_gold_tr": "tr",
    # Portuguese
    "google_news_gold_br": "pt",
    # Hindi
    "google_news_gold_in": "hi",
}

CRYPTOPANIC_URL = "https://cryptopanic.com/api/v1/posts/"


class NewsCollector(BaseCollector):
    """Collects gold, commodity & macro news from RSS feeds and optional CryptoPanic API."""

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def collect(self) -> dict:
        """Collect news from all sources."""
        cryptopanic_news = await self._get_cryptopanic()
        rss_news = await self._get_rss_feeds()

        all_news = []
        if cryptopanic_news:
            all_news.extend(cryptopanic_news)
        if rss_news:
            all_news.extend(rss_news)

        return {
            "news": all_news,
            "count": len(all_news),
            "timestamp": self.now().isoformat(),
        }

    async def _get_cryptopanic(self) -> list[dict] | None:
        """Get news from CryptoPanic API."""
        if not settings.cryptopanic_api_key:
            logger.debug("CryptoPanic API key not set, skipping")
            return None

        data = await self.fetch_json(
            CRYPTOPANIC_URL,
            params={
                "auth_token": settings.cryptopanic_api_key,
                "currencies": "GOLD",
                "filter": "important",
                "public": "true",
            },
        )

        if not data or "results" not in data:
            return None

        news = []
        for item in data["results"]:
            votes = item.get("votes", {})
            positive = votes.get("positive", 0)
            negative = votes.get("negative", 0)
            total = positive + negative
            sentiment = (positive - negative) / total if total > 0 else 0

            news.append({
                "source": "cryptopanic",
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "published": item.get("published_at", ""),
                "sentiment_score": sentiment,
                "raw_sentiment": item.get("metadata", {}).get("sentiment"),
            })

        return news

    async def _get_rss_feeds(self) -> list[dict]:
        """Parse RSS feeds for gold & macro news — all sources in parallel-ish loop."""
        all_news = []
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; GriffinGold/1.0; +https://griffingold.app)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        }

        for source, url in RSS_FEEDS.items():
            try:
                session = await self.get_session()
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status != 200:
                        logger.debug(f"RSS {source} returned HTTP {resp.status}")
                        continue
                    content = await resp.text()

                feed = feedparser.parse(content)

                lang_hint = FEED_LANGUAGE_HINTS.get(source)

                for entry in feed.entries[:15]:  # Last 15 per source
                    published = ""
                    if hasattr(entry, "published"):
                        published = entry.published
                    elif hasattr(entry, "updated"):
                        published = entry.updated

                    all_news.append({
                        "source": source,
                        "title": entry.get("title", ""),
                        "url": entry.get("link", ""),
                        "published": published,
                        "sentiment_score": None,
                        "raw_sentiment": None,
                        "language": lang_hint,
                    })

            except Exception as e:
                logger.debug(f"Error parsing RSS feed {source}: {e}")

        return all_news
