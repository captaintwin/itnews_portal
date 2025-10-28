import json
import os
import re
import hashlib
import requests
from pathlib import Path
from urllib.parse import urlparse, urljoin
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from core.logger import log
from sources.rss import fetch_rss



# === Константы ===
MAX_ITEMS_PER_SOURCE = 20
DATA_FILE = Path("data/news.json")
# === ПУТИ ===
DATA_DIR = Path("data")
IMG_DIR = DATA_DIR / "images"     # ← вот это объявление должно быть ДО использования
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

def _is_recent_day(published_at, days=2):
    try:
        if isinstance(published_at, str):
            published_at = datetime.fromisoformat(published_at[:19])
    except Exception:
        return False
    return published_at >= datetime.utcnow() - timedelta(days=days)
def _dedup_by_url(items):
    """Удаляет дубли по полю url"""
    seen = set()
    result = []
    for it in items:
        url = it.get("url")
        if url and url not in seen:
            seen.add(url)
            result.append(it)
    return result
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
    """
    Собирает свежие статьи из доверенных источников и сохраняет в data/news.json,
    строго в прежней структуре полей (id, title, url, summary, source, published_at, image_path).
    """
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    os.makedirs("data", exist_ok=True)

    collected = []

    for src in RSS_SOURCES:
        try:
            items = fetch_rss(src, limit=MAX_ITEMS_PER_SOURCE)
            log.info(f"Fetched {len(items)} from {src}")
        except Exception as e:
            log.error(f"Error fetching {src}: {e}")
            continue

        # если задан лимит — подстрахуемся ещё раз
        sliced = items if MAX_ITEMS_PER_SOURCE is None else items[:MAX_ITEMS_PER_SOURCE]

        for news in sliced:
            url = news.get("url")
            title = news.get("title", "").strip()
            published = (news.get("published_at") or datetime.utcnow().replace(tzinfo=timezone.utc).isoformat())

            # фильтры качества/валидности — как у тебя было
            if not url:
                continue
            if not is_trusted_source(url):
                continue
            if has_bad_words(title):
                continue
            if not is_valid_title(title):
                continue
            if not _is_recent_day(published, days=7):  # допустим, не старше недели
                continue

            news_id = generate_id(url)

            # картинка остаётся как было (можно отключить, если не нужно)
            saved_img = None
            try:
                img_url = fetch_main_image(url)
                if img_url:
                    saved_img = download_image(img_url, IMG_DIR, news_id)
            except Exception:
                saved_img = None

            # ВАЖНО: пишем строго прежние поля
            collected.append({
                "id": news_id,
                "title": title,
                "url": url,
                "summary": news.get("summary", ""),
                "source": news.get("source") or src,
                "published_at": published,
                "image_path": saved_img  # может быть None
            })

    # дедуп по URL и сортировка по дате (новые сверху)
    collected = _dedup_by_url(collected)
    try:
        collected.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    except Exception:
        pass

    # сохраняем
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(collected, f, ensure_ascii=False, indent=2)

    log.info(f"✅ Saved {len(collected)} items to {DATA_FILE.resolve()}")
    return collected
