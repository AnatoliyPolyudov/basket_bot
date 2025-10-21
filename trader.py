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
        На следующем шаге сюда будем добавлять реальные ордера.
        """
        if self.paper_trading:
            logger.info(f"[PAPER TRADING] Signal received: {signal}")
            logger.info(f"[PAPER TRADING] Data: {data}")
        else:
            logger.info(f"[REAL TRADING] Would execute: {signal}")
