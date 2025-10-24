def get_top_symbols_from_exchange(limit=30):
    """Получает ТОЛЬКО ликвидные символы с OKX"""
    try:
        # Жестко задаем список ликвидных пар (топ-20 по объему)
        liquid_symbols = [
            "BTC/USDT:USDT", "ETH/USDT:USDT", "BNB/USDT:USDT", "SOL/USDT:USDT",
            "XRP/USDT:USDT", "ADA/USDT:USDT", "AVAX/USDT:USDT", "DOT/USDT:USDT",
            "LINK/USDT:USDT", "LTC/USDT:USDT", "ATOM/USDT:USDT", "DOGE/USDT:USDT",
            "MATIC/USDT:USDT", "TRX/USDT:USDT", "XLM/USDT:USDT", "BCH/USDT:USDT",
            "FIL/USDT:USDT", "ETC/USDT:USDT", "EOS/USDT:USDT", "AAVE/USDT:USDT"
        ]
        
        print(f"✅ Using {len(liquid_symbols)} LIQUID symbols")
        print("📋 Liquid symbols:", liquid_symbols[:10])
        
        return liquid_symbols[:limit]
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return get_fallback_symbols()[:limit]