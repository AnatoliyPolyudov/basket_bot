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

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

class SimpleBasketMonitor(Subject):
    def __init__(self):
        super().__init__()
        self.exchange = ccxt.okx({
            "enableRateLimit": True,
            "options": {"defaultType": "swap"},
            "sandbox": False
        })
        self.target = "BTC/USDT:USDT"
        
        self.basket_symbols = [
            "ETH/USDT:USDT",      # ~$3,000 - дорогой актив
            "BNB/USDT:USDT",      # ~$600
            "SOL/USDT:USDT",      # ~$150  
            "XRP/USDT:USDT",      # ~$0.50
            "ADA/USDT:USDT",      # ~$0.40
            "AVAX/USDT:USDT",     # ~$30
            "DOT/USDT:USDT",      # ~$6
            "LINK/USDT:USDT",     # ~$15
            "TRX/USDT:USDT"     # ~$0.70
        ]
        
        self.historical_data = {}
        self.timeframe = "15m"
        self.lookback_bars = 672
        self.data_loaded = False
        
    def complete_data_reset(self):
        """ПОЛНЫЙ СБРОС всех данных и перезагрузка"""
        logger.info("🗑️ COMPLETE DATA RESET INITIATED...")
        
        self.historical_data = {}
        self.data_loaded = False
        
        if self.fetch_historical_data():
            logger.info("✅ COMPLETE RESET SUCCESSFUL - Fresh data loaded")
            
            spread_stats = self.calculate_spread_stats()
            if spread_stats:
                mean, std = spread_stats
                logger.info(f"📊 NEW SPREAD STATS: mean={mean:.3f}, std={std:.3f}")
            return True
        else:
            logger.error("❌ COMPLETE RESET FAILED")
            return False
        
    def fetch_historical_data(self):
        """Загрузка исторических данных"""
        if self.data_loaded:
            logger.info("📊 Historical data already loaded, skipping...")
            return True
            
        logger.info("🔄 FETCHING FRESH HISTORICAL DATA FROM OKX...")
        
        success_count = 0
        for symbol in [self.target] + self.basket_symbols:
            try:
                ohlcv = self.exchange.fetch_ohlcv(symbol, self.timeframe, limit=self.lookback_bars)
                if ohlcv and len(ohlcv) >= 100:
                    self.historical_data[symbol] = [c[4] for c in ohlcv]
                    success_count += 1
                    logger.info(f"✅ Loaded {len(self.historical_data[symbol])} bars for {symbol}")
                else:
                    logger.warning(f"❌ No data for {symbol}")
            except Exception as e:
                logger.warning(f"❌ Error loading {symbol}: {e}")
        
        valid_symbols = [s for s in [self.target] + self.basket_symbols 
                        if s in self.historical_data and len(self.historical_data[s]) >= 100]
        
        if len(valid_symbols) >= 4:
            self.data_loaded = True
            logger.info(f"🎯 Successfully loaded {success_count} symbols")
            return True
        else:
            logger.error(f"❌ Not enough valid symbols: {len(valid_symbols)}/4")
            return False

    def calculate_spread_stats(self):
        """Расчет статистики исторического спреда"""
        historical_spread = self.calculate_spread()
        if historical_spread is not None and len(historical_spread) >= 100:
            return np.mean(historical_spread), np.std(historical_spread)
        return None

    def calculate_spread(self, current_prices=None):
        """
        ПРАВИЛЬНЫЙ метод по R коду: отношение обычных цен
        """
        if current_prices:
            btc_price = current_prices[self.target]
            alt_prices = [current_prices[s] for s in self.basket_symbols if s in current_prices]
            
            if not alt_prices or btc_price <= 0:
                return None
                
            avg_alt_price = np.mean(alt_prices)
            if avg_alt_price <= 0:
                return None
                
            spread = btc_price / avg_alt_price
            return spread
            
        else:
            min_len = min(len(self.historical_data[s]) for s in [self.target] + self.basket_symbols 
                         if s in self.historical_data)
            
            if min_len < 100:
                return None
                
            btc_prices = np.array(self.historical_data[self.target][-min_len:])
            alt_prices_matrix = []
            
            for symbol in self.basket_symbols:
                if symbol in self.historical_data and len(self.historical_data[symbol]) >= min_len:
                    alt_prices_matrix.append(self.historical_data[symbol][-min_len:])
            
            if not alt_prices_matrix:
                return None
                
            alt_prices_matrix = np.array(alt_prices_matrix)
            avg_alt_prices = np.mean(alt_prices_matrix, axis=0)
            
            spread = btc_prices / avg_alt_prices
            return spread

    def calculate_zscore(self, current_prices):
        """Z-score как в R коде"""
        current_spread = self.calculate_spread(current_prices)
        if current_spread is None:
            return None, None, None
            
        historical_spread = self.calculate_spread()
        if historical_spread is None or len(historical_spread) < 100:
            return None, None, None
            
        mean = np.mean(historical_spread)
        std = np.std(historical_spread)
        
        if std < 1e-10:
            return None, None, None
            
        z = (current_spread - mean) / std
        
        logger.info(f"📊 R-STYLE CALC: spread={current_spread:.3f}, mean={mean:.3f}, std={std:.3f}, z={z:.2f}")
        return z, current_spread, (mean, std)

    def get_current_prices(self):
        """Получение текущих цен"""
        try:
            symbols = [self.target] + self.basket_symbols
            tickers = self.exchange.fetch_tickers(symbols)
            prices = {}
            
            for symbol in symbols:
                if symbol in tickers and tickers[symbol].get("last") is not None:
                    prices[symbol] = tickers[symbol]["last"]
                else:
                    logger.warning(f"⚠️ Missing price for {symbol}")
                    return None
                    
            return prices
        except Exception as e:
            logger.warning(f"❌ Error fetching prices: {e}")
            return None

    def trading_signal(self, z):
        """Логика сигналов с агрессивными параметрами"""
        if z is None:
            return "NO DATA"
            
        if z > 0.6:
            return "SHORT BTC / LONG BASKET"
        if z < -0.6:
            return "LONG BTC / SHORT BASKET"
        if abs(z) < 0.08:
            return "EXIT POSITION"
            
        return "HOLD"

    def run(self, interval_minutes=1):
        """Основной цикл с автокоррекцией"""
        logger.info("🚀 Starting ULTIMATE R-CODE BASED MONITOR...")
        
        logger.info("🔥 PERFORMING COMPLETE DATA RESET BEFORE START...")
        if not self.complete_data_reset():
            logger.error("❌ CRITICAL: Complete data reset failed")
            return
            
        logger.info(f"🎯 Monitoring {len(self.basket_symbols)} symbols with FRESH data")
        
        consecutive_bad_z = 0
        
        while True:
            try:
                prices = self.get_current_prices()
                if not prices:
                    time.sleep(60)
                    continue
                    
                z, spread, stats = self.calculate_zscore(prices)
                signal = self.trading_signal(z)
                
                current_time = datetime.utcnow().strftime('%H:%M:%S')
                
                if z is not None and abs(z) > 3.0:
                    consecutive_bad_z += 1
                    logger.warning(f"🚨 ABNORMAL Z-score: {z:.2f} (consecutive: {consecutive_bad_z})")
                    
                    if consecutive_bad_z >= 2:
                        logger.info("🔄 AUTO-CORRECTING: Reloading historical data...")
                        if self.complete_data_reset():
                            consecutive_bad_z = 0
                            continue
                else:
                    consecutive_bad_z = 0
                
                if z is not None:
                    status = "🚨 ABNORMAL" if abs(z) > 3.0 else "✅ NORMAL"
                    logger.info(f"[{current_time}] Z: {z:6.2f} {status} | Signal: {signal} | Spread: {spread:.3f}")
                else:
                    logger.info(f"[{current_time}] Z: NO DATA | Signal: {signal}")
                
                report_data = {
                    "time": datetime.utcnow(),
                    "target_price": prices[self.target],
                    "basket_price": np.mean([prices[s] for s in self.basket_symbols]),
                    "spread": spread if spread else 0,
                    "z": z if z else 0,
                    "signal": signal,
                    "basket_symbols": self.basket_symbols
                }
                self.notify(report_data)
                
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("🛑 Monitoring stopped by user")
                break
            except Exception as e:
                logger.warning(f"❌ Error in main loop: {e}")
                time.sleep(60)


def telegram_polling(trader):
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
                    handle_callback(data, trader)
                offset = update["update_id"] + 1
            time.sleep(1)
        except Exception as e:
            print("Telegram polling error:", e)
            time.sleep(5)


def main():
    monitor = SimpleBasketMonitor()
    monitor.attach(ConsoleObserver())

    trader = OKXBasketTrader(paper_trading=True, max_exposure=1000)
    monitor.attach(trader)

    telegram_observer = TelegramObserver(trader=trader)
    monitor.attach(telegram_observer)

    polling_thread = threading.Thread(target=telegram_polling, args=(trader,), daemon=True)
    polling_thread.start()

    monitor.run(interval_minutes=1)


if __name__ == "__main__":
    main()
