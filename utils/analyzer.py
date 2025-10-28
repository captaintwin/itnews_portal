import json
from pathlib import Path

NEWS_FILE = Path("data/news.json")
ARTICLES_DIR = Path("data/articles")
SELECTED_FILE = Path("data/selected.json")

def analyze_articles(top_ratio=0.3):
    with open(NEWS_FILE, "r", encoding="utf-8") as f:
        news = json.load(f)

    for n in news:
        art_path = ARTICLES_DIR / f"{n['id']}.txt"
        if art_path.exists():
            n["char_count"] = len(art_path.read_text(encoding="utf-8"))
        else:
            n["char_count"] = 0

    news = sorted(news, key=lambda x: x["char_count"], reverse=True)
    top_count = max(1, int(len(news) * top_ratio))
    selected = news[:top_count]

    with open(SELECTED_FILE, "w", encoding="utf-8") as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)

    return selected
