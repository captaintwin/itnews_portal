import json
import os
import re
import hashlib
import requests
from pathlib import Path
from urllib.parse import urlparse, urljoin
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from core.logger import log
from sources.rss import fetch_rss

# === Константы ===
MAX_ITEMS_PER_SOURCE = 3
DATA_FILE = Path("data/news.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ITNewsBot/1.0)"}

RSS_SOURCES = [
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss",
    "https://techcrunch.com/feed/",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://www.engadget.com/rss.xml",
    "https://venturebeat.com/feed/",
    "https://github.blog/feed/",
    "https://stackoverflow.blog/feed/",
    "https://feeds.feedburner.com/TheHackersNews",
]

WHITE_DOMAINS = [
    "theverge.com", "techcrunch.com", "wired.com", "arstechnica.com",
    "venturebeat.com", "github.blog", "engadget.com", "stackoverflow.blog",
    "feeds.feedburner.com"
]

BAD_KEYWORDS = [
    "discount", "sale", "offer", "affiliate", "casino", "bet", "token",
    "crypto", "sponsored", "vpn", "deal", "price"
]


# === Фильтры ===
def is_trusted_source(url: str) -> bool:
    domain = urlparse(url).netloc.lower()
    return any(d in domain for d in WHITE_DOMAINS)

def has_bad_words(text: str) -> bool:
    return any(bad in (text or "").lower() for bad in BAD_KEYWORDS)

def is_recent(published_at, days=3):
    try:
        if isinstance(published_at, str):
            published_at = datetime.fromisoformat(published_at[:19])
    except Exception:
        return False
    return published_at >= datetime.utcnow() - timedelta(days=days)

def is_valid_title(title: str) -> bool:
    wc = len(title.split())
    return 3 <= wc <= 15


# === Утилиты ===
def generate_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]

def fetch_main_image(url):
    """Извлекает основную картинку со страницы."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        log.warning(f"[fetch_main_image] Failed to fetch {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    for prop in ["og:image", "twitter:image", "twitter:image:src"]:
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            return urljoin(url, tag["content"])

    link_tag = soup.find("link", rel="image_src")
    if link_tag and link_tag.get("href"):
        return urljoin(url, link_tag["href"])

    article = soup.find("article") or soup.find("main") or soup
    img_tag = article.find("img")
    if img_tag and img_tag.get("src") and not img_tag["src"].startswith("data:"):
        return urljoin(url, img_tag["src"])

    return None

def download_image(image_url: str, folder: Path, news_id: str):
    """Скачивает картинку и кэширует её."""
    ext = os.path.splitext(urlparse(image_url).path)[1]
    if not ext or len(ext) > 6:
        ext = ".jpg"

    img_path = folder / f"preview_{news_id}{ext}"
    if img_path.exists():
        log.info(f"🟡 Cached: {img_path.name}")
        return str(img_path)

    try:
        resp = requests.get(image_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        with open(img_path, "wb") as f:
            f.write(resp.content)
        log.info(f"🖼 Saved new image: {img_path}")
        return str(img_path)
    except Exception as e:
        log.warning(f"⚠️ Failed to download image {image_url}: {e}")
        return None


# === Основная функция ===
def collect_all():
    """Собирает по 3 свежие статьи из доверенных источников и сохраняет в JSON."""
    img_root = Path("data/images")
    img_root.mkdir(parents=True, exist_ok=True)
    os.makedirs("data", exist_ok=True)

    all_news = []
    for src in RSS_SOURCES:
        try:
            items = fetch_rss(src, limit=MAX_ITEMS_PER_SOURCE)
        except Exception as e:
            log.error(f"Error fetching {src}: {e}")
            continue

        for news in items[:MAX_ITEMS_PER_SOURCE]:
            url = news.get("url")
            title = news.get("title", "")
            published = news.get("published_at") or datetime.utcnow().isoformat()

            if not is_trusted_source(url): continue
            if has_bad_words(title): continue
            if not is_valid_title(title): continue
            if not is_recent(published): continue

            news_id = generate_id(url)
            img_url = fetch_main_image(url)
            saved_img = download_image(img_url, img_root, news_id) if img_url else None

            all_news.append({
                "id": news_id,
                "title": title,
                "url": url,
                "summary": news.get("summary", ""),
                "source": news.get("source", src),
                "published_at": published,
                "image_path": saved_img
            })

    # сохранить
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_news, f, ensure_ascii=False, indent=2)

    log.info(f"✅ Saved {len(all_news)} news items to {DATA_FILE.resolve()}")
    return all_news
