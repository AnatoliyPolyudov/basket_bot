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
        self.basket_symbols = [
            "DOGE/USDT:USDT",
            "ADA/USDT:USDT",
            "XRP/USDT:USDT",
            "PEPE/USDT:USDT"
        ]
        self.basket_weights = []
        self.historical_data = {}
        self.lookback_days = 60

    def fetch_historical_data(self):
        logger.info("Fetching historical data from OKX...")
        for symbol in [self.target] + self.basket_symbols:
            try:
                since = self.exchange.parse8601(
                    (datetime.utcnow() - pd.Timedelta(days=self.lookback_days)).isoformat()
                )
                ohlcv = self.exchange.fetch_ohlcv(symbol, "1d", since=since, limit=self.lookback_days)
                if not ohlcv:
                    logger.warning(f"No data for {symbol}")
                    continue
                self.historical_data[symbol] = [c[4] for c in ohlcv]
                logger.info(f"Loaded {len(self.historical_data[symbol])} days for {symbol}")
            except Exception as e:
                logger.warning(f"Error loading {symbol}: {e}")

        valid = [s for s in [self.target] + self.basket_symbols if s in self.historical_data and len(self.historical_data[s]) >= 20]
        if len(valid) < 3:
            logger.error("Not enough valid symbols for analysis.")
            return False
        return True

    def calculate_basket_weights(self):
        volatilities = {}
        valid_symbols = []

        print("="*50, flush=True)
        print("CORRELATION & VOLATILITY ANALYSIS", flush=True)
        print("="*50, flush=True)

        for symbol in self.basket_symbols:
            if symbol in self.historical_data and self.target in self.historical_data:
                x = np.array(self.historical_data[self.target])
                y = np.array(self.historical_data[symbol])
                if len(x) != len(y):
                    continue
                    
                corr = np.corrcoef(x, y)[0, 1]
                if np.isnan(corr):
                    continue
                    
                valid_symbols.append(symbol)

                returns = np.diff(np.log(y))
                sigma = max(np.std(returns), 1e-4)
                volatilities[symbol] = sigma

                asset_name = symbol.split('/')[0]
                corr_percent = abs(corr) * 100
                quality = (
                    "EXCELLENT" if corr > 0.8 else
                    "GOOD" if corr > 0.6 else
                    "AVERAGE" if corr > 0.4 else
                    "WEAK" if corr > 0.2 else
                    "NO CORR"
                )
                direction = "positive" if corr > 0 else "negative"
                print(f"{asset_name:8} | Corr: {corr:6.3f} | {corr_percent:5.1f}% | {quality:8} | {direction} | vol={sigma:.4f}", flush=True)

        self.basket_symbols = valid_symbols
        if not self.basket_symbols:
            logger.error("No valid symbols for basket weights.")
            return

        inv_vars = np.array([1 / (volatilities[s]**2) for s in self.basket_symbols])
        self.basket_weights = inv_vars / np.sum(inv_vars)

        print("="*50, flush=True)
        print("FINAL BASKET WITH WEIGHTS (1/vol method)", flush=True)
        print("="*50, flush=True)
        for s, w in zip(self.basket_symbols, self.basket_weights):
            asset_name = s.split('/')[0]
            print(f"{asset_name:8} | Weight: {w:6.3f} | vol={volatilities[s]:.4f}", flush=True)
        print("="*50, flush=True)

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
        if min_len < 20:
            return None
            
        target_prices = np.array(self.historical_data[self.target][-min_len:])
        basket_prices = np.zeros(min_len)
        for i, s in enumerate(self.basket_symbols):
            basket_prices += self.basket_weights[i] * np.array(self.historical_data[s][-min_len:])
        return np.log(target_prices / basket_prices)

    def calculate_zscore(self, current_prices):
        if not current_prices or not all(s in current_prices for s in [self.target] + self.basket_symbols):
            return None, None, None
            
        basket_price_now = self.calculate_basket_price(current_prices)
        if basket_price_now <= 0:
            return None, None, None
            
        spread_now = np.log(current_prices[self.target] / basket_price_now)
        spread_hist = self.calculate_spread_series()
        
        if spread_hist is None:
            return None, None, None
            
        mean, std = np.mean(spread_hist), np.std(spread_hist)
        if std < 1e-10:
            return None, None, None
            
        z = (spread_now - mean) / std
        return z, spread_now, (mean, std)

    def trading_signal(self, z):
        if z is None: return "NO DATA"
        if z > 2.0: return "SHORT BTC / LONG BASKET"
        if z < -2.0: return "LONG BTC / SHORT BASKET"
        if abs(z) < 0.5: return "EXIT POSITION"
        return "HOLD"

    def run(self, interval_minutes=1):
        logger.info("Starting OKX basket monitor...")
        sys.stdout.flush()

        if not self.fetch_historical_data():
            logger.error("Failed to fetch historical data.")
            return

        self.calculate_basket_weights()
        if not self.basket_symbols:
            logger.error("No valid symbols for monitoring.")
            return

        logger.info(f"Monitoring symbols: {self.basket_symbols}")
        last_telegram_time = datetime.utcnow() - timedelta(minutes=10)

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
                    print(f"[{current_time}] Z-score: {z:6.2f} | Signal: {signal} | Spread: {spread:.5f}", flush=True)
                else:
                    print(f"[{current_time}] Z-score: NO DATA | Signal: {signal}", flush=True)

                if datetime.utcnow() - last_telegram_time >= timedelta(minutes=10):
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
                        "basket_weights": self.basket_weights
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