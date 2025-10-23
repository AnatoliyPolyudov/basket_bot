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
        
        # ПРОСТАЯ КОРЗИНА - как в R коде
        self.basket_symbols = [
            "DOGE/USDT:USDT", "XRP/USDT:USDT", "AVAX/USDT:USDT",
            "SOL/USDT:USDT", "DOT/USDT:USDT", "ADA/USDT:USDT",
            "LINK/USDT:USDT", "BNB/USDT:USDT", "TRX/USDT:USDT"
        ]
        
        self.historical_data = {}
        self.timeframe = "15m"
        self.lookback_bars = 672  # 7 дней в 15-минутках
        
    def fetch_historical_data(self):
        """ПРОСТАЯ загрузка данных"""
        logger.info("Fetching historical data...")
        
        for symbol in [self.target] + self.basket_symbols:
            try:
                ohlcv = self.exchange.fetch_ohlcv(symbol, self.timeframe, limit=self.lookback_bars)
                if ohlcv:
                    self.historical_data[symbol] = [c[4] for c in ohlcv]  # только цены закрытия
                    logger.info(f"✅ Loaded {len(self.historical_data[symbol])} bars for {symbol}")
                else:
                    logger.warning(f"❌ No data for {symbol}")
            except Exception as e:
                logger.warning(f"❌ Error loading {symbol}: {e}")
        
        # Проверяем что достаточно данных
        valid_symbols = [s for s in [self.target] + self.basket_symbols 
                        if s in self.historical_data and len(self.historical_data[s]) >= 100]
        
        if len(valid_symbols) < 4:
            logger.error("❌ Not enough valid symbols")
            return False
            
        return True

    def calculate_spread(self, current_prices=None):
    """
    ИСПРАВЛЕННЫЙ метод - логарифмический спред
    """
    if current_prices:
        # ТЕКУЩИЙ СПРЕД
        btc_price = current_prices[self.target]
        alt_prices = [current_prices[s] for s in self.basket_symbols if s in current_prices]
        
        if not alt_prices or btc_price <= 0:
            return None
            
        avg_alt_price = np.mean(alt_prices)
        if avg_alt_price <= 0:
            return None
            
        # ЛОГАРИФМИЧЕСКИЙ СПРЕД - РЕШЕНИЕ ПРОБЛЕМЫ!
        spread = np.log(btc_price) - np.log(avg_alt_price)
        logger.info(f"📊 LOG SPREAD: log(BTC)={np.log(btc_price):.3f}, log(Alts)={np.log(avg_alt_price):.3f}, spread={spread:.3f}")
        return spread
        
    else:
        # ИСТОРИЧЕСКИЙ СПРЕД
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
        
        # Защита от нулевых/отрицательных цен
        btc_prices = np.maximum(btc_prices, 0.01)
        avg_alt_prices = np.maximum(avg_alt_prices, 0.01)
        
        spread = np.log(btc_prices) - np.log(avg_alt_prices)
        return spread

    def calculate_zscore(self, current_prices):
        """
        ПРОСТОЙ Z-score как в R коде
        """
        # 1. Текущий спред
        current_spread = self.calculate_spread(current_prices)
        if current_spread is None:
            return None, None, None
            
        # 2. Исторический спред
        historical_spread = self.calculate_spread()
        if historical_spread is None or len(historical_spread) < 100:
            return None, None, None
            
        # 3. Z-score
        mean = np.mean(historical_spread)
        std = np.std(historical_spread)
        
        if std < 1e-10:
            return None, None, None
            
        z = (current_spread - mean) / std
        
        logger.info(f"📊 SIMPLE CALC: spread={current_spread:.3f}, mean={mean:.3f}, std={std:.3f}, z={z:.2f}")
        return z, current_spread, (mean, std)

    def get_current_prices(self):
        """Простое получение текущих цен"""
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
        """
        ПРОСТАЯ логика сигналов с вашими агрессивными параметрами
        """
        if z is None:
            return "NO DATA"
            
        # ВАШИ АГРЕССИВНЫЕ ПОРОГИ - НЕ МЕНЯЕМ!
        if z > 0.6:
            return "SHORT BTC / LONG BASKET"
        if z < -0.6:
            return "LONG BTC / SHORT BASKET"
        if abs(z) < 0.08:
            return "EXIT POSITION"
            
        return "HOLD"

    def run(self, interval_minutes=1):
        """Простой основной цикл"""
        logger.info("🚀 Starting SIMPLE basket monitor...")
        
        if not self.fetch_historical_data():
            logger.error("❌ Failed to load historical data")
            return
            
        logger.info(f"🎯 Monitoring {len(self.basket_symbols)} symbols")
        
        while True:
            try:
                prices = self.get_current_prices()
                if not prices:
                    time.sleep(60)
                    continue
                    
                z, spread, stats = self.calculate_zscore(prices)
                signal = self.trading_signal(z)
                
                current_time = datetime.utcnow().strftime('%H:%M:%S')
                
                if z is not None:
                    logger.info(f"[{current_time}] Z: {z:6.2f} | Signal: {signal} | Spread: {spread:.3f}")
                else:
                    logger.info(f"[{current_time}] Z: NO DATA | Signal: {signal}")
                
                # Отправляем данные наблюдателям
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
    """Telegram polling (оставляем как есть)"""
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
    """Простой запуск"""
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
