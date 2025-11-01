# utils/scheduler.py
import json
import random
import os
from datetime import datetime, timedelta
from pathlib import Path
import pytz
from telegram import Bot
from core.logger import log


# === Пути и конфигурация ===
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
SELECTED_FILE = DATA_DIR / "selected.json"
SCHEDULE_FILE = DATA_DIR / "schedule.json"

# === Telegram ===
BOT_TOKEN = os.getenv("REPORT_TELEGRAM_TOKEN")
TECH_CHAT_ID = os.getenv("TELEGRAM_CHAT")

# === Локальный часовой пояс ===
tz = pytz.timezone("Europe/Belgrade")


def build_schedule(
    start_hour: int = 9,
    end_hour: int = 21,
    per_source_limit: int = 5,
    daily_limit: int = 20,
):
    """
    Формирует равномерное расписание публикаций на день.
    - ограничивает максимум per_source_limit статей с одного источника
    - максимум daily_limit публикаций в день
    - перемешивает порядок
    - сохраняет расписание в data/schedule.json
    - отправляет отчёт в техчат
    """

    # === Загружаем отобранные новости ===
    if not SELECTED_FILE.exists():
        log.warning("⚠️ Файл selected.json не найден, нечего планировать.")
        return []

    with open(SELECTED_FILE, "r", encoding="utf-8") as f:
        selected = json.load(f)

    if not selected:
        log.warning("⚠️ Нет новостей для расписания.")
        return []

    # === Ограничиваем по источникам ===
    filtered = []
    source_counter = {}
    for item in selected:
        src = item.get("source", "unknown")
        if source_counter.get(src, 0) < per_source_limit:
            filtered.append(item)
            source_counter[src] = source_counter.get(src, 0) + 1

    # === Перемешиваем, чтобы чередовались источники ===
    random.shuffle(filtered)

    # === Применяем дневной лимит ===
    if len(filtered) > daily_limit:
        filtered = filtered[:daily_limit]
        log.info(f"📊 Ограничено дневным лимитом: {daily_limit} статей.")
    else:
        log.info(f"📊 Всего статей для публикации: {len(filtered)}")

    news_count = len(filtered)
    if news_count == 0:
        log.warning("⚠️ После фильтрации не осталось статей.")
        return []

    # === Расчёт времени ===
    now = datetime.now(tz)
    start_time = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    end_time = now.replace(hour=end_hour, minute=0, second=0, microsecond=0)

    if now > start_time:
        start_time = now + timedelta(minutes=5)

    total_minutes = (end_time - start_time).total_seconds() / 60
    interval = total_minutes / news_count

    # === Формируем план ===
    schedule = []
    for i, item in enumerate(filtered):
        post_time = start_time + timedelta(minutes=i * interval)
        schedule.append({
            "time": post_time.strftime("%Y-%m-%d %H:%M"),
            "title": item.get("title", "Без названия"),
            "source": item.get("source", ""),
            "url": item.get("url", ""),
            "id": item.get("id", ""),
        })

    # === Сохраняем план ===
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)

    first_time = schedule[0]["time"].split(" ")[1]
    last_time = schedule[-1]["time"].split(" ")[1]
    log.info(
        f"🕒 Расписание создано: {news_count} публикаций "
        f"с {first_time} до {last_time} (интервал ~{interval:.1f} мин)"
    )

    # === Отправляем отчёт ===
    send_schedule_report(schedule)

    return schedule


def send_schedule_report(plan):
    """Отправляет в техчат краткий отчёт о плане публикаций."""
    if not BOT_TOKEN or not TECH_CHAT_ID:
        log.warning("⚠️ Не заданы TELEGRAM_CHAT или REPORT_TELEGRAM_TOKEN.")
        return

    bot = Bot(token=BOT_TOKEN)
    text = "<b>🗓 План публикаций на день</b>\n\n"

    for item in plan:
        text += f"🕒 {item['time']}\n<b>{item['title']}</b>\n<i>{item['source']}</i>\n\n"

    try:
        bot.send_message(chat_id=TECH_CHAT_ID, text=text.strip(), parse_mode="HTML")
        log.info("📨 План публикаций успешно отправлен в техчат.")
    except Exception as e:
        log.error(f"⚠️ Ошибка при отправке отчёта в Telegram: {e}")
