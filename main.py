import logging
import time
import pandas as pd
from pairs_core import BacktestPair, BacktestPortfolio, GenerateReport_xts
from telegram_bot import start_telegram_bot  # если у тебя есть функция запуска бота

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
    logging.info("Basket bot started")

    # Пример: запуск бэктеста для одной пары
    try:
        logging.info("Loading pair data from CSV...")
        data = pd.read_csv('pairs_sample.csv')  # укажи реальный CSV
        logging.info("Running backtest for single pair...")
        result = BacktestPair(data, mean=35, generateReport=True)
        logging.info("Single pair backtest done")

        # Пример: запуск портфеля
        logging.info("Running portfolio backtest...")
        names = ['pair1.csv', 'pair2.csv']  # список реальных CSV файлов
        portfolio_returns = BacktestPortfolio(names, startDate='2024-01-01', endDate='2025-10-24', leverage=1)
        logging.info("Portfolio backtest done")

    except Exception as e:
        logging.error(f"Error in backtesting: {e}")

    # Запуск телеграм-бота (если есть)
    try:
        logging.info("Starting Telegram bot...")
        start_telegram_bot()  # замени на функцию из твоего telegram_bot.py
        logging.info("Telegram bot is running")
    except Exception as e:
        logging.error(f"Error in Telegram bot: {e}")

    # Если нужно, можно запускать основной цикл
    while True:
        try:
            logging.info("Bot main loop tick...")
            # Здесь можно добавлять периодические задачи, например обновление портфеля
            time.sleep(60)
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
