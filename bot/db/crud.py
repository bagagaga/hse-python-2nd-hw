import sqlite3
from datetime import datetime, date
from config.config import DATABASE_URL
from bot.utils.logging import logger


def execute_query(query, params=(), fetchone=False, fetchall=False):
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if fetchone:
            result = cursor.fetchone()
        elif fetchall:
            result = cursor.fetchall()
        else:
            result = None
        conn.commit()
        return result
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


def create_db():
    execute_query('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        weight INTEGER,
                        height INTEGER,
                        age INTEGER,
                        activity INTEGER,
                        city TEXT,
                        water_goal INTEGER,
                        calorie_goal INTEGER)''')


def get_user_by_id(user_id: int):
    row = execute_query("SELECT * FROM users WHERE user_id = ?", (user_id,), fetchone=True)
    if row:
        keys = ["user_id", "username", "weight", "height", "age", "activity", "city", "water_goal", "calorie_goal"]
        return dict(zip(keys, row))
    return None


def add_user(user_id, username, weight, height, age, activity, city, water_goal, calorie_goal):
    try:
        execute_query('''INSERT INTO users 
                         (user_id, username, weight, height, age, activity, city, water_goal, calorie_goal) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (user_id, username, weight, height, age, activity, city, water_goal, calorie_goal))
    except sqlite3.IntegrityError:
        raise ValueError(f"User with ID {user_id} already exists.")


def delete_user(user_id):
    execute_query('DELETE FROM users WHERE user_id = ?', (user_id,))


def update_user(user_id, **kwargs):
    for key, value in kwargs.items():
        execute_query(f'UPDATE users SET {key} = ? WHERE user_id = ?', (value, user_id))


def create_log_tables():
    log_tables = [
        '''CREATE TABLE IF NOT EXISTS water_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp DATETIME,
            amount_ml FLOAT,
            FOREIGN KEY(user_id) REFERENCES users(user_id))''',
        '''CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp DATETIME,
            food TEXT,
            calories_per_100g FLOAT,
            grams FLOAT,
            FOREIGN KEY(user_id) REFERENCES users(user_id))''',
        '''CREATE TABLE IF NOT EXISTS exercise_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            exercise_type TEXT,
            timestamp DATETIME,
            duration_minutes FLOAT,
            calories_burned FLOAT,
            FOREIGN KEY(user_id) REFERENCES users(user_id))'''
    ]
    for table_query in log_tables:
        execute_query(table_query)


def log_entry(table, user_id, **kwargs):
    columns = ', '.join(kwargs.keys())
    placeholders = ', '.join(['?'] * len(kwargs))
    query = f'INSERT INTO {table} (user_id, {columns}) VALUES (?, {placeholders})'
    execute_query(query, (user_id, *kwargs.values()))


def log_water(user_id, amount_ml):
    log_entry('water_logs', user_id, timestamp=datetime.now(), amount_ml=amount_ml)


def log_food(user_id, food, calories_per_100g, grams):
    log_entry('food_logs', user_id, timestamp=datetime.now(), food=food, calories_per_100g=calories_per_100g, grams=grams)


def log_exercise(user_id, exercise_type, duration_minutes, calories_burned):
    log_entry('exercise_logs', user_id, timestamp=datetime.now(), exercise_type=exercise_type, duration_minutes=duration_minutes, calories_burned=calories_burned)


def get_daily_summary(user_id):
    today = date.today().isoformat()

    summary_queries = {
        "water_goal": "SELECT water_goal FROM users WHERE user_id = ?",
        "calorie_goal": "SELECT calorie_goal FROM users WHERE user_id = ?",
        "total_water_ml": '''SELECT SUM(amount_ml) FROM water_logs 
                             WHERE user_id = ? AND DATE(timestamp) = ? AND amount_ml > 0''',
        "extra_water": '''SELECT SUM(amount_ml) FROM water_logs 
                          WHERE user_id = ? AND DATE(timestamp) = ? AND amount_ml < 0''',
        "total_calories_consumed": '''SELECT SUM((calories_per_100g * grams) / 100) 
                                      FROM food_logs WHERE user_id = ? AND DATE(timestamp) = ?''',
        "total_calories_burned": '''SELECT SUM(calories_burned) FROM exercise_logs 
                                    WHERE user_id = ? AND DATE(timestamp) = ?'''
    }

    summary = {}
    for key, query in summary_queries.items():
        params = (user_id, today) if "DATE" in query else (user_id,)
        summary[key] = execute_query(query, params, fetchone=True)[0] or 0

    return summary
