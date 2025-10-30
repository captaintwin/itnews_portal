import json
from datetime import datetime
from pathlib import Path

from core.logger import log
from sources.collector import collect_all
from utils.analyzer import analyze_articles  # выбирает топовые статьи
from utils.reporter import send_report         # формирует отчёт и отправляет в техчат
from utils.scheduler import build_schedule   # рассчитывает расписание постов


# === Пути данных ===
DATA_DIR = Path("data")
NEWS_FILE = DATA_DIR / "news.json"
SELECTED_FILE = DATA_DIR / "selected.json"
SCHEDULE_FILE = DATA_DIR / "schedule.json"
STATE_FILE = DATA_DIR / "state.json"


def main():
    log.info("🚀 Запуск утреннего пайплайна сбора и анализа новостей")

    # 1️⃣ Сбор всех новостей из RSS
    news = collect_all()
    if not news:
        log.warning("⚠️ Новости не собраны, выход.")
        return

    # 2️⃣ Формирование расписания (с 05:00 до 22:00)
    build_schedule(len(news))

    # 3️⃣ Анализ статей — выбираем по 3 самых длинных с каждого источника
    selected = analyze_articles(top_n=3)
    if not selected:
        log.warning("⚠️ Не выбрано ни одной статьи.")
        return

    # 4️⃣ Сохраняем список выбранных статей
    SELECTED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SELECTED_FILE, "w", encoding="utf-8") as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)

    # 5️⃣ Генерируем и отправляем отчёт
    send_report(selected)

    # 6️⃣ Сбрасываем state.json для постинга заново
    STATE_FILE.write_text(json.dumps({"last_index": -1}, indent=2), encoding="utf-8")

    log.info("✅ Утренний сбор новостей завершён успешно.")


if __name__ == "__main__":
    main()
