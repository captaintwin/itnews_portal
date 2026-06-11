# utils/alerts.py — тревожные уведомления в техчат
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from core.logger import log

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
TOKEN = os.getenv("REPORT_TELEGRAM_TOKEN") or os.getenv("TELEGRAM_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT")


def alert(text: str):
    """Отправляет сообщение о проблеме в техчат. Никогда не бросает исключений."""
    log.error(f"🚨 ALERT: {text}")
    if not TOKEN or not CHAT:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT, "text": f"🚨 itnews\n{text}"[:4000]},
            timeout=15,
        )
    except Exception as e:
        log.error(f"⚠️ Не удалось отправить алерт: {e}")
