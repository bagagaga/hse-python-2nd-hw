from bot.db.models import User

def add_user(session, telegram_id, age, weight, height, gender, activity_level):
    # Проверяем, существует ли пользователь
    user = session.query(User).filter(User.telegram_id == telegram_id).first()
    if user:
        user.age = age
        user.weight = weight
        user.height = height
        user.gender = gender
        user.activity_level = activity_level
    else:
        user = User(
            telegram_id=telegram_id,
            age=age,
            weight=weight,
            height=height,
            gender=gender,
            activity_level=activity_level
        )
        session.add(user)
    session.commit()

def get_user(session, telegram_id):
    return session.query(User).filter(User.telegram_id == telegram_id).first()
