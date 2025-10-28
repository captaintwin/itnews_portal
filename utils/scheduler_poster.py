# utils/scheduler_poster.py
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Bot

from utils.post_to_telegram import send_post
from core.config import TELEGRAM_CHAT, REPORT_TELEGRAM_TOKEN
from core.logger import log


# === Конфигурация ===
tz = pytz.timezone("Europe/Belgrade")
SELECTED_FILE = Path("data/selected.json")


def schedule_posts():
    """Планирует публикации на текущий день и отправляет отчёт в техчат."""
    if not SELECTED_FILE.exists():
        log.warning("⚠️ data/selected.json не найден — нечего постить.")
        return

    with SELECTED_FILE.open("r", encoding="utf-8") as f:
        selected = json.load(f)

    if not selected:
        log.warning("⚠️ Список статей для публикации пуст.")
        return

    # === Расчёт временного диапазона ===
    scheduler = BackgroundScheduler(timezone=tz)
    now = datetime.now(tz)
    start_time = now + timedelta(minutes=10)  # старт через 10 минут после сбора
    end_time = now.replace(hour=23, minute=0, second=0, microsecond=0)

    total_minutes = max(1, (end_time - start_time).total_seconds() / 60)
    interval = total_minutes / len(selected)

    schedule_plan = []
    for i, item in enumerate(selected):
        post_time = start_time + timedelta(minutes=i * interval)
        scheduler.add_job(send_post, "date", run_date=post_time, args=[item])

        schedule_plan.append({
            "title": item.get("title", "Без названия")[:180],
            "source": item.get("source", ""),
            "time": post_time.strftime("%Y-%m-%d %H:%M"),
        })
        log.info(f"📅 Запланировано: {item.get('title', '')[:60]} — {post_time.strftime('%H:%M')}")

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


def send_schedule_report(plan: list[dict]):
    """Отправляет отчёт с планом постов в техчат."""
    if not TELEGRAM_CHAT or not REPORT_TELEGRAM_TOKEN:
        log.error("❌ Нет REPORT_TELEGRAM_TOKEN или TELEGRAM_CHAT в конфигурации. Отчёт не отправлен.")
        return

    bot = Bot(token=TELEGRAM_CHAT)

    lines = ["<b>🗓 План публикаций на сегодня</b>", ""]
    for item in plan:
        lines.append(f"🕒 {item['time']}\n<b>{item['title']}</b>\n<i>{item['source']}</i>\n")
    text = "\n".join(lines).strip()

    try:
        bot.send_message(chat_id=REPORT_TELEGRAM_TOKEN, text=text, parse_mode="HTML")
        log.info("📨 Отчёт с планом публикаций отправлен в техчат.")
    except Exception as e:
        log.error(f"⚠️ Ошибка при отправке отчёта в техчат: {e}")
