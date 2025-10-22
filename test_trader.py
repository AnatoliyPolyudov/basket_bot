# test_trader.py

from monitor import OKXBasketMonitor
from trader import OKXBasketTrader
from console_observer import ConsoleObserver
from telegram_observer import TelegramObserver

def main():
    # --- Создаём монитор ---
    monitor = OKXBasketMonitor()

    # --- Подключаем ConsoleObserver для логов ---
    console_observer = ConsoleObserver()
    monitor.attach(console_observer)

    # --- Подключаем трейдер в режиме Paper Trading ---
    trader = OKXBasketTrader(paper_trading=True, max_exposure=1000)
    monitor.attach(trader)

    # --- Подключаем TelegramObserver с кнопками ---
    telegram_observer = TelegramObserver(
        token="YOUR_TELEGRAM_BOT_TOKEN",
        chat_id="YOUR_CHAT_ID",
        trader=trader  # передаём трейдера для кнопок
    )
    monitor.attach(telegram_observer)

    print("✅ Starting monitor + trader in PAPER TRADING mode...")
