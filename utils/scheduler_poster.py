from apscheduler.schedulers.background import BackgroundScheduler
from utils.post_to_telegram import send_post
import json, time
from datetime import datetime, timedelta

def schedule_posts():
    with open("data/selected.json", "r", encoding="utf-8") as f:
        selected = json.load(f)

    if not selected:
        print("Нет статей для публикации.")
        return

    scheduler = BackgroundScheduler()
    interval = 24 * 60 / len(selected)  # в минутах между постами
    start_time = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

    for i, item in enumerate(selected):
        post_time = start_time + timedelta(minutes=i * interval)
        scheduler.add_job(send_post, "date", run_date=post_time, args=[item])
        print(f"📅 Запланировано: {item['title']} — {post_time.strftime('%H:%M')}")

    scheduler.start()
    while True:
        time.sleep(60)
