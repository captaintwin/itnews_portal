# utils/text_stats.py — частотный анализ текстов статей (слова и биграммы)
import re
import sqlite3
from collections import Counter
from pathlib import Path

from core.logger import log

DATA_DIR = Path("data")
ARTICLES_DIR = DATA_DIR / "articles"
DB_FILE = DATA_DIR / "stats.sqlite"

# Слова храним все с частотой >= MIN_WORD_COUNT (нужно для анализа распределения),
# биграммы — только топ.
MIN_WORD_COUNT = 2
MAX_WORDS = 8000
TOP_BIGRAMS = 150

WORD_RE = re.compile(r"[a-z][a-z'\-]{2,}")

# Стоп-слова: служебные английские + типичный «мусор» новостных страниц
STOPWORDS = frozenset("""
the and for that with this from are was were has have had been being you your
not all can will would could should shall may might must about into over under
out off above below between through during before after again further then once
here there when where why how what which who whom whose its it's they them their
she her his him our ours out own same such than too very just don does did doing
one two three four five six seven eight nine ten new also said says like get got
make makes made making use used using uses via according still even much many
more most other some any both each few only well way year years day days week
weeks month months time times now today yesterday tomorrow back next last first
second while since because per amid among across around against within without
including include includes but however although though thats lets etc per
read continue reading posted share comments comment subscribe subscription
newsletter advertisement advert sponsored image images photo photos credit
caption getty reuters sign log login rights reserved privacy policy terms
email click follow following related story stories article articles news
report reports reported reporting company companies inc llc ltd corp says said
take takes took taken see seen sees want wants really thing things lot bit
people person way ways set sets need needs needed help helps part parts come
comes came going goes gone know knows known think thinks thought top best
these those them homepage feed feeds digest daily added posts post topic topics
skip content menu search open close show hide view trending latest popular
""".split())


def _tokens(text: str):
    return [w for w in WORD_RE.findall(text.lower()) if w not in STOPWORDS]


def compute_word_stats(run_date: str, items: list):
    """
    Считает частоты слов и биграмм по текстам статей текущего прогона
    (data/articles/{id}.txt + заголовки) и сохраняет в stats.sqlite.
    """
    try:
        _compute(run_date, items)
    except Exception as e:
        log.error(f"⚠️ Ошибка анализа текстов: {e}")


def _compute(run_date: str, items: list):
    words = Counter()
    bigrams = Counter()
    analyzed = 0

    for item in items:
        if not isinstance(item, dict):
            continue
        parts = [item.get("title", "")]
        art = ARTICLES_DIR / f"{item.get('id', '')}.txt"
        if art.exists():
            try:
                parts.append(art.read_text(encoding="utf-8"))
            except Exception:
                pass

        toks = _tokens("\n".join(parts))
        if not toks:
            continue
        analyzed += 1
        words.update(toks)
        bigrams.update(
            f"{a} {b}" for a, b in zip(toks, toks[1:])
        )

    if not analyzed:
        log.warning("⚠️ Нет текстов для частотного анализа.")
        return

    con = sqlite3.connect(DB_FILE)
    try:
        con.execute(
            "CREATE TABLE IF NOT EXISTS word_stats ("
            "run_date TEXT, kind TEXT, term TEXT, cnt INTEGER, "
            "PRIMARY KEY (run_date, kind, term))"
        )
        con.execute("DELETE FROM word_stats WHERE run_date = ?", (run_date,))
        word_rows = [
            (run_date, "word", t, c)
            for t, c in words.most_common(MAX_WORDS)
            if c >= MIN_WORD_COUNT
        ]
        con.executemany(
            "INSERT INTO word_stats VALUES (?,?,?,?)",
            word_rows
            + [(run_date, "bigram", t, c) for t, c in bigrams.most_common(TOP_BIGRAMS)],
        )
        con.commit()
    finally:
        con.close()

    log.info(
        f"🔤 Частотный анализ за {run_date}: {analyzed} текстов, "
        f"{len(words)} уникальных слов."
    )
