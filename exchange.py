# exchange.py
import ccxt import logging from typing import Dict, 
List from config import config class OKXExchange:
    def __init__(self): self.logger = 
        logging.getLogger(__name__) self.exchange = 
        self._initialize_exchange() self.markets = None 
        self.load_markets()
    def _initialize_exchange(self) -> ccxt.Exchange: 
        exchange_config = {
            'apiKey': config.OKX_API_KEY, 'secret': 
            config.OKX_SECRET_KEY, 'password': 
            config.OKX_PASSPHRASE, 'sandbox': False, 
            'enableRateLimit': True, 'options': {
                'defaultType': config.MARKET_TYPE
            }
        }
        return ccxt.okx(exchange_config) def 
    load_markets(self) -> None:
        try: self.markets = 
            self.exchange.load_markets() 
            self.logger.info("Markets loaded 
            successfully")
        except Exception as e: 
            self.logger.error(f"Error loading markets: 
            {e}") raise
    def get_swap_symbols(self) -> List[str]: symbols = 
        [] for symbol, market in self.markets.items():
            if market.get('swap') and 
            market.get('active') and 
            symbol.endswith(config.FUTURES_SUFFIX):
                symbols.append(symbol) return symbols 
    def fetch_tickers(self, symbols: List[str] = None) 
    -> Dict:
        try: if symbols: return 
                self.exchange.fetch_tickers(symbols)
            return self.exchange.fetch_tickers() except 
        Exception as e:
            self.logger.error(f"Error fetching tickers: 
            {e}") return {}
    def fetch_ohlcv(self, symbol: str, timeframe: str = 
    None, limit: int = None) -> List:
        try: tf = timeframe or config.TIMEFRAME lim = 
            limit or config.LOOKBACK return 
            self.exchange.fetch_ohlcv(symbol, 
            timeframe=tf, limit=lim)
        except Exception as e: 
            self.logger.error(f"Error fetching OHLCV 
            for {symbol}: {e}") return []
    def fetch_balance(self) -> Dict: try: return 
            self.exchange.fetch_balance()
        except Exception as e: 
            self.logger.error(f"Error fetching balance: 
            {e}") return {}
    def set_leverage(self, symbol: str, leverage: int) 
    -> bool:
        try: self.exchange.set_leverage(leverage, 
            symbol) self.logger.info(f"Leverage set to 
            {leverage} for {symbol}") return True
        except Exception as e: 
            self.logger.error(f"Error setting leverage 
            for {symbol}: {e}") return False
    def create_order(self, symbol: str, order_type: 
    str, side: str, amount: float, price: float = None) 
    -> Dict:
        try: order_params = { 'symbol': symbol, 'type': 
                order_type, 'side': side, 'amount': 
                amount
            }
            if price is not None: order_params['price'] 
                = price
            return 
            self.exchange.create_order(**order_params)
        except Exception as e: 
            self.logger.error(f"Error creating order 
            for {symbol}: {e}") return {}
    def get_positions(self, symbol: str = None) -> 
    List[Dict]:
        try: positions = 
            self.exchange.fetch_positions([symbol] if 
            symbol else None) return [pos for pos in 
            positions if pos.get('contracts', 0) > 0]
        except Exception as e: 
            self.logger.error(f"Error fetching 
            positions: {e}") return []
    def close_position(self, symbol: str) -> bool: try: 
            positions = self.get_positions(symbol) if 
            not positions:
                return True for position in positions: 
                side = 'sell' if position['side'] == 
                'long' else 'buy' 
                self.create_order(symbol=symbol, 
                order_type='market', side=side, 
                amount=abs(position['contracts']))
            return True except Exception as e: 
            self.logger.error(f"Error closing position 
            for {symbol}: {e}") return False
# Global exchange instance
exchange = OKXExchange()
