import json
from datetime import datetime
from utils.post_to_telegram import send_post
from core.logger import log

def post_half():
    """Постит первую или вторую половину списка selected.json"""
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

    for news in subset:
        try:
            send_post(news)
        except Exception as e:
            log.error(f"Ошибка при публикации {news.get('title')}: {e}")
