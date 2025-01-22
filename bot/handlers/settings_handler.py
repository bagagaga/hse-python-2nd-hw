import asyncio
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
import re
from bot.utils.logging import logger
from bot.db.crud import create_db
from bot.db.crud import create_log_tables
from bot.db.crud import get_user_by_id
from config.config import BOT_TOKEN
from bot.db.crud import (
    add_user,
    update_user,
    log_water,
    log_food,
    log_exercise,
    get_daily_summary,
)
from bot.utils.calculation import (
    calculate_exercise_calories,
    calculate_calorie_goal,
    calculate_water_goal,
    get_food_info,
    get_weather,
)
from bot.utils.calculation import EXTRA_WATER_ACTIVITY

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)


class ProfileSetup(StatesGroup):
    weight = State()
    height = State()
    age = State()
    activity = State()
    city = State()
    calorie_goal = State()
    water_goal = State()
    set_custom_calorie_goal = State()
    set_custom_water_goal = State()


class FoodLogState(StatesGroup):
    waiting_for_food_name = State()
    waiting_for_food_amount = State()


@router.message(F.text == "/set_profile")
async def set_profile_handler(message: types.Message, state: FSMContext):
    await message.answer("Введите ваш вес (в кг):")
    await state.set_state(ProfileSetup.weight)
    logger.info(f"User {message.from_user.id} requested /set_profile")


@router.message(ProfileSetup.weight)
async def set_weight(message: types.Message, state: FSMContext):
    try:
        weight = int(message.text)
        await state.update_data(weight=weight)
        await message.answer("Введите ваш рост (в см):")
        await state.set_state(ProfileSetup.height)
    except ValueError:
        await message.answer("🚫 Пожалуйста, введите числовое значение для веса.")


@router.message(ProfileSetup.height)
async def set_height(message: types.Message, state: FSMContext):
    try:
        height = int(message.text)
        await state.update_data(height=height)
        await message.answer("Введите ваш возраст:")
        await state.set_state(ProfileSetup.age)
    except ValueError:
        await message.answer("🚫 Пожалуйста, введите числовое значение для роста.")


@router.message(ProfileSetup.age)
async def set_age(message: types.Message, state: FSMContext):
    try:
        age = int(message.text)
        await state.update_data(age=age)
        await message.answer("Сколько минут активности у вас в день?")
        await state.set_state(ProfileSetup.activity)
    except ValueError:
        await message.answer("🚫 Пожалуйста, введите числовое значение для возраста.")


@router.message(ProfileSetup.activity)
async def set_activity(message: types.Message, state: FSMContext):
    try:
        activity = int(message.text)
        await state.update_data(activity=activity)
        await message.answer("В каком городе вы находитесь? Например, Порту.")
        await state.set_state(ProfileSetup.city)
    except ValueError:
        await message.answer("🚫 Пожалуйста, введите числовое значение для активности.")


@router.message(ProfileSetup.city)
async def set_city(message: types.Message, state: FSMContext):
    try:
        city = message.text
        get_weather(city)
        data = await state.get_data()

        weight = data["weight"]
        height = data["height"]
        age = data["age"]
        activity = data["activity"]

        waiting_message = await message.answer(
            "🔄 Составляю план, пожалуйста, подождите..."
        )
        await asyncio.sleep(2)

        calorie_goal = calculate_calorie_goal(
            weight=weight, height=height, age=age, activity_minutes=activity
        )
        water_goal = calculate_water_goal(
            weight=weight, activity_minutes=activity, city=city
        )

        await state.update_data(
            city=city,
            weight=weight,
            height=height,
            age=age,
            activity=activity,
            calorie_goal=calorie_goal,
            water_goal=water_goal,
        )

        keyboard_calorie_goal = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Да", callback_data="calorie_goal_yes")],
                [InlineKeyboardButton(text="Нет", callback_data="calorie_goal_no")],
            ]
        )
        await waiting_message.edit_text(
            f"🌱☀️ Я рекомендую придерживаться следующей цели по калориям: {round(calorie_goal)} ккал.\n\n"
            f"❓ Вы согласны с этой целью?",
            reply_markup=keyboard_calorie_goal,
        )
    except ValueError:
        await waiting_message.edit_text(
            "🚫 Не можем найти такой город. Пожалуйста, попробуйте еще раз."
        )


@router.message(ProfileSetup.set_custom_calorie_goal, F.text.regexp(r"^\d+$"))
async def set_custom_calorie_goal(message: types.Message, state: FSMContext):
    custom_calorie_goal = int(message.text)
    await state.update_data(calorie_goal=custom_calorie_goal)
    await message.answer("✅ Цель по калориям установлена.")
    await ask_water_goal(message, state)


@router.message(ProfileSetup.set_custom_water_goal, F.text.regexp(r"^\d+$"))
async def set_custom_water_goal(message: types.Message, state: FSMContext):
    custom_water_goal = int(message.text)
    await state.update_data(water_goal=custom_water_goal)
    await message.answer("✅ Цель по воде установлена.")
    await finalize_profile(message, state)


@router.callback_query(lambda c: c.data and c.data.startswith("calorie_goal_"))
async def handle_calorie_goal_confirmation(
    callback_query: types.CallbackQuery, state: FSMContext
):
    if callback_query.data == "calorie_goal_yes":
        await ask_water_goal(callback_query.message, state)
    else:
        await callback_query.message.edit_text(
            "💬 Пожалуйста, введите свою цель по калориям (например: 2000):"
        )
        await state.set_state(ProfileSetup.set_custom_calorie_goal)


async def ask_water_goal(message: types.Message, state: FSMContext):
    data = await state.get_data()
    water_goal = data["water_goal"]

    keyboard_water_goal = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="water_goal_yes")],
            [InlineKeyboardButton(text="Нет", callback_data="water_goal_no")],
        ]
    )
    await message.answer(
        f"💧 Я рекомендую вам выпивать {round(water_goal)} мл воды в день.\n\n"
        f"❓ Вы согласны с этой целью?",
        reply_markup=keyboard_water_goal,
    )


@router.callback_query(lambda c: c.data and c.data.startswith("water_goal_"))
async def handle_water_goal_confirmation(
    callback_query: types.CallbackQuery, state: FSMContext
):
    if callback_query.data == "water_goal_yes":
        await finalize_profile(callback_query.message, state)
    else:
        await callback_query.message.edit_text(
            "💬 Пожалуйста, введите свою цель по воде (в мл):"
        )
        await state.set_state(ProfileSetup.set_custom_water_goal)


async def finalize_profile(message: types.Message, state: FSMContext):
    data = await state.get_data()
    existing_user = get_user_by_id(message.from_user.id)
    weight = data["weight"]
    height = data["height"]
    age = data["age"]
    activity = data["activity"]
    calorie_goal = data["calorie_goal"]
    city = data["city"]
    water_goal = data["water_goal"]

    if existing_user:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Да", callback_data="update_profile_yes")],
                [InlineKeyboardButton(text="Нет", callback_data="update_profile_no")],
            ]
        )
        await message.answer(
            "Профиль уже существует. Хотите обновить информацию?", reply_markup=keyboard
        )

        await state.update_data(
            city=city,
            weight=weight,
            height=height,
            age=age,
            activity=activity,
            calorie_goal=calorie_goal,
            water_goal=water_goal,
        )
    else:
        add_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            weight=weight,
            height=height,
            age=age,
            activity=activity,
            city=city,
            water_goal=water_goal,
            calorie_goal=calorie_goal,
        )
        await message.answer(
            f"Ваш профиль создан!\nЦель воды: {round(water_goal)} мл\nЦель калорий: {round(calorie_goal)} ккал."
        )
        await state.clear()


@router.callback_query(lambda c: c.data and c.data.startswith("update_profile_"))
async def handle_update_confirmation(
    callback_query: types.CallbackQuery, state: FSMContext
):
    if callback_query.data == "update_profile_yes":
        data = await state.get_data()
        update_user(
            user_id=callback_query.from_user.id,
            weight=data["weight"],
            height=data["height"],
            age=data["age"],
            activity=data["activity"],
            city=data["city"],
            water_goal=data["water_goal"],
            calorie_goal=data["calorie_goal"],
        )
        await callback_query.message.edit_text(
            f"Ваш профиль успешно обновлен!\nЦель воды: {round(data['water_goal'])} мл\nЦель калорий: {round(data['calorie_goal'])} ккал."
        )
        await state.clear()
    elif callback_query.data == "update_profile_no":
        await callback_query.message.edit_text("Ваш профиль остался без изменений.")
        await state.clear()


@router.message(Command("log_water"))
async def log_water_handler(message: types.Message):
    logger.info(f"User {message.from_user.id} requested /log_water")
    try:
        match = re.search(r"[-+]?\d*[\.,]?\d+", message.text)
        if match:
            amount = match.group().replace(",", ".")
            log_water(message.from_user.id, amount)

            user_summary = get_daily_summary(message.from_user.id)
            water_left = (
                user_summary.get("water_goal", 0)
                - user_summary.get("total_water_ml", 0)
                - user_summary.get("extra_water", 0)
            )
            message_log = f"💧 Записано {amount} мл воды."
            if water_left <= 0.0:
                await message.answer(f"{message_log} Вы выполнили дневную норму воды!")
            else:
                await message.answer(
                    f"{message_log} Осталось выпить {round(water_left, 2)} мл."
                )

            logger.debug(f"Logged {amount} of water for user {message.from_user.id}")
        else:
            logger.debug(f"Cannot log water amount for user {message.from_user.id}")
            await message.answer(
                "🚫 Пожалуйста, укажите количество воды в мл, например: /log_water 500"
            )
    except Exception as e:
        await message.answer(
            f"Возникла неизвестная ошибка. Пожалуйста, попробуйте еще раз."
        )
        logger.error(f"Cannot log water: {e}")


@router.message(Command("log_food"))
async def log_food_handler(
    message: types.Message, command: CommandObject, state: FSMContext
):
    logger.info(f"User {message.from_user.id} requested /log_food")
    food_name = command.args.strip() if command.args else None

    if not food_name:
        await message.answer("❓ Укажите название продукта, например: /log_food банан")
        return

    waiting_message = await message.answer(
        "🔄 Ищу информацию о продукте, пожалуйста, подождите..."
    )
    food_info = get_food_info(food_name)

    if not food_info:
        await waiting_message.edit_text(
            "🚫 Не удалось найти информацию о продукте. Попробуйте снова."
        )
        return

    calories_per_100g = food_info.get("calories", 0.0)
    await state.update_data(food_name=food_name, calories_per_100g=calories_per_100g)

    await waiting_message.edit_text(
        f"🍌 {food_name.capitalize()} — {round(calories_per_100g)} ккал на 100 г.\n"
        "Сколько грамм вы съели? Введите число."
    )
    await state.set_state(FoodLogState.waiting_for_food_amount)


@router.message(FoodLogState.waiting_for_food_amount, F.text.regexp(r"^\d+$"))
async def process_food_amount(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        food_name = data["food_name"]
        calories_per_100g = data["calories_per_100g"]

        grams = int(message.text)
        calories = (calories_per_100g * grams) / 100
        log_food(message.from_user.id, food_name, calories_per_100g, grams)

        await message.answer(
            f"✅ Записано: {round(calories, 1)} ккал из {grams} г {food_name.capitalize()}.\n"
            f"Продолжайте следить за своим рационом! 🥗"
        )
        await state.clear()
    except ValueError:
        await message.answer(
            "🚫 Пожалуйста, введите числовое значение для веса продукта."
        )


@router.message(FoodLogState.waiting_for_food_amount)
async def handle_invalid_food_amount(message: types.Message, state: FSMContext):
    await message.answer("🚫 Пожалуйста, введите числовое значение для веса продукта.")
    await state.set_state()


@router.message(Command("log_workout"))
async def log_workout_handler(message: types.Message):
    logger.info(f"User {message.from_user.id} requested /log_workout")
    args = message.text.removeprefix("/log_workout").strip().split()
    if len(args) < 2:
        await message.answer(
            "❓ Укажите тип тренировки и длительность, например:\n"
            "/log_workout бег 30"
        )
        return

    exercise_type, duration_minutes = args[0], args[1]
    try:
        duration_minutes = int(duration_minutes)

        calories_burned = calculate_exercise_calories(exercise_type, duration_minutes)
        extra_water = (duration_minutes / 30) * EXTRA_WATER_ACTIVITY

        log_exercise(
            message.from_user.id, exercise_type, duration_minutes, calories_burned
        )
        log_water(message.from_user.id, -extra_water)

        await message.answer(
            f"🏋️‍♂️ {exercise_type.capitalize()}\n"
            f"- Продолжительность: {duration_minutes} мин\n"
            f"- Потрачено: {calories_burned:.1f} ккал\n"
            f"- Дополнительно выпейте: {extra_water:.1f} мл воды 💧"
        )
    except ValueError:
        await message.answer(
            "🚫 Укажите длительность тренировки числом, например: /log_workout плавание 45"
        )
        logger.debug(f"Cannot log workout amount for user {message.from_user.id}")
    except Exception as e:
        await message.answer("🚫 Ошибка при обработке тренировки. Попробуйте снова.")
        logger.error(f"Cannot log workout: {e}")


@router.message(Command("check_progress"))
async def check_progress_handler(message: types.Message):
    try:
        logger.info(f"User {message.from_user.id} requested /check_progress")
        user_summary = get_daily_summary(message.from_user.id)

        total_calories_consumed = user_summary.get("total_calories_consumed", 0)
        total_calories_burned = user_summary.get("total_calories_burned", 0)
        total_water_ml = user_summary.get("total_water_ml", 0)
        water_delta = (
            user_summary.get("water_goal", 0)
            - total_water_ml
            - user_summary.get("extra_water", 0)
        )

        await message.answer(
            "📊 Прогресс:\n"
            f"Вода:\n- Выпито: {total_water_ml:.1f} мл.\n"
            f"- Осталось: {water_delta if water_delta > 0 else 0:.1f} мл.\n\n"
            f"Калории:\n- Потреблено: {round(total_calories_consumed)} ккал из "
            f"{round(user_summary.get('calorie_goal', 0))} ккал.\n"
            f"- Потрачено: {round(total_calories_burned)} ккал.\n"
            f"- Баланс: {round(total_calories_consumed - total_calories_burned)} ккал.\n"
        )
    except Exception as e:
        await message.answer("🚫 Ошибка при получении данных. Попробуйте снова.")
        logger.error(f"Cannot log workout: {e}")


async def set_bot_commands():
    commands = [
        types.BotCommand(command="/set_profile", description="Настроить профиль"),
        types.BotCommand(
            command="/log_water", description="Записать количество выпитой воды"
        ),
        types.BotCommand(command="/log_food", description="Добавить съеденную еду"),
        types.BotCommand(command="/log_workout", description="Записать тренировку"),
        types.BotCommand(
            command="/check_progress", description="Показать прогресс за день"
        ),
    ]
    await bot.set_my_commands(commands)


async def main():
    create_db()
    create_log_tables()
    logger.debug("Databases are configured.")

    dp.shutdown.register(on_shutdown)
    dp.startup.register(on_startup)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

    await dp.start_polling(bot)


async def on_startup():
    await set_bot_commands()
    logger.info("Bot launched!")


async def on_shutdown():
    logger.info("Bot stopped!")
