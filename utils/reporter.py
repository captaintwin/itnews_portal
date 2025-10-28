import json
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
from telegram import Bot
import os

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

REPORT_FILE = Path("data/report.txt")
TECH_CHAT = os.getenv("TELEGRAM_CHAT")
BOT_TOKEN = os.getenv("REPORT_TELEGRAM_TOKEN")

def send_report(selected):
    report_lines = [
        f"=== План публикаций на {datetime.now().date()} ===",
        f"Всего статей: {len(selected)}",
        ""
    ]
    for n in selected[:10]:
        report_lines.append(f"• {n['source']}: {n['title']} ({n['char_count']} знаков)")

    REPORT_FILE.write_text("\n".join(report_lines), encoding="utf-8")

    bot = Bot(token=BOT_TOKEN)
    bot.send_message(chat_id=TECH_CHAT, text=REPORT_FILE.read_text(), parse_mode="HTML")
