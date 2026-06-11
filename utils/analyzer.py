# utils/analyzer.py — отбор статей: фильтр рекламы/купонов + скоринг новостности
import json
import math
import re
from collections import defaultdict
from pathlib import Path

from core.logger import log

NEWS_FILE = Path("data/news.json")
ARTICLES_DIR = Path("data/articles")
SELECTED_FILE = Path("data/selected.json")

# === Жёсткий чёрный список: купоны, подборки, гайды по покупкам ===
TITLE_BLACKLIST = [
    r"\bcoupons?\b",
    r"\bpromo[\s-]?codes?\b",
    r"\bdiscount(s|ed)?\b",
    r"\d+% off\b",
    r"\$\d+ off\b",
    r"\b(best|daily|top|hottest) deals\b",
    r"\bdeal of the day\b",
    r"\bdeals (on|under|for)\b",
    r"\b(gift|buying|holiday) guide\b",
    r"\bbest [\w\s'-]{0,45}(of |in )?20\d\d\b",   # «The Best E-Readers of 2026»
    r"\btop \d+\b",
    r"\b(our|editors'?|\w+'s) favou?rites?\b",    # «Engadget's favorite GBA games»
    r"\bgiveaway\b",
    r"\bsweepstakes?\b",
    r"\bsponsored\b",
    r"\bwebinar\b",
    r"\branked\b",
    r"\bsave (up to )?\$?\d+",
]
URL_BLACKLIST = [
    r"/(coupons?|deals|shopping|sponsored|gift-guide)s?/",
    r"promo[\s_-]?code",
    r"/best-[\w-]+-20\d\d",
]

# === Маркеры партнёрского/рекламного контента в тексте ===
COMMERCIAL_MARKERS = [
    "earn a commission", "affiliate link", "affiliate commission",
    "use code", "promo code", "coupon", "% off", "discount code",
    "buy now", "shop now", "add to cart", "msrp", "retail price",
    "sponsored content", "partner content", "brought to you by",
    "limited time offer", "deal price", "list price", "check price",
]

# === Признаки настоящей новости (заголовок весит втрое больше текста) ===
NEWS_KEYWORDS = [
    "announce", "launch", "release", "unveil", "introduce", "reveal",
    "research", "study", "report", "breakthrough", "discover",
    "breach", "attack", "hack", "vulnerability", "exploit", "malware",
    "ransomware", "leak", "outage", "security", "privacy",
    "open source", "open-source", "model", "benchmark", "dataset",
    "algorithm", "framework", "kernel", "compiler", "protocol",
    "funding", "raises", "acquisition", "acquires", "merger", "ipo",
    "lawsuit", "regulation", "ban", "antitrust", "fine", "ruling",
    "startup", "chip", "semiconductor", "quantum", "robot", "satellite",
    "update", "feature", "beta", "rollout", "shutdown", "patch",
]

_title_black = [re.compile(p, re.I) for p in TITLE_BLACKLIST]
_url_black = [re.compile(p, re.I) for p in URL_BLACKLIST]


def is_blacklisted(item: dict) -> str | None:
    """Возвращает причину бана или None."""
    title = item.get("title", "")
    url = item.get("url", "")
    for rx in _title_black:
        if rx.search(title):
            return f"title ~ {rx.pattern}"
    for rx in _url_black:
        if rx.search(url):
            return f"url ~ {rx.pattern}"
    return None


def score_item(item: dict, text: str) -> float:
    """Скоринг «новостности»: ключевые слова − рекламные маркеры + длина (с потолком)."""
    title = item.get("title", "").lower()
    body = text.lower()

    title_hits = sum(1 for k in NEWS_KEYWORDS if k in title)
    text_hits = min(sum(1 for k in NEWS_KEYWORDS if k in body), 10)

    commercial_hits = sum(body.count(m) for m in COMMERCIAL_MARKERS)

    # Партнёрский контент почти всегда содержит дисклеймер о комиссии
    if "earn a commission" in body or "affiliate link" in body:
        return -100.0
    if commercial_hits >= 5:
        return -100.0

    # Длина полезна, но логарифмически и с потолком, чтобы
    # гигантские каталожные страницы не выигрывали автоматом
    length_score = min(math.log10(max(len(text), 1)), 4.5)

    return 3.0 * title_hits + text_hits + length_score - 2.0 * commercial_hits


def analyze_articles(top_n=3, min_score=2.0):
    """Выбирает по top_n самых «новостных» статей из каждого источника."""
    if not NEWS_FILE.exists():
        log.warning(f"⚠️ Файл {NEWS_FILE} не найден")
        return []

    with open(NEWS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        news = data.get("items", data)

    scored = []
    for n in news:
        reason = is_blacklisted(n)
        if reason:
            log.info(f"🚫 Реклама/подборка ({reason}): {n.get('title', '')[:80]}")
            continue

        art_path = ARTICLES_DIR / f"{n['id']}.txt"
        if not art_path.exists():
            continue
        try:
            text = art_path.read_text(encoding="utf-8")
        except Exception as e:
            log.warning(f"⚠️ Ошибка чтения {art_path}: {e}")
            continue

        n["char_count"] = len(text)
        n["score"] = round(score_item(n, text), 2)

        if n["score"] <= -100.0:
            log.info(f"🚫 Партнёрский контент: {n.get('title', '')[:80]}")
            continue
        if n["score"] < min_score:
            log.info(f"⏬ Низкий скор ({n['score']}): {n.get('title', '')[:80]}")
            continue

        scored.append(n)

    # Группировка по источнику, top_n лучших по скору
    grouped = defaultdict(list)
    for n in scored:
        grouped[n.get("source", "unknown")].append(n)

    selected = []
    for src, items in grouped.items():
        items.sort(key=lambda x: x["score"], reverse=True)
        top_items = items[:top_n]
        selected.extend(top_items)
        log.info(f"📚 {src}: выбрано {len(top_items)} из {len(items)} (после фильтров)")

    SELECTED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SELECTED_FILE, "w", encoding="utf-8") as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)

    log.info(f"✅ Всего отобрано {len(selected)} статей из {len(grouped)} источников")
    return selected
