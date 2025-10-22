from observer import Observer
from telegram import Bot
from datetime import datetime

# --- Настройки Telegram ---
TELEGRAM_BOT_TOKEN = "8436652130:AAF6On0GJtRHfMZyqD3mpM57eXZfWofJeng"
TELEGRAM_CHAT_ID = 317217451  # числовой ID чата, куда приходят уведомления

class TelegramObserver(Observer):
    def __init__(self):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)

    def update(self, data):
        # формируем сообщение
        msg = (
            f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] Basket Monitor Update\n"
            f"Signal: {data['signal']}\n"
            f"Z-score: {data['z']:.4f}\n"
            f"Spread: {data['spread']:.6f}\n"
            f"Basket Price: {data['basket_price']:.2f}\n"
            f"Target Price: {data['target_price']:.2f}"
        )
        try:
            self.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
            print("✅ Telegram message sent")
        except Exception as e:
            print("❌ Telegram send failed:", e)
