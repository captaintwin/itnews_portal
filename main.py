# main.py
from pathlib import Path

from core.logger import log
from sources.collector import collect_all
from utils.article_extractor import extract_all_articles
from utils.analyzer import analyze_articles
from utils.scheduler import build_schedule
from utils.reporter import send_report
from utils.post_next import post_next
from utils.stats import archive_day, cleanup_old
from utils.alerts import alert


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
        alert("После отбора 0 статей — сегодня публикаций не будет.")
        archive_day()
        return

    # 2️⃣ Формирование расписания и отчёта
    schedule = build_schedule()
    if not schedule:
        alert("Расписание не создано (запуск вне окна постинга?) — публикаций не будет.")
        archive_day()
        return
    send_report(selected)

    # 3️⃣ Запуск постинга по расписанию
    log.info("🕒 Запуск режима планового постинга.")
    post_next()

    # 4️⃣ Архивация итогов дня и чистка старых файлов
    archive_day()
    cleanup_old(days=7)

    log.info("✅ Скрипт завершил работу за день.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        alert(f"Прогон упал с ошибкой:\n{traceback.format_exc()[-1500:]}")
        raise
