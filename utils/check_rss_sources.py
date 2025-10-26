import requests
import json
from xml.etree import ElementTree

sources = [
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
    {"name": "Engadget", "url": "https://www.engadget.com/rss.xml"},
    {"name": "ZDNet", "url": "https://www.zdnet.com/news/rss.xml"},
    {"name": "CNET", "url": "https://www.cnet.com/rss/news/"},
    {"name": "VentureBeat", "url": "https://venturebeat.com/feed/"},
    {"name": "Hacker News", "url": "https://hacker-news.firebaseio.com/v0/"},
    {"name": "TechRadar", "url": "https://www.techradar.com/rss"},
    {"name": "GitHub Blog", "url": "https://github.blog/feed/"},
    {"name": "Stack Overflow Blog", "url": "https://stackoverflow.blog/feed/"},
    {"name": "Dev.to", "url": "https://dev.to/feed"},
    {"name": "The Hacker News", "url": "https://feeds.feedburner.com/TheHackersNews"},
]

def check_feed(url):
    try:
        resp = requests.get(url, timeout=10)
        status = resp.status_code
        content_type = resp.headers.get("Content-Type", "")
        valid_xml = False

        if "xml" in content_type or resp.text.strip().startswith("<?xml"):
            try:
                root = ElementTree.fromstring(resp.text)
                tag = root.tag.lower()
                if "rss" in tag or "feed" in tag:
                    valid_xml = True
            except Exception:
                pass

        return {
            "status_code": status,
            "content_type": content_type,
            "is_rss": valid_xml,
            "ok": status == 200 and valid_xml
        }
    except Exception as e:
        return {"error": str(e), "ok": False}

results = []
print("\n=== Проверка RSS-источников ===\n")

for src in sources:
    res = check_feed(src["url"])
    status_icon = "✓" if res["ok"] else ("⚠" if res.get("status_code") == 200 else "❌")
    details = (
        f"({res['status_code']})"
        if "status_code" in res
        else f"(error: {res.get('error', 'unknown')})"
    )
    print(f"{status_icon} {src['name']:<25} {details}")
    results.append({"source": src["name"], "url": src["url"], **res})

# Сохраняем JSON с результатами
with open("rss_status.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n✅ Проверка завершена. Результаты сохранены в rss_status.json")
