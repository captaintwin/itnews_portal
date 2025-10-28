from telegram import Bot
from telegram.error import TelegramError
import os
from html import unescape
import re
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT")
bot = Bot(token=BOT_TOKEN)

def clean_html(text):
    text = re.sub(r'<[^>]+>', '', text)
    return unescape(text)

def send_post(news_item):
    title = news_item.get("title", "Без названия")
    summary = news_item.get("summary", "")
    url = news_item.get("url", "")
    text = f"<b>{title}</b>\n\n{clean_html(summary)}\n\n<a href='{url}'>Читать далее →</a>"

    try:
        bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")
        print(f"[OK] Sent: {title}")
    except TelegramError as e:
        print(f"[Telegram error] {e}")
