from observer import Observer
from datetime import datetime

class ConsoleObserver(Observer):
    def update(self, data):
        # 🆕 ОБРАБАТЫВАЕМ НОВЫЙ ФОРМАТ ДАННЫХ
        pairs_data = data.get('pairs_data', [])
        total_pairs = data.get('total_pairs', 0)
        active_pairs = data.get('active_pairs', 0)
        
        print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] R-STYLE PAIR MONITOR")
        print(f"Active Pairs: {active_pairs}/{total_pairs}")
        print("-" * 50)
        
        for pair_data in pairs_data:
            pair_name = pair_data.get('pair_name', 'UNKNOWN')
            signal = pair_data.get('signal', 'NO DATA')
            z_score = pair_data.get('z', 0)
            spread = pair_data.get('spread', 0)
            adf_passed = pair_data.get('adf_passed', False)
            
            print(f"Pair: {pair_name}")
            print(f"  Signal: {signal}")
            
            # 🆕 БЕЗОПАСНОЕ ФОРМАТИРОВАНИЕ Z-SCORE
            if z_score is None:
                print(f"  Z-score: N/A")
            else:
                try:
                    z_float = float(z_score)
                    print(f"  Z-score: {z_float:.4f}")
                except (ValueError, TypeError):
                    print(f"  Z-score: {z_score}")
            
            # 🆕 БЕЗОПАСНОЕ ФОРМАТИРОВАНИЕ SPREAD
            if spread is None:
                print(f"  Spread: N/A")
            else:
                try:
                    spread_float = float(spread)
                    print(f"  Spread: {spread_float:.6f}")
                except (ValueError, TypeError):
                    print(f"  Spread: {spread}")
            
            print(f"  ADF: {'PASSED' if adf_passed else 'FAILED'}")
            
            # 🆕 БЕЗОПАСНОЕ ФОРМАТИРОВАНИЕ ЦЕН
            price_a = pair_data.get('price_a', 0)
            price_b = pair_data.get('price_b', 0)
            asset_a = pair_data.get('asset_a', '')
            asset_b = pair_data.get('asset_b', '')
            
            try:
                price_a_float = float(price_a) if price_a is not None else 0
                price_b_float = float(price_b) if price_b is not None else 0
                print(f"  Prices: {asset_a}={price_a_float:.2f} | {asset_b}={price_b_float:.2f}")
            except (ValueError, TypeError):
                print(f"  Prices: {asset_a}={price_a} | {asset_b}={price_b}")
            
            print("-" * 30)