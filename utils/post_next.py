import os, json
from datetime import datetime
from pathlib import Path
from telegram import Bot

NEWS_FILE = Path("data/news.json")
STATE_FILE = Path("data/state.json")
SCHEDULE_FILE = Path("data/schedule.json")

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
chat_id = os.getenv("TELEGRAM_CHAT")


def load_json(path, default):
    if path.exists():
        return json.load(open(path, "r", encoding="utf-8"))
    return default


def post_next():
    news_data = load_json(NEWS_FILE, {})
    news = news_data.get("items", news_data)
    state = load_json(STATE_FILE, {"last_index": -1})
    schedule = load_json(SCHEDULE_FILE, [])

    if not news:
        print("⚠️ Нет новостей для постинга.")
        return

    next_index = state["last_index"] + 1
    if next_index >= len(news):
        print("✅ Все новости уже опубликованы.")
        return

    # Проверяем время
    now = datetime.utcnow().strftime("%H:%M")
    if schedule and now < schedule[next_index]:
        print(f"⏳ Ещё рано: сейчас {now}, следующая публикация в {schedule[next_index]}")
        return

    n = news[next_index]
    msg = f"📰 <b>{n['title']}</b>\n\n{n['summary']}\n<a href='{n['url']}'>Читать подробнее</a>"
    bot.send_message(chat_id, msg, parse_mode="HTML")

    state["last_index"] = next_index
    json.dump(state, open(STATE_FILE, "w", encoding="utf-8"))
    print(f"✅ Опубликовано {next_index+1}/{len(news)} ({schedule[next_index]})")


if __name__ == "__main__":
    post_next()
