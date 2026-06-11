# utils/post_next.py
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytz
from core.logger import log
from utils.post_to_telegram import send_post

DATA_DIR = Path("data")
SELECTED_FILE = DATA_DIR / "selected.json"
SCHEDULE_FILE = DATA_DIR / "schedule.json"
SENT_FILE = DATA_DIR / "sent_news.json"
POST_LOG_FILE = DATA_DIR / "post_log.json"

tz = pytz.timezone("Europe/Belgrade")

# как часто проверять (сек)
TICK_SECONDS = 60
# если пост «просрочен» больше чем на столько — пропускаем
GRACE_SKIP_MIN = 180  # 3 часа

def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log.error(f"⚠️ Ошибка чтения {path}: {e}")
        return default

def _save_json(path: Path, obj):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log.error(f"⚠️ Ошибка записи {path}: {e}")

def post_next():
    selected = _load_json(SELECTED_FILE, [])
    schedule = _load_json(SCHEDULE_FILE, [])
    sent = set(_load_json(SENT_FILE, []))
    post_log = _load_json(POST_LOG_FILE, [])

    if not selected:
        log.warning("⚠️ selected.json пуст — нечего постить.")
        return
    if not schedule:
        log.warning("⚠️ schedule.json пуст — нет расписания.")
        return

    # Быстрый доступ: id -> news и id -> schedule
    by_id_news = {n["id"]: n for n in selected if "id" in n}
    by_id_sched = {s["id"]: s for s in schedule if "id" in s and "time" in s}

    # Контрольная метка
    log.info(f"📚 Загружено статей: {len(by_id_news)}, расписание: {len(by_id_sched)}, уже отправлено: {len(sent)}")

    while True:
        now = datetime.now(tz)
        changed = False

        # Собираем «должные к публикации» id (время <= now, и ещё не отправлены)
        due_ids = []
        for sid, sched in by_id_sched.items():
            if sid in sent:
                continue
            try:
                # В schedule время локальное, парсим и локализуем
                post_time = tz.localize(datetime.strptime(sched["time"], "%Y-%m-%d %H:%M"))
            except Exception as e:
                log.error(f"⚠️ Неверный формат времени у {sid}: {sched.get('time')}. Ошибка: {e}")
                continue

            delta_min = (now - post_time).total_seconds() / 60.0
            if delta_min >= 0:
                # уже пора (или уже прошло)
                # если прошло слишком много — пропускаем, чтобы не «строчить» старьё
                if delta_min > GRACE_SKIP_MIN:
                    log.info(f"⏭ Пропуск просроченного на {delta_min:.1f} мин: {by_id_news.get(sid, {}).get('title','(нет заголовка)')[:80]}")
                    sent.add(sid)
                    post_log.append({
                        "id": sid,
                        "planned": sched["time"],
                        "actual": None,
                        "status": "skipped",
                    })
                    changed = True
                else:
                    due_ids.append(sid)

        # Публикуем всё, что «созрело» к этому тику
        if due_ids:
            # В разумном порядке: по времени из расписания
            due_ids.sort(key=lambda x: by_id_sched[x]["time"])
            for sid in due_ids:
                news = by_id_news.get(sid)
                if not news:
                    # нет контента для этого id — считаем отправленным, чтобы не зациклиться
                    sent.add(sid)
                    post_log.append({
                        "id": sid,
                        "planned": by_id_sched[sid]["time"],
                        "actual": None,
                        "status": "skipped",
                    })
                    changed = True
                    continue
                try:
                    ok = send_post(news)
                except Exception as e:
                    log.error(f"❌ Ошибка постинга: {e}")
                    ok = False

                if ok:
                    sent.add(sid)
                    post_log.append({
                        "id": sid,
                        "planned": by_id_sched[sid]["time"],
                        "actual": now.strftime("%Y-%m-%d %H:%M"),
                        "status": "posted",
                    })
                    changed = True
                    log.info(f"✅ Опубликовано: {news.get('title', '')[:100]}")
                else:
                    # не помечаем отправленным — повторим на следующем тике,
                    # через GRACE_SKIP_MIN пост будет пропущен автоматически
                    log.error(f"❌ Не отправлено (повторим): {news.get('title', '')[:80]}")

        if changed:
            _save_json(SENT_FILE, list(sent))
            _save_json(POST_LOG_FILE, post_log)

        # Выход, если всё отправлено
        if len(sent) >= len(by_id_sched):
            log.info("🎉 Все публикации по расписанию завершены.")
            break

        # Для информации — когда ближайшая публикация
        future_times = []
        for sid, sched in by_id_sched.items():
            if sid in sent:
                continue
            try:
                t = tz.localize(datetime.strptime(sched["time"], "%Y-%m-%d %H:%M"))
                if t > now:
                    future_times.append(t)
            except Exception:
                pass
        if future_times:
            next_t = min(future_times)
            wait_min = (next_t - now).total_seconds() / 60.0
            log.info(f"⏳ Следующая проверка через {TICK_SECONDS}s. Ближайшая публикация в {next_t.strftime('%H:%M')} (через {wait_min:.1f} мин).")
        else:
            log.info(f"⏳ Следующая проверка через {TICK_SECONDS}s.")

        time.sleep(TICK_SECONDS)

if __name__ == "__main__":
    post_next()
