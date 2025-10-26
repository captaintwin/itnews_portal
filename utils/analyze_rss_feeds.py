import requests
import feedparser
import json
from datetime import datetime
from urllib.parse import urlparse

sources = [
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
    {"name": "Engadget", "url": "https://www.engadget.com/rss.xml"},
    {"name": "ZDNet", "url": "https://www.zdnet.com/news/rss.xml"},
    {"name": "CNET", "url": "https://www.cnet.com/rss/news/"},
    {"name": "VentureBeat", "url": "https://venturebeat.com/feed/"},
    {"name": "GitHub Blog", "url": "https://github.blog/feed/"},
    {"name": "Stack Overflow Blog", "url": "https://stackoverflow.blog/feed/"},
    {"name": "Dev.to", "url": "https://dev.to/feed"},
    {"name": "The Hacker News", "url": "https://feeds.feedburner.com/TheHackersNews"}
]

FIELDS = ["id", "title", "description", "content", "url", "image", "publishedAt", "lang", "source"]

def extract_info(entry, source_name, source_url):
    """Преобразует одну запись RSS в унифицированный объект"""
    title = getattr(entry, "title", "")
    link = getattr(entry, "link", "")
    desc = getattr(entry, "summary", "")
    content = getattr(entry, "content", [{}])[0].get("value", desc)
    published = getattr(entry, "published", "")
    image = ""
    lang = getattr(entry, "language", "en")

    # Ищем возможное изображение
    if "media_content" in entry:
        image = entry.media_content[0].get("url", "")
    elif "media_thumbnail" in entry:
        image = entry.media_thumbnail[0].get("url", "")

    return {
        "id": hash(link) % 10**10,
        "title": title,
        "description": desc,
        "content": content,
        "url": link,
        "image": image,
        "publishedAt": published,
        "lang": lang,
        "source": {
            "id": urlparse(source_url).netloc,
            "name": source_name,
            "url": source_url,
            "country": ""
        }
    }

def evaluate_structure(article):
    """Оценивает, насколько запись соответствует требуемым полям"""
    filled = sum(1 for k in FIELDS if article.get(k) or (k == "source" and article.get("source", {}).get("name")))
    return round((filled / len(FIELDS)) * 100, 1)

results = []

for src in sources:
    print(f"\n=== {src['name']} ===")
    try:
        feed = feedparser.parse(src["url"])
        if not feed.entries:
            print("❌ Нет записей")
            results.append({"source": src["name"], "coverage": 0})
            continue

        articles = [extract_info(e, src["name"], src["url"]) for e in feed.entries[:3]]
        coverage = evaluate_structure(articles[0])

        print(f"✓ Найдено {len(feed.entries)} записей, покрытие структуры: {coverage}%")
        print(f"Пример: {articles[0]['title'][:60]}...")
        results.append({
            "source": src["name"],
            "url": src["url"],
            "coverage": coverage,
            "example": articles[0]
        })
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        results.append({"source": src["name"], "url": src["url"], "error": str(e)})

with open("rss_analysis.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n✅ Анализ завершён. Результаты сохранены в rss_analysis.json")
