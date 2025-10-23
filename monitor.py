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

class OKXBasketMonitor(Subject):
    def __init__(self):
        super().__init__()
        self.exchange = ccxt.okx({
            "enableRateLimit": True,
            "options": {"defaultType": "swap"},
            "sandbox": False
        })
        self.target = "BTC/USDT:USDT"
        # РАСШИРЕННАЯ КОРЗИНА с большей волатильностью
        self.basket_symbols = [
            "DOGE/USDT:USDT",
            "XRP/USDT:USDT", 
            "MATIC/USDT:USDT",
            "AVAX/USDT:USDT",
            # ДОБАВЛЕНЫ НОВЫЕ АКТИВЫ ДЛЯ ВОЛАТИЛЬНОСТИ
            "SOL/USDT:USDT",
            "DOT/USDT:USDT", 
            "ADA/USDT:USDT",
            "LINK/USDT:USDT"
        ]
        self.basket_weights = []
        self.historical_data = {}
        self.timeframe = "15m"
        self.lookback_bars = 672
        self.normalization_factors = {}
        self.last_data_update = None
        self.data_update_interval = timedelta(hours=1)
        self.consecutive_hold_signals = 0  # Счетчик подряд идущих HOLD сигналов

    def fetch_historical_data(self):
        logger.info("Fetching 15-MINUTE historical data from OKX...")
        successful_symbols = []
        
        for symbol in [self.target] + self.basket_symbols:
            try:
                ohlcv = self.exchange.fetch_ohlcv(symbol, self.timeframe, limit=self.lookback_bars)
                if not ohlcv:
                    logger.warning(f"No data for {symbol}")
                    continue
                self.historical_data[symbol] = [c[4] for c in ohlcv]
                successful_symbols.append(symbol)
                logger.info(f"Loaded {len(self.historical_data[symbol])} 15min bars for {symbol}")
            except Exception as e:
                logger.warning(f"Error loading {symbol}: {e}")

        min_bars_required = 96
        valid = [s for s in [self.target] + self.basket_symbols 
                if s in self.historical_data and len(self.historical_data[s]) >= min_bars_required]
        
        # СОРТИРУЕМ ПО КОРРЕЛЯЦИИ И БЕРЕМ ТОП-6
        if len(valid) >= 4:
            correlations = []
            for symbol in valid:
                if symbol != self.target:
                    x = np.array(self.historical_data[self.target])
                    y = np.array(self.historical_data[symbol])
                    if len(x) == len(y):
                        corr = np.corrcoef(x, y)[0, 1]
                        correlations.append((symbol, abs(corr) if not np.isnan(corr) else 0))
            
            # Берем топ-6 по корреляции
            correlations.sort(key=lambda x: x[1], reverse=True)
            top_symbols = [self.target] + [s[0] for s in correlations[:6]]
            self.basket_symbols = [s for s in self.basket_symbols if s in top_symbols and s != self.target]
            logger.info(f"Selected top {len(self.basket_symbols)} symbols by correlation")
        
        if len(valid) < 4:
            logger.error("Not enough valid symbols for analysis.")
            return False
        
        self.last_data_update = datetime.utcnow()
        return True

    def should_update_historical_data(self):
        if self.last_data_update is None:
            return True
        return datetime.utcnow() - self.last_data_update > self.data_update_interval

    def calculate_basket_weights(self):
        correlations = []
        valid_symbols = []

        print("="*50, flush=True)
        print("CALCULATING WEIGHTS BASED ON CORRELATION", flush=True)
        print("="*50, flush=True)

        for symbol in self.basket_symbols:
            if symbol in self.historical_data and self.target in self.historical_data:
                x = np.array(self.historical_data[self.target])
                y = np.array(self.historical_data[symbol])
                if len(x) == len(y):
                    corr = np.corrcoef(x, y)[0, 1]
                    if not np.isnan(corr):
                        # УВЕЛИЧИВАЕМ ВЕС МЕНЕЕ КОРРЕЛИРОВАННЫХ АКТИВОВ
                        adjusted_corr = 1.0 - abs(corr)  # Инвертируем для большей волатильности
                        correlations.append(adjusted_corr)
                        valid_symbols.append(symbol)
                        asset_name = symbol.split('/')[0]
                        quality = (
                            "EXCELLENT" if corr > 0.8 else
                            "GOOD" if corr > 0.6 else
                            "AVERAGE" if corr > 0.4 else
                            "WEAK" if corr > 0.2 else
                            "NO CORR"
                        )
                        direction = "positive" if corr > 0 else "negative"
                        print(f"{asset_name:8} | Correlation: {corr:6.3f} | {quality:8} | {direction}", flush=True)

        self.basket_symbols = valid_symbols
        if not correlations:
            logger.error("No valid symbols for basket weights.")
            return

        self.basket_weights = np.array(correlations) / np.sum(correlations)

        self.calculate_normalization_factors()

        print("="*50, flush=True)
        print("FINAL BASKET WITH WEIGHTS (VOLATILITY-OPTIMIZED)", flush=True)
        print("="*50, flush=True)
        for i, s in enumerate(self.basket_symbols):
            asset_name = s.split('/')[0]
            original_corr = np.corrcoef(
                np.array(self.historical_data[self.target]),
                np.array(self.historical_data[s])
            )[0, 1]
            print(f"{asset_name:8} | Weight: {self.basket_weights[i]:6.3f} | Correlation: {original_corr:6.3f}", flush=True)
        print("="*50, flush=True)

    def calculate_normalization_factors(self):
        """Рассчитываем факторы нормализации"""
        self.normalization_factors[self.target] = np.mean(self.historical_data[self.target])
        
        basket_prices = np.zeros(len(self.historical_data[self.target]))
        for i, s in enumerate(self.basket_symbols):
            basket_prices += self.basket_weights[i] * np.array(self.historical_data[s])
        
        self.normalization_factors['basket'] = np.mean(basket_prices)
        
        print(f"NORMALIZATION: BTC_mean={self.normalization_factors[self.target]:.2f}, basket_mean={self.normalization_factors['basket']:.4f}", flush=True)

    def get_current_prices(self):
        try:
            symbols = [self.target] + self.basket_symbols
            tickers = self.exchange.fetch_tickers(symbols)
            prices = {s: tickers[s]["last"] for s in symbols if s in tickers and tickers[s].get("last") is not None}
            if len(prices) != len(symbols):
                logger.warning("Some prices are missing.")
                return None
            return prices
        except Exception as e:
            logger.warning(f"Error fetching tickers: {e}")
            return None

    def calculate_basket_price(self, prices):
        return sum(self.basket_weights[i] * prices[s] for i, s in enumerate(self.basket_symbols) if s in prices)

    def calculate_spread_series(self):
        min_len = min(len(self.historical_data[s]) for s in [self.target] + self.basket_symbols if s in self.historical_data)
        if min_len < 96:
            return None
            
        target_prices = np.array(self.historical_data[self.target][-min_len:])
        basket_prices = np.zeros(min_len)
        for i, s in enumerate(self.basket_symbols):
            basket_prices += self.basket_weights[i] * np.array(self.historical_data[s][-min_len:])
        
        normalized_target = target_prices / self.normalization_factors[self.target]
        normalized_basket = basket_prices / self.normalization_factors['basket']
        
        return normalized_target / normalized_basket

    def calculate_zscore(self, current_prices):
        if not current_prices or not all(s in current_prices for s in [self.target] + self.basket_symbols):
            return None, None, None
            
        basket_price_now = self.calculate_basket_price(current_prices)
        if basket_price_now <= 0:
            return None, None, None
            
        normalized_target_now = current_prices[self.target] / self.normalization_factors[self.target]
        normalized_basket_now = basket_price_now / self.normalization_factors['basket']
        
        spread_now = normalized_target_now / normalized_basket_now
        spread_hist = self.calculate_spread_series()
        
        if spread_hist is None:
            return None, None, None
            
        mean, std = np.mean(spread_hist), np.std(spread_hist)
        if std < 1e-10:
            return None, None, None
            
        z = (spread_now - mean) / std
        
        print(f"DEBUG: BTC={current_prices[self.target]:.2f} (norm={normalized_target_now:.3f})", flush=True)
        print(f"DEBUG: basket={basket_price_now:.4f} (norm={normalized_basket_now:.3f})", flush=True)
        print(f"DEBUG: spread_now={spread_now:.3f}, mean={mean:.3f}, std={std:.3f}, z={z:.2f}", flush=True)
        
        return z, spread_now, (mean, std)

    def trading_signal(self, z):
        """ОПТИМИЗИРОВАННЫЕ ПОРОГИ ДЛЯ БОЛЬШЕЙ ЧУВСТВИТЕЛЬНОСТИ"""
        if z is None: 
            return "NO DATA"
        
        # ПОНИЖЕННЫЕ ПОРОГИ ДЛЯ БОЛЕЕ ЧАСТЫХ СИГНАЛОВ
        if z > 1.5:    # было 2.0
            self.consecutive_hold_signals = 0
            return "SHORT BTC / LONG BASKET"
        if z < -1.5:   # было -2.0
            self.consecutive_hold_signals = 0  
            return "LONG BTC / SHORT BASKET"
        if abs(z) < 0.3:  # было 0.5 - раньше выходим из позиций
            self.consecutive_hold_signals = 0
            return "EXIT POSITION"
        
        self.consecutive_hold_signals += 1
        
        # ЕСЛИ ДОЛГО НЕТ СИГНАЛОВ - УВЕДОМЛЯЕМ
        if self.consecutive_hold_signals >= 10:
            logger.info("LOW VOLATILITY - Consider expanding basket further")
            self.consecutive_hold_signals = 0
            
        return "HOLD"

    def run(self, interval_minutes=1):
        logger.info("Starting OKX basket monitor with OPTIMIZED parameters...")
        sys.stdout.flush()

        if not self.fetch_historical_data():
            logger.error("Failed to fetch historical data.")
            return

        self.calculate_basket_weights()
        if not self.basket_symbols:
            logger.error("No valid symbols for monitoring.")
            return

        logger.info(f"Monitoring {len(self.basket_symbols)} symbols: {[s.split('/')[0] for s in self.basket_symbols]}")
        last_telegram_time = datetime.utcnow() - timedelta(minutes=10)

        while True:
            try:
                if self.should_update_historical_data():
                    logger.info("Updating historical data...")
                    if self.fetch_historical_data():
                        self.calculate_basket_weights()
                
                prices = self.get_current_prices()
                if not prices:
                    time.sleep(60)
                    continue

                z, spread, stats = self.calculate_zscore(prices)
                signal = self.trading_signal(z)
                current_time = datetime.utcnow().strftime('%H:%M:%S')
                
                if z is not None:
                    print(f"[{current_time}] Z-score: {z:6.2f} | Signal: {signal} | Spread: {spread:.3f}", flush=True)
                else:
                    print(f"[{current_time}] Z-score: NO DATA | Signal: {signal}", flush=True)

                # БОЛЕЕ ЧАСТЫЕ УВЕДОМЛЕНИЯ ПРИ ИЗМЕНЕНИИ СИГНАЛА
                if datetime.utcnow() - last_telegram_time >= timedelta(minutes=10) or "EXIT" in signal or "LONG" in signal or "SHORT" in signal:
                    report_data = {
                        "time": datetime.utcnow(),
                        "target_price": prices[self.target],
                        "basket_price": self.calculate_basket_price(prices),
                        "spread": spread if spread else 0,
                        "mean": stats[0] if stats else 0,
                        "std": stats[1] if stats else 0,
                        "z": z if z else 0,
                        "signal": signal,
                        "basket_symbols": self.basket_symbols,
                        "basket_weights": self.basket_weights,
                        "timeframe": "15m",
                        "consecutive_hold": self.consecutive_hold_signals
                    }
                    self.notify(report_data)
                    last_telegram_time = datetime.utcnow()

                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user.")
                break
            except Exception as e:
                logger.warning(f"Error in loop: {e}")
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
    monitor = OKXBasketMonitor()
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