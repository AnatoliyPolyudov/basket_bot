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
            print(f"  Z-score: {z_score:.4f}")
            print(f"  Spread: {spread:.6f}")
            print(f"  ADF: {'PASSED' if adf_passed else 'FAILED'}")
            print(f"  Prices: {pair_data.get('asset_a', '')}={pair_data.get('price_a', 0):.2f} | {pair_data.get('asset_b', '')}={pair_data.get('price_b', 0):.2f}")
            print("-" * 30)