# utils/post_next.py
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
import pytz
from core.logger import log
from utils.post_to_telegram import send_post

# === Пути ===
DATA_DIR = Path("data")
SCHEDULE_FILE = DATA_DIR / "schedule.json"
SELECTED_FILE = DATA_DIR / "selected.json"
SENT_FILE = DATA_DIR / "sent_news.json"

# === Часовой пояс ===
tz = pytz.timezone("Europe/Belgrade")


def load_json(path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning(f"⚠️ Ошибка чтения {path.name}: {e}")
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def post_next(instant=False):
    """Фоновая публикация новостей по расписанию или мгновенно при instant=True."""
    log.info("🚀 Запуск постинга по расписанию")

    schedule = load_json(SCHEDULE_FILE, [])
    selected = load_json(SELECTED_FILE, [])
    sent = set(load_json(SENT_FILE, []))

    if not schedule or not selected:
        log.warning("⚠️ Нет расписания или списка статей — постинг невозможен.")
        return

    # === Сопоставление расписания и статей ===
    schedule_map = {}
    for i, s in enumerate(schedule):
        try:
            t = s["time"] if isinstance(s, dict) else s
            news_id = s.get("id") if isinstance(s, dict) else selected[i].get("id")
            schedule_map[news_id] = datetime.strptime(t, "%Y-%m-%d %H:%M")
        except Exception:
            continue

    log.info(f"📋 Загружено расписание на {len(schedule_map)} постов.")

    if instant:
        log.info("⚡ Режим instant: публикуем все посты сразу.")
        for item in selected:
            news_id = item.get("id")
            if news_id in sent:
                continue
            try:
                send_post(item)
                sent.add(news_id)
                save_json(SENT_FILE, list(sent))
                log.info(f"✅ Опубликовано: {item['title']}")
                time.sleep(2)  # небольшая пауза между постами
            except Exception as e:
                log.error(f"❌ Ошибка при публикации {item.get('title')}: {e}")
        return

    # === Обычный режим (фон, проверка по времени) ===
    while True:
        now = datetime.now(tz)
        for item in selected:
            news_id = item.get("id")
            post_time = schedule_map.get(news_id)
            if not post_time:
                continue

            if post_time.tzinfo is None:
                post_time = tz.localize(post_time)

            if news_id in sent:
                continue

            # Если текущее время >= времени поста
            if now >= post_time:
                try:
                    send_post(item)
                    sent.add(news_id)
                    save_json(SENT_FILE, list(sent))
                    log.info(f"✅ Опубликовано: {item['title']}")
                except Exception as e:
                    log.error(f"❌ Ошибка при публикации {item.get('title')}: {e}")

        time.sleep(60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post IT news according to schedule")
    parser.add_argument("--instant", action="store_true", help="publish all posts immediately")
    args = parser.parse_args()

    post_next(instant=args.instant)
