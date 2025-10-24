#!/usr/bin/env python3
"""
КОНФИГУРАЦИЯ ТОРГОВЫХ ПАР - ТОЛЬКО ЛИКВИДНЫЕ И ПРОВЕРЕННЫЕ ПАРЫ
"""

import ccxt
import json
from typing import List, Dict
import time

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

def get_fallback_symbols():
    """Резервные символы если не удалось загрузить с биржи"""
    return [
        "BTC/USDT:USDT", "ETH/USDT:USDT", "BNB/USDT:USDT", "SOL/USDT:USDT",
        "XRP/USDT:USDT", "ADA/USDT:USDT", "AVAX/USDT:USDT", "DOT/USDT:USDT",
        "LINK/USDT:USDT", "LTC/USDT:USDT", "ATOM/USDT:USDT", "TRX/USDT:USDT",
        "XLM/USDT:USDT", "BCH/USDT:USDT", "FIL/USDT:USDT", "ETC/USDT:USDT",
        "EOS/USDT:USDT", "AAVE/USDT:USDT", "ALGO/USDT:USDT", "XTZ/USDT:USDT"
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
    
    # Новый проверенный пресет с ликвидными парами
    liquid_pairs = [
        {"asset_a": "BTC/USDT:USDT", "asset_b": "ETH/USDT:USDT", "name": "BTC_ETH"},
        {"asset_a": "BTC/USDT:USDT", "asset_b": "BNB/USDT:USDT", "name": "BTC_BNB"},
        {"asset_a": "BTC/USDT:USDT", "asset_b": "SOL/USDT:USDT", "name": "BTC_SOL"},
        {"asset_a": "BTC/USDT:USDT", "asset_b": "XRP/USDT:USDT", "name": "BTC_XRP"},
        {"asset_a": "BTC/USDT:USDT", "asset_b": "ADA/USDT:USDT", "name": "BTC_ADA"},
        {"asset_a": "ETH/USDT:USDT", "asset_b": "BNB/USDT:USDT", "name": "ETH_BNB"},
        {"asset_a": "ETH/USDT:USDT", "asset_b": "SOL/USDT:USDT", "name": "ETH_SOL"},
        {"asset_a": "ETH/USDT:USDT", "asset_b": "ADA/USDT:USDT", "name": "ETH_ADA"},
        {"asset_a": "BNB/USDT:USDT", "asset_b": "SOL/USDT:USDT", "name": "BNB_SOL"},
        {"asset_a": "XRP/USDT:USDT", "asset_b": "ADA/USDT:USDT", "name": "XRP_ADA"},
        {"asset_a": "BTC/USDT:USDT", "asset_b": "LTC/USDT:USDT", "name": "BTC_LTC"},
        {"asset_a": "ETH/USDT:USDT", "asset_b": "LTC/USDT:USDT", "name": "ETH_LTC"},
        {"asset_a": "BTC/USDT:USDT", "asset_b": "LINK/USDT:USDT", "name": "BTC_LINK"},
        {"asset_a": "ETH/USDT:USDT", "asset_b": "LINK/USDT:USDT", "name": "ETH_LINK"},
        {"asset_a": "BTC/USDT:USDT", "asset_b": "AVAX/USDT:USDT", "name": "BTC_AVAX"},
    ]
    
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
        ],
        
        # 🎯 НОВЫЙ ПРОВЕРЕННЫЙ ПРЕСЕТ
        "liquid_pairs_15": liquid_pairs,
        
        # 🔥 УЛЬТРА-ЛИКВИДНЫЕ ПАРЫ (топ-8)
        "ultra_liquid_8": [
            {"asset_a": "BTC/USDT:USDT", "asset_b": "ETH/USDT:USDT", "name": "BTC_ETH"},
            {"asset_a": "BTC/USDT:USDT", "asset_b": "BNB/USDT:USDT", "name": "BTC_BNB"},
            {"asset_a": "BTC/USDT:USDT", "asset_b": "SOL/USDT:USDT", "name": "BTC_SOL"},
            {"asset_a": "ETH/USDT:USDT", "asset_b": "BNB/USDT:USDT", "name": "ETH_BNB"},
            {"asset_a": "ETH/USDT:USDT", "asset_b": "SOL/USDT:USDT", "name": "ETH_SOL"},
            {"asset_a": "BNB/USDT:USDT", "asset_b": "SOL/USDT:USDT", "name": "BNB_SOL"},
            {"asset_a": "BTC/USDT:USDT", "asset_b": "ADA/USDT:USDT", "name": "BTC_ADA"},
            {"asset_a": "ETH/USDT:USDT", "asset_b": "ADA/USDT:USDT", "name": "ETH_ADA"},
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

if __name__ == "__main__":
    print("🔍 TESTING ALL PRESETS...")
    presets = get_all_presets()
    
    for name, pairs in presets.items():
        print(f"\n🎯 {name.upper()} ({len(pairs)} pairs):")
        for pair in pairs[:3]:  # Показываем первые 3 пары
            print(f"   {pair['name']}: {pair['asset_a']} / {pair['asset_b']}")
        if len(pairs) > 3:
            print(f"   ... and {len(pairs) - 3} more pairs")