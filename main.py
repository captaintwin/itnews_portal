# main.py
from sources.collector import collect_all
from utils.article_extractor import extract_all_articles
from utils.analyzer import analyze_articles
from utils.reporter import send_report
from utils.scheduler_poster import schedule_posts
from core.logger import log


def main():
    log.info("=== СБОР НОВОСТЕЙ ===")
    collect_all()  # 1. Собираем RSS и сохраняем data/news.json

    log.info("=== ЗАГРУЗКА И ОЧИСТКА СТАТЕЙ ===")
    extract_all_articles()  # 2. Парсим текст со страниц и сохраняем *.txt

    log.info("=== АНАЛИЗ КОНТЕНТА ===")
    selected = analyze_articles()  # 3. Выбираем 20–30% самых длинных статей
    # (результат сохраняется в data/selected.json)

    log.info("=== ФОРМИРУЕМ ОТЧЁТ ===")
    send_report(selected)  # 4. Отправляем отчёт в техчат

    log.info("=== ЗАПУСК ПЛАНИРОВЩИКА ===")
    schedule_posts()  # 5. Расписание постинга (текущий день)

    log.info("=== ГОТОВО ===")


if __name__ == "__main__":
    main()
