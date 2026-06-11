# utils/stats.py — архивация дневной статистики в SQLite
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytz
from core.logger import log
from utils.text_stats import compute_word_stats

DATA_DIR = Path("data")
DB_FILE = DATA_DIR / "stats.sqlite"

tz = pytz.timezone("Europe/Belgrade")

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_date    TEXT PRIMARY KEY,
    collected   INTEGER,
    selected    INTEGER,
    scheduled   INTEGER,
    posted      INTEGER,
    skipped     INTEGER,
    finished_at TEXT
);
CREATE TABLE IF NOT EXISTS posts (
    id           TEXT,
    run_date     TEXT,
    source       TEXT,
    title        TEXT,
    url          TEXT,
    planned_time TEXT,
    actual_time  TEXT,
    status       TEXT,
    has_image    INTEGER,
    PRIMARY KEY (id, run_date)
);
CREATE TABLE IF NOT EXISTS source_stats (
    run_date  TEXT,
    source    TEXT,
    collected INTEGER,
    selected  INTEGER,
    PRIMARY KEY (run_date, source)
);
"""


def _load(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def archive_day():
    """Сохраняет итоги прогона в data/stats.sqlite. Никогда не роняет main."""
    try:
        _archive()
    except Exception as e:
        log.error(f"⚠️ Ошибка архивации статистики: {e}")


def _archive():
    news = _load(DATA_DIR / "news.json", {})
    selected = _load(DATA_DIR / "selected.json", [])
    schedule = _load(DATA_DIR / "schedule.json", [])
    post_log = _load(DATA_DIR / "post_log.json", [])

    collected_items = news.get("items", []) if isinstance(news, dict) else []
    sel_by_id = {n["id"]: n for n in selected if isinstance(n, dict) and "id" in n}
    sched_by_id = {
        s["id"]: s for s in schedule
        if isinstance(s, dict) and "id" in s and "time" in s
    }
    log_by_id = {e["id"]: e for e in post_log if isinstance(e, dict) and "id" in e}

    # Фолбэк для прогонов без post_log: всё из sent_news считаем опубликованным
    if not log_by_id:
        sent = set(_load(DATA_DIR / "sent_news.json", []))
        log_by_id = {
            sid: {"id": sid, "planned": sched_by_id[sid]["time"],
                  "actual": sched_by_id[sid]["time"], "status": "posted"}
            for sid in sent if sid in sched_by_id
        }

    now = datetime.now(tz)
    # Дата прогона — из расписания (на случай архивации после полуночи)
    if sched_by_id:
        run_date = sorted(s["time"] for s in sched_by_id.values())[0].split(" ")[0]
    else:
        run_date = now.strftime("%Y-%m-%d")

    col_by_src, sel_by_src = {}, {}
    for it in collected_items:
        src = it.get("source", "unknown")
        col_by_src[src] = col_by_src.get(src, 0) + 1
    for it in sel_by_id.values():
        src = it.get("source", "unknown")
        sel_by_src[src] = sel_by_src.get(src, 0) + 1

    posted = sum(1 for e in log_by_id.values() if e.get("status") == "posted")
    skipped = sum(1 for e in log_by_id.values() if e.get("status") == "skipped")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_FILE)
    try:
        con.executescript(SCHEMA)
        con.execute(
            "INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?)",
            (run_date, len(collected_items), len(sel_by_id), len(sched_by_id),
             posted, skipped, now.strftime("%Y-%m-%d %H:%M")),
        )
        for src in set(col_by_src) | set(sel_by_src):
            con.execute(
                "INSERT OR REPLACE INTO source_stats VALUES (?,?,?,?)",
                (run_date, src, col_by_src.get(src, 0), sel_by_src.get(src, 0)),
            )
        for sid, sched in sched_by_id.items():
            sel = sel_by_id.get(sid, {})
            entry = log_by_id.get(sid, {})
            con.execute(
                "INSERT OR REPLACE INTO posts VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    sid,
                    run_date,
                    sel.get("source", sched.get("source", "unknown")),
                    sel.get("title", sched.get("title", "")),
                    sel.get("url", sched.get("url", "")),
                    sched["time"],
                    entry.get("actual"),
                    entry.get("status", "unknown"),
                    1 if sel.get("image_path") else 0,
                ),
            )
        con.commit()
    finally:
        con.close()

    log.info(
        f"📦 Статистика за {run_date} сохранена: "
        f"собрано {len(collected_items)}, в плане {len(sched_by_id)}, "
        f"опубликовано {posted}, пропущено {skipped}."
    )

    # Частотный анализ текстов собранных статей
    compute_word_stats(run_date, collected_items)
