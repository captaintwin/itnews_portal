import json
from datetime import datetime
from pathlib import Path

from core.logger import log
from sources.collector import collect_all
from utils.analyzer import analyze_articles  # выбирает топовые статьи
from utils.reporter import send_report         # формирует отчёт и отправляет в техчат
from utils.scheduler import build_schedule   # рассчитывает расписание постов

# main.py
from sources.collector import collect_all
from utils.article_extractor import extract_all_articles
from utils.analyzer import analyze_articles
from utils.reporter import send_report
from utils.post_next import post_next  # если хочешь сразу постить

from core.logger import log

if __name__ == "__main__":
    log.info("🚀 Запуск утреннего пайплайна сбора и анализа новостей")

    news = collect_all()
    if not news:
        log.warning("⚠️ Новости не собраны, выход.")
        exit()

    extract_all_articles()
    selected = analyze_articles(top_n=3)
    send_report(selected)

    # ⚙️ Раскомментируй, если хочешь публиковать сразу:
    #post_next()

