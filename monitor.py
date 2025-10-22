import ccxt
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime
from observer import Subject
from console_observer import ConsoleObserver
from trader import OKXBasketTrader
from telegram_observer import TelegramObserver
from callback_handler import handle_callback
import threading
import requests

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

class OKXBasketMonitor(Subject):
    def __init__(self):
        super().__init__()
        self.exchange = ccxt.okx({
            "enableRateLimit": True,
            "options": {"defaultType": "swap"},
            "sandbox": False
        })
        self.target = "BTC/USDT:USDT"
        self.basket_symbols = ["ETH/USDT:USDT","BNB/USDT:USDT","SOL/USDT:USDT","XRP/USDT:USDT"]
        self.basket_weights = []
        self.historical_data = {}
        self.lookback_days = 30

    # --- все методы fetch_historical_data, calculate_basket_weights, get_current_prices, calculate_basket_price, calculate_spread_series, calculate_zscore, trading_signal оставляем без изменений ---

    def run(self, interval_minutes=1):
        logger.info("Starting OKX basket monitor...")
        if not self.fetch_historical_data():
            logger.error("Failed to fetch historical data.")
            return
        self.calculate_basket_weights()
        if not self.basket_symbols:
            logger.error("No valid symbols for monitoring.")
            return
        logger.info(f"Monitoring symbols: {self.basket_symbols}")

        while True:
            try:
                prices = self.get_current_prices()
                if not prices:
                    time.sleep(60)
                    continue

                z, spread, stats = self.calculate_zscore(prices)
                if z is not None:
                    mean, std = stats
                    signal = self.trading_signal(z)

                    report_data = {
                        "time": datetime.utcnow(),
                        "target_price": prices[self.target],
                        "basket_price": self.calculate_basket_price(prices),
                        "spread": spread,
                        "mean": mean,
                        "std": std,
                        "z": z,
                        "signal": signal,
                        "basket_symbols": self.basket_symbols,
                        "basket_weights": self.basket_weights
                    }

                    self.notify(report_data)
                else:
                    logger.warning("Z-score unavailable.")

                time.sleep(interval_minutes*60)
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user.")
                break
            except Exception as e:
                logger.warning(f"Error in loop: {e}")
                time.sleep(60)


# --- Telegram callback polling ---
def telegram_polling(trader):
    TELEGRAM_BOT_TOKEN = "8436652130:AAF6On0GJtRHfMZyqD3mpM57eXZfWofJeng"
    TELEGRAM_CHAT_ID = 317217451
    offset = None
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"

    while True:
        try:
            params = {'timeout': 30, 'offset': offset}
            response = requests.get(url, params=params, timeout=35)
            updates = response.json().get("result", [])
            for update in updates:
                if "callback_query" in update:
                    data = update["callback_query"]["data"]
                    handle_callback(data, trader)
                offset = (update["update_id"] + 1)
            time.sleep(1)
        except Exception as e:
            print("Telegram polling error:", e)
            time.sleep(5)


# --- Главная функция ---
def main():
    monitor = OKXBasketMonitor()

    # Console logs
    monitor.attach(ConsoleObserver())

    # Paper trading
    trader = OKXBasketTrader(paper_trading=True, max_exposure=1000)
    monitor.attach(trader)

    # Telegram notifications с кнопками
    telegram_observer = TelegramObserver(trader=trader)
    monitor.attach(telegram_observer)

    # Старт polling Telegram callback в отдельном потоке
    polling_thread = threading.Thread(target=telegram_polling, args=(trader,), daemon=True)
    polling_thread.start()

    # Тестовое сообщение при старте
    monitor.notify({
        "signal": "✅ Test message: TelegramObserver работает!",
        "z": 0,
        "spread": 0,
        "basket_price": 0,
        "target_price": 0
    })

    monitor.run(interval_minutes=1)


if __name__ == "__main__":
    main()
