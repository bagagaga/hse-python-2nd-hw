from sqlalchemy import Column, Integer, String, Float, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

# Описание таблицы пользователей
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    age = Column(Integer, nullable=False)
    weight = Column(Float, nullable=False)
    height = Column(Float, nullable=False)
    gender = Column(String(1), nullable=False)
    activity_level = Column(Integer, nullable=False)

# Настройка подключения
def get_engine(database_url):
    return create_engine(database_url)

def get_session(database_url):
    engine = get_engine(database_url)
    Session = sessionmaker(bind=engine)
    return Session()

# Создание таблиц
def init_db(database_url):
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
