import json
import time
import os
from pathlib import Path
from telegram import Bot
from telegram.error import TelegramError
from PIL import Image
from dotenv import load_dotenv
load_dotenv()

print("DEBUG TOKEN:", os.getenv("TELEGRAM_TOKEN"))
print("DEBUG CHAT:", os.getenv("TELEGRAM_CHAT"))

# === НАСТРОЙКИ ===
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT")

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
NEWS_FILE = DATA_DIR / "news.json"
IMAGES_DIR = DATA_DIR / "images"
SENT_LOG = DATA_DIR / "sent_news.json"

bot = Bot(token=BOT_TOKEN)


def load_sent_ids():
    """Загружает список уже отправленных ID новостей"""
    if SENT_LOG.exists():
        with open(SENT_LOG, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_sent_ids(sent_ids):
    """Сохраняет обновлённый список отправленных ID"""
    with open(SENT_LOG, "w", encoding="utf-8") as f:
        json.dump(list(sent_ids), f, ensure_ascii=False, indent=2)


import re
from html import unescape

def format_post(news_item):
    """Форматирует текст поста и очищает HTML"""
    title = news_item.get("title", "Без названия")
    summary = news_item.get("summary", "")
    url = news_item.get("url", "")
    source = news_item.get("source", "")
    date = news_item.get("published_at", "")[:10]

    # 1. Убираем все HTML-теги, кроме <b>, <i> и <a href="">
    summary = re.sub(r'<(?!\/?(b|i|a)( |>))[^>]+>', '', summary)

    # 2. Раскодируем HTML-сущности (&amp;, &#39; и т.п.)
    summary = unescape(summary)

    # 3. Ограничим длину описания (чтобы Telegram не ругался)
    if len(summary) > 900:
        summary = summary[:897].rsplit(' ', 1)[0] + "…"

    invisible = "\u2063"
    return (
        f"<b>{title}</b>\n"
        f"{summary.strip()}\n\n"
        f"Источник: <i>{source}</i> | {date}\n"
        f"<a href='{url}'>Читать далее →</a>\n\n"
        f"{invisible}"
    )

def get_image_path(news_id: str):
    """Находит изображение по ID новости"""
    candidates = [
        IMAGES_DIR / f"preview_{news_id}.jpg",
        IMAGES_DIR / f"preview_{news_id}.png",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def prepare_image(image_path, max_size=1280):
    """Масштабирует изображение под Telegram"""
    img = Image.open(image_path).convert("RGB")
    w, h = img.size

    if max(w, h) <= max_size:
        temp_path = image_path.parent / f"tg_{image_path.stem}.jpg"
        img.save(temp_path, "JPEG", quality=90)
        img.close()
        return temp_path

    ratio = max_size / max(w, h)
    new_size = (int(w * ratio), int(h * ratio))
    img_resized = img.resize(new_size, Image.LANCZOS)

    temp_path = image_path.parent / f"tg_{image_path.stem}.jpg"
    img_resized.save(temp_path, "JPEG", quality=90)
    img.close()
    img_resized.close()
    return temp_path


def send_post(news_item):
    """Отправляет новость в Telegram"""
    text = format_post(news_item)
    news_id = news_item.get("id")
    image_path = get_image_path(news_id)

    try:
        if image_path:
            formatted_path = prepare_image(image_path)
            with open(formatted_path, "rb") as img:
                bot.send_photo(chat_id=CHAT_ID, photo=img, caption=text, parse_mode="HTML")
            os.remove(formatted_path)
        else:
            bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")

        print(f"[OK] Опубликовано: {news_item['title']}")
    except TelegramError as e:
        print(f"[Ошибка Telegram] {e}")
    except Exception as e:
        print(f"[Ошибка публикации {news_id}] {e}")


def main():
    sent_ids = load_sent_ids()

    with open(NEWS_FILE, "r", encoding="utf-8") as f:
        news_list = json.load(f)

    # сортируем по дате (новые сначала)
    news_list.sort(key=lambda x: x.get("published_at", ""), reverse=True)

    for item in news_list:
        news_id = item.get("id")
        if not news_id or news_id in sent_ids:
            continue

        send_post(item)
        sent_ids.add(news_id)
        save_sent_ids(sent_ids)
        time.sleep(3)  # задержка между постами


if __name__ == "__main__":
    main()  # локальный запуск

# чтобы main() можно было вызвать из других модулей
__all__ = ["main"]

