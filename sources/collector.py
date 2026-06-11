import os
import json
import random
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from core.logger import log
from sources.rss import fetch_rss
from utils.helpers import generate_id, fetch_main_image, download_image

# === НАСТРОЙКИ ===
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
IMG_DIR = DATA_DIR / "images"
NEWS_PATH = DATA_DIR / "news.json"
SCHEDULE_FILE = Path("data/schedule.json")

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
    "https://www.analyticsvidhya.com/blog/feed/",
    "https://www.marktechpost.com/feed/",
    "https://thenewstack.io/feed/",
    "https://towardsdatascience.com/feed",
    "https://ai.googleblog.com/feeds/posts/default",
    "https://openai.com/blog/rss",

]

def build_schedule(news_count, start_hour=5, end_hour=22):
    """Создаёт расписание постинга на день."""
    start = datetime.combine(datetime.today(), datetime.min.time()).replace(hour=start_hour)
    total_minutes = (end_hour - start_hour) * 60
    if news_count == 0:
        return []
    interval = total_minutes / news_count

    times = [start + timedelta(minutes=i * interval) for i in range(news_count)]
    schedule = [t.strftime("%H:%M") for t in times]

    SCHEDULE_FILE.write_text(json.dumps(schedule, indent=2), encoding="utf-8")
    log.info(f"🕒 Сформировано расписание из {len(schedule)} публикаций каждые {interval:.1f} мин.")
    return schedule

def load_existing_ids():
    """Загружает уже собранные новости (для защиты от дублей)."""
    if NEWS_PATH.exists():
        try:
            with open(NEWS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {item["id"] for item in data.get("items", [])}
        except Exception as e:
            log.warning(f"⚠️ Не удалось загрузить {NEWS_PATH}: {e}")
    return set()


def safe_fetch_image(url):
    """Безопасно получает ссылку на главное изображение."""
    try:
        return fetch_main_image(url)
    except Exception as e:
        log.warning(f"⚠️ Ошибка поиска изображения: {e}")
        return None


def is_today(published_at):
    """Проверяет, относится ли дата публикации к сегодняшнему дню."""
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return dt.date() == date.today()
    except Exception:
        return False


def collect_from_source(src):
    """Собирает новости за сегодня из одного RSS-источника."""
    collected = []
    try:
        items = fetch_rss(src)
    except Exception as e:
        log.error(f"❌ Ошибка при парсинге {src}: {e}")
        return collected

    if not items:
        log.warning(f"⚠️ Пустой RSS: {src}")
        return collected

    today_items = [n for n in items if is_today(n.get("published_at", ""))]
    log.info(f"📡 {src} → найдено {len(today_items)} новостей за сегодня")

    for news in today_items:
        url = news.get("url")
        if not url:
            continue

        title = news.get("title", "").strip()
        summary = news.get("summary", "")
        published = news.get("published_at") or datetime.utcnow().isoformat()
        source = news.get("source", src)
        news_id = generate_id(url)

        # Ищем изображение
        img_url = safe_fetch_image(url)
        img_path = None
        if img_url:
            img_path = download_image(img_url, IMG_DIR, news_id)
            if img_path:
                log.info(f"🖼 {title[:60]}... — изображение сохранено")
            else:
                log.warning(f"⚠️ Не удалось скачать изображение: {title}")
        else:
            log.warning(f"⚠️ Изображение не найдено: {title}")

        collected.append({
            "id": news_id,
            "title": title,
            "url": url,
            "summary": summary[:600],
            "source": source,
            "published_at": published,
            "image_path": str(img_path) if img_path else None,
        })

    return collected

def save_to_json(items):
    """Сохраняет результат в JSON с метаданными."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    output = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "total": len(items),
        "items": items,
    }

    with open(NEWS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    log.info(f"✅ Сохранено {len(items)} новостей в {NEWS_PATH.resolve()}")


def collect_all():
    """Основная функция: сбор только свежих (сегодняшних) новостей без дублей."""
    log.info("🚀 Старт сбора новостей за сегодня")

    existing_ids = load_existing_ids()
    all_news = []

    for src in RSS_SOURCES:
        source_news = collect_from_source(src)
        for item in source_news:
            # Пропускаем дубли по ID
            if item["id"] in existing_ids:
                continue

            # Пропускаем старые публикации (не за сегодня)
            try:
                pub_date = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00")).date()
                if pub_date != date.today():
                    continue
            except Exception:
                continue

            all_news.append(item)
            existing_ids.add(item["id"])

    # Перемешиваем, чтобы источники чередовались
    random.shuffle(all_news)

    # Логируем итоги
    total = len(all_news)
    log.info(f"📰 После фильтрации по дате и дублям осталось {total} свежих новостей.")

    # Сохраняем и создаём расписание
    save_to_json(all_news)
    build_schedule(total)

    log.info(f"✅ Сохранено {total} актуальных новостей и создано расписание.")
    return all_news
