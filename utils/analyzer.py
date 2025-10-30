import json
from pathlib import Path
from collections import defaultdict
from core.logger import log  # если используешь свой логгер

NEWS_FILE = Path("data/news.json")
ARTICLES_DIR = Path("data/articles")
SELECTED_FILE = Path("data/selected.json")


def analyze_articles(top_n=3):
    """Выбирает по top_n самых длинных статей из каждого источника."""
    if not NEWS_FILE.exists():
        log.warning(f"⚠️ Файл {NEWS_FILE} не найден")
        return []

    # Загружаем данные
    with open(NEWS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        news = data.get("items", data)

    # Подсчёт длины текста каждой статьи
    for n in news:
        art_path = ARTICLES_DIR / f"{n['id']}.txt"
        if art_path.exists():
            try:
                text = art_path.read_text(encoding="utf-8")
                n["char_count"] = len(text)
            except Exception as e:
                log.warning(f"⚠️ Ошибка чтения {art_path}: {e}")
                n["char_count"] = 0
        else:
            n["char_count"] = 0

    # Группировка по источнику
    grouped = defaultdict(list)
    for n in news:
        src = n.get("source", "unknown")
        grouped[src].append(n)

    # Для каждого источника берём top_n самых длинных
    selected = []
    for src, items in grouped.items():
        items = [n for n in items if n["char_count"] > 0]
        items.sort(key=lambda x: x["char_count"], reverse=True)
        top_items = items[:top_n]
        selected.extend(top_items)
        log.info(f"📚 {src}: выбрано {len(top_items)} из {len(items)} статей")

    # Сохраняем результат
    SELECTED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SELECTED_FILE, "w", encoding="utf-8") as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)

    log.info(f"✅ Всего отобрано {len(selected)} статей из {len(grouped)} источников")
    return selected
