# telegram_observer.py
from observer import Observer
import json
import requests
from datetime import datetime, timedelta
from callback_handler import handle_callback

TELEGRAM_BOT_TOKEN = "8436652130:AAF6On0GJtRHfMZyqD3mpM57eXZfWofJeng"
TELEGRAM_CHAT_ID = 317217451  # числовой ID чата

class TelegramObserver(Observer):
    def __init__(self, trader=None):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.trader = trader
        self.last_sent = datetime.utcnow() - timedelta(minutes=10)  # сразу можно отправить

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
            print("✅ Telegram message sent")
        except Exception as e:
            print("❌ Telegram send failed:", e)

    def update(self, data):
        # проверка интервала (раз в 10 минут)
        if datetime.utcnow() - self.last_sent < timedelta(minutes=10):
            return
        self.last_sent = datetime.utcnow()

        # формируем текст сообщения
        basket_symbols = data.get('basket_symbols', [])
        symbols_text = ", ".join(basket_symbols) if basket_symbols else "—"
        
        msg = (
            f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] Basket Monitor Update\n"
            f"Signal: {data.get('signal')}\n"
            f"Z-score: {data.get('z', 0):.4f}\n"
            f"Spread: {data.get('spread', 0):.6f}\n"
            f"Basket Price: {data.get('basket_price', 0):.2f}\n"
            f"Target Price: {data.get('target_price', 0):.2f}\n"
            f"Current pairs: {symbols_text}"
        )

        buttons = None
        signal = data.get('signal', "")
        # Кнопки для всех сигналов кроме NO DATA
        if signal and signal != "NO DATA":
            buttons = [
                [
                    {'text': 'Open Position', 'callback_data': f'OPEN:{signal}'},
                    {'text': 'Close Position', 'callback_data': f'CLOSE:{signal}'}
                ]
            ]

        self.send_message(msg, buttons)
