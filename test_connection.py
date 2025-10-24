#!/usr/bin/env python3
import ccxt
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_okx_connection():
    print("🔍 Testing OKX connection...")
    
    try:
        exchange = ccxt.okx({
            "enableRateLimit": True,
            "options": {"defaultType": "swap"},
            "sandbox": False
        })
        
        # Загружаем рынки
        print("📊 Loading markets...")
        markets = exchange.load_markets()
        print(f"✅ Loaded {len(markets)} markets")
        
        # Пробуем получить тикеры для основных пар
        test_symbols = ["BTC/USDT:USDT", "ETH/USDT:USDT", "BNB/USDT:USDT"]
        print("📈 Testing price data...")
        
        for symbol in test_symbols:
            try:
                ticker = exchange.fetch_ticker(symbol)
                print(f"✅ {symbol}: {ticker['last']}")
            except Exception as e:
                print(f"❌ {symbol}: {e}")
                
        # Тестируем исторические данные
        print("📊 Testing historical data...")
        ohlcv = exchange.fetch_ohlcv("BTC/USDT:USDT", "15m", limit=10)
        print(f"✅ BTC Historical data: {len(ohlcv)} bars")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    test_okx_connection()