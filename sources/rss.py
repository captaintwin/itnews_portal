 #парсинг RSS-фидов (feedparser);

import feedparser
from core.logger import log

def fetch_rss(feed_url: str, limit: int = 20):
    """Загружает новости из RSS-ленты и возвращает список словарей"""
    log.info(f"Fetching RSS: {feed_url}")
    feed = feedparser.parse(feed_url)
    articles = []

    for entry in feed.entries[:limit]:
        article = {
            "title": getattr(entry, "title", "").strip(),
            "url": getattr(entry, "link", "").strip(),
            "summary": getattr(entry, "summary", "")[:500].strip(),
            "published": getattr(entry, "published", ""),
            "source": feed.feed.get("title", feed_url),
        }
        articles.append(article)

    log.info(f"Found {len(articles)} items from {feed_url}")
    return articles
