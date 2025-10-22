from observer import Observer
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
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

        # Две кнопки: открыть и закрыть
        keyboard = [
            [
                InlineKeyboardButton("Открыть", callback_data="open"),
                InlineKeyboardButton("Закрыть", callback_data="close"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем сообщение с кнопками
        try:
            asyncio.run(
                self.bot.send_message(
                    chat_id=self.chat_id,
                    text=msg,
                    reply_markup=reply_markup
                )
            )
            print(f"Telegram message sent with buttons: {data['signal']}")
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")
