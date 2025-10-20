import logging
import numpy as np
from typing import Tuple, Optional
from datetime import datetime
from config import config
from exchange import exchange
from basket_manager import basket_manager

class SignalGenerator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.spread_history = []
        self.current_zscore = 0.0
        self.current_ratio = 0.0
        
    def calculate_spread_series(self) -> Optional[np.ndarray]:
        target_prices = self._fetch_ohlcv_data(config.TARGET_PAIR)
        if target_prices is None:
            return None
            
        basket_symbols, basket_weights = basket_manager.get_basket_info()
        if not basket_symbols:
            return None
            
        basket_series = []
        for symbol in basket_symbols:
            symbol_prices = self._fetch_ohlcv_data(symbol)
            if symbol_prices is None:
                return None
            basket_series.append(symbol_prices)
        
        min_length = min(len(target_prices), *[len(s) for s in basket_series])
        if min_length < 10:
            return None
        
        target_aligned = target_prices[-min_length:]
        basket_matrix = np.array([s[-min_length:] for s in basket_series])
        
        weights = np.array(basket_weights)
        weights = weights / np.sum(np.abs(weights))
        basket_prices = np.dot(weights, basket_matrix)
        
        spread_series = target_aligned / basket_prices
        return spread_series

    def _fetch_ohlcv_data(self, symbol: str) -> Optional[np.ndarray]:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, limit=config.LOOKBACK)
            if not ohlcv:
                return None
            closes = [candle[4] for candle in ohlcv]
            return np.array(closes, dtype=np.float64)
        except Exception as e:
            self.logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    def calculate_current_zscore(self) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        spread_series = self.calculate_spread_series()
        if spread_series is None:
            return None, None, None, None
            
        current_prices = self._get_current_prices()
        if current_prices is None:
            return None, None, None, None
            
        basket_price = self._calculate_current_basket_price(current_prices)
        if basket_price is None:
            return None, None, None, None
        
        current_ratio = current_prices[config.TARGET_PAIR] / basket_price
        spread_mean = np.mean(spread_series)
        spread_std = np.std(spread_series)
        
        if spread_std < 1e-12:
            return None, None, None, None
        
        z_score = (current_ratio - spread_mean) / spread_std
        
        self.current_zscore = z_score
        self.current_ratio = current_ratio
        
        return z_score, current_ratio, spread_mean, spread_std

    def _get_current_prices(self) -> Optional[dict]:
        symbols = [config.TARGET_PAIR] + basket_manager.basket_symbols
        try:
            tickers = exchange.fetch_tickers(symbols)
            prices = {}
            for symbol in symbols:
                if symbol in tickers:
                    prices[symbol] = float(tickers[symbol]['last'])
                else:
                    return None
            return prices
        except Exception as e:
            self.logger.error(f"Error fetching current prices: {e}")
            return None

    def _calculate_current_basket_price(self, prices: dict) -> Optional[float]:
        basket_symbols, basket_weights = basket_manager.get_basket_info()
        if not basket_symbols:
            return None
            
        basket_price = 0
        for i, symbol in enumerate(basket_symbols):
            if symbol in prices:
                weight = basket_weights[i]
                basket_price += weight * prices[symbol]
            else:
                return None
                
        return basket_price

    def generate_signal(self) -> str:
        z_score, ratio, mean, std = self.calculate_current_zscore()
        if z_score is None:
            return "NO_SIGNAL"
        
        if abs(z_score) >= config.Z_ENTER:
            if z_score > 0:
                return "SHORT_TARGET_LONG_BASKET"
            else:
                return "LONG_TARGET_SHORT_BASKET"
                
        elif abs(z_score) <= config.Z_EXIT:
            return "EXIT_POSITION"
            
        return "NO_SIGNAL"

    def get_current_metrics(self) -> Tuple[float, float, float, float]:
        return self.current_zscore, self.current_ratio, 0.0, 0.0

    def is_stop_loss_triggered(self) -> bool:
        return abs(self.current_zscore) >= config.MAX_Z_STOP

# Global signal generator instance
signal_generator = SignalGenerator()
