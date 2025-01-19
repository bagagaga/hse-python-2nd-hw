import logging
from config.config import LOG_FILE

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()  # Для вывода логов в консоль
    ]
)

logger = logging.getLogger(__name__)
