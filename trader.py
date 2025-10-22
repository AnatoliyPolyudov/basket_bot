# trader.py

from observer import Observer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OKXBasketTrader(Observer):
    def __init__(self, paper_trading=True, max_exposure=1000):
        """
        paper_trading: True — не ставит реальные ордера, только выводит в консоль.
        max_exposure: максимальная сумма на одну позицию.
        """
        self.paper_trading = paper_trading
        self.max_exposure = max_exposure
        self.current_positions = {}  # словарь вида {'BTC/USDT': size, 'ETH/USDT': size}

    def update(self, data):
        """
        Метод Observer: вызывается при каждом новом сигнале от монитора.
        """
        signal = data.get("signal")
        if signal:
            self.execute_signal(signal, data)

    def execute_signal(self, signal, data):
        """
        Пока просто выводит, что будет сделано.
        """
        if self.paper_trading:
            logger.info(f"[PAPER TRADING] Signal received: {signal}")
            logger.info(f"[PAPER TRADING] Data: {data}")
        else:
            logger.info(f"[REAL TRADING] Would execute: {signal}")

    # --- Новые методы для кнопок ---
    def open_position(self, symbol: str, size=None):
        if size is None:
            size = self.max_exposure
        self.current_positions[symbol] = size
        logger.info(f"[PAPER TRADING] Opened position {symbol} with size {size}")

    def close_position(self, symbol: str):
        if symbol in self.current_positions:
            del self.current_positions[symbol]
            logger.info(f"[PAPER TRADING] Closed position {symbol}")
        else:
            logger.info(f"[PAPER TRADING] No open position to close for {symbol}")
