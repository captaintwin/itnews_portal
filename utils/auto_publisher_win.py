import json
import time
import os
from datetime import datetime
from pathlib import Path
import pytz
from telegram import Bot, TelegramError
from dotenv import load_dotenv

# === Импорты твоих модулей ===
from core.logger import log
from sources.collector import collect_all
from utils.article_extractor import extract_all_articles
from utils.analyzer import analyze_articles
from utils.scheduler import build_schedule

# === Инициализация ===
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT")
tz = pytz.timezone("Europe/Belgrade")

DATA_DIR = Path("data")
SCHEDULE_FILE = DATA_DIR / "schedule.json"
POSTED_FILE = DATA_DIR / "posted.json"

bot = Bot(token=BOT_TOKEN)

# === Постинг ===
def load_schedule():
    if not SCHEDULE_FILE.exists():
        return []
    with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def mark_posted(post_id):
    posted = []
    if POSTED_FILE.exists():
        posted = json.load(open(POSTED_FILE, "r", encoding="utf-8"))
    posted.append(post_id)
    json.dump(posted, open(POSTED_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def is_posted(post_id):
    if not POSTED_FILE.exists():
        return False
    posted = json.load(open(POSTED_FILE, "r", encoding="utf-8"))
    return post_id in posted

def post_news(item):
    text = f"<b>{item['title']}</b>\n<i>{item['source']}</i>\n\n<a href='{item['url']}'>Читать далее →</a>"
    try:
        bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")
        log.info(f"[OK] Опубликовано: {item['title']}")
        mark_posted(item['id'])
    except TelegramError as e:
        log.error(f"[Ошибка Telegram] {e}")

def auto_post_loop():
    log.info("🚀 Автопостинг запущен.")
    while True:
        schedule = load_schedule()
        now = datetime.now(tz).strftime("%Y-%m-%d %H:%M")

        for item in schedule:
            if item["time"] <= now and not is_posted(item["id"]):
                post_news(item)

        time.sleep(60)  # Проверка раз в минуту


# === Главный процесс ===
def main():
    log.info("=== 📰 СТАРТ: сбор и публикация новостей ===")

    # 1️⃣ Сбор и анализ
    log.info("📡 Сбор RSS-новостей...")
    collect_all()

    log.info("📄 Извлечение текстов...")
    extract_all_articles()

    log.info("🤖 Анализ контента...")
    selected = analyze_articles()
    if not selected:
        log.warning("⚠️ Нет подходящих статей.")
        return

    # 2️⃣ Планирование публикаций
    log.info("📅 Создание расписания...")
    build_schedule()

    # 3️⃣ Автопостинг
    log.info("▶️ Запуск цикла автопостинга...")
    auto_post_loop()


if __name__ == "__main__":
    main()
