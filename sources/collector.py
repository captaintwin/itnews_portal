import os
import json
import random
from datetime import datetime
from pathlib import Path

from core.logger import log
from sources.rss import fetch_rss
from utils.helpers import generate_id, fetch_main_image, download_image

# Максимум статей с одного источника
MAX_PER_SOURCE = 5

# Список RSS-источников
RSS_SOURCES = [
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss",
    "https://techcrunch.com/feed/",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://www.engadget.com/rss.xml",
    "https://www.zdnet.com/news/rss.xml",
    "https://www.cnet.com/rss/news/",
    "https://venturebeat.com/feed/",
    "https://github.blog/feed/",
    "https://stackoverflow.blog/feed/",
    "https://dev.to/feed",
    "https://feeds.feedburner.com/TheHackersNews",
]


def collect_all():
    """Собирает новости (до 5 на источник), перемешивает и сохраняет в JSON."""
    IMG_DIR = Path("data/images")
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    os.makedirs("data", exist_ok=True)

    all_news = []

    for src in RSS_SOURCES:
        log.info(f"Fetching RSS: {src}")
        try:
            items = fetch_rss(src, limit=MAX_PER_SOURCE)
        except Exception as e:
            log.error(f"Error fetching {src}: {e}")
            continue

        if not items:
            log.warning(f"No items from {src}")
            continue

        clean_items = []
        for news in items[:MAX_PER_SOURCE]:
            url = news.get("url")
            if not url:
                continue

            title = news.get("title", "").strip()
            published = news.get("published_at") or datetime.utcnow().isoformat()
            summary = news.get("summary", "")
            source = news.get("source", src)

            news_id = generate_id(url)
            img_url = fetch_main_image(url)
            saved_img = None

            if img_url:
                saved_img = download_image(img_url, IMG_DIR, news_id)
                if saved_img:
                    log.info(f"🖼 Saved new image: {saved_img}")
                else:
                    log.warning(f"⚠️ Failed to download image for: {title}")
            else:
                log.warning(f"⚠️ No main image found for: {title}")

            clean_items.append({
                "id": news_id,
                "title": title,
                "url": url,
                "summary": summary,
                "source": source,
                "published_at": published,
                "image_path": saved_img
            })

        if clean_items:
            log.info(f"Found {len(clean_items)} items from {src}")
            all_news.extend(clean_items)

    # 🔄 Перемешиваем для разнообразной подачи
    random.shuffle(all_news)

    log.info(f"✅ Total collected: {len(all_news)} (max {MAX_PER_SOURCE} per source)")

    # 💾 Сохраняем в JSON
    output_path = Path("data/news.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_news, f, ensure_ascii=False, indent=2)

    log.info(f"✅ Saved {len(all_news)} news items to {output_path.resolve()}")
    return all_news
