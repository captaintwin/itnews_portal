import os
from dotenv import load_dotenv
from pathlib import Path
import os
from dotenv import load_dotenv
# загружаем .env из корня проекта
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

# === Telegram Tokens ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
REPORT_TELEGRAM_TOKEN = os.getenv("REPORT_TELEGRAM_TOKEN")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT")

# === Debug ===
print("DEBUG CONFIG:")
print(f"  TELEGRAM_TOKEN = {bool(TELEGRAM_TOKEN)}")
print(f"  REPORT_TELEGRAM_TOKEN = {bool(REPORT_TELEGRAM_TOKEN)}")
print(f"  TELEGRAM_CHAT = {TELEGRAM_CHAT}")