# main.py
from datetime import datetime
from pathlib import Path
import pytz

from core.logger import log
from sources.collector import collect_all
from utils.article_extractor import extract_all_articles
from utils.analyzer import analyze_articles
from utils.scheduler import build_schedule
from utils.reporter import send_report
from utils.post_next import post_next


tz = pytz.timezone("Europe/Belgrade")

def main():
    log.info("=== Сбор и анализ новостей ===")

    # === Сбрасываем историю отправленных постов ===
    SENT_FILE = Path("data/sent_news.json")
    if SENT_FILE.exists():
        try:
            SENT_FILE.unlink()
            log.info("♻️ Сброшен список отправленных постов (sent_news.json).")
        except Exception as e:
            log.warning(f"⚠️ Не удалось удалить sent_news.json: {e}")

    # 1️⃣ Сбор и анализ новостей
    collect_all()
    extract_all_articles()
    selected = analyze_articles()

    if not selected:
        log.warning("⚠️ Нет статей для публикации.")
        return

    # 2️⃣ Формирование расписания и отчёта
    build_schedule()
    send_report(selected)

    # 3️⃣ Запуск постинга по расписанию
    now = datetime.now(tz)
    log.info("🕒 Запуск режима планового постинга.")
    post_next()

    log.info("✅ Скрипт завершил подготовку и перешёл в фоновый режим постинга.")


if __name__ == "__main__":
    main()
