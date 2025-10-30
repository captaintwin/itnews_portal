import json
from datetime import datetime, timedelta
from pathlib import Path
from core.logger import log


SCHEDULE_FILE = Path("data/schedule.json")


def build_schedule(news_count: int, start_hour: int = 5, end_hour: int = 22):
    """
    Создаёт равномерное расписание публикаций между start_hour и end_hour.
    Сохраняет результат в data/schedule.json.
    """
    if news_count <= 0:
        log.warning("⚠️ Нет новостей для построения расписания.")
        return []

    # начало и конец дня
    today = datetime.now()
    start_time = today.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    end_time = today.replace(hour=end_hour, minute=0, second=0, microsecond=0)

    # если текущее время уже позже старта (например, при ручном запуске)
    if datetime.now() > start_time:
        start_time = datetime.now() + timedelta(minutes=5)

    total_minutes = (end_time - start_time).total_seconds() / 60
    interval = total_minutes / news_count

    schedule = []
    for i in range(news_count):
        t = start_time + timedelta(minutes=i * interval)
        schedule.append(t.strftime("%H:%M"))

    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)

    first_time, last_time = schedule[0], schedule[-1]
    log.info(
        f"🕒 Расписание создано: {news_count} публикаций "
        f"с {first_time} до {last_time} (интервал ~{interval:.1f} мин)"
    )

    return schedule
