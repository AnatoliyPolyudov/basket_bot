# monitor.py
import ccxt
import numpy as np
import time
import logging
from datetime import datetime

# Logging setup (без временных меток в выводе)
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.FileHandler("okx_basket_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OKXBasketMonitor:
    def __init__(self):
        self.exchange = ccxt.okx({
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},  # используем spot (USDT)
            "sandbox": False
        })
        self.target = "BTC/USDT:USDT"
        self.basket_symbols = ["ETH/USDT:USDT", "BNB/USDT:USDT", "SOL/USDT:USDT", "XRP/USDT:USDT"]
        self.basket_weights = []
        self.historical_data = {}
        self.lookback_days = 20  # меньше дней, чтобы экономить память

    def fetch_historical_data(self):
        logger.info("Fetching historical data from OKX...")
        symbols = [self.target] + self.basket_symbols
        for symbol in symbols:
            try:
                since = self.exchange.parse8601(
                    (datetime.utcnow() - np.timedelta64(self.lookback_days, 'D')).astype(str)
                )
                ohlcv = self.exchange.fetch_ohlcv(symbol, "1d", since=since, limit=self.lookback_days)
                if ohlcv:
                    # Храним только close
                    self.historical_data[symbol] = np.array([c[4] for c in ohlcv], dtype=np.float32)
                    logger.info(f"Loaded {len(self.historical_data[symbol])} days for {symbol}")
                else:
                    logger.warning(f"No data for {symbol}")
            except Exception as e:
                logger.error(f"Error loading data for {symbol}: {e}")

        # Проверяем минимальное количество валидных символов
        valid = [s for s in symbols if s in self.historical_data and len(self.historical_data[s]) >= 10]
        if len(valid) < 3:
            logger.error("Not enough valid symbols for analysis.")
            return False
        return True

    def calculate_basket_weights(self):
        correlations = []
        valid_symbols = []
        for s in self.basket_symbols:
            if s in self.historical_data and self.target in self.historical_data:
                if len(self.historical_data[s]) == len(self.historical_data[self.target]):
                    corr = np.corrcoef(self.historical_data[self.target], self.historical_data[s])[0, 1]
                    if not np.isnan(corr):
                        correlations.append(corr)
                        valid_symbols.append(s)
                        logger.info(f"Correlation BTC/{s}: {corr:.3f}")
        self.basket_symbols = valid_symbols
        if correlations:
            abs_corr = np.abs(correlations)
            self.basket_weights = abs_corr / abs_corr.sum()
        else:
            self.basket_weights = np.ones(len(self.basket_symbols)) / len(self.basket_symbols)
            logger.warning("No valid correlations, using equal weights.")
        for s, w in zip(self.basket_symbols, self.basket_weights):
            logger.info(f"{s}: weight={w:.3f}")

    def get_current_prices(self):
        prices = {}
        try:
            symbols = [self.target] + self.basket_symbols
            tickers = self.exchange.fetch_tickers(symbols)
            for s in symbols:
                if s in tickers and tickers[s].get("last") is not None:
                    prices[s] = tickers[s]["last"]
            if len(prices) != len(symbols):
                logger.warning("Some prices are missing.")
                return None
            return prices
        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            return None

    def calculate_basket_price(self, prices):
        return sum(self.basket_weights[i] * prices[s] for i, s in enumerate(self.basket_symbols) if s in prices)

    def calculate_zscore(self, current_prices):
        if not all(s in current_prices for s in [self.target] + self.basket_symbols):
            return None, None, None
        basket = self.calculate_basket_price(current_prices)
        spread_now = current_prices[self.target] / basket
        min_len = min(len(self.historical_data[s]) for s in [self.target] + self.basket_symbols)
        target_hist = self.historical_data[self.target][-min_len:]
        basket_hist = np.zeros(min_len, dtype=np.float32)
        for i, s in enumerate(self.basket_symbols):
            basket_hist += self.basket_weights[i] * self.historical_data[s][-min_len:]
        spread_hist = target_hist / basket_hist
        mean, std = spread_hist.mean(), spread_hist.std()
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

    def run(self, interval_minutes=5):
        logger.info("Starting basket monitor...")
        if not self.fetch_historical_data():
            return
        self.calculate_basket_weights()
        if not self.basket_symbols:
            return
        logger.info(f"Monitoring symbols: {self.basket_symbols}")

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
                    report = f"""
BTC: {prices[self.target]:.2f}
Basket: {self.calculate_basket_price(prices):.2f}
Spread: {spread:.6f}
Mean ± Std: {mean:.6f} ± {std:.6f}
Z-Score: {z:.4f}
Signal: {signal}
"""
                    print(report)
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                logger.info("Stopped by user.")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(60)

def main():
    monitor = OKXBasketMonitor()
    monitor.run(interval_minutes=5)

if __name__ == "__main__":
    main()
