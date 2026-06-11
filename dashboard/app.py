# dashboard/app.py — веб-дашборд статистики itnews_portal
import json
import os
import sqlite3
from datetime import datetime
from functools import wraps
from pathlib import Path

import pytz
from dotenv import load_dotenv
from flask import Flask, Response, render_template, request

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DB_FILE = DATA_DIR / "stats.sqlite"

load_dotenv(dotenv_path=BASE_DIR / ".env")
PASSWORD = os.getenv("DASHBOARD_PASSWORD")

tz = pytz.timezone("Europe/Belgrade")

app = Flask(__name__)


def protected(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if PASSWORD:
            auth = request.authorization
            if not auth or auth.password != PASSWORD:
                return Response(
                    "Требуется авторизация", 401,
                    {"WWW-Authenticate": 'Basic realm="itnews dashboard"'},
                )
        return f(*args, **kwargs)
    return wrapper


def query(sql, args=()):
    if not DB_FILE.exists():
        return []
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, args)]
    except sqlite3.OperationalError:
        # таблица ещё не создана (нет данных за этот период)
        return []
    finally:
        con.close()


def _load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def live_today():
    """Текущее состояние дня из живых JSON-файлов (пока прогон не заархивирован)."""
    schedule = _load_json(DATA_DIR / "schedule.json", [])
    post_log = _load_json(DATA_DIR / "post_log.json", [])
    sent = set(_load_json(DATA_DIR / "sent_news.json", []))

    today = datetime.now(tz).strftime("%Y-%m-%d")
    log_by_id = {e["id"]: e for e in post_log if isinstance(e, dict) and "id" in e}

    items = []
    for s in schedule:
        if not (isinstance(s, dict) and "id" in s and "time" in s):
            continue
        if not s["time"].startswith(today):
            return []  # расписание от другого дня — не показываем как «сегодня»
        entry = log_by_id.get(s["id"])
        if entry:
            status = entry.get("status", "unknown")
        elif s["id"] in sent:
            status = "posted"
        else:
            status = "pending"
        items.append({
            "time": s["time"].split(" ")[1],
            "title": s.get("title", ""),
            "url": s.get("url", ""),
            "source": s.get("source", ""),
            "status": status,
        })
    items.sort(key=lambda x: x["time"])
    return items


def word_analytics():
    """Топ слов/биграмм за 7 дней и растущие термины (последний день vs предыдущие)."""
    top_words = query(
        "SELECT term, SUM(cnt) AS cnt FROM word_stats WHERE kind = 'word' "
        "AND run_date >= date('now', '-7 day') "
        "GROUP BY term ORDER BY cnt DESC LIMIT 25"
    )
    top_bigrams = query(
        "SELECT term, SUM(cnt) AS cnt FROM word_stats WHERE kind = 'bigram' "
        "AND run_date >= date('now', '-7 day') "
        "GROUP BY term ORDER BY cnt DESC LIMIT 15"
    )

    # Тренды: частота в последний день против среднего за предыдущие 7 дней
    trends = []
    dates = [r["run_date"] for r in query(
        "SELECT DISTINCT run_date FROM word_stats ORDER BY run_date DESC LIMIT 8"
    )]
    if len(dates) >= 2:
        last, prev = dates[0], dates[1:]
        cur = {r["term"]: r["cnt"] for r in query(
            "SELECT term, cnt FROM word_stats WHERE kind = 'word' AND run_date = ?",
            (last,),
        )}
        ph = ",".join("?" * len(prev))
        old = {r["term"]: r["avg_cnt"] for r in query(
            f"SELECT term, AVG(cnt) AS avg_cnt FROM word_stats "
            f"WHERE kind = 'word' AND run_date IN ({ph}) GROUP BY term",
            tuple(prev),
        )}
        for term, cnt in cur.items():
            if cnt < 3:
                continue
            base = old.get(term, 0)
            growth = cnt / (base + 1)
            trends.append({
                "term": term, "today": cnt,
                "prev_avg": round(base, 1), "growth": round(growth, 1),
            })
        trends.sort(key=lambda x: x["growth"], reverse=True)
        trends = trends[:20]

    return top_words, top_bigrams, trends


@app.route("/")
@protected
def index():
    runs = query("SELECT * FROM runs ORDER BY run_date DESC LIMIT 30")[::-1]
    sources = query(
        "SELECT source, SUM(collected) AS collected, SUM(selected) AS selected "
        "FROM source_stats GROUP BY source ORDER BY collected DESC"
    )
    posts_by_source = query(
        "SELECT source, "
        "SUM(status = 'posted') AS posted, "
        "SUM(status = 'skipped') AS skipped "
        "FROM posts GROUP BY source ORDER BY posted DESC"
    )
    recent_posts = query(
        "SELECT * FROM posts WHERE status = 'posted' "
        "ORDER BY run_date DESC, planned_time DESC LIMIT 50"
    )

    totals = {
        "days": len(runs),
        "posted": sum(r["posted"] or 0 for r in runs),
        "skipped": sum(r["skipped"] or 0 for r in runs),
        "collected": sum(r["collected"] or 0 for r in runs),
    }

    today_items = live_today()
    today_posted = sum(1 for i in today_items if i["status"] == "posted")
    top_words, top_bigrams, trends = word_analytics()

    return render_template(
        "index.html",
        runs=runs,
        sources=sources,
        posts_by_source=posts_by_source,
        recent_posts=recent_posts,
        totals=totals,
        today_items=today_items,
        today_posted=today_posted,
        top_words=top_words,
        top_bigrams=top_bigrams,
        trends=trends,
        now=datetime.now(tz).strftime("%d.%m.%Y %H:%M"),
        has_history=bool(runs),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
