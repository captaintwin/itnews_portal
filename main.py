# main.py
from sources.collector import collect_all
from utils.post_to_telegram import main as post_to_telegram_main
from core.logger import log
from pathlib import Path
import traceback

DATA_FILE = Path("data/news.json")

def main():
    log.info("=== СБОР НОВОСТЕЙ ===")
    try:
        collected = collect_all()
        log.info(f"Собрано {len(collected)} новостей")
    except Exception as e:
        log.error(f"Ошибка при сборе новостей: {e}")
        log.debug(traceback.format_exc())
        return

    # Проверяем, создался ли news.json
    if not DATA_FILE.exists():
        log.error(f"Файл {DATA_FILE} не найден. Сборщик не создал новости.")
        return

    if not collected:
        log.info("Нет новых новостей для публикации.")
        return

    log.info("=== ПУБЛИКАЦИЯ В TELEGRAM ===")
    try:
        post_to_telegram_main()
        log.info("Публикация завершена успешно.")
    except Exception as e:
        log.error(f"Ошибка при публикации: {e}")
        log.debug(traceback.format_exc())

    log.info("=== ГОТОВО ===")


if __name__ == "__main__":
    main()
