
from core.logger import log
from sources.collector import collect_all
from utils.article_extractor import extract_all_articles
from utils.reporter import send_report
from utils.analyzer import analyze_articles


if __name__ == "__main__":
    log.info("🚀 Запуск пайплайна сбора и анализа новостей")

    # 1️⃣ Сбор новостей
    news = collect_all()
    if not news:
        log.warning("⚠️ Новости не собраны — выходим.")
        exit()

    # 2️⃣ Извлечение текстов статей
    extract_all_articles()

    # 3️⃣ Анализ (выбор топ-3 по каждому источнику)
    selected = analyze_articles(top_n=3)

    # 4️⃣ Отправка отчёта в Telegram
    send_report(selected)

    # 5️⃣ (опционально) Публикация следующей статьи
    # post_next()

    log.info("✅ Все шаги успешно выполнены.")
