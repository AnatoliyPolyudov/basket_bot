#!/usr/bin/env python3
"""
КОНФИГУРАЦИЯ ТОРГОВЫХ ПАР
Легко добавлять, удалять и тестировать пары
"""

# 🎯 БАЗА ДАННЫХ ВСЕХ ДОСТУПНЫХ СИМВОЛОВ НА OKX
AVAILABLE_SYMBOLS = [
    "BTC/USDT:USDT", "ETH/USDT:USDT", "BNB/USDT:USDT", "SOL/USDT:USDT",
    "XRP/USDT:USDT", "ADA/USDT:USDT", "AVAX/USDT:USDT", "DOT/USDT:USDT", 
    "LINK/USDT:USDT", "LTC/USDT:USDT", "ATOM/USDT:USDT", "TRX/USDT:USDT",
    "XLM/USDT:USDT", "BCH/USDT:USDT", "FIL/USDT:USDT", "ETC/USDT:USDT",
    "EOS/USDT:USDT", "AAVE/USDT:USDT", "ALGO/USDT:USDT", "XTZ/USDT:USDT",
    "XMR/USDT:USDT", "DASH/USDT:USDT", "ZEC/USDT:USDT", "COMP/USDT:USDT"
]

# 🎯 ПРЕСЕТЫ ПАР (легко переключаться между наборами)
PAIR_PRESETS = {
    "top_10_btc_pairs": [
        # Топ-10 пар BTC с основными альтами
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
    
    "eth_cross_pairs": [
        # Пары ETH с другими альтами
        {"asset_a": "ETH/USDT:USDT", "asset_b": "BNB/USDT:USDT", "name": "ETH_BNB"},
        {"asset_a": "ETH/USDT:USDT", "asset_b": "SOL/USDT:USDT", "name": "ETH_SOL"},
        {"asset_a": "ETH/USDT:USDT", "asset_b": "XRP/USDT:USDT", "name": "ETH_XRP"},
        {"asset_a": "ETH/USDT:USDT", "asset_b": "ADA/USDT:USDT", "name": "ETH_ADA"},
        {"asset_a": "ETH/USDT:USDT", "asset_b": "AVAX/USDT:USDT", "name": "ETH_AVAX"},
        {"asset_a": "ETH/USDT:USDT", "asset_b": "DOT/USDT:USDT", "name": "ETH_DOT"},
    ],
    
    "altcoin_pairs": [
        # Пары между альтами
        {"asset_a": "BNB/USDT:USDT", "asset_b": "SOL/USDT:USDT", "name": "BNB_SOL"},
        {"asset_a": "SOL/USDT:USDT", "asset_b": "AVAX/USDT:USDT", "name": "SOL_AVAX"},
        {"asset_a": "XRP/USDT:USDT", "asset_b": "ADA/USDT:USDT", "name": "XRP_ADA"},
        {"asset_a": "DOT/USDT:USDT", "asset_b": "LINK/USDT:USDT", "name": "DOT_LINK"},
        {"asset_a": "LTC/USDT:USDT", "asset_b": "ATOM/USDT:USDT", "name": "LTC_ATOM"},
    ],
    
    "full_20_pairs": [
        # Полный набор из 20 пар (текущий)
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
        {"asset_a": "ETH/USDT:USDT", "asset_b": "BNB/USDT:USDT", "name": "ETH_BNB"},
        {"asset_a": "ETH/USDT:USDT", "asset_b": "SOL/USDT:USDT", "name": "ETH_SOL"},
        {"asset_a": "ETH/USDT:USDT", "asset_b": "XRP/USDT:USDT", "name": "ETH_XRP"},
        {"asset_a": "ETH/USDT:USDT", "asset_b": "ADA/USDT:USDT", "name": "ETH_ADA"},
        {"asset_a": "ETH/USDT:USDT", "asset_b": "AVAX/USDT:USDT", "name": "ETH_AVAX"},
        {"asset_a": "ETH/USDT:USDT", "asset_b": "DOT/USDT:USDT", "name": "ETH_DOT"},
        {"asset_a": "BNB/USDT:USDT", "asset_b": "SOL/USDT:USDT", "name": "BNB_SOL"},
        {"asset_a": "SOL/USDT:USDT", "asset_b": "AVAX/USDT:USDT", "name": "SOL_AVAX"},
        {"asset_a": "XRP/USDT:USDT", "asset_b": "ADA/USDT:USDT", "name": "XRP_ADA"},
        {"asset_a": "DOT/USDT:USDT", "asset_b": "LINK/USDT:USDT", "name": "DOT_LINK"},
    ]
}

def generate_pair_name(asset_a, asset_b):
    """Автогенерация имени пары"""
    name_a = asset_a.split('/')[0]
    name_b = asset_b.split('/')[0]
    return f"{name_a}_{name_b}"

def create_custom_pairs(asset_list, base_asset=None):
    """
    Автоматическое создание пар из списка активов
    """
    pairs = []
    
    if base_asset:
        # Создаем пары с базовым активом
        for asset in asset_list:
            if asset != base_asset:
                pairs.append({
                    "asset_a": base_asset,
                    "asset_b": asset,
                    "name": generate_pair_name(base_asset, asset)
                })
    else:
        # Создаем все возможные комбинации
        for i in range(len(asset_list)):
            for j in range(i + 1, len(asset_list)):
                pairs.append({
                    "asset_a": asset_list[i],
                    "asset_b": asset_list[j], 
                    "name": generate_pair_name(asset_list[i], asset_list[j])
                })
    
    return pairs

def validate_pair(pair):
    """Проверка валидности пары"""
    if pair["asset_a"] not in AVAILABLE_SYMBOLS:
        return False, f"Asset A not available: {pair['asset_a']}"
    if pair["asset_b"] not in AVAILABLE_SYMBOLS:
        return False, f"Asset B not available: {pair['asset_b']}"
    if pair["asset_a"] == pair["asset_b"]:
        return False, "Assets cannot be the same"
    
    return True, "Valid"

def get_preset(preset_name):
    """Получить пресет пар по имени"""
    return PAIR_PRESETS.get(preset_name, [])

def list_available_presets():
    """Список доступных пресетов"""
    return list(PAIR_PRESETS.keys())

def test_pair_combinations():
    """Тестирование различных комбинаций пар"""
    test_results = {}
    
    for preset_name, pairs in PAIR_PRESETS.items():
        valid_pairs = []
        invalid_pairs = []
        
        for pair in pairs:
            is_valid, message = validate_pair(pair)
            if is_valid:
                valid_pairs.append(pair)
            else:
                invalid_pairs.append((pair, message))
        
        test_results[preset_name] = {
            'total': len(pairs),
            'valid': len(valid_pairs),
            'invalid': invalid_pairs
        }
    
    return test_results

if __name__ == "__main__":
    # Тестирование при запуске напрямую
    print("🔍 TESTING PAIR CONFIGURATIONS...")
    results = test_pair_combinations()
    
    for preset, data in results.items():
        print(f"\n📊 {preset.upper()}:")
        print(f"   Total pairs: {data['total']}")
        print(f"   Valid pairs: {data['valid']}")
        print(f"   Invalid pairs: {len(data['invalid'])}")
        
        for invalid_pair, reason in data['invalid']:
            print(f"     ❌ {invalid_pair['name']}: {reason}")