import sys
from sources.collector import collect_all
from utils.article_extractor import extract_all_articles
from utils.analyzer import analyze_articles
from utils.reporter import send_report
from utils.scheduler_poster import schedule_posts
from utils.half_poster import post_half
from core.logger import log

def main():
    args = sys.argv[1:]

    # Только сбор новостей и анализ (без постинга)
    if "--collect-only" in args:
        log.info("=== Сбор и анализ новостей ===")
        collect_all()
        extract_all_articles()
        selected = analyze_articles()
        send_report(selected)
        log.info("✅ Новости собраны и сохранены в data/selected.json")
        return

    # Постим половину списка (для GitHub Actions)
    if "--half-post" in args:
        log.info("=== Постинг половины списка ===")
        post_half()
        return

    # Полный запуск (локально)
    log.info("=== Полный режим запуска ===")
    collect_all()
    extract_all_articles()
    selected = analyze_articles()
    send_report(selected)
    schedule_posts()
    log.info("=== Готово ===")

if __name__ == "__main__":
    main()
