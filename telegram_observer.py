from observer import Observer
from telegram import Bot
from datetime import datetime
import asyncio

class TelegramObserver(Observer):
    def __init__(self, token: str, chat_id: str):
        self.bot = Bot(token=token)
        self.chat_id = chat_id

    def update(self, data):
        msg = (
            f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] Basket Monitor Update\n"
            f"Signal: {data['signal']}\n"
            f"Z-score: {data['z']:.4f}\n"
            f"Spread: {data['spread']:.6f}\n"
            f"Basket Price: {data['basket_price']:.2f}\n"
            f"Target Price: {data['target_price']:.2f}"
        )
        # Отправляем сообщение синхронно через asyncio.run
        try:
            asyncio.run(self.bot.send_message(chat_id=self.chat_id, text=msg))
            print(f"✅ Telegram message sent: {msg[:50]}...")
        except Exception as e:
            print(f"❌ Failed to send Telegram message: {e}")
