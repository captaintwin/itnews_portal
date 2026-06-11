from telegram import Bot
from telegram.error import RetryAfter, TelegramError
from pathlib import Path
import os
import time
from html import unescape
import re
from urllib.parse import urlparse
from dotenv import load_dotenv

# === Настройки окружения ===
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
# Новости — в публичный канал; если он не задан, фолбэк на техчат
CHAT_ID = os.getenv("TELEGRAM_CHANNEL") or os.getenv("TELEGRAM_CHAT")

bot = Bot(token=BOT_TOKEN)

# === Утилита для очистки HTML из summary ===
def clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)  # удаляем HTML-теги
    return unescape(text).strip()


def source_link(news_item: dict) -> str:
    """Имя источника со ссылкой на его сайт (домен берём из URL статьи)."""
    url = news_item.get("url", "")
    netloc = urlparse(url).netloc
    # «Engadget - Technology News & Expert Reviews» → «Engadget»
    name = re.split(r"\s+[-|–]\s+", news_item.get("source", ""))[0].strip()
    if not name:
        name = netloc.removeprefix("www.")
    if not netloc:
        return name
    return f'<a href="https://{netloc}">{name}</a>'

# === Основная функция отправки поста ===
def send_post(news_item: dict) -> bool:
    """
    Отправляет пост в Telegram. Возвращает True при успехе.
    При flood control (RetryAfter) ждёт и повторяет до 3 раз.
    Если указано image_path и файл существует — отправляет с фото.
    """
    title = news_item.get("title", "Без названия")
    summary = news_item.get("summary", "")
    url = news_item.get("url", "")
    img_path = news_item.get("image_path", "")

    # Формируем текст поста
    text = (
        f"<b>{title}</b>\n\n"
        f"{clean_html(summary)}\n\n"
        f"<a href='{url}'>Читать далее →</a>\n"
        f"📰 {source_link(news_item)}"
    )

    for attempt in range(3):
        try:
            if img_path and Path(img_path).exists():
                with open(img_path, "rb") as photo:
                    bot.send_photo(
                        chat_id=CHAT_ID,
                        photo=photo,
                        caption=text,
                        parse_mode="HTML",
                    )
                print(f"[OK] Sent with image: {title}")
            else:
                bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")
                print(f"[OK] Sent without image: {title}")
            return True

        except RetryAfter as e:
            wait = int(getattr(e, "retry_after", 30)) + 1
            print(f"[Flood control] Жду {wait}s (попытка {attempt + 1}/3): {title}")
            time.sleep(wait)
        except TelegramError as e:
            print(f"[Telegram error] {e}")
            return False

    return False
