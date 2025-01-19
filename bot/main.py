import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
import sqlite3
from bot.utils.logging import logger
from config.config import BOT_TOKEN
from config.config import DATABASE_URL


async def on_startup(dispatcher):
    logger.info("Бот запущен!")

async def on_shutdown(dispatcher):
    logger.info("Бот остановлен.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Функция для создания базы данных и таблицы
def create_db():
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT)''')
    conn.commit()
    conn.close()

# Функция для добавления пользователя в базу данных
def add_user(user_id, username):
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    conn.close()

# Хэндлер для команды /start
@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username

    # Добавляем пользователя в базу данных
    add_user(user_id, username)

    # Отправляем сообщение пользователю
    await message.reply(f'Привет, {username}! Ты был добавлен в базу данных.')


# Основная функция
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    create_db()
    asyncio.run(main())
