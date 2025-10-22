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
    basket_symbols = data.get('basket_symbols', [])
    symbols_text = "\n".join(basket_symbols) if basket_symbols else "—"

    # округление для удобного отображения
    z_score = round(data.get('z', 0), 2)
    spread = round(data.get('spread', 0), 3)
    basket_price = round(data.get('basket_price', 0), 2)
    target_price = round(data.get('target_price', 0), 2)

    msg = (
        f"Z-score: {z_score}\n"
        f"Spread: {spread}\n"
        f"Basket Price: {basket_price}\n"
        f"Target Price: {target_price}\n"
        f"Current pairs:\n{symbols_text}"
    )

    buttons = None
    signal = data.get('signal', "")
    if signal and signal != "NO DATA":
        buttons = [
            [
                {'text': 'Open Position', 'callback_data': f'OPEN:{signal}'},
                {'text': 'Close Position', 'callback_data': f'CLOSE:{signal}'}
            ]
        ]

    self.send_message(msg, buttons)
