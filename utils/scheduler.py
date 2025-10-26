 #планировщик задач (если не cron).

import schedule, time
from utils.post_to_telegram import main as post_to_telegram

def job():
    print("🕒 Posting batch...")
    post_to_telegram()

schedule.every().day.at("09:00").do(job)
schedule.every().day.at("14:00").do(job)
schedule.every().day.at("20:00").do(job)

while True:
    schedule.run_pending()
    time.sleep(30)
