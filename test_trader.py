from monitor import OKXBasketMonitor
from trader import OKXBasketTrader
from console_observer import ConsoleObserver
from telegram_observer import TelegramObserver

def main():
    monitor = OKXBasketMonitor()

    console_observer = ConsoleObserver()
    monitor.attach(console_observer)

    trader = OKXBasketTrader(paper_trading=True, max_exposure=1000)
    monitor.attach(trader)

    telegram_observer = TelegramObserver(
        token="YOUR_TOKEN",
        chat_id="YOUR_CHAT_ID",
        trader=trader  # передаём трейдера
    )
    monitor.attach(telegram_observer)

    print("✅ Starting monitor + trader in PAPER TRADING mode...")
    monitor.run(interval_minutes=1)

if __name__ == "__main__":
    main()
