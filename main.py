# main.py
from datetime import datetime
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

    # 1️⃣ Сбор и анализ
    collect_all()
    extract_all_articles()
    selected = analyze_articles()

    if not selected:
        log.warning("⚠️ Нет статей для публикации.")
        return

    # 2️⃣ Планирование публикаций
    build_schedule()
    send_report(selected)

    # 3️⃣ Определяем режим постинга
    now = datetime.now(tz)
    if now.hour < 9:
        log.info("🕒 Сейчас до 9:00 — запускаем постинг по расписанию.")
        post_next(instant=False)
    else:
        log.info("⚡ Уже после 9:00 — включаем instant постинг (для теста).")
        post_next(instant=True)


if __name__ == "__main__":
    main()
