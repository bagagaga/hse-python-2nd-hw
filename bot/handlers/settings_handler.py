from aiogram import types, Dispatcher
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Функция управления настройками
async def settings_command(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("⚙️ Изменить параметры"))
    keyboard.add(KeyboardButton("⬅️ Назад"))

    await message.answer(
        "⚙️ Настройки бота:\n"
        "1. Изменить параметры пользователя\n"
        "2. Вернуться в главное меню",
        reply_markup=keyboard
    )

async def update_parameters(message: types.Message):
    await message.answer(
        "Введите новые параметры в формате:\n"
        "`Возраст, Вес (кг), Рост (см), Пол (М/Ж)`\n\n"
        "Пример: `30, 75, 180, М`",
        parse_mode="Markdown"
    )

@dp.message_handler(commands=['save'])
async def save_parameters(message: types.Message):
    try:
        age, weight, height, gender = message.text.split(",")
        age = int(age.strip())
        weight = float(weight.strip())
        height = float(height.strip())
        gender = gender.strip().upper()

        # Здесь логика сохранения данных пользователя (например, в файл или базу данных)

        await message.answer("✅ Параметры успешно обновлены!")
    except Exception:
        await message.answer("Ошибка: проверьте введенные данные.")

# Регистрация хэндлеров
def register_handlers(dp: Dispatcher):
    dp.register_message_handler(settings_command, Text(equals="⚙️ Настройки"))
    dp.register_message_handler(update_parameters, Text(equals="⚙️ Изменить параметры"))
    dp.register_message_handler(save_parameters, regexp=r"^\d{1,3},\s*\d{1,3}(.\d+)?,\s*\d{1,3},\s*[МЖ]$")
