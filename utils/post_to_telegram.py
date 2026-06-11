from telegram import Bot
from telegram.error import TelegramError
from pathlib import Path
import os
from html import unescape
import re
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

# === Основная функция отправки поста ===
def send_post(news_item: dict):
    """
    Отправляет пост в Telegram.
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
        f"<a href='{url}'>Читать далее →</a>"
    )

    try:
        if img_path and Path(img_path).exists():
            # === Отправляем с изображением ===
            with open(img_path, "rb") as photo:
                bot.send_photo(
                    chat_id=CHAT_ID,
                    photo=photo,
                    caption=text,
                    parse_mode="HTML",
                )
            print(f"[OK] Sent with image: {title}")
        else:
            # === Если нет картинки — обычное сообщение ===
            bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")
            print(f"[OK] Sent without image: {title}")

    except TelegramError as e:
        print(f"[Telegram error] {e}")
