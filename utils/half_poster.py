import json
import time
from datetime import datetime
from utils.post_to_telegram import send_post
from core.logger import log


def post_half():
    """Постит первую или вторую половину selected.json равномерно в течение 6 часов"""
    with open("data/selected.json", "r", encoding="utf-8") as f:
        items = json.load(f)

    if not items:
        log.warning("⚠️ Нет статей для публикации.")
        return

    half = len(items) // 2
    current_hour = datetime.now().hour

    if current_hour < 12:
        subset = items[:half]
        log.info(f"📤 Публикуется первая половина ({len(subset)} новостей).")
    else:
        subset = items[half:]
        log.info(f"📤 Публикуется вторая половина ({len(subset)} новостей).")

    # Публикуем равномерно в течение 6 часов
    total_posts = len(subset)
    total_duration = 6 * 60 * 60  # 6 часов в секундах
    interval = total_duration / total_posts

    for i, news in enumerate(subset, 1):
        try:
            send_post(news)
            log.info(f"✅ Опубликовано {i}/{total_posts}: {news.get('title')}")
        except Exception as e:
            log.error(f"Ошибка при публикации {news.get('title')}: {e}")

        if i < total_posts:
            log.info(f"⏱ Следующий пост через {int(interval // 60)} мин {int(interval % 60)} сек")
            time.sleep(interval)
