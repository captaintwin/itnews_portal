import os
from dotenv import load_dotenv
load_dotenv()

#Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")