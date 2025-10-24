import logging
from pairs_core import run_backtester  # пример функции из твоих модулей
from telegram_bot import start_bot      # пример запуска телеграм-бота
import time

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("basket-bot.log"),  # запись в файл
        logging.StreamHandler()                 # вывод в консоль
    ]
)

def main():
    logging.info("Bot started")

    # Пример цикла работы бота
    while True:
        try:
            logging.info("Fetching market data...")
            # здесь твоя функция работы с парами
            run_backtester()  # замените на реальный вызов
            logging.info("Backtest completed")

            logging.info("Running telegram bot tasks...")
            start_bot()  # если нужно, заменить на твой код
            logging.info("Telegram bot tasks done")

        except Exception as e:
            logging.error(f"Error occurred: {e}")

        # Пауза между циклами (например 60 секунд)
        time.sleep(60)

if __name__ == "__main__":
    main()
