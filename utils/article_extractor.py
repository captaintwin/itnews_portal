import requests
from bs4 import BeautifulSoup
from pathlib import Path
import json
from core.logger import log

NEWS_FILE = Path("data/news.json")
ARTICLES_DIR = Path("data/articles")


def extract_all_articles():
    """Скачивает HTML-страницы из news.json и сохраняет очищенный текст в .txt файлы."""
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)

    with open(NEWS_FILE, "r", encoding="utf-8") as f:
        news_data = json.load(f)
        if isinstance(news_data, dict) and "items" in news_data:
            news_list = news_data["items"]
        else:
            news_list = news_data

    for item in news_list:
        url = item.get("url")
        if not url:
            continue

        art_path = ARTICLES_DIR / f"{item['id']}.txt"
        if art_path.exists():
            continue

        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                log.warning(f"⚠️ {r.status_code} — {url}")
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            text = soup.get_text(separator="\n").replace("\xa0", " ").replace("\r", "")
            clean_lines = [
                line.strip()
                for line in text.splitlines()
                if len(line.strip()) > 50
                and not line.lower().startswith(("cookie", "accept", "privacy"))
            ]
            text = "\n".join(clean_lines)

            if len(text) < 300:
                log.warning(f"⚠️ Too short ({len(text)} chars): {url}")
                continue

            art_path.write_text(text, encoding="utf-8")
            log.info(f"📝 Saved article text: {art_path.name}")

        except Exception as e:
            log.warning(f"[extract] Failed {url}: {e}")
            continue
