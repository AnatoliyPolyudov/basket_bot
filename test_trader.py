from monitor import OKXBasketMonitor
from trader import OKXBasketTrader
from console_observer import ConsoleObserver
from telegram_observer import TelegramObserver

# --- Настройки Telegram ---
TELEGRAM_BOT_TOKEN = "8436652130:AAF6On0GJtRHfMZyqD3mpM57eXZfWofJeng"
TELEGRAM_CHAT_ID = "317217451"

def main():
    # --- Создаём монитор ---
    monitor = OKXBasketMonitor()

    # --- Подключаем ConsoleObserver для логов ---
    console_observer = ConsoleObserver()
    monitor.attach(console_observer)

    # --- Подключаем трейдер в Paper Trading режиме ---
    trader = OKXBasketTrader(paper_trading=True, max_exposure=1000)
    monitor.attach(trader)

    # --- Подключаем TelegramObserver с кнопками ---
    telegram_observer = TelegramObserver(
        token=TELEGRAM_BOT_TOKEN,
        chat_id=TELEGRAM_CHAT_ID,
        trader=trader
    )
    monitor.attach(telegram_observer)

    print("✅ Starting monitor + trader in PAPER TRADING mode...")
    monitor.run(interval_minutes=1)  # короткий интервал для теста

if __name__ == "__main__":
    main()
