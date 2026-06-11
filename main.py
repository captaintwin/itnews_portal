# main.py
from pathlib import Path

from core.logger import log
from sources.collector import collect_all
from utils.article_extractor import extract_all_articles
from utils.analyzer import analyze_articles
from utils.scheduler import build_schedule
from utils.reporter import send_report
from utils.post_next import post_next
from utils.stats import archive_day


def main():
    log.info("=== Сбор и анализ новостей ===")

    # === Сбрасываем историю отправленных постов и лог публикаций ===
    for fname in ("data/sent_news.json", "data/post_log.json"):
        f = Path(fname)
        if f.exists():
            try:
                f.unlink()
                log.info(f"♻️ Сброшен {f.name}.")
            except Exception as e:
                log.warning(f"⚠️ Не удалось удалить {f.name}: {e}")

    # 1️⃣ Сбор и анализ новостей
    collect_all()
    extract_all_articles()
    selected = analyze_articles()

    if not selected:
        log.warning("⚠️ Нет статей для публикации.")
        archive_day()
        return

    # 2️⃣ Формирование расписания и отчёта
    build_schedule()
    send_report(selected)

    # 3️⃣ Запуск постинга по расписанию
    log.info("🕒 Запуск режима планового постинга.")
    post_next()

    # 4️⃣ Архивация итогов дня в SQLite (для дашборда)
    archive_day()

    log.info("✅ Скрипт завершил работу за день.")


if __name__ == "__main__":
    main()
