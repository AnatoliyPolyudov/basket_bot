from observer import Observer
from datetime import datetime

class ConsoleObserver(Observer):
    def update(self, data):
        basket_symbols = data.get('basket_symbols', [])
        symbols_text = "\n".join(basket_symbols) if basket_symbols else "—"

        print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] Basket Monitor Update")
        print(f"Signal: {data.get('signal')}")
        print(f"Z-score: {data.get('z', 0):.4f}")
        print(f"Spread: {data.get('spread', 0):.6f}")
        print(f"Basket Price: {data.get('basket_price', 0):.2f}")
        print(f"Target Price: {data.get('target_price', 0):.2f}")
        print(f"Current pairs:\n{symbols_text}")
        print("-" * 50)
