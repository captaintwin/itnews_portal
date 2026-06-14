# utils/watchdog.py — проверка пропущенного постинга и автозапуск itnews.service
import json
import subprocess
from datetime import datetime
from pathlib import Path

import pytz
from core.logger import log
from utils.alerts import alert

tz = pytz.timezone("Europe/Belgrade")
DATA = Path("data")
POST_LOG = DATA / "post_log.json"
SCHEDULE = DATA / "schedule.json"

SERVICE = "itnews.service"
# Окно, в котором имеет смысл догонять пропущенный запуск
WINDOW_START = (8, 50)   # после срабатывания таймера (08:45) + запас
WINDOW_END = (21, 0)


def _service_active() -> bool:
    r = subprocess.run(
        ["systemctl", "is-active", SERVICE],
        capture_output=True, text=True,
    )
    return r.stdout.strip() == "active"


def _posted_today(today: str) -> int:
    try:
        entries = json.loads(POST_LOG.read_text(encoding="utf-8"))
    except Exception:
        entries = []
    return sum(
        1 for e in entries
        if e.get("status") == "posted" and str(e.get("actual", "")).startswith(today)
    )


def _schedule_is_today(today: str) -> bool:
    try:
        schedule = json.loads(SCHEDULE.read_text(encoding="utf-8"))
    except Exception:
        return False
    return bool(schedule) and schedule[0].get("time", "").startswith(today)


def _in_recovery_window(now: datetime) -> bool:
    start = now.replace(hour=WINDOW_START[0], minute=WINDOW_START[1], second=0, microsecond=0)
    end = now.replace(hour=WINDOW_END[0], minute=WINDOW_END[1], second=0, microsecond=0)
    return start <= now < end


def needs_recovery(now: datetime | None = None) -> bool:
    """True, если сегодня ещё не было постов, сервис не работает и мы в окне постинга."""
    now = now or datetime.now(tz)
    today = now.strftime("%Y-%m-%d")

    if not _in_recovery_window(now):
        return False
    if _service_active():
        return False
    if _posted_today(today) > 0:
        # Уже что-то ушло — рестарт main.py сбросит sent_news и даст дубли
        return False
    return True


def recover():
    """Запускает itnews.service, если пропущен дневной прогон."""
    now = datetime.now(tz)
    if not needs_recovery(now):
        return False

    log.info("🔄 Watchdog: пропущен постинг, запускаю itnews.service")
    try:
        subprocess.run(["systemctl", "start", SERVICE], check=True)
        alert(
            f"Watchdog: сервер пропустил запуск ({now.strftime('%H:%M')}). "
            f"itnews.service стартовал автоматически."
        )
        return True
    except subprocess.CalledProcessError as e:
        alert(f"Watchdog: не удалось запустить {SERVICE}: {e}")
        return False


def check_alert_only():
    """Утренняя проверка: если к 10:15 всё ещё нет постов — алерт (recover уже не сработал)."""
    now = datetime.now(tz)
    today = now.strftime("%Y-%m-%d")
    if _posted_today(today) > 0 or _service_active():
        return
    alert(
        f"Watchdog: к {now.strftime('%H:%M')} нет публикаций за сегодня.\n"
        f"Проверь: journalctl -u itnews.service -n 50"
    )


def run():
    """Сначала попытка догнать пропущенный запуск, затем алерт (после 10:15)."""
    recover()
    now = datetime.now(tz)
    if (now.hour, now.minute) >= (10, 15):
        check_alert_only()


if __name__ == "__main__":
    run()
