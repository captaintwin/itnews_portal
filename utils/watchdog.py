# utils/watchdog.py — алерт, если за сегодня ещё не было ни одной публикации.
# Запускается systemd-таймером утром (после старта основного прогона).
import json
from datetime import datetime
from pathlib import Path

import pytz
from utils.alerts import alert

tz = pytz.timezone("Europe/Belgrade")
POST_LOG = Path("data/post_log.json")


def check():
    now = datetime.now(tz)
    today = now.strftime("%Y-%m-%d")
    try:
        entries = json.loads(POST_LOG.read_text(encoding="utf-8"))
    except Exception:
        entries = []

    posted_today = [
        e for e in entries
        if e.get("status") == "posted" and str(e.get("actual", "")).startswith(today)
    ]
    if not posted_today:
        alert(
            f"Watchdog: к {now.strftime('%H:%M')} нет ни одной публикации за сегодня.\n"
            f"Проверь: journalctl -u itnews.service -n 50"
        )


if __name__ == "__main__":
    check()
