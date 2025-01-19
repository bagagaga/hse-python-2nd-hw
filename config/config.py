import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='bot.env')

BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_FILE = "data/logs/bot.log"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/db/bot.db")
if not BOT_TOKEN:
    print(os.path)
    raise ValueError("Токен не найден! Пожалуйста, проверьте bot.env.")