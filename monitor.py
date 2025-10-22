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

# Create separate logger for pretty output
console_logger = logging.StreamHandler()
console_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
console_logger.setFormatter(formatter)

pretty_logger = logging.getLogger('pretty')
pretty_logger.setLevel(logging.INFO)
pretty_logger.addHandler(console_logger)
pretty_logger.propagate = False

class OKXBasketMonitor(Subject):
    def __init__(self):
        super().__init__()
        self.exchange = ccxt.okx({
            "enableRateLimit": True,
            "options": {"defaultType": "swap"},
            "sandbox": False
        })
        self.target = "ETH/USDT:USDT"
        # Meme basket instead of regular alts
        self.basket_symbols = ["DOGE/USDT:USDT", "SHIB/USDT:USDT", "PEPE/USDT:USDT"]
        self.basket_weights = []
        self.historical_data = {}
        self.lookback_days = 30

    def fetch_historical_data(self):
        logger.info("📊 Fetching historical data from OKX...")
        for symbol in [self.target] + self.basket_symbols:
            try:
                since = self.exchange.parse8601(
                    (datetime.utcnow() - pd.Timedelta(days=self.lookback_days)).isoformat()
                )
                ohlcv = self.exchange.fetch_ohlcv(symbol, "1d", since=since, limit=30)
                if not ohlcv:
                    logger.warning(f"⚠️ No data for {symbol}")
                    continue
                self.historical_data[symbol] = [c[4] for c in ohlcv]
                logger.info(f"✅ Loaded {len(self.historical_data[symbol])} days for {symbol}")
            except Exception as e:
                logger.warning(f"❌ Error loading {symbol}: {e}")

        # ADDED: check what loaded
        print(f"📦 Loaded data: {list(self.historical_data.keys())}", flush=True)
        
        valid = [s for s in [self.target]+self.basket_symbols if s in self.historical_data and len(self.historical_data[s])>=10]
        if len(valid) < 3:
            logger.error("❌ Not enough valid symbols for analysis.")
            return False
        return True

    def calculate_basket_weights(self):
        correlations, valid = [], []
        
        # FIXED: use regular print with flush instead of pretty_logger
        print("🔍 " + "="*50, flush=True)
        print("🔍 CORRELATION ANALYSIS WITH ETH", flush=True)
        print("🔍 " + "="*50, flush=True)
        
        for symbol in self.basket_symbols:
            if symbol in self.historical_data and self.target in self.historical_data:
                x, y = self.historical_data[self.target], self.historical_data[symbol]
                if len(x) == len(y):
                    corr = np.corrcoef(x, y)[0, 1]
                    if not np.isnan(corr):
                        correlations.append(corr)
                        valid.append(symbol)
                        
                        # BEAUTIFUL CORRELATION OUTPUT
                        asset_name = symbol.split('/')[0]
                        corr_percent = abs(corr) * 100
                        
                        if corr > 0.8:
                            emoji, quality = "🟢", "EXCELLENT"
                        elif corr > 0.6:
                            emoji, quality = "🟡", "GOOD" 
                        elif corr > 0.4:
                            emoji, quality = "🟠", "AVERAGE"
                        elif corr > 0.2:
                            emoji, quality = "🔴", "WEAK"
                        else:
                            emoji, quality = "💤", "NO CORR"
                        
                        direction = "positive" if corr > 0 else "negative"
                        print(f"{emoji} {asset_name:6} | {corr:7.3f} | {corr_percent:5.1f}% | {quality:10} | {direction}", flush=True)
        
        print("🔍 " + "="*50, flush=True)
        
        self.basket_symbols = valid
        if not correlations:
            if not self.basket_symbols:
                logger.error("❌ No valid symbols for basket weights.")
                return
            self.basket_weights = np.ones(len(self.basket_symbols)) / len(self.basket_symbols)
            return
        
        abs_corr = np.abs(correlations)
        self.basket_weights = abs_corr / np.sum(abs_corr)
        
        print("🎯 " + "="*50, flush=True)
        print("🎯 FINAL BASKET WITH WEIGHTS", flush=True)
        print("🎯 " + "="*50, flush=True)
        
        total_corr = 0
        for s, w, c in zip(self.basket_symbols, self.basket_weights, correlations):
            asset_name = s.split('/')[0]
            total_corr += abs(c)
            print(f"📊 {asset_name:6} | Weight: {w:6.3f} | Corr: {c:6.3f}", flush=True)
        
        avg_correlation = total_corr / len(correlations)
        print(f"📈 Average correlation: {avg_correlation:.3f}", flush=True)
        print("🎯 " + "="*50, flush=True)

    def get_current_prices(self):
        prices = {}
        try:
            symbols = [self.target] + self.basket_symbols
            tickers = self.exchange.fetch_tickers(symbols)
            for s in symbols:
                if s in tickers and tickers[s].get("last") is not None:
                    prices[s] = tickers[s]["last"]
            if len(prices) != len(symbols):
                logger.warning("⚠️ Some prices are missing.")
                return None
            return prices
        except Exception as e:
            logger.warning(f"❌ Error fetching tickers: {e}")
            return None

    def calculate_basket_price(self, prices):
        return sum(self.basket_weights[i] * prices[s] for i, s in enumerate(self.basket_symbols) if s in prices)

    def calculate_spread_series(self):
        min_len = min(len(self.historical_data[s]) for s in [self.target]+self.basket_symbols if s in self.historical_data)
        if min_len < 10:
            logger.warning("⚠️ Insufficient historical data.")
            return None
        target = np.array(self.historical_data[self.target][-min_len:])
        basket = np.zeros(min_len)
        for i, s in enumerate(self.basket_symbols):
            basket += self.basket_weights[i] * np.array(self.historical_data[s][-min_len:])
        return target / basket

    def calculate_zscore(self, current_prices):
        if not all(s in current_prices for s in [self.target]+self.basket_symbols):
            return None, None, None
        spread_now = current_prices[self.target] / self.calculate_basket_price(current_prices)
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
        if z > 2.0: return "SHORT ETH / LONG BASKET"
        if z < -2.0: return "LONG ETH / SHORT BASKET"
        if abs(z) < 0.5: return "EXIT POSITION"
        return "HOLD"

    def run(self, interval_minutes=1):
        logger.info("🚀 Starting OKX basket monitor...")
        
        # ADDED: force flush before analysis
        sys.stdout.flush()
        
        if not self.fetch_historical_data():
            logger.error("❌ Failed to fetch historical data.")
            return
        
        # ADDED: force flush before weight calculation
        sys.stdout.flush()
        
        self.calculate_basket_weights()
        
        # ADDED: force flush after weight calculation
        sys.stdout.flush()
        
        if not self.basket_symbols:
            logger.error("❌ No valid symbols for monitoring.")
            return
        logger.info(f"📊 Monitoring symbols: {self.basket_symbols}")

        last_telegram_time = datetime.utcnow() - timedelta(minutes=10)

        # --- first actual message ---
        prices = self.get_current_prices()
        if prices:
            z, spread, stats = self.calculate_zscore(prices)
            mean, std = stats if stats else (0, 0)
            signal = self.trading_signal(z)
            report_data = {
                "time": datetime.utcnow(),
                "target_price": prices.get(self.target, 0),
                "basket_price": self.calculate_basket_price(prices),
                "spread": spread if spread else 0,
                "mean": mean,
                "std": std,
                "z": z if z else 0,
                "signal": signal,
                "basket_symbols": self.basket_symbols,
                "basket_weights": self.basket_weights
            }
            self.notify(report_data)
            last_telegram_time = datetime.utcnow()

        while True:
            try:
                prices = self.get_current_prices()
                if not prices:
                    time.sleep(60)
                    continue

                z, spread, stats = self.calculate_zscore(prices)
                if z is not None:
                    mean, std = stats
                    signal = self.trading_signal(z)

                    report_data = {
                        "time": datetime.utcnow(),
                        "target_price": prices[self.target],
                        "basket_price": self.calculate_basket_price(prices),
                        "spread": spread,
                        "mean": mean,
                        "std": std,
                        "z": z,
                        "signal": signal,
                        "basket_symbols": self.basket_symbols,
                        "basket_weights": self.basket_weights
                    }

                    # Beautiful Z-score output in real time
                    current_time = datetime.utcnow().strftime('%H:%M:%S')
                    if abs(z) < 1.0:
                        z_color = "🟢"
                    elif abs(z) < 2.0:
                        z_color = "🟡"
                    elif abs(z) < 3.0:
                        z_color = "🟠"
                    else:
                        z_color = "🔴"
                    
                    pretty_logger.info(f"{z_color} [{current_time}] Z-score: {z:6.2f} | Signal: {signal}")

                    if datetime.utcnow() - last_telegram_time >= timedelta(minutes=10):
                        self.notify(report_data)
                        last_telegram_time = datetime.utcnow()
                else:
                    current_time = datetime.utcnow().strftime('%H:%M:%S')
                    pretty_logger.info(f"⚪ [{current_time}] Z-score: NO DATA")

                time.sleep(interval_minutes*60)
            except KeyboardInterrupt:
                logger.info("🛑 Monitoring stopped by user.")
                break
            except Exception as e:
                logger.warning(f"❌ Error in loop: {e}")
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
                offset = (update["update_id"] + 1)
            time.sleep(1)
        except Exception as e:
            print("❌ Telegram polling error:", e)
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