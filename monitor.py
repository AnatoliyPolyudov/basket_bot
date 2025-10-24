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
    def __init__(self, pair_preset="ultra_liquid_8"):
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
            self.trading_pairs = get_preset("ultra_liquid_8")
        
        logger.info(f"🎯 Loaded {len(self.trading_pairs)} pairs from preset: {pair_preset}")
        
        # Все уникальные символы для загрузки данных
        self.all_symbols = set()
        for pair in self.trading_pairs:
            self.all_symbols.add(pair["asset_a"])
            self.all_symbols.add(pair["asset_b"])
        self.all_symbols = list(self.all_symbols)
        
        self.historical_data = {}
        self.timeframe = "1h"  # Упростили timeframe для быстрой загрузки
        self.lookback_bars = 100  # Уменьшили с 672 до 100
        self.data_loaded = False
        self.window_bars = 20  # Уменьшили окно для Z-score
        
        # ADF настройки (упрощенные)
        self.adf_lookbacks = [30, 20]  # Меньше баров для теста
        self.adf_critical_value = -1.5  # Более мягкий критерий
        
        # Храним состояние для каждой пары
        self.pair_states = {}
        for pair in self.trading_pairs:
            self.pair_states[pair["name"]] = {
                'current_signal': 'HOLD',
                'adf_passed': False,
                'position_open': False,
                'data_loaded': False
            }
        
        # 🆕 ДЛЯ ПЕРЕДАЧИ ДАННЫХ В TELEGRAM
        self.current_report_data = None
        
    def complete_data_reset(self):
        """ПОЛНЫЙ СБРОС всех данных и перезагрузка"""
        logger.info("🗑️ COMPLETE DATA RESET INITIATED...")
        logger.info(f"🎯 Loading data for {len(self.all_symbols)} symbols and {len(self.trading_pairs)} pairs")
        
        self.historical_data = {}
        self.data_loaded = False
        
        if self.fetch_historical_data():
            logger.info("✅ COMPLETE RESET SUCCESSFUL - Fresh data loaded")
            
            # Тестируем ADF для каждой пары
            successful_pairs = 0
            for pair in self.trading_pairs:
                spread_data = self.get_pair_historical_spread(pair)
                if spread_data is not None:
                    adf_passed = self.calculate_adf_test(spread_data)
                    self.pair_states[pair["name"]]['data_loaded'] = True
                    self.pair_states[pair["name"]]['adf_passed'] = adf_passed
                    if adf_passed:
                        successful_pairs += 1
                    logger.info(f"📊 {pair['name']}: ADF {'PASSED' if adf_passed else 'FAILED'}")
                else:
                    logger.warning(f"❌ {pair['name']}: No historical data")
            
            logger.info(f"🎯 Successfully initialized {successful_pairs}/{len(self.trading_pairs)} pairs")
            return True
        else:
            logger.error("❌ COMPLETE RESET FAILED")
            return False
        
    def fetch_historical_data(self):
        """Загрузка исторических данных для всех символов"""
        if self.data_loaded:
            logger.info("📊 Historical data already loaded, skipping...")
            return True
            
        logger.info(f"🔄 FETCHING DATA FOR {len(self.all_symbols)} SYMBOLS FROM OKX...")
        
        success_count = 0
        for symbol in self.all_symbols:
            try:
                logger.info(f"📥 Loading {symbol}...")
                ohlcv = self.exchange.fetch_ohlcv(symbol, self.timeframe, limit=self.lookback_bars)
                if ohlcv and len(ohlcv) >= 50:  # Уменьшили минимальное требование
                    self.historical_data[symbol] = [c[4] for c in ohlcv]
                    success_count += 1
                    logger.info(f"✅ {symbol}: {len(self.historical_data[symbol])} bars")
                else:
                    logger.warning(f"❌ No data for {symbol} - got {len(ohlcv) if ohlcv else 0} bars")
            except Exception as e:
                logger.warning(f"❌ Error loading {symbol}: {e}")
        
        # Требуем загрузки хотя бы 60% символов
        min_required = max(3, len(self.all_symbols) * 0.6)
        if success_count >= min_required:
            self.data_loaded = True
            logger.info(f"🎯 Successfully loaded {success_count}/{len(self.all_symbols)} symbols")
            return True
        else:
            logger.error(f"❌ Not enough valid symbols: {success_count}/{len(self.all_symbols)} (need at least {min_required})")
            return False

    def get_pair_historical_spread(self, pair):
        """Исторический спред для конкретной пары"""
        if pair["asset_a"] not in self.historical_data:
            return None
        if pair["asset_b"] not in self.historical_data:
            return None
            
        len_a = len(self.historical_data[pair["asset_a"]])
        len_b = len(self.historical_data[pair["asset_b"]])
        
        min_len = min(len_a, len_b)
        
        if min_len < max(self.adf_lookbacks):
            return None
            
        prices_a = np.array(self.historical_data[pair["asset_a"]][-min_len:])
        prices_b = np.array(self.historical_data[pair["asset_b"]][-min_len:])
        
        spread = prices_a / prices_b
        return spread

    def calculate_adf_test(self, spread_data):
        """ADF тест на стационарность"""
        if spread_data is None or len(spread_data) < max(self.adf_lookbacks):
            return False
        
        try:
            adf_passed = True
            
            for lookback in self.adf_lookbacks:
                if len(spread_data) < lookback:
                    adf_passed = False
                    break
                    
                test_data = spread_data[-lookback:]
                adf_result = adfuller(test_data, maxlag=1, regression='c', autolag=None)
                adf_statistic = adf_result[0]
                
                if adf_statistic > self.adf_critical_value:
                    adf_passed = False
                    break
            
            return adf_passed
            
        except Exception as e:
            logger.warning(f"❌ ADF test error: {e}")
            return False

    def calculate_pair_spread(self, pair, current_prices):
        """Текущий спред для пары: Asset_A / Asset_B"""
        if pair["asset_a"] not in current_prices or pair["asset_b"] not in current_prices:
            return None
            
        price_a = current_prices[pair["asset_a"]]
        price_b = current_prices[pair["asset_b"]]
        
        if price_a <= 0 or price_b <= 0:
            return None
            
        spread = price_a / price_b
        return spread

    def calculate_zscore_for_pair(self, pair, current_prices):
        """Z-score для конкретной пары на скользящем окне"""
        current_spread = self.calculate_pair_spread(pair, current_prices)
        if current_spread is None:
            return None, None, None
            
        historical_spread = self.get_pair_historical_spread(pair)
        if historical_spread is None or len(historical_spread) < self.window_bars:
            return None, None, None
        
        window_data = historical_spread[-self.window_bars:]
        
        mean = np.mean(window_data)
        std = np.std(window_data)
        
        if std < 1e-10:
            return None, None, None
            
        z = (current_spread - mean) / std
        
        # 🆕 ПРОВЕРКА НА NaN И INF
        if np.isnan(z) or np.isinf(z):
            return None, None, None
            
        return z, current_spread, (mean, std)

    def trading_signal_for_pair(self, z, is_stationary, pair_name):
        """Логика сигналов для пары с ADF проверкой"""
        if z is None:
            return "NO DATA"
            
        if not is_stationary:
            return "NO TRADE - NOT STATIONARY"
            
        # R-пороги
        if z > 1.0:
            return f"SHORT_{pair_name.split('_')[0]}_LONG_{pair_name.split('_')[1]}"
        if z < -1.0:
            return f"LONG_{pair_name.split('_')[0]}_SHORT_{pair_name.split('_')[1]}"
        if abs(z) < 0.5:
            return "EXIT_POSITION"
            
        return "HOLD"

    def get_current_prices(self):
        """Получение текущих цен для всех символов"""
        try:
            # Разбиваем на группы по 10 символов чтобы избежать лимитов
            all_prices = {}
            for i in range(0, len(self.all_symbols), 10):
                symbols_batch = self.all_symbols[i:i+10]
                try:
                    tickers = self.exchange.fetch_tickers(symbols_batch)
                    
                    for symbol in symbols_batch:
                        if symbol in tickers and tickers[symbol].get("last") is not None:
                            all_prices[symbol] = tickers[symbol]["last"]
                        else:
                            logger.warning(f"⚠️ Missing price for {symbol}")
                except Exception as e:
                    logger.warning(f"⚠️ Batch price error: {e}")
                    # Продолжаем с другими батчами
                
                time.sleep(0.2)  # Пауза между запросами
            
            # Проверяем что загрузились все необходимые цены
            required_symbols = set()
            for pair in self.trading_pairs:
                required_symbols.add(pair["asset_a"])
                required_symbols.add(pair["asset_b"])
            
            missing_prices = required_symbols - set(all_prices.keys())
            if missing_prices:
                logger.warning(f"⚠️ Missing prices for: {missing_prices}")
                return None
                    
            return all_prices
        except Exception as e:
            logger.warning(f"❌ Error fetching prices: {e}")
            return None

    def run(self, interval_minutes=1):
        """Основной цикл мониторинга для всех пар"""
        logger.info("🚀 Starting R-STYLE PAIR MONITOR...")
        logger.info(f"🎯 Monitoring {len(self.trading_pairs)} trading pairs")
        logger.info(f"🎯 {len(self.all_symbols)} unique symbols")
        logger.info(f"🎯 ADF Lookbacks: {self.adf_lookbacks} bars")
        logger.info(f"🎯 Z-score Window: {self.window_bars} bars")
        logger.info(f"🎯 R-STYLE THRESHOLDS: ENTER ±1.0, EXIT ±0.5")
        
        logger.info("🔥 PERFORMING COMPLETE DATA RESET BEFORE START...")
        if not self.complete_data_reset():
            logger.error("❌ CRITICAL: Complete data reset failed")
            return
            
        consecutive_bad_data = 0
        
        while True:
            try:
                prices = self.get_current_prices()
                if not prices:
                    consecutive_bad_data += 1
                    if consecutive_bad_data >= 3:
                        logger.error("🚨 Too many consecutive price errors, restarting...")
                        self.complete_data_reset()
                        consecutive_bad_data = 0
                    time.sleep(60)
                    continue
                
                consecutive_bad_data = 0
                current_time = datetime.utcnow().strftime('%H:%M:%S')
                
                # 🎯 ОБРАБАТЫВАЕМ КАЖДУЮ ПАРУ НЕЗАВИСИМО
                all_pair_data = []
                active_pairs_count = 0
                trading_signals_count = 0
                
                for pair in self.trading_pairs:
                    # Пропускаем пары без данных
                    if not self.pair_states[pair["name"]]['data_loaded']:
                        continue
                        
                    # Расчет Z-score и ADF для пары
                    z, spread, stats = self.calculate_zscore_for_pair(pair, prices)
                    historical_spread = self.get_pair_historical_spread(pair)
                    is_stationary = self.calculate_adf_test(historical_spread) if historical_spread is not None else False
                    
                    signal = self.trading_signal_for_pair(z, is_stationary, pair["name"])
                    
                    # Обновляем состояние пары
                    self.pair_states[pair["name"]]['adf_passed'] = is_stationary
                    self.pair_states[pair["name"]]['current_signal'] = signal
                    
                    if is_stationary:
                        active_pairs_count += 1
                    if signal not in ["HOLD", "NO DATA", "NO TRADE - NOT STATIONARY"]:
                        trading_signals_count += 1
                    
                    # Логирование только для пар с данными и сигналами
                    if z is not None and is_stationary:
                        adf_status = "STATIONARY"
                        status = "🚨 ABNORMAL" if abs(z) > 3.0 else "✅ NORMAL"
                        
                        if signal != "HOLD":
                            # 🆕 БЕЗОПАСНОЕ ФОРМАТИРОВАНИЕ
                            try:
                                logger.info(f"[{current_time}] {pair['name']}: Z={z:.2f} {status} | {signal}")
                            except (ValueError, TypeError) as format_error:
                                logger.warning(f"[{current_time}] {pair['name']}: Z=INVALID {status} | {signal}")
                    
                    # Собираем данные для уведомлений
                    pair_data = {
                        "pair_name": pair["name"],
                        "asset_a": pair["asset_a"],
                        "asset_b": pair["asset_b"], 
                        "price_a": prices.get(pair["asset_a"], 0),
                        "price_b": prices.get(pair["asset_b"], 0),
                        "spread": spread if spread else 0,
                        "z": z if z else 0,
                        "signal": signal,
                        "adf_passed": is_stationary
                    }
                    all_pair_data.append(pair_data)
                
                # Сводка по итерации
                logger.info(f"📊 [{current_time}] Active: {active_pairs_count}/{len(self.trading_pairs)} | Signals: {trading_signals_count}")
                
                # Уведомляем наблюдателей
                report_data = {
                    "time": datetime.utcnow(),
                    "pairs_data": all_pair_data,
                    "total_pairs": len(self.trading_pairs),
                    "active_pairs": active_pairs_count,
                    "trading_signals": trading_signals_count
                }
                
                # 🆕 СОХРАНЯЕМ ТЕКУЩИЕ ДАННЫЕ ДЛЯ TELEGRAM
                self.current_report_data = report_data
                
                self.notify(report_data)
                
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("🛑 Monitoring stopped by user")
                break
            except Exception as e:
                logger.warning(f"❌ Error in main loop: {e}")
                time.sleep(60)


def telegram_polling(trader, telegram_observer, monitor_instance):
    """
    Обновленная функция polling с передачей текущих данных монитора
    """
    TELEGRAM_BOT_TOKEN = "8436652130:AAF6On0GJtRHfMZyqD3mpM57eXZfWofJeng"
    offset = None
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"

    while True:
        try:
            params = {'timeout': 30, 'offset': offset}
            response = requests.get(url, params=params, timeout=35)
            updates = response.json().get("result", [])
            for update in updates:
                if "callback_query" in update:
                    data = update["callback_query"]["data"]
                    
                    # 🆕 ПЕРЕДАЕМ ТЕКУЩИЕ ДАННЫЕ МОНИТОРА
                    current_data = None
                    if monitor_instance and hasattr(monitor_instance, 'current_report_data'):
                        current_data = monitor_instance.current_report_data
                    
                    handle_callback(data, trader, telegram_observer, current_data)
                offset = update["update_id"] + 1
            time.sleep(1)
        except Exception as e:
            print("Telegram polling error:", e)
            time.sleep(5)


def main():
    # 🎯 ВОЗМОЖНОСТЬ ВЫБОРА ПРЕСЕТА ЧЕРЕЗ АРГУМЕНТЫ
    import argparse
    
    parser = argparse.ArgumentParser(description='R-Style Pair Trading Monitor')
    parser.add_argument('--preset', type=str, default='ultra_liquid_8', 
                       help='Pair preset: ultra_liquid_8, liquid_pairs_15, top_10_btc_pairs, auto_top_30')
    parser.add_argument('--test', action='store_true', help='Test pair configurations')
    
    args = parser.parse_args()
    
    if args.test:
        from pairs_config import get_all_presets
        print("🔍 TESTING ALL PAIR PRESETS...")
        results = get_all_presets()
        
        for preset_name, pairs in results.items():
            print(f"\n📊 {preset_name.upper()}:")
            print(f"   Valid pairs: {len(pairs)}")
            if len(pairs) > 0:
                print(f"   Sample: {pairs[0]['name']} - {pairs[0]['asset_a']} / {pairs[0]['asset_b']}")
        sys.exit(0)
    
    # Запуск монитора с выбранным пресетом
    monitor = RStylePairMonitor(pair_preset=args.preset)
    monitor.attach(ConsoleObserver())

    # 🆕 ОБНОВЛЕННЫЙ TRADER С НАЧАЛЬНЫМ БАЛАНСОМ
    trader = OKXBasketTrader(paper_trading=True, max_exposure=1000, initial_balance=10000)
    monitor.attach(trader)

    telegram_observer = TelegramObserver(trader=trader)
    monitor.attach(telegram_observer)

    # 🆕 ОБНОВЛЕННЫЙ ВЫЗОВ С ПЕРЕДАЧЕЙ МОНИТОРА
    polling_thread = threading.Thread(
        target=telegram_polling, 
        args=(trader, telegram_observer, monitor),  # 🆕 ПЕРЕДАЕМ МОНИТОР
        daemon=True
    )
    polling_thread.start()

    monitor.run(interval_minutes=1)


if __name__ == "__main__":
    main()