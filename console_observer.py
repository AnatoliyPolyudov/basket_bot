from observer import Observer
from datetime import datetime

class ConsoleObserver(Observer):
    def update(self, data):
        print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] Observer received update:")
        print(f"  Signal: {data['signal']}, Z-score: {data['z']:.4f}, Spread: {data['spread']:.6f}")
