from observer import Observer
import json
import requests
from callback_handler import handle_callback

TELEGRAM_BOT_TOKEN = "8436652130:AAF6On0GJtRHfMZyqD3mpM57eXZfWofJeng"
TELEGRAM_CHAT_ID = 317217451

class TelegramObserver(Observer):
    def __init__(self, trader=None):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.trader = trader
        self.last_signal = None
        self.last_z = None

    def send_message(self, text, buttons=None):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if buttons:
            payload['reply_markup'] = json.dumps({'inline_keyboard': buttons})
        try:
            requests.post(url, data=payload, timeout=10)
            print("Telegram message sent")
        except Exception as e:
            print("Telegram send failed:", e)

    def update(self, data):
        current_signal = data.get('signal', "")
        current_z = data.get('z', 0)
        
        # ФИЛЬТРАЦИЯ: отправляем только при изменении сигнала или сильном изменении Z-score
        should_send = False
        
        # 1. Сигнал изменился
        if current_signal != self.last_signal:
            should_send = True
        
        # 2. Z-score сильно изменился (более чем на 0.1)
        elif (self.last_z is not None and 
              abs(current_z - self.last_z) > 0.1 and
              current_signal != "HOLD" and current_signal != "NO DATA"):
            should_send = True
        
        # 3. Сильный сигнал (выход за пороги)
        elif (current_signal in ["SHORT BTC / LONG BASKET", "LONG BTC / SHORT BASKET", "EXIT POSITION"] and
              current_signal != self.last_signal):
            should_send = True
        
        # 4. Первое сообщение
        elif self.last_signal is None:
            should_send = True
        
        if not should_send:
            return  # Не отправляем сообщение
        
        # Обновляем последние значения
        self.last_signal = current_signal
        self.last_z = current_z
        
        # Формируем сообщение
        basket_symbols = data.get('basket_symbols', [])
        symbols_text = "\n".join(basket_symbols) if basket_symbols else "—"

        z_score = round(data.get('z', 0), 2)
        spread = round(data.get('spread', 0), 3)
        basket_price = round(data.get('basket_price', 0), 2)
        target_price = round(data.get('target_price', 0), 2)

        msg = (
            f"STATISTICAL ARBITRAGE ALERT\n"
            f"Signal: {current_signal}\n"
            f"Z-score: {z_score}\n"
            f"Spread: {spread}\n"
            f"Basket Price: {basket_price}\n"
            f"Target Price: {target_price}\n"
            f"Current pairs:\n{symbols_text}"
        )

        buttons = None
        if current_signal and current_signal != "NO DATA" and current_signal != "HOLD":
            buttons = [
                [
                    {'text': 'OPEN', 'callback_data': f'OPEN:{current_signal}'},
                    {'text': 'CLOSE', 'callback_data': f'CLOSE:{current_signal}'}
                ]
            ]

        self.send_message(msg, buttons)
