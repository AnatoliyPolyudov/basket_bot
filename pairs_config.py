#!/usr/bin/env python3
"""
КОНФИГУРАЦИЯ ТОРГОВЫХ ПАР - АВТОМАТИЧЕСКАЯ ЗАГРУЗКА ТОП-30
"""

import ccxt
import json
from typing import List, Dict
import time

def get_top_symbols_from_exchange(limit=30):
    """Автоматически получает топовые символы с OKX по объему"""
    try:
        exchange = ccxt.okx({
            "enableRateLimit": True,
            "options": {"defaultType": "swap"},
            "sandbox": False
        })
        
        print(f"🔍 Loading top {limit} symbols from OKX...")
        
        # Загружаем рынки
        markets = exchange.load_markets()
        print(f"✅ Loaded {len(markets)} total markets")
        
        # Фильтруем USDT своп пары
        usdt_pairs = []
        for symbol, market in markets.items():
            if (market.get('quote') == 'USDT' and 
                market.get('type') == 'swap' and 
                market.get('active') and
                '/USDT:USDT' in symbol):
                
                # Используем базовую информацию
                base_currency = market.get('base')
                if base_currency:
                    usdt_pairs.append({
                        'symbol': symbol,
                        'volume': market.get('info', {}).get('volCcy24h', 0) or 1000000,  # fallback volume
                        'base': base_currency
                    })
        
        # Если не нашли пары, используем fallback
        if not usdt_pairs:
            print("⚠️ No USDT pairs found, using fallback")
            return get_fallback_symbols()
        
        # Сортируем по символу (так как объем может быть недоступен)
        usdt_pairs.sort(key=lambda x: x['symbol'])
        
        # Берем топ лимит
        top_symbols = [pair['symbol'] for pair in usdt_pairs[:limit]]
        
        print(f"✅ Successfully loaded {len(top_symbols)} symbols")
        print("📋 Sample symbols:", top_symbols[:5])
        return top_symbols
        
    except Exception as e:
        print(f"❌ Error loading symbols from exchange: {e}")
        # Fallback на основные пары
        return get_fallback_symbols()

def get_fallback_symbols():
    """Резервные символы если не удалось загрузить с биржи"""
    return [
        "BTC/USDT:USDT", "ETH/USDT:USDT", "BNB/USDT:USDT", "SOL/USDT:USDT",
        "XRP/USDT:USDT", "ADA/USDT:USDT", "AVAX/USDT:USDT", "DOT/USDT:USDT",
        "LINK/USDT:USDT", "LTC/USDT:USDT", "ATOM/USDT:USDT", "TRX/USDT:USDT",
        "XLM/USDT:USDT", "BCH/USDT:USDT", "FIL/USDT:USDT", "ETC/USDT:USDT",
        "EOS/USDT:USDT", "AAVE/USDT:USDT", "ALGO/USDT:USDT", "XTZ/USDT:USDT",
        "XMR/USDT:USDT", "DASH/USDT:USDT", "ZEC/USDT:USDT", "COMP/USDT:USDT",
        "DOGE/USDT:USDT", "MATIC/USDT:USDT", "NEAR/USDT:USDT", "SAND/USDT:USDT",
        "MANA/USDT:USDT", "ENJ/USDT:USDT"
    ]

def generate_top_30_pairs(symbols: List[str]):
    """Генерирует топ-30 торговых пар"""
    pairs = []
    
    if not symbols:
        symbols = get_fallback_symbols()
    
    # Убедимся что BTC и ETH есть в списке
    essential_symbols = ["BTC/USDT:USDT", "ETH/USDT:USDT"]
    for essential in essential_symbols:
        if essential not in symbols:
            symbols.insert(0, essential)
    
    # 1. BTC пары с топ-10 альтами (кроме себя)
    btc_symbol = "BTC/USDT:USDT"
    btc_counter = 0
    for symbol in symbols:
        if symbol != btc_symbol and btc_counter < 10:
            alt_name = symbol.split('/')[0]
            pairs.append({
                "asset_a": btc_symbol,
                "asset_b": symbol,
                "name": f"BTC_{alt_name}",
                "type": "btc_pair"
            })
            btc_counter += 1
    
    # 2. ETH пары с топ-8 альтами (кроме BTC и себя)
    eth_symbol = "ETH/USDT:USDT"
    eth_counter = 0
    for symbol in symbols:
        if (symbol != eth_symbol and 
            symbol != btc_symbol and 
            not symbol.startswith('BTC/') and 
            eth_counter < 8):
            alt_name = symbol.split('/')[0]
            pairs.append({
                "asset_a": eth_symbol,
                "asset_b": symbol,
                "name": f"ETH_{alt_name}",
                "type": "eth_pair"
            })
            eth_counter += 1
    
    # 3. Пары между топ-12 альтами (исключая BTC/ETH)
    alt_symbols = [s for s in symbols if not s.startswith('BTC/') and not s.startswith('ETH/')][:12]
    alt_pairs_added = 0
    
    for i in range(len(alt_symbols)):
        for j in range(i + 1, len(alt_symbols)):
            if alt_pairs_added >= 12:  # Ограничиваем количество
                break
                
            asset_a = alt_symbols[i]
            asset_b = alt_symbols[j]
            name_a = asset_a.split('/')[0]
            name_b = asset_b.split('/')[0]
            
            pairs.append({
                "asset_a": asset_a,
                "asset_b": asset_b,
                "name": f"{name_a}_{name_b}",
                "type": "alt_pair"
            })
            alt_pairs_added += 1
        
        if alt_pairs_added >= 12:
            break
    
    # Обрезаем до 30 пар если получилось больше
    pairs = pairs[:30]
    
    print(f"✅ Generated {len(pairs)} trading pairs:")
    print(f"   - {btc_counter} BTC pairs")
    print(f"   - {eth_counter} ETH pairs") 
    print(f"   - {alt_pairs_added} ALT pairs")
    
    return pairs

def get_current_top_30_pairs():
    """Основная функция - возвращает текущие топ-30 пар"""
    top_symbols = get_top_symbols_from_exchange(35)  # Берем немного больше на всякий случай
    return generate_top_30_pairs(top_symbols)

# 🎯 ПРЕСЕТЫ (автоматические + ручные для совместимости)
def get_all_presets():
    """Все доступные пресеты"""
    auto_pairs = get_current_top_30_pairs()
    
    return {
        # 🚀 АВТОМАТИЧЕСКИЕ ПРЕСЕТЫ
        "auto_top_30": auto_pairs,
        "auto_top_20": auto_pairs[:20],
        "auto_top_15": auto_pairs[:15],
        "auto_btc_focused": [p for p in auto_pairs if p["asset_a"] == "BTC/USDT:USDT"][:15],
        
        # 📋 РУЧНЫЕ ПРЕСЕТЫ (для совместимости)
        "top_10_btc_pairs": [
            {"asset_a": "BTC/USDT:USDT", "asset_b": "ETH/USDT:USDT", "name": "BTC_ETH"},
            {"asset_a": "BTC/USDT:USDT", "asset_b": "BNB/USDT:USDT", "name": "BTC_BNB"},
            {"asset_a": "BTC/USDT:USDT", "asset_b": "SOL/USDT:USDT", "name": "BTC_SOL"},
            {"asset_a": "BTC/USDT:USDT", "asset_b": "XRP/USDT:USDT", "name": "BTC_XRP"},
            {"asset_a": "BTC/USDT:USDT", "asset_b": "ADA/USDT:USDT", "name": "BTC_ADA"},
            {"asset_a": "BTC/USDT:USDT", "asset_b": "AVAX/USDT:USDT", "name": "BTC_AVAX"},
            {"asset_a": "BTC/USDT:USDT", "asset_b": "DOT/USDT:USDT", "name": "BTC_DOT"},
            {"asset_a": "BTC/USDT:USDT", "asset_b": "LINK/USDT:USDT", "name": "BTC_LINK"},
            {"asset_a": "BTC/USDT:USDT", "asset_b": "LTC/USDT:USDT", "name": "BTC_LTC"},
            {"asset_a": "BTC/USDT:USDT", "asset_b": "ATOM/USDT:USDT", "name": "BTC_ATOM"},
        ]
    }

# Глобальные переменные для обратной совместимости
PAIR_PRESETS = get_all_presets()
AVAILABLE_SYMBOLS = get_top_symbols_from_exchange(30) or get_fallback_symbols()

def get_preset(preset_name):
    """Получить пресет по имени"""
    all_presets = get_all_presets()
    return all_presets.get(preset_name, [])

def list_available_presets():
    """Список всех доступных пресетов"""
    return list(get_all_presets().keys())

def refresh_presets():
    """Принудительное обновление пресетов с биржи"""
    global PAIR_PRESETS, AVAILABLE_SYMBOLS
    PAIR_PRESETS = get_all_presets()
    AVAILABLE_SYMBOLS = get_top_symbols_from_exchange(30) or get_fallback_symbols()
    return PAIR_PRESETS

if __name__ == "__main__":
    def test_pair_combinations():
    """Тестирует все пресеты пар и возвращает результаты"""
    print("🔍 TESTING ALL PAIR PRESETS...")
    results = {}
    
    all_presets = get_all_presets()
    
    for preset_name, pairs in all_presets.items():
        valid_pairs = 0
        total_pairs = len(pairs)
        
        # Проверяем каждую пару на валидность
        for pair in pairs:
            if (pair.get('asset_a') and 
                pair.get('asset_b') and 
                pair.get('name')):
                valid_pairs += 1
        
        results[preset_name] = {
            'valid': valid_pairs,
            'total': total_pairs,
            'pairs': pairs
        }
        
        print(f"📊 {preset_name.upper()}:")
        print(f"   Valid pairs: {valid_pairs}/{total_pairs}")
        if valid_pairs > 0:
            print(f"   Sample: {pairs[0]['name']} - {pairs[0]['asset_a']} / {pairs[0]['asset_b']}")
    
    return results
    
    print("🔍 TESTING AUTO TOP-30 PRESETS...")
    presets = get_all_presets()
    
    for name, pairs in presets.items():
        if name.startswith('auto_'):
            print(f"\n🎯 {name.upper()} ({len(pairs)} pairs):")
            for pair in pairs[:5]:  # Показываем первые 5 пар
                print(f"   {pair['name']}: {pair['asset_a']} / {pair['asset_b']}")
            if len(pairs) > 5:
                print(f"   ... and {len(pairs) - 5} more pairs")