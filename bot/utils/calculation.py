import requests
from config.config import WEATHER_API_KEY
from bot.utils.logging import logger

BASE_WATER_MULTIPLIER = 30  # мл воды на кг веса
BASE_WATER_ACTIVITY = 500  # мл за 30 минут активности
EXTRA_WATER_ACTIVITY = 200  # мл за 30 минут тренировки
EXTRA_WATER_HOT_WEATHER = 500  # мл за жаркую погоду
HOT_WEATHER_THRESHOLD = 25  # °C
DEFAULT_TIMEOUT_SECONDS = 10

CALORIE_MULTIPLIER = {
    "weight": 10,
    "height": 6.25,
    "age": 5,
}

EXERCISE_CALORIES = {
    "бег": 10,  # ккал/мин
    "ходьба": 5,
    "плавание": 8,
    "велосипед": 7,
}


def get_food_info(product_name):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&search_terms={product_name}&json=true"
    food_info_result = None
    try:
        response = requests.get(url, timeout=DEFAULT_TIMEOUT_SECONDS)
        if response.status_code == 200:
            data = response.json()
            products = data.get("products", [])
            if products:  # Проверяем, есть ли найденные продукты
                first_product = products[0]
                food_info_result = {
                    "name": first_product.get("product_name", "Неизвестно"),
                    "calories": first_product.get("nutriments", {}).get(
                        "energy-kcal_100g", 0
                    ),
                }
                logger.debug(food_info_result)
    except requests.exceptions.Timeout:
        logger.error(f"Request timed out after {DEFAULT_TIMEOUT_SECONDS} seconds.")
    except Exception as e:
        logger.error(f"Cannot find food: {e}")

    return food_info_result


def get_weather(city: str) -> dict:

    response = requests.get(
        url="http://api.openweathermap.org/data/2.5/forecast",
        params={"q": city, "appid": WEATHER_API_KEY, "units": "metric"},
    )
    if response.status_code != 200:
        raise ValueError("Ошибка при получении данных о погоде.")

    forecast_data = response.json()
    tomorrow_temp = forecast_data["list"][1]["main"]["temp"]
    logger.debug(f"Get weather forecast in {city}: {tomorrow_temp}")
    return tomorrow_temp


def calculate_water_goal(weight: float, activity_minutes: int, city: str) -> float:
    water_goal = weight * BASE_WATER_MULTIPLIER
    water_goal += (activity_minutes / 30) * BASE_WATER_ACTIVITY
    try:
        tomorrow_temp = get_weather(city)
        if tomorrow_temp > HOT_WEATHER_THRESHOLD:
            water_goal += EXTRA_WATER_HOT_WEATHER
    except ValueError as e:
        logger.error(f"Get weather API error: {e}")

    return water_goal


def calculate_calorie_goal(
    weight: float, height: float, age: int, activity_minutes: int
) -> float:
    calorie_goal = (
        CALORIE_MULTIPLIER["weight"] * weight
        + CALORIE_MULTIPLIER["height"] * height
        - CALORIE_MULTIPLIER["age"] * age
        + 5
    )

    calorie_goal += activity_minutes * (200 / 60)

    return calorie_goal


def calculate_exercise_calories(exercise_type: str, duration_minutes: int) -> float:
    calories_per_minute = EXERCISE_CALORIES.get(exercise_type.lower(), 6)
    return calories_per_minute * duration_minutes
