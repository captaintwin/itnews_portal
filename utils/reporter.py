import json
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
from telegram import Bot
import os

# === Настройки окружения ===
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

REPORT_FILE = Path("data/report.txt")
SCHEDULE_FILE = Path("data/schedule.json")
TECH_CHAT = os.getenv("TELEGRAM_CHAT")
BOT_TOKEN = os.getenv("REPORT_TELEGRAM_TOKEN")


def send_report(selected: list[dict]):
    """Формирует и отправляет подробный отчёт о собранных статьях и расписании постов."""
    if not selected:
        print("⚠️ Пустой список статей — отчёт не сформирован.")
        return

    today = datetime.now().strftime("%d.%m.%Y %H:%M")
    total = len(selected)

    # === Загружаем расписание, если есть ===
    if SCHEDULE_FILE.exists():
        try:
            schedule = json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
        except Exception:
            schedule = []
    else:
        schedule = []

    # === Группировка по источникам ===
    sources = {}
    for i, n in enumerate(selected):
        src = n.get("source", "Неизвестный источник")
        n["_schedule_time"] = schedule[i] if i < len(schedule) else None
        sources.setdefault(src, []).append(n)

    # === Формирование HTML-отчёта ===
    lines = [
        f"<b>🗓 План публикаций на {today}</b>",
        f"Всего статей: <b>{total}</b>",
        "",
    ]

    for src, items in sources.items():
        lines.append(f"<b>📚 {src}</b> — {len(items)} статей")
        for n in sorted(items, key=lambda x: -x.get("char_count", 0))[:3]:
            title = n.get("title", "Без названия").strip().replace("<", "&lt;").replace(">", "&gt;")
            length = n.get("char_count", 0)
            pub_time = n.get("_schedule_time")
            if pub_time:
                lines.append(f" • {title}\n   ⏰ <i>{pub_time}</i> — {length} знаков")
            else:
                lines.append(f" • {title} <i>({length} знаков)</i>")
        lines.append("")

    text = "\n".join(lines).strip()

    # === Локальный .txt отчёт (без HTML) ===
    plain_text = text.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(plain_text, encoding="utf-8")

    # === Отправка в Telegram ===
    if not BOT_TOKEN or not TECH_CHAT:
        print("⚠️ Не задан TELEGRAM_CHAT или REPORT_TELEGRAM_TOKEN — отчёт не отправлен.")
        return

    bot = Bot(token=BOT_TOKEN)
    try:
        bot.send_message(chat_id=TECH_CHAT, text=text, parse_mode="HTML")
        print(f"✅ Отчёт отправлен в техчат ({total} статей).")
    except Exception as e:
        print(f"⚠️ Ошибка при отправке отчёта: {e}")
