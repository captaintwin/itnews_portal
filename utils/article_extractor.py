import requests
from bs4 import BeautifulSoup
from pathlib import Path
import json
from core.logger import log

NEWS_FILE = Path("data/news.json")
ARTICLES_DIR = Path("data/articles")

def extract_all_articles():
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    with open(NEWS_FILE, "r", encoding="utf-8") as f:
        news_list = json.load(f)

    for item in news_list:
        url = item.get("url")
        if not url:
            continue
        art_path = ARTICLES_DIR / f"{item['id']}.txt"
        if art_path.exists():
            continue
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.text, "html.parser")
            text = soup.get_text(separator="\n")
            # отбрасываем короткие строки (меню, футеры)
            text = "\n".join([line.strip() for line in text.splitlines() if len(line.strip()) > 50])
            art_path.write_text(text, encoding="utf-8")
            log.info(f"📝 Saved article text: {art_path.name}")
        except Exception as e:
            log.warning(f"[extract] Failed {url}: {e}")
