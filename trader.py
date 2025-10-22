# trader.py

from observer import Observer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OKXBasketTrader(Observer):
    def __init__(self, paper_trading=True, max_exposure=1000):
        self.paper_trading = paper_trading
        self.max_exposure = max_exposure
        self.current_positions = {}  # {'BTC/USDT': size, ...}

    def update(self, data):
        """Вызывается монитором при новом сигнале"""
        signal = data.get("signal")
        if signal:
            self.execute_signal(signal, data)

    def execute_signal(self, signal, data):
        """Обработка сигнала от монитора"""
        if self.paper_trading:
            logger.info(f"[PAPER TRADING] Signal received: {signal}")
            logger.info(f"[PAPER TRADING] Data: {data}")
        else:
            logger.info(f"[REAL TRADING] Would execute: {signal}")

    # Новые методы для кнопок
    def open_position(self, symbol, size=None):
        """Открыть позицию (paper)"""
        size = size or self.max_exposure
        self.current_positions[symbol] = self.current_positions.get(symbol, 0) + size
        logger.info(f"[PAPER TRADING] Opened {symbol} position: {size}")

    def close_position(self, symbol):
        """Закрыть позицию (paper)"""
        if symbol in self.current_positions:
            logger.info(f"[PAPER TRADING] Closed {symbol} position: {self.current_positions[symbol]}")
            del self.current_positions[symbol]
        else:
            logger.info(f"[PAPER TRADING] No position to close for {symbol}")
