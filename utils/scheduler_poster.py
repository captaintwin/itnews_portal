# utils/scheduler_poster.py
import json
import time
from datetime import datetime, timedelta
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from utils.post_to_telegram import send_post
from telegram import Bot
from core.config import TELEGRAM_TOKEN, REPORT_TELEGRAM_TOKEN, TELEGRAM_CHAT # <-- централизованно
from core.logger import log
from pathlib import Path

# === Конфигурация ===
tz = pytz.timezone("Europe/Belgrade")
SELECTED_FILE = Path("data/selected.json")


def schedule_posts():
    """Равномерно планирует публикации на следующий день и отправляет отчёт в техчат."""
    if not SELECTED_FILE.exists():
        log.warning("⚠️ Файл data/selected.json не найден — нечего постить.")
        return

    with open(SELECTED_FILE, "r", encoding="utf-8") as f:
        selected = json.load(f)

    if not selected:
        log.warning("⚠️ Список статей для публикации пуст.")
        return

    # === Расчёт времени ===
    scheduler = BackgroundScheduler(timezone=tz)
    interval = 12 * 60 / len(selected)  # равномерно на 12 часов (09:00–21:00)

    now = datetime.now(tz)
    start_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if now.hour >= 9:
        start_time += timedelta(days=1)

    schedule_plan = []
    for i, item in enumerate(selected):
        post_time = start_time + timedelta(minutes=i * interval)
        scheduler.add_job(send_post, "date", run_date=post_time, args=[item])
        schedule_plan.append({
            "title": item["title"],
            "source": item.get("source", ""),
            "time": post_time.strftime("%Y-%m-%d %H:%M"),
        })
        log.info(f"📅 Запланировано: {item['title']} — {post_time.strftime('%Y-%m-%d %H:%M')}")

    # === Отправляем отчёт в техчат ===
    send_schedule_report(schedule_plan)

    # === Запускаем планировщик ===
    scheduler.start()
    log.info("✅ Планировщик запущен. Постинг идёт в фоне.")

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        log.info("🛑 Планировщик остановлен.")


def send_schedule_report(plan):
    """Отправляет отчёт с планом постов в техчат."""
    if not REPORT_TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        print("⚠️ Ошибка: отсутствует BOT_TOKEN или TECH_CHAT в конфигурации.")
        return

    bot = Bot(token=REPORT_TELEGRAM_TOKEN)
    text = "<b>🗓 План публикаций на день</b>\n\n"
    for item in plan:
        text += f"🕒 {item['time']}\n<b>{item['title']}</b>\n<i>{item['source']}</i>\n\n"

    try:
        bot.send_message(chat_id=TELEGRAM_CHAT, text=text.strip(), parse_mode="HTML")
        log.info("📨 Отчёт с планом публикаций отправлен в техчат.")
    except Exception as e:
        log.error(f"⚠️ Ошибка при отправке отчёта в техчат: {e}")
