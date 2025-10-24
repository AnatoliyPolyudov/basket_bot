import ccxt
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime, timedelta
from observer import Subject
from console_observer import ConsoleObserver
from trader import OKXBasketTrader
from telegram_observer import TelegramObserver
from callback_handler import handle_callback
import threading
import requests
import sys
from statsmodels.tsa.stattools import adfuller
import warnings
warnings.filterwarnings('ignore')

# 🎯 ИМПОРТИРУЕМ КОНФИГУРАЦИЮ ПАР
from pairs_config import get_preset, PAIR_PRESETS

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

class RStylePairMonitor(Subject):
    def __init__(self, pair_preset="full_20_pairs"):
        super().__init__()
        self.exchange = ccxt.okx({
            "enableRateLimit": True,
            "options": {"defaultType": "swap"},
            "sandbox": False
        })
        
        # 🎯 ЗАГРУЖАЕМ ПАРЫ ИЗ КОНФИГА
        self.trading_pairs = get_preset(pair_preset)
        if not self.trading_pairs:
            logger.error(f"❌ Preset '{pair_preset}' not found! Using default.")
            self.trading_pairs = get_preset("full_20_pairs")
        
        logger.info(f"🎯 Loaded {len(self.trading_pairs)} pairs from preset: {pair_preset}")
        
        # Все уникальные символы для загрузки данных
        self.all_symbols = set()
        for pair in self.trading_pairs:
            self.all_symbols.add(pair["asset_a"])
            self.all_symbols.add(pair["asset_b"])
        self.all_symbols = list(self.all_symbols)
        
        self.historical_data = {}
        self.timeframe = "15m"
        self.lookback_bars = 672
        self.data_loaded = False
        self.window_bars = 35
        
        # ADF настройки
        self.adf_lookbacks = [60, 40, 20]
        self.adf_critical_value = -2.58
        
        # Храним состояние для каждой пары
        self.pair_states = {}
        for pair in self.trading_pairs:
            self.pair_states[pair["name"]] = {
                'current_signal': 'HOLD',
                'adf_passed': False,
                'position_open': False,
                'data_loaded': False
            }
    
    # ... остальные методы остаются без изменений ...
    # complete_data_reset, fetch_historical_data, get_pair_historical_spread, 
    # calculate_adf_test, calculate_pair_spread, calculate_zscore_for_pair,
    # trading_signal_for_pair, get_current_prices, run
    
    def switch_preset(self, new_preset):
        """Динамическое переключение пресета пар"""
        logger.info(f"🔄 Switching to preset: {new_preset}")
        
        new_pairs = get_preset(new_preset)
        if not new_pairs:
            logger.error(f"❌ Preset '{new_preset}' not found!")
            return False
        
        self.trading_pairs = new_pairs
        
        # Обновляем список символов
        self.all_symbols = set()
        for pair in self.trading_pairs:
            self.all_symbols.add(pair["asset_a"])
            self.all_symbols.add(pair["asset_b"])
        self.all_symbols = list(self.all_symbols)
        
        # Сбрасываем состояния
        self.pair_states = {}
        for pair in self.trading_pairs:
            self.pair_states[pair["name"]] = {
                'current_signal': 'HOLD',
                'adf_passed': False,
                'position_open': False,
                'data_loaded': False
            }
        
        # Перезагружаем данные
        return self.complete_data_reset()

# 🎯 ФУНКЦИЯ ДЛЯ ТЕСТИРОВАНИЯ ПАР
def test_pair_presets():
    """Тестирование различных пресетов пар"""
    from pairs_config import test_pair_combinations
    
    print("🔍 TESTING ALL PAIR PRESETS...")
    results = test_pair_combinations()
    
    for preset, data in results.items():
        print(f"\n📊 {preset.upper()}:")
        print(f"   Valid pairs: {data['valid']}/{data['total']}")
        
        if data['invalid']:
            print("   ❌ Invalid pairs:")
            for invalid_pair, reason in data['invalid']:
                print(f"      - {invalid_pair['name']}: {reason}")

if __name__ == "__main__":
    # 🎯 ВОЗМОЖНОСТЬ ВЫБОРА ПРЕСЕТА ЧЕРЕЗ АРГУМЕНТЫ
    import argparse
    
    parser = argparse.ArgumentParser(description='R-Style Pair Trading Monitor')
    parser.add_argument('--preset', type=str, default='full_20_pairs', 
                       help='Pair preset: top_10_btc_pairs, eth_cross_pairs, altcoin_pairs, full_20_pairs')
    parser.add_argument('--test', action='store_true', help='Test pair configurations')
    
    args = parser.parse_args()
    
    if args.test:
        test_pair_presets()
        sys.exit(0)
    
    # Запуск монитора с выбранным пресетом
    monitor = RStylePairMonitor(pair_preset=args.preset)
    monitor.attach(ConsoleObserver())

    trader = OKXBasketTrader(paper_trading=True, max_exposure=1000)
    monitor.attach(trader)

    telegram_observer = TelegramObserver(trader=trader)
    monitor.attach(telegram_observer)

    polling_thread = threading.Thread(target=telegram_polling, args=(trader,), daemon=True)
    polling_thread.start()

    monitor.run(interval_minutes=1)