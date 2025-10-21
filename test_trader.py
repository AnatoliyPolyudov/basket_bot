# test_trader.py

from monitor import OKXBasketMonitor
from trader import OKXBasketTrader
from console_observer import ConsoleObserver

def main():
    # Создаем монитор
    monitor = OKXBasketMonitor()

    # Подключаем ConsoleObserver для логов
    console_observer = ConsoleObserver()
    monitor.attach(console_observer)

    # Подключаем трейдер в режиме paper trading
    trader = OKXBasketTrader(paper_trading=True, max_exposure=1000)
    monitor.attach(trader)

    print("✅ Starting monitor + trader in PAPER TRADING mode...")
    # Запускаем монитор (он будет уведомлять трейдера)
    monitor.run(interval_minutes=1)  # маленький интервал для теста

if __name__ == "__main__":
    main()
