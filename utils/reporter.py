import json
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
from telegram import Bot
from io import BytesIO
import os
import traceback
import time

# === Настройки окружения ===
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

REPORT_FILE = Path("data/report.txt")
SCHEDULE_FILE = Path("data/schedule.json")
TECH_CHAT = os.getenv("TELEGRAM_CHAT")
BOT_TOKEN = os.getenv("REPORT_TELEGRAM_TOKEN")


def send_report(selected: list[dict]):
    """Формирует и отправляет отчёт: отдельное сообщение по каждому источнику."""
    if not selected:
        print("⚠️ Пустой список статей — отчёт не сформирован.")
        return

    today = datetime.now().strftime("%d.%m.%Y %H:%M")
    total = len(selected)

    # === Загружаем расписание (если есть) ===
    schedule = []
    if SCHEDULE_FILE.exists():
        try:
            schedule = json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    # === Группировка по источникам ===
    sources = {}
    for i, n in enumerate(selected):
        src = n.get("source", "Неизвестный источник")
        n["_schedule_time"] = schedule[i]["time"] if i < len(schedule) and "time" in schedule[i] else None
        sources.setdefault(src, []).append(n)

    # === Сохраняем полный текст отчёта ===
    lines = [f"🗓 Отчёт о публикациях на {today}\nВсего статей: {total}\n"]
    for src, items in sources.items():
        lines.append(f"\n📚 {src} ({len(items)} статей):")
        for n in items:
            title = n.get("title", "Без названия")
            url = n.get("url", "")
            time_str = n.get("_schedule_time", "")
            lines.append(f" • {title} — {time_str} ({url})")

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")

    # === Telegram ===
    if not BOT_TOKEN or not TECH_CHAT:
        print("⚠️ Не заданы TELEGRAM_CHAT или REPORT_TELEGRAM_TOKEN — отчёт не отправлен.")
        return

    bot = Bot(token=BOT_TOKEN)

    try:
        bot.send_message(
            chat_id=TECH_CHAT,
            text=f"📰 Отчёт о публикациях на {today}\nВсего статей: {total}\nИсточников: {len(sources)}",
        )

        # === Отправляем по источникам ===
        for src, items in sources.items():
            text = [f"<b>📚 {src}</b> — {len(items)} статей\n"]
            for n in items[:10]:  # максимум 10 постов на источник
                title = n.get("title", "Без названия").replace("<", "&lt;").replace(">", "&gt;")
                url = n.get("url", "")
                pub_time = n.get("_schedule_time")
                link = f'<a href="{url}">{title}</a>' if url else title
                line = f"• {link}"
                if pub_time:
                    line += f"\n   ⏰ <i>{pub_time}</i>"
                text.append(line)

            text_block = "\n".join(text).strip()
            bot.send_message(chat_id=TECH_CHAT, text=text_block, parse_mode="HTML")
            print(f"✅ Отправлен блок: {src}")
            time.sleep(1.5)  # небольшая пауза между отправками, чтобы не попасть в лимиты

        # === Прикрепляем файл со всем отчётом ===
        file_data = BytesIO(REPORT_FILE.read_bytes())
        bot.send_document(
            chat_id=TECH_CHAT,
            document=file_data,
            filename="report.txt",
            caption=f"📎 Полный отчёт ({total} статей, {len(sources)} источников)",
        )

        print("✅ Отчёт успешно отправлен по блокам.")

    except Exception as e:
        print(f"⚠️ Ошибка при отправке отчёта: {e}")
        traceback.print_exc()
