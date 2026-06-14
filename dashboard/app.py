# dashboard/app.py — веб-дашборд статистики itnews_portal
import json
import math
import os
import sqlite3
import statistics
import sys
from collections import Counter
from datetime import datetime
from functools import wraps
from pathlib import Path

import pytz
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, make_response, render_template, request, url_for

from i18n import METRIC_DESC, METRIC_KEYS, TRANSLATIONS, resolve_lang

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
from utils.text_stats import is_commerce_bigram, is_commerce_word

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
                lang = resolve_lang(request)
                return Response(
                    TRANSLATIONS[lang]["auth_required"], 401,
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


def _filter_words(rows, limit=None):
    out = [r for r in rows if not is_commerce_word(r["term"])]
    return out[:limit] if limit else out


def _filter_bigrams(rows, limit=None):
    out = [r for r in rows if not is_commerce_bigram(r["term"])]
    return out[:limit] if limit else out


def word_analytics():
    """Топ слов/биграмм за 7 дней и растущие термины (последний день vs предыдущие)."""
    top_words = _filter_words(query(
        "SELECT term, SUM(cnt) AS cnt FROM word_stats WHERE kind = 'word' "
        "AND run_date >= date('now', '-7 day') "
        "GROUP BY term ORDER BY cnt DESC LIMIT 200"
    ), 25)
    top_bigrams = _filter_bigrams(query(
        "SELECT term, SUM(cnt) AS cnt FROM word_stats WHERE kind = 'bigram' "
        "AND run_date >= date('now', '-7 day') "
        "GROUP BY term ORDER BY cnt DESC LIMIT 80"
    ), 15)

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
            if cnt < 3 or is_commerce_word(term):
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


def _aggregated_words(days=7):
    return _filter_words(query(
        "SELECT term, SUM(cnt) AS cnt FROM word_stats WHERE kind = 'word' "
        "AND run_date >= date('now', ? || ' day') "
        "GROUP BY term ORDER BY cnt DESC",
        (f"-{days}",),
    ))


def _central_stats(freqs):
    """Центральные тенденции и границы для фильтрации слов по метрикам."""
    n = len(freqs)
    mean = sum(freqs) / n
    median = statistics.median(freqs)
    mode_val, mode_n = Counter(freqs).most_common(1)[0]
    std = statistics.stdev(freqs) if n > 1 else 0.0
    if n >= 4:
        qs = statistics.quantiles(freqs, n=4)
        q1, q3 = qs[0], qs[2]
    else:
        q1, q3 = min(freqs), max(freqs)
    iqr = q3 - q1
    outlier_thr = q3 + 1.5 * iqr
    return {
        "mean": round(mean, 1),
        "median": round(median, 1),
        "mode": mode_val,
        "mode_words": mode_n,
        "std": round(std, 1),
        "q1": round(q1, 1),
        "q3": round(q3, 1),
        "iqr": round(iqr, 1),
        "outlier_thr": round(outlier_thr, 1),
        "max": freqs[0],
        # границы для API-фильтров
        "mean_lo": max(2, int(mean - std)),
        "mean_hi": max(2, int(mean + std)),
        "median_lo": int(math.floor(median)),
        "median_hi": int(math.ceil(median)),
        "q3_lo": int(math.floor(q3)),
        "q3_hi": int(math.floor(outlier_thr)),
    }


def word_distribution():
    """Распределение частот слов за 7 дней: гистограмма, Ципф, центр. тенденции, полюса."""
    rows = _aggregated_words()
    if not rows:
        return None

    freqs = [r["cnt"] for r in rows]
    n = len(freqs)
    central = _central_stats(freqs)

    buckets = [(2, 2), (3, 4), (5, 9), (10, 19), (20, 49),
               (50, 99), (100, 199), (200, None)]
    hist = []
    for lo, hi in buckets:
        cnt = sum(1 for f in freqs if f >= lo and (hi is None or f <= hi))
        label = str(lo) if hi == lo else (f"{lo}–{hi}" if hi else f"{lo}+")
        hist.append({"label": label, "count": cnt, "lo": lo, "hi": hi})

    # Кривая Ципфа (ранг → частота), даунсэмплинг до ~150 точек
    step = max(1, n // 150)
    zipf = [
        {"rank": i + 1, "freq": r["cnt"]}
        for i, r in enumerate(rows)
        if i % step == 0 or i == n - 1
    ]

    # Полюса: верхний (хаб-слова), нижний (хвост), выбросы (за пределами IQR)
    high_pole = [{"term": r["term"], "cnt": r["cnt"]} for r in rows[:15]]
    low_pole = [{"term": r["term"], "cnt": r["cnt"]} for r in reversed(rows) if r["cnt"] <= 3][:30]
    outliers = [{"term": r["term"], "cnt": r["cnt"]} for r in rows if r["cnt"] > central["outlier_thr"]]

    return {
        "hist": hist,
        "zipf": zipf,
        "unique": n,
        "total": sum(freqs),
        "max": freqs[0],
        "central": {k: central[k] for k in (
            "mean", "median", "mode", "mode_words", "std",
            "q1", "q3", "iqr", "outlier_thr",
        )},
        "poles": {
            "high": high_pole,
            "low": low_pole,
            "outliers": outliers,
        },
    }


@app.route("/api/words/metric")
@protected
def words_for_metric():
    """Слова, соответствующие центральной метрике (клик по графику тенденций)."""
    metric = request.args.get("metric", "")
    days = request.args.get("days", default=7, type=int)
    lang = resolve_lang(request)
    t = TRANSLATIONS[lang]
    if metric not in METRIC_KEYS:
        return jsonify({"error": "unknown metric"}), 400

    label = t[METRIC_KEYS[metric]]
    rows = _aggregated_words(days)
    if not rows:
        return jsonify({"label": label, "words": [], "total": 0, "desc": ""})

    freqs = [r["cnt"] for r in rows]
    c = _central_stats(freqs)

    if metric == "mode":
        words = [r for r in rows if r["cnt"] == c["mode"]]
        desc = METRIC_DESC[lang]["mode"].format(v=c["mode"])
    elif metric == "median":
        words = [r for r in rows if c["median_lo"] <= r["cnt"] <= c["median_hi"]]
        desc = METRIC_DESC[lang]["median"].format(
            lo=c["median_lo"], hi=c["median_hi"], v=c["median"],
        )
    elif metric == "mean":
        words = [r for r in rows if c["mean_lo"] <= r["cnt"] <= c["mean_hi"]]
        desc = METRIC_DESC[lang]["mean"].format(
            lo=c["mean_lo"], hi=c["mean_hi"], mean=c["mean"], std=c["std"],
        )
    elif metric == "q3":
        words = [r for r in rows if c["q3_lo"] <= r["cnt"] <= c["q3_hi"]]
        desc = METRIC_DESC[lang]["q3"].format(lo=c["q3_lo"], hi=c["q3_hi"])
    else:  # max
        words = [r for r in rows if r["cnt"] == c["max"]]
        desc = METRIC_DESC[lang]["max"].format(v=c["max"])

    return jsonify({
        "label": label,
        "metric": metric,
        "desc": desc,
        "words": words[:500],
        "total": len(words),
    })


@app.route("/api/words/bucket")
@protected
def words_in_bucket():
    """Слова в выбранной корзине частот (клик по гистограмме)."""
    lo = request.args.get("lo", type=int)
    hi = request.args.get("hi", type=int)
    days = request.args.get("days", default=7, type=int)
    if lo is None:
        return jsonify({"error": "lo required"}), 400

    sql = (
        "SELECT term, SUM(cnt) AS cnt FROM word_stats WHERE kind = 'word' "
        "AND run_date >= date('now', ? || ' day') "
        "GROUP BY term HAVING cnt >= ?"
    )
    args = [f"-{days}", lo]
    if hi is not None:
        sql += " AND cnt <= ?"
        args.append(hi)
    sql += " ORDER BY cnt DESC, term LIMIT 500"

    words = _filter_words(query(sql, tuple(args)))
    label = str(lo) if hi == lo else (f"{lo}–{hi}" if hi else f"{lo}+")
    return jsonify({"label": label, "lo": lo, "hi": hi, "words": words, "total": len(words)})


def _nav_url(lang):
    endpoint = request.endpoint or "index"
    return url_for(endpoint, lang=lang)


def _render(template, active_nav, **kwargs):
    lang = resolve_lang(request)
    t = TRANSLATIONS[lang]
    resp = make_response(render_template(
        template,
        active_nav=active_nav,
        now=datetime.now(tz).strftime("%d.%m.%Y %H:%M"),
        t=t,
        lang=lang,
        nav_url=_nav_url,
        **kwargs,
    ))
    if request.args.get("lang") in TRANSLATIONS:
        resp.set_cookie("lang", lang, max_age=365 * 24 * 3600)
    return resp


def _run_totals():
    runs = query("SELECT * FROM runs ORDER BY run_date DESC LIMIT 30")
    return runs, {
        "days": len(runs),
        "posted": sum(r["posted"] or 0 for r in runs),
        "skipped": sum(r["skipped"] or 0 for r in runs),
        "collected": sum(r["collected"] or 0 for r in runs),
    }


@app.route("/")
@protected
def index():
    runs, totals = _run_totals()
    recent_posts = query(
        "SELECT * FROM posts WHERE status = 'posted' "
        "ORDER BY run_date DESC, planned_time DESC LIMIT 50"
    )
    today_items = live_today()
    today_posted = sum(1 for i in today_items if i["status"] == "posted")
    return _render(
        "index.html",
        "overview",
        totals=totals,
        today_items=today_items,
        today_posted=today_posted,
        recent_posts=recent_posts,
    )


@app.route("/metrics")
@protected
def metrics():
    runs, _ = _run_totals()
    runs = runs[::-1]
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
    top_words, top_bigrams, trends = word_analytics()
    distribution = word_distribution()
    return _render(
        "metrics.html",
        "metrics",
        runs=runs,
        sources=sources,
        posts_by_source=posts_by_source,
        top_words=top_words,
        top_bigrams=top_bigrams,
        trends=trends,
        distribution=distribution,
        has_history=bool(runs),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
