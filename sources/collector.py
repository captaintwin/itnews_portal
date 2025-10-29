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
import random
from utils.helpers import generate_id, fetch_main_image, download_image

MAX_PER_SOURCE = 5  # максимум статей с одного источника

def collect_all():
    """Собирает новости (до 5 на источник), перемешивает и сохраняет в JSON."""
    img_root = Path("data/images")
    img_root.mkdir(parents=True, exist_ok=True)
    os.makedirs("data", exist_ok=True)

    all_news = []
    for src in RSS_SOURCES:
        try:
            items = fetch_rss(src, limit=MAX_PER_SOURCE)
        except Exception as e:
            log.error(f"Error fetching {src}: {e}")
            continue

        clean_items = []
        for news in items[:MAX_PER_SOURCE]:
            url = news.get("url")
            title = news.get("title", "")
            published = news.get("published_at") or datetime.utcnow().isoformat()
            news_id = generate_id(url)
            img_url = fetch_main_image(url)
            saved_img = download_image(img_url, img_root, news_id) if img_url else None

            clean_items.append({
                "id": news_id,
                "title": title,
                "url": url,
                "summary": news.get("summary", ""),
                "source": news.get("source", src),
                "published_at": published,
                "image_path": saved_img
            })

        all_news.extend(clean_items)

    # 🔄 Перемешиваем, чтобы не шли блоками по источникам
    random.shuffle(all_news)

    log.info(f"Total collected: {len(all_news)} (max {MAX_PER_SOURCE} per source)")

    # Сохраняем в JSON
    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(all_news, f, ensure_ascii=False, indent=2)

    return all_news



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
