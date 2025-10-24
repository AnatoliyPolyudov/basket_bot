from observer import Observer
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class OKXBasketTrader(Observer):
    def __init__(self, paper_trading=True, max_exposure=1000):
        self.paper_trading = paper_trading
        self.max_exposure = max_exposure
        self.current_positions = {}  # 🆕 Формат: {pair_name: {signal: str, size: float}}

    def update(self, data):
        """
        Метод Observer: вызывается при каждом новом сигнале от монитора.
        """
        # 🆕 ОБРАБАТЫВАЕМ ДАННЫЕ ОТ R-ПОДХОДА
        pairs_data = data.get('pairs_data', [])
        
        for pair_data in pairs_data:
            signal = pair_data.get("signal")
            pair_name = pair_data.get("pair_name")
            
            if signal and signal != "HOLD" and signal != "NO DATA" and signal != "NO TRADE - NOT STATIONARY":
                self.execute_signal(signal, pair_data, pair_name)

    def execute_signal(self, signal, data, pair_name):
        """
        Обработка сигнала для конкретной пары.
        """
        if self.paper_trading:
            logger.debug(f"[PAPER TRADING] Pair {pair_name}: Signal received: {signal}")
        else:
            logger.info(f"[REAL TRADING] Pair {pair_name}: Would execute: {signal}")

    # --- Методы для кнопок ---
    def open_position(self, signal: str, pair_name: str, size=None):
        if size is None:
            size = self.max_exposure / 4  # 🆕 Распределяем капитал по парам
        
        # 🆕 Сохраняем позицию с информацией о паре
        self.current_positions[pair_name] = {
            'signal': signal,
            'size': size,
            'pair_name': pair_name
        }
        logger.info(f"✅ [PAPER] OPENED: {pair_name} - {signal} with size {size}")

    def close_position(self, signal: str, pair_name: str):
        if pair_name in self.current_positions:
            position = self.current_positions[pair_name]
            del self.current_positions[pair_name]
            logger.info(f"✅ [PAPER] CLOSED: {pair_name} - {position['signal']}")
        else:
            logger.warning(f"⚠️ [PAPER] No open position to close for {pair_name}")