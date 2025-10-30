import feedparser
from datetime import datetime, timedelta, timezone
from core.logger import log


def fetch_rss(feed_url: str, limit: int = 20, hours_back: int = 24):
    """
    Загружает новости из RSS-ленты, фильтрует по дате (за последние X часов)
    и возвращает список словарей.
    """
    log.info(f"Fetching RSS: {feed_url}")
    feed = feedparser.parse(feed_url)
    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)

    for entry in feed.entries[:limit]:
        # Получаем дату публикации
        published_parsed = getattr(entry, "published_parsed", None)
        if published_parsed:
            pub_date = datetime(*published_parsed[:6], tzinfo=timezone.utc)
        else:
            pub_date = None

        # Пропускаем старые статьи
        if pub_date and pub_date < cutoff:
            continue

        # Собираем данные о статье
        article = {
            "title": getattr(entry, "title", "").strip(),
            "url": getattr(entry, "link", "").strip(),
            "summary": getattr(entry, "summary", "")[:500].strip(),
            "published_at": pub_date.isoformat() if pub_date else "",
            "source": feed.feed.get("title", feed_url),
        }
        articles.append(article)

    log.info(f"📡 {feed_url} → найдено {len(articles)} новостей за последние {hours_back} ч.")
    return articles
