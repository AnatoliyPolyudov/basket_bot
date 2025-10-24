from observer import Observer
import logging
from datetime import datetime
import json

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class OKXBasketTrader(Observer):
    def __init__(self, paper_trading=True, max_exposure=1000):
        self.paper_trading = paper_trading
        self.max_exposure = max_exposure
        self.current_positions = {}  # 🆕 Формат: {pair_name: {signal: str, size: float, entry_time: datetime, entry_z: float}}
        self.position_history = []   # 🆕 История всех сделок
        self.trading_enabled = True  # 🆕 Флаг включения/выключения торговли

    def update(self, data):
        """
        Метод Observer: вызывается при каждом новом сигнале от монитора.
        """
        if not self.trading_enabled:
            return
            
        # 🆕 ОБРАБАТЫВАЕМ ДАННЫЕ ОТ R-ПОДХОДА
        pairs_data = data.get('pairs_data', [])
        
        for pair_data in pairs_data:
            signal = pair_data.get("signal")
            pair_name = pair_data.get("pair_name")
            z_score = pair_data.get("z", 0)
            
            # 🆕 АВТОМАТИЧЕСКОЕ ЗАКРЫТИЕ ПО EXIT SIGNAL
            if signal == "EXIT_POSITION" and pair_name in self.current_positions:
                self.close_position(signal, pair_name, f"Auto-close on exit signal (Z={z_score:.2f})")
            
            # 🆕 АВТОМАТИЧЕСКОЕ ОТКРЫТИЕ ПО СИГНАЛАМ (если нет открытой позиции)
            elif (signal and 
                  signal not in ["HOLD", "NO DATA", "NO TRADE - NOT STATIONARY", "EXIT_POSITION"] and
                  pair_name not in self.current_positions):
                
                # 🆕 ПРОВЕРЯЕМ ADF ТЕСТ ПЕРЕД ОТКРЫТИЕМ
                adf_passed = pair_data.get("adf_passed", False)
                if adf_passed:
                    self.open_position(signal, pair_name, z_score=z_score)

    def execute_signal(self, signal, data, pair_name):
        """
        Обработка сигнала для конкретной пары.
        """
        if self.paper_trading:
            logger.debug(f"[PAPER TRADING] Pair {pair_name}: Signal received: {signal}")
        else:
            logger.info(f"[REAL TRADING] Pair {pair_name}: Would execute: {signal}")

    # --- 🆕 УЛУЧШЕННЫЕ МЕТОДЫ ДЛЯ КНОПОК ---
    def open_position(self, signal: str, pair_name: str, size=None, z_score=0):
        """Открытие позиции с полным трекингом"""
        if size is None:
            size = self.max_exposure / 4  # 🆕 Распределяем капитал по парам
        
        # 🆕 ПРОВЕРЯЕМ НЕТ ЛИ УЖЕ ОТКРЫТОЙ ПОЗИЦИИ
        if pair_name in self.current_positions:
            logger.warning(f"⚠️ [PAPER] Position already open for {pair_name}: {self.current_positions[pair_name]['signal']}")
            return False
        
        # 🆕 СОЗДАЕМ ПОЗИЦИЮ С ДЕТАЛЬНОЙ ИНФОРМАЦИЕЙ
        position = {
            'signal': signal,
            'size': size,
            'pair_name': pair_name,
            'entry_time': datetime.now(),
            'entry_z': z_score,
            'status': 'OPEN',
            'type': 'MANUAL' if 'MANUAL' in signal else 'AUTO'
        }
        
        self.current_positions[pair_name] = position
        
        # 🆕 ДОБАВЛЯЕМ В ИСТОРИЮ
        trade_record = position.copy()
        trade_record['action'] = 'OPEN'
        trade_record['timestamp'] = datetime.now().isoformat()
        self.position_history.append(trade_record)
        
        logger.info(f"✅ [PAPER] OPENED: {pair_name} - {signal} | Size: {size} | Z: {z_score:.2f}")
        return True

    def close_position(self, signal: str, pair_name: str, reason="Manual close"):
        """Закрытие позиции с сохранением в историю"""
        if pair_name not in self.current_positions:
            logger.warning(f"⚠️ [PAPER] No open position to close for {pair_name}")
            return False
        
        position = self.current_positions[pair_name]
        
        # 🆕 СОЗДАЕМ ЗАПИСЬ О ЗАКРЫТИИ
        close_record = {
            'action': 'CLOSE',
            'pair_name': pair_name,
            'original_signal': position['signal'],
            'close_signal': signal,
            'size': position['size'],
            'entry_time': position['entry_time'],
            'exit_time': datetime.now(),
            'entry_z': position['entry_z'],
            'exit_reason': reason,
            'duration_minutes': round((datetime.now() - position['entry_time']).total_seconds() / 60, 1),
            'timestamp': datetime.now().isoformat()
        }
        
        self.position_history.append(close_record)
        
        # 🆕 УДАЛЯЕМ ИЗ ТЕКУЩИХ ПОЗИЦИЙ
        del self.current_positions[pair_name]
        
        logger.info(f"✅ [PAPER] CLOSED: {pair_name} | Reason: {reason} | Duration: {close_record['duration_minutes']}min")
        return True

    # --- 🆕 МЕТОДЫ ДЛЯ ПОЛУЧЕНИЯ СТАТУСА ---
    def get_open_positions(self):
        """Возвращает список открытых позиций"""
        return self.current_positions

    def get_position_history(self, limit=10):
        """Возвращает историю сделок"""
        return self.position_history[-limit:] if self.position_history else []

    def get_trading_summary(self):
        """Возвращает сводку по торговле"""
        total_trades = len([h for h in self.position_history if h['action'] == 'CLOSE'])
        open_positions = len(self.current_positions)
        
        return {
            'total_trades': total_trades,
            'open_positions': open_positions,
            'current_positions': list(self.current_positions.keys()),
            'last_trades': self.get_position_history(5)
        }

    def export_trading_log(self, filename=None):
        """Экспорт лога торговли в файл"""
        if not filename:
            filename = f"trading_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        log_data = {
            'export_time': datetime.now().isoformat(),
            'summary': self.get_trading_summary(),
            'position_history': self.position_history,
            'current_positions': self.current_positions
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2, default=str)
            logger.info(f"✅ Trading log exported to {filename}")
            return True
        except Exception as e:
            logger.error(f"❌ Error exporting log: {e}")
            return False

    # --- 🆕 МЕТОДЫ УПРАВЛЕНИЯ ТОРГОВЛЕЙ ---
    def enable_trading(self):
        """Включить автоматическую торговлю"""
        self.trading_enabled = True
        logger.info("✅ AUTO TRADING ENABLED")

    def disable_trading(self):
        """Выключить автоматическую торговлю"""
        self.trading_enabled = False
        logger.info("🚫 AUTO TRADING DISABLED")

    def close_all_positions(self, reason="Manual close all"):
        """Закрыть все открытые позиции"""
        closed_count = 0
        for pair_name in list(self.current_positions.keys()):
            if self.close_position("CLOSE_ALL", pair_name, reason):
                closed_count += 1
        
        logger.info(f"✅ Closed {closed_count} positions")
        return closed_count