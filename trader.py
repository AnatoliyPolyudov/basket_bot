from observer import Observer
import logging

# Установи уровень WARNING вместо INFO
logging.basicConfig(level=logging.WARNING)  # ← было INFO
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
        if signal and signal != "HOLD":  # ← ДОБАВЛЕНО: игнорируем HOLD сигналы
            self.execute_signal(signal, data)

    def execute_signal(self, signal, data):
        """
        Пока просто выводит, что будет сделано.
        """
        if self.paper_trading:
            # Используем debug вместо info для спам-сообщений
            logger.debug(f"[PAPER TRADING] Signal received: {signal}")
            logger.debug(f"[PAPER TRADING] Data: {data}")
        else:
            logger.info(f"[REAL TRADING] Would execute: {signal}")

    # --- Методы для кнопок ---
    def open_position(self, signal: str, size=None):
        if size is None:
            size = self.max_exposure
        self.current_positions[signal] = size
        # Оставляем info только для важных действий
        logger.info(f"✅ [PAPER] OPENED: {signal} with size {size}")

    def close_position(self, signal: str):
        if signal in self.current_positions:
            del self.current_positions[signal]
            logger.info(f"✅ [PAPER] CLOSED: {signal}")
        else:
            logger.warning(f"⚠️ [PAPER] No open position to close for {signal}")