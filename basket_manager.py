# basket_manager.py
import logging import numpy as np from typing import 
List, Tuple, Optional from datetime import datetime, 
timedelta from config import config from exchange 
import exchange class BasketManager:
    def __init__(self): self.logger = 
        logging.getLogger(__name__) 
        self.basket_symbols: List[str] = [] 
        self.basket_weights: List[float] = [] 
        self.last_rebalance: datetime = 
        datetime.utcnow() - 
        timedelta(hours=config.REBALANCE_HOURS + 1)
    def get_high_volume_symbols(self) -> List[str]: 
        try:
            tickers = exchange.fetch_tickers() 
            volume_data = [] for symbol, ticker in 
            tickers.items():
                if 
                symbol.endswith(config.FUTURES_SUFFIX) 
                or symbol == config.TARGET_PAIR:
                    continue volume = 
                ticker.get('quoteVolume', 0) if volume 
                and volume > config.MIN_VOLUME_FILTER:
                    volume_data.append((symbol, 
                    volume))
            volume_data.sort(key=lambda x: x[1], 
            reverse=True) return [s[0] for s in 
            volume_data[:config.TOP_BY_VOLUME]]
        except Exception as e: 
            self.logger.error(f"Error getting high 
            volume symbols: {e}") return []
    def fetch_ohlcv_data(self, symbol: str, limit: int 
    = None) -> Optional[np.ndarray]:
        try: ohlcv = exchange.fetch_ohlcv(symbol, 
            limit=limit or config.LOOKBACK) if not 
            ohlcv:
                return None closes = [candle[4] for 
            candle in ohlcv] return np.array(closes, 
            dtype=np.float64)
        except Exception as e: 
            self.logger.error(f"Error fetching OHLCV 
            for {symbol}: {e}") return None
    def calculate_correlations(self, candidates: 
    List[str]) -> List[Tuple[str, float]]:
        target_prices = 
        self.fetch_ohlcv_data(config.TARGET_PAIR) if 
        target_prices is None or len(target_prices) < 
        config.LOOKBACK // 2:
            return [] correlations = [] for symbol in 
        candidates:
            symbol_prices = 
            self.fetch_ohlcv_data(symbol) if 
            symbol_prices is None:
                continue min_len = 
            min(len(target_prices), len(symbol_prices)) 
            if min_len < config.LOOKBACK // 2:
                continue correlation = 
            np.corrcoef(target_prices[-min_len:], 
            symbol_prices[-min_len:])[0, 1] if not 
            np.isnan(correlation):
                correlations.append((symbol, 
                correlation))
        return correlations def build_basket(self) -> 
    bool:
        self.logger.info("Building new basket...") 
        candidates = self.get_high_volume_symbols() if 
        not candidates:
            self.logger.error("No candidates found") 
            return False
        correlations = 
        self.calculate_correlations(candidates) if not 
        correlations:
            self.logger.error("No correlations 
            calculated") return False
        correlations.sort(key=lambda x: abs(x[1]), 
        reverse=True) selected = 
        correlations[:config.BASKET_SIZE] if 
        len(selected) < 2:
            self.logger.error("Not enough correlated 
            instruments") return False
        symbols = [s[0] for s in selected] corr_values 
        = np.array([s[1] for s in selected]) weights = 
        np.abs(corr_values) weights = weights / 
        weights.sum() signed_weights = weights * 
        np.sign(corr_values) self.basket_symbols = 
        symbols self.basket_weights = 
        signed_weights.tolist() self.last_rebalance = 
        datetime.utcnow() self.logger.info(f"Basket 
        built: {symbols}") self.logger.info(f"Weights: 
        {signed_weights}") return True
    def should_rebalance(self) -> bool: 
        time_since_rebalance = datetime.utcnow() - 
        self.last_rebalance return 
        time_since_rebalance.total_seconds() >= 
        config.REBALANCE_HOURS * 3600
    def get_basket_info(self) -> Tuple[List[str], 
    List[float]]:
        return self.basket_symbols, self.basket_weights 
    def get_current_basket_price(self) -> 
    Optional[float]:
        if not self.basket_symbols: return None prices 
        = [] for symbol in self.basket_symbols:
            try: ticker = 
                exchange.fetch_tickers([symbol]) price 
                = ticker[symbol]['last'] 
                prices.append(float(price))
            except Exception as e: 
                self.logger.error(f"Error fetching 
                price for {symbol}: {e}") return None
        if len(prices) != len(self.basket_symbols): 
            return None
        return float(np.dot(self.basket_weights, 
        prices))
# Global basket manager instance
basket_manager = BasketManager()
