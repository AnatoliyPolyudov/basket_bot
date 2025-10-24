# pairs_history.py

class HistoryStorage:
    def __init__(self):
        self.data = {}

    def add_point(self, pair_name: str, value: float):
        if pair_name not in self.data:
            self.data[pair_name] = []
        self.data[pair_name].append(value)

        # ограничиваем длину истории
        if len(self.data[pair_name]) > 300:
            self.data[pair_name] = self.data[pair_name][-300:]

    def get_history(self, pair_name: str):
        return self.data.get(pair_name, [])
