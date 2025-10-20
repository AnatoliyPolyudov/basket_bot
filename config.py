import os from dataclasses import dataclass @dataclass 
class TradingConfig:
    # Exchange Settings
    EXCHANGE_ID: str = "okx" TARGET_PAIR: str = 
    "SOL-USDT-SWAP" BASKET_SIZE: int = 4 TIMEFRAME: str 
    = "5m" LOOKBACK: int = 120 REFRESH_INTERVAL: int = 
    60
    
    # Strategy Parameters
    Z_ENTER: float = 2.0 Z_EXIT: float = 0.7 
    MAX_Z_STOP: float = 4.0
    
    # Basket Settings
    TOP_BY_VOLUME: int = 30 MIN_VOLUME_FILTER: float = 
    1000000.0 REBALANCE_HOURS: int = 6
    
    # Risk Management
    MAX_POSITION_SIZE: float = 1000.0 ENABLE_STOP_LOSS: 
    bool = True LEVERAGE: int = 3
    
    # OKX API Configuration
    OKX_API_KEY: str = os.getenv("OKX_API_KEY", "") 
    OKX_SECRET_KEY: str = os.getenv("OKX_SECRET_KEY", 
    "") OKX_PASSPHRASE: str = 
    os.getenv("OKX_PASSPHRASE", "")
    
    # Trading Settings
    MARKET_TYPE: str = "swap" # spot, swap, future 
    MARGIN_MODE: str = "cross" # isolated, cross
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: str = 
    os.getenv("TELEGRAM_BOT_TOKEN", "") 
    TELEGRAM_CHAT_ID: str = 
    os.getenv("TELEGRAM_CHAT_ID", "") TELEGRAM_ENABLED: 
    bool = True
    
    # Symbol Configuration
    FUTURES_SUFFIX: str = "-SWAP" SPOT_SUFFIX: str = 
    "/USDT"
    
    def validate(self): if self.Z_ENTER <= self.Z_EXIT: 
            raise ValueError("Z_ENTER must be greater 
            than Z_EXIT")
        if self.BASKET_SIZE < 2: raise 
            ValueError("BASKET_SIZE must be at least 
            2")
        if self.LOOKBACK < 20: raise 
            ValueError("LOOKBACK must be at least 20")
        if not self.OKX_API_KEY: raise 
            ValueError("OKX_API_KEY is required")
        if self.LEVERAGE < 1 or self.LEVERAGE > 100: 
            raise ValueError("LEVERAGE must be between 
            1 and 100")
config = TradingConfig()
