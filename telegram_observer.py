# telegram_observer.py
from observer import Observer
import json
import requests
from datetime import datetime

TELEGRAM_BOT_TOKEN = "8436652130:AAF6On0GJtRHfMZyqD3mpM57eXZfWofJeng"
TELEGRAM_CHAT_ID = 317217451  # числовой ID чата

class TelegramObserver(Observer):
    def __init__(self, trader=None):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.trader = trader

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
        # формируем текст сообщения
        msg = (
            f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] Basket Monitor Update\n"
            f"Signal: {data.get('signal')}\n"
            f"Z-score: {data.get('z', 0):.4f}\n"
            f"Spread: {data.get('spread', 0):.6f}\n"
            f"Basket Price: {data.get('basket_price', 0):.2f}\n"
            f"Target Price: {data.get('target_price', 0):.2f}"
        )

        buttons = None
        signal = data.get('signal', "")
        if "LONG" in signal or "SHORT" in signal:
            buttons = [
                [
                    {'text': 'Open Position', 'callback_data': f'OPEN:{signal}'},
                    {'text': 'Close Position', 'callback_data': f'CLOSE:{signal}'}
                ]
            ]

        self.send_message(msg, buttons)
